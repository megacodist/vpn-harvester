import binascii
import csv
import base64
import re
from datetime import datetime
from pathlib import Path
import sys
csv.field_size_limit(10_000_000)

from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils.vpn_gate import parseVpnGateCsv, IVpnGateableDb, VpnGateCsvData


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


def saveOvpnFiles(dir_: Path, vpnGateData: VpnGateCsvData) -> None:
    # Getting the index of host name column...
    try:
        idxHostName = vpnGateData.header.index('HostName')
    except ValueError:
        print("Failed to find host name column.")
        sys.exit(1)
    # Getting the index of OpenVPN base64 column...
    try:
        idxBase64 = vpnGateData.header.index("OpenVPN_ConfigData_Base64")
    except ValueError:
        print("Failed to find OpenVPN Base64 column.")
        sys.exit(1)
    for row in vpnGateData.rows:
        # Getting host name...
        try:
            hostName = row[idxHostName]
        except IndexError:
            print(f"No host name of `{row}`")
            continue
        # Getting OpenVPN base64 text...
        try:
            b64Ovpn = row[idxBase64]
        except IndexError:
            print(f"No OpenVPN config data of `{hostName}`")
            continue
        # Decoding the Base64 OpenVPN config...
        try:
            binBase64 = base64.b64decode(b64Ovpn)
        except (binascii.Error) as err:
            print(f"Skipping {hostName}: Base64 decode error: {err}")
            continue
        # Writing to .ovpn file...
        filename = f"{hostName}.ovpn"
        filepath = OVPNS_DIR / filename
        with open(filepath, 'wb') as f:
            f.write(binBase64)
        print(f"Written {filepath}")
        


def renderHtmlFromCsv(
        csv: VpnGateCsvData,
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
    from widgets.vpn_narvester_win import VpnHarvesterWin
    #
    vpnHarvesterApp = VpnHarvesterWin()
    vpnHarvesterApp.mainloop()


if __name__ == '__main__':
    main()
