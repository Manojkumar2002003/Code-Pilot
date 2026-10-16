"""Tests for Requirement Generation and Clarification API (S3.6).

Covers all 14 required capabilities:
1. Successful initial generation.
2. Retrieval of a generation result and its status.
3. Retrieval of the latest generation result.
4. Clarification session and question retrieval.
5. Successful answer submission and refinement.
6. Invalid request payloads and incomplete required answers.
7. Missing project, generation, and clarification session.
8. Cross-project access attempts.
9. Invalid lifecycle transitions.
10. Provider failures and timeout/error mapping.
11. Preservation of previous results and submitted answers after refinement failure.
12. Ensuring proposed requirements are not automatically approved or persisted as approved requirements.
13. Response-schema validation and backward compatibility with existing endpoints.
14. Duplicate or repeated requests where idempotent behavior is supported.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.clarifications import get_refinement_service
from app.database.base import Base
from app.main import app
from app.models.clarification import ClarificationSession, GenerationRevision  # noqa: F401
from app.models.project import Project
from app.models.requirement import Requirement
from app.repositories.clarification import (
    ClarificationSessionRepository,
    GenerationRevisionRepository,
)
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.clarification import (
    ClarificationSessionStatus,
    RequirementGenerationResponse,
)
from app.schemas.llm import LLMError, LLMErrorCode
from app.schemas.project_context import (
    ClarificationQuestion,
)
from app.schemas.requirement_generation import (
    GenerationExecutionMetadata,
    GenerationMode,
    NFRCategory,
    ProposedFunctionalRequirement,
    ProposedNonFunctionalRequirement,
    RequirementGenerationResult,
)
from app.services.project_context_builder import ProjectContextBuilder
from app.services.requirement_refinement import RequirementRefinementService


def sample_initial_result(project_id: str, generation_id: str = "gen-initial-001") -> RequirementGenerationResult:
    return RequirementGenerationResult(
        generation_id=generation_id,
        project_id=project_id,
        summary="Initial requirement specification for CodePilot developer workspace.",
        functional_requirements=[
            ProposedFunctionalRequirement(
                id="FR-1",
                title="Project Management",
                description="Manage software projects with SQLite.",
                expected_behavior="User can create and list projects.",
                acceptance_criteria=["Can create project", "Can list projects"],
            ),
            ProposedFunctionalRequirement(
                id="FR-2",
                title="Clarification Engine",
                description="Prompt user with clarification questions.",
                expected_behavior="Interactive clarification questions displayed.",
                acceptance_criteria=["Questions are presented"],
            ),
        ],
        non_functional_requirements=[
            ProposedNonFunctionalRequirement(
                id="NFR-1",
                title="Response Time",
                description="Fast interactive generation response.",
                category=NFRCategory.PERFORMANCE,
                target_metric="p95 < 800ms",
            ),
        ],
        clarification_questions=[
            ClarificationQuestion(
                id="CQ-1",
                question="Which database engine should be used for production storage?",
                rationale="Affects DB migration and ORM configuration.",
                category="architecture",
                is_required=True,
                suggested_options=["PostgreSQL", "SQLite", "MySQL"],
            ),
            ClarificationQuestion(
                id="CQ-2",
                question="Is multi-factor authentication (MFA) required?",
                rationale="Affects auth flow complexity.",
                category="security",
                is_required=False,
                suggested_options=["Yes", "No"],
            ),
        ],
        execution_metadata=GenerationExecutionMetadata(
            generation_mode=GenerationMode.INITIAL,
            initial_provider="gemini",
            final_provider="gemini",
            duration_seconds=1.1,
            failover_occurred=False,
        ),
    )


def sample_refined_result(project_id: str, generation_id: str = "gen-refined-002") -> RequirementGenerationResult:
    return RequirementGenerationResult(
        generation_id=generation_id,
        project_id=project_id,
        summary="Refined requirement specification incorporating PostgreSQL database backend.",
        functional_requirements=[
            ProposedFunctionalRequirement(
                id="FR-1",
                title="Project Management",
                description="Manage software projects backed by PostgreSQL database.",
                expected_behavior="User can create and list projects with PostgreSQL persistence.",
                acceptance_criteria=["Can create project", "PostgreSQL persistence confirmed"],
            ),
            ProposedFunctionalRequirement(
                id="FR-2",
                title="Clarification Engine",
                description="Prompt user with clarification questions.",
                expected_behavior="Interactive clarification questions displayed.",
                acceptance_criteria=["Questions are presented"],
            ),
            ProposedFunctionalRequirement(
                id="FR-3",
                title="PostgreSQL Migration Engine",
                description="Alembic migrations on startup.",
                expected_behavior="Auto-applies migrations.",
                acceptance_criteria=["Migrations run successfully"],
            ),
        ],
        non_functional_requirements=[
            ProposedNonFunctionalRequirement(
                id="NFR-1",
                title="Response Time",
                description="Fast interactive generation response.",
                category=NFRCategory.PERFORMANCE,
                target_metric="p95 < 800ms",
            ),
        ],
        clarification_questions=[],
        execution_metadata=GenerationExecutionMetadata(
            generation_mode=GenerationMode.REFINEMENT,
            initial_provider="gemini",
            final_provider="gemini",
            duration_seconds=1.4,
            failover_occurred=False,
        ),
    )


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_project(db_session: Session) -> Project:
    project = Project(
        name="CodePilot Requirements Studio",
        description="Local-first developer tool with AI-assisted software requirements engineering.",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_project_b(db_session: Session) -> Project:
    project = Project(
        name="Secondary Isolated Project",
        description="Second project for multi-tenancy and isolation validation.",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def refinement_setup(
    db_session: Session,
) -> tuple[RequirementRefinementService, AsyncMock]:
    session_repo = ClarificationSessionRepository(db_session)
    revision_repo = GenerationRevisionRepository(db_session)
    project_repo = ProjectRepository(db_session)
    req_repo = RequirementRepository(db_session)
    context_builder = ProjectContextBuilder(project_repo, req_repo)

    mock_agent = AsyncMock()
    service = RequirementRefinementService(
        session_repository=session_repo,
        revision_repository=revision_repo,
        project_repository=project_repo,
        requirement_repository=req_repo,
        agent=mock_agent,
        context_builder=context_builder,
    )
    return service, mock_agent


@pytest.fixture
def client(
    db_session: Session,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> TestClient:
    service, _ = refinement_setup
    from app.database import get_db

    app.dependency_overrides[get_refinement_service] = lambda: service
    app.dependency_overrides[get_db] = lambda: db_session
    test_client = TestClient(app)
    try:
        yield test_client
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# 1. Successful initial generation
# ==============================================================================

def test_01_successful_initial_generation(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
    db_session: Session,
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    resp = client.post(
        f"/api/projects/{test_project.id}/requirement-generations",
        json={"instructions": "Focus on database backend"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["generation_id"] == "gen-initial-001"
    assert data["project_id"] == test_project.id
    assert data["status"] == "awaiting_clarification"
    assert data["revision_number"] == 1
    assert data["session_id"] is not None
    assert len(data["result"]["functional_requirements"]) == 2
    assert len(data["result"]["clarification_questions"]) == 2
    assert data["clarification_session"]["has_unanswered_required_questions"] is True

    # Validate persisted revision in database
    rev_repo = GenerationRevisionRepository(db_session)
    rev = rev_repo.get_by_generation_id("gen-initial-001")
    assert rev is not None
    assert rev.project_id == test_project.id
    assert rev.revision_number == 1


# ==============================================================================
# 2. Retrieval of a generation result and its status
# ==============================================================================

def test_02_retrieve_generation_status_and_result(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    create_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations")
    assert create_resp.status_code == 201
    gen_id = create_resp.json()["generation_id"]

    get_resp = client.get(f"/api/projects/{test_project.id}/requirement-generations/{gen_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["generation_id"] == gen_id
    assert data["project_id"] == test_project.id
    assert data["status"] == "awaiting_clarification"
    assert len(data["result"]["functional_requirements"]) == 2


# ==============================================================================
# 3. Retrieval of the latest generation result
# ==============================================================================

def test_03_retrieve_latest_generation_result(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    client.post(f"/api/projects/{test_project.id}/requirement-generations")

    latest_resp = client.get(f"/api/projects/{test_project.id}/requirement-generations/latest")
    assert latest_resp.status_code == 200
    assert latest_resp.json()["generation_id"] == "gen-initial-001"
    assert latest_resp.json()["revision_number"] == 1


# ==============================================================================
# 4. Clarification session and question retrieval
# ==============================================================================

def test_04_retrieve_clarification_session_and_questions(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    gen_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations").json()
    session_id = gen_resp["session_id"]

    # Retrieve session details
    sess_resp = client.get(f"/api/projects/{test_project.id}/clarification-sessions/{session_id}")
    assert sess_resp.status_code == 200
    assert sess_resp.json()["id"] == session_id
    assert sess_resp.json()["status"] == "awaiting_clarification"

    # Retrieve questions (all)
    q_resp = client.get(f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/questions")
    assert q_resp.status_code == 200
    assert len(q_resp.json()) == 2

    # Retrieve questions (pending only)
    pending_resp = client.get(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/questions?pending_only=true"
    )
    assert pending_resp.status_code == 200
    assert len(pending_resp.json()) == 2


# ==============================================================================
# 5. Successful answer submission and refinement
# ==============================================================================

def test_05_submit_answers_and_refine(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    gen_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations").json()
    session_id = gen_resp["session_id"]

    # Submit required answer for CQ-1
    ans_resp = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/answers",
        json={
            "answers": [
                {
                    "question_id": "CQ-1",
                    "answer": "PostgreSQL 16",
                    "selected_options": ["PostgreSQL"],
                }
            ]
        },
    )
    assert ans_resp.status_code == 200
    assert ans_resp.json()["status"] == "ready_for_refinement"

    # Pending questions now only 1 (CQ-2 optional)
    pending_resp = client.get(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/questions?pending_only=true"
    )
    assert len(pending_resp.json()) == 1
    assert pending_resp.json()[0]["id"] == "CQ-2"

    # Trigger refinement
    mock_agent.generate_requirements.return_value = sample_refined_result(test_project.id)
    refine_resp = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/refine",
        json={"instructions": "Focus on PostgreSQL configuration"},
    )
    assert refine_resp.status_code == 200
    refine_data = refine_resp.json()
    assert refine_data["session"]["status"] == "completed"
    assert refine_data["revision"]["revision_number"] == 2
    assert refine_data["diff_summary"]["new_requirements"] == ["FR-3"]

    # Revisions list has 2 entries
    revs_resp = client.get(f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/revisions")
    assert revs_resp.status_code == 200
    assert len(revs_resp.json()) == 2

    # Latest generation is now Revision 2
    latest_resp = client.get(f"/api/projects/{test_project.id}/requirement-generations/latest")
    assert latest_resp.status_code == 200
    assert latest_resp.json()["revision_number"] == 2
    assert latest_resp.json()["generation_id"] == "gen-refined-002"


# ==============================================================================
# 6. Invalid request payloads and incomplete required answers
# ==============================================================================

def test_06_validation_and_incomplete_required_answers(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    gen_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations").json()
    session_id = gen_resp["session_id"]

    # 1. Invalid payload: temperature > 2.0 (422)
    bad_req = client.post(
        f"/api/projects/{test_project.id}/requirement-generations",
        json={"temperature": 5.0},
    )
    assert bad_req.status_code == 422

    # 2. Unknown question identifier (400)
    unknown_q = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/answers",
        json={"answers": [{"question_id": "CQ-DOESNT-EXIST", "answer": "Some answer"}]},
    )
    assert unknown_q.status_code == 400
    assert unknown_q.json()["error"]["code"] == "INVALID_CLARIFICATION_ANSWER"

    # 3. Empty answer for required question fails Pydantic schema validation (422)
    empty_ans = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/answers",
        json={"answers": [{"question_id": "CQ-1", "answer": "   "}]},
    )
    assert empty_ans.status_code == 422
    assert empty_ans.json()["error"]["code"] == "VALIDATION_ERROR"

    # 4. Refinement attempt without answering required question CQ-1 (409)
    premature_refine = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/refine",
        json={},
    )
    assert premature_refine.status_code == 409
    assert premature_refine.json()["error"]["code"] == "INVALID_SESSION_STATE"


# ==============================================================================
# 7. Missing project, generation, and clarification session
# ==============================================================================

def test_07_missing_resources_return_404(
    client: TestClient,
    test_project: Project,
) -> None:
    # 1. Non-existent project
    resp = client.post("/api/projects/non-existent-proj/requirement-generations")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "PROJECT_NOT_FOUND"

    # 2. Non-existent generation
    resp = client.get(f"/api/projects/{test_project.id}/requirement-generations/non-existent-gen")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "GENERATION_NOT_FOUND"

    # 3. Non-existent clarification session
    resp = client.get(f"/api/projects/{test_project.id}/clarification-sessions/non-existent-sess")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "CLARIFICATION_SESSION_NOT_FOUND"

    # 4. Latest generation when none exist
    resp = client.get(f"/api/projects/{test_project.id}/requirement-generations/latest")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "GENERATION_NOT_FOUND"


# ==============================================================================
# 8. Cross-project access attempts
# ==============================================================================

def test_08_cross_project_isolation(
    client: TestClient,
    test_project: Project,
    test_project_b: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    gen_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations").json()
    gen_id = gen_resp["generation_id"]
    session_id = gen_resp["session_id"]

    # Attempt to access project A's generation through project B -> 404
    cross_gen = client.get(f"/api/projects/{test_project_b.id}/requirement-generations/{gen_id}")
    assert cross_gen.status_code == 404
    assert cross_gen.json()["error"]["code"] == "GENERATION_PROJECT_MISMATCH"

    # Attempt to access project A's session through project B -> 404
    cross_sess = client.get(f"/api/projects/{test_project_b.id}/clarification-sessions/{session_id}")
    assert cross_sess.status_code == 404
    assert cross_sess.json()["error"]["code"] == "PROJECT_MISMATCH"


# ==============================================================================
# 9. Invalid lifecycle transitions
# ==============================================================================

def test_09_invalid_lifecycle_transitions(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
    db_session: Session,
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    gen_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations").json()
    session_id = gen_resp["session_id"]

    # Manually transition session to cancelled
    sess_repo = ClarificationSessionRepository(db_session)
    session = sess_repo.get_by_id(session_id)
    assert session is not None
    session.status = ClarificationSessionStatus.CANCELLED.value
    sess_repo.update(session)

    # Submitting answers to cancelled session -> 409
    ans_resp = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/answers",
        json={"answers": [{"question_id": "CQ-1", "answer": "PostgreSQL"}]},
    )
    assert ans_resp.status_code == 409
    assert ans_resp.json()["error"]["code"] == "INVALID_SESSION_STATE"

    # Refining cancelled session -> 409
    refine_resp = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/refine",
        json={},
    )
    assert refine_resp.status_code == 409
    assert refine_resp.json()["error"]["code"] == "INVALID_SESSION_STATE"


# ==============================================================================
# 10. Provider failures and timeout/error mapping
# ==============================================================================

def test_10_provider_failure_mapping(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup

    # 1. Rate limit -> 429
    mock_agent.generate_requirements.side_effect = LLMError(
        code=LLMErrorCode.RATE_LIMIT_EXCEEDED,
        message="Rate limit exceeded across all configured providers.",
    )
    resp_rate = client.post(f"/api/projects/{test_project.id}/requirement-generations")
    assert resp_rate.status_code == 429
    assert resp_rate.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    # 2. Timeout -> 504
    mock_agent.generate_requirements.side_effect = LLMError(
        code=LLMErrorCode.REQUEST_TIMEOUT,
        message="LLM inference timed out.",
    )
    resp_timeout = client.post(f"/api/projects/{test_project.id}/requirement-generations")
    assert resp_timeout.status_code == 504
    assert resp_timeout.json()["error"]["code"] == "REQUEST_TIMEOUT"

    # 3. Provider outage -> 503
    mock_agent.generate_requirements.side_effect = LLMError(
        code=LLMErrorCode.PROVIDER_OUTAGE,
        message="All cloud providers currently unavailable.",
    )
    resp_outage = client.post(f"/api/projects/{test_project.id}/requirement-generations")
    assert resp_outage.status_code == 503
    assert resp_outage.json()["error"]["code"] == "PROVIDER_OUTAGE"


# ==============================================================================
# 11. Preservation of previous results and submitted answers after refinement failure
# ==============================================================================

def test_11_answers_and_history_preserved_on_refinement_failure(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    # Initial generation succeeded
    gen_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations").json()
    gen_id = gen_resp["generation_id"]
    session_id = gen_resp["session_id"]

    # Submit answer
    client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/answers",
        json={"answers": [{"question_id": "CQ-1", "answer": "PostgreSQL 16"}]},
    )

    # Refinement fails with provider network error
    mock_agent.generate_requirements.side_effect = LLMError(
        code=LLMErrorCode.NETWORK_ERROR,
        message="Connection reset during generation.",
    )
    fail_resp = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/refine",
        json={},
    )
    assert fail_resp.status_code == 502

    # Check that session retains the submitted answer and status is marked failed
    sess_resp = client.get(f"/api/projects/{test_project.id}/clarification-sessions/{session_id}").json()
    assert sess_resp["status"] == "failed"
    assert len(sess_resp["answers"]) == 1
    assert sess_resp["answers"][0]["answer"] == "PostgreSQL 16"

    # Original Revision 1 result remains intact and retrievable
    orig_gen = client.get(f"/api/projects/{test_project.id}/requirement-generations/{gen_id}").json()
    assert orig_gen["generation_id"] == gen_id
    assert orig_gen["revision_number"] == 1

    # Retry refinement succeeds without re-submitting answers
    mock_agent.generate_requirements.side_effect = None
    mock_agent.generate_requirements.return_value = sample_refined_result(test_project.id)
    retry_resp = client.post(
        f"/api/projects/{test_project.id}/clarification-sessions/{session_id}/refine",
        json={},
    )
    assert retry_resp.status_code == 200
    assert retry_resp.json()["session"]["status"] == "completed"


# ==============================================================================
# 12. Ensuring proposed requirements are not automatically approved or persisted
# ==============================================================================

def test_12_proposed_requirements_not_persisted_as_approved(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
    db_session: Session,
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    # Initial generation
    client.post(f"/api/projects/{test_project.id}/requirement-generations")

    # Check approved requirements table
    req_repo = RequirementRepository(db_session)
    approved_reqs = req_repo.list_by_project(test_project.id)
    assert len(approved_reqs) == 0, "Proposed requirements must NOT be inserted into approved requirements table!"

    # Verify existing approved requirement CRUD API returns empty list
    api_reqs = client.get(f"/api/projects/{test_project.id}/requirements").json()
    assert len(api_reqs) == 0


# ==============================================================================
# 13. Response-schema validation and backward compatibility with existing endpoints
# ==============================================================================

def test_13_backward_compatibility_with_clarifications_router(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(test_project.id)

    gen_resp = client.post(f"/api/projects/{test_project.id}/requirement-generations").json()
    session_id = gen_resp["session_id"]

    # 1. Access via S3.6 route
    resp_s36 = client.get(f"/api/projects/{test_project.id}/clarification-sessions/{session_id}")
    assert resp_s36.status_code == 200

    # 2. Access via S3.5 route (/clarifications/sessions/{session_id})
    resp_s35 = client.get(f"/api/projects/{test_project.id}/clarifications/sessions/{session_id}")
    assert resp_s35.status_code == 200

    # Both return identical payloads
    assert resp_s36.json()["id"] == resp_s35.json()["id"]
    assert resp_s36.json()["status"] == resp_s35.json()["status"]


# ==============================================================================
# 14. Duplicate or repeated requests where idempotent behavior is supported
# ==============================================================================

def test_14_idempotent_duplicate_request_reuse(
    client: TestClient,
    test_project: Project,
    refinement_setup: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    _, mock_agent = refinement_setup
    mock_agent.generate_requirements.return_value = sample_initial_result(
        test_project.id, generation_id="gen-idempotent-999"
    )

    # 1. First call with explicit request_id
    resp1 = client.post(
        f"/api/projects/{test_project.id}/requirement-generations",
        json={"request_id": "gen-idempotent-999"},
    )
    assert resp1.status_code == 201
    assert resp1.json()["generation_id"] == "gen-idempotent-999"
    assert mock_agent.generate_requirements.call_count == 1

    # 2. Duplicate call with identical request_id and force_new=False
    resp2 = client.post(
        f"/api/projects/{test_project.id}/requirement-generations",
        json={"request_id": "gen-idempotent-999", "force_new": False},
    )
    assert resp2.status_code == 201
    assert resp2.json()["generation_id"] == "gen-idempotent-999"

    # Agent was NOT called a second time
    assert mock_agent.generate_requirements.call_count == 1
