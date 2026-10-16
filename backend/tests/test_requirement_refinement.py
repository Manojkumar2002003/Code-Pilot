"""Tests for Requirement Refinement Service, Clarification Sessions, Revisions, and API."""

from __future__ import annotations

from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

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
    ClarificationAnswerInput,
    ClarificationAnswerSubmission,
    ClarificationSessionConcurrencyError,
    ClarificationSessionCreate,
    ClarificationSessionNotFoundError,
    ClarificationSessionProjectMismatchError,
    ClarificationSessionStatus,
    GenerationRevisionNotFoundError,
    InvalidClarificationAnswerError,
    InvalidSessionStateError,
    RefinementTriggerRequest,
)
from app.schemas.llm import LLMError, LLMErrorCode
from app.schemas.project_context import (
    ClarificationAnswer,
    ClarificationQuestion,
)
from app.schemas.requirement import (
    RequirementPriority,
    RequirementType,
)
from app.schemas.requirement_generation import (
    GenerationExecutionMetadata,
    GenerationMode,
    NFRCategory,
    ProposalReviewStatus,
    ProposedFunctionalRequirement,
    ProposedNonFunctionalRequirement,
    RequirementGenerationResult,
)
from app.services.project_context_builder import (
    ProjectContextBuilder,
    detect_context_conflicts,
)
from app.services.requirement_refinement import RequirementRefinementService


def sample_initial_generation_result(project_id: str) -> RequirementGenerationResult:
    return RequirementGenerationResult(
        generation_id="gen-initial-101",
        project_id=project_id,
        summary="Initial requirements for CodePilot workflow tool.",
        functional_requirements=[
            ProposedFunctionalRequirement(
                id="FR-1",
                title="Project Management",
                description="Manage software projects locally.",
                expected_behavior="User can create and list projects.",
                acceptance_criteria=["Can create project"],
            ),
            ProposedFunctionalRequirement(
                id="FR-2",
                title="Requirement Clarification",
                description="Iteratively clarify requirement ambiguities.",
                expected_behavior="Presents questions to user.",
                acceptance_criteria=["Can answer questions"],
            ),
        ],
        non_functional_requirements=[
            ProposedNonFunctionalRequirement(
                id="NFR-1",
                title="Response Latency",
                description="Fast response times for clarification.",
                category=NFRCategory.PERFORMANCE,
                target_metric="p95 < 500ms",
            ),
        ],
        clarification_questions=[
            ClarificationQuestion(
                id="CQ-1",
                question="Which database engine should be used for production storage?",
                rationale="Determines SQL dialect and connection pooling architecture.",
                category="architecture",
                is_required=True,
                suggested_options=["PostgreSQL", "SQLite", "MySQL"],
            ),
            ClarificationQuestion(
                id="CQ-2",
                question="Is multi-factor authentication (MFA) required?",
                rationale="Affects auth flow and third-party provider integration.",
                category="security",
                is_required=False,
                suggested_options=["Yes", "No", "Optional in settings"],
            ),
        ],
        execution_metadata=GenerationExecutionMetadata(
            generation_mode=GenerationMode.INITIAL,
            initial_provider="gemini",
            final_provider="gemini",
            duration_seconds=1.2,
        ),
    )


def sample_refined_generation_result(project_id: str) -> RequirementGenerationResult:
    return RequirementGenerationResult(
        generation_id="gen-refined-202",
        project_id=project_id,
        summary="Refined requirements specification incorporating PostgreSQL choice.",
        functional_requirements=[
            ProposedFunctionalRequirement(
                id="FR-1",
                title="Project Management",
                description="Manage software projects with PostgreSQL storage backend.",
                expected_behavior="User can create and list projects backed by PostgreSQL.",
                acceptance_criteria=["Can create project", "Data persisted in PostgreSQL"],
            ),
            ProposedFunctionalRequirement(
                id="FR-2",
                title="Requirement Clarification",
                description="Iteratively clarify requirement ambiguities.",
                expected_behavior="Presents questions to user.",
                acceptance_criteria=["Can answer questions"],
            ),
            ProposedFunctionalRequirement(
                id="FR-3",
                title="Database Migration Engine",
                description="Run Alembic migrations on startup.",
                expected_behavior="Applies pending migrations automatically.",
                acceptance_criteria=["Schema matches migration HEAD"],
            ),
        ],
        non_functional_requirements=[
            ProposedNonFunctionalRequirement(
                id="NFR-1",
                title="Response Latency",
                description="Fast response times for clarification.",
                category=NFRCategory.PERFORMANCE,
                target_metric="p95 < 500ms",
            ),
        ],
        clarification_questions=[],  # All questions resolved
        execution_metadata=GenerationExecutionMetadata(
            generation_mode=GenerationMode.REFINEMENT,
            initial_provider="gemini",
            final_provider="gemini",
            duration_seconds=1.5,
        ),
    )


@pytest.fixture
def db_session() -> Session:
    from sqlalchemy.pool import StaticPool
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
        name="CodePilot Cloud Platform",
        description="Local-first developer tool with AI-assisted software requirements engineering.",
        status="active",
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project


@pytest.fixture
def test_approved_requirement(db_session: Session, test_project: Project) -> Requirement:
    req = Requirement(
        project_id=test_project.id,
        title="Project Workspace Navigation",
        description="User can navigate between overview, requirements, architecture, and tasks.",
        type="functional",
        priority="high",
        status="approved",
    )
    db_session.add(req)
    db_session.commit()
    db_session.refresh(req)
    return req


@pytest.fixture
def refinement_service(db_session: Session) -> tuple[RequirementRefinementService, AsyncMock]:
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


# =========================================================================
# Unit Tests for RequirementRefinementService and Clarification Lifecycle
# =========================================================================


def test_create_session_and_initialize_from_generation(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)

    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    assert session_resp.project_id == test_project.id
    assert session_resp.generation_id == initial_res.generation_id
    assert session_resp.current_revision == 1
    assert session_resp.status == ClarificationSessionStatus.AWAITING_CLARIFICATION
    assert len(session_resp.questions) == 2
    assert session_resp.has_unanswered_required_questions is True
    assert "CQ-1" in session_resp.unanswered_question_ids

    # Verify Revision 1 was created
    rev1 = service.get_revision(test_project.id, session_resp.id, 1)
    assert rev1.revision_number == 1
    assert rev1.parent_generation_id is None
    assert rev1.generation_mode == "initial"
    assert rev1.result.generation_id == initial_res.generation_id


def test_get_session_and_filter_pending_questions(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    all_q = service.get_questions(test_project.id, session_resp.id, pending_only=False)
    assert len(all_q) == 2

    # Submit answer for CQ-1
    service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[
                ClarificationAnswerInput(
                    question_id="CQ-1",
                    answer="Use PostgreSQL 16 with asyncpg.",
                    selected_options=["PostgreSQL"],
                )
            ]
        ),
    )

    pending_q = service.get_questions(test_project.id, session_resp.id, pending_only=True)
    assert len(pending_q) == 1
    assert pending_q[0].id == "CQ-2"


def test_submit_valid_answers_and_status_transitions(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    # Initial state: awaiting clarification
    assert session_resp.status == ClarificationSessionStatus.AWAITING_CLARIFICATION

    # Submit answer for required CQ-1
    updated_session = service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[
                ClarificationAnswerInput(
                    question_id="CQ-1",
                    answer="PostgreSQL database.",
                    selected_options=["PostgreSQL"],
                )
            ]
        ),
    )

    # Status should transition to ready_for_refinement because required CQ-1 is answered
    assert updated_session.status == ClarificationSessionStatus.READY_FOR_REFINEMENT
    assert updated_session.has_unanswered_required_questions is False
    assert len(updated_session.answers) == 1
    assert updated_session.answers[0].question_id == "CQ-1"
    assert updated_session.answers[0].answer == "PostgreSQL database."


def test_reject_unknown_question_id(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    with pytest.raises(InvalidClarificationAnswerError) as exc_info:
        service.submit_answers(
            test_project.id,
            session_resp.id,
            ClarificationAnswerSubmission(
                answers=[
                    ClarificationAnswerInput(
                        question_id="CQ-NON_EXISTENT",
                        answer="Invalid answer",
                    )
                ]
            ),
        )
    assert "does not exist in clarification session" in str(exc_info.value)


def test_reject_duplicate_question_id_in_submission(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    with pytest.raises(InvalidClarificationAnswerError) as exc_info:
        service.submit_answers(
            test_project.id,
            session_resp.id,
            ClarificationAnswerSubmission(
                answers=[
                    ClarificationAnswerInput(question_id="CQ-1", answer="Option A"),
                    ClarificationAnswerInput(question_id="CQ-1", answer="Option B"),
                ]
            ),
        )
    assert "Duplicate answer for question 'CQ-1'" in str(exc_info.value)


def test_enforce_project_isolation(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    foreign_project_id = "foreign-proj-999"

    # Attempt to access session using another project ID
    with pytest.raises(ClarificationSessionProjectMismatchError) as exc_info:
        service.get_session(foreign_project_id, session_resp.id)
    assert "belongs to project" in str(exc_info.value)


def test_explicit_answer_update(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    # First answer
    service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-1", answer="Initial SQLite answer")]
        ),
    )

    # Explicit update
    updated = service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-1", answer="Updated PostgreSQL answer")]
        ),
    )

    assert len(updated.answers) == 1
    assert updated.answers[0].answer == "Updated PostgreSQL answer"


def test_incremental_answers_preservation(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    # 1. Answer CQ-1
    service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-1", answer="PostgreSQL")]
        ),
    )

    # 2. Later answer CQ-2
    updated = service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-2", answer="MFA required")]
        ),
    )

    # Both answers must be preserved
    answered_qids = {a.question_id for a in updated.answers}
    assert answered_qids == {"CQ-1", "CQ-2"}


@pytest.mark.asyncio
async def test_iterative_refinement_workflow_and_revisions(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, mock_agent = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    # Submit answer for CQ-1
    service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-1", answer="Use PostgreSQL 16.")]
        ),
    )

    # Mock agent returning refined specification
    refined_res = sample_refined_generation_result(test_project.id)
    mock_agent.generate_requirements.return_value = refined_res

    # Trigger refinement
    refinement_result = await service.refine_requirements(
        test_project.id,
        session_resp.id,
        RefinementTriggerRequest(instructions="Focus on persistence architecture"),
    )

    # 1. Verify agent call
    mock_agent.generate_requirements.assert_awaited_once()
    call_kwargs = mock_agent.generate_requirements.await_args.kwargs
    assert call_kwargs["mode"] == GenerationMode.REFINEMENT
    assert len(call_kwargs["user_clarifications"]) == 1
    assert call_kwargs["user_clarifications"][0].answer == "Use PostgreSQL 16."

    # 2. Verify Revision 2 was saved
    assert refinement_result.revision.revision_number == 2
    assert refinement_result.revision.parent_generation_id == initial_res.generation_id
    assert refinement_result.session.current_revision == 2
    assert refinement_result.session.generation_id == refined_res.generation_id
    assert refinement_result.session.status == ClarificationSessionStatus.COMPLETED

    # 3. Verify Diff summary
    diff = refinement_result.diff_summary
    assert diff is not None
    assert "FR-3" in diff.new_requirements
    assert "FR-1" in diff.changed_requirements
    assert "FR-2" in diff.retained_requirements
    assert "NFR-1" in diff.retained_requirements


@pytest.mark.asyncio
async def test_refinement_preserves_submitted_answers_on_llm_failure(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, mock_agent = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    # Submit answer
    service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-1", answer="PostgreSQL database")]
        ),
    )

    # Mock agent failure (e.g. Rate limit or outage)
    mock_agent.generate_requirements.side_effect = LLMError(
        message="Rate limit exceeded on all configured providers",
        code=LLMErrorCode.RATE_LIMIT_EXCEEDED,
    )

    with pytest.raises(LLMError):
        await service.refine_requirements(
            test_project.id,
            session_resp.id,
            RefinementTriggerRequest(),
        )

    # Verify session state after failure
    failed_session = service.get_session(test_project.id, session_resp.id)
    assert failed_session.status == ClarificationSessionStatus.FAILED
    assert "Rate limit exceeded" in (failed_session.last_error or "")

    # Crucial: submitted answers are NOT lost
    assert len(failed_session.answers) == 1
    assert failed_session.answers[0].question_id == "CQ-1"
    assert failed_session.answers[0].answer == "PostgreSQL database"


@pytest.mark.asyncio
async def test_safe_refinement_retry_after_failure(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, mock_agent = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-1", answer="PostgreSQL")]
        ),
    )

    # Fail once
    mock_agent.generate_requirements.side_effect = LLMError(
        message="Transient timeout",
        code=LLMErrorCode.REQUEST_TIMEOUT,
    )
    with pytest.raises(LLMError):
        await service.refine_requirements(test_project.id, session_resp.id, RefinementTriggerRequest())

    # Now succeed on retry
    mock_agent.generate_requirements.side_effect = None
    mock_agent.generate_requirements.return_value = sample_refined_generation_result(test_project.id)

    res = await service.refine_requirements(test_project.id, session_resp.id, RefinementTriggerRequest())
    assert res.session.status == ClarificationSessionStatus.COMPLETED
    assert res.revision.revision_number == 2


def test_concurrency_guard_prevents_duplicate_runs(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    # Manually simulate in-progress session
    session_repo = ClarificationSessionRepository(db_session)
    session_model = session_repo.get_by_id(session_resp.id)
    assert session_model is not None
    session_model.status = ClarificationSessionStatus.REFINEMENT_IN_PROGRESS.value
    session_repo.update(session_model)

    # Submitting answers or refining while in progress must fail with Concurrency Error
    with pytest.raises(ClarificationSessionConcurrencyError):
        service.submit_answers(
            test_project.id,
            session_resp.id,
            ClarificationAnswerSubmission(
                answers=[ClarificationAnswerInput(question_id="CQ-1", answer="Answer")]
            ),
        )


def test_cannot_refine_with_unanswered_required_questions(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, _ = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    # Attempt refinement without answering required CQ-1
    import asyncio
    with pytest.raises(InvalidSessionStateError) as exc_info:
        asyncio.run(
            service.refine_requirements(
                test_project.id,
                session_resp.id,
                RefinementTriggerRequest(),
            )
        )
    assert "required clarification questions ['CQ-1'] must be answered first" in str(exc_info.value)


def test_context_conflict_detection(test_project: Project, db_session: Session) -> None:
    project_repo = ProjectRepository(db_session)
    builder = ProjectContextBuilder(project_repo)
    context = builder.build_context(
        test_project.id,
        goals=["Must use SQLite for all database persistence."],
    )

    conflicting_answers = [
        ClarificationAnswer(
            question_id="CQ-1",
            project_id=test_project.id,
            answer="We will use MongoDB instead of SQLite for flexibility.",
        )
    ]

    conflicts = detect_context_conflicts(context, conflicting_answers)
    assert len(conflicts) == 1
    assert "instead of" in conflicts[0]
    assert "Must use SQLite" in conflicts[0]


def test_preserves_existing_approved_requirements(
    db_session: Session,
    test_project: Project,
    test_approved_requirement: Requirement,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, mock_agent = refinement_service
    initial_res = sample_initial_generation_result(test_project.id)
    session_resp = service.initialize_from_generation(test_project.id, initial_res)

    service.submit_answers(
        test_project.id,
        session_resp.id,
        ClarificationAnswerSubmission(
            answers=[ClarificationAnswerInput(question_id="CQ-1", answer="PostgreSQL")]
        ),
    )

    mock_agent.generate_requirements.return_value = sample_refined_generation_result(test_project.id)

    import asyncio
    asyncio.run(
        service.refine_requirements(
            test_project.id,
            session_resp.id,
            RefinementTriggerRequest(include_approved_requirements=True),
        )
    )

    # Verify approved requirement was not modified, deleted, or converted
    req_repo = RequirementRepository(db_session)
    approved_req = req_repo.get_by_id(test_approved_requirement.id)
    assert approved_req is not None
    assert approved_req.status == "approved"
    assert approved_req.title == "Project Workspace Navigation"


# =========================================================================
# FastAPI Endpoints Integration Tests
# =========================================================================


def test_clarifications_api_full_flow(
    db_session: Session,
    test_project: Project,
    refinement_service: tuple[RequirementRefinementService, AsyncMock],
) -> None:
    service, mock_agent = refinement_service

    # Override get_refinement_service dependency in FastAPI
    from app.api.clarifications import get_refinement_service
    app.dependency_overrides[get_refinement_service] = lambda: service

    client = TestClient(app)
    try:
        # 1. Create a clarification session via API
        init_res = sample_initial_generation_result(test_project.id)
        # Pre-seed revision 1 before session creation
        rev_repo = GenerationRevisionRepository(db_session)
        rev_repo.create(
            GenerationRevision(
                project_id=test_project.id,
                session_id=None,
                generation_id=init_res.generation_id,
                parent_generation_id=None,
                revision_number=1,
                generation_mode="initial",
                summary=init_res.summary,
                result_data=init_res.model_dump(mode="json"),
            )
        )

        create_resp = client.post(
            f"/api/projects/{test_project.id}/clarifications/sessions",
            json={
                "generation_id": init_res.generation_id,
                "questions": [q.model_dump() for q in init_res.clarification_questions],
            },
        )
        assert create_resp.status_code == 201
        session_id = create_resp.json()["id"]

        # 2. Get questions via API
        q_resp = client.get(f"/api/projects/{test_project.id}/clarifications/sessions/{session_id}/questions")
        assert q_resp.status_code == 200
        assert len(q_resp.json()) == 2

        # 3. Submit answer via API
        ans_resp = client.post(
            f"/api/projects/{test_project.id}/clarifications/sessions/{session_id}/answers",
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

        # 4. Trigger refinement via API
        mock_agent.generate_requirements.return_value = sample_refined_generation_result(test_project.id)
        refine_resp = client.post(
            f"/api/projects/{test_project.id}/clarifications/sessions/{session_id}/refine",
            json={"instructions": "Focus on database backend"},
        )
        assert refine_resp.status_code == 200
        refine_data = refine_resp.json()
        assert refine_data["session"]["status"] == "completed"
        assert refine_data["revision"]["revision_number"] == 2
        assert refine_data["diff_summary"]["new_requirements"] == ["FR-3"]

        # 5. Get latest result via API
        latest_resp = client.get(
            f"/api/projects/{test_project.id}/clarifications/sessions/{session_id}/result"
        )
        assert latest_resp.status_code == 200
        assert latest_resp.json()["generation_id"] == "gen-refined-202"

        # 6. List revisions via API
        revs_resp = client.get(
            f"/api/projects/{test_project.id}/clarifications/sessions/{session_id}/revisions"
        )
        assert revs_resp.status_code == 200
        assert len(revs_resp.json()) >= 2

        # 7. Error test: unknown question
        err_resp = client.post(
            f"/api/projects/{test_project.id}/clarifications/sessions/{session_id}/answers",
            json={"answers": [{"question_id": "CQ-INVALID", "answer": "test"}]},
        )
        assert err_resp.status_code == 400
        assert err_resp.json()["error"]["code"] == "INVALID_CLARIFICATION_ANSWER"

    finally:
        app.dependency_overrides.clear()
