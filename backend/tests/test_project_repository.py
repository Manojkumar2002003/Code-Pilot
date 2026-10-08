from app.database import SessionLocal, init_db
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.schemas.project import ProjectCreate, ProjectStatus, ProjectUpdate


def test_repository_create_persists_project_and_defaults_values():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        created = repo.create(ProjectCreate(name='Repo Project', description='Created through repository'))

        assert created.id is not None
        assert created.name == 'Repo Project'
        assert created.description == 'Created through repository'
        assert created.status == 'active'
        assert created.created_at is not None
        assert created.updated_at is not None

        saved = session.query(Project).filter_by(id=created.id).one()
        assert saved.name == 'Repo Project'
        assert saved.status == 'active'
    finally:
        session.close()


def test_repository_get_by_id_and_list_are_predictable():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        first = repo.create(ProjectCreate(name='Project One', description='First'))
        second = repo.create(ProjectCreate(name='Project Two', description='Second'))

        assert repo.get_by_id(first.id).name == 'Project One'
        assert repo.get_by_id('missing-id') is None

        results = repo.list()
        names = [project.name for project in results]
        assert names[0] == 'Project Two'
        assert names[1] == 'Project One'
        assert len(results) >= 2
    finally:
        session.close()


def test_repository_update_applies_partial_changes_without_overwriting_ignored_fields():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        project = repo.create(ProjectCreate(name='Original Name', description='Original description'))
        before_update = project.updated_at

        updated = repo.update(project, ProjectUpdate(name='Updated Name', status=ProjectStatus.ARCHIVED))

        assert updated.id == project.id
        assert updated.name == 'Updated Name'
        assert updated.description == 'Original description'
        assert updated.status == 'archived'
        assert updated.created_at == project.created_at
        assert updated.updated_at >= before_update
    finally:
        session.close()


def test_repository_delete_removes_entity_and_keeps_other_projects_intact():
    init_db()
    session = SessionLocal()

    try:
        repo = ProjectRepository(session)
        first = repo.create(ProjectCreate(name='Delete Me', description='Delete this'))
        second = repo.create(ProjectCreate(name='Keep Me', description='Keep this'))

        deleted = repo.delete(first)
        assert deleted is True
        assert repo.get_by_id(first.id) is None
        assert repo.get_by_id(second.id).name == 'Keep Me'
    finally:
        session.close()
