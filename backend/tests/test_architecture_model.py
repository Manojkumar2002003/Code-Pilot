from datetime import datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, engine, init_db
from app.models import Architecture, Project


def test_architectures_table_is_created():
    init_db()
    inspector = inspect(SessionLocal().bind)
    assert inspector.has_table('architectures')
    columns = {column['name'] for column in inspector.get_columns('architectures')}
    assert {'id', 'project_id', 'name', 'description', 'content', 'created_at', 'updated_at'}.issubset(columns)


def test_architecture_can_be_created_and_persisted_for_project():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Architecture Model Test Project', description='Project for architecture tests')
        session.add(project)
        session.commit()
        session.refresh(project)

        architecture = Architecture(
            project_id=project.id,
            name='Microservices Blueprint',
            description='Core microservices layout and dependencies.',
            content={
                'style': 'microservices',
                'components': [{'name': 'auth-svc', 'type': 'service'}, {'name': 'gateway', 'type': 'api'}],
            },
        )
        session.add(architecture)
        session.commit()
        session.refresh(architecture)

        assert architecture.id is not None
        assert architecture.project_id == project.id
        assert architecture.name == 'Microservices Blueprint'
        assert architecture.description == 'Core microservices layout and dependencies.'
        assert architecture.content == {
            'style': 'microservices',
            'components': [{'name': 'auth-svc', 'type': 'service'}, {'name': 'gateway', 'type': 'api'}],
        }
        assert isinstance(architecture.created_at, datetime)
        assert isinstance(architecture.updated_at, datetime)

        saved = session.query(Architecture).filter_by(id=architecture.id).one()
        assert saved.name == 'Microservices Blueprint'
        assert saved.content['style'] == 'microservices'
    finally:
        session.close()


def test_architecture_project_relationship_bidirectional():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Relationship Test Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        architecture = Architecture(
            project_id=project.id,
            name='Monolith Architecture',
            description='Modular monolith design.',
        )
        session.add(architecture)
        session.commit()
        session.refresh(architecture)
        session.refresh(project)

        assert architecture.project is not None
        assert architecture.project.id == project.id
        assert project.architecture is not None
        assert project.architecture.id == architecture.id
        assert project.architecture.name == 'Monolith Architecture'
    finally:
        session.close()


def test_architecture_one_to_one_cardinality_enforced():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Cardinality Test Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        arch1 = Architecture(project_id=project.id, name='First Architecture')
        session.add(arch1)
        session.commit()

        arch2 = Architecture(project_id=project.id, name='Second Architecture')
        session.add(arch2)
        with pytest.raises(IntegrityError):
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_architecture_foreign_key_is_enforced_in_sqlite():
    init_db()
    with engine.connect() as connection:
        connection.execute(text('PRAGMA foreign_keys = ON'))

    session = SessionLocal()
    try:
        with pytest.raises(IntegrityError):
            invalid_architecture = Architecture(
                project_id='nonexistent-project-uuid',
                name='Orphan Architecture',
            )
            session.add(invalid_architecture)
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_architecture_updates_updated_at():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Timestamp Architecture Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        architecture = Architecture(project_id=project.id, name='Original Name')
        session.add(architecture)
        session.commit()
        session.refresh(architecture)

        orig_updated_at = architecture.updated_at
        architecture.name = 'Updated Name'
        session.commit()
        session.refresh(architecture)

        assert architecture.updated_at >= orig_updated_at
    finally:
        session.close()


def test_architecture_model_validates_non_empty_name():
    with pytest.raises(ValueError, match="Architecture name cannot be empty"):
        Architecture(project_id='proj-1', name='')

    with pytest.raises(ValueError, match="Architecture name cannot be empty"):
        Architecture(project_id='proj-1', name='   ')
