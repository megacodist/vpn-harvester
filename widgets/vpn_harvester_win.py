#
# 
#

from dataclasses import dataclass
from pathlib import Path
import tkinter as tk
from tkinter import ttk


@dataclass
class VpnGateSettings:
    openvpn_exe_path: Path = Path(r"C:\Program Files\OpenVPN\bin\openvpn.exe")
    ovpn_dir: Path = Path("ovpn_files")


class VpnHarvesterWin(tk.Tk):
    def __init__(self):
        # Creating the window...
        super().__init__()
        self.title("VPN Gate Connection Tester")
        self.geometry("1000x800")
        # Instantiating variables...
        self.active_threads = []
        # Initializing the GUI...
        self._frm_container = ttk.Frame(self)
        self._frm_container.pack(expand=True, fill='both', padx=5, pady=5)
        self._initMenubar()
        self._initToolbar()
        self._initPanes()
        self._initServersVw()
        self._initStatsVw()
        self._initTestsVw()
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
        pdw_main_hor = ttk.PanedWindow(
            self._frm_container,
            orient=tk.HORIZONTAL)
        pdw_main_hor.pack(fill=tk.BOTH, expand=True)
        # 2. Creating the vertical PanedWindow for the left side (top vs.
        # bottom)...
        pdw_left_ver = ttk.PanedWindow(
            pdw_main_hor,
            orient=tk.VERTICAL)
        # 3. Creating the final horizontal PanedWindow for the bottom-left
        # area...
        pdw_btm_hor = ttk.PanedWindow(
            pdw_left_ver,
            orient=tk.HORIZONTAL)
        # 4. Creating the actual Labelframe widgets that will act as the
        # panes...
        self._lfrm_servers = ttk.Labelframe(
            pdw_left_ver,
            text="VPN Gate Servers")
        self._lfrm_stats = ttk.Labelframe(
            pdw_btm_hor,
            text="Owner Statistics")
        self._lfrm_tests = ttk.Labelframe(
            pdw_btm_hor,
            text="User Tests")
        self._lfrm_msgs = ttk.Labelframe(
            pdw_main_hor,
            text="Message")
        # 5. Adding the panes to their respective containers from the
        # inside out...
        # 5.a. Adding the stats and tests panes to the bottom-most
        # container...
        pdw_btm_hor.add(self._lfrm_stats, weight=1)
        pdw_btm_hor.add(self._lfrm_tests, weight=1)
        # 5.b. Add the servers pane (top) and the bottom container to the
        # left-side container...
        pdw_left_ver.add(self._lfrm_servers, weight=3) # Give more vertical space
        pdw_left_ver.add(pdw_btm_hor, weight=1)
        # 5c. Finally, adding the entire left-side container and the right
        # message box to the main container...
        pdw_main_hor.add(pdw_left_ver, weight=2) # Give more horizontal space
        pdw_main_hor.add(self._lfrm_msgs, weight=1)

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

    def _onWinClosing(self) -> None:
        pass
