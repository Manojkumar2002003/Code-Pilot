from datetime import datetime

import pytest

from app.database import SessionLocal, init_db
from app.models import Architecture, Project
from app.repositories.architecture import ArchitectureRepository
from app.schemas.architecture import ArchitectureCreate, ArchitectureUpdate


def _create_project(session, name='Arch Repo Project') -> Project:
    project = Project(name=name, description='Test project for architecture repo')
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
    return ArchitectureRepository(repo_session)


def test_architecture_repository_create_and_get_by_id(repository, repo_session):
    project = _create_project(repo_session)

    created = repository.create(project.id, ArchitectureCreate(
        name='Hexagonal Architecture',
        description='Ports and adapters architectural style.',
        content={'style': 'hexagonal', 'layers': ['core', 'adapters']},
    ))

    assert created.id is not None
    assert created.project_id == project.id
    assert created.name == 'Hexagonal Architecture'
    assert created.description == 'Ports and adapters architectural style.'
    assert created.content == {'style': 'hexagonal', 'layers': ['core', 'adapters']}
    assert isinstance(created.created_at, datetime)
    assert isinstance(created.updated_at, datetime)

    fetched = repository.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == 'Hexagonal Architecture'


def test_architecture_repository_get_by_project_id(repository, repo_session):
    project_1 = _create_project(repo_session, 'Project 1')
    project_2 = _create_project(repo_session, 'Project 2')

    arch_1 = repository.create(project_1.id, ArchitectureCreate(
        name='Arch 1',
        description='Project 1 architecture',
    ))

    result_1 = repository.get_by_project_id(project_1.id)
    assert result_1 is not None
    assert result_1.id == arch_1.id
    assert result_1.name == 'Arch 1'

    result_2 = repository.get_by_project_id(project_2.id)
    assert result_2 is None

    nonexistent = repository.get_by_project_id('nonexistent-project-id')
    assert nonexistent is None


def test_architecture_repository_update_partial_fields(repository, repo_session):
    project = _create_project(repo_session)

    created = repository.create(project.id, ArchitectureCreate(
        name='Initial Name',
        description='Initial description.',
        content={'v': 1},
    ))

    updated = repository.update(created, ArchitectureUpdate(
        name='Updated Name',
        content={'v': 2, 'features': ['auth']},
    ))

    assert updated.name == 'Updated Name'
    assert updated.description == 'Initial description.'
    assert updated.content == {'v': 2, 'features': ['auth']}


def test_architecture_repository_delete(repository, repo_session):
    project = _create_project(repo_session)

    created = repository.create(project.id, ArchitectureCreate(
        name='To be deleted',
    ))

    deleted = repository.delete(created)
    assert deleted is True

    assert repository.get_by_id(created.id) is None
    assert repository.get_by_project_id(project.id) is None

    with pytest.raises(ValueError, match="was not found"):
        fake_arch = Architecture(id='missing-uuid', project_id=project.id, name='Ghost')
        repository.delete(fake_arch)
