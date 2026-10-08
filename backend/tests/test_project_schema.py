from datetime import datetime

import pytest
from pydantic import ValidationError

from app.database import SessionLocal, init_db
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectStatus, ProjectUpdate


def test_valid_create_schema_normalizes_input():
    payload = {
        'name': '  CodePilot Demo  ',
        'description': '  AI software engineering project  ',
    }
    project = ProjectCreate.model_validate(payload)

    assert project.name == 'CodePilot Demo'
    assert project.description == 'AI software engineering project'


def test_create_schema_rejects_missing_empty_or_blank_name():
    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({'description': 'Test project'})

    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({'name': ''})

    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({'name': '   '})


def test_create_schema_rejects_invalid_name_length_and_invalid_description_length():
    long_name = 'x' * 101
    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({'name': long_name})

    long_description = 'x' * 2001
    with pytest.raises(ValidationError):
        ProjectCreate.model_validate({'name': 'Test', 'description': long_description})


def test_description_allows_none_and_trims_whitespace():
    cleared = ProjectCreate.model_validate({'name': 'Example', 'description': '   '})
    assert cleared.description is None

    explicit_none = ProjectCreate.model_validate({'name': 'Example', 'description': None})
    assert explicit_none.description is None


def test_status_enum_accepts_valid_values_and_rejects_invalid_values():
    assert ProjectStatus('active') == ProjectStatus.ACTIVE
    assert ProjectStatus('archived') == ProjectStatus.ARCHIVED

    with pytest.raises(ValueError):
        ProjectStatus('deleted')


def test_update_schema_allows_partial_updates_and_rejects_empty_payload():
    assert ProjectUpdate.model_validate({'name': 'New Name'}).name == 'New Name'
    assert ProjectUpdate.model_validate({'description': 'New Description'}).description == 'New Description'
    assert ProjectUpdate.model_validate({'status': 'archived'}).status == ProjectStatus.ARCHIVED

    with pytest.raises(ValidationError):
        ProjectUpdate.model_validate({})


def test_project_response_model_validates_sqlalchemy_instance():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Schema Response Project', description='Project for schema serialization')
        session.add(project)
        session.commit()
        session.refresh(project)

        response = ProjectResponse.model_validate(project)
        assert response.id == project.id
        assert response.name == 'Schema Response Project'
        assert response.description == 'Project for schema serialization'
        assert response.status == ProjectStatus.ACTIVE
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)
    finally:
        session.close()
