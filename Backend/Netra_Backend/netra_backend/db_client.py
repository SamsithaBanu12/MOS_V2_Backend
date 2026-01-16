# netra_backend/db_client.py
import psycopg2
import logging
import os
from typing import Dict, List, Any, Set

import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

logger = logging.getLogger(__name__)

def _infer_pg_type(value: Any) -> str:
    """Very simple type inference: int -> BIGINT, float -> DOUBLE PRECISION, bool -> BOOLEAN, datetime -> TIMESTAMPTZ, else TEXT."""
    if isinstance(value, bool):
        return "BOOLEAN"
    if isinstance(value, int):
        return "BIGINT"
    if isinstance(value, float):
        return "DOUBLE PRECISION"
    if isinstance(value, datetime):
        return "TIMESTAMPTZ"
    return "TEXT"


class PostgresClient:
    """
    Simple PostgreSQL client for:
    - Creating per-packet tables if not exists
    - Inserting decoded rows
    - Logging decoder-not-found and decoder-failed cases
    """

    def __init__(self):
        # Placeholder credentials – you will fill these via environment variables
        self.host = os.getenv("DB_HOST", "127.0.0.1")
        self.port = int(os.getenv("DB_PORT", "5432"))
        self.dbname = os.getenv("DB_NAME", "netra_tlm")
        self.user = os.getenv("DB_USER", "netra_user")
        self.password = os.getenv("DB_PASSWORD", "netra_password")

        self.conn = None
        self._known_tables: Set[str] = set()
        self._connect()
        self._ensure_decoder_not_found_table()
        self._ensure_decoder_failed_table()

    def _connect(self) -> None:
        logger.info(
            "Connecting to Postgres host=%s port=%s db=%s user=%s",
            self.host,
            self.port,
            self.dbname,
            self.user,
        )
        self.conn = psycopg2.connect(
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
        )
        self.conn.autocommit = True
        logger.info("Connected to Postgres")

    def _table_exists_in_db(self, table_name: str) -> bool:
        """Check if table actually exists in the database."""
        with self.conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                );
            """, (table_name,))
            return cur.fetchone()[0]

    def ensure_table_for_packet(self, packet_table: str, sample_row: Dict[str, Any]) -> None:
        """
        Ensure a table exists for this packet.
        Table name will be quoted exactly as provided (so use UPPERCASE if you like).
        """
        # If we think it exists, verify it actually does in the DB
        if packet_table in self._known_tables:
            if self._table_exists_in_db(packet_table):
                logger.info("Table %s already exists in DB, skipping creation", packet_table)
                return
            else:
                # Table was deleted externally, remove from cache
                self._known_tables.discard(packet_table)
                logger.warning("Table %s was deleted externally, recreating...", packet_table)

        columns_sql_parts = []
        for key, value in sample_row.items():
            col_type = _infer_pg_type(value)
            col_name = key  # assume safe; if needed, sanitize externally
            logger.info("  Column '%s': value=%s, inferred_type=%s", col_name, type(value).__name__, col_type)
            columns_sql_parts.append(f'"{col_name}" {col_type}')

        # Add a simple surrogate PK id and a timestamp
        columns_sql = ", ".join(
            ['id BIGSERIAL PRIMARY KEY', 'created_at TIMESTAMPTZ DEFAULT NOW()'] + columns_sql_parts
        )

        # Quote table name to preserve case and underscores
        table_quoted = f'"{packet_table}"'
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_quoted} ({columns_sql});"

        logger.info("Creating table %s with SQL: %s", packet_table, create_sql)
        with self.conn.cursor() as cur:
            cur.execute(create_sql)

        self._known_tables.add(packet_table)

    def insert_rows(self, packet_table: str, rows: List[Dict[str, Any]]) -> None:
        """
        Insert multiple rows into the packet's table.
        Assumes ensure_table_for_packet has already been called at least once.
        """
        if packet_table not in self._known_tables:
            # create from first row on the fly
            self.ensure_table_for_packet(packet_table, rows[0])

        table_quoted = f'"{packet_table}"'
        # All rows assumed to have same keys
        keys = list(rows[0].keys())
        columns_sql = ", ".join(f'"{k}"' for k in keys)
        values = [[row.get(k) for k in keys] for row in rows]

        insert_sql = f"INSERT INTO {table_quoted} ({columns_sql}) VALUES %s"

        logger.debug("Inserting %d rows into %s", len(rows), packet_table)
        try:
            with self.conn.cursor() as cur:
                execute_values(cur, insert_sql, values)
        except psycopg2.errors.UndefinedTable:
            # Table was deleted between check and insert, recreate and retry
            logger.warning("Table %s disappeared during insert, recreating...", packet_table)
            self._known_tables.discard(packet_table)
            self.ensure_table_for_packet(packet_table, rows[0])
            # Retry insert
            with self.conn.cursor() as cur:
                execute_values(cur, insert_sql, values)

    def _ensure_decoder_not_found_table(self) -> None:
        """
        Table for cases where decoder module/function does NOT exist.
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS "DECODER_NOT_FOUND" (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            packet_name TEXT,
            hex_payload TEXT,
            error TEXT
        );
        """
        with self.conn.cursor() as cur:
            cur.execute(create_sql)
        self._known_tables.add("DECODER_NOT_FOUND")

    def _ensure_decoder_failed_table(self) -> None:
        """
        Table for cases where decoder exists but fails (buffer error, runtime error, DB error, etc.).
        """
        create_sql = """
        CREATE TABLE IF NOT EXISTS "DECODER_FAILED" (
            id BIGSERIAL PRIMARY KEY,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            packet_name TEXT,
            hex_payload TEXT,
            error TEXT
        );
        """
        with self.conn.cursor() as cur:
            cur.execute(create_sql)
        self._known_tables.add("DECODER_FAILED")

    def insert_decoder_not_found(self, packet_name: str, hex_payload: str, error: str) -> None:
        """
        Insert entry into DECODER_NOT_FOUND table.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "DECODER_NOT_FOUND" (packet_name, hex_payload, error) VALUES (%s, %s, %s)',
                (packet_name, hex_payload, error),
            )

    def insert_decoder_failed(self, packet_name: str, hex_payload: str, error: str) -> None:
        """
        Insert entry into DECODER_FAILED table.
        """
        with self.conn.cursor() as cur:
            cur.execute(
                'INSERT INTO "DECODER_FAILED" (packet_name, hex_payload, error) VALUES (%s, %s, %s)',
                (packet_name, hex_payload, error),
            )
