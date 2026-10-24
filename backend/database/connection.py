"""Database connection and session management for CHARACTER ENGINE backend."""

import os
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.config.config import Config, get_config


class DatabaseManager:
    """Database connection and session manager."""

    def __init__(self, config: Config):
        """Initialize database manager.

        Args:
            config: Configuration object
        """
        self.config = config
        self._engine = None
        self._session_factory = None

    def get_engine(self):
        """Get or create database engine.

        Returns:
            SQLAlchemy engine
        """
        if self._engine is None:
            # Use SQLite for test environment, PostgreSQL for others
            if self.config.environment.value == "test":
                # In-memory database shared by every session of this manager
                # (StaticPool keeps a single connection alive). Set
                # CHARACTER_ENGINE_TEST_DB_FILE=1 to debug against a file instead.
                if os.getenv("CHARACTER_ENGINE_TEST_DB_FILE"):
                    database_url = f"sqlite:///{self.config.database.database}.db"
                    pool_args = {}
                else:
                    database_url = "sqlite://"
                    pool_args = {
                        "poolclass": StaticPool,
                        "connect_args": {"check_same_thread": False},
                    }
            else:
                database_url = (
                    f"postgresql://{self.config.database.username}:"
                    f"{self.config.database.password}@"
                    f"{self.config.database.host}:"
                    f"{self.config.database.port}/"
                    f"{self.config.database.database}"
                )
                pool_args = {
                    "pool_size": self.config.database.pool_size,
                    "max_overflow": self.config.database.max_overflow,
                    "pool_pre_ping": True
                }

            self._engine = create_engine(
                database_url,
                echo=self.config.database.echo_sql,
                **pool_args
            )

        return self._engine

    def get_session_factory(self):
        """Get or create session factory.

        Returns:
            SQLAlchemy session factory
        """
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.get_engine(),
                autocommit=False,
                autoflush=False
            )

        return self._session_factory

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get database session with automatic cleanup.

        Yields:
            SQLAlchemy session

        Example:
            with db_manager.get_session() as session:
                user = session.query(User).first()
        """
        session = self.get_session_factory()()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def create_tables(self):
        """Create all database tables.

        This is for development/testing only. Use migrations in production.
        """
        from backend.database.models import Base
        Base.metadata.create_all(bind=self.get_engine())

    def drop_tables(self):
        """Drop all database tables.

        This is for development/testing only. Never use in production.
        """
        from backend.database.models import Base
        Base.metadata.drop_all(bind=self.get_engine())


# Global database manager instance
_db_manager: Optional[DatabaseManager] = None


def get_db_manager(config: Optional[Config] = None) -> DatabaseManager:
    """Get global database manager instance.

    Args:
        config: Configuration object (uses default if not provided)

    Returns:
        Database manager instance
    """
    global _db_manager

    if _db_manager is None:
        if config is None:
            config = get_config()
        _db_manager = DatabaseManager(config)

    return _db_manager


def get_session() -> Generator[Session, None, None]:
    """Get database session (for dependency injection).

    Yields:
        SQLAlchemy session
    """
    db_manager = get_db_manager()
    with db_manager.get_session() as session:
        yield session
