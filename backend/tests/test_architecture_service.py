import pytest

from app.database import SessionLocal, init_db
from app.models import Project
from app.repositories.architecture import ArchitectureRepository
from app.repositories.project import ProjectRepository
from app.schemas.architecture import ArchitectureCreate, ArchitectureUpdate
from app.services.architecture import (
    ArchitectureAlreadyExistsError,
    ArchitectureNotFoundError,
    ArchitectureProjectMismatchError,
    ArchitectureService,
)
from app.services.project import ProjectNotFoundError


def _create_project(session, name='Arch Service Project') -> Project:
    project = Project(name=name, description='Project for architecture service test')
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def test_architecture_service_create_and_get():
    init_db()
    session = SessionLocal()
    try:
        project = _create_project(session, 'Service Test Project')
        project_repo = ProjectRepository(session)
        arch_repo = ArchitectureRepository(session)
        service = ArchitectureService(arch_repo, project_repo)

        created = service.create_architecture(project.id, ArchitectureCreate(
            name='Clean Architecture',
            description='Domain-driven clean architecture.',
            content={'pattern': 'clean-architecture'},
        ))

        assert created.project_id == project.id
        assert created.name == 'Clean Architecture'

        by_project = service.get_architecture_by_project(project.id)
        assert by_project.id == created.id

        by_id = service.get_architecture(project.id, created.id)
        assert by_id.id == created.id
    finally:
        session.close()


def test_architecture_service_rejects_missing_project():
    init_db()
    session = SessionLocal()
    try:
        project_repo = ProjectRepository(session)
        arch_repo = ArchitectureRepository(session)
        service = ArchitectureService(arch_repo, project_repo)

        with pytest.raises(ProjectNotFoundError):
            service.create_architecture('nonexistent-project-id', ArchitectureCreate(name='Fail'))

        with pytest.raises(ProjectNotFoundError):
            service.get_architecture_by_project('nonexistent-project-id')
    finally:
        session.close()


def test_architecture_service_enforces_one_architecture_per_project():
    init_db()
    session = SessionLocal()
    try:
        project = _create_project(session, 'Single Arch Project')
        project_repo = ProjectRepository(session)
        arch_repo = ArchitectureRepository(session)
        service = ArchitectureService(arch_repo, project_repo)

        service.create_architecture(project.id, ArchitectureCreate(name='First'))

        with pytest.raises(ArchitectureAlreadyExistsError):
            service.create_architecture(project.id, ArchitectureCreate(name='Second'))
    finally:
        session.close()


def test_architecture_service_rejects_mismatched_project_access():
    init_db()
    session = SessionLocal()
    try:
        project_1 = _create_project(session, 'Project Alpha')
        project_2 = _create_project(session, 'Project Beta')
        project_repo = ProjectRepository(session)
        arch_repo = ArchitectureRepository(session)
        service = ArchitectureService(arch_repo, project_repo)

        arch_1 = service.create_architecture(project_1.id, ArchitectureCreate(name='Alpha Arch'))

        with pytest.raises(ArchitectureProjectMismatchError):
            service.get_architecture(project_2.id, arch_1.id)

        with pytest.raises(ArchitectureProjectMismatchError):
            service.update_architecture(project_2.id, arch_1.id, ArchitectureUpdate(name='Hacked'))

        with pytest.raises(ArchitectureProjectMismatchError):
            service.delete_architecture(project_2.id, arch_1.id)
    finally:
        session.close()


def test_architecture_service_handles_missing_architecture():
    init_db()
    session = SessionLocal()
    try:
        project = _create_project(session, 'Empty Arch Project')
        project_repo = ProjectRepository(session)
        arch_repo = ArchitectureRepository(session)
        service = ArchitectureService(arch_repo, project_repo)

        with pytest.raises(ArchitectureNotFoundError):
            service.get_architecture_by_project(project.id)

        with pytest.raises(ArchitectureNotFoundError):
            service.get_architecture(project.id, 'missing-arch-id')
    finally:
        session.close()


def test_architecture_service_update_and_delete():
    init_db()
    session = SessionLocal()
    try:
        project = _create_project(session, 'Update Delete Arch Project')
        project_repo = ProjectRepository(session)
        arch_repo = ArchitectureRepository(session)
        service = ArchitectureService(arch_repo, project_repo)

        arch = service.create_architecture(project.id, ArchitectureCreate(
            name='Initial Architecture',
            description='Initial Description',
        ))

        updated = service.update_architecture(project.id, arch.id, ArchitectureUpdate(
            name='Modified Architecture',
            content={'diagram': 'c4-model'},
        ))
        assert updated.name == 'Modified Architecture'
        assert updated.description == 'Initial Description'
        assert updated.content == {'diagram': 'c4-model'}

        assert service.delete_architecture(project.id, arch.id) is True

        with pytest.raises(ArchitectureNotFoundError):
            service.get_architecture_by_project(project.id)
    finally:
        session.close()
