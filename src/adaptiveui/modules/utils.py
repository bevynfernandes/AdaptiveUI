import os
import sys

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


def pp_get(var: bool) -> str:
    """
    Returns a string representation of the given boolean variable.

    Args:
        var (bool): The boolean variable to be converted.

    Returns:
        str: The string representation of the boolean variable. Returns "Enabled" if the variable is True, and "Disabled" if it is False.
    """
    return "Enabled" if var else "Disabled"


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
