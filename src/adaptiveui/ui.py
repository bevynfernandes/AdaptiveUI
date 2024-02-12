# AdaptiveUI - My custom UI warpper for tkinter

import colorsys
import ctypes
import os
import re
import tkinter as tk
import tkinter.font as tkfont
from io import StringIO
from pprint import pformat
from sys import excepthook
from threading import Thread
from tkinter import ttk
from typing import Callable, Iterator

import sv_ttk
from PIL import Image, ImageTk

from .modules.config import *
from .modules.exceptions import UIUnbindError
from .modules.log import logger
from .modules.server import SocketClient, SocketServer
from .modules.utils import SEPARATOR, resource_path

DPI_FIX_DONE = False
FaultTolerantTk = tk.Tk

class AdaptiveUIInfo:
    VERSION = "1.1.0"
    AUTHOR = "EpicGamerCodes"
    LICENSE = "GPL v3"

class Images:
    """A class containing the paths to the images used in the UI."""
    ICON = resource_path("data/images/icon.png")
    WARNING = resource_path("data/images/warning.png")
    ERROR = resource_path("data/images/error.png")
    NO_ENTRY = resource_path("data/images/no_entry.png")
    SUCCESS = resource_path("data/images/success.png")

class Signals:
    """A class containing the socket signals used in the UI."""
    UPDATE_COLORS = f"AUI_UPDATE_COLORS"
    INFO_POPUP = f"AUI_INFO_POPUP"
    ERROR_OCCURRED = f"AUI_ERROR_OCCURRED"


def dpi_fix():
    """Fixes the DPI scaling issue on Windows on High DPI devices."""
    global DPI_FIX_DONE
    if os.name == "nt":
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(Configs.AUMID)
        if Configs.DPI_FIX and not DPI_FIX_DONE:
            DPI_FIX_DONE = True
            ctypes.windll.shcore.SetProcessDpiAwareness(1)

def _adjust_color_brightness(color: str, factor: float) -> str:
    """
    Adjust the brightness of a color.

    Parameters:
        color (str): The color to adjust in hex format.
        factor (float): The factor by which to adjust the brightness.

    Returns:
        str: The adjusted color in hex format.
    """
    # Check if color is a valid hex color string
    if not isinstance(color, str) or len(color) != 7 or not color.startswith('#'):
        raise ValueError('Invalid color. Expected a hex color string.')

    # Convert the hex color to RGB
    r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

    # Convert the RGB color to HSV
    h, s, v = colorsys.rgb_to_hsv(r/255., g/255., b/255.)

    # Adjust the brightness
    v = max(0, min(1, v * factor))

    # Convert the HSV color back to RGB
    r, g, b = colorsys.hsv_to_rgb(h, s, v)

    # Convert the RGB color back to hex
    return f'#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}'

def darken_color(color: str, factor=0.75) -> str:
    """
    Darken a color.

    Parameters:
        color (str): The color to darken in hex format.
        factor (float): The factor by which to darken the color. Default is 0.75.

    Returns:
        str: The darkened color in hex format.
    """
    return _adjust_color_brightness(color, factor)

def lighten_color(color: str, factor=1.75) -> str:
    """
    Lighten a color.

    Parameters:
        color (str): The color to lighten in hex format.
        factor (float): The factor by which to lighten the color. Default is 1.75.

    Returns:
        str: The lightened color in hex format.
    """
    return _adjust_color_brightness(color, factor)

def set_rc_menu(rc_menu: tk.Menu, items: list[tuple[str]]):
    """
    Sets up a right-click menu with the given items.

    Args:
        rc_menu (tk.Menu): The right-click menu to set up.
        items (list[tuple[str]]): A list of tuples containing the label and command for each menu item.

    Returns:
        None
    """
    for label, command in items:
        if label == SEPARATOR[0]:
            rc_menu.add_separator(background=ColorPalette.bg)
        else:
            rc_menu.add_command(label=label, command=command, background=ColorPalette.bg, foreground=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg))

def color_title_bar(window: FaultTolerantTk, dark: bool = True):
    """
    Sets the color of the title bar of the specified window to dark or light.

    Args:
        window (FaultTolerantTk): The window whose title bar color will be set.
        dark (bool, optional): Determines whether the title bar color should be dark or light. 
            Defaults to True (dark).

    Returns:
        None
    """
    if not Configs.DARK_WINDOW_TITLE:
        return
    
    if os.name != "nt":
        logger.debug("Not on Windows, skipping title bar color change.")
        return

    logger.debug(f"Setting title bar of '{window.winfo_name()}' to {"dark" if dark else "light"}...")
    window.update()
    hwnd = ctypes.windll.user32.GetParent(window.winfo_id())
    rendering_policy = 20
    value = ctypes.c_int(2) if dark else ctypes.c_int(0)
    value_size = ctypes.sizeof(value)
    ctypes.windll.dwmapi.DwmSetWindowAttribute(
        hwnd, rendering_policy, ctypes.byref(value), value_size
    )
    
    # Some odd trick to make sure it applies
    window.geometry(str(window.winfo_width()+1) + "x" + str(window.winfo_height()+1))
    window.geometry(str(window.winfo_width()-1) + "x" + str(window.winfo_height()-1))

class MarkdownText(tk.Text):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default_font = tkfont.nametofont(self.cget("font"))

        em = default_font.measure("m")
        default_size = default_font.cget("size")
        
        bold_font_config = default_font.configure()
        bold_font_config['weight'] = 'bold'
        bold_font = tkfont.Font(**bold_font_config)

        italic_font_config = default_font.configure()
        italic_font_config['slant'] = 'italic'
        italic_font = tkfont.Font(**italic_font_config)
        
        strike_font_config = default_font.configure()
        strike_font_config['overstrike'] = True
        strike_font = tkfont.Font(**strike_font_config)

        blockquote_font_config = default_font.configure()
        blockquote_font_config['slant'] = 'italic'
        blockquote_font = tkfont.Font(**blockquote_font_config)

        code_font_config = default_font.configure()
        code_font_config['family'] = 'Courier'
        code_font = tkfont.Font(**code_font_config)

        self.tag_configure(">", font=blockquote_font, lmargin1=em, lmargin2=em)
        self.tag_configure("```", font=code_font, background="#f0f0f0")
        self.tag_configure("**", font=bold_font)
        self.tag_configure("*", font=italic_font)
        self.tag_configure("~~", font=strike_font)
        self.tag_chars = "*"
        self.tag_chars += "~"
        self.tag_char_re = re.compile(r"[*~]")

        max_heading = 3
        for i in range(1, max_heading + 1):
            header_font_config = default_font.configure()
            header_font_config['size'] = int(default_size * i + 3)
            header_font_config['weight'] = 'bold'
            header_font = tkfont.Font(**header_font_config)
            self.tag_configure("#" * (max_heading - i), font=header_font, spacing3=default_size)

        lmargin2 = em + default_font.measure("\u2022 ")
        self.tag_configure("bullet", lmargin1=em, lmargin2=lmargin2)
        lmargin2 = em + default_font.measure("1. ")
        self.tag_configure("numbered", lmargin1=em, lmargin2=lmargin2)

        self.numbered_index = 1

    def insert_bullet(self, position, text):
        self.insert(position, f"\u2022 {text}", "bullet")

    def insert_numbered(self, position, text):
        self.insert(position, f"{self.numbered_index}. {text}", "numbered")
        self.numbered_index += 1

    def insert_markdown(self, mkd_text: str):
        if not isinstance(mkd_text, str):
            mkd_text = str(mkd_text)

        self.code_block = False

        for line in mkd_text.split("\n"):
            if line == "":
                self.numbered_index = 1
                self.insert("end", line)
            elif line.startswith("#"):
                tag = re.match(r"(#+) (.*)", line)
                self.insert("end", tag.group(2), tag.group(1))
            elif line.startswith("* "):
                self.insert_bullet("end", line[2:])
            elif line.startswith("~~"):
                self.insert("end", line[2:-2], "~~")
            elif line.startswith("1. "):
                self.insert_numbered("end", line[2:])
            elif line.startswith(">"):
                self.insert("end", line[1:], ">")
            elif line.startswith("```"):
                if self.code_block:
                    self.insert("end", line[3:], "```")
                    self.code_block = False
                else:
                    self.code_block = True
            elif self.code_block:
                self.insert("end", line, "```")
            elif not self.tag_char_re.search(line):
                self.insert("end", line)
            else:
                tag = None
                accumulated = []
                skip_next = False
                for i, c in enumerate(line):
                    if skip_next:
                        skip_next = False
                        continue
                    if c in self.tag_chars and (not tag or c == tag[0]):
                        if tag:
                            self.insert("end", "".join(accumulated), tag)
                            accumulated = []
                            tag = None
                        else:
                            self.insert("end", "".join(accumulated))
                            accumulated = []
                            tag = c
                            next_i = i + 1
                            if len(line) > next_i and line[next_i] == tag:
                                tag = line[i : next_i + 1]
                                skip_next = True
                    else:
                        accumulated.append(c)
                self.insert("end", "".join(accumulated), tag)
            self.insert("end", "\n")

class StyleManager:
    def __init__(self):
        self.style = ttk.Style()
        sv_ttk.set_theme("dark")
    
    def set_color(self, bg: str, fg: str):
        self.style.map('TButton',
            foreground=[('pressed', lighten_color(fg)), ('active', fg)],
        )
        
        widgets = ('TButton', 'TButton.label', 'TLabel', 'TEntry', 'Horizontal.TProgressbar',
                   'Vertical.TScrollbar', 'TSeparator', 'TFrame', 'Treeview')
        for widget in widgets:
            self.style.configure(widget, background=bg, foreground=fg)

class Tools:
    @staticmethod
    def center_window(
        window: FaultTolerantTk | tk.Toplevel, size: list = None, simple: bool = True
    ) -> FaultTolerantTk | tk.Toplevel:
        """
        Centers the specified window on the screen.

        Args:
            window (FaultTolerantTk | tk.Toplevel): The window to center.
            size (list, optional): The size of the window as a list of width and height. Defaults to None.
            simple (bool, optional): Whether to use a simple centering method. Defaults to True.

        Returns:
            FaultTolerantTk | tk.Toplevel: The centered window.
        """
        if not simple:
            w, h = size or (window.winfo_width(), window.winfo_height())
            ws, hs = window.winfo_screenwidth(), window.winfo_screenheight()
            window.geometry("+%d+%d" % ((ws / 2) - (w / 2), (hs / 2) - (h / 2)))
        else:
            window.eval("tk::PlaceWindow . center")
        return window

    @staticmethod
    def init_placeholder(widget: tk.Entry, placeholder_text: str, show: str = None):
        widget.placeholder = placeholder_text
        if not widget.get():
            widget.insert("end", placeholder_text)

        widget.bind("<FocusIn>", lambda event: Tools.remove_placeholder(event, show))
        widget.bind("<FocusOut>", Tools.add_placeholder)

    @staticmethod
    def remove_placeholder(event: tk.Event, show: str):
        widget = event.widget
        if widget.get() == getattr(widget, "placeholder", ""):
            widget.config(show=show)
            widget.delete(0, "end")

    @staticmethod
    def add_placeholder(event: tk.Event):
        widget = event.widget
        if not widget.get():
            widget.config(show="")
            widget.insert(0, getattr(widget, "placeholder", ""))

    @staticmethod
    def text(
        default_text: str = False,
        edit: bool = False,
        height: int = 2,
        width: int = 40,
        font: tuple = (Configs.FONT, Configs.FONT_SIZE[0]),
        borderwidth: int = 0,
        window: FaultTolerantTk | tk.Toplevel = None,
        markdown: bool = False,
    ) -> tk.Text:
        """
        Creates a text widget with customizable properties.

        Args:
            default_text (str, optional): The default text to display in the widget. Defaults to False.
            edit (bool, optional): Whether the widget is editable. Defaults to False.
            height (int, optional): The height of the widget in lines. Defaults to 2.
            width (int, optional): The width of the widget in characters. Defaults to 40.
            font (tuple, optional): The font of the widget specified as a tuple of font family and size. Defaults to (Configs.FONT, Configs.FONT_SIZE[0]).
            borderwidth (int, optional): The width of the widget's border. Defaults to 0.
            window (FaultTolerantTk | tk.Toplevel, optional): The parent window for the widget. Defaults to None.

        Returns:
            tk.Text: The created text widget.
        """
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(size=Configs.FONT_SIZE[0])
        
        txt = MarkdownText(
            window,
            height=height,
            width=width,
            borderwidth=borderwidth,
            bg=ColorPalette.bg,
            fg=ColorPalette.fg,
            wrap=tk.WORD,
            font=default_font
        )
        txt.configure(font=font)
        if default_text:
            if markdown and isinstance(default_text, str):
                txt.insert_markdown(default_text)
            else:
                txt.insert("end", default_text)
        if not edit:
            txt.config(state="disabled")
        return txt

    @staticmethod
    def button(
        label: str,
        command,
        ret: bool = False,
        window: FaultTolerantTk | tk.Toplevel = False,
        pady=0,
        bind_return: bool = True,
    ) -> ttk.Button:
        btn = ttk.Button(window, text=label, command=command, style=AdaptiveUIConfigs.BUTTON_TYPE)
        if bind_return:
            btn.bind("<Return>", lambda _: command())
        if ret:
            return btn

class SharedFrame(ttk.Frame):
    """A class representing a shared frame.

    Args:
        parent: The parent FaultTolerantTk instance.
        *args: Variable length argument list.
        **kwargs: Arbitrary keyword arguments.

    Attributes:
        text: A StringVar for storing text.
        notice: A StringVar for storing notice.
        wait_var: A BooleanVar for storing wait status.
        master: The parent FaultTolerantTk instance.
        label_font: The font settings for labels.
        notice_font: The font settings for notices.
        label_settings: The settings for labels.
        notice_settings: The settings for notices.

    Methods:
        clear_frame: Clears the frame.
        apack: Packs the frame with config.
        loading: Displays a loading screen.

    """
    def __init__(self, parent: FaultTolerantTk, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.text = tk.StringVar()
        self.notice = tk.StringVar()
        self.wait_var = tk.BooleanVar(self, value=False)
        self.master = parent
        self.label_font = (Configs.FONT, Configs.FONT_SIZE[0])
        self.notice_font = (Configs.FONT, Configs.FONT_SIZE[1])
        self.label_settings = {
            "textvariable": self.text,
            "font": self.label_font,
            "justify": tk.CENTER,
            "wraplength": 400,
        }
        self.notice_settings = {
            "textvariable": self.notice,
            "font": self.notice_font,
            "justify": tk.CENTER,
            "wraplength": 400,
        }

    def clear(self):
        """Clears the frame."""
        for widget in self.winfo_children():
            widget.destroy()

    def _apack(self):
        """Auto Pack with config"""
        self.pack(fill="both", expand=True)

    def loading(self, after=None, step: bool = False, max_len: int = 400):
        """Displays a loading screen.

        Args:
            after: A function to be called after loading.
        """
        self.clear()
        self._apack()
        self._label = ttk.Label(self, **self.label_settings, background=ColorPalette.bg, foreground=ColorPalette.fg)
        self._label.pack()
        self._progress_bar = ttk.Progressbar(
            self, orient="horizontal", mode="indeterminate" if not step else "determinate", length=max_len
        )
        if not step:
            self._progress_bar.start(20)
        self._progress_bar.pack(pady=5)
        self._notice = ttk.Label(self, **self.notice_settings, background=ColorPalette.bg, foreground=ColorPalette.fg)
        self._notice.pack(pady=5)
        if after is not None:
            self.after(1, after)

class _Info:
    def __init__(
        self,
        window: FaultTolerantTk | SharedFrame,
        text: str | StringIO,
        title: str = BuildConfigs.NAME,
        notice: str = "",
        wait_var: tk.BooleanVar = None,
        grab_input: bool = True,
        global_grab: bool = False,
        button_name: str | None = "Continue",
        scrollbar_enabled: int = 1, # 1 = Enabled (Auto) | 2 = Force Enabled | 0 = Disabled
        show_text_box: bool = True,
        add_image: str = False,
        markdown: bool = False,
    ):
        self.window = window
        self.text = text
        self.title = title
        self.notice = notice
        self.set_window = isinstance(self.window, SharedFrame)
        self.grab_input = grab_input
        self.global_grab = global_grab
        self.button_name = button_name
        self.scrollbar_enabled = scrollbar_enabled
        self.show_text_box = show_text_box
        self.add_image = add_image
        self.markdown = markdown
        
        self.button = None
        self.last_log_data = None

        self.wait_var = wait_var or self.window.wait_var
        if self.set_window:
            self.wait_var.set(False)
        
        self.popup = self.create_popup()
        self.f = ttk.Frame(self.popup)
        oldgeo = self.popup.geometry().split("+")[0].split("x")
        self.popup.minsize(int(oldgeo[0]) + 416, int(oldgeo[1]) + 70)

    def cont(self, *args):
        if not self.set_window:
            self.popup.destroy()
        self.wait_var.set(True)

    def start(self):
        if self.add_image:
            self.create_image()
        self.f.pack(side="top", fill="both", expand=True)

        if self.show_text_box:
            self.create_text()
        if self.notice:
            self.create_notice()
        if not self.button_name is None:
            self.create_button()
        if isinstance(self.text, StringIO):
            self.update_log()
        elif self.grab_input and AdaptiveUIConfigs.INFO_GRAB_INPUT_ENABLED:
            self.popup.lift()
            self.popup.focus_force()
            if self.global_grab:
                self.popup.grab_set_global()
            else:
                self.popup.grab_set()
            self.window.wait_window(self.popup)

    def create_popup(self):
        if not self.set_window:
            size = ""
            if isinstance(self.text, StringIO):
                size = (1014, 329)
            elif self.add_image:
                size = (400, 270)
            popup = UserInterface._create_window(
                self.title, center=True, is_toplevel=self.window, size=size, resizable=True
            )
            popup.bind("<Escape>", lambda _: popup.destroy())
        else:
            popup = self.window
            popup.clear()
            self.oldgeo = popup.master.geometry()
            popup.master.geometry("")
        return popup

    def create_image(self):
        # Load the image
        image = Image.open(self.add_image)
        # Resize the image
        image = image.resize((128, 128), Image.Resampling.LANCZOS)
        self.image = ImageTk.PhotoImage(image)
        # Create a label with the image
        self.image_label = ttk.Label(self.popup, image=self.image)
        # Add the label to the left side of the popup
        self.image_label.pack(side="left", padx=8)

    def create_text(self):
        # Configure self.f to expand
        self.f.grid_rowconfigure(0, weight=1)
        self.f.grid_columnconfigure(0, weight=1)

        self.wtext = Tools.text(default_text=self.text, window=self.f, markdown=self.markdown)

        # Delay the scrollbar check until after the widget has been drawn
        self.wtext.after_idle(self.check_scrollbar)

        self.wtext.grid(row=0, column=0, sticky='nsew', padx=8 if not self.add_image else 0, pady=8)

    def check_scrollbar(self):
        count = int(self.wtext.index('end-1c').split('.')[0])
        window_height = MagicNumbers.UI_CS_WINDOW_HEIGHT # Quick Fix
        #window_height = self.wtext.count("1.0", "end", "displaylines")[0]
        if (self.scrollbar_enabled and count > window_height) or self.scrollbar_enabled == 2:
            scrollbar = ttk.Scrollbar(self.f, orient=tk.VERTICAL)
            self.wtext.configure(yscrollcommand=scrollbar.set)
            scrollbar.config(command=self.wtext.yview)
            scrollbar.grid(row=0, column=1, sticky='ns')
        else:
            self.scrollbar_enabled = False
        
        if self.button is not None:
            try:
                self.button.place(relx=1, rely=1, x=-25 if self.scrollbar_enabled else -8, y=-8, anchor='se')
            except AttributeError:
                self.create_button()
                self.button.place(relx=1, rely=1, x=-25 if self.scrollbar_enabled else -8, y=-8, anchor='se')

    def create_button(self):
        self.button = ttk.Button(
            self.popup, text=self.button_name, command=self.cont, style=AdaptiveUIConfigs.BUTTON_TYPE
        )
        self.button.bind("<Return>", self.cont)

    def create_notice(self):
        ttk.Label(
            self.popup,
            text=self.notice + "\n",
            font=(Configs.FONT, Configs.FONT_SIZE[1]),
            justify=tk.CENTER,
            background=ColorPalette.bg,
            foreground=ColorPalette.fg,
        ).pack(side='bottom', padx=8 if not self.add_image else 0, pady=30) 

    def update_log(self):
        log_data = self.text.getvalue()
        if log_data != self.last_log_data:  # only update if the log data has changed
            self.wtext.config(state=tk.NORMAL)
            self.wtext.delete(1.0, tk.END)
            self.wtext.insert(tk.END, log_data)
            self.wtext.config(state=tk.DISABLED)
            self.wtext.yview_moveto(1)
            self.last_log_data = log_data  # store the current log data

        self.popup.after(1000, self.update_log)

class UserInterface:
    _dark_mode: bool = LocalSettings.read().dark_mode
    
    def __init__(self, window_name: str, size: tuple[int, int] = None, center: bool = True, resizable: bool = False, icon: str = Images.ICON):
        global excepthook, FaultTolerantTk

        class FaultTolerantTk(tk.Tk):
            @classmethod
            def report_callback_exception(cls, exc: BaseException, val: BaseException, tb):
                self._custom_traceback(exc, val, tb)
                self.error(
                    f"An error has occurred. Please report this to the developer.\n\n{repr(exc)}: {val}",
                    "⚠️ Critical Error!",
                )
        
        excepthook = self._custom_traceback
        
        if size is None:
            size = (400, 200)
        self.orginal_size = size
        self._reset__temp_data()
        
        self._window = self._create_window(window_name, center, size, icon, resizable)
        
        self.set_theme(self._dark_mode)
        self.frame = SharedFrame(self._window)
        self.frame._apack()
        self.style_manager = StyleManager()

        self.socket_server = SocketServer({
            Signals.UPDATE_COLORS: (self._handle_signal_ls, {"selected_colorpalette": None, "dark_mode": None, "bg": None, "fg": None}),
            Signals.INFO_POPUP: (self.info, {"message": ""}),
            Signals.ERROR_OCCURRED: (self._socket_error_detected, {"message": ""})
        }, requires={"version": AdaptiveUIInfo.VERSION})
        self.socket_server.attach_metadata(self._gen_socket_metadata)
        self.socket_client = SocketClient(requires={"version": AdaptiveUIInfo.VERSION})

        self._color_palette_history_window = False
        self.running = False
        
        lsettings = LocalSettings.read()
        ColorPalette.color_schemes["saved"] = {k: tuple(v) for k, v in lsettings.saved_colorpalettes.items()}
        
        settings_colorpalette = lsettings.selected_colorpalette.split(", ")
        try:
            ColorPalette.bg = ColorPalette.color_schemes[settings_colorpalette[0]][settings_colorpalette[1]][0]
        except KeyError: # Color Removed
            settings_colorpalette = ("defaults", ColorPalette._default_selected_color_scheme)
            lsettings.selected_colorpalette = ColorPalette._default_selected_color_scheme
            ColorPalette._selected_color_scheme = ColorPalette._default_selected_color_scheme
            lsettings.write("Color palette not found, reverting to default")
            ColorPalette.bg = ColorPalette.color_schemes[settings_colorpalette[0]][settings_colorpalette[1]][0]
        ColorPalette.fg = ColorPalette.color_schemes[settings_colorpalette[0]][settings_colorpalette[1]][1]
        ColorPalette._selected_color_scheme = settings_colorpalette[1]
        
        self.wait_var = self.frame.wait_var
        self.clear = self.frame.clear
        self.loading = self.frame.loading
    
    def _custom_traceback(self, exc: BaseException, val: BaseException, tb):
        print("Custom traceback called")  # Add this line
        logger.exception(exc)
        Thread(target=lambda: self.socket_client.send(Signals.ERROR_OCCURRED, {"message": f"{repr(exc)}: {val}"})).start()
    
    def _gen_socket_metadata(self) -> dict:
        return {"aui_stats": self._get_raw_stats()}
    
    def _reset__temp_data(self):
        self.__temp_data: dict[str, dict | list[_Info] | bool] = {"binds": {}, "open_info_windows": [], "total_opened_windows": 0, "cp_apply_warning_given": False, "cp_custom_apply_warning_given": False, "cp_not_default_warning_given": False, "geometry_old_size": None}
    
    def _display_info(self, message: str, title: str, extra_info: str = "", wait_var_value: bool = False, grab_input: bool = True, button_name: str = "Continue", global_grab: bool = False, scrollbar_enabled: int = 1, add_image: str = False, markdown: bool = False) -> _Info:
        self._clean_iwindows()
        wait_var = tk.BooleanVar(value=wait_var_value)
        info = _Info(self._window, message, title, extra_info, wait_var=wait_var, grab_input=grab_input, button_name=button_name, global_grab=global_grab, scrollbar_enabled=scrollbar_enabled, add_image=add_image, markdown=markdown)
        self.__temp_data["total_opened_windows"] += 1
        self.__temp_data["open_info_windows"].append(info)
        info.start()
    
    def destroy(self):
        logger.debug("Destroying window...")
        self._window.destroy()

    def quit(self):
        logger.debug("Quitting Tcl interpreter...")
        self._window.quit()
    
    def _handle_signal_ls(self, selected_colorpalette: str, dark_mode: bool, bg: str, fg: str):
        lsettings = LocalSettings.read()
        lsettings.selected_colorpalette = selected_colorpalette
        if dark_mode is not self._dark_mode:
            self.set_theme(dark_mode)
        self.set_color(bg, fg, no_popup=True, no_socket=True, force_apply=True)
    
    def _socket_error_detected(self, message: str):
        self.error(f"An error was detected in another instance of {BuildConfigs.NAME}:\n{message}")
    
    def geometry(self, size: tuple[int, int] | str = None, revert: bool = False):
        """
        Get or set the geometry (size and position) of the window.

        Args:
            size (tuple[int, int] | str, optional): The desired size of the window. 
                It can be specified as a tuple of integers (width, height) or as a string 
                in the format "widthxheight". If set to None, the current geometry is returned. 
                Defaults to None.
            revert (bool, optional): If True, reverts the window size to the previous size. 
                Defaults to False.

        Returns:
            str: The current geometry of the window if size is None.

        Examples:
            # Get the current geometry
            current_geometry = geometry()

            # Set the window size to (800, 600)
            geometry((800, 600))

            # Set the window size to "1024x768"
            geometry("1024x768")

            # Revert the window size to the previous size
            geometry(revert=True)
        """
        current_window_size = self._window.geometry()

        if revert:
            revert_size = self.__temp_data.pop("geometry_old_size", self.orginal_size)
            logger.debug(f"Reverting window size ({current_window_size} -> {revert_size})...")
            self._window.geometry(revert_size)
            return

        if size is None:
            return current_window_size

        logger.debug(f"Setting window size to {size if size else 'auto'}...")
        self.__temp_data["geometry_old_size"] = current_window_size

        if isinstance(size, str):
            self._window.geometry(size)
        else:
            self._window.geometry(f"{size[0]}x{size[1]}")
    
    def bind(self, event: str, function: Callable):
        logger.debug(f"Binding {event=} to function '{function.__name__}'...")
        if self.__temp_data["binds"].get(event, False):
            self.unbind(event)
        self.__temp_data["binds"][event] = (self._window.bind(event, function), function.__name__)

    def unbind(self, event: str):
        logger.debug(f"Unbinding {event=} from function '{self.__temp_data["binds"][event][1]}'...")
        if event not in self.__temp_data["binds"]:
            raise UIUnbindError(f"No such event: {event}")

        self._window.unbind(event, self.__temp_data["binds"][event][0])
        del self.__temp_data["binds"][event]

    def toggle_var(self, var: ToggleVar):
        """
        Toggles the given variable and displays the result in a messagebox.

        Args:
            var (ToggleVar): The variable to be toggled.

        Returns:
            None
        """
        if not isinstance(var, ToggleVar):
            logger.error("Can not toggle this variable (needs to be ToggleVar type)!")
            return

        nvar = var.toggle()
        logger.debug(f"Toggled '{var.name}' to '{nvar}' via Debug Menu")
        self.info(
            f"{var.name}: {var.pp_get()}",
            "DEBUG Menu",
        )

    def randomise_color_palette(self):
        logger.debug("Randomising color palette...")
        ColorPalette.randomise()
        self.set_color(ColorPalette.bg, ColorPalette.fg)
    
    def _test_constant_random_color(self, cooldown: int = 75):
        ColorPalette.randomise()
        self.set_color(ColorPalette.bg, ColorPalette.fg, logging_enabled=False)
        self._window.after(cooldown, self._test_constant_random_color)
    
    def show_color_palette_history(self):
        wait_var = tk.BooleanVar(value=False)
        self._color_palette_history_window = _Info(self._window, "", f"{BuildConfigs.NAME} - Color Palette History", grab_input=False, button_name=None, scrollbar_enabled=0, wait_var=wait_var, show_text_box=False)
        self._color_palette_history_window.start()

    def set_color(self, bg_color: str, fg_color: str, skip_window: bool = False, container = None, logging_enabled: bool = True, force_apply: bool = False, no_popup: bool = False, no_socket: bool = False):
        excluded_widgets = [self.predefined_color_rc] + self._get_all_descendants(self.predefined_color_rc)

        if not self._dark_mode:
            self._dark_mode = True
            self.set_theme(self._dark_mode)

        ColorPalette.bg = bg_color
        ColorPalette.fg = fg_color
        category = "Unknown"

        if not skip_window: # So that it doesnt repeat for every child
            # Check if the color scheme exists in the dictionary
            for category in tuple(ColorPalette.color_schemes.keys()):
                for scheme, colors in ColorPalette.color_schemes[category].items():
                    if colors == (bg_color, fg_color):
                        if ColorPalette._selected_color_scheme == scheme and not force_apply:
                            logger.debug(f"Color scheme '{scheme}' is already selected, skipping...")
                            if not no_popup:
                                self.info("This color scheme is already selected!")
                            return
                        ColorPalette._selected_color_scheme = scheme
                        if not no_popup:
                            lsettings = LocalSettings.read()
                            lsettings.selected_colorpalette = f"{category}, {scheme}"
                            lsettings.write(f"Set selected color palette to {category}, {scheme}")
                            if self.running:
                                Thread(target=lambda: self.socket_client.send(Signals.UPDATE_COLORS, {"selected_colorpalette": lsettings.selected_colorpalette, "dark_mode": self._dark_mode, "bg": bg_color, "fg": fg_color})).start()
                        break
                else:
                    continue  # executed if the loop ended normally (no break)
                break  # executed if 'continue' was skipped (break)
            else:
                ColorPalette._selected_color_scheme = "Custom"
            
            self.style_manager.set_color(bg_color, fg_color)
        
        #if (bg_color, fg_color) != ColorPalette.color_schemes["Default"]:
        #    logger.debug("Disabling Switch Theme")
        #    self.ui_right_click.entryconfig("Switch UI Theme", state="disabled")
        #else:
        #    logger.debug("Enabling Switch Theme")
        #    self.ui_right_click.entryconfig("Switch UI Theme", state="normal")
        
        if container is None:
            container = self._window

        if logging_enabled:
            logger.debug(f"Setting colors of {container} to bg={bg_color}, fg={fg_color}...")

        if not skip_window:
            self._window.configure(background=bg_color)

        if isinstance(container, (FaultTolerantTk, tk.Toplevel)):
            container.configure(background=bg_color)
            if bg_color is not None:
                container.option_add("*Background", bg_color)
            if fg_color is not None:
                container.option_add("*Foreground", fg_color)
        
        if self._color_palette_history_window:
            if not self._color_palette_history_window.popup.winfo_exists():
                self._color_palette_history_window = False
            else:
                new_frame = ttk.Frame(self._color_palette_history_window.popup)
                new_frame.configure(background=bg_color)
                new_frame.pack(fill="both", expand=True)

        for child in container.winfo_children():
            if child in excluded_widgets:
                pass
            elif child.winfo_children():
                # child has children, go through its children
                self.set_color(bg_color, fg_color, True, child, logging_enabled)
            else:
                self._set_child_color(child, bg_color, fg_color)
        
        if skip_window or not self.running:
            return

        is_custom_scheme = ColorPalette._selected_color_scheme == "Custom"
        if not self.__temp_data["cp_custom_apply_warning_given"] and is_custom_scheme and not no_popup:
            self.warning("You are using a Custom ColorPalette!\nThis will not be saved when you close the program.", extra_info="This message will be displayed only once per session.")
            self.__temp_data["cp_custom_apply_warning_given"] = True
        elif not self.__temp_data["cp_not_default_warning_given"] and category != "defaults" and not no_popup:
            self.warning("You are using an Alternative ColorPalette!\nThis may not work well and is still being worked on.", extra_info="This message will be displayed only once per session.")
            self.__temp_data["cp_not_default_warning_given"] = True
        
        if not self.__temp_data["cp_apply_warning_given"] and not is_custom_scheme and not no_popup:
            self.warning("You need to restart the program for the new ColorPalette to fully take effect.", extra_info="This message will be displayed only once per session.")
            self.__temp_data["cp_apply_warning_given"] = True

    def _get_raw_stats(self) -> dict:
        self._clean_iwindows()
        stats = {
            "Version": AdaptiveUIInfo.VERSION,
            "Author": AdaptiveUIInfo.AUTHOR,
            "License": AdaptiveUIInfo.LICENSE,
            "Active Open Windows": len(self.__temp_data['open_info_windows']) + 1,  # account for the main window
            "Total Opened Windows": self.__temp_data['total_opened_windows'] + 1,
            "Active Keybinds": (len(self.__temp_data['binds']), ', '.join(self.__temp_data['binds'].keys())),
            "Parent Window Size": self.geometry(),
            "Window Theme": 'Dark' if self._dark_mode else 'Light',
            "ColorPalette": (ColorPalette.bg, ColorPalette.fg, ColorPalette._selected_color_scheme)
        }
        return stats
    
    def _get_stats(self) -> str:
        raw_stats = self._get_raw_stats()
        stats = f"Version: {raw_stats['Version']}"
        stats += f"\nAuthor: {raw_stats['Author']}"
        stats += f"\nLicense: {raw_stats['License']}"
        stats += f"\n\nActive Open Windows: {raw_stats['Active Open Windows'] + 1}" # account for the info window that will show this
        stats += f"\nTotal Opened Windows: {raw_stats['Total Opened Windows'] + 1}"
        stats += f"\nActive Keybinds: {raw_stats['Active Keybinds'][0]} ({raw_stats['Active Keybinds'][1]})"
        stats += f"\nParent Window Size: {raw_stats['Parent Window Size']}"
        stats += f"\nWindow Theme: {raw_stats['Window Theme']}"
        stats += f"\nColorPalette: {raw_stats['ColorPalette'][0]}, {raw_stats['ColorPalette'][1]} ({raw_stats['ColorPalette'][2]})"
        return stats

    def _save_current_color_palette(self, name: str) -> str:
        lsettings = LocalSettings.read()
        lsettings.saved_colorpalettes[name] = (ColorPalette.bg, ColorPalette.fg)
        lsettings.write("Saved Custom ColorPalette")
        return "Saved ColorPalette to LocalSettings.\nYou can view it in the Predefined ColorPalette Menu."
    
    def _clear_saved_color_palettes(self) -> str:
        lsettings = LocalSettings.read()
        lsettings.saved_colorpalettes = {}
        lsettings.write("Cleared Saved ColorPalettes")
        return "Cleared Saved ColorPalettes."
    
    def mount_ui_rc_menu(self, parent_menu: tk.Menu = None):
        self.ui_right_click = None
        if parent_menu is None:
            self.ui_right_click = tk.Menu(
            self._window, tearoff=0, bg=ColorPalette.bg, fg=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg)
        )
            self.bind("<Button-3>", self._do_popup)
        else:
            self.ui_right_click = tk.Menu(parent_menu, tearoff=0, bg=ColorPalette.bg, fg=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg))
        
        test_rc = tk.Menu(self.ui_right_click, tearoff=0, bg=ColorPalette.bg, fg=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg))
        color_rc = tk.Menu(self.ui_right_click, tearoff=0, bg=ColorPalette.bg, fg=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg))
        custom_color_rc = tk.Menu(self.ui_right_click, tearoff=0, bg=ColorPalette.bg, fg=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg))

        test_rc_commands = [
            ("Perform UI Lockout", self.grab_test),
            SEPARATOR,
            ("View '__temp_data'", lambda: self.info(pformat(self.__temp_data), "AdaptiveUI - __temp_data")),
            ("Reset '__temp_data'", self._reset__temp_data),
            ("Cleanup '__temp_data'", self._clean_iwindows),
            SEPARATOR,
            ("Toggle 'INFO_GRAB_INPUT_ENABLED'", lambda: self.toggle_var(AdaptiveUIConfigs.INFO_GRAB_INPUT_ENABLED)),
            SEPARATOR,
            ("info()", lambda: self.info("This is a test message.", "Test Message")),
            ("error()", lambda: self.error("This is a test error message.", "Test Error")),
            ("warning()", lambda: self.warning("This is a test warning message.", "Test Warning")),
            ("success()", lambda: self.success("This is a test success message.", "Test Success")),
            SEPARATOR,
            ("View Connected Socket Info", lambda: self.info(pformat(self.socket_client.get_server_info()), "AdaptiveUI Socket Info")),
            ("Info Popup over Socket", lambda: self.socket_client.send(Signals.INFO_POPUP, {"message": "Hello, World!"}, False)),
            SEPARATOR,
            (
                "Critical Crash via Menu",
                lambda: test_rc.delete(
                    "DEBUG RC MENU: Critical Crash via Menu"
                ),
            ),
        ]
        color_rc_commands = [
            ("Randomise Color Palette", self.randomise_color_palette),
            ("Enable Fun Color Palette", self._test_constant_random_color),
            ("View ColorPalette History", self.show_color_palette_history)
        ]
        custom_color_rc_commands = [
            ("Set Custom ColorPalette Hex", lambda: self.set_color(self.get_input_string("Set ColorPalette", ColorPalette.bg, "Enter ColorPalette Background Hex"), self.get_input_string("Set ColorPalette", ColorPalette.fg, "Enter ColorPalette Foreground Hex"))),
            ("Save Current ColorPalette", lambda: self.info(self._save_current_color_palette(self.get_input_string("Save Current ColorPalette", info="ColorPalette Name:")), "AdaptiveUI Info")),
            ("Clear Saved ColorPalettes", lambda: self.info(self._clear_saved_color_palettes(), "AdaptiveUI Info")),
        ]
        
        self.predefined_color_rc = tk.Menu(self.ui_right_click, tearoff=0, bg=ColorPalette.bg, fg=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg))

        for scheme_name, color_scheme in ColorPalette.color_schemes.items():
            predefined_scheme_color_rc = tk.Menu(self.ui_right_click, tearoff=0, bg=ColorPalette.bg, fg=ColorPalette.fg, activebackground=darken_color(ColorPalette.bg), activeforeground=lighten_color(ColorPalette.fg))
            for predefined_color in color_scheme:
                color_name = predefined_color
                predefined_scheme_color_rc.add_command(
                    label=predefined_color, 
                    command=lambda color_name=color_name, cs=color_scheme: self.set_color(*cs[color_name]), 
                    background=color_scheme[predefined_color][0], 
                    foreground=color_scheme[predefined_color][1],
                    activebackground=darken_color(color_scheme[predefined_color][0]),
                    activeforeground=lighten_color(color_scheme[predefined_color][1])
                )
            self.predefined_color_rc.add_cascade(label=scheme_name.replace("_", " ").title(), menu=predefined_scheme_color_rc)
        
        set_rc_menu(test_rc, test_rc_commands)
        set_rc_menu(color_rc, color_rc_commands)
        set_rc_menu(custom_color_rc, custom_color_rc_commands)

        self.ui_right_click.add_command(label="View AdaptiveUI Info", command=lambda: self.info(self._get_stats(), "AdaptiveUI Info"))
        # self.ui_right_click.add_command(label="Switch UI Theme", command=self.toggle_theme, state="disabled")        
        self.ui_right_click.add_cascade(label="Predefined ColorPalettes", menu=self.predefined_color_rc)
        self.ui_right_click.add_cascade(label="Custom ColorPalettes", menu=custom_color_rc)
        if AdaptiveUIConfigs.TOOLS_ENABLED:
            self.ui_right_click.add_separator()
            self.ui_right_click.add_cascade(label="Testing Tools", menu=test_rc)
            self.ui_right_click.add_cascade(label="ColorPalette Tools", menu=color_rc)

        if parent_menu is not None:
            parent_menu.add_cascade(
            label="AdaptiveUI Tools", menu=self.ui_right_click
        )
    
    def _do_popup(self, event: tk.Event):
        if self.ui_right_click is None:
            return

        try:
            self.ui_right_click.tk_popup(event.x_root, event.y_root)
        finally:
            self.ui_right_click.grab_release()

    def _set_child_color(self, child: tk.Widget, bg_color: str, fg_color: str):
        if isinstance(child, (tk.Label, tk.Text, tk.Button, tk.Checkbutton, tk.Radiobutton, tk.Listbox)):
            child.config(bg=bg_color, fg=fg_color)
        elif isinstance(child, tk.Menu):
            child.config(bg=bg_color, fg=fg_color, activebackground=darken_color(bg_color), activeforeground=lighten_color(fg_color))
        elif isinstance(child, tk.Canvas):
            child.config(bg=bg_color)
    
    def _get_all_descendants(self, widget: tk.Widget):
        descendants = widget.winfo_children()
        for child in widget.winfo_children():
            descendants.extend(self._get_all_descendants(child))
        return descendants
    
    def set_theme(self, dark: bool = True):
        logger.debug(f"Setting theme to {'dark' if dark else 'light'}...")
        self._dark_mode = dark
        self.__class__._dark_mode = dark # Fix for classmethods
        sv_ttk.set_theme("dark" if dark else "light")
        color_title_bar(self._window, dark)
        for window in self._get_open_iwindows():
            color_title_bar(window.popup, dark)
        self._window.update()
    
    def _get_open_iwindows(self) -> Iterator[_Info]:
        for window in self.__temp_data["open_info_windows"]:
            if window.popup.winfo_exists():
                yield window
            else:
                self.__temp_data["open_info_windows"].remove(window)
    
    def _clean_iwindows(self):
        for window in self._get_open_iwindows():
            if not window.popup.winfo_exists():
                window.popup.destroy()
    
    def get_input_string(self, title: str, placeholder: str = "", info: str = "", button_name: str = "Continue") -> str:
        logger.debug("Displaying input window...")
        top = self._create_window(title, center=True, size=(400, 200), resizable=True, is_toplevel=self._window)
        if info:
            info_label = ttk.Label(top, text=info)
            info_label.pack()
        entry = ttk.Entry(top)
        if placeholder:
            Tools.init_placeholder(entry, placeholder)
        entry.pack(pady=8 if info else 0)
        button = Tools.button(button_name, top.quit, True, top)
        button.pack(pady=0)
        top.mainloop()

        return entry.get()
    
    def toggle_theme(self):
        logger.debug("Toggling theme...")
        self.set_theme(not self._dark_mode)
        logger.debug("Saving theme preference to Local Settings...")
        lsettings = LocalSettings.read()
        lsettings.dark_mode = self._dark_mode
        lsettings.write(f"Toggle theme to {'dark' if self._dark_mode else 'light'}")
    
    def info(self, message: str, title: str = BuildConfigs.NAME, extra_info: str = "", scrollbar_enabled: int = 1, image: str = False):
        if not title == BuildConfigs.NAME:
            title = f"{BuildConfigs.NAME} - {title}"
        logger.debug(f"Displaying info popup window...")
        self._display_info(message, title, extra_info, scrollbar_enabled=scrollbar_enabled, add_image=image)
    
    def warning(self, message: str, title: str = BuildConfigs.NAME, extra_info: str = "", scrollbar_enabled: int = 1, image: str = Images.WARNING):
        self.info(message, title, extra_info, scrollbar_enabled, image)

    def error(self, message: str, title: str = BuildConfigs.NAME, extra_info: str = "", scrollbar_enabled: int = 1, image: str = Images.ERROR):
        self.info(message, title, extra_info, scrollbar_enabled, image)
    
    def success(self, message: str, title: str = BuildConfigs.NAME, extra_info: str = "", scrollbar_enabled: int = 1, image: str = Images.SUCCESS):
        self.info(message, title, extra_info, scrollbar_enabled, image)

    def view_log_window(self, log: StringIO):
        logger.debug(f"Displaying log window...")
        self._display_info(log, f"{BuildConfigs.NAME} - Debug Log", grab_input=False, button_name="Close", scrollbar_enabled=2)

    def grab_test(self, global_mode: bool = False):
        if not global_mode:
            logger.debug("Grabbing all events (event lock)...")
            self._display_info("Event Grab enabled.", "UI Tools - Event Lock", "Inputs are disabled for the parent window and all of its child windows.", button_name="End", add_image=Images.NO_ENTRY)
        else:
            if os.name == "nt":
                self._display_info("This feature is not supported on Windows!", "UI Tools - Display Lockout", button_name="Understood", add_image=Images.NO_ENTRY)
                return
            logger.debug("Grabbing events globally (Display Lockout)...")
            self._display_info("Global Event Grab (Display Lockout) enabled.", "UI Tools - Display Lockout", "Inputs to all windows execpt this one are disabled.", button_name="End", global_grab=True, add_image=Images.NO_ENTRY)

    @classmethod
    def _create_window(
        cls,
        title: str,
        center: bool = False,
        size: tuple[int, int] | str = None,
        icon: str = Images.ICON,
        resizable: bool = False,
        is_toplevel: FaultTolerantTk = False,
    ) -> FaultTolerantTk | tk.Toplevel:
        if size is None:
            size = [400, 200]
        window = tk.Toplevel(is_toplevel) if is_toplevel else FaultTolerantTk()
        window.title(title)
        window.iconphoto(False, tk.PhotoImage(file=icon))
        window.attributes("-alpha", 0.95)
        dpi_fix()
        if center:
            Tools.center_window(window, size, False)
        None if resizable else window.resizable(0, 0)
        if isinstance(size, str):
            window.geometry(size)
        else:
            window.geometry(f"{size[0]}x{size[1]}")
        
        if cls._dark_mode:
            color_title_bar(window)
        else:
            color_title_bar(window, False)
        return window

    def run(self):
        self.set_color(ColorPalette.bg, ColorPalette.fg, force_apply=True)
        self.running = True
        self._window.mainloop()
