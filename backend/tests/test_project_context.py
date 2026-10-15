"""Tests for Project Context schemas and ProjectContextBuilder service."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.schemas.project import ProjectCreate
from app.schemas.project_context import (
    ApprovedRequirementSummary,
    ClarificationAnswer,
    ClarificationQuestion,
    ContextProvenance,
    ContextSourceType,
    ProjectContext,
)
from app.schemas.requirement import (
    RequirementCreate,
    RequirementPriority,
    RequirementType,
    RequirementUpdate,
)
from app.services.project import ProjectNotFoundError
from app.services.project_context_builder import (
    CrossProjectContextError,
    ProjectContextBuilder,
)


@pytest.fixture
def db_session() -> Session:
    """Create an isolated in-memory SQLite database session."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def project_repo(db_session: Session) -> ProjectRepository:
    return ProjectRepository(db_session)


@pytest.fixture
def requirement_repo(db_session: Session) -> RequirementRepository:
    return RequirementRepository(db_session)


@pytest.fixture
def sample_project(project_repo: ProjectRepository) -> Project:
    return project_repo.create(
        ProjectCreate(
            name="E-Commerce Platform",
            description="A cloud-native online shopping platform with cart and checkout.",
        )
    )


class TestProjectContextSchemas:
    """Test standalone Pydantic models in project_context.py."""

    def test_clarification_question_creation(self) -> None:
        q = ClarificationQuestion(
            id="CQ-1",
            question="What payment gateways must be supported?",
            rationale="Needed to specify PCI compliance and checkout integration requirements.",
            category="payments",
            is_required=True,
            suggested_options=["Stripe", "PayPal", "Apple Pay"],
        )
        assert q.id == "CQ-1"
        assert q.is_required is True
        assert len(q.suggested_options) == 3
        assert q.user_response is None

    def test_clarification_question_empty_validation(self) -> None:
        with pytest.raises((ValueError, Exception), match=r"(Question identifier cannot be empty|String should have at least 1 character)"):
            ClarificationQuestion(
                id="  ",
                question="Some question?",
                rationale="Some rationale",
            )

        with pytest.raises((ValueError, Exception), match=r"(Question text cannot be empty|String should have at least 1 character)"):
            ClarificationQuestion(
                id="CQ-1",
                question="   ",
                rationale="Some rationale",
            )

    def test_clarification_answer_creation(self) -> None:
        ans = ClarificationAnswer(
            question_id="CQ-1",
            project_id="proj-123",
            answer="We will support Stripe and PayPal initially.",
            selected_options=["Stripe", "PayPal"],
        )
        assert ans.question_id == "CQ-1"
        assert ans.project_id == "proj-123"
        assert len(ans.selected_options) == 2

    def test_clarification_answer_empty_validation(self) -> None:
        with pytest.raises((ValueError, Exception), match=r"(Clarification answer cannot be empty|String should have at least 1 character)"):
            ClarificationAnswer(
                question_id="CQ-1",
                project_id="proj-123",
                answer="   ",
            )

    def test_context_provenance_creation(self) -> None:
        prov = ContextProvenance(
            source_type=ContextSourceType.USER_CLARIFICATION,
            source_id="CQ-1",
            description="User selected Stripe and PayPal",
        )
        assert prov.source_type == ContextSourceType.USER_CLARIFICATION
        assert prov.timestamp is not None

    def test_project_context_isolation_validation(self) -> None:
        """ProjectContext must reject clarification answers from a different project."""
        foreign_answer = ClarificationAnswer(
            question_id="CQ-99",
            project_id="foreign-proj-456",
            answer="Foreign answer",
        )
        with pytest.raises(ValueError, match="Cross-project data detected"):
            ProjectContext(
                project_id="my-proj-123",
                project_name="My Project",
                user_clarifications=[foreign_answer],
            )

    def test_project_context_to_prompt_summary(self) -> None:
        ctx = ProjectContext(
            project_id="proj-1",
            project_name="Test App",
            project_description="Test description",
            goals=["High availability", "Sub-second search"],
            user_clarifications=[
                ClarificationAnswer(
                    question_id="CQ-1",
                    project_id="proj-1",
                    answer="OAuth2 only",
                    selected_options=["OAuth2"],
                )
            ],
            existing_approved_requirements=[
                ApprovedRequirementSummary(
                    id="req-1",
                    title="User Registration",
                    description="Allow users to sign up",
                    type=RequirementType.FUNCTIONAL,
                    priority=RequirementPriority.HIGH,
                )
            ],
        )
        summary = ctx.to_prompt_summary()
        assert "Project Name: Test App" in summary
        assert "Description:\nTest description" in summary
        assert "High availability" in summary
        assert "[Q: CQ-1]: OAuth2 only" in summary
        assert "User Registration" in summary


class TestProjectContextBuilder:
    """Test ProjectContextBuilder service."""

    def test_build_context_success(
        self,
        project_repo: ProjectRepository,
        sample_project: Project,
    ) -> None:
        builder = ProjectContextBuilder(project_repository=project_repo)
        context = builder.build_context(sample_project.id)

        assert context.project_id == sample_project.id
        assert context.project_name == sample_project.name
        assert context.project_description == sample_project.description
        assert context.project_status == "active"
        assert len(context.provenance_records) >= 1
        assert context.provenance_records[0].source_type == ContextSourceType.PROJECT_METADATA

    def test_build_context_missing_project(
        self,
        project_repo: ProjectRepository,
    ) -> None:
        builder = ProjectContextBuilder(project_repository=project_repo)
        with pytest.raises(ProjectNotFoundError):
            builder.build_context("non-existent-id")

    def test_build_context_empty_description(
        self,
        project_repo: ProjectRepository,
    ) -> None:
        empty_desc_proj = project_repo.create(
            ProjectCreate(name="Minimal Project", description=None)
        )
        builder = ProjectContextBuilder(project_repository=project_repo)
        context = builder.build_context(empty_desc_proj.id)

        assert context.project_name == "Minimal Project"
        assert context.project_description is None
        assert "Description: None provided." in context.to_prompt_summary()

    def test_build_context_with_clarifications(
        self,
        project_repo: ProjectRepository,
        sample_project: Project,
    ) -> None:
        builder = ProjectContextBuilder(project_repository=project_repo)
        clarification = ClarificationAnswer(
            question_id="CQ-1",
            project_id=sample_project.id,
            answer="Store credit only for returns.",
        )
        context = builder.build_context(
            sample_project.id,
            user_clarifications=[clarification],
            goals=["Modern UI", "Fast checkout"],
        )

        assert len(context.user_clarifications) == 1
        assert context.user_clarifications[0].answer == "Store credit only for returns."
        assert len(context.goals) == 2

        # Check provenance
        source_types = [p.source_type for p in context.provenance_records]
        assert ContextSourceType.PROJECT_METADATA in source_types
        assert ContextSourceType.USER_CLARIFICATION in source_types
        assert ContextSourceType.USER_GOAL in source_types

    def test_build_context_cross_project_isolation(
        self,
        project_repo: ProjectRepository,
        sample_project: Project,
    ) -> None:
        """Injecting a clarification belonging to a different project must be rejected."""
        builder = ProjectContextBuilder(project_repository=project_repo)
        other_project = project_repo.create(ProjectCreate(name="Other Project"))

        foreign_clarification = ClarificationAnswer(
            question_id="CQ-1",
            project_id=other_project.id,
            answer="Secret data from other project",
        )

        with pytest.raises(CrossProjectContextError) as exc_info:
            builder.build_context(
                sample_project.id,
                user_clarifications=[foreign_clarification],
            )

        assert sample_project.id in str(exc_info.value)
        assert other_project.id in str(exc_info.value)

    def test_build_context_with_approved_requirements(
        self,
        project_repo: ProjectRepository,
        requirement_repo: RequirementRepository,
        sample_project: Project,
    ) -> None:
        # Create draft, approved, and rejected requirements
        req_draft = requirement_repo.create(
            sample_project.id,
            RequirementCreate(
                title="Draft Feature",
                description="Unapproved feature",
                type=RequirementType.FUNCTIONAL,
            ),
        )

        req_approved = requirement_repo.create(
            sample_project.id,
            RequirementCreate(
                title="Approved Feature",
                description="Approved login workflow",
                type=RequirementType.FUNCTIONAL,
                priority=RequirementPriority.HIGH,
            ),
        )
        requirement_repo.update(req_approved, RequirementUpdate(status="approved"))

        req_rejected = requirement_repo.create(
            sample_project.id,
            RequirementCreate(
                title="Rejected Feature",
                description="Rejected legacy bridge",
                type=RequirementType.NON_FUNCTIONAL,
            ),
        )
        requirement_repo.update(req_rejected, RequirementUpdate(status="rejected"))

        builder = ProjectContextBuilder(
            project_repository=project_repo,
            requirement_repository=requirement_repo,
        )

        # 1. When include_approved_requirements is False (default)
        ctx_default = builder.build_context(sample_project.id, include_approved_requirements=False)
        assert len(ctx_default.existing_approved_requirements) == 0

        # 2. When include_approved_requirements is True
        ctx_with_reqs = builder.build_context(sample_project.id, include_approved_requirements=True)
        assert len(ctx_with_reqs.existing_approved_requirements) == 1
        approved = ctx_with_reqs.existing_approved_requirements[0]
        assert approved.id == req_approved.id
        assert approved.title == "Approved Feature"
        assert approved.status == "approved"
