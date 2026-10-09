from datetime import datetime

import pytest

from app.database import SessionLocal, init_db
from app.models import Project, Requirement
from app.repositories.requirement import RequirementRepository
from app.schemas.requirement import RequirementCreate, RequirementUpdate


def _create_project(session, name='Project Alpha') -> Project:
    project = Project(name=name, description='Test project')
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
    return RequirementRepository(repo_session)


def test_requirement_repository_create_and_persist_requirement(repository, repo_session):
    project = _create_project(repo_session)

    created = repository.create(project.id, RequirementCreate(
        title='User can edit profile',
        description='Users can update their profile details.',
        type='functional',
        priority='high',
    ))

    assert created.id is not None
    assert created.project_id == project.id
    assert created.status == 'draft'
    assert isinstance(created.created_at, datetime)
    assert isinstance(created.updated_at, datetime)


def test_requirement_repository_list_by_project_and_empty_collection(repository, repo_session):
    project_a = _create_project(repo_session, 'Project A')
    project_b = _create_project(repo_session, 'Project B')

    repository.create(project_a.id, RequirementCreate(title='Alpha one', description='Alpha description', type='functional', priority='medium'))
    repository.create(project_b.id, RequirementCreate(title='Beta one', description='Beta description', type='functional', priority='low'))

    project_a_requirements = repository.list_by_project(project_a.id)
    project_b_requirements = repository.list_by_project(project_b.id)

    assert [item.title for item in project_a_requirements] == ['Alpha one']
    assert [item.title for item in project_b_requirements] == ['Beta one']

    empty = repository.list_by_project('missing-project-id')
    assert empty == []


def test_requirement_repository_updates_only_supplied_fields_and_delete_requirement(repository, repo_session):
    project = _create_project(repo_session)
    requirement = repository.create(project.id, RequirementCreate(
        title='Original requirement',
        description='Initial description.',
        type='functional',
        priority='medium',
    ))

    updated = repository.update(requirement, RequirementUpdate(status='approved'))
    assert updated.title == 'Original requirement'
    assert updated.description == 'Initial description.'
    assert updated.status == 'approved'

    deleted = repository.delete(requirement)
    assert deleted is True
    assert repository.get_by_id(requirement.id) is None

    with pytest.raises(ValueError):
        repository.delete(Requirement(id='missing-id', project_id=project.id, title='Nope', description='Nope', type='functional', priority='low'))
