from datetime import datetime

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal, engine, init_db
from app.models import Project, Task


def test_tasks_table_is_created():
    init_db()
    inspector = inspect(SessionLocal().bind)
    assert inspector.has_table('tasks')
    columns = {column['name'] for column in inspector.get_columns('tasks')}
    assert {'id', 'project_id', 'title', 'description', 'status', 'priority', 'created_at', 'updated_at'}.issubset(columns)


def test_task_can_be_created_and_persisted_for_project():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Task Model Test Project', description='Project for task tests')
        session.add(project)
        session.commit()
        session.refresh(project)

        task = Task(
            project_id=project.id,
            title='Implement Authentication',
            description='Build JWT auth workflow for users.',
            priority='high',
            status='todo',
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.id is not None
        assert task.project_id == project.id
        assert task.title == 'Implement Authentication'
        assert task.description == 'Build JWT auth workflow for users.'
        assert task.priority == 'high'
        assert task.status == 'todo'
        assert isinstance(task.created_at, datetime)
        assert isinstance(task.updated_at, datetime)

        saved = session.query(Task).filter_by(id=task.id).one()
        assert saved.project_id == project.id
        assert saved.title == 'Implement Authentication'
        assert saved.status == 'todo'
    finally:
        session.close()


def test_task_defaults_status_and_priority():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Defaults Task Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        task = Task(
            project_id=project.id,
            title='Default Task Values',
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        assert task.status == 'todo'
        assert task.priority == 'medium'
        assert task.description is None
        assert task.created_at.tzinfo is None
        assert task.updated_at.tzinfo is None
        assert task.created_at <= task.updated_at
    finally:
        session.close()


def test_task_updates_updated_at():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Task Timestamp Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        task = Task(
            project_id=project.id,
            title='Initial Title',
            description='Initial Description',
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        original_updated_at = task.updated_at
        task.title = 'Updated Task Title'
        session.commit()
        session.refresh(task)

        assert task.updated_at >= original_updated_at
    finally:
        session.close()


def test_task_foreign_key_is_enforced_in_sqlite():
    init_db()
    with engine.connect() as connection:
        connection.execute(text('PRAGMA foreign_keys = ON'))

    session = SessionLocal()
    try:
        with pytest.raises((IntegrityError, Exception)):
            invalid_task = Task(
                project_id='nonexistent-project-id',
                title='Orphan Task',
                description='This task should fail due to missing project foreign key.',
            )
            session.add(invalid_task)
            session.commit()
        session.rollback()
    finally:
        session.close()


def test_task_project_relationship_bidirectional():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Relationship Task Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        task1 = Task(project_id=project.id, title='First Project Task')
        task2 = Task(project_id=project.id, title='Second Project Task')
        session.add_all([task1, task2])
        session.commit()
        session.refresh(task1)
        session.refresh(task2)
        session.refresh(project)

        assert task1.project is not None
        assert task1.project.id == project.id
        assert len(project.tasks) >= 2
        task_ids = [t.id for t in project.tasks]
        assert task1.id in task_ids
        assert task2.id in task_ids
    finally:
        session.close()


def test_project_cascade_deletes_tasks():
    init_db()
    session = SessionLocal()

    try:
        project = Project(name='Cascade Delete Project')
        session.add(project)
        session.commit()
        session.refresh(project)

        task = Task(project_id=project.id, title='Cascade Target Task')
        session.add(task)
        session.commit()
        task_id = task.id

        session.delete(project)
        session.commit()

        assert session.get(Task, task_id) is None
    finally:
        session.close()


def test_task_model_validates_non_empty_title():
    with pytest.raises(ValueError, match="Task title cannot be empty"):
        Task(project_id='p-1', title='')

    with pytest.raises(ValueError, match="Task title cannot be empty"):
        Task(project_id='p-1', title='   ')


def test_task_model_validates_status_and_priority():
    with pytest.raises(ValueError, match="Task status must be one of"):
        Task(project_id='p-1', title='Valid Title', status='invalid_status')

    with pytest.raises(ValueError, match="Task priority must be one of"):
        Task(project_id='p-1', title='Valid Title', priority='urgent')


def test_task_repr():
    task = Task(id='task-uuid', project_id='proj-uuid', title='Repr Task')
    assert repr(task) == "Task(id='task-uuid', title='Repr Task', project_id='proj-uuid')"
