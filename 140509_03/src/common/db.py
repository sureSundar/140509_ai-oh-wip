from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session


_DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(_DATABASE_URL) if _DATABASE_URL else None
SessionLocal: Optional[sessionmaker] = (
    sessionmaker(bind=engine, autoflush=False, autocommit=False) if engine else None
)


def is_db_enabled() -> bool:
    return engine is not None and SessionLocal is not None


@contextmanager
def get_session() -> Iterator[Session]:
    if not is_db_enabled():
        raise RuntimeError("Database not configured; set DATABASE_URL to enable persistence.")
    assert SessionLocal is not None
    session: Session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

