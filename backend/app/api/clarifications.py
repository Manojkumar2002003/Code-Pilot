"""Clarification and iterative requirement generation API router.

Exposes endpoints for:
- Initializing clarification sessions
- Retrieving clarification sessions and questions
- Submitting clarification answers
- Triggering iterative requirement refinement
- Retrieving latest generation results and historical revisions
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.agents.requirement_analyst import RequirementAnalystAgent
from app.core.config import get_llm_settings
from app.core.llm_config import LLMSettings
from app.database import get_db
from app.repositories.clarification import (
    ClarificationSessionRepository,
    GenerationRevisionRepository,
)
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.clarification import (
    ClarificationAnswerSubmission,
    ClarificationSessionCreate,
    ClarificationSessionResponse,
    GenerationRevisionResponse,
    RefinementExecutionResult,
    RefinementTriggerRequest,
)
from app.schemas.project_context import ClarificationQuestion
from app.schemas.requirement_generation import RequirementGenerationResult
from app.services.llm.service import LLMService
from app.services.project_context_builder import ProjectContextBuilder
from app.services.requirement_refinement import RequirementRefinementService

router = APIRouter(
    prefix="/projects/{project_id}/clarifications",
    tags=["clarifications"],
)


def get_refinement_service(
    db: Session = Depends(get_db),
    llm_settings: LLMSettings = Depends(get_llm_settings),
) -> RequirementRefinementService:
    """FastAPI dependency providing a RequirementRefinementService."""
    session_repo = ClarificationSessionRepository(db)
    revision_repo = GenerationRevisionRepository(db)
    project_repo = ProjectRepository(db)
    req_repo = RequirementRepository(db)
    context_builder = ProjectContextBuilder(project_repo, req_repo)
    llm_service = LLMService(settings=llm_settings)
    agent = RequirementAnalystAgent(
        llm_service=llm_service, context_builder=context_builder
    )
    return RequirementRefinementService(
        session_repository=session_repo,
        revision_repository=revision_repo,
        project_repository=project_repo,
        requirement_repository=req_repo,
        agent=agent,
        context_builder=context_builder,
    )


@router.post(
    "/sessions",
    response_model=ClarificationSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create or initialize a clarification session",
)
def create_session(
    project_id: str,
    data: ClarificationSessionCreate,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> ClarificationSessionResponse:
    """Initialize a new clarification session for a project."""
    return service.create_session(project_id, data)


@router.get(
    "/sessions",
    response_model=list[ClarificationSessionResponse],
    summary="List clarification sessions for a project",
)
def list_sessions(
    project_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> list[ClarificationSessionResponse]:
    """Retrieve all clarification sessions for the specified project."""
    return service.list_sessions(project_id)


@router.get(
    "/sessions/{session_id}",
    response_model=ClarificationSessionResponse,
    summary="Get a clarification session by ID",
)
def get_session(
    project_id: str,
    session_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> ClarificationSessionResponse:
    """Retrieve details, questions, answers, and status of a session."""
    return service.get_session(project_id, session_id)


@router.get(
    "/sessions/{session_id}/questions",
    response_model=list[ClarificationQuestion],
    summary="Get clarification questions for a session",
)
def get_questions(
    project_id: str,
    session_id: str,
    pending_only: bool = Query(
        default=False, description="Filter for unanswered questions only"
    ),
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> list[ClarificationQuestion]:
    """Retrieve clarification questions, optionally filtering unanswered."""
    return service.get_questions(
        project_id, session_id, pending_only=pending_only
    )


@router.post(
    "/sessions/{session_id}/answers",
    response_model=ClarificationSessionResponse,
    summary="Submit answers to clarification questions",
)
def submit_answers(
    project_id: str,
    session_id: str,
    submission: ClarificationAnswerSubmission,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> ClarificationSessionResponse:
    """Submit responses to one or more clarification questions in a session."""
    return service.submit_answers(project_id, session_id, submission)


@router.post(
    "/sessions/{session_id}/refine",
    response_model=RefinementExecutionResult,
    summary="Trigger iterative requirement refinement",
)
async def refine_requirements(
    project_id: str,
    session_id: str,
    request: RefinementTriggerRequest,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> RefinementExecutionResult:
    """Refine proposed requirements using user clarification answers."""
    return await service.refine_requirements(project_id, session_id, request)


@router.get(
    "/sessions/{session_id}/result",
    response_model=RequirementGenerationResult,
    summary="Get the latest generated requirement specification for a session",
)
def get_latest_generation(
    project_id: str,
    session_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> RequirementGenerationResult:
    """Retrieve the latest requirement generation specification."""
    return service.get_latest_generation(project_id, session_id)


@router.get(
    "/sessions/{session_id}/revisions",
    response_model=list[GenerationRevisionResponse],
    summary="List generation revisions for a session",
)
def list_revisions(
    project_id: str,
    session_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> list[GenerationRevisionResponse]:
    """Retrieve historical generation revisions produced across iterations."""
    return service.list_revisions(project_id, session_id)


@router.get(
    "/sessions/{session_id}/revisions/{revision_number}",
    response_model=GenerationRevisionResponse,
    summary="Get a specific generation revision by revision number",
)
def get_revision(
    project_id: str,
    session_id: str,
    revision_number: int,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> GenerationRevisionResponse:
    """Retrieve a specific prior generation revision."""
    return service.get_revision(project_id, session_id, revision_number)


__all__ = ["router", "get_refinement_service"]
