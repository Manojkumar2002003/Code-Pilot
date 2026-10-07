from sqlalchemy import text

from app.database import SessionLocal, check_database_connection, engine, get_db


def test_database_engine_is_created():
    assert engine is not None


def test_database_connection_executes_select_one():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1")).scalar_one()
        assert result == 1


def test_database_session_can_be_created_and_closed():
    session = SessionLocal()
    try:
        result = session.execute(text("SELECT 1")).scalar_one()
        assert result == 1
    finally:
        session.close()


def test_database_dependency_yields_valid_session():
    db_gen = get_db()
    db = next(db_gen)

    try:
        result = db.execute(text("SELECT 1")).scalar_one()
        assert result == 1
    finally:
        db_gen.close()


def test_database_connectivity_helper_returns_true():
    assert check_database_connection() is True
