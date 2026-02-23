from __future__ import annotations

import sqlite3
from pathlib import Path

LATEST_SCHEMA_VERSION = 1


def get_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def apply_schema_v1(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema_v1.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.execute("PRAGMA user_version = 1")


def migrate(conn: sqlite3.Connection) -> int:
    current = get_user_version(conn)
    if current < 1:
        apply_schema_v1(conn)
        conn.commit()
        current = 1
    return current
