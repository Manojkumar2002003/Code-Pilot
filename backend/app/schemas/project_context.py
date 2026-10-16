"""Project context schema for CodePilot requirement generation.

Defines the typed representations for project data, user clarifications,
context provenance, and approved requirement summaries used by the future
Requirement Analyst agent.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.requirement import RequirementPriority, RequirementType


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ContextSourceType(str, Enum):
    """Categorizes the origin of a piece of project context."""

    PROJECT_METADATA = "project_metadata"
    USER_CLARIFICATION = "user_clarification"
    APPROVED_REQUIREMENT = "approved_requirement"
    USER_GOAL = "user_goal"
    USER_INSTRUCTION = "user_instruction"


class ContextProvenance(BaseModel):
    """Tracks the origin, authenticity, and timestamp of context items."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    source_type: ContextSourceType
    source_id: str | None = Field(
        default=None,
        description="Optional identifier of the origin entity (e.g. requirement ID or question ID).",
    )
    description: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Explanation of how and where this information originated.",
    )
    timestamp: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when this context record was created or verified.",
    )


class ApprovedRequirementSummary(BaseModel):
    """Summary of an existing approved requirement for refinement or regeneration context."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(..., min_length=1, description="Requirement identifier.")
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    type: RequirementType
    priority: RequirementPriority
    status: str = Field(
        default="approved",
        description="Persistence status in the requirements module.",
    )


class ClarificationQuestion(BaseModel):
    """A structured clarification question posed to resolve ambiguous project details."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Stable identifier (e.g. CQ-1).",
    )
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The question prompt for the user.",
    )
    rationale: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Why this information matters for the specification.",
    )
    category: str = Field(
        default="general",
        min_length=1,
        max_length=100,
        description="Relevant project or requirement domain (e.g. scope, security, performance).",
    )
    is_required: bool = Field(
        default=False,
        description="Whether answering is required before proceeding.",
    )
    suggested_options: list[str] = Field(
        default_factory=list,
        description="Optional suggested multiple-choice answers.",
    )
    user_response: str | None = Field(
        default=None,
        description="User's text answer, once provided.",
    )
    selected_options: list[str] = Field(
        default_factory=list,
        description="Options selected by the user from suggested_options.",
    )

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question identifier cannot be empty.")
        return cleaned

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Question text cannot be empty.")
        return cleaned

    @field_validator("rationale")
    @classmethod
    def validate_rationale(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Rationale text cannot be empty.")
        return cleaned


class ClarificationAnswer(BaseModel):
    """User-provided answer to a specific clarification question."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Identifier of the question being answered.",
    )
    project_id: str = Field(
        ...,
        min_length=1,
        max_length=64,
        description="Project to which this clarification belongs.",
    )
    answer: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Free-text answer provided by the user.",
    )
    selected_options: list[str] = Field(
        default_factory=list,
        description="Optional choices selected from suggested options.",
    )
    answered_at: datetime = Field(
        default_factory=utc_now,
        description="Timestamp when the user provided the response.",
    )

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Clarification answer cannot be empty.")
        return cleaned


class ProjectContext(BaseModel):
    """Typed project context provided to future AI requirement generation agents.

    Distinguishes user-provided facts from inferred assumptions and
    isolates data strictly by project_id.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    project_id: str = Field(..., min_length=1, description="Primary project identifier.")
    project_name: str = Field(..., min_length=1, max_length=255)
    project_description: str | None = Field(
        default=None,
        max_length=10000,
        description="Raw project description provided by the user.",
    )
    project_status: str = Field(
        default="active",
        description="Current project status (e.g. active, archived).",
    )
    goals: list[str] = Field(
        default_factory=list,
        description="Explicit user-provided goals or objectives.",
    )
    user_clarifications: list[ClarificationAnswer] = Field(
        default_factory=list,
        description="Answers to previously posed clarification questions.",
    )
    existing_approved_requirements: list[ApprovedRequirementSummary] = Field(
        default_factory=list,
        description="Approved requirements included only when refinement or regeneration is requested.",
    )
    existing_proposed_requirements: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Previously proposed draft requirements included for refinement.",
    )
    clarification_questions: list[ClarificationQuestion] = Field(
        default_factory=list,
        description="Clarification questions associated with this context.",
    )
    provenance_records: list[ContextProvenance] = Field(
        default_factory=list,
        description="Provenance audit trail for items in the context.",
    )
    additional_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional non-sensitive project metadata.",
    )

    @field_validator("project_name")
    @classmethod
    def validate_project_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Project name cannot be empty.")
        return cleaned

    @model_validator(mode="after")
    def validate_isolation(self) -> ProjectContext:
        """Verify that all child items belong strictly to this project."""
        for clarification in self.user_clarifications:
            if clarification.project_id != self.project_id:
                raise ValueError(
                    f"Cross-project data detected in project context: "
                    f"Clarification for question {clarification.question_id} belongs to project "
                    f"'{clarification.project_id}', but context is for '{self.project_id}'."
                )
        return self

    def to_prompt_summary(self) -> str:
        """Generate a structured text summary for LLM prompt construction."""
        lines = [
            f"Project Name: {self.project_name}",
            f"Project ID: {self.project_id}",
            f"Project Status: {self.project_status}",
        ]
        if self.project_description:
            lines.append(f"Description:\n{self.project_description}")
        else:
            lines.append("Description: None provided.")

        if self.goals:
            lines.append("Stated Goals:")
            for goal in self.goals:
                lines.append(f" - {goal}")

        if self.clarification_questions:
            lines.append("Clarification Questions Context:")
            for q in self.clarification_questions:
                answered = any(a.question_id == q.id for a in self.user_clarifications)
                status_str = "Answered by User" if answered else "Pending User Answer"
                lines.append(f" - [{q.id}] ({status_str}) {q.question} (Rationale: {q.rationale})")

        if self.user_clarifications:
            lines.append("User Clarifications:")
            for c in self.user_clarifications:
                options_text = f" (Selected: {', '.join(c.selected_options)})" if c.selected_options else ""
                lines.append(f" - [Q: {c.question_id}]: {c.answer}{options_text}")

        if self.existing_approved_requirements:
            lines.append("Existing Approved Requirements:")
            for r in self.existing_approved_requirements:
                lines.append(f" - [{r.type.value.upper()}] {r.title} ({r.priority.value}): {r.description}")

        if self.existing_proposed_requirements:
            lines.append("Previously Proposed Draft Requirements (Subject to Refinement):")
            for req in self.existing_proposed_requirements:
                req_id = req.get("id", "Unknown") if isinstance(req, dict) else getattr(req, "id", "Unknown")
                title = req.get("title", "") if isinstance(req, dict) else getattr(req, "title", "")
                desc = req.get("description", "") if isinstance(req, dict) else getattr(req, "description", "")
                lines.append(f" - [{req_id}] {title}: {desc}")

        return "\n".join(lines)


__all__ = [
    "ContextSourceType",
    "ContextProvenance",
    "ApprovedRequirementSummary",
    "ClarificationQuestion",
    "ClarificationAnswer",
    "ProjectContext",
]
