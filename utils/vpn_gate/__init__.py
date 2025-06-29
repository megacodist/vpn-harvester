import csv
from dataclasses import dataclass
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


def parseVpnGateCsv(csv_text: str) -> VpnGateData | None:
    """
    Parses VPN Gate CSV text into a `VpnGateData` object. Returns `None`
    if the source data is empty.

    Exceptions:
        TypeError: If the CSV format is invalid.
        ValueError: if header format is invalid.
    """
    lines = csv_text.strip().splitlines()
    lines = [
        line
        for line in lines
        if line and not line.startswith('*')]
    if not lines:
        return None
    #
    headerLine = lines[0]
    if not headerLine.startswith('#'):
        raise ValueError(
            "Invalid CSV format: Header line does not start with '#'.")
    # Parsing the header and rows separately...
    csv_header_str = headerLine[1:]
    data_lines = lines[1:]
    try:
        # Using StringIO for robust parsing of single lines...
        header = next(csv.reader(StringIO(csv_header_str)))
        # If there are no data lines, reader will be empty
        if not data_lines:
            rows = []
        else:
            csv_file = StringIO('\n'.join(data_lines))
            reader = csv.reader(csv_file)
            rows = list(reader)
    except csv.Error as e:
        raise TypeError("Malformed CSV text") from e
    # Returning the structured object...
    return VpnGateData(headers=header, rows=rows)
