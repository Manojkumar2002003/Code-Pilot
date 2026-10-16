"""FastAPI endpoints for Requirement Generation and Clarification Workflow.

Exposes REST endpoints for:
- Starting initial AI requirement generation
- Retrieving generation status and results
- Retrieving the latest generation result for a project
- Retrieving clarification sessions and questions
- Submitting answers to clarification questions
- Triggering iterative requirement refinement
- Accessing historical generation revisions
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.api.clarifications import get_refinement_service
from app.schemas.clarification import (
    ClarificationAnswerSubmission,
    ClarificationSessionResponse,
    GenerationRevisionResponse,
    RefinementExecutionResult,
    RefinementTriggerRequest,
    RequirementGenerationResponse,
    RequirementGenerationStartRequest,
)
from app.schemas.project_context import ClarificationQuestion
from app.schemas.requirement_generation import RequirementGenerationResult
from app.services.requirement_refinement import RequirementRefinementService

router = APIRouter(
    prefix="/projects/{project_id}",
    tags=["requirement-generations"],
)


# --- Requirement Generation Endpoints ---


@router.post(
    "/requirement-generations",
    response_model=RequirementGenerationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start requirement generation for a project",
)
async def start_generation(
    project_id: str,
    request: RequirementGenerationStartRequest | None = None,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> RequirementGenerationResponse:
    """Start initial AI requirement generation from project description and context."""
    return await service.start_initial_generation(project_id, request)


@router.get(
    "/requirement-generations/latest",
    response_model=RequirementGenerationResponse,
    summary="Get the latest requirement generation result for a project",
)
def get_latest_generation_for_project(
    project_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> RequirementGenerationResponse:
    """Retrieve the most recent requirement generation result for the project."""
    return service.get_latest_generation_for_project(project_id)


@router.get(
    "/requirement-generations/{generation_id}",
    response_model=RequirementGenerationResponse,
    summary="Get requirement generation status and result",
)
def get_generation(
    project_id: str,
    generation_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> RequirementGenerationResponse:
    """Retrieve the status and specification of a specific requirement generation attempt."""
    return service.get_generation(project_id, generation_id)


# --- Clarification Session Endpoints ---


@router.get(
    "/clarification-sessions/{session_id}",
    response_model=ClarificationSessionResponse,
    summary="Get clarification session by ID",
)
def get_clarification_session(
    project_id: str,
    session_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> ClarificationSessionResponse:
    """Retrieve details, pending questions, answers, and status of a session."""
    return service.get_session(project_id, session_id)


@router.get(
    "/clarification-sessions/{session_id}/questions",
    response_model=list[ClarificationQuestion],
    summary="Get clarification questions for a session",
)
def get_clarification_questions(
    project_id: str,
    session_id: str,
    pending_only: bool = Query(
        default=False, description="Filter for unanswered questions only"
    ),
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> list[ClarificationQuestion]:
    """Retrieve questions for a clarification session, optionally filtering unanswered."""
    return service.get_questions(project_id, session_id, pending_only=pending_only)


@router.post(
    "/clarification-sessions/{session_id}/answers",
    response_model=ClarificationSessionResponse,
    summary="Submit answers to clarification questions",
)
def submit_clarification_answers(
    project_id: str,
    session_id: str,
    submission: ClarificationAnswerSubmission,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> ClarificationSessionResponse:
    """Submit responses to one or more clarification questions in a session."""
    return service.submit_answers(project_id, session_id, submission)


@router.post(
    "/clarification-sessions/{session_id}/refine",
    response_model=RefinementExecutionResult,
    summary="Trigger or resume requirement refinement",
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
    "/clarification-sessions/{session_id}/result",
    response_model=RequirementGenerationResult,
    summary="Get latest requirement specification for a session",
)
def get_latest_session_result(
    project_id: str,
    session_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> RequirementGenerationResult:
    """Retrieve the latest requirement generation specification for the session."""
    return service.get_latest_generation(project_id, session_id)


@router.get(
    "/clarification-sessions/{session_id}/revisions",
    response_model=list[GenerationRevisionResponse],
    summary="List generation revisions for a session",
)
def list_session_revisions(
    project_id: str,
    session_id: str,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> list[GenerationRevisionResponse]:
    """Retrieve historical generation revisions for the clarification session."""
    return service.list_revisions(project_id, session_id)


@router.get(
    "/clarification-sessions/{session_id}/revisions/{revision_number}",
    response_model=GenerationRevisionResponse,
    summary="Get a specific generation revision by revision number",
)
def get_session_revision(
    project_id: str,
    session_id: str,
    revision_number: int,
    service: RequirementRefinementService = Depends(get_refinement_service),
) -> GenerationRevisionResponse:
    """Retrieve a specific prior generation revision."""
    return service.get_revision(project_id, session_id, revision_number)


__all__ = ["router"]
