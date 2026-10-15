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
    """Raised when data belonging to another project is injected into a project's context."""

    def __init__(self, target_project_id: str, foreign_project_id: str, item_id: str | None = None):
        super().__init__(
            f"Cross-project context violation: attempted to attach data belonging to project "
            f"'{foreign_project_id}' into project '{target_project_id}'"
            + (f" (item: {item_id})" if item_id else ".")
        )
        self.target_project_id = target_project_id
        self.foreign_project_id = foreign_project_id
        self.item_id = item_id


class ProjectContextBuilder:
    """Builds a validated ProjectContext while strictly enforcing project isolation."""

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
    ) -> ProjectContext:
        """Construct a ProjectContext from database models and user clarifications.

        Args:
            project_id: Target project ID.
            user_clarifications: Optional user responses to clarification questions.
            include_approved_requirements: Whether to load approved requirements for refinement.
            goals: Optional explicit user-stated goals.
            additional_metadata: Optional non-sensitive extra metadata.

        Returns:
            A validated ProjectContext instance.

        Raises:
            ProjectNotFoundError: If the project does not exist.
            CrossProjectContextError: If any supplied data belongs to a different project.
        """
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
                description=f"Loaded project metadata from repository: '{project.name}' (status: {project.status})",
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
                provenance_records.append(
                    ContextProvenance(
                        source_type=ContextSourceType.USER_CLARIFICATION,
                        source_id=clarification.question_id,
                        description=(
                            f"User answer for question '{clarification.question_id}': "
                            f"'{clarification.answer[:60]}...'" if len(clarification.answer) > 60
                            else f"User answer for question '{clarification.question_id}': '{clarification.answer}'"
                        ),
                    )
                )

        # 3. Include approved requirements only when explicitly requested
        approved_summaries: list[ApprovedRequirementSummary] = []
        if include_approved_requirements:
            if self.requirement_repository is None:
                raise ValueError("RequirementRepository is required to load approved requirements.")

            requirements = self.requirement_repository.list_by_project(project_id)
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
                            description=f"Approved requirement '{req.title}' ({req.type}, {req.priority})",
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
                        description=f"User-provided {len(goal_list)} high-level project goals",
                    )
                )

        return ProjectContext(
            project_id=project.id,
            project_name=project.name,
            project_description=project.description,
            project_status=project.status,
            goals=goal_list,
            user_clarifications=validated_clarifications,
            existing_approved_requirements=approved_summaries,
            provenance_records=provenance_records,
            additional_metadata=additional_metadata or {},
        )


__all__ = [
    "CrossProjectContextError",
    "ProjectContextBuilder",
]
