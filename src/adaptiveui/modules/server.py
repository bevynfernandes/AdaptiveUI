import json
import socket
import threading
import uuid
import zlib
from datetime import datetime
from random import randint

from .config import BuildConfigs
from .log import logger

INSTANCE_ID = randint(0, 100000)


class InternalSignals:
    ERROR_SIGNAL_IGNORED = "__error_signal_ignored"
    ERROR_SIGNAL_NOT_FOUND = "__error_signal_not_found"
    ERROR_REQUIREMENTS_MISMATCH = "__error_requirements_mismatch"
    SUCCESS_SIGNAL_PROCESSED = "__success_signal_processed"
    FETCH_SOCKET_METADATA = "__fetch_socket_metadata"


def generate_metadata(request_id: str = None) -> dict:
    return {
        "instance_id": INSTANCE_ID,
        "name": BuildConfigs.NAME,
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id if request_id is not None else str(uuid.uuid4()),
    }


def dict_compare(d1: dict, d2: dict):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared_keys = d1_keys & d2_keys
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in shared_keys if d1[o] != d2[o]}
    same = shared_keys - modified.keys()
    return added, removed, modified, same


class SocketServer:
    """
    A class representing a socket server.

    Attributes:
        signals (dict): A dictionary mapping signals to corresponding functions.
        host (str): The host IP address to bind the server to. Default is "127.0.0.1".
        port (int): The port number to bind the server to. Default is 50007.
        requires (dict): A dictionary specifying the required parameters for signal processing.

    Raises:
        ValueError: If the port number is not between 49152 and 65535.

    Methods:
        handle_client: Handles a client connection.
        receive: Starts the server and listens for incoming connections.
        attach_metadata: Attaches additional metadata to the server.
    """

    def __init__(
        self,
        signals: dict,
        host: str = "127.0.0.1",
        port: int = 50007,
        requires: dict = {},
    ):
        self.signals = signals
        self.host = host
        self.port = port
        self.requires = requires

        if port < 49152 or port > 65535:
            raise ValueError("Port number must be between 49152 and 65535")

        self._extra_metadata = []
        self.server_thread = threading.Thread(target=self.receive, daemon=True)
        self.server_thread.start()

    def attach_metadata(self, function):
        """
        Attaches additional metadata to the server.

        Args:
            function: The function that generates the additional metadata.
        """
        self._extra_metadata.append(function)

    def _get_metadata(self, request_id: str = None):
        """
        Retrieves the metadata for a request.

        Args:
            request_id (str): The ID of the request.

        Returns:
            dict: The metadata for the request.
        """
        metadata = generate_metadata(request_id)
        metadata["attached"] = {}
        for func in self._extra_metadata:
            metadata["attached"].update(func())
        return metadata

    def handle_client(self, conn: socket.socket, addr: str):
        """
        Handles a client connection.

        Args:
            conn (socket.socket): The client socket connection.
            addr (str): The client address.

        Raises:
            Exception: If an error occurs during the handling of the client connection.
        """
        try:
            logger.debug(f"Connected to {addr}...")
            compressed_data = conn.recv(1024)
            # Decompress the data after receiving
            data: dict = json.loads(zlib.decompress(compressed_data).decode())
            signal: str = data.get("signal")
            params: dict = data.get("params")
            logger.debug(f"Received signal: {signal}")

            if (
                params.get("__socket_metadata", {}).get("instance_id", "<UNKNOWN>")
                == INSTANCE_ID
            ):
                logger.warning("Ignoring signal from self")
                self._send(
                    conn,
                    InternalSignals.ERROR_SIGNAL_IGNORED,
                    {"message": "Ignoring signal from self"},
                    params.get("request_id"),
                )
            elif not params.get("__socket_requires", {}) == self.requires:
                not_met = dict_compare(
                    params.get("__socket_requires", {}), self.requires
                )[2]
                logger.error(
                    f"Signal does not meet the requirements. Mismatch: {not_met}",
                )
                self._send(
                    conn,
                    InternalSignals.ERROR_REQUIREMENTS_MISMATCH,
                    {"message": f"Requirements Mismatch: {not_met}"},
                    params.get("request_id"),
                )
            elif signal == InternalSignals.FETCH_SOCKET_METADATA:
                logger.debug("Sending socket metadata...")
                self._send(
                    conn,
                    InternalSignals.SUCCESS_SIGNAL_PROCESSED,
                    request_id=params.get("request_id"),
                )
            elif signal in self.signals:
                function, function_params = self.signals[signal]
                function(**{k: params.get(k, v) for k, v in function_params.items()})
                self._send(
                    conn,
                    InternalSignals.SUCCESS_SIGNAL_PROCESSED,
                    {"message": f"Signal '{signal}' processed successfully"},
                    params.get("request_id"),
                )
            else:
                self._send(
                    conn,
                    InternalSignals.ERROR_SIGNAL_NOT_FOUND,
                    {"message": f"Signal '{signal}' not found"},
                    params.get("request_id"),
                )
                logger.error(f"Signal '{signal}' not found!")
            logger.debug(f"Signal '{signal}' processed")
        except Exception as e:
            logger.exception(e)
        finally:
            conn.close()

    def _send(
        self,
        conn: socket.socket,
        signal: str,
        params: dict = {},
        request_id: str = None,
    ):
        """
        Sends a signal to the client.

        Args:
            conn (socket.socket): The client socket connection.
            signal (str): The signal to send.
            params (dict): The parameters to include in the signal.
            request_id (str): The ID of the request.
        """
        # Compress the data before sending
        compressed_data = zlib.compress(
            json.dumps(
                {"signal": signal, "params": params}
                | {"__socket_metadata": self._get_metadata(request_id)}
            ).encode()
        )
        conn.sendall(compressed_data)

    def receive(self):
        """
        Starts the server and listens for incoming connections.

        Raises:
            Exception: If an error occurs during the server setup or while listening for connections.
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.host, self.port))
                s.listen(1)
                while True:
                    conn, addr = s.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client, args=(conn, addr), daemon=True
                    )
                    client_thread.start()
        except Exception as e:
            logger.error(f"An error occurred: {e}")


class SocketClient:
    """
    Represents a client that communicates with a server using sockets.

    Args:
        host (str): The IP address or hostname of the server. Defaults to "127.0.0.1".
        port (int): The port number of the server. Defaults to 50007.
        requires (dict): A dictionary of required data for the server. Defaults to an empty dictionary.

    Attributes:
        host (str): The IP address or hostname of the server.
        port (int): The port number of the server.
        requires (dict): A dictionary of required data for the server.

    Methods:
        send: Sends a signal to the server with optional parameters and waits for a response.
        get_server_info: Sends a request to the server to get its metadata.

    """

    def __init__(self, host: str = "127.0.0.1", port: int = 50007, requires: dict = {}):
        self.host = host
        self.port = port
        self.requires = requires

    def _receive_data(self, s: socket.socket) -> dict:
        """
        Receives and interprets data from the server.

        Args:
            s (socket.socket): The socket object used for communication with the server.

        Returns:
            dict: The interpreted response data from the server.

        """
        try:
            compressed_data = s.recv(1024)
            data: dict = json.loads(zlib.decompress(compressed_data).decode())
            logger.debug(f"Response from server: {data.get('message', data)}")
        finally:
            s.close()
        return self._interpret_response(data)

    def _interpret_response(self, data: dict) -> dict:
        """
        Interprets the response received from the server.

        Args:
            data (dict): The response data received from the server.

        Returns:
            dict: The interpreted response data.

        """
        signal: str = data.get("signal")
        message: str = data.get("params", {}).get("message", "<No message>")

        signal_log_map = {
            InternalSignals.ERROR_SIGNAL_IGNORED: logger.error,
            InternalSignals.ERROR_SIGNAL_NOT_FOUND: logger.error,
            InternalSignals.ERROR_REQUIREMENTS_MISMATCH: logger.error,
            InternalSignals.SUCCESS_SIGNAL_PROCESSED: logger.debug,
        }

        log_func = signal_log_map.get(signal, logger.info)
        log_func(f"Received Signal response - {signal} | Message: {message}")

        return data

    def send(
        self, signal: str, params: dict = {}, wait_for_response: bool = True
    ) -> dict:
        """
        Sends a signal to the server with optional parameters and waits for a response.

        Args:
            signal (str): The signal to be sent to the server.
            params (dict): Optional parameters to be sent along with the signal. Defaults to an empty dictionary.
            wait_for_response (bool): Whether to wait for a response from the server. Defaults to True.

        Returns:
            dict: The response data received from the server, if wait_for_response is True. Otherwise, returns None.

        """
        params["__socket_metadata"] = generate_metadata()
        params["__socket_requires"] = self.requires

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.settimeout(10.0)
            s.connect((self.host, self.port))
            # Compress the data before sending
            compressed_data = zlib.compress(
                json.dumps({"signal": signal, "params": params}).encode()
            )
            s.sendall(compressed_data)
            if wait_for_response:
                return self._receive_data(s)
            else:
                thread = threading.Thread(target=self._receive_data, args=(s,))
                thread.start()
                return None
        except socket.timeout:
            if wait_for_response:
                logger.error("A timeout occurred")
        except Exception as e:
            logger.exception(e)
            s.close()

    def get_server_info(self) -> dict:
        """
        Sends a request to the server to get its metadata.

        Returns:
            dict: The server's metadata.

        """
        data = self.send(InternalSignals.FETCH_SOCKET_METADATA)
        return data["__socket_metadata"]
