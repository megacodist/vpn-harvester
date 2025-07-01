import csv
from dataclasses import dataclass
import html
from io import StringIO


@dataclass
class VpnGateData:
    """
    A container for VPN Gate CSV data, separating headers from data rows.
    This class is used to encapsulate the parsed CSV data from VPN Gate.
    Attributes:
        headers (list[str]): The header row of the CSV.
        rows (list[list[str]]): The data rows of the CSV.
    """
    headers: list[str]
    rows: list[list[str]]


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
    lines = csv_text.strip().splitlines()
    # Filtering out the leading and trailing comment lines...
    startIdx = 1 if lines and lines[0].startswith('*') else 0
    stopIdx = len(lines) if lines and lines[-1].startswith('*') else None
    lines = lines[startIdx:stopIdx]
    # Checking the header line...
    noHeaderError: bool =  False
    linesIter: Iterator[str] = iter(lines)
    try:
        line = next(linesIter)
    except StopIteration:
        noHeaderError =  True
    else:
        if not line.startswith('#'):
            noHeaderError = True
    if noHeaderError:
        raise TypeError(
            "Invalid format: Header line starting with '#' not found.")
    # 
    formatError: bool = any([
        line.startswith('*') or line.startswith('#')
        for line in lines])
    if formatError:
        raise TypeError(
            "Format error: unexpected comments or header in the CSV")
    # Isolate header and data lines
    try:
        # Using the `csv` module for robust parsing...
        # Parsing header...
        header_tuple = tuple(next(csv.reader(StringIO(lines[0]))))
        n_cols = len(header_tuple)
        # Parsing data rows...
        csv_file = StringIO('\n'.join(lines[1:]))
        reader = csv.reader(csv_file)
        processed_rows = []
        for i, row in enumerate(reader, start=1):
            n_data_line = len(row)
            diff = n_cols - n_data_line
            # Implement logic from AlgoDraft for row consistency
            if diff < 0:
                raise TypeError(
                    f"Format error on data row {i}: Found {n_data_line}"
                    f" columns, but header has {n_cols}.")
            elif diff > 0:
                # Pad the row with empty strings if it's shorter
                row.extend([''] * diff)
            #
            processed_rows.append(tuple(row)) # Store as immutable tuple
    except csv.Error as e:
        raise TypeError("Malformed CSV text could not be parsed.") from e

    return VpnGateData(header=header_tuple, rows=processed_rows)


def csvObjToHtmlTable(obj: VpnGateData, id: str = "", class_name: str = "") -> str:
    """
    Converts a VpnGateData object into an HTML table string.

    Args:
        obj: The VpnGateData object containing the header and rows.
        id (str, optional): The ID to assign to the <table> element. Defaults to "".
        class_name (str, optional): The class name(s) to assign to the <table>
                                    element. Defaults to "".

    Returns:
        A string containing the generated HTML table.
    """
    # Start building the table tag, adding id and class attributes if provided
    table_attributes = []
    if id:
        table_attributes.append(f'id="{html.escape(id)}"')
    if class_name:
        table_attributes.append(f'class="{html.escape(class_name)}"')
    
    html_parts = [f"<table {' '.join(table_attributes)}>"]

    # Build the header
    html_parts.append("  <thead>")
    html_parts.append("    <tr>")
    for header_item in obj.header:
        html_parts.append(f"      <th>{html.escape(header_item)}</th>")
    html_parts.append("    </tr>")
    html_parts.append("  </thead>")

    # Build the body
    html_parts.append("  <tbody>")
    for row in obj.rows:
        html_parts.append("    <tr>")
        for cell in row:
            html_parts.append(f"      <td>{html.escape(cell)}</td>")
        html_parts.append("    </tr>")
    html_parts.append("  </tbody>")

    # Close the table
    html_parts.append("</table>")

    return "\n".join(html_parts)
