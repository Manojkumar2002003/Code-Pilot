import pytest

from app.database import SessionLocal, init_db
from app.models import Project
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate
from app.services.project import ProjectNotFoundError
from app.services.task import (
    TaskNotFoundError,
    TaskProjectMismatchError,
    TaskService,
)


def _create_project(session, name='Service Project Alpha') -> Project:
    project = Project(name=name, description='Project for service tests')
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture
def service_setup():
    init_db()
    session = SessionLocal()
    try:
        project_repo = ProjectRepository(session)
        task_repo = TaskRepository(session)
        service = TaskService(task_repo, project_repo)
        yield session, service
    finally:
        session.close()


def test_task_service_create_and_list_for_existing_project(service_setup):
    session, service = service_setup
    project = _create_project(session, 'Task Service Project')

    created = service.create_task(project.id, TaskCreate(
        title='Design Database Schema',
        description='Create ER diagrams and models.',
        priority=TaskPriority.HIGH,
        status=TaskStatus.TODO,
    ))

    assert created.id is not None
    assert created.project_id == project.id
    assert created.title == 'Design Database Schema'
    assert created.description == 'Create ER diagrams and models.'
    assert created.priority == 'high'
    assert created.status == 'todo'

    tasks = service.list_tasks(project.id)
    assert len(tasks) == 1
    assert tasks[0].id == created.id


def test_task_service_rejects_missing_project(service_setup):
    _, service = service_setup

    with pytest.raises(ProjectNotFoundError):
        service.create_task('nonexistent-project-id', TaskCreate(title='Should fail'))

    with pytest.raises(ProjectNotFoundError):
        service.list_tasks('nonexistent-project-id')

    with pytest.raises(ProjectNotFoundError):
        service.get_task('nonexistent-project-id', 'some-task-id')

    with pytest.raises(ProjectNotFoundError):
        service.update_task('nonexistent-project-id', 'some-task-id', TaskUpdate(title='New Title'))

    with pytest.raises(ProjectNotFoundError):
        service.delete_task('nonexistent-project-id', 'some-task-id')


def test_task_service_rejects_missing_task(service_setup):
    session, service = service_setup
    project = _create_project(session, 'Project Missing Task')

    with pytest.raises(TaskNotFoundError):
        service.get_task(project.id, 'missing-task-id')

    with pytest.raises(TaskNotFoundError):
        service.update_task(project.id, 'missing-task-id', TaskUpdate(title='Updated'))

    with pytest.raises(TaskNotFoundError):
        service.delete_task(project.id, 'missing-task-id')


def test_task_service_rejects_cross_project_access(service_setup):
    session, service = service_setup
    project_a = _create_project(session, 'Project Alpha')
    project_b = _create_project(session, 'Project Beta')

    task_a = service.create_task(project_a.id, TaskCreate(title='Task belonging to A'))

    with pytest.raises(TaskProjectMismatchError):
        service.get_task(project_b.id, task_a.id)

    with pytest.raises(TaskProjectMismatchError):
        service.update_task(project_b.id, task_a.id, TaskUpdate(title='Illegal update'))

    with pytest.raises(TaskProjectMismatchError):
        service.delete_task(project_b.id, task_a.id)


def test_task_service_update_and_delete_in_project_context(service_setup):
    session, service = service_setup
    project = _create_project(session, 'CRUD Context Project')

    task = service.create_task(project.id, TaskCreate(
        title='Original Task Name',
        description='Original details',
        priority=TaskPriority.LOW,
        status=TaskStatus.TODO,
    ))

    # Partial update: modify status and priority, leave title and description intact
    updated = service.update_task(project.id, task.id, TaskUpdate(
        status=TaskStatus.IN_PROGRESS,
        priority=TaskPriority.CRITICAL,
    ))
    assert updated.title == 'Original Task Name'
    assert updated.description == 'Original details'
    assert updated.status == 'in_progress'
    assert updated.priority == 'critical'

    # Retrieve to confirm persistence
    fetched = service.get_task(project.id, task.id)
    assert fetched.status == 'in_progress'
    assert fetched.priority == 'critical'

    # Delete within project context
    deleted = service.delete_task(project.id, task.id)
    assert deleted is True

    # Confirm deletion
    with pytest.raises(TaskNotFoundError):
        service.get_task(project.id, task.id)
