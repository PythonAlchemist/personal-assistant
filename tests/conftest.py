"""Shared test fixtures."""

import pytest

from assistant.storage.database import get_connection, init_db


@pytest.fixture
def db():
    """In-memory SQLite database for testing."""
    conn = get_connection(":memory:")
    init_db(conn)
    yield conn
    conn.close()
