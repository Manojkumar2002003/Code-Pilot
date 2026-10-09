from datetime import datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, text

from app.database import SessionLocal, engine, init_db
from app.models import Project, Requirement
from app.schemas.requirement import (
    RequirementCreate,
    RequirementPriority,
    RequirementResponse,
    RequirementStatus,
    RequirementType,
    RequirementUpdate,
)


def test_requirements_table_is_created():
    init_db()
    inspector = inspect(SessionLocal().bind)
    assert inspector.has_table('requirements')
    columns = {column['name'] for column in inspector.get_columns('requirements')}
    assert {'id', 'project_id', 'title', 'description', 'type', 'priority', 'status', 'created_at', 'updated_at'}.issubset(columns)


def test_requirement_can_be_created_and_persisted_for_project():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Requirement Demo Project', description='Project for requirement tests')
        session.add(project)
        session.commit()
        session.refresh(project)

        requirement = Requirement(
            project_id=project.id,
            title='  User can sign in  ',
            description='Users can sign in with valid credentials.',
            type='functional',
            priority='high',
        )
        session.add(requirement)
        session.commit()
        session.refresh(requirement)

        assert requirement.id is not None
        assert requirement.project_id == project.id
        assert requirement.title == 'User can sign in'
        assert requirement.description == 'Users can sign in with valid credentials.'
        assert requirement.type == 'functional'
        assert requirement.priority == 'high'
        assert requirement.status == 'draft'
        assert isinstance(requirement.created_at, datetime)
        assert isinstance(requirement.updated_at, datetime)

        saved = session.query(Requirement).filter_by(id=requirement.id).one()
        assert saved.project_id == project.id
        assert saved.status == 'draft'
    finally:
        session.close()


def test_requirement_updates_updated_at():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Requirement Timestamp Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        requirement = Requirement(
            project_id=project.id,
            title='Project timeline',
            description='Project timeline description.',
            type='functional',
            priority='medium',
        )
        session.add(requirement)
        session.commit()
        session.refresh(requirement)

        original_updated_at = requirement.updated_at
        requirement.title = 'Updated requirement title'
        session.commit()
        session.refresh(requirement)

        assert requirement.updated_at >= original_updated_at
    finally:
        session.close()


def test_requirement_foreign_key_is_enforced_in_sqlite():
    init_db()
    with engine.connect() as connection:
        connection.execute(text('PRAGMA foreign_keys = ON'))

    session = SessionLocal()
    try:
        with pytest.raises(Exception):
            invalid_requirement = Requirement(
                project_id='missing-project',
                title='Broken requirement',
                description='This should fail because the project does not exist.',
                type='functional',
                priority='low',
            )
            session.add(invalid_requirement)
            session.commit()
    finally:
        session.close()


def test_valid_requirement_create_schema_normalizes_and_validates():
    payload = {
        'title': '  User can download data  ',
        'description': '  Users can export the project data in CSV format.  ',
        'type': 'functional',
        'priority': 'high',
    }

    requirement = RequirementCreate.model_validate(payload)

    assert requirement.title == 'User can download data'
    assert requirement.description == 'Users can export the project data in CSV format.'
    assert requirement.type == RequirementType.FUNCTIONAL
    assert requirement.priority == RequirementPriority.HIGH


def test_requirement_schema_rejects_empty_title_and_invalid_values():
    with pytest.raises(ValidationError):
        RequirementCreate.model_validate({'title': '', 'description': 'Body', 'type': 'functional', 'priority': 'high'})

    with pytest.raises(ValidationError):
        RequirementCreate.model_validate({'title': '   ', 'description': 'Body', 'type': 'functional', 'priority': 'high'})

    with pytest.raises(ValidationError):
        RequirementCreate.model_validate({'title': 'Fake', 'description': 'Body', 'type': 'unknown', 'priority': 'high'})

    with pytest.raises(ValidationError):
        RequirementCreate.model_validate({'title': 'Fake', 'description': 'Body', 'type': 'functional', 'priority': 'urgent'})


def test_requirement_update_schema_allows_partial_updates_and_rejects_immutable_fields():
    updated = RequirementUpdate.model_validate({'title': 'Renamed requirement', 'status': 'approved'})
    assert updated.title == 'Renamed requirement'
    assert updated.status == RequirementStatus.APPROVED

    with pytest.raises(ValidationError):
        RequirementUpdate.model_validate({'id': 'abc123'})

    with pytest.raises(ValidationError):
        RequirementUpdate.model_validate({'project_id': 'project-id'})

    with pytest.raises(ValidationError):
        RequirementUpdate.model_validate({})


def test_requirement_response_model_validates_sqlalchemy_instance():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Schema Response Requirement Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        requirement = Requirement(
            project_id=project.id,
            title='Requirement response schema',
            description='This requirement validates the response schema layer.',
            type='non_functional',
            priority='critical',
            status='approved',
        )
        session.add(requirement)
        session.commit()
        session.refresh(requirement)

        response = RequirementResponse.model_validate(requirement)
        assert response.id == requirement.id
        assert response.project_id == project.id
        assert response.title == 'Requirement response schema'
        assert response.description == 'This requirement validates the response schema layer.'
        assert response.type == RequirementType.NON_FUNCTIONAL
        assert response.priority == RequirementPriority.CRITICAL
        assert response.status == RequirementStatus.APPROVED
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)
    finally:
        session.close()
