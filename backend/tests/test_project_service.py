from app.database import SessionLocal, init_db
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectStatus, ProjectUpdate
from app.services.project import ProjectNotFoundError, ProjectService


def test_service_create_project_persists_and_returns_project():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        service = ProjectService(repo)

        project = service.create_project(ProjectCreate(name='Service Project', description='Created by service'))

        assert project.id is not None
        assert project.name == 'Service Project'
        assert project.description == 'Created by service'
        assert project.status == 'active'
    finally:
        session.close()


def test_service_get_project_returns_entity_or_raises_not_found():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        service = ProjectService(repo)
        created = service.create_project(ProjectCreate(name='Lookup Project'))

        assert service.get_project(created.id).name == 'Lookup Project'

        try:
            service.get_project('missing-id')
            assert False, 'expected ProjectNotFoundError'
        except ProjectNotFoundError:
            pass
    finally:
        session.close()


def test_service_list_projects_returns_all_projects_in_descending_created_order():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        service = ProjectService(repo)

        service.create_project(ProjectCreate(name='Alpha'))
        service.create_project(ProjectCreate(name='Beta'))

        projects = service.list_projects()
        assert [project.name for project in projects[:2]] == ['Beta', 'Alpha']
    finally:
        session.close()


def test_service_update_project_applies_partial_changes():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        service = ProjectService(repo)

        project = service.create_project(ProjectCreate(name='Old Name', description='Old'))
        updated = service.update_project(project.id, ProjectUpdate(name='New Name', status=ProjectStatus.ARCHIVED))

        assert updated.name == 'New Name'
        assert updated.description == 'Old'
        assert updated.status == 'archived'
    finally:
        session.close()


def test_service_delete_project_removes_entity_and_raises_for_missing_project():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        service = ProjectService(repo)

        project = service.create_project(ProjectCreate(name='Delete Me'))
        assert service.delete_project(project.id) is True

        try:
            service.delete_project('missing-id')
            assert False, 'expected ProjectNotFoundError'
        except ProjectNotFoundError:
            pass
    finally:
        session.close()
