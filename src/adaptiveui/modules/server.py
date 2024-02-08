import json
import socket
import threading
import uuid
from datetime import datetime
from random import randint

from .config import BuildConfigs
from .log import logger

INSTANCE_ID = randint(0, 100000)

def generate_metadata(request_id: str = None) -> dict:
    return {
        "instance_id": INSTANCE_ID,
        "name": BuildConfigs.NAME,
        "timestamp": datetime.now().isoformat(),
        "request_id": request_id if request_id is not None else str(uuid.uuid4()),
    }


class SocketServer:
    """
    A class representing a socket server.

    Attributes:
        signals (dict): A dictionary mapping signals to corresponding functions.
        host (str): The host IP address to bind the server to. Default is "127.0.0.1".
        port (int): The port number to bind the server to. Default is 50007.

    Raises:
        ValueError: If the port number is not between 49152 and 65535.

    Methods:
        handle_client: Handles a client connection.
        receive: Starts the server and listens for incoming connections.
    """

    def __init__(self, signals: dict, host: str = "127.0.0.1", port: int = 50007):
        self.signals = signals
        self.host = host
        self.port = port

        if port < 49152 or port > 65535:
            raise ValueError("Port number must be between 49152 and 65535")

        self._extra_metadata = []
        self.server_thread = threading.Thread(target=self.receive, daemon=True)
        self.server_thread.start()

    def attach_metadata(self, function):
        self._extra_metadata.append(function)

    def _get_metadata(self, request_id: str = None):
        metadata = generate_metadata(request_id)
        for func in self._extra_metadata:
            metadata.update(func())
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
            data: dict = json.loads(conn.recv(1024).decode())
            signal: str = data.get("signal")
            params: dict = data.get("params")
            logger.debug(f"Received signal: {signal}")
            if params.get("__socket_metadata").get("instance_id") == INSTANCE_ID:
                logger.warning("Ignoring signal from self")
                self._send(conn, "__error_signal_ignored", {"message": "Ignoring signal from self"}, params.get("request_id"))
            elif signal == "__fetch_socket_metadata":
                logger.debug("Sending socket metadata...")
                self._send(
                    conn, "__procesed", request_id=params.get("request_id")
                )
            elif signal in self.signals:
                function, function_params = self.signals[signal]
                function(**{k: params.get(k, v) for k, v in function_params.items()})
                self._send(
                    conn,
                    "__success_signal_processed",
                    {"message": f"Signal '{signal}' processed successfully"},
                    params.get("request_id"),
                )
            else:
                self._send(
                    conn,
                    "__error_signal_not_found",
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
        conn.sendall(
            json.dumps(
                {"signal": signal, "params": params}
                | {"__socket_metadata": self._get_metadata(request_id)}
            ).encode()
        )

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
    A class representing a socket client.

    Attributes:
        host (str): The host IP address to connect to. Default is "127.0.0.1".
        port (int): The port number to connect to. Default is 50007.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 50007):
        self.host = host
        self.port = port

    def send(
        self, signal: str, params: dict = {}, wait_for_response: bool = True
    ) -> str:
        """
        Sends a signal with parameters to the server.

        Args:
            signal (str): The signal to send.
            params (dict): The parameters to send along with the signal.
            wait_for_response (bool): Whether to wait for a response from the server. Default is True.

        Returns:
            bool: True if the signal was successfully sent, False otherwise.
        """
        params["__socket_metadata"] = generate_metadata()

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10.0)  # set a timeout of 5 seconds
                s.connect((self.host, self.port))
                s.sendall(json.dumps({"signal": signal, "params": params}).encode())
                if wait_for_response:
                    data = s.recv(1024).decode()
                    jdata: dict = json.loads(data)
                    logger.debug(f"Response from server: {jdata.get("message", jdata)}")
                    return data
                else:
                    return None
        except socket.timeout:
            if wait_for_response:
                logger.error("A timeout occurred")
        except Exception as e:
            logger.exception(e)

    def get_server_info(self) -> dict:
        """
        Sends a request to the server to get its __socket_metadata.

        Returns:
            dict: The server's __socket_metadata.
        """
        data = self.send("__fetch_socket_metadata")
        return json.loads(data)["__socket_metadata"]
