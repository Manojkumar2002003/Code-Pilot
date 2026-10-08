from datetime import datetime

from sqlalchemy import inspect

from app.database import SessionLocal, init_db
from app.models.project import Project


def test_projects_table_is_created():
    init_db()
    inspector = inspect(SessionLocal().bind)
    assert inspector.has_table('projects')
    columns = {column['name'] for column in inspector.get_columns('projects')}
    assert {'id', 'name', 'description', 'status', 'created_at', 'updated_at'}.issubset(columns)


def test_project_can_be_created_and_persisted():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='CodePilot Demo', description='Demo project for validation')
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.id is not None
        assert project.name == 'CodePilot Demo'
        assert project.description == 'Demo project for validation'
        assert project.status == 'active'
        assert project.created_at is not None
        assert project.updated_at is not None
        assert isinstance(project.created_at, datetime)
        assert isinstance(project.updated_at, datetime)

        saved = session.query(Project).filter_by(id=project.id).one()
        assert saved.name == 'CodePilot Demo'
        assert saved.status == 'active'
    finally:
        session.close()


def test_project_defaults_status_and_utc_timestamps():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Default Status Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        assert project.status == 'active'
        assert project.created_at.tzinfo is None
        assert project.updated_at.tzinfo is None
        assert project.created_at <= project.updated_at
    finally:
        session.close()
