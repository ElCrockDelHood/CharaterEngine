"""DatabaseManager.dispose(): test fixtures close the in-memory SQLite connection."""

import sqlite3

import pytest
from sqlalchemy import inspect

from backend.config.config import Config, Environment
from backend.database.connection import DatabaseManager


def test_dispose_closes_the_sqlite_connection_and_resets_the_engine():
    manager = DatabaseManager(Config(environment=Environment.TEST))
    manager.create_tables()
    engine = manager.get_engine()
    raw = engine.raw_connection()
    dbapi = raw.dbapi_connection
    raw.close()                                   # back to the StaticPool, still open
    dbapi.execute("SELECT 1")

    manager.dispose()

    with pytest.raises(sqlite3.ProgrammingError):
        dbapi.execute("SELECT 1")                 # closed, nothing left for the garbage collector
    fresh = manager.get_engine()
    assert fresh is not engine
    assert inspect(fresh).get_table_names() == []  # a new, empty in-memory database
    manager.dispose()


def test_dispose_without_engine_is_a_no_op():
    manager = DatabaseManager(Config(environment=Environment.TEST))
    manager.dispose()
    manager.dispose()
