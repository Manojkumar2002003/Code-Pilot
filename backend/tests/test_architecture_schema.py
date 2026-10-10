from datetime import datetime

import pytest
from pydantic import ValidationError

from app.database import SessionLocal, init_db
from app.models import Architecture, Project
from app.schemas.architecture import (
    ArchitectureCreate,
    ArchitectureResponse,
    ArchitectureUpdate,
)


def test_valid_architecture_create_schema_normalizes_and_validates():
    payload = {
        'name': '  Event-Driven Architecture  ',
        'description': '  Decoupled event streaming architecture.  ',
        'content': {'broker': 'kafka', 'topics': ['events', 'audit']},
    }

    schema = ArchitectureCreate.model_validate(payload)
    assert schema.name == 'Event-Driven Architecture'
    assert schema.description == 'Decoupled event streaming architecture.'
    assert schema.content == {'broker': 'kafka', 'topics': ['events', 'audit']}


def test_architecture_schema_rejects_empty_name():
    with pytest.raises(ValidationError):
        ArchitectureCreate.model_validate({'name': ''})

    with pytest.raises(ValidationError):
        ArchitectureCreate.model_validate({'name': '   '})


def test_architecture_schema_rejects_server_managed_fields_on_create():
    with pytest.raises(ValidationError):
        ArchitectureCreate.model_validate({'name': 'Valid Name', 'id': 'custom-id'})

    with pytest.raises(ValidationError):
        ArchitectureCreate.model_validate({'name': 'Valid Name', 'project_id': 'proj-123'})

    with pytest.raises(ValidationError):
        ArchitectureCreate.model_validate({'name': 'Valid Name', 'created_at': datetime.now()})


def test_architecture_update_schema_allows_partial_updates():
    update1 = ArchitectureUpdate.model_validate({'name': 'New Architecture Name'})
    assert update1.name == 'New Architecture Name'
    assert update1.description is None
    assert update1.content is None

    update2 = ArchitectureUpdate.model_validate({'content': {'pattern': 'CQRS'}})
    assert update2.name is None
    assert update2.content == {'pattern': 'CQRS'}

    update3 = ArchitectureUpdate.model_validate({'description': 'Updated description'})
    assert update3.description == 'Updated description'


def test_architecture_update_schema_rejects_empty_and_immutable_fields():
    with pytest.raises(ValidationError):
        ArchitectureUpdate.model_validate({})

    with pytest.raises(ValidationError):
        ArchitectureUpdate.model_validate({'id': 'cannot-change-id'})

    with pytest.raises(ValidationError):
        ArchitectureUpdate.model_validate({'project_id': 'cannot-change-project'})


def test_architecture_response_model_validates_sqlalchemy_instance():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Schema Response Arch Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        architecture = Architecture(
            project_id=project.id,
            name='Cloud Native Blueprint',
            description='Kubernetes-based deployment architecture.',
            content={'infrastructure': 'k8s', 'replicas': 3},
        )
        session.add(architecture)
        session.commit()
        session.refresh(architecture)

        response = ArchitectureResponse.model_validate(architecture)
        assert response.id == architecture.id
        assert response.project_id == project.id
        assert response.name == 'Cloud Native Blueprint'
        assert response.description == 'Kubernetes-based deployment architecture.'
        assert response.content == {'infrastructure': 'k8s', 'replicas': 3}
        assert isinstance(response.created_at, datetime)
        assert isinstance(response.updated_at, datetime)
    finally:
        session.close()
