#
# 
#

from dataclasses import dataclass
import logging
from pathlib import Path
import tkinter as tk
from tkinter import ttk

from utils.settings import VpnGateAppSettings


@dataclass
class VpnGateSettings:
    openvpn_exe_path: Path = Path(r"C:\Program Files\OpenVPN\bin\openvpn.exe")
    ovpn_dir: Path = Path("ovpn_files")


class VpnHarvesterWin(tk.Tk):
    def __init__(self, settings: VpnGateAppSettings) -> None:
        # Creating the window...
        super().__init__()
        self.title("VPN Gate Connection Tester")
        self.geometry(f"{settings.win_width}x{settings.win_height}+"
            f"{settings.win_x}+{settings.win_y}")
        # Attributes...
        self._settings = settings
        # Initializing the GUI...
        self._frm_container = ttk.Frame(self)
        self._frm_container.pack(expand=True, fill='both', padx=5, pady=5)
        self._pndw_mainHorz: ttk.PanedWindow
        """
        The horizontal `PanedWindow` which splits the window into `pndw_l`
        and `pndw_r` sections.
        """
        self._pndw_leftVert: ttk.PanedWindow
        """
        The vertical `PanedWindow` for the `pndw_l`, splitting it
        into `pndw_lt` and `pndw_lb` sections.
        """
        self._pndw_btmLeftHorz: ttk.PanedWindow
        """
        The horizontal `PanedWindow` for the `pndw_lb` section,
        splitting it into `pndw_lbl` and `pndw_lbr` sections.
        """
        self._initMenubar()
        self._initToolbar()
        self._initPanes()
        self._initServersVw()
        self._initStatsVw()
        self._initTestsVw()
        #
        self.update()
        self._pndw_mainHorz.sashpos(0, self._settings.pndw_main_horz)
        self.update_idletasks()
        self._pndw_leftVert.sashpos(0, self._settings.pndw_left_vert)
        self.update_idletasks()
        self._pndw_btmLeftHorz.sashpos(0, self._settings.pndw_btm_left_horz)
        self.update_idletasks()
        # Bindings & events...
        self.protocol("WM_DELETE_WINDOW", self._onWinClosing)
    
    def _initMenubar(self) -> None:
        #
        self._menubar = tk.Menu(self._frm_container)
        self.config(menu=self._menubar)
        # File Menu
        self._menu_app = tk.Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(
            label='App',
            menu=self._menu_app)
        self._menu_app.add_command(
            label="Setting...",
            command=self._showSettingsDlg)
        self._menu_app.add_separator()
        self._menu_app.add_command(label="Exit", command=self.quit)
        # Tools Menu
        self._menu_tools = tk.Menu(self._menubar, tearoff=0)
        self._menubar.add_cascade(label="Tools", menu=self._menu_tools)
        self._menu_tools.add_command(
            label="Load VPN Gate Servers from File...",
            command=self._loadCsvFromFile)
        self._menu_tools.add_command(
            label="Load VPN Gate Servers from URL...",
            command=self._loadCsvFromUrl)
        self._menu_tools.add_command(
            label="Check Selected Server...",
            command=self._checkServer)
    
    def _initToolbar(self):
        self._toolbar = ttk.Frame(
            self._frm_container,
            relief=tk.RAISED,
            padding=2)
        self._toolbar.pack(side=tk.TOP, fill=tk.X)
        # Example with text buttons; icons can be added with Pillow
        self._btn_load = ttk.Button(
            self._toolbar,
            text="Load CSV",
            command=self._loadCsvFromFile)
        self._btn_load.pack(side=tk.LEFT, padx=2, pady=2)
        #
        self._btn_check = ttk.Button(
            self._toolbar,
            text="Check Selected",
            command=self._checkServer)
        self._btn_check.pack(side=tk.LEFT, padx=2, pady=2)

    def _initPanes(self):
        # 1. Creating the top-level horizontal PanedWindow (left vs. right)...
        self._pndw_mainHorz = ttk.PanedWindow(
            self._frm_container,
            orient=tk.HORIZONTAL)
        self._pndw_mainHorz.pack(fill=tk.BOTH, expand=True)
        # 2. Creating the vertical PanedWindow for the left side (top vs.
        # bottom)...
        self._pndw_leftVert = ttk.PanedWindow(
            self._pndw_mainHorz,
            orient=tk.VERTICAL)
        # 3. Creating the final horizontal PanedWindow for the bottom-left
        # area...
        self._pndw_btmLeftHorz = ttk.PanedWindow(
            self._pndw_leftVert,
            orient=tk.HORIZONTAL)
        # 4. Creating the actual Labelframe widgets that will act as the
        # panes...
        self._lfrm_servers = ttk.Labelframe(
            self._pndw_leftVert,
            text="VPN Gate Servers")
        self._lfrm_stats = ttk.Labelframe(
            self._pndw_btmLeftHorz,
            text="Owner Statistics")
        self._lfrm_tests = ttk.Labelframe(
            self._pndw_btmLeftHorz,
            text="User Tests")
        self._lfrm_msgs = ttk.Labelframe(
            self._pndw_mainHorz,
            text="Message")
        # 5. Adding the panes to their respective containers from the
        # inside out...
        # 5.a. Adding the stats and tests panes to the bottom-most
        # container...
        self._pndw_btmLeftHorz.add(self._lfrm_stats, weight=1)
        self._pndw_btmLeftHorz.add(self._lfrm_tests, weight=1)
        # 5.b. Add the servers pane (top) and the bottom container to the
        # left-side container...
        self._pndw_leftVert.add(self._lfrm_servers, weight=3) # Give more vertical space
        self._pndw_leftVert.add(self._pndw_btmLeftHorz, weight=1)
        # 5c. Finally, adding the entire left-side container and the right
        # message box to the main container...
        self._pndw_mainHorz.add(self._pndw_leftVert, weight=2) # Give more horizontal space
        self._pndw_mainHorz.add(self._lfrm_msgs, weight=1)

    def _initServersVw(self) -> None:
        pass

    def _initStatsVw(self) -> None:
        pass

    def _initTestsVw(self) -> None:
        pass

    def _showSettingsDlg(self) -> None:
        pass

    def _loadCsvFromFile(self) -> None:
        pass
    
    def _loadCsvFromUrl(self) -> None:
        pass

    def _checkServer(self) -> None:
        pass

    def _saveGeometry(self) -> None:
        """Saves the geometry of the window to the app settings object."""
        import re
        w_h_x_y = self.winfo_geometry()
        GEOMETRY_REGEX = r"""
            (?P<width>\d+)    # The width of the window
            x(?P<height>\d+)  # The height of the window
            \+(?P<x>\d+)      # The x-coordinate of the window
            \+(?P<y>\d+)      # The y-coordinate of the window"""
        match = re.search(
            GEOMETRY_REGEX,
            w_h_x_y,
            re.VERBOSE)
        if match:
            self._settings.win_width = int(match.group('width'))
            self._settings.win_height = int(match.group('height'))
            self._settings.win_x = int(match.group('x'))
            self._settings.win_y = int(match.group('y'))
        else:
            logging.error(
                'Cannot get the geometry of the window.',
                stack_info=True)

    def _onWinClosing(self) -> None:
        self._saveGeometry()
        #
        self._settings.pndw_main_horz = self._pndw_mainHorz.sashpos(0)
        self._settings.pndw_left_vert = self._pndw_leftVert.sashpos(0)
        self._settings.pndw_btm_left_horz = self._pndw_btmLeftHorz.sashpos(0)
        #
        self.destroy()
