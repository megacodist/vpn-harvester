#
# 
#

import tkinter as tk
from tkinter import ttk
from tkinter import filedialog


class VpnHarvesterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("VPN Gate Connection Tester")
        self.geometry("1000x800")

        # --- State Variables ---
        self.vpn_data: Optional[VpnGateData] = None
        self.temp_ovpn_dir = tempfile.TemporaryDirectory()
        self.openvpn_exe_path = Path(r"C:\Program Files\OpenVPN\bin\openvpn.exe") # Default
        self.check_result_queue = queue.Queue()
        self.active_threads = []

        # --- UI Setup ---
        self._initGui()
        self._initToolbar()
        self._create_panes()
        self._create_widgets()
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
            label="Load VPN List (.csv)...",
            command=self.load_csv_from_file)
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
            command=self.load_csv_from_file)
        self._btn_load.pack(side=tk.LEFT, padx=2, pady=2)
        #
        self._btn_check = ttk.Button(
            self._toolbar,
            text="Check Selected",
            command=self.check_selected)
        self._btn_check.pack(side=tk.LEFT, padx=2, pady=2)

    def _create_panes(self):
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

    def _create_widgets(self):
        # --- Top Pane: Server List Treeview ---
        self.tree = ttk.Treeview(
            self._lfrm_servers,
            columns=("HostName", "Country", "Ping", "Speed", "Score"),
            show="headings",
        )
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Define headings
        self.tree.heading("HostName", text="HostName")
        self.tree.heading("Country", text="Country")
        self.tree.heading("Ping", text="Ping (ms)")
        self.tree.heading("Speed", text="Speed (Mbps)")
        self.tree.heading("Score", text="Score")
        
        # Configure columns
        self.tree.column("HostName", width=150)
        self.tree.column("Country", width=100)
        self.tree.column("Ping", width=60, anchor=tk.E)
        self.tree.column("Speed", width=100, anchor=tk.E)
        self.tree.column("Score", width=100, anchor=tk.E)
        
        # Add a scrollbar
        scrollbar = ttk.Scrollbar(self.tree, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.tree.bind("<<TreeviewSelect>>", self.on_server_select)

        # Configure tags for coloring rows
        self.tree.tag_configure("success", background="#dff0d8") # Light green
        self.tree.tag_configure("failure", background="#f2dede") # Light red

        # --- Bottom Right Pane: Log Viewer ---
        self.log_text = tk.Text(self._lfrm_tests, wrap=tk.WORD, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        log_scrollbar = ttk.Scrollbar(self.log_text, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # --- Bottom Left Pane: Details ---
        self.details_frame = ttk.Frame(self._lfrm_stats, padding=10)
        self.details_frame.pack(fill=tk.BOTH, expand=True)
        self.detail_labels = {}
        for i, label_text in enumerate(["IP Address:", "Uptime:", "Operator:", "Sessions:"]):
            ttk.Label(self.details_frame, text=label_text).grid(row=i, column=0, sticky=tk.W, pady=2)
            value_label = ttk.Label(self.details_frame, text="N/A")
            value_label.grid(row=i, column=1, sticky=tk.W, padx=5)
            self.detail_labels[label_text] = value_label

    # --- GUI Actions ---
    
    def load_csv_from_file(self):
        filepath = filedialog.askopenfilename(
            title="Select VPN Gate CSV File",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
        )
        if not filepath:
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                csv_text = f.read()
            self.vpn_data = parse_vpn_gate_csv(csv_text)
            self.populate_treeview()
        except Exception as e:
            messagebox.showerror("Error Loading File", f"Could not load or parse the file:\n{e}")

    def set_openvpn_path(self):
        filepath = filedialog.askopenfilename(
            title="Select openvpn.exe",
            filetypes=[("Executable Files", "*.exe"), ("All Files", "*.*")],
        )
        if filepath:
            self.openvpn_exe_path = Path(filepath)
            messagebox.showinfo("Path Set", f"OpenVPN executable path set to:\n{self.openvpn_exe_path}")

    def populate_treeview(self):
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)

        if not self.vpn_data:
            return
            
        # Get column indices for display
        try:
            h = self.vpn_data.header
            idx = {
                "HostName": h.index("HostName"), "Country": h.index("CountryLong"),
                "Ping": h.index("Ping"), "Speed": h.index("Speed"), "Score": h.index("Score"),
            }
        except ValueError:
            messagebox.showerror("Format Error", "CSV header is missing required columns.")
            return

        for i, row in enumerate(self.vpn_data.rows):
            try:
                # Format for display
                speed_mbps = f"{int(row[idx['Speed']]) / 1_000_000:.2f}"
                values_to_display = (
                    row[idx["HostName"]], row[idx["Country"]], row[idx["Ping"]],
                    speed_mbps, row[idx["Score"]],
                )
                # The 'itemid' (iid) is how we'll uniquely identify this row later
                self.tree.insert("", tk.END, iid=row[idx["HostName"]], values=values_to_display)
            except (ValueError, IndexError):
                continue # Skip rows that can't be parsed

    def on_server_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return
        
        selected_iid = selected_items[0]
        
        # Find the full data row corresponding to the selected item
        if not self.vpn_data: return
        h, rows = self.vpn_data.header, self.vpn_data.rows
        host_name_idx = h.index("HostName")
        
        data_row = next((row for row in rows if row[host_name_idx] == selected_iid), None)
        
        if data_row:
            # Update detail labels
            self.detail_labels["IP Address:"].config(text=data_row[h.index("IP")])
            uptime_ms = int(data_row[h.index("Uptime")])
            uptime_str = f"{uptime_ms / (1000*60*60):.2f} hours"
            self.detail_labels["Uptime:"].config(text=uptime_str)
            self.detail_labels["Operator:"].config(text=data_row[h.index("Operator")])
            self.detail_labels["Sessions:"].config(text=data_row[h.index("NumVpnSessions")])

    def check_selected(self):
        if not self.openvpn_exe_path.is_file():
            messagebox.showerror("Error", f"openvpn.exe not found at:\n{self.openvpn_exe_path}")
            return
            
        selected_items = self.tree.selection()
        if not selected_items:
            messagebox.showwarning("No Selection", "Please select a server from the list to test.")
            return

        selected_iid = selected_items[0]

        # Find the config data for the selected server
        h, rows = self.vpn_data.header, self.vpn_data.rows
        host_name_idx = h.index("HostName")
        config_idx = h.index("OpenVPN_ConfigData_Base64")
        
        data_row = next((row for row in rows if row[host_name_idx] == selected_iid), None)

        if data_row:
            try:
                # Decode Base64 and save to a temporary file
                config_data = base64.b64decode(data_row[config_idx]).decode("utf-8")
                temp_path = Path(self.temp_ovpn_dir.name) / f"{selected_iid}.ovpn"
                temp_path.write_text(config_data)

                # Clear previous log
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete("1.0", tk.END)
                self.log_text.insert("1.0", f"Starting connection test for {selected_iid}...\n")
                self.log_text.config(state=tk.DISABLED)

                # Run the check in a separate thread to avoid freezing the GUI
                thread = threading.Thread(
                    target=check_ovpn,
                    args=(temp_path, selected_iid, self.openvpn_exe_path, self.check_result_queue),
                    daemon=True,
                )
                self.active_threads.append(thread)
                thread.start()

            except Exception as e:
                messagebox.showerror("Error", f"Could not prepare or start the test:\n{e}")

    def process_queue(self):
        """Process results from the worker threads."""
        try:
            while True:
                result = self.check_result_queue.get_nowait()
                
                # Update the log view
                self.log_text.config(state=tk.NORMAL)
                self.log_text.delete("1.0", tk.END)
                self.log_text.insert("1.0", result.log)
                self.log_text.config(state=tk.DISABLED)

                # Update the treeview row color
                tag = "success" if result.success else "failure"
                if self.tree.exists(result.host_name):
                    self.tree.item(result.host_name, tags=(tag,))

        except queue.Empty:
            # Check again later
            self.after(100, self.process_queue)

    def _onWinClosing(self):
        # Clean up temporary directory
        self.temp_ovpn_dir.cleanup()
        self.destroy()
