# vpn_gate.py

from __future__ import annotations
import abc
import csv
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import StringIO
from ipaddress import IPv4Address, IPv6Address, ip_address
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Type, TypeVar
from bisect import bisect_left

# --- Custom Exceptions ---

class VpnGateError(Exception):
    """Base class for all VPN Gate-related errors in this module."""
    pass

class HeadingNotFoundError(VpnGateError):
    """Raised when a required CSV heading is not found."""
    pass

class FormatError(VpnGateError):
    """Raised for general CSV format violations."""
    pass
    
class BadColumnsError(VpnGateError):
    """Raised when CSV columns do not match expected columns."""
    pass

class MismatchingConfigNamesError(VpnGateError):
    """Raised when updating configs with different names."""
    pass

class ConflictingConfigIDsError(VpnGateError):
    """Raised when updating configs with conflicting non-null IDs."""
    pass

class DifferentStatAtTimestampError(VpnGateError):
    """
    Raised when two `OwnerStat` objects with a different values co-exist
    at the same timestamp.
    """
    pass

class StatChronologicallyExistsError(VpnGateError):
    """
    Raised when an identical `OwnerStat` exists chronologically next to the
    new one. This means the new stat is identical to its chronological
    neighbors.
    """
    pass
    
class DifferentTestAtTimestampError(VpnGateError):
    """
    Raised when two `UserTest` objects with a different values co-exist
    at the same timestamp.
    """
    pass


# --- Type Definitions ---
IPAddress = IPv4Address | IPv6Address
T = TypeVar('T', bound='CsvBase')
_cls_heading_cache: Dict[Type[CsvBase], dict[Tuple[str, ...], dict[str, int]]]
_cls_heading_cache = {}

# --- Data Models ---

class CsvBase:
    """Base class for objects that can be created from a CSV row."""
    MP_HEADING_ATTR: Dict[str, str] = {}
    id: Optional[int]

    @classmethod
    def get_csv_headings(cls) -> Set[str]:
        """
        Returns a set of all expected CSV heading needed for this class.
        """
        return set(cls.MP_HEADING_ATTR.keys())
    
    @classmethod
    def get_csv_attrs(cls) -> Set[str]:
        """
        Returns a set of all attributes populated from the CSV.
        """
        return set(cls.MP_HEADING_ATTR.values())

    @classmethod
    def from_csv(
            cls: Type[T],
            headings: Tuple[str, ...],
            values: Tuple[str, ...],
            ) -> T:
        """
        Factory method to create an instance from a CSV row.

        Raises:
            `HeadingNotFoundError`
        """
        # Obtaining `heading -> index` mapping...
        if cls not in _cls_heading_cache:
            _cls_heading_cache[cls] = {}
        if headings not in _cls_heading_cache[cls]:
            mp_heading_idx = {}
            for heading in cls.MP_HEADING_ATTR:
                try:
                    idx = headings.index(heading)
                except ValueError as e:
                    raise HeadingNotFoundError(
                        f"Required heading '{heading}' not found in "
                        "CSV.") from e
                else:
                    mp_heading_idx[heading] = idx
            _cls_heading_cache[cls][headings] = mp_heading_idx
        mp_heading_idx = _cls_heading_cache[cls][headings]
        # Preparing attributes for the dataclass constructor...
        attrs = {}
        for csv_heading, attr_name in cls.MP_HEADING_ATTR.items():
            idx = mp_heading_idx[csv_heading]
            attrs[attr_name] = values[idx] if idx < len(values) else ""
        # Creating the instance...
        instance = cls(**attrs)
        instance.id = None
        return instance

@dataclass
class VpnConfig(CsvBase):    
    name: str
    country_code: str
    country_name: str
    log_type: str
    operator_name: str
    operator_message: str
    ovpn_config_base64: str
    ip: Optional[IPAddress] = None
    id: Optional[int] = None

    MP_HEADING_ATTR: Dict[str, str] = {
        'HostName': 'name',
        'CountryShort': 'country_code',
        'CountryLong': 'country_name',
        'IP': 'ip',
        'LogType': 'log_type',
        'Operator': 'operator_name',
        'Message': 'operator_message',
        'OpenVPN_ConfigData_Base64': 'ovpn_config_base64'}

    def __post_init__(self):
        # Convert IP string to IPAddress object after initialization
        try:
            self.ip = ip_address(self.ip) if isinstance(self.ip, str) \
                else self.ip
        except ValueError:
            self.ip = None # Handle invalid IP strings gracefully

    def update_with(self, other: VpnConfig) -> bool:
        """
        Updates this config with another one. Returns `True` if any
        attribute changes, otherwise `False`.

        Raises:
            `MismatchingConfigNamesError` if names differ.
            `ConflictingConfigIDsError` if IDs are different integers.
        """
        updated = False
        if self.name != other.name:
            raise MismatchingConfigNamesError(
                f"Expected name '{self.name}', got '{other.name}'")
        if other.id is not None:
            if self.id is None:
                self.id = other.id
                updated = True
            elif self.id != other.id:
                raise ConflictingConfigIDsError(
                    f"Conflicting IDs: {self.id} and {other.id}")
        # Updating other attributes if they differ...
        for attr in (self.get_csv_attrs() - {'name', 'id'}):
            selfAttr = getattr(self, attr)
            otherAttr = getattr(other, attr)
            if selfAttr != otherAttr:
                setattr(self, attr, otherAttr)
                updated = True
        return updated

@dataclass
class OwnerStat(CsvBase):
    score: int
    ping: int
    speed: int
    num_vpn_sessions: int
    uptime: int
    total_users: int
    total_traffic: int
    dt_saved: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))
    id: Optional[int] = None

    MP_HEADING_ATTR: Dict[str, str] = {
        'Score': 'score',
        'Ping': 'ping',
        'Speed': 'speed',
        'NumVpnSessions': 'num_vpn_sessions',
        'Uptime': 'uptime',
        'TotalUsers': 'total_users',
        'TotalTraffic': 'total_traffic',}

    def __post_init__(self):
        # Type conversions
        for attr in self.MP_HEADING_ATTR.values():
            val = getattr(self, attr)
            if isinstance(val, str):
                setattr(self, attr, int(val) if val.isdigit() else 0) 
                setattr(self, attr, int(val) if val.isdigit() else 0)
    def equals_but_id_ts(self, other: 'OwnerStat') -> bool:
        """Checks equality on all fields except `id` and `dt_saved`."""
        return all(
            getattr(self, attr) == getattr(other, attr)
            for attr in self.MP_HEADING_ATTR.values())


@dataclass
class UserTest:
    id: int | None
    ping: int
    speed: int
    dt_saved: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class VpnGateServer:
    config: VpnConfig
    stats: Dict[datetime, OwnerStat] = field(default_factory=dict)
    tests: Dict[datetime, UserTest] = field(default_factory=dict)
    
    @staticmethod
    def get_all_headings() -> Set[str]:
        """
        Returns a set of all headings used in this class.
        """
        return VpnConfig.get_csv_headings().union(OwnerStat.get_csv_headings())

    @classmethod
    def from_csv_row(
            cls,
            headings: Tuple[str, ...],
            values: Tuple[str, ...],
            ) -> VpnGateServer:
        """
        Factory method to create a `VpnGateServer` instance from a CSV row.

        Args:
            headings: A tuple of CSV headings.
            values: A tuple of CSV values.

        Returns:
            A `VpnGateServer` instance.
    
        Raises:
            `HeadingNotFoundError`:
        """
        try:
            config = VpnConfig.from_csv(headings, values)
            stat = OwnerStat.from_csv(headings, values)
        except HeadingNotFoundError as e:
            raise BadColumnsError(
                "CSV row is missing required headings.") from e
        return cls(config, stats={stat.dt_saved: stat})

    def get_last_stat_dt(self) -> Optional[datetime]:
        return max(self.stats.keys()) if self.stats else None

    def get_last_test_dt(self) -> Optional[datetime]:
        return max(self.tests.keys()) if self.tests else None

    def update_with(self, other: VpnGateServer) -> bool:
        """
        Updates this server with another one. Returns `True` if updated.

        Raises:
            `MismatchingConfigNamesError`:
                if config names differ.
            `ConflictingConfigIDsError`:
                if config IDs are different integers.
        """
        # Updating the config...
        bkpConfig: VpnConfig = self.config
        try:
            updated = self.config.update_with(other.config)
        except (MismatchingConfigNamesError, ConflictingConfigIDsError) as e:
            # If config update fails, restore the original config
            self.config = bkpConfig
            raise e
        # Adding new stats...
        bkpStats = self.stats.copy()
        for stat in other.stats.values():
            try:
                self.add_stat(stat)
                updated = True
            except (DifferentStatAtTimestampError,
                        StatChronologicallyExistsError) as err:
                self.stats = bkpStats  # Restore stats on error
                raise err
        # Adding new tests...
        bkpTests = self.tests.copy()
        for test in other.tests.values():
            try:
                self.add_test(test)
                updated = True
            except DifferentTestAtTimestampError:
                continue
        # If we reach here, all updates were successful
        return updated

    def add_stat(self, stat: OwnerStat):
        """
        Adds a new stat to the server. If a stat with the same timestamp
        already exists, it checks if they are identical (except for ID and
        timestamp).

        Raises:
            `DifferentStatAtTimestampError` if a different stat exists at the
                same timestamp.
            `StatChronologicallyExistsError` if the new stat is identical to
                its chronological neighbors.
        """
        sorted_keys = sorted(self.stats.keys())
        idx = bisect_left(sorted_keys, stat.dt_saved)
        # Checking for existing stat at the same timestamp...
        if idx < len(sorted_keys) and sorted_keys[idx] == stat.dt_saved:
            if not self.stats[sorted_keys[idx]].equals_but_id_ts(stat):
                raise DifferentStatAtTimestampError(
                    f"Different stat exists at {stat.dt_saved}")
            return # It's the same, do nothing
        # Check if the new stat is identical to its chronological neighbors
        prev_stat_same = False
        if idx > 0:
            prev_stat_same = self.stats[
                sorted_keys[idx - 1]].equals_but_id_ts(stat)
        next_stat_same = False
        if idx < len(sorted_keys):
            next_stat_same = self.stats[sorted_keys[idx]].equals_but_id_ts(
                stat)
        if prev_stat_same or next_stat_same:
            raise StatChronologicallyExistsError(
                "Stat is identical to its neighbor(s).")
        self.stats[stat.dt_saved] = stat

    def add_test(self, test: UserTest):
        """
        Adds a new test to the server.

        Raises:
            `DifferentTestAtTimestampError`:
                if a different test exists at the same timestamp.
        """
        if test.dt_saved in self.tests and self.tests[test.dt_saved] != test:
            raise DifferentTestAtTimestampError(
                f"Different test exists at {test.dt_saved}")
        self.tests[test.dt_saved] = test

# --- Database Interface ---

class IVpnGateableDb(abc.ABC):
    """
    This interface is supposed to work with a database containing the
    following tables:
        CREATE TABLE IF NOT EXISTS vpn_config (
            config_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR(255) NOT NULL UNIQUE,
            ip VARCHAR(45),
            country_code VARCHAR(10) NOT NULL,
            country_name VARCHAR(255) NOT NULL,
            log_type             VARCHAR(255),
            operator_name        TEXT,
            operator_message     TEXT,
            ovpn_config_base64   TEXT
        );
        CREATE TABLE IF NOT EXISTS owner_stat (
            stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id            INTEGER NOT NULL,
            saved_ts            TIMESTAMP NOT NULL,
            score                BIGINT,
            ping_ms              INTEGER,
            speed_bps            BIGINT,
            num_vpn_sessions     INTEGER,
            uptime_ms            BIGINT,
            total_users          BIGINT,
            total_traffic_bytes  BIGINT,
            UNIQUE (config_id, saved_ts),
            FOREIGN KEY (config_id) REFERENCES vpn_config(config_id)
                ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS user_test (
            test_id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_id            INTEGER NOT NULL,
            saved_ts            TIMESTAMP NOT NULL,
            ping_ms              INTEGER,
            speed_bps            BIGINT,
            UNIQUE (config_id, saved_ts),
            FOREIGN KEY (config_id) REFERENCES vpn_config(config_id)
                ON DELETE CASCADE
        );
    """
    @staticmethod
    @abc.abstractmethod
    def create_empty_db(path: Path):
        """
        Creates an empty database with the necessary tables at the path:
        * It will create the file if the it doesn't exist, or
        * It will clear the file if the file already exists,.
        An then tables will be created.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def __init__(self, path: Path):
        """Connects to a database file."""
        raise NotImplementedError

    @abc.abstractmethod
    def check_db(self) -> bool:
        """
        Checks if the connected database has the necessary tables and columns.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def read_server(self, server_name: str) -> VpnGateServer | None:
        """
        Reads a single server and its related data by its unique name.
        Returns `None` if nothing found.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def read_all_servers(self) -> Tuple[VpnGateServer, ...]:
        """
        Reads all servers, stats, and tests from the database.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def upsert_server(self, server: VpnGateServer):
        """
        Automatically inserts or updates a server into the database. If
        inserted, it sets the ID of the server's config with the generated
        ID from database.
        """
        raise NotImplementedError

    @abc.abstractmethod
    def delete_server(self, server_name: str):
        """
        Deletes a server by name and any related stats and tests.
        """
        raise NotImplementedError
        
    @abc.abstractmethod
    def close(self):
        """Closes the database connection."""
        raise NotImplementedError

# --- CSV Data Structures and Parser ---

@dataclass
class VpnGateCsvData:
    header: Tuple[str, ...]
    rows: List[Tuple[str, ...]]


def parseVpnGateCsv(csv_text: str) -> VpnGateCsvData:
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
    return VpnGateCsvData(header=tplHeader, rows=processed_rows)
