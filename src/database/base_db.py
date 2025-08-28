"""
Base database logic using SQLAlchemy for PostgreSQL.
"""

import os
import threading
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from src.logger import log
from src.models import Base


class BaseDbLogic:
    def __init__(self):
        self._lock = threading.RLock()  # Reentrant lock for thread safety
        self._conn_params = {
            "host": os.environ.get("POSTGRES_HOST", "localhost"),
            "port": int(os.environ.get("POSTGRES_PORT", "5432")),
            "database": os.environ.get("POSTGRES_DATABASE", "medicony"),
            "user": os.environ.get("POSTGRES_USER", "medicony"),
            "password": os.environ.get("POSTGRES_PASSWORD", ""),
        }

        # Create database URL with proper URL encoding for password
        database_url = f"postgresql://{self._conn_params['user']}:{quote_plus(self._conn_params['password'])}@{self._conn_params['host']}:{self._conn_params['port']}/{self._conn_params['database']}"

        try:
            # Create engine
            self.engine = create_engine(database_url, echo=False, pool_pre_ping=True)

            # Create session factory
            self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

            # Create tables
            Base.metadata.create_all(bind=self.engine)

            log.info(
                f"Connected to PostgreSQL database at {self._conn_params['host']}:{self._conn_params['port']} using SQLAlchemy"
            )
        except Exception as e:
            log.error(f"Failed to connect to PostgreSQL: {e}")
            raise

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.SessionLocal()
