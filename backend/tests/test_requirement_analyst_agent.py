"""Tests for RequirementAnalystAgent, prompts, context validation, and bounded repair."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.project import Project
from app.repositories.project import ProjectRepository
from app.repositories.requirement import RequirementRepository
from app.agents import (
    RequirementAnalystAgent,
    RequirementAnalystService,
)
from app.schemas.llm import (
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMResponse,
    ModelMetadata,
    TokenUsage,
)
from app.schemas.project import ProjectCreate
from app.schemas.project_context import ClarificationAnswer
from app.schemas.requirement import (
    RequirementCreate,
    RequirementPriority,
    RequirementType,
    RequirementUpdate,
)
from app.schemas.requirement_generation import (
    ContextWindowExceededError,
    GenerationMode,
    GenerationSchemaValidationError,
    InsufficientContextError,
    RequirementGenerationResult,
)
from app.services.llm.service import LLMService
from app.services.project import ProjectNotFoundError
from app.services.project_context_builder import ProjectContextBuilder


@pytest.fixture
def db_session() -> Session:
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
def context_builder(
    project_repo: ProjectRepository,
    requirement_repo: RequirementRepository,
) -> ProjectContextBuilder:
    return ProjectContextBuilder(
        project_repository=project_repo,
        requirement_repository=requirement_repo,
    )


@pytest.fixture
def valid_project(project_repo: ProjectRepository) -> Project:
    return project_repo.create(
        ProjectCreate(
            name="Cloud Commerce",
            description="A modern microservices-based e-commerce platform with automated invoicing.",
        )
    )


@pytest.fixture
def valid_specification_dict() -> dict:
    return {
        "summary": "Generated requirements for Cloud Commerce platform.",
        "functional_requirements": [
            {
                "id": "FR-1",
                "title": "Product Catalog Search",
                "description": "Users can search products by keyword and category.",
                "expected_behavior": "Returns paginated list of matching items in < 200ms.",
                "actor": "Shopper",
                "priority": "high",
                "acceptance_criteria": ["Filters by price range", "Supports fuzzy matching"],
                "dependencies": [],
                "assumptions": ["Catalog is indexed in Elasticsearch"],
            },
            {
                "id": "FR-2",
                "title": "Automated Invoicing",
                "description": "Generate PDF invoice on order completion.",
                "expected_behavior": "Dispatches invoice to customer email upon successful payment.",
                "actor": "Billing System",
                "priority": "medium",
                "acceptance_criteria": ["Includes VAT breakdown", "PDF downloadable from order history"],
                "dependencies": ["FR-1"],
                "assumptions": ["Customer has verified email address"],
            },
        ],
        "non_functional_requirements": [
            {
                "id": "NFR-1",
                "title": "Search Latency",
                "description": "Catalog query response time.",
                "category": "performance",
                "priority": "high",
                "target_metric": "p95 < 200ms",
                "is_target_unresolved": False,
                "acceptance_criteria": ["Benchmark verifies response under load"],
            }
        ],
        "user_stories": [
            {
                "id": "US-1",
                "title": "Search and Discovery",
                "actor": "Shopper",
                "action": "search for products using keywords",
                "benefit": "find relevant items quickly",
                "acceptance_criteria": ["Results match input keywords"],
                "related_requirement_ids": ["FR-1"],
            }
        ],
        "business_rules": [
            {
                "id": "BR-1",
                "rule": "Prices displayed must include regional sales tax.",
                "provenance": "model_inferred",
                "related_requirement_ids": ["FR-1"],
            }
        ],
        "assumptions": [
            {
                "id": "ASM-1",
                "statement": "Payment gateway supports webhook notifications.",
                "category": "integrations",
                "related_requirement_ids": ["FR-2"],
                "is_unresolved": False,
            }
        ],
        "dependencies": [
            {
                "id": "DEP-1",
                "source_id": "FR-2",
                "target_id": "FR-1",
                "description": "Invoicing depends on catalog items.",
            }
        ],
        "clarification_questions": [
            {
                "id": "CQ-1",
                "question": "Which payment gateways should be supported initially?",
                "rationale": "Required to design checkout integration adapters.",
                "category": "integrations",
                "is_required": True,
                "suggested_options": ["Stripe", "Adyen", "PayPal"],
            }
        ],
    }


def create_mock_llm_service(
    return_response: LLMResponse | None = None,
    side_effect: Exception | None = None,
) -> MagicMock:
    service = MagicMock(spec=LLMService)
    service.settings = MagicMock()
    service.settings.default_provider = LLMProviderID.GEMINI
    service.settings.gemini_model = "gemini-2.0-flash"
    service.settings.max_output_tokens = 4096
    service.model_registry = MagicMock()
    service.model_registry.get.return_value = ModelMetadata(
        provider=LLMProviderID.GEMINI,
        model_id="gemini-2.0-flash",
        display_name="Gemini 2.0 Flash",
        context_window_tokens=1048576,
        max_output_tokens=8192,
    )

    if side_effect:
        service.generate = AsyncMock(side_effect=side_effect)
    else:
        service.generate = AsyncMock(return_value=return_response)
    return service


class TestRequirementAnalystAgent:
    """Test suite for RequirementAnalystAgent orchestration."""

    @pytest.mark.asyncio
    async def test_successful_initial_generation(
        self,
        valid_project: Project,
        context_builder: ProjectContextBuilder,
        valid_specification_dict: dict,
    ) -> None:
        mock_response = LLMResponse(
            content=json.dumps(valid_specification_dict),
            provider=LLMProviderID.GEMINI,
            model="gemini-2.0-flash",
            structured_output=valid_specification_dict,
            token_usage=TokenUsage(prompt_tokens=450, completion_tokens=620, total_tokens=1070),
            duration_seconds=1.25,
        )
        mock_llm = create_mock_llm_service(return_response=mock_response)

        agent = RequirementAnalystAgent(
            llm_service=mock_llm,
            context_builder=context_builder,
        )

        result = await agent.generate_requirements(
            project_id=valid_project.id,
            mode=GenerationMode.INITIAL,
            instructions="Focus on microservices scalability.",
        )

        assert isinstance(result, RequirementGenerationResult)
        assert RequirementAnalystService is RequirementAnalystAgent
        assert result.project_id == valid_project.id
        assert len(result.functional_requirements) == 2
        assert len(result.non_functional_requirements) == 1
        assert len(result.user_stories) == 1
        assert len(result.clarification_questions) == 1
        assert result.user_stories[0].related_requirement_ids == ["FR-1"]

        # Check telemetry
        meta = result.execution_metadata
        assert meta is not None
        assert meta.generation_mode == GenerationMode.INITIAL
        assert meta.final_provider == LLMProviderID.GEMINI
        assert meta.final_model == "gemini-2.0-flash"
        assert meta.repair_attempts == 0
        assert meta.structured_output_validated is True
        assert meta.token_usage.total_tokens == 1070

    @pytest.mark.asyncio
    async def test_insufficient_context_error(
        self,
        project_repo: ProjectRepository,
        context_builder: ProjectContextBuilder,
    ) -> None:
        empty_project = project_repo.create(
            ProjectCreate(name="Empty App", description="")
        )
        mock_llm = create_mock_llm_service()
        agent = RequirementAnalystAgent(llm_service=mock_llm, context_builder=context_builder)

        with pytest.raises(InsufficientContextError, match="insufficient detail for requirement generation"):
            await agent.generate_requirements(project_id=empty_project.id)

        # Also test short description (<10 chars)
        short_project = project_repo.create(
            ProjectCreate(name="Tiny", description="App")
        )
        with pytest.raises(InsufficientContextError):
            await agent.generate_requirements(project_id=short_project.id)

    @pytest.mark.asyncio
    async def test_missing_project_error(
        self,
        context_builder: ProjectContextBuilder,
    ) -> None:
        mock_llm = create_mock_llm_service()
        agent = RequirementAnalystAgent(llm_service=mock_llm, context_builder=context_builder)

        with pytest.raises(ProjectNotFoundError):
            await agent.generate_requirements(project_id="non-existent-proj-id")

    @pytest.mark.asyncio
    async def test_context_window_exceeded_error(
        self,
        valid_project: Project,
        context_builder: ProjectContextBuilder,
    ) -> None:
        mock_llm = create_mock_llm_service()
        # Constrain context window in model registry mock
        mock_llm.model_registry.get.return_value = ModelMetadata(
            provider=LLMProviderID.GEMINI,
            model_id="gemini-small",
            display_name="Small Model",
            context_window_tokens=100,  # Extremely small
            max_output_tokens=50,
        )

        agent = RequirementAnalystAgent(llm_service=mock_llm, context_builder=context_builder)

        with pytest.raises(ContextWindowExceededError, match="exceeds model 'gemini-small' context limit"):
            await agent.generate_requirements(
                project_id=valid_project.id,
                model="gemini-small",
            )

    @pytest.mark.asyncio
    async def test_bounded_repair_success(
        self,
        valid_project: Project,
        context_builder: ProjectContextBuilder,
        valid_specification_dict: dict,
    ) -> None:
        """First LLM call returns malformed JSON, second call (repair) returns valid output."""
        malformed_response = LLMResponse(
            content="```json\n{INVALID_JSON_CONTENT\n```",
            provider=LLMProviderID.GROQ,
            model="llama-3.1-8b-instant",
        )

        repaired_response = LLMResponse(
            content=json.dumps(valid_specification_dict),
            provider=LLMProviderID.GROQ,
            model="llama-3.1-8b-instant",
            structured_output=valid_specification_dict,
        )

        mock_llm = create_mock_llm_service()
        mock_llm.generate = AsyncMock(side_effect=[malformed_response, repaired_response])

        agent = RequirementAnalystAgent(
            llm_service=mock_llm,
            context_builder=context_builder,
            max_repair_attempts=1,
        )

        result = await agent.generate_requirements(project_id=valid_project.id)

        assert isinstance(result, RequirementGenerationResult)
        assert len(result.functional_requirements) == 2
        assert mock_llm.generate.call_count == 2
        assert result.execution_metadata.repair_attempts == 1

    @pytest.mark.asyncio
    async def test_bounded_repair_exhausted_failure(
        self,
        valid_project: Project,
        context_builder: ProjectContextBuilder,
    ) -> None:
        """Both original and repair attempts fail, raising GenerationSchemaValidationError."""
        bad_response = LLMResponse(
            content="Not JSON",
            provider=LLMProviderID.OPENROUTER,
            model="meta-llama/llama-3.1-8b-instruct:free",
        )

        mock_llm = create_mock_llm_service()
        mock_llm.generate = AsyncMock(side_effect=[bad_response, bad_response])

        agent = RequirementAnalystAgent(
            llm_service=mock_llm,
            context_builder=context_builder,
            max_repair_attempts=1,
        )

        with pytest.raises(GenerationSchemaValidationError, match="failed schema validation after 1 repair attempt"):
            await agent.generate_requirements(project_id=valid_project.id)

        assert mock_llm.generate.call_count == 2

    @pytest.mark.asyncio
    async def test_refinement_mode_with_clarifications(
        self,
        valid_project: Project,
        context_builder: ProjectContextBuilder,
        valid_specification_dict: dict,
    ) -> None:
        mock_response = LLMResponse(
            content=json.dumps(valid_specification_dict),
            provider=LLMProviderID.GEMINI,
            model="gemini-2.0-flash",
            structured_output=valid_specification_dict,
        )
        mock_llm = create_mock_llm_service(return_response=mock_response)

        agent = RequirementAnalystAgent(
            llm_service=mock_llm,
            context_builder=context_builder,
        )

        clarifications = [
            ClarificationAnswer(
                question_id="CQ-1",
                project_id=valid_project.id,
                answer="We will support Stripe and PayPal exclusively.",
                selected_options=["Stripe", "PayPal"],
            )
        ]

        result = await agent.generate_requirements(
            project_id=valid_project.id,
            mode=GenerationMode.REFINEMENT,
            user_clarifications=clarifications,
        )

        assert result.execution_metadata.generation_mode == GenerationMode.REFINEMENT
        # Verify refinement prompt was used
        call_args = mock_llm.generate.call_args[0][0]
        assert "refining a software requirements specification based on user-supplied clarification answers" in call_args.system_instruction

    @pytest.mark.asyncio
    async def test_regeneration_mode_preserves_approved_requirements(
        self,
        valid_project: Project,
        requirement_repo: RequirementRepository,
        context_builder: ProjectContextBuilder,
        valid_specification_dict: dict,
    ) -> None:
        # Create an approved requirement in the database
        approved_req = requirement_repo.create(
            valid_project.id,
            RequirementCreate(
                title="Existing User Management",
                description="RBAC with Admin and Customer roles.",
                type=RequirementType.FUNCTIONAL,
                priority=RequirementPriority.HIGH,
            ),
        )
        requirement_repo.update(approved_req, RequirementUpdate(status="approved"))

        mock_response = LLMResponse(
            content=json.dumps(valid_specification_dict),
            provider=LLMProviderID.GEMINI,
            model="gemini-2.0-flash",
            structured_output=valid_specification_dict,
        )
        mock_llm = create_mock_llm_service(return_response=mock_response)

        agent = RequirementAnalystAgent(
            llm_service=mock_llm,
            context_builder=context_builder,
        )

        result = await agent.generate_requirements(
            project_id=valid_project.id,
            mode=GenerationMode.REGENERATION,
        )

        assert result.execution_metadata.generation_mode == GenerationMode.REGENERATION
        # Database requirement must NOT be modified or deleted
        db_req = requirement_repo.get_by_id(approved_req.id)
        assert db_req is not None
        assert db_req.title == "Existing User Management"
        assert db_req.status == "approved"

        # Verify regeneration prompt was sent with approved requirement in context
        call_args = mock_llm.generate.call_args[0][0]
        assert "Existing User Management" in call_args.messages[0].content
        assert "regenerating a software requirements specification in the presence of existing approved requirements" in call_args.system_instruction

    @pytest.mark.asyncio
    async def test_failover_telemetry_recording(
        self,
        valid_project: Project,
        context_builder: ProjectContextBuilder,
        valid_specification_dict: dict,
    ) -> None:
        """When failover occurs in LLMService, telemetry accurately reflects initial vs final provider."""
        mock_response = LLMResponse(
            content=json.dumps(valid_specification_dict),
            provider=LLMProviderID.GROQ,  # Fell over to Groq
            model="llama-3.1-8b-instant",
            structured_output=valid_specification_dict,
            metadata={"failover_occurred": True, "initial_provider": "gemini"},
        )
        mock_llm = create_mock_llm_service(return_response=mock_response)

        agent = RequirementAnalystAgent(
            llm_service=mock_llm,
            context_builder=context_builder,
        )

        result = await agent.generate_requirements(
            project_id=valid_project.id,
            provider=LLMProviderID.GEMINI,
        )

        meta = result.execution_metadata
        assert meta.initial_provider == LLMProviderID.GEMINI
        assert meta.final_provider == LLMProviderID.GROQ
        assert meta.failover_occurred is True

    @pytest.mark.asyncio
    async def test_llm_error_propagation(
        self,
        valid_project: Project,
        context_builder: ProjectContextBuilder,
    ) -> None:
        mock_llm = create_mock_llm_service(
            side_effect=LLMError(
                code=LLMErrorCode.QUOTA_EXHAUSTED,
                message="All provider quotas exhausted",
            )
        )
        agent = RequirementAnalystAgent(llm_service=mock_llm, context_builder=context_builder)

        with pytest.raises(LLMError) as exc_info:
            await agent.generate_requirements(project_id=valid_project.id)

        assert exc_info.value.code == LLMErrorCode.QUOTA_EXHAUSTED
