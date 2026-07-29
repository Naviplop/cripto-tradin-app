from __future__ import annotations

from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from infrastructure.persistence.sqlalchemy.models import Base, create_engine_from_url, create_session_factory


_engine = None
_SessionFactory = None


def init_engine(database_url: str) -> None:
    global _engine, _SessionFactory
    _engine = create_engine_from_url(database_url)
    _SessionFactory = create_session_factory(_engine)


def get_session_factory() -> sessionmaker:
    if _SessionFactory is None:
        raise RuntimeError("Engine not initialized. Call init_engine first.")
    return _SessionFactory


def get_engine():
    if _engine is None:
        raise RuntimeError("Engine not initialized. Call init_engine first.")
    return _engine


def create_all():
    engine = get_engine()
    Base.metadata.create_all(engine)


def drop_all():
    engine = get_engine()
    Base.metadata.drop_all(engine)
