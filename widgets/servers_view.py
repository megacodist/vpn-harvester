#
#
#

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, TYPE_CHECKING

import tksheet

# Import the data model this view will be responsible for displaying
from utils.vpn_gate import VpnGateServer

if TYPE_CHECKING:
    # This is for static type checking, helps your editor with hints.
    # The `_` is a common convention for a translation function.
    _: Callable[[str], str] = lambda a: a


class ServersView(tksheet.Sheet):
    """
    A tksheet-based widget for displaying and interacting with a list of
    `VpnGateServer` objects.
    """
    def __init__(
            self,
            master: tk.Misc,
            double_clicked_cb: Callable[[str], None] | None = None,
            **kwargs
            ) -> None:
        super().__init__(master, **kwargs)
        
        # --- Define Headers for VpnGateServer Data ---
        self.headers([
            _('Name'), _('Country'), _('IP Address'), _('Ping'),
            _('Speed (Mbps)'), _('Score'), _('Sessions')
        ])

        # Default column widths, can be overridden by kwargs
        self.column_width(0, 150) # Name
        self.column_width(1, 120) # Country
        self.column_width(2, 100) # IP
        self.column_width(3, 60)  # Ping
        self.column_width(4, 100) # Speed
        self.column_width(5, 100) # Score
        self.column_width(6, 70)  # Sessions
        
        # --- Internal State and Callbacks ---
        self._mpNameRow = dict[str, int]()
        self._cbDoubleClicked = double_clicked_cb
        
        # --- Bindings ---
        self.enable_bindings(
            'single_select', 'drag_select', 'row_select', 'column_select',
            'ctrl_click_select', 'up', 'down', 'left', 'right'
        )
        # Custom binding to detect when a row is selected or double-clicked
        self.extra_bindings([
            ("begin_edit_cell", self._on_begin_edit_cell),
            ('row_select_enable', self._on_begin_edit_cell),
        ])
        
        # --- Visual Tags for Row Status ---
        self.tag_configure("success", bg="#dff0d8") # Light green
        self.tag_configure("failure", bg="#f2dede") # Light red
        self.tag_configure("testing", bg="#d9edf7") # Light blue

    def _on_begin_edit_cell(self, event: tksheet.EventDataDict) -> None:
        """Internal handler to fire the double-click callback."""
        if self._cbDoubleClicked:
            # Get the name of the server in the selected row
            selected_rows = self.get_selected_rows(get_cells=False)
            if selected_rows:
                server_name = self.get_cell_data(list(selected_rows)[0], 0)
                # Fire the callback with the server name
                self.after(10, lambda: self._cbDoubleClicked(server_name))

    def get_selected_names(self) -> tuple[str, ...]:
        """Gets the unique names of the servers in all selected rows."""
        # Using a set to ensure names are unique, even if cells are multi-selected
        selected_rows_indices = {cell[0] for cell in self.get_selected_cells()}
        return tuple(self.get_cell_data(r, 0) for r in sorted(selected_rows_indices))

    def clear(self) -> None:
        """Clears all server entries from the view."""
        # Clearing the data and our internal name-to-row mapping
        super().set_sheet_data(data=[[]], reset_col_positions=False, reset_row_positions=False)
        self._mpNameRow.clear()
        # Redraw to ensure the view is empty
        self.refresh()

    def _get_row_data_from_server(self, server: VpnGateServer) -> list:
        """Helper to format a VpnGateServer object into a list for display."""
        latest_stat = None
        if server.stats:
            # Find the most recent stat entry
            latest_stat_dt = max(server.stats.keys())
            latest_stat = server.stats[latest_stat_dt]

        return [
            server.config.name,
            server.config.country_name,
            str(server.config.ip) if server.config.ip else "N/A",
            latest_stat.ping if latest_stat else "N/A",
            f"{(latest_stat.speed / 1_000_000):.2f}" if latest_stat else "N/A",
            latest_stat.score if latest_stat else "N/A",
            latest_stat.num_vpn_sessions if latest_stat else "N/A",
        ]

    def populate(self, servers: Iterable[VpnGateServer]) -> None:
        """Clears the view and populates it with a new list of servers."""
        self.clear()
        
        data_to_load = []
        for idx, server in enumerate(servers):
            data_to_load.append(self._get_row_data_from_server(server))
            self._mpNameRow[server.config.name] = idx
        
        if data_to_load:
            self.set_sheet_data(data_to_load, reset_col_positions=False, reset_row_positions=False)
        self.refresh()

    def change_server(self, server_name: str, new_server: VpnGateServer) -> None:
        """Updates an existing server's data in the view."""
        if server_name not in self._mpNameRow:
            return
            
        row_idx = self._mpNameRow[server_name]
        new_data = self._get_row_data_from_server(new_server)
        self.set_row_data(row_idx, new_data)
        
        # If the name changed, update the mapping
        if server_name != new_server.config.name:
            del self._mpNameRow[server_name]
            self._mpNameRow[new_server.config.name] = row_idx
        
        self.refresh(row_idx, 0)

    def append_server(self, server: VpnGateServer) -> None:
        """Adds a single new server to the end of the view."""
        new_row_data = self._get_row_data_from_server(server)
        self.insert_row(new_row_data)
        new_row_idx = self.get_total_rows() - 1
        self._mpNameRow[server.config.name] = new_row_idx
        self.refresh()
        
    def delete_server(self, server_name: str) -> None:
        """Deletes a server from the view by its name."""
        if server_name not in self._mpNameRow:
            return
            
        row_idx = self._mpNameRow[server_name]
        self.delete_row(row_idx)
        del self._mpNameRow[server_name]
        
        # After deletion, all subsequent row indices have shifted. Rebuild map.
        # This is a simple but effective way to keep the map consistent.
        self._rebuild_name_map()
        self.refresh()

    def _rebuild_name_map(self) -> None:
        """Internal helper to resync the name-to-row mapping."""
        self._mpNameRow.clear()
        all_data = self.get_sheet_data()
        for idx, row_data in enumerate(all_data):
            if row_data:
                self._mpNameRow[row_data[0]] = idx

    def set_row_status_success(self, server_name: str):
        """Applies 'success' styling to the row for the given server."""
        if server_name in self._mpNameRow:
            row_idx = self._mpNameRow[server_name]
            self.dehighlight_rows(row_idx) # Clear other highlights
            self.highlight_rows(row_idx, bg=self.tag_cget("success", "bg"), fg="black")

    def set_row_status_failure(self, server_name: str):
        """Applies 'failure' styling to the row for the given server."""
        if server_name in self._mpNameRow:
            row_idx = self._mpNameRow[server_name]
            self.dehighlight_rows(row_idx)
            self.highlight_rows(row_idx, bg=self.tag_cget("failure", "bg"), fg="black")

    def set_row_status_testing(self, server_name: str):
        """Applies 'testing' styling to the row for the given server."""
        if server_name in self._mpNameRow:
            row_idx = self._mpNameRow[server_name]
            self.dehighlight_rows(row_idx)
            self.highlight_rows(row_idx, bg=self.tag_cget("testing", "bg"), fg="black")

    def clear_row_status(self, server_name: str):
        """Removes all custom styling from the row."""
        if server_name in self._mpNameRow:
            self.dehighlight_rows(self._mpName_row[server_name])
