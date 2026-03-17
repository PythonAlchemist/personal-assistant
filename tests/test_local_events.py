"""Tests for local events service."""

import sqlite3
from assistant.storage.database import get_connection, init_db


def test_local_events_table_exists():
    conn = get_connection(":memory:")
    init_db(conn)
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='local_events'"
    )
    assert cursor.fetchone() is not None
    conn.close()
