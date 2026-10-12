from datetime import datetime

import pytest

from app.database import SessionLocal, init_db
from app.models import Project, Task
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate


def _create_project(session, name='Project Alpha') -> Project:
    project = Project(name=name, description='Test project for task repo')
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def repo_session():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def repository(repo_session):
    return TaskRepository(repo_session)


def test_task_repository_create_and_retrieve_by_id(repository, repo_session):
    project = _create_project(repo_session, 'Task Repo Project')

    created = repository.create(project.id, TaskCreate(
        title='Implement API endpoint',
        description='Create GET and POST routes.',
        priority=TaskPriority.HIGH,
        status=TaskStatus.TODO,
    ))

    assert created.id is not None
    assert created.project_id == project.id
    assert created.title == 'Implement API endpoint'
    assert created.description == 'Create GET and POST routes.'
    assert created.priority == 'high'
    assert created.status == 'todo'
    assert isinstance(created.created_at, datetime)
    assert isinstance(created.updated_at, datetime)

    retrieved = repository.get_by_id(created.id)
    assert retrieved is not None
    assert retrieved.id == created.id
    assert retrieved.title == 'Implement API endpoint'


def test_task_repository_get_by_id_returns_none_for_missing(repository):
    assert repository.get_by_id('nonexistent-task-id') is None


def test_task_repository_list_by_project_and_isolates_projects(repository, repo_session):
    project_a = _create_project(repo_session, 'Project One')
    project_b = _create_project(repo_session, 'Project Two')

    task_a = repository.create(project_a.id, TaskCreate(title='Task for Project A'))
    task_b = repository.create(project_b.id, TaskCreate(title='Task for Project B'))

    list_a = repository.list_by_project(project_a.id)
    list_b = repository.list_by_project(project_b.id)

    assert [t.id for t in list_a] == [task_a.id]
    assert [t.id for t in list_b] == [task_b.id]

    empty_list = repository.list_by_project('nonexistent-project-id')
    assert empty_list == []


def test_task_repository_updates_only_supplied_fields(repository, repo_session):
    project = _create_project(repo_session, 'Update Test Project')
    task = repository.create(project.id, TaskCreate(
        title='Initial Title',
        description='Initial Details',
        priority=TaskPriority.LOW,
        status=TaskStatus.TODO,
    ))
    initial_updated_at = task.updated_at

    updated = repository.update(task, TaskUpdate(
        status=TaskStatus.IN_PROGRESS,
    ))

    assert updated.title == 'Initial Title'
    assert updated.description == 'Initial Details'
    assert updated.priority == 'low'
    assert updated.status == 'in_progress'
    assert updated.updated_at >= initial_updated_at

    updated2 = repository.update(task, TaskUpdate(
        title='New Title',
        priority=TaskPriority.CRITICAL,
    ))

    assert updated2.title == 'New Title'
    assert updated2.description == 'Initial Details'
    assert updated2.status == 'in_progress'
    assert updated2.priority == 'critical'


def test_task_repository_delete_task(repository, repo_session):
    project = _create_project(repo_session, 'Delete Test Project')
    task = repository.create(project.id, TaskCreate(title='Task to Delete'))

    deleted = repository.delete(task)
    assert deleted is True
    assert repository.get_by_id(task.id) is None

    with pytest.raises(ValueError, match="Task with id .* was not found"):
        repository.delete(Task(id='nonexistent-id', project_id=project.id, title='Ghost'))

    with pytest.raises(ValueError, match="Task cannot be None"):
        repository.delete(None)
