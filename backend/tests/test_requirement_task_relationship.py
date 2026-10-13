import pytest
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.database import SessionLocal, init_db
from app.main import app
from app.models import Project, Requirement, RequirementTask, Task
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.repositories.task import TaskRepository
from app.schemas.task import TaskCreate, TaskPriority, TaskStatus, TaskUpdate
from app.services.requirement import (
    CrossProjectAssociationError,
    RequirementNotFoundError,
    RequirementService,
    RequirementTaskAlreadyLinkedError,
    RequirementTaskNotLinkedError,
)
from app.services.task import TaskNotFoundError, TaskService


def _create_project(session, name="Rel Project"):
    p = Project(name=name, description="Test project for associations")
    session.add(p)
    session.commit()
    session.refresh(p)
    return p


def _create_requirement(session, project_id, title="Requirement 1"):
    r = Requirement(
        project_id=project_id,
        title=title,
        description="Requirement description",
        type="functional",
        priority="high",
        status="approved",
    )
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


def _create_task(session, project_id, title="Task 1"):
    t = Task(
        project_id=project_id,
        title=title,
        description="Task description",
        priority="high",
        status="todo",
    )
    session.add(t)
    session.commit()
    session.refresh(t)
    return t


@pytest.fixture
def db_session():
    init_db()
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    init_db()
    return TestClient(app)


def test_requirement_tasks_table_is_created(db_session):
    inspector = inspect(db_session.bind)
    assert inspector.has_table("requirement_tasks")
    cols = {col["name"] for col in inspector.get_columns("requirement_tasks")}
    assert {"requirement_id", "task_id", "created_at"}.issubset(cols)


def test_link_and_retrieve_associations_bidirectionally(db_session):
    project = _create_project(db_session, "Bidirectional Project")
    req1 = _create_requirement(db_session, project.id, "Req A")
    req2 = _create_requirement(db_session, project.id, "Req B")
    task1 = _create_task(db_session, project.id, "Task X")
    task2 = _create_task(db_session, project.id, "Task Y")

    req_repo = RequirementRepository(db_session)
    task_repo = TaskRepository(db_session)

    # Link Req A -> Task X and Req A -> Task Y
    req_repo.link_task(req1, task1)
    req_repo.link_task(req1, task2)
    # Link Task X -> Req B (so Task X has Req A and Req B)
    task_repo.link_requirement(task1, req2)

    # Verify via Requirement
    tasks_for_req1 = req_repo.get_associated_tasks(req1)
    task_ids_req1 = {t.id for t in tasks_for_req1}
    assert task1.id in task_ids_req1
    assert task2.id in task_ids_req1

    # Verify via Task
    reqs_for_task1 = task_repo.get_associated_requirements(task1)
    req_ids_task1 = {r.id for r in reqs_for_task1}
    assert req1.id in req_ids_task1
    assert req2.id in req_ids_task1

    # Check model properties
    assert task1.id in req1.task_ids
    assert req1.id in task1.requirement_ids


def test_unlink_association_does_not_delete_entities(db_session):
    project = _create_project(db_session, "Unlink Project")
    req = _create_requirement(db_session, project.id, "Req To Unlink")
    task = _create_task(db_session, project.id, "Task To Unlink")

    req_repo = RequirementRepository(db_session)
    req_repo.link_task(req, task)
    assert req_repo.is_task_linked(req, task)

    # Unlink
    unlinked = req_repo.unlink_task(req, task)
    assert unlinked is True
    assert not req_repo.is_task_linked(req, task)

    # Ensure neither requirement nor task was deleted
    assert db_session.get(Requirement, req.id) is not None
    assert db_session.get(Task, task.id) is not None


def test_entity_deletion_cascades_junction_record_only(db_session):
    project = _create_project(db_session, "Cascade Project")
    req = _create_requirement(db_session, project.id, "Req Cascade")
    task = _create_task(db_session, project.id, "Task Cascade")

    req_repo = RequirementRepository(db_session)
    req_repo.link_task(req, task)

    junction_count = db_session.execute(
        select(RequirementTask).where(
            RequirementTask.requirement_id == req.id,
            RequirementTask.task_id == task.id,
        )
    ).scalars().all()
    assert len(junction_count) == 1

    # Delete task: junction record removed, requirement remains
    db_session.delete(task)
    db_session.commit()

    assert db_session.get(Task, task.id) is None
    assert db_session.get(Requirement, req.id) is not None
    junction_after = db_session.execute(
        select(RequirementTask).where(
            RequirementTask.requirement_id == req.id,
            RequirementTask.task_id == task.id,
        )
    ).scalars().all()
    assert len(junction_after) == 0


def test_service_rejects_duplicate_association(db_session):
    project = _create_project(db_session, "Duplicate Link Project")
    req = _create_requirement(db_session, project.id, "Req Dupe")
    task = _create_task(db_session, project.id, "Task Dupe")

    proj_repo = ProjectRepository(db_session)
    req_repo = RequirementRepository(db_session)
    task_repo = TaskRepository(db_session)

    service = RequirementService(req_repo, proj_repo, task_repo)
    service.link_task(project.id, req.id, task.id)

    with pytest.raises(RequirementTaskAlreadyLinkedError):
        service.link_task(project.id, req.id, task.id)


def test_service_rejects_unlinking_nonexistent_association(db_session):
    project = _create_project(db_session, "Not Linked Project")
    req = _create_requirement(db_session, project.id, "Req Unlinked")
    task = _create_task(db_session, project.id, "Task Unlinked")

    proj_repo = ProjectRepository(db_session)
    req_repo = RequirementRepository(db_session)
    task_repo = TaskRepository(db_session)

    service = RequirementService(req_repo, proj_repo, task_repo)
    with pytest.raises(RequirementTaskNotLinkedError):
        service.unlink_task(project.id, req.id, task.id)


def test_service_rejects_cross_project_association(db_session):
    p1 = _create_project(db_session, "Project One")
    p2 = _create_project(db_session, "Project Two")

    req_p1 = _create_requirement(db_session, p1.id, "Req in P1")
    task_p2 = _create_task(db_session, p2.id, "Task in P2")

    proj_repo = ProjectRepository(db_session)
    req_repo = RequirementRepository(db_session)
    task_repo = TaskRepository(db_session)

    req_service = RequirementService(req_repo, proj_repo, task_repo)
    task_service = TaskService(task_repo, proj_repo, req_repo)

    with pytest.raises(CrossProjectAssociationError):
        req_service.link_task(p1.id, req_p1.id, task_p2.id)

    with pytest.raises(CrossProjectAssociationError):
        task_service.link_requirement(p2.id, task_p2.id, req_p1.id)


def test_service_rejects_nonexistent_entities(db_session):
    project = _create_project(db_session, "Nonexistent Entity Project")
    req = _create_requirement(db_session, project.id, "Valid Req")
    task = _create_task(db_session, project.id, "Valid Task")

    proj_repo = ProjectRepository(db_session)
    req_repo = RequirementRepository(db_session)
    task_repo = TaskRepository(db_session)
    req_service = RequirementService(req_repo, proj_repo, task_repo)

    with pytest.raises(TaskNotFoundError):
        req_service.link_task(project.id, req.id, "nonexistent-task-id")

    with pytest.raises(RequirementNotFoundError):
        req_service.link_task(project.id, "nonexistent-req-id", task.id)


def test_persistence_across_new_database_session(db_session):
    project = _create_project(db_session, "Session Persistence Project")
    req = _create_requirement(db_session, project.id, "Persistent Req")
    task = _create_task(db_session, project.id, "Persistent Task")

    req_repo = RequirementRepository(db_session)
    req_repo.link_task(req, task)
    db_session.close()

    # Open fresh session
    new_session = SessionLocal()
    try:
        fresh_req = new_session.get(Requirement, req.id)
        assert fresh_req is not None
        assert task.id in fresh_req.task_ids

        fresh_task = new_session.get(Task, task.id)
        assert fresh_task is not None
        assert req.id in fresh_task.requirement_ids
    finally:
        new_session.close()


def test_api_requirement_tasks_endpoints(client, db_session):
    project = _create_project(db_session, "API Req Tasks Project")
    req = _create_requirement(db_session, project.id, "API Req 1")
    task = _create_task(db_session, project.id, "API Task 1")

    # 1. Link via body POST
    link_res = client.post(
        f"/api/projects/{project.id}/requirements/{req.id}/tasks",
        json={"task_id": task.id},
    )
    assert link_res.status_code == 201
    assert link_res.json()["id"] == task.id

    # 2. List tasks for requirement
    list_res = client.get(f"/api/projects/{project.id}/requirements/{req.id}/tasks")
    assert list_res.status_code == 200
    tasks = list_res.json()
    assert len(tasks) == 1
    assert tasks[0]["id"] == task.id

    # 3. Duplicate link -> 409 Conflict
    dupe_res = client.post(
        f"/api/projects/{project.id}/requirements/{req.id}/tasks",
        json={"task_id": task.id},
    )
    assert dupe_res.status_code == 409
    assert dupe_res.json()["error"]["code"] == "REQUIREMENT_TASK_ALREADY_LINKED"

    # 4. Unlink -> 204 No Content
    unlink_res = client.delete(f"/api/projects/{project.id}/requirements/{req.id}/tasks/{task.id}")
    assert unlink_res.status_code == 204

    # 5. List after unlink -> empty
    list_after = client.get(f"/api/projects/{project.id}/requirements/{req.id}/tasks")
    assert list_after.status_code == 200
    assert len(list_after.json()) == 0

    # 6. Unlink again -> 404
    unlink_again = client.delete(f"/api/projects/{project.id}/requirements/{req.id}/tasks/{task.id}")
    assert unlink_again.status_code == 404
    assert unlink_again.json()["error"]["code"] == "REQUIREMENT_TASK_NOT_LINKED"


def test_api_task_requirements_endpoints(client, db_session):
    project = _create_project(db_session, "API Task Reqs Project")
    req = _create_requirement(db_session, project.id, "API Req 2")
    task = _create_task(db_session, project.id, "API Task 2")

    # 1. Link via path POST
    link_res = client.post(
        f"/api/projects/{project.id}/tasks/{task.id}/requirements/{req.id}"
    )
    assert link_res.status_code == 201
    assert link_res.json()["id"] == req.id

    # 2. List requirements for task
    list_res = client.get(f"/api/projects/{project.id}/tasks/{task.id}/requirements")
    assert list_res.status_code == 200
    reqs = list_res.json()
    assert len(reqs) == 1
    assert reqs[0]["id"] == req.id

    # 3. Duplicate link -> 409
    dupe_res = client.post(
        f"/api/projects/{project.id}/tasks/{task.id}/requirements/{req.id}"
    )
    assert dupe_res.status_code == 409
    assert dupe_res.json()["error"]["code"] == "REQUIREMENT_TASK_ALREADY_LINKED"

    # 4. Unlink -> 204
    del_res = client.delete(f"/api/projects/{project.id}/tasks/{task.id}/requirements/{req.id}")
    assert del_res.status_code == 204

    # 5. List after unlink -> empty
    list_after = client.get(f"/api/projects/{project.id}/tasks/{task.id}/requirements")
    assert list_after.status_code == 200
    assert len(list_after.json()) == 0


def test_api_cross_project_rejection(client, db_session):
    p1 = _create_project(db_session, "API Cross Project 1")
    p2 = _create_project(db_session, "API Cross Project 2")

    req = _create_requirement(db_session, p1.id, "Req P1")
    task = _create_task(db_session, p2.id, "Task P2")

    # Linking cross-project via p1 endpoint
    res1 = client.post(
        f"/api/projects/{p1.id}/requirements/{req.id}/tasks",
        json={"task_id": task.id},
    )
    assert res1.status_code == 400
    assert res1.json()["error"]["code"] == "CROSS_PROJECT_ASSOCIATION"

    # Linking cross-project via p2 endpoint
    res2 = client.post(
        f"/api/projects/{p2.id}/tasks/{task.id}/requirements/{req.id}"
    )
    assert res2.status_code == 400
    assert res2.json()["error"]["code"] == "CROSS_PROJECT_ASSOCIATION"


def test_task_create_and_update_with_requirement_ids(client, db_session):
    project = _create_project(db_session, "Task Create With Reqs Project")
    req1 = _create_requirement(db_session, project.id, "Req Alpha")
    req2 = _create_requirement(db_session, project.id, "Req Beta")

    # Create task with linked req1
    create_res = client.post(
        f"/api/projects/{project.id}/tasks",
        json={
            "title": "Task with linked req",
            "priority": "high",
            "requirement_ids": [req1.id],
        },
    )
    assert create_res.status_code == 201
    created_task = create_res.json()
    assert req1.id in created_task["requirement_ids"]

    task_id = created_task["id"]

    # Update task to link req2 instead
    update_res = client.patch(
        f"/api/projects/{project.id}/tasks/{task_id}",
        json={"requirement_ids": [req2.id]},
    )
    assert update_res.status_code == 200
    updated_task = update_res.json()
    assert req2.id in updated_task["requirement_ids"]
    assert req1.id not in updated_task["requirement_ids"]
