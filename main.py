import csv
import base64
import re
from datetime import datetime
from pathlib import Path
import sys
csv.field_size_limit(10_000_000)

from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils.vpn_gate import parseVpnGateCsv, VpnGateData, Ovpn, IVpnGateableDb, SqliteDb


# Configuration
APP_DIR: Path = Path(__file__).resolve().parent
API_CSV_URL: str = 'http://www.vpngate.net/api/iphone/'
DB_PATH: Path = APP_DIR / 'ovpns.db'
OVPNS_DIR: Path = APP_DIR / 'ovpns'
OVPNS_DIR.mkdir(exist_ok=True)


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


def processRows(
        text: str,
        db: IVpnGateableDb,
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
        csv: VpnGateData,
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
    #
    from utils.inet import fetchTextRes
    INPUT_PRMPT = (
        "\nEnter a source for the CSV data:\n"
        "- A file path (e.g., /path/to/data.csv)\n"
        "- A URL (e.g., https://example.com/data.csv)\n"
        "- Nothing to use the default VPN Gate list\n"
        "> ")
    DEFAULT_URL = 'http://www.vpngate.net/api/iphone/'
    # Looping until valid input is received...
    urlReqstd: bool = False
    text: str = ""
    while True:
        try:
            pathUrl: str = input(INPUT_PRMPT).strip()
            # Determining the choice...
            if not pathUrl:
                pathUrl = DEFAULT_URL
                urlReqstd = True
            else:
                path = Path(pathUrl)
                if path.is_file():
                    print(f'Reading CSV data from file: {path}')
                    urlReqstd = False
                    text = path.read_text(encoding='utf-8')
                else:
                    urlReqstd = True
            if urlReqstd:
                print(f'Fetching CSV data from URL: {pathUrl}')
                text = fetchTextRes(pathUrl)
            if text:
                break
        except KeyboardInterrupt:
            sys.exit(0)
        except Exception as e:
            print(f"Error: {e}")
            continue
    #
    print(f'Parsing CSV data...')
    try:
        csvData: VpnGateData = parseVpnGateCsv(text)
    except Exception as err:
        print(f'Error parsing CSV data: {err}')
        sys.exit(1)
    if not csvData.rows:
        print('No valid data found in the CSV.')
        sys.exit(1)
    renderHtmlFromCsv(
        csvData,
        APP_DIR / 'vpn-gate-report.j2',
        APP_DIR / 'vpn-gate-report.html')
    print('Done.')


if __name__ == '__main__':
    main()
