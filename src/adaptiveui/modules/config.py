import json
import os
import secrets
from dataclasses import asdict, dataclass, field
from tkinter.messagebox import showerror, showwarning

from .log import logger
from .toggle_var import ToggleVar

_LOCAL_SETTINGS_W_ENABLED = (True, "")  # Local Settings write enabled
_LOCAL_SETTINGS_VERSION = 1  # Current version of local settings
_LOCAL_SETTINGS_UNSUPPORTED_VERSION = (
    0,
    _LOCAL_SETTINGS_VERSION,
)  # Lowest and highest supported version of local settings
LS_REMOVE_SAFE_FLAG = "Remove safe exit flag"


# BUILD Configs (should not be changed during runtime - with exceptions)
class BuildConfigs:
    NAME = "AdaptiveUI"
    APP_PATH = (
        f"{os.path.expanduser('~')}/AppData/Local/Programs/AdaptiveUI"
        if os.name == "nt"
        else os.path.expanduser("~") + f"/.config/AdaptiveUI"
    )


_LOCAL_SETTINGS_PATH = f"{BuildConfigs.APP_PATH}/local_settings.json"


# Changeable Configs (can be changed using the server or code during runtime)
class Configs:
    """
    A class that holds various configuration settings for the application.
    """

    AUMID = BuildConfigs.NAME
    DPI_FIX = True
    FONT = "Segoe UI"
    DARK_WINDOW_TITLE = True
    FONT_SIZE = (14, 12)


class ColorPalette:
    """
    A class representing a color palette.

    Attributes:
        bg: The background color.
        fg: The foreground color.
    """

    color_schemes = {
        "defaults": {
            "White on Dark Grey": ("#1c1c1c", "#ffffff"),
            "Light Grey on Dark Grey": ("#1c1c1c", "#d3d3d3"),
            "Light Blue on Dark Grey": ("#1c1c1c", "#add8e6"),
            "Light Green on Dark Grey": ("#1c1c1c", "#90ee90"),
            "Light Yellow on Dark Grey": ("#1c1c1c", "#ffffe0"),
            "Light Pink on Dark Grey": ("#1c1c1c", "#ffb6c1"),
            "Light Coral on Dark Grey": ("#1c1c1c", "#f08080"),
            "Light Cyan on Dark Grey": ("#1c1c1c", "#e0ffff"),
            "Light Goldenrod on Dark Grey": ("#1c1c1c", "#fafad2"),
            "Light Sky Blue on Dark Grey": ("#1c1c1c", "#87cefa"),
            "Light Peach on Dark Grey": ("#1c1c1c", "#ffdab9"),
            "Light Lavender on Dark Grey": ("#1c1c1c", "#e6e6fa"),
            "Light Mint on Dark Grey": ("#1c1c1c", "#f5fffa"),
            "Light Wheat on Dark Grey": ("#1c1c1c", "#f5deb3"),
            "Light Teal on Dark Grey": ("#1c1c1c", "#e0f0ff"),
            "Light Olive on Dark Grey": ("#1c1c1c", "#f5f5dc"),
        },
        "alternatives": {
            "Black on Yellow": ("#ffff00", "#000000"),
            "Yellow on Black": ("#000000", "#ffff00"),
            "White on Purple": ("#800080", "#ffffff"),
            "Purple on White": ("#ffffff", "#800080"),
            "White on Black": ("#000000", "#ffffff"),
            "Black on White": ("#ffffff", "#000000"),
            "Blue on Grey": ("#808080", "#0000ff"),
            "Grey on Blue": ("#0000ff", "#808080"),
            "Green on Black": ("#000000", "#008000"),
            "Black on Green": ("#008000", "#000000"),
            "Red on Yellow": ("#ffff00", "#ff0000"),
            "Yellow on Red": ("#ff0000", "#ffff00"),
            "Cyan on Black": ("#000000", "#00ffff"),
            "Black on Cyan": ("#00ffff", "#000000"),
            "White on Navy": ("#000080", "#ffffff"),
            "Navy on White": ("#ffffff", "#000080"),
            "Yellow on Navy": ("#000080", "#ffff00"),
            "Navy on Yellow": ("#ffff00", "#000080"),
            "White on Maroon": ("#800000", "#ffffff"),
            "Maroon on White": ("#ffffff", "#800000"),
        },
        "light_mode": {
            "Black on Light Grey": ("#d3d3d3", "#000000"),
            "Navy on Light Yellow": ("#ffffe0", "#000080"),
            "Maroon on Light Cyan": ("#e0ffff", "#800000"),
            "Green on Light Peach": ("#ffdab9", "#008000"),
            "Purple on Light Lavender": ("#e6e6fa", "#800080"),
            "Blue on Light Mint": ("#f5fffa", "#0000ff"),
            "Red on Light Teal": ("#e0f0ff", "#ff0000"),
            "Brown on Light Pink": ("#ffb6c1", "#a52a2a"),
            "Orange on Light Blue": ("#add8e6", "#ff4500"),
        },
        "saved": {},
    }

    _default_selected_color_scheme = "White on Dark Grey"
    _selected_color_scheme = _default_selected_color_scheme
    bg = color_schemes["defaults"][_selected_color_scheme][0]
    fg = color_schemes["defaults"][_selected_color_scheme][1]

    @classmethod
    def randomise(cls):
        cls.bg = f"#{secrets.token_hex(3)}"
        cls.fg = f"#{secrets.token_hex(3)}"

        logger.info(f"Set random color palette: bg={cls.bg}, fg={cls.fg}")


class MagicNumbers:
    "A magic number is a numeric literal that is used in the code without any explanation of its meaning (even I don't know why)."
    UI_CS_WINDOW_HEIGHT = 10  # At least its my size for my display


class AdaptiveUIConfigs:
    TOOLS_ENABLED = True
    INFO_GRAB_INPUT_ENABLED = ToggleVar("INFO_GRAB_INPUT_ENABLED", True)
    BUTTON_TYPE = "TButton"  # TButton or Accent.TButton
    START_ANIMATION_ENABLED = ToggleVar("ANIMATION_ENABLED", True)
    EXIT_ANIMATION_ENABLED = ToggleVar("ANIMATION_ENABLED", True)


@dataclass(slots=True)
class _LocalSettings:
    """
    Class representing local settings for the application.
    """

    _version: int = _LOCAL_SETTINGS_VERSION

    dark_mode: bool = True

    selected_colorpalette: str = "defaults, White on Dark Grey"
    saved_colorpalettes: dict[str, list[str, str]] = field(default_factory=dict)

    _last_update_reason: str = ""

    def write(self, reason: str):
        """
        Write the configuration settings to the local storage.

        Args:
            reason (str): The reason for writing the settings.

        Returns:
            None
        """
        LocalSettings.write(self, reason)


class LocalSettings:
    __cache: _LocalSettings = None

    @staticmethod
    def _ensure_path_exists():
        if not os.path.exists(_LOCAL_SETTINGS_PATH):
            os.makedirs(os.path.dirname(_LOCAL_SETTINGS_PATH), exist_ok=True)

    @classmethod
    def _read(cls) -> _LocalSettings:
        error = ""
        logger.info("Reading local settings...")
        cls._ensure_path_exists()

        if not os.path.exists(_LOCAL_SETTINGS_PATH):
            logger.info("Local settings not found. Creating new settings...")
            return _LocalSettings()

        with open(_LOCAL_SETTINGS_PATH, "r") as f:
            try:
                lsettings = json.load(f)
                if lsettings["_version"] < _LOCAL_SETTINGS_UNSUPPORTED_VERSION[0]:
                    logger.error(
                        f"Unsupported local settings version: {lsettings['_version']}"
                    )
                    error = (
                        "Unsupported local settings version. Settings have been reset."
                    )
                elif lsettings["_version"] > _LOCAL_SETTINGS_UNSUPPORTED_VERSION[1]:
                    error = "Local settings version is higher than the supported version. Some Settings fail may to load."
                    logger.warning(error)
                    showwarning(BuildConfigs.NAME, error)
                    try:
                        return _LocalSettings(**lsettings)
                    except Exception:
                        error = "Failed to load local settings from a higher version. Settings have been reset."
                        logger.error(error)
                else:
                    return _LocalSettings(**lsettings)
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.error(f"Failed to read local settings: {e}")
                error = "Failed to read local settings. Settings have been reset."

        os.remove(_LOCAL_SETTINGS_PATH)
        showerror(
            BuildConfigs.NAME,
            error,
        )
        return _LocalSettings()

    @classmethod
    def read(cls) -> _LocalSettings:
        if cls.__cache is None:
            cls.__cache = cls._read()
        return cls.__cache

    @classmethod
    def write(cls, settings: _LocalSettings, reason: str):
        logger.info(f"Writing local settings for reason: {reason}...")
        if not reason == LS_REMOVE_SAFE_FLAG:
            settings._last_update_reason = reason

        if not _LOCAL_SETTINGS_W_ENABLED[0]:
            logger.warning(
                f"Local settings write is disabled. Reason: {_LOCAL_SETTINGS_W_ENABLED[1]}"
            )
            return

        cls._ensure_path_exists()

        with open(_LOCAL_SETTINGS_PATH, "w") as f:
            json.dump(asdict(settings), f, indent=4)

        cls.__cache = settings
