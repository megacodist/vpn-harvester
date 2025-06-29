import csv
import base64
import re
import requests
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional, Protocol
csv.field_size_limit(10_000_000)

from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils.vpn_gate import parseVpnGateCsv


# Configuration
APP_DIR: Path = Path(__file__).resolve().parent
API_CSV_URL: str = 'http://www.vpngate.net/api/iphone/'
DB_PATH: Path = APP_DIR / 'ovpns.db'
OVPNS_DIR: Path = APP_DIR / 'ovpns'
OVPNS_DIR.mkdir(exist_ok=True)


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


class IOvpnableDb(Protocol):
    def connect(self, path: Path) -> None: ...
    def select(self, hostName: str) -> Optional[Ovpn]: ...
    def update(self, ovpn: Ovpn) -> None: ...
    def insert(self, ovpn: Ovpn) -> None: ...
    def close(self) -> None: ...


class SqliteDb(IOvpnableDb):  # Renamed from Ovpnable for clarity
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


def slugify(text: str, delim: str = "-") -> str:
    """
    Convert a string into a URL-friendly slug by splitting on non-alphanumeric
    characters and joining parts with a specified delimiter defaults to
    hyphen.

    Args:
        s (str): The input string to be slugified.
        delim (str): The delimiter to use for joining the parts. Defaults
            to hyphen ('-').

    Returns:
        str: The slugified string with lowercase alphanumeric parts joined
        by hyphens.

    Examples:
        >>> slugify("Hello, World! This is a test.")
        'hello-world-this-is-a-test'
        >>> slugify("!Hello World!")
        'hello-world'
        >>> slugify("hello_world test-123")
        'hello-world-test-123'
        >>> slugify("!!!")
        ''
    """
    parts: list[str] = re.split(r'[\W_]+', text.lower())
    filtered_parts: list[str] = [part for part in parts if part]
    return delim.join(filtered_parts)


def fetchTextRes(url: str, timeout: float = 10.0) -> str:
    """
    Fetches a text resource from a URL, checks that it's plain text, and
    decodes it using the character set specified in the Content-Type
    header. Raises exceptions for network errors, server errors, and MIME
    type errors.

    Args:
        url: The URL to fetch the resource from.
        timeout: Maximum time to wait for the server response in seconds
            (default: 10.0).

    Returns:
        The decoded text content of the response.

    Raises:
        ValueError: If the Content-Type is not 'text/plain' or is missing.
        requests.HTTPError: For HTTP 4xx or 5xx status codes (e.g., 403, 503).
        requests.exceptions.RequestException: Something wrong happened with
            the network, URL, etc. such as:
            requests.exceptions.ConnectionError
        requests.Timeout: If the request times out.
        requests.ConnectionError: For network issues like DNS failure.
        requests.RequestException: For other request-related errors.
    """
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    content_type = response.headers.get('Content-Type', '').lower()
    media_type = content_type.split(';', 1)[0].strip()
    if media_type != 'text/plain':
        raise ValueError(f"Expected 'text/plain', but got '{media_type}'")
    # Decoding & returning the text...
    return response.text


def processRows(
        text: str,
        db: IOvpnableDb,
        outputDir: Path,
        url: str,
    ) -> None:
    reader = csv.reader(text.splitlines())
    for row in reader:
        if not row or row[0].startswith('#'):
            continue
        if not row[0] or not row[0].isdigit():
            print(f'Skipping row with invalid public IP: {row[0]}')
            continue
        if not row[4] or not row[4].strip().isalnum():
            print(f'Skipping row with empty host name: {row[4]}')
            continue
        if not row[14]:
            print(f'Skipping row with empty OVPN base64 data: {row[14]}')
            continue

        publicIp = row[0]
        hostName = row[4]
        ovpnBase64 = row[14]
        udpPort = int(row[11]) if row[11] else None
        tcpPort = int(row[12]) if row[12] else None
        configData = base64.b64decode(ovpnBase64)

        slug = slugify(hostName)
        filename = f"{slug}_{publicIp}.ovpn"
        filepath = outputDir / filename

        existing = db.select(hostName)
        ovpn = Ovpn(hostName, publicIp, udpPort, tcpPort, url, datetime.utcnow())

        if existing:
            if (existing.ip, existing.udpPort, existing.tcpPort) != (ovpn.ip, ovpn.udpPort, ovpn.tcpPort):
                print(f'Updating VPN config: {filename}')
                filepath.write_bytes(configData)
                db.update(ovpn)
        else:
            print(f'Downloading new VPN config: {filename}')
            filepath.write_bytes(configData)
            db.insert(ovpn)


def renderHtmlFromCsv(
        csv: list[list[str]],
        template_path: Path,
        output_path: Path,
        ) -> None:
    # Set up Jinja2
    env = Environment(
        loader=FileSystemLoader(template_path.parent),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template(template_path.name)
    # Render template
    html = template.render(data=csv, now=datetime.now())
    # Write HTML file
    output_path.write_text(html, encoding='utf-8')
    print(f'HTML report written to {output_path}')


def main() -> None:
    db = SqliteDb()
    db.connect(DB_PATH)
    try:
        print(f"Fetching CSV data from {API_CSV_URL}...")
        text = fetchTextRes(API_CSV_URL)
    except Exception as err:
        print(f"Failed to read the VPN Gate CSV due to: {err}")
    else:
        #processRows(lines, db, OVPNS_DIR, API_CSV_URL)
        try:
            csv = parseVpnGateCsv(text)
        except ValueError as e:
            print(f"Error parsing CSV: {e}")
        else:
            renderHtmlFromCsv(
                csv,
                APP_DIR / 'vpn-gate-report.j2',
                APP_DIR / 'vpn-gate-report.html')
    db.close()
    print('Done.')


if __name__ == '__main__':
    main()
