from __future__ import annotations

from pathlib import Path
from typing import Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.database.base import Base
from app.models import Architecture, Project, Requirement  # noqa: F401

PROJECT_ROOT = Path(__file__).resolve().parents[3]


def resolve_database_url(database_url: str | None = None) -> str:
    url = database_url or get_settings().database_url
    if not url.startswith("sqlite"):
        return url
    if url == "sqlite:///:memory:":
        return url

    candidate = url.replace("sqlite:///", "", 1)
    candidate = candidate.lstrip("/")
    candidate = candidate[2:] if candidate.startswith("./") else candidate

    if not candidate or candidate == ":memory:":
        return url

    db_path = Path(candidate)
    if not db_path.is_absolute():
        db_path = (PROJECT_ROOT / db_path).resolve()

    return f"sqlite:///{db_path.as_posix()}"


def create_database_engine(database_url: str | None = None) -> Engine:
    resolved_url = resolve_database_url(database_url)
    if resolved_url.startswith("sqlite"):
        (PROJECT_ROOT / "data").mkdir(parents=True, exist_ok=True)
    engine_kwargs = {}
    if resolved_url.startswith("sqlite"):
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    return create_engine(resolved_url, **engine_kwargs)


engine = create_database_engine()


@event.listens_for(engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    if dbapi_connection.__class__.__module__.endswith("sqlite3"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    data_dir = PROJECT_ROOT / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)

    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))


def check_database_connection() -> bool:
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1")).scalar_one()
            return result == 1
    except Exception:
        return False


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "create_database_engine",
    "resolve_database_url",
    "init_db",
    "check_database_connection",
    "get_db",
]

