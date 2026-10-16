"""Clarification and iterative refinement schemas for CodePilot.

Defines schemas for clarification sessions, question/answer validation,
session lifecycle states, generation revisions, and refinement execution results.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.llm import LLMProviderID
from app.schemas.project_context import ClarificationAnswer, ClarificationQuestion, ProjectContext
from app.schemas.requirement_generation import (
    GenerationExecutionMetadata,
    RequirementGenerationResult,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ClarificationSessionStatus(str, Enum):
    """Lifecycle state of a requirement clarification session."""

    AWAITING_CLARIFICATION = "awaiting_clarification"
    READY_FOR_REFINEMENT = "ready_for_refinement"
    REFINEMENT_IN_PROGRESS = "refinement_in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


VALID_STATE_TRANSITIONS: dict[ClarificationSessionStatus, set[ClarificationSessionStatus]] = {
    ClarificationSessionStatus.AWAITING_CLARIFICATION: {
        ClarificationSessionStatus.READY_FOR_REFINEMENT,
        ClarificationSessionStatus.REFINEMENT_IN_PROGRESS,
        ClarificationSessionStatus.CANCELLED,
    },
    ClarificationSessionStatus.READY_FOR_REFINEMENT: {
        ClarificationSessionStatus.AWAITING_CLARIFICATION,
        ClarificationSessionStatus.REFINEMENT_IN_PROGRESS,
        ClarificationSessionStatus.CANCELLED,
    },
    ClarificationSessionStatus.REFINEMENT_IN_PROGRESS: {
        ClarificationSessionStatus.COMPLETED,
        ClarificationSessionStatus.AWAITING_CLARIFICATION,
        ClarificationSessionStatus.READY_FOR_REFINEMENT,
        ClarificationSessionStatus.FAILED,
    },
    ClarificationSessionStatus.FAILED: {
        ClarificationSessionStatus.REFINEMENT_IN_PROGRESS,
        ClarificationSessionStatus.READY_FOR_REFINEMENT,
        ClarificationSessionStatus.AWAITING_CLARIFICATION,
        ClarificationSessionStatus.CANCELLED,
    },
    ClarificationSessionStatus.COMPLETED: {
        ClarificationSessionStatus.AWAITING_CLARIFICATION,
        ClarificationSessionStatus.READY_FOR_REFINEMENT,
        ClarificationSessionStatus.REFINEMENT_IN_PROGRESS,
    },
    ClarificationSessionStatus.CANCELLED: set(),
}


# --- Exceptions ---


class ClarificationSessionError(Exception):
    """Base exception for clarification session operations."""
    pass


class ClarificationSessionNotFoundError(ClarificationSessionError):
    """Raised when a clarification session is not found."""

    def __init__(self, session_id: str):
        super().__init__(f"Clarification session '{session_id}' not found.")
        self.session_id = session_id


class ClarificationSessionProjectMismatchError(ClarificationSessionError):
    """Raised when a session does not belong to the target project."""

    def __init__(self, session_id: str, target_project_id: str, actual_project_id: str):
        super().__init__(
            f"Clarification session '{session_id}' belongs to project '{actual_project_id}', "
            f"not target project '{target_project_id}'."
        )
        self.session_id = session_id
        self.target_project_id = target_project_id
        self.actual_project_id = actual_project_id


class InvalidClarificationAnswerError(ClarificationSessionError):
    """Raised when submitted clarification answers are invalid."""
    pass


class InvalidSessionStateError(ClarificationSessionError):
    """Raised when an invalid lifecycle state transition is attempted."""
    pass


class ClarificationSessionConcurrencyError(ClarificationSessionError):
    """Raised when an overlapping refinement operation is already in progress."""
    pass


class GenerationRevisionNotFoundError(ClarificationSessionError):
    """Raised when a requested generation revision is not found."""

    def __init__(self, revision_identifier: str):
        super().__init__(f"Generation revision '{revision_identifier}' not found.")
        self.revision_identifier = revision_identifier


class ContextConflictError(ClarificationSessionError):
    """Raised or reported when user answers conflict with earlier verified context facts."""
    pass


# --- Schemas ---


class ClarificationAnswerInput(BaseModel):
    """Input payload for submitting an answer to a clarification question."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_id: str = Field(..., min_length=1, max_length=64)
    answer: str = Field(..., min_length=1, max_length=5000)
    selected_options: list[str] = Field(default_factory=list)

    @field_validator("question_id")
    @classmethod
    def validate_question_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question identifier cannot be empty.")
        return cleaned

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification answer cannot be empty or whitespace only.")
        return cleaned


class ClarificationAnswerSubmission(BaseModel):
    """Request payload containing one or more clarification answers."""

    model_config = ConfigDict(extra="forbid")

    answers: list[ClarificationAnswerInput] = Field(..., min_length=1)


class ClarificationSessionCreate(BaseModel):
    """Payload to initialize a clarification session from a generation result."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    generation_id: str = Field(..., min_length=1, max_length=64)
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    initial_context: ProjectContext | None = None


class ClarificationSessionResponse(BaseModel):
    """Representation of an active or completed clarification session."""

    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    generation_id: str
    status: ClarificationSessionStatus
    current_revision: int
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    answers: list[ClarificationAnswer] = Field(default_factory=list)
    unanswered_question_ids: list[str] = Field(default_factory=list)
    has_unanswered_required_questions: bool = False
    last_error: str | None = None
    created_at: datetime
    updated_at: datetime


class GenerationRevisionResponse(BaseModel):
    """Representation of an immutable generation revision."""

    model_config = ConfigDict(extra="forbid")

    id: str
    project_id: str
    session_id: str | None = None
    generation_id: str
    parent_generation_id: str | None = None
    revision_number: int
    generation_mode: str
    summary: str
    created_at: datetime
    result: RequirementGenerationResult


class RequirementDiffItem(BaseModel):
    """Change item between generation revisions."""

    model_config = ConfigDict(extra="forbid")

    id: str
    title: str
    change_type: str = Field(..., description="new, changed, retained, or removed")
    details: str | None = None


class RequirementDiffSummary(BaseModel):
    """Structured summary of changes between two generation revisions."""

    model_config = ConfigDict(extra="forbid")

    new_requirements: list[str] = Field(default_factory=list)
    changed_requirements: list[str] = Field(default_factory=list)
    retained_requirements: list[str] = Field(default_factory=list)
    removed_requirements: list[str] = Field(default_factory=list)
    diff_items: list[RequirementDiffItem] = Field(default_factory=list)
    total_current: int = 0
    total_previous: int = 0


class RefinementTriggerRequest(BaseModel):
    """Request payload to initiate or resume refinement on a clarification session."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    instructions: str | None = Field(default=None, max_length=5000)
    answers: list[ClarificationAnswerInput] | None = None
    include_approved_requirements: bool = False
    provider: LLMProviderID | None = None
    model: str | None = None
    temperature: float | None = None


class RefinementExecutionResult(BaseModel):
    """Composite response returned when refinement successfully completes."""

    model_config = ConfigDict(extra="forbid")

    session: ClarificationSessionResponse
    latest_generation: RequirementGenerationResult
    revision: GenerationRevisionResponse
    diff_summary: RequirementDiffSummary | None = None
    new_clarification_questions: list[ClarificationQuestion] = Field(default_factory=list)
    execution_metadata: GenerationExecutionMetadata | None = None
    context_conflicts: list[str] = Field(default_factory=list)


__all__ = [
    "VALID_STATE_TRANSITIONS",
    "ClarificationAnswerInput",
    "ClarificationAnswerSubmission",
    "ClarificationSessionConcurrencyError",
    "ClarificationSessionCreate",
    "ClarificationSessionError",
    "ClarificationSessionNotFoundError",
    "ClarificationSessionProjectMismatchError",
    "ClarificationSessionResponse",
    "ClarificationSessionStatus",
    "ContextConflictError",
    "GenerationRevisionNotFoundError",
    "GenerationRevisionResponse",
    "InvalidClarificationAnswerError",
    "InvalidSessionStateError",
    "RefinementExecutionResult",
    "RefinementTriggerRequest",
    "RequirementDiffItem",
    "RequirementDiffSummary",
]
