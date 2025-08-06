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



class VpnHarvesterApp(tk.Tk):
    def __init__(self):
        # Creating the window...
        super().__init__()
        self.title("VPN Gate Connection Tester")
        self.geometry("1000x800")
        # Instantiating variables...
        self.active_threads = []
        # Initializing the GUI...
        self._initGui()
        self._initToolbar()
        self._initPanes()
        self._initServersVw()
        self._initStatsVw()
        self._initTestsVw()
        # Bindings & events...
        self.protocol("WM_DELETE_WINDOW", self._onWinClosing)
        # Start the queue checker
        self.after(100, self.process_queue)
    
    def _initGui(self) -> None:
        self._frm_container = ttk.Frame(self)
        self._frm_container.pack(expand=True, fill='both')
        #
        self._menubar = tk.Menu(self._frm_container)
        self.config(menu=self._menubar)
        # File Menu
        self._menu_file = tk.Menu(self._menubar, tearoff=0)
        self._menu_file.add_command(
            label="Load VPN List from File...",
            command=self._loadCsvFromFile)
        self._menu_file.add_command(
            label="Set OpenVPN Path...",
            command=self.set_openvpn_path)
        self._menu_file.add_separator()
        self._menu_file.add_command(label="Exit", command=self.quit)
        self._menubar.add_cascade(label="File", menu=self._menu_file)
        # Tools Menu
        self._menu_tools = tk.Menu(self._menubar, tearoff=0)
        self._menu_tools.add_command(
            label="Check Selected Server",
            command=self.check_selected)
        self._menubar.add_cascade(label="Tools", menu=self._menu_tools)
    
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
            command=self.check_selected)
        self._btn_check.pack(side=tk.LEFT, padx=2, pady=2)

    def _initPanes(self):
        # Main vertical pane (top vs bottom)
        self._pdw_ver = ttk.PanedWindow(
            self._frm_container,
            orient=tk.VERTICAL)
        self._pdw_ver.pack(fill=tk.BOTH, expand=True)
        # Bottom horizontal pane (left vs right)
        self._pdw_hor = ttk.PanedWindow(
            self._frm_container,
            orient=tk.HORIZONTAL)
        # Frames for content
        self._lfrm_servers = ttk.Labelframe(
            self._pdw_ver,
            text="VPN Gate Servers")
        self._lfrm_stats = ttk.Labelframe(
            self._pdw_hor,
            text="Owner Statistics")
        self._lfrm_tests = ttk.Labelframe(
            self._pdw_hor,
            text="User Tests")
        #
        self._pdw_ver.add(self._lfrm_servers, weight=3) # Top pane gets more space
        self._pdw_ver.add(self._pdw_hor, weight=2)
        self._pdw_hor.add(self._lfrm_stats, weight=1)
        self._pdw_hor.add(self._lfrm_tests, weight=1)

    def _initServersVw(self):
        pass

    def _initStatsVw(self):
        pass

    def _initTestsVw(self):
        pass

    def _loadCsvFromFile(self):
        pass
