from app.database import SessionLocal, init_db
from app.models import Project
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.requirement import RequirementCreate, RequirementUpdate
from app.services.project import ProjectNotFoundError
from app.services.requirement import RequirementNotFoundError, RequirementProjectMismatchError, RequirementService


def _create_project(session, name='Project Alpha') -> Project:
    project = Project(name=name, description='Test project')
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


def test_requirement_service_create_and_list_for_existing_project():
    init_db()
    session = SessionLocal()
    try:
        project = _create_project(session, 'Service Project')
        project_repository = ProjectRepository(session)
        requirement_repository = RequirementRepository(session)
        service = RequirementService(requirement_repository, project_repository)

        created = service.create_requirement(project.id, RequirementCreate(
            title='Service requirement',
            description='Service requirement description.',
            type='functional',
            priority='high',
        ))

        assert created.project_id == project.id
        assert created.title == 'Service requirement'

        listed = service.list_requirements(project.id)
        assert [item.id for item in listed] == [created.id]
    finally:
        session.close()


def test_requirement_service_rejects_missing_project_and_wrong_requirements():
    init_db()
    session = SessionLocal()
    try:
        project_a = _create_project(session, 'Alpha')
        project_b = _create_project(session, 'Beta')
        project_repository = ProjectRepository(session)
        requirement_repository = RequirementRepository(session)
        service = RequirementService(requirement_repository, project_repository)

        try:
            service.create_requirement('missing-project', RequirementCreate(title='Bad', description='Bad', type='functional', priority='low'))
            assert False, 'Expected ProjectNotFoundError'
        except ProjectNotFoundError:
            pass

        req = service.create_requirement(project_a.id, RequirementCreate(title='A requirement', description='Req desc', type='functional', priority='medium'))

        try:
            service.get_requirement(project_b.id, req.id)
            assert False, 'Expected RequirementProjectMismatchError'
        except RequirementProjectMismatchError:
            pass

        try:
            service.get_requirement(project_a.id, 'missing-id')
            assert False, 'Expected RequirementNotFoundError'
        except RequirementNotFoundError:
            pass
    finally:
        session.close()


def test_requirement_service_update_and_delete_respect_project_context():
    init_db()
    session = SessionLocal()
    try:
        project_a = _create_project(session, 'First Project')
        project_b = _create_project(session, 'Second Project')
        project_repository = ProjectRepository(session)
        requirement_repository = RequirementRepository(session)
        service = RequirementService(requirement_repository, project_repository)

        requirement = service.create_requirement(project_a.id, RequirementCreate(
            title='Alpha title',
            description='Alpha description',
            type='functional',
            priority='medium',
        ))

        updated = service.update_requirement(project_a.id, requirement.id, RequirementUpdate(status='approved'))
        assert updated.title == 'Alpha title'
        assert updated.status == 'approved'

        try:
            service.delete_requirement(project_b.id, requirement.id)
            assert False, 'Expected RequirementProjectMismatchError'
        except RequirementProjectMismatchError:
            pass

        assert service.delete_requirement(project_a.id, requirement.id) is True
        try:
            service.get_requirement(project_a.id, requirement.id)
            assert False, 'Expected RequirementNotFoundError'
        except RequirementNotFoundError:
            pass
    finally:
        session.close()
