"""Project Context Builder service for CodePilot.

Extracts, validates, and prepares project data, user clarifications, and
approved requirements into a typed ProjectContext object for future
AI requirement generation.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.project_context import (
    ApprovedRequirementSummary,
    ClarificationAnswer,
    ContextProvenance,
    ContextSourceType,
    ProjectContext,
)
from app.schemas.requirement import RequirementPriority, RequirementType
from app.services.project import ProjectNotFoundError


class CrossProjectContextError(Exception):
    """Raised when data for another project is injected into context."""

    def __init__(
        self,
        target_project_id: str,
        foreign_project_id: str,
        item_id: str | None = None,
    ):
        super().__init__(
            f"Cross-project context violation: attempted to attach data "
            f"belonging to project '{foreign_project_id}' into project "
            f"'{target_project_id}'"
            + (f" (item: {item_id})" if item_id else ".")
        )
        self.target_project_id = target_project_id
        self.foreign_project_id = foreign_project_id
        self.item_id = item_id


class ProjectContextBuilder:
    """Builds a validated ProjectContext strictly enforcing isolation."""

    def __init__(
        self,
        project_repository: ProjectRepository,
        requirement_repository: RequirementRepository | None = None,
    ):
        self.project_repository = project_repository
        self.requirement_repository = requirement_repository

    def build_context(
        self,
        project_id: str,
        *,
        user_clarifications: Sequence[ClarificationAnswer] | None = None,
        include_approved_requirements: bool = False,
        goals: Sequence[str] | None = None,
        additional_metadata: dict[str, Any] | None = None,
        existing_proposed_requirements: (
            Sequence[dict[str, Any] | Any] | None
        ) = None,
        clarification_questions: Sequence[Any] | None = None,
    ) -> ProjectContext:
        """Construct a ProjectContext from database models and clarifications."""
        # 1. Verify project exists
        project = self.project_repository.get_by_id(project_id)
        if project is None:
            raise ProjectNotFoundError(project_id)

        provenance_records: list[ContextProvenance] = []

        # Record project metadata provenance
        provenance_records.append(
            ContextProvenance(
                source_type=ContextSourceType.PROJECT_METADATA,
                source_id=project.id,
                description=(
                    f"Loaded project metadata from repository: '{project.name}' "
                    f"(status: {project.status})"
                ),
            )
        )

        # 2. Process user clarifications and enforce project boundary
        validated_clarifications: list[ClarificationAnswer] = []
        if user_clarifications:
            for clarification in user_clarifications:
                if clarification.project_id != project_id:
                    raise CrossProjectContextError(
                        target_project_id=project_id,
                        foreign_project_id=clarification.project_id,
                        item_id=clarification.question_id,
                    )
                validated_clarifications.append(clarification)
                ans_preview = (
                    f"'{clarification.answer[:60]}...'"
                    if len(clarification.answer) > 60
                    else f"'{clarification.answer}'"
                )
                provenance_records.append(
                    ContextProvenance(
                        source_type=ContextSourceType.USER_CLARIFICATION,
                        source_id=clarification.question_id,
                        description=(
                            f"User answer for question "
                            f"'{clarification.question_id}': {ans_preview}"
                        ),
                    )
                )

        # 3. Include approved requirements only when explicitly requested
        approved_summaries: list[ApprovedRequirementSummary] = []
        if include_approved_requirements:
            if self.requirement_repository is None:
                raise ValueError(
                    "RequirementRepository is required to load approved requirements."
                )

            requirements = self.requirement_repository.list_by_project(
                project_id
            )
            for req in requirements:
                # Include strictly approved requirements
                if req.status == "approved":
                    summary = ApprovedRequirementSummary(
                        id=req.id,
                        title=req.title,
                        description=req.description,
                        type=RequirementType(req.type),
                        priority=RequirementPriority(req.priority),
                        status=req.status,
                    )
                    approved_summaries.append(summary)
                    provenance_records.append(
                        ContextProvenance(
                            source_type=ContextSourceType.APPROVED_REQUIREMENT,
                            source_id=req.id,
                            description=(
                                f"Approved requirement '{req.title}' "
                                f"({req.type}, {req.priority})"
                            ),
                        )
                    )

        # 4. Record user goals if supplied
        goal_list: list[str] = []
        if goals:
            for goal in goals:
                cleaned_goal = str(goal).strip()
                if cleaned_goal:
                    goal_list.append(cleaned_goal)
            if goal_list:
                provenance_records.append(
                    ContextProvenance(
                        source_type=ContextSourceType.USER_GOAL,
                        description=(
                            f"User-provided {len(goal_list)} "
                            f"high-level project goals"
                        ),
                    )
                )

        # 5. Format existing proposed requirements
        formatted_proposed: list[dict[str, Any]] = []
        if existing_proposed_requirements:
            for item in existing_proposed_requirements:
                if hasattr(item, "model_dump"):
                    formatted_proposed.append(item.model_dump())
                elif isinstance(item, dict):
                    formatted_proposed.append(item)

        # 6. Questions
        questions_list: list[Any] = (
            list(clarification_questions) if clarification_questions else []
        )

        return ProjectContext(
            project_id=project.id,
            project_name=project.name,
            project_description=project.description,
            project_status=project.status,
            goals=goal_list,
            user_clarifications=validated_clarifications,
            existing_approved_requirements=approved_summaries,
            existing_proposed_requirements=formatted_proposed,
            clarification_questions=questions_list,
            provenance_records=provenance_records,
            additional_metadata=additional_metadata or {},
        )


def detect_context_conflicts(
    context: ProjectContext,
    new_answers: Sequence[ClarificationAnswer],
) -> list[str]:
    """Detect potential conflicts between user answers and initial goals."""
    conflicts: list[str] = []
    conflict_triggers = [
        "instead of",
        "replace",
        "rather than",
        "no longer",
        "do not use",
        "not using",
        "switch from",
    ]

    for answer in new_answers:
        ans_lower = answer.answer.lower()
        for goal in context.goals:
            for trigger in conflict_triggers:
                if trigger in ans_lower:
                    conflicts.append(
                        f"Potential conflict: Clarification answer for "
                        f"question '{answer.question_id}' "
                        f"('{answer.answer[:60]}...') contains '{trigger}', "
                        f"which may conflict with stated goal: '{goal}'."
                    )
                    break

    return conflicts


__all__ = [
    "CrossProjectContextError",
    "ProjectContextBuilder",
    "detect_context_conflicts",
]
