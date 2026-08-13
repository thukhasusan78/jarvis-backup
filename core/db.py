"""Shared SQLite helpers: WAL mode, busy timeout, and safe connections."""
import sqlite3
from contextlib import contextmanager
from typing import Iterator, Optional


def connect_db(db_path: str, timeout: float = 30.0) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=timeout)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA busy_timeout=30000;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def db_connection(db_path: str, timeout: float = 30.0) -> Iterator[sqlite3.Connection]:
    conn = connect_db(db_path, timeout=timeout)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
