import binascii
import csv
import base64
import logging
from datetime import datetime
from pathlib import Path
import sys
csv.field_size_limit(10_000_000)

from jinja2 import Environment, FileSystemLoader, select_autoescape

from utils.vpn_gate import VpnGateCsvData, IVpnGateableDb


# Configuration
_APP_DIR: Path = Path(__file__).resolve().parent
_SECRET_KEY = b"a-secret-key"
API_CSV_URL: str = 'http://www.vpngate.net/api/iphone/'
DB_PATH: Path = _APP_DIR / 'ovpns.db'
OVPNS_DIR: Path = _APP_DIR / 'ovpns'
OVPNS_DIR.mkdir(exist_ok=True)


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


def connectDb(
        db_path: Path,
        db_class: type[IVpnGateableDb],
        ) -> IVpnGateableDb | None:
    """
    Attempts to connect to a database file, validates its schema, and
    returns a DB object.

    Args:
        `db_path`: The file system path to the database.
        `db_class`: The class (implementing `IVpnGateableDb`) to use for
            the connection.

    Returns:
        An instance of the `db_class` if connection and validation are
            successful, otherwise `None`.
    """
    import sqlite3
    db = None
    try:
        # Attempt to instantiate the database object, which connects
        # to the file
        db = db_class(db_path)
    except (IOError, PermissionError) as err:
        # Catches file system errors like permission denied
        logging.error(
            f"Database path '{db_path}' is inaccessible: {err}",
            exc_info=True)
        print(f"Error: Database path '{db_path}' is inaccessible.")
        return None
    except sqlite3.DatabaseError as err:
        # Catches errors where the file is not a valid SQLite database
        logging.error(
            (f"File '{db_path}' is not a valid database for "
                f"{db_class.__name__}: {err}"),
            exc_info=True)
        print(f"Error: The file at '{db_path}' is not a valid database.")
        return None
    except Exception as err:
        # Catch any other unexpected errors during initialization
        logging.critical(
            f"An unexpected error occurred connecting to '{db_path}': {err}",
            exc_info=True)
        print(
            "An unexpected critical error occurred during database connection.")
        return None
    # If the connection was successful, check the database schema
    if db.check_db():
        logging.info(f"Successfully connected to and validated database: {db_path}")
        return db
    else:
        logging.error(f"Database at '{db_path}' does not have the necessary tables and columns.")
        print(f"Error: The database at '{db_path}' does not have the required schema.")
        db.close()  # Clean up the connection before exiting
        return None


def main() -> None:
    # Configure the logger
    print("Configuring the logger...")
    from utils.logger import configureLogger
    configureLogger(_APP_DIR / 'log.log')
    # Load application settings
    #spinner.start(_('LOADING_SETTINGS'))
    print("Loading settings...")
    from megacodist.settings import BadConfigFileError
    from utils.settings import VpnGateAppSettings
    settings = VpnGateAppSettings(_SECRET_KEY)
    pthSett = _APP_DIR / 'config.bin'
    flSett = pthSett.touch(exist_ok=True)
    flSett = open(pthSett, mode="rb+")
    try:
        settings.load(flSett)
    except BadConfigFileError as err:
        #spinner.stop(_('BAD_SETTINGS_FILE'))
        logging.error(f"Failed to load config file: {err}")
        print("Failed to load config file.")
    else:
        #spinner.stop(_("SETTINGS_LOADED"))
        pass
    #
    from utils.vpn_gate.manager import VpnGateSqlite as typDb
    pthDb = _APP_DIR / "ovpns.db"
    db = connectDb(pthDb, typDb)
    if db is None:
        sys.exit(1)
    #
    from widgets.vpn_harvester_win import VpnHarvesterWin
    vpnHarvesterApp = VpnHarvesterWin(settings=settings, db=db)
    try:
        vpnHarvesterApp.mainloop()
        flSett.seek(0)
        settings.save(flSett)
    finally:
        flSett.close()


if __name__ == '__main__':
    main()
