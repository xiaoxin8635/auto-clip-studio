from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy import event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_session_factory: sessionmaker[Session] | None = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        settings = get_settings()
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        database_url = f"sqlite:///{settings.data_dir / 'autoclip.sqlite3'}"
        _engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        event.listens_for(_engine, "connect")(_enable_sqlite_wal)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def reset_db_cache() -> None:
    """Reset cached engine; used by tests that isolate the data directory."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None


def _enable_sqlite_wal(dbapi_connection, _record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=30000")
    cursor.close()


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    if _session_factory is None:
        get_engine()
        assert _session_factory is not None
    session = _session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
