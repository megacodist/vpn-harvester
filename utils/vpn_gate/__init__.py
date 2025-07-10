import csv
from dataclasses import dataclass
from datetime import datetime
import html
from io import StringIO
from pathlib import Path
import sqlite3
from typing import Iterator, Optional, Protocol


@dataclass
class VpnGateData:
    """
    A container for VPN Gate CSV data, separating headers from data rows.
    This class is used to encapsulate the parsed CSV data from VPN Gate.
    Attributes:
        headers (tuple[str, ...]): The header row of the CSV.
        rows (list[tuple[str, ...]]): The data rows of the CSV.
    """
    header: tuple[str, ...]
    rows: list[tuple[str, ...]]


class Ovpn:
    def __init__(
            self,
            hostName: str,
            ip: str,
            udpPort: int | None,
            tcpPort: int | None,
            ovcUrl: str,
            downloadedAt: datetime,
            ) -> None:
        self.hostName = hostName
        self.ip = ip
        self.udpPort = udpPort
        self.tcpPort = tcpPort
        self.ovcUrl = ovcUrl
        self.downloadedAt = downloadedAt


class IVpnGateableDb(Protocol):
    def connect(self, path: Path) -> None: ...
    def select(self, hostName: str) -> Optional[Ovpn]: ...
    def update(self, ovpn: Ovpn) -> None: ...
    def insert(self, ovpn: Ovpn) -> None: ...
    def close(self) -> None: ...


class SqliteDb(IVpnGateableDb): 
    def __init__(self):
        self._conn: sqlite3.Connection | None = None

    def connect(self, path: Path) -> None:
        self._conn = sqlite3.connect(path)
        cursor = self._conn.cursor()
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS ovpn (
            host_name TEXT PRIMARY KEY,
            ip TEXT,
            udp_port INTEGER,
            tcp_port INTEGER,
            ovc_url TEXT,
            downloaded_at TEXT
        )
        ''')
        self._conn.commit()

    def select(self, hostName: str) -> Optional[Ovpn]:
        """
        Select an OVPN entry by host name. Raises `RuntimeError` if the
        database connection has not been established.
        """
        if self._conn is None:
            raise RuntimeError(
                "Database connection has not been established.")
        cursor = self._conn.cursor()
        cursor.execute('SELECT ip, udp_port, tcp_port, ovc_url, downloaded_at FROM ovpn WHERE host_name = ?', (hostName,))
        row = cursor.fetchone()
        if row:
            return Ovpn(hostName, row[0], row[1], row[2], row[3], datetime.fromisoformat(row[4]))
        return None

    def update(self, ovpn: Ovpn) -> None:
        """
        Update an existing OVPN entry in the database. Raises `RuntimeError`
        if the database connection has not been established.
        """
        if self._conn is None:
            raise RuntimeError(
                "Database connection has not been established.")
        cursor = self._conn.cursor()
        cursor.execute(
            'UPDATE ovpn SET ip=?, udp_port=?, tcp_port=?, ovc_url=?, downloaded_at=? WHERE host_name=?',
            (ovpn.ip, ovpn.udpPort, ovpn.tcpPort, ovpn.ovcUrl, ovpn.downloadedAt.isoformat(), ovpn.hostName)
        )
        self._conn.commit()

    def insert(self, ovpn: Ovpn) -> None:
        """
        Insert a new OVPN entry into the database. Raises `RuntimeError`
        if the database connection has not been established.
        """
        if self._conn is None:
            raise RuntimeError(
                "Database connection has not been established.")
        cursor = self._conn.cursor()
        cursor.execute(
            'INSERT INTO ovpn (host_name, ip, udp_port, tcp_port, ovc_url, downloaded_at) VALUES (?, ?, ?, ?, ?, ?)',
            (ovpn.hostName, ovpn.ip, ovpn.udpPort, ovpn.tcpPort, ovpn.ovcUrl, ovpn.downloadedAt.isoformat())
        )
        self._conn.commit()

    def close(self) -> None:
        if self._conn:
            self._conn.close()


def parseVpnGateCsv(csv_text: str) -> VpnGateData:
    """
    Parses VPN Gate CSV text into a VpnGateData object, handling the specific
    format quirks of the vpngate.net API.

    This function combines robust CSV parsing with logic to handle ragged rows
    by padding them to match the header's column count.

    Args:
        csv_text: The raw string content from the VPN Gate API.

    Returns:
        A VpnGateData object containing the parsed header and data rows, or
        None if the input text is empty after filtering comments.

    Raises:
        TypeError: If the underlying CSV data is not consistent with the
        expected format, such as missing headers or inconsistent row lengths.
    """
    lines = csv_text.splitlines()
    lines = [line.strip() for line in lines]
    # Identifying star- and hash-started line indices in the original list...
    starIndices = {i for i, ln in enumerate(lines) if ln.startswith('*')}
    hashIndices = {i for i, ln in enumerate(lines) if ln.startswith('#')}
    # Removing leading & trailing star-started lines...
    allIndices = set(range(len(lines)))
    nonStarIndices = allIndices - starIndices
    if not nonStarIndices:
        raise TypeError("No non-asterisk lines to parse.")
    temp = sorted(nonStarIndices)
    startIdx, stopIdx = temp[0], temp[-1] + 1
    # Remove leading/trailing '*' lines by slicing
    lines = lines[startIdx:stopIdx]
    # Updating star- & hash- started lines indices
    # after removing leading and traling start-started lines...
    starIndices = {
        idx - startIdx
        for idx in starIndices
        if startIdx < idx < stopIdx}
    hashIndices = {
        idx - startIdx
        for idx in hashIndices
        if startIdx <= idx < stopIdx}
    #
    if starIndices:
        raise TypeError(
            "Comments (start-started lines) found in the middle")
    if hashIndices != {0}:
        raise TypeError(
            "Unsupported header position: " + str(hashIndices))
    # Removing the leading '#' from the header...
    lines[0] = lines[0][1:]  
    # Isolate header and data lines
    try:
        # Using the `csv` module for robust parsing...
        # Parsing header...
        tplHeader = tuple(next(csv.reader(StringIO(lines[0]))))
        nCols = len(tplHeader)
        # Parsing data rows...
        strmCsv = StringIO('\n'.join(lines[1:]))
        reader = csv.reader(strmCsv)
        processed_rows = []
        for i, row in enumerate(reader, start=1):
            nRowCols = len(row)
            diff = nCols - nRowCols
            # Implement logic from AlgoDraft for row consistency
            if diff < 0:
                raise TypeError(
                    f"Format error on data row {i}: Found {nRowCols}"
                    f" columns, but header has {nCols}.")
            elif diff > 0:
                # Pad the row with empty strings if it's shorter
                row.extend([''] * diff)
            #
            processed_rows.append(tuple(row)) # Store as immutable tuple
    except csv.Error as e:
        raise TypeError("Malformed CSV text could not be parsed.") from e
    #
    return VpnGateData(header=tplHeader, rows=processed_rows)


def csvObjToHtmlTable(
        obj: VpnGateData,
        id: str = "",
        class_: str = "",
        ) -> str:
    """
    Converts a `VpnGateData` object into an HTML table string.

    Args:
        obj: The `VpnGateData` object containing the header and rows.
        id (str, optional): The ID to assign to the <table> element.
            Defaults to "".
        class_ (str, optional): The class name(s) to assign to the <table>
            element. Defaults to "".

    Returns:
        A string containing the generated HTML table.
    """
    # Start building the table tag, adding id and class attributes if provided
    tableAttrs = []
    if id:
        tableAttrs.append(f'id="{html.escape(id)}"')
    if class_:
        tableAttrs.append(f'class="{html.escape(class_)}"')
    
    tableElem = [f"<table {' '.join(tableAttrs)}>"]
    # Building the header...
    tableElem.append("  <thead>")
    tableElem.append("    <tr>")
    for header_item in obj.header:
        tableElem.append(f"      <th>{html.escape(header_item)}</th>")
    tableElem.append("    </tr>")
    tableElem.append("  </thead>")
    # Building the body...
    tableElem.append("  <tbody>")
    for row in obj.rows:
        tableElem.append("    <tr>")
        for cell in row:
            tableElem.append(f"      <td>{html.escape(cell)}</td>")
        tableElem.append("    </tr>")
    tableElem.append("  </tbody>")
    # Closing the table...
    tableElem.append("</table>")
    # Returning the final HTML string...
    return "\n".join(tableElem)
