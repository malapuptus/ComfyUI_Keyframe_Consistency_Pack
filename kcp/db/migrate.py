from __future__ import annotations

import sqlite3
from pathlib import Path

LATEST_SCHEMA_VERSION = 2


def get_user_version(conn: sqlite3.Connection) -> int:
    row = conn.execute("PRAGMA user_version").fetchone()
    return int(row[0]) if row else 0


def apply_schema_v1(conn: sqlite3.Connection) -> None:
    schema_path = Path(__file__).with_name("schema_v1.sql")
    conn.executescript(schema_path.read_text(encoding="utf-8"))
    conn.execute("PRAGMA user_version = 1")


def apply_schema_v2(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS seed_bank_entry (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          seed INTEGER NOT NULL,
          created_at INTEGER NOT NULL,
          prompt_hash TEXT NOT NULL DEFAULT '',
          context_hash TEXT NOT NULL DEFAULT '',
          checkpoint TEXT NOT NULL DEFAULT '',
          sampler TEXT NOT NULL DEFAULT '',
          scheduler TEXT NOT NULL DEFAULT '',
          steps INTEGER NOT NULL DEFAULT 20,
          cfg REAL NOT NULL DEFAULT 7.0,
          width INTEGER NOT NULL DEFAULT 1024,
          height INTEGER NOT NULL DEFAULT 1024,
          positive_prompt TEXT NOT NULL DEFAULT '',
          negative_prompt TEXT NOT NULL DEFAULT '',
          tags_csv TEXT NOT NULL DEFAULT '',
          note TEXT NOT NULL DEFAULT '',
          context_json TEXT NOT NULL DEFAULT '{}',
          UNIQUE(seed, context_hash)
        );

        CREATE INDEX IF NOT EXISTS idx_seed_bank_created ON seed_bank_entry(created_at DESC);
        CREATE INDEX IF NOT EXISTS idx_seed_bank_seed ON seed_bank_entry(seed);
        CREATE INDEX IF NOT EXISTS idx_seed_bank_prompt_hash ON seed_bank_entry(prompt_hash);
        CREATE INDEX IF NOT EXISTS idx_seed_bank_checkpoint ON seed_bank_entry(checkpoint);
        """
    )
    conn.execute("PRAGMA user_version = 2")


def migrate(conn: sqlite3.Connection) -> int:
    current = get_user_version(conn)
    if current < 1:
        apply_schema_v1(conn)
        conn.commit()
        current = 1
    if current < 2:
        apply_schema_v2(conn)
        conn.commit()
        current = 2
    return current
