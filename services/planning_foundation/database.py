"""PostgreSQL connection and schema helpers."""

from __future__ import annotations

from pathlib import Path

import psycopg
from psycopg.rows import dict_row


class Database:
    def __init__(self, dsn: str) -> None:
        if not dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("Hatcommways requires a PostgreSQL DSN")
        self.dsn = dsn

    def connect(self) -> psycopg.Connection:
        return psycopg.connect(self.dsn, row_factory=dict_row)

    def apply_schema(self) -> None:
        schema_path = Path(__file__).with_name("schema.sql")
        with self.connect() as connection:
            connection.execute(schema_path.read_text(encoding="utf-8"))
