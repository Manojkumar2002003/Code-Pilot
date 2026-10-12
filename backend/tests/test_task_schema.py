from datetime import datetime

import pytest
from pydantic import ValidationError

from app.models import Project, Task
from app.schemas.task import (
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskUpdate,
)


def test_valid_task_create_schema_normalizes_and_validates():
    payload = {
        'title': '  Set up database migrations  ',
        'description': '  Configure Alembic and base models.  ',
        'priority': 'high',
        'status': 'todo',
    }

    task = TaskCreate.model_validate(payload)
    assert task.title == 'Set up database migrations'
    assert task.description == 'Configure Alembic and base models.'
    assert task.priority == TaskPriority.HIGH
    assert task.status == TaskStatus.TODO


def test_task_create_schema_applies_defaults_when_optional_omitted():
    task = TaskCreate.model_validate({'title': 'Minimal Task'})
    assert task.title == 'Minimal Task'
    assert task.description is None
    assert task.priority == TaskPriority.MEDIUM
    assert task.status == TaskStatus.TODO


def test_task_schema_rejects_empty_or_whitespace_title():
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': ''})

    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': '    '})


def test_task_schema_rejects_overlong_title_and_description():
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'x' * 256})

    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'Valid Title', 'description': 'x' * 5001})


def test_task_status_and_priority_enums_are_validated():
    assert TaskStatus('todo') == TaskStatus.TODO
    assert TaskStatus('in_progress') == TaskStatus.IN_PROGRESS
    assert TaskStatus('completed') == TaskStatus.COMPLETED
    assert TaskStatus('blocked') == TaskStatus.BLOCKED
    assert TaskStatus('cancelled') == TaskStatus.CANCELLED

    assert TaskPriority('low') == TaskPriority.LOW
    assert TaskPriority('medium') == TaskPriority.MEDIUM
    assert TaskPriority('high') == TaskPriority.HIGH
    assert TaskPriority('critical') == TaskPriority.CRITICAL

    with pytest.raises(ValueError):
        TaskStatus('agent_running')

    with pytest.raises(ValueError):
        TaskStatus('awaiting_review')

    with pytest.raises(ValueError):
        TaskPriority('urgent')

    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'Invalid status', 'status': 'unknown_status'})

    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'Invalid priority', 'priority': 'extreme'})


def test_task_schema_rejects_server_managed_fields_on_create():
    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'Test Task', 'id': 'custom-id'})

    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'Test Task', 'project_id': 'proj-123'})

    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'Test Task', 'created_at': datetime.now()})

    with pytest.raises(ValidationError):
        TaskCreate.model_validate({'title': 'Test Task', 'updated_at': datetime.now()})


def test_task_update_schema_allows_partial_updates():
    update_title = TaskUpdate.model_validate({'title': 'Renamed Task'})
    assert update_title.title == 'Renamed Task'
    assert update_title.description is None
    assert update_title.status is None
    assert update_title.priority is None

    update_status = TaskUpdate.model_validate({'status': 'in_progress'})
    assert update_status.title is None
    assert update_status.status == TaskStatus.IN_PROGRESS

    update_priority = TaskUpdate.model_validate({'priority': 'critical'})
    assert update_priority.priority == TaskPriority.CRITICAL

    update_desc = TaskUpdate.model_validate({'description': 'New details'})
    assert update_desc.description == 'New details'


def test_task_update_schema_rejects_empty_payload_and_immutable_fields():
    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({})

    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({'id': 'cannot-modify-id'})

    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({'project_id': 'cannot-modify-project'})

    with pytest.raises(ValidationError):
        TaskUpdate.model_validate({'created_at': datetime.now()})


def test_task_response_model_serializes_sqlalchemy_instance():
    project = Project(id='proj-test-1', name='Schema Response Project')
    task = Task(
        id='task-test-1',
        project_id=project.id,
        title='Response Schema Verification',
        description='Ensure Pydantic from_attributes correctly serializes Task ORM.',
        priority='high',
        status='in_progress',
    )

    response = TaskResponse.model_validate(task)
    assert response.id == 'task-test-1'
    assert response.project_id == 'proj-test-1'
    assert response.title == 'Response Schema Verification'
    assert response.description == 'Ensure Pydantic from_attributes correctly serializes Task ORM.'
    assert response.priority == TaskPriority.HIGH
    assert response.status == TaskStatus.IN_PROGRESS
    assert isinstance(response.created_at, datetime)
    assert isinstance(response.updated_at, datetime)
