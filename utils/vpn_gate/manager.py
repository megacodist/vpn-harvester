# utils.py

from __future__ import annotations
import logging
from pathlib import Path
import sqlite3
from typing import Dict, Optional, Set

from . import (IVpnGateableDb, VpnGateServer,parseVpnGateCsv,
    BadColumnsError, VpnConfig, OwnerStat, UserTest)


# --- SQLite Database Implementation (Placeholder) ---   
class VpnGateSqlite(IVpnGateableDb):
    """
    A concrete implementation of the `IVpnGateableDb` interface using SQLite.
    """
    _CREATE_SCHEMA_SQL = """
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
    def create_empty_db(path: Path):
        """
        Ensures a fresh, empty database with the correct schema exists at
        the path:

        - If the file already exists at the path, it will be DELETED. And a
        new, empty database file is then created.
        - If the file doesn't exist, it will be created.

        Raises:
            `OSError`:
                If the file cannot be deleted or created.
            `sqlite3.Error`:
                If there is an error during the creation of the database
                or schema.
        """
        # Deleting the file if it exists...
        if path.exists():
            path.unlink()
        # Creating the new database and schema...
        with sqlite3.connect(path) as conn:
            conn.executescript(VpnGateSqlite._CREATE_SCHEMA_SQL)

    def __init__(self, path: Path):
        """Connects to a database file, enabling foreign keys and row factory."""
        # Using detect_types to enable the datetime converters we
        # registered...
        self._conn = sqlite3.connect(
            path,
            detect_types=sqlite3.PARSE_DECLTYPES)
        # Using Row factory to access columns by name...
        self._conn.row_factory = sqlite3.Row
        # Foreign keys are disabled by default in SQLite,
        # Must be enabled per-connection...
        self._conn.execute("PRAGMA foreign_keys = ON;")

    def check_db(self) -> bool:
        """
        Checks if the connected database has the necessary tables and columns.
        """
        # Defining the expected schema for validation...
        expected_schema = {
            'vpn_config': {
                'config_id', 'name', 'ip', 'country_code', 'country_name', 
                'log_type', 'operator_name', 'operator_message',
                'ovpn_config_base64'
            },
            'owner_stat': {
                'stat_id', 'config_id', 'saved_ts', 'score', 'ping_ms', 
                'speed_bps', 'num_vpn_sessions', 'uptime_ms', 'total_users', 
                'total_traffic_bytes'
            },
            'user_test': {
                'test_id', 'config_id', 'saved_ts', 'ping_ms', 'speed_bps'
            }
        }
        #
        try:
            cursor = self._conn.cursor()
            for table_name, expected_columns in expected_schema.items():
                # PRAGMA table_info is the SQLite command to get schema info
                cursor.execute(f"PRAGMA table_info('{table_name}');")
                rows = cursor.fetchall()
                if not rows:
                    # Table doesn't exist, returning `False`...
                    return False
                # Extracting the column names from the pragma result...
                actual_columns = {row['name'] for row in rows}
                # Checking if the actual columns match what we expect...
                if actual_columns != expected_columns:
                    return False
            # Returning `True`, if all tables and columns match...
            return True
        except sqlite3.Error:
            return False

    def read_all_servers(self) -> tuple[VpnGateServer, ...]:
        """
        Reads all servers, stats, and tests from the database.
        """
        cursor = self._conn.cursor()
        # 1. Fetching all configs and create `VpnGateServer` objects...
        servers_by_id: Dict[int, VpnGateServer] = {}
        cursor.execute("SELECT * FROM vpn_config")
        for row in cursor:
            config = VpnConfig(**dict(row))
            servers_by_id[config.id] = VpnGateServer(config=config) # type: ignore
        # 2. Fetching all owner stats and attach them to the correct server...
        cursor.execute("SELECT * FROM owner_stat")
        for row in cursor:
            stat = OwnerStat(
                id=row['stat_id'],
                dt_saved=row['saved_ts'],
                **{k: row[k] for k in OwnerStat.get_csv_attrs()})
            # The config_id tells us which server this stat belongs to
            server = servers_by_id.get(row['config_id'])
            if server:
                server.stats[stat.dt_saved] = stat
        # 3. Fetching all user tests and attach them...
        cursor.execute("SELECT * FROM user_test")
        for row in cursor:
            test = UserTest(
                id=row['test_id'],
                dt_saved=row['saved_ts'],
                ping=row['ping_ms'],
                speed=row['speed_bps'],)
            server = servers_by_id.get(row['config_id'])
            if server:
                server.tests[test.dt_saved] = test
        #
        return tuple(servers_by_id.values())

    def read_server(self, server_name: str) -> Optional[VpnGateServer]:
        """
        Reads a single server and its related data by its unique name.
        Returns `None` if nothing found.
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "SELECT * FROM vpn_config WHERE name = ?",
            (server_name,))
        config_row = cursor.fetchone()
        if not config_row:
            return None
        # Creating the config and server objects...
        config = VpnConfig(**dict(config_row))
        server = VpnGateServer(config=config)
        # Fetching & adding stats...
        cursor.execute(
            "SELECT * FROM owner_stat WHERE config_id = ?",
            (config.id,))
        for row in cursor:
            stat = OwnerStat(
                id=row['stat_id'],
                dt_saved=row['saved_ts'],
                **{k:row[k] for k in OwnerStat.get_csv_attrs()})
            server.stats[stat.dt_saved] = stat
        # Fetching & adding tests...
        cursor.execute(
            "SELECT * FROM user_test WHERE config_id = ?",
            (config.id,))
        for row in cursor:
            test = UserTest(
                id=row['test_id'],
                dt_saved=row['saved_ts'],
                ping=row['ping_ms'],
                speed=row['speed_bps'])
            server.tests[test.dt_saved] = test
        #
        return server

    def _insert_config(
            self,
            cursor: sqlite3.Cursor,
            config: VpnConfig,
            ) -> int:
        """Inserts a new config and returns its new ID."""
        fields = [f for f in config.get_csv_attrs() if f != 'id']
        placeholders = ', '.join('?' for _ in fields)
        values = [getattr(config, f) for f in fields]
        cursor.execute(
            f"INSERT INTO vpn_config ({', '.join(fields)}) VALUES ({placeholders})",
            values,)
        return cursor.lastrowid # type:ignore

    def _update_config(
                self,
                cursor: sqlite3.Cursor,
                config: VpnConfig,
                ) -> None:
        """Updates an existing config's attributes."""
        fields_to_update = [
            f for f in config.get_csv_attrs() if f not in {'id', 'name'}]
        set_clause = ', '.join(f'{field} = ?' for field in fields_to_update)
        values = [getattr(config, f) for f in fields_to_update]
        values.append(config.id) # For the WHERE clause
        cursor.execute(
            f"UPDATE vpn_config SET {set_clause} WHERE config_id = ?",
            values,)
    
    def upsert_server(self, server: VpnGateServer) -> None:
        """
        Automatically inserts or updates a server into the database. If
        inserted, it sets the ID of the server's config with the generated
        ID from database.
        """
        # Using transaction: commit on seccess, rollback on error...
        with self._conn:
            cursor = self._conn.cursor()
            config = server.config
            # 1. Upserting the VpnConfig...
            if config.id is None:
                # INSERT new config and get its ID back
                new_id = self._insert_config(cursor, config)
                config.id = new_id
            else:
                # UPDATE existing config
                self._update_config(cursor, config)
            # 2. Upsert OwnerStats (must have a valid config.id now)
            for stat in server.stats.values():
                if stat.id is None:
                    cursor.execute(
                        """
                            INSERT INTO owner_stat (
                                config_id, saved_ts, score, ping_ms, 
                                speed_bps, num_vpn_sessions, uptime_ms, 
                                total_users, total_traffic)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            config.id, stat.dt_saved, stat.score, stat.ping,
                            stat.speed, stat.num_vpn_sessions, stat.uptime,
                            stat.total_users, stat.total_traffic
                        ),)
                    stat.id = cursor.lastrowid # Set the ID on the object
            # 3. Upsert UserTests
            for test in server.tests.values():
                if test.id is None:
                    cursor.execute(
                        """
                            INSERT INTO user_test (
                                config_id, saved_ts, ping_ms, speed_bps)
                            VALUES (?, ?, ?, ?)
                        """,
                        (config.id, test.dt_saved, test.ping, test.speed),)
                    test.id = cursor.lastrowid # Set the ID on the object

    def delete_server(self, server_name: str):
        """
        Deletes a server by name and any related stats and tests.
        """
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute(
                "DELETE FROM vpn_config WHERE name = ?",
                (server_name,))

    def close(self):
        """Closes the database connection."""
        if self._conn:
            self._conn.close()


class VpnGateManager:
    """
    Orchestrates loading VPN server data, managing it in memory,
    and committing changes to a database.
    """
    def __init__(self, db: IVpnGateableDb):
        self._db: IVpnGateableDb = db
        self._mpNameServer: Dict[str, VpnGateServer] = {}
        self._stDelSrvrNames: Set[str] = set()
        self._stUpdSrvrNames: Set[str] = set()

    def reset_servers_from_db(self):
        """
        Clears the current in-memory state and reloads all servers
        from the database.
        """
        servers = self._db.read_all_servers()
        # Empty all in-memory collections
        self._mpNameServer.clear()
        self._stDelSrvrNames.clear()
        self._stUpdSrvrNames.clear()
        #
        for server in servers:
            self._mpNameServer[server.config.name] = server

    def sync_from_csv(self, csv_text: str):
        """
        Synchronizes the in-memory server list with a new CSV data source.
        
        This method will:
        1. Add new servers not previously seen.
        2. Update existing servers with new information.
        3. Mark any servers that are no longer in the CSV for deletion.
        
        Raises:
            `vpn_gate.BadColumnsError`: If the CSV headers do not match
                expectations.
            `FormatError`: If the CSV format is invalid.
        """
        # Parse CSV text
        csv_data = parseVpnGateCsv(csv_text)
        if set(csv_data.header) != VpnGateServer.get_all_headings():
            raise BadColumnsError(
                "The columns from the CSV data do not match the expected"
                " columns.")
        # Integrate newly-parsed data
        fresh_server_names = set()
        for row in csv_data.rows:
            server_from_csv = VpnGateServer.from_csv_row(csv_data.header, row)
            server_name = server_from_csv.config.name
            fresh_server_names.add(server_name)
            #
            if server_name in self._mpNameServer:
                # Logic for UPDATING an existing server
                try:
                    existing_server = self._mpNameServer[server_name]
                    if existing_server.update_with(server_from_csv):
                        self._stUpdSrvrNames.add(server_name)
                except Exception as e:
                    logging.warning(
                        f"Could not update server '{server_name}': {e}")
            else:
                # Logic for ADDING a new server
                self._mpNameServer[server_name] = server_from_csv
                self._stUpdSrvrNames.add(server_name)
        # Cleanup stale servers
        # Find servers that are in our manager but were not in the new CSV
        current_server_names = set(self._mpNameServer.keys())
        stale_server_names = current_server_names - fresh_server_names
        for name in stale_server_names:
            # Mark the stale server for deletion
            self.delete_server(name)

    def delete_server(self, server_name: str):
        """
        Marks a server for deletion from the database and removes it
        from the in-memory collection.
        """
        try:
            del self._mpNameServer[server_name]
        except KeyError:
            logging.warning(
                f"Attempted to delete non-existent server: {server_name}")
        else:
            self._stUpdSrvrNames.discard(server_name)
            self._stDelSrvrNames.add(server_name)
            logging.info(f"Server '{server_name}' marked for deletion.")
            
    def save_changes(self):
        """
        Commits all tracked changes (updates, inserts, deletions) to the
        database using the provided database interface.
        """
        logging.info("Saving changes to the database...")
        for name in self._stUpdSrvrNames:
            if name in self._mpNameServer:
                self._db.upsert_server(self._mpNameServer[name])
        logging.info(f"  - Upserted {len(self._stUpdSrvrNames)} servers.")
        #
        for name in self._stDelSrvrNames:
            self._db.delete_server(name)
        logging.info(f"  - Deleted {len(self._stDelSrvrNames)} servers.")
        #
        self._stUpdSrvrNames.clear()
        self._stDelSrvrNames.clear()
        logging.info("Save complete.")
