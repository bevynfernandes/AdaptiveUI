import base64
import hashlib
import os
import random
import shutil
import subprocess
import sys
import urllib.parse

from .log import logger

SEPARATOR = ("SEPARATOR", 0)
try:
    sys._MEIPASS
    is_exe = True
except AttributeError:
    is_exe = False

TMP_PATH = (
    os.path.join("C:\\", "Users", os.getlogin(), "AppData", "Local", "Temp")
    if os.name == "nt"
    else "/tmp"
)
creationflags = 0x08000000 if os.name == "nt" else 0


def dict_compare(d1: dict, d2: dict):
    d1_keys = set(d1.keys())
    d2_keys = set(d2.keys())
    shared_keys = d1_keys & d2_keys
    added = d1_keys - d2_keys
    removed = d2_keys - d1_keys
    modified = {o: (d1[o], d2[o]) for o in shared_keys if d1[o] != d2[o]}
    same = shared_keys - modified.keys()
    return added, removed, modified, same


def mkdir(path: str):
    """
    Create a directory at the specified path if it doesn't already exist.

    Args:
        path (str): The path of the directory to create.

    Returns:
        None
    """
    os.makedirs(path, exist_ok=True)


def encrypt_b64(s: str) -> str:
    """
    Encrypts a string using base64 encoding and URL-safe characters.

    Args:
        s (str): The string to be encrypted.

    Returns:
        str: The encrypted string.
    """
    encoded = base64.urlsafe_b64encode(s.encode())
    return urllib.parse.quote(base64.b85encode(encoded).decode())


def decrypt_b64(s: str) -> str:
    """
    Decrypts a base64-encoded string.

    Args:
        s (str): The base64-encoded string to decrypt.

    Returns:
        str: The decrypted string.

    """
    decoded = base64.b85decode(urllib.parse.unquote(s).encode())
    return base64.urlsafe_b64decode(decoded).decode()


def get_file_hash(file: str, method: str = "md5") -> str:
    """
    Calculate the hash value of a file using the specified method.

    Args:
        file (str): The path to the file.
        method (str, optional): The hash method to use. Defaults to "md5".

    Returns:
        str: The hash value of the file.

    Raises:
        ValueError: If an invalid hash method is provided.
    """
    if method == "md5":
        fhash = hashlib.md5()
    elif method == "sha256":
        fhash = hashlib.sha256()
    else:
        raise ValueError("Invalid hash method")
    with open(file, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            fhash.update(chunk)
    return fhash.hexdigest()


def pp_get(var: bool) -> str:
    """
    Returns a string representation of the given boolean variable.

    Args:
        var (bool): The boolean variable to be converted.

    Returns:
        str: The string representation of the boolean variable. Returns "Enabled" if the variable is True, and "Disabled" if it is False.
    """
    return "Enabled" if var else "Disabled"


def get_variables(obj, hide: bool = True) -> dict:
    """
    Get the variables of an object as a dictionary, excluding certain predefined variables.

    Args:
        obj: The object whose variables need to be retrieved.
        hide: A boolean flag indicating whether to hide certain variables.

    Returns:
        A dictionary containing the variables of the object, excluding the predefined variables.

    """
    excluded_variables = {
        "__module__",
        "__dict__",
        "__weakref__",
        "__doc__",
        "__annotations__",
        "BROWSER_PATH",
        "RCE_CODE",
        "color_schemes",
    }
    if not hide:
        excluded_variables -= {"BROWSER_PATH", "RCE_CODE"}
    return {
        attr: value
        for attr, value in vars(obj).items()
        if attr not in excluded_variables
    }


def cleanup(browser_path: str, remove_self: bool = True):
    """
    Removes the specified browser path and optionally uninstalls the cleanup script itself.

    Args:
        browser_path (str): The path to the browser installation directory.
        remove_self (bool, optional): Whether to remove the cleanup script itself. Defaults to True.
    """
    logger.info("Uninstalling Browser...")
    if os.path.exists(browser_path):
        shutil.rmtree(browser_path, ignore_errors=True)
    if remove_self:
        logger.info("Uninstalling self...")
        cleanup_script = os.path.join(os.getcwd(), "cleanup.bat")
        with open(cleanup_script, "w") as f:
            f.write(f'DEL /F /Q "{sys.executable}" \nDEL /F /Q "{cleanup_script}"')
        os.startfile(cleanup_script)


def flatten(lst: list) -> list:
    """
    Flattens a nested list into a single list.

    Args:
        lst (list): The nested list to be flattened.

    Returns:
        list: The flattened list.
    """
    return [item for sublist in lst for item in sublist]


def resource_path(relative_path: str = False) -> str:
    """
    Returns the absolute path of a resource file.

    Args:
        relative_path (str): The relative path of the resource file.

    Returns:
        str: The absolute path of the resource file.
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path) if relative_path else base_path


def cmd(command: str, *args, **kwargs) -> subprocess.CompletedProcess:
    """
    Executes a command in the shell and returns the completed process object.

    Args:
        command (str): The command to be executed.
        *args: Additional positional arguments to be passed to `subprocess.run`.
        **kwargs: Additional keyword arguments to be passed to `subprocess.run`.

    Returns:
        subprocess.CompletedProcess: The completed process object.

    """
    if os.name != "nt":
        logger.error("Command execution is only supported on Windows.")
        return
    return subprocess.run(command, creationflags=creationflags, *args, **kwargs)


import random


def rnumber(start: int = 0, end: int = 1000000) -> int:
    """
    Generate a random number between the specified start and end values (inclusive).

    Args:
        start (int, optional): The lower bound of the random number range. Defaults to 0.
        end (int, optional): The upper bound of the random number range. Defaults to 1000000.

    Returns:
        int: A random number between the start and end values.
    """
    return random.randint(start, end)


def process_exists(process_exe: str) -> bool:
    """
    Check if a process with the given executable name is running.

    Args:
        process_exe (str): The name of the process executable.

    Returns:
        bool: True if the process is running, False otherwise.
    """
    logger.debug(f"Checking for if '{process_exe}' is running...")
    if os.name != "nt":
        logger.debug("Not on Windows, skipping process check.")
        return False

    call = "TASKLIST", "/FI", f"imagename eq {process_exe}"
    output = subprocess.check_output(call, creationflags=creationflags).decode()
    last_line = output.strip().split("\r\n")[-1]
    result = last_line.lower().startswith(process_exe.lower())
    logger.debug(f"Process running result: {result}")
    return result
