# servers_view.py

import logging
from typing import Callable, Iterable, Optional, Tuple, TYPE_CHECKING

import tksheet

from utils.vpn_gate import VpnGateServer

if TYPE_CHECKING:
    # This is for static type checking.
    # The `_` is a common convention for a translation function.
    _: Callable[[str], str] = lambda a: a
_: Callable[[str], str] = lambda a: a


class ServersView(tksheet.Sheet):
    """
    It's a matrix display of VPNs. Every VPN occupies one row.
    Columns are attributes of the `config` property.
    """
    def __init__(self, master, **kwargs) -> None:
        super().__init__(master, **kwargs)
        # Define Headers
        self.headers([
            _('Name'), _('Country Code'), _('Country Name'), _('IP Address'),
            _('Log Type'), _('Operator'), _('Message')])
        # Attributes
        self._mpNameRow = dict[str, int]()
        self._on_selection_changed_cb: Callable[[str | None], None] | None \
            = None
        # Set necessary user interaces
        self.enable_bindings('single_select', 'row_select', 'next', 'prior',
            'up', 'down', 'copy', 'column_width_resize',
            'double_click_column_resize')
        # Set bindings
        self.extra_bindings("row_select", self._on_row_select)
        self.extra_bindings("deselect", self._on_deselect)
        self.extra_bindings("copy", self._on_copy)

    def get_selection_cb(self) -> Callable[[str | None], None] | None:
        """Returns the current selection change callback function."""
        return self._on_selection_changed_cb

    def set_selection_cb(self, cb: Callable[[str | None], None] | None) -> None:
        """
        Sets the callback function to be fired when the selection changes.
        - Called with server name (`str`) on selection.
        - Called with `None` on deselection.
        """
        self._on_selection_changed_cb = cb

    def get_cols_width(self) -> Tuple[int, int, int, int, int, int, int]:
        """Returns a 7-tuple consisting of all column widths."""
        # The tksheet method returns a list of floats, so we cast to int and tuple
        widths = self.get_column_widths()
        return tuple(int(w) for w in widths) # type: ignore

    def set_cols_width(
            self,
            widths: Tuple[int, int, int, int, int, int, int],
            ) -> None:
        """
        Sets the width of all 7 columns from a tuple. Ignores extra values.
        Raises `IndexError` if there is no enough integers.
        """
        try:
            for i, width in enumerate(widths):
                self.column_width(column=i, width=width)
        except IndexError as err:
            err.args = ("No enough integers to set columns of ServersView",)
            # Re-raise the modified exception with the original traceback
            raise IndexError from err

    def _on_row_select(self, event: tksheet.EventDataDict) -> None:
        """Handler for the 'row_select' event from tksheet."""
        if self._on_selection_changed_cb is None:
            return
        try:
            server_name: str = self.get_cell_data(event['row'], 0)
            if server_name:
                self._on_selection_changed_cb(server_name)
        except Exception:
            pass

    def _on_deselect(self, _: tksheet.EventDataDict) -> None:
        """Handler for the 'deselect' event from tksheet."""
        if self._on_selection_changed_cb is None:
            return
        self._on_selection_changed_cb(None)

    def _on_copy(self, _: tksheet.EventDataDict) -> None:
        """
        Handler for the 'copy' event.
        Creates a comma-separated string of the selected server's values
        and places it on the clipboard.
        """
        # Get all currently selected rows
        selected_rows = self.get_selected_rows()
        # Proceed only if a single row is selected
        if len(selected_rows) == 1:
            row_index = list(selected_rows)[0]
            if not isinstance(row_index, int):
                logging.error(
                    "Failed to copy a server. Expected an index but got %s",
                    row_index)
                return
            # Retrieve all data from that row
            row_data = self.get_row_data(row_index)
            # Convert all data points to strings and join them with a comma
            comma_separated_string = ",".join(map(str, row_data))
            # Overwrite the system clipboard with our custom string
            self.clipboard_clear()
            self.clipboard_append(comma_separated_string)

    def clear_view(self) -> None:
        """Removes all servers from the view."""
        if self.get_total_rows() > 0:
            self.set_sheet_data(data=[[]])
        self._mpNameRow.clear()
        self.refresh()

    def _get_row_data_from_server(self, server: VpnGateServer) -> list[str]:
        config = server.config
        return [
            config.name, config.country_code, config.country_name,
            str(config.ip) if config.ip else "N/A",
            config.log_type, config.operator_name, config.operator_message,]

    def populate(self, servers: Iterable[VpnGateServer]) -> None:
        """Populates the view with the provided servers."""
        self.clear_view()
        data_to_load = []
        for idx, server in enumerate(servers):
            data_to_load.append(self._get_row_data_from_server(server))
            self._mpNameRow[server.config.name] = idx
        if data_to_load:
            self.set_sheet_data(data_to_load)
        self.refresh()

    def add_server(self, server: VpnGateServer) -> None:
        """Adds this server to the end of the view."""
        new_row_data = self._get_row_data_from_server(server)
        self.insert_row(new_row_data)
        new_row_idx = self.get_total_rows() - 1
        self._mpNameRow[server.config.name] = new_row_idx
        self.refresh()
