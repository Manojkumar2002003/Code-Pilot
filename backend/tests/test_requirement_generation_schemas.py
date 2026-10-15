"""Tests for Requirement Generation schemas, referential integrity, and review lifecycle."""

from __future__ import annotations

import json
import pytest

from app.schemas.llm import LLMProviderID, LLMResponse
from app.schemas.project_context import ClarificationQuestion, ProjectContext
from app.schemas.requirement import (
    RequirementCreate,
    RequirementPriority,
    RequirementType,
)
from app.schemas.requirement_generation import (
    GenerationSchemaValidationError,
    NFRCategory,
    ProposalLifecycleError,
    ProposalReviewStatus,
    ProposedAssumption,
    ProposedBusinessRule,
    ProposedDependency,
    ProposedFunctionalRequirement,
    ProposedNonFunctionalRequirement,
    ProposedUserStory,
    RequirementGenerationRequest,
    RequirementGenerationResult,
    RequirementReviewDecision,
    ReviewDecision,
    RuleProvenance,
    convert_proposal_to_requirement_create,
)


@pytest.fixture
def sample_context() -> ProjectContext:
    return ProjectContext(
        project_id="proj-100",
        project_name="AI Analytics Suite",
        project_description="Real-time analytics dashboard with predictive alerts.",
    )


class TestProposedRequirements:
    """Test individual proposed requirement models and review lifecycle transitions."""

    def test_functional_requirement_creation_and_fields(self) -> None:
        fr = ProposedFunctionalRequirement(
            id="FR-1",
            title="Real-Time Metric Ingestion",
            description="Ingest streaming metrics via WebSockets.",
            expected_behavior="System consumes JSON telemetry frames within 100ms.",
            actor="Monitoring Agent",
            priority=RequirementPriority.HIGH,
            acceptance_criteria=["Telemetry latency < 100ms", "Graceful reconnect on dropped connection"],
            dependencies=[],
            assumptions=["Metrics use UTF-8 JSON format"],
        )
        assert fr.id == "FR-1"
        assert fr.title == "Real-Time Metric Ingestion"
        assert fr.review_status == ProposalReviewStatus.DRAFT
        assert len(fr.acceptance_criteria) == 2

    def test_functional_requirement_empty_field_validation(self) -> None:
        with pytest.raises((ValueError, Exception), match=r"(Requirement title cannot be empty|String should have at least 1 character)"):
            ProposedFunctionalRequirement(
                id="FR-1",
                title="   ",
                description="Valid description",
                expected_behavior="Valid behavior",
            )

        with pytest.raises((ValueError, Exception), match=r"(Expected behavior cannot be empty|String should have at least 1 character)"):
            ProposedFunctionalRequirement(
                id="FR-1",
                title="Valid title",
                description="Valid description",
                expected_behavior="   ",
            )

    def test_functional_requirement_review_decisions(self) -> None:
        fr = ProposedFunctionalRequirement(
            id="FR-1",
            title="Initial Title",
            description="Initial Description",
            expected_behavior="Initial Behavior",
        )

        # 1. Accept decision
        fr.apply_decision(RequirementReviewDecision(target_id="FR-1", decision=ReviewDecision.ACCEPT))
        assert fr.review_status == ProposalReviewStatus.ACCEPTED

        # 2. Reject decision
        fr.apply_decision(RequirementReviewDecision(target_id="FR-1", decision=ReviewDecision.REJECT))
        assert fr.review_status == ProposalReviewStatus.REJECTED

        # 3. Modify decision
        fr.apply_decision(
            RequirementReviewDecision(
                target_id="FR-1",
                decision=ReviewDecision.MODIFY,
                modified_title="Updated Title",
                modified_priority=RequirementPriority.CRITICAL,
                notes="Elevated priority for Q3 launch",
            )
        )
        assert fr.review_status == ProposalReviewStatus.MODIFIED
        assert fr.title == "Updated Title"
        assert fr.priority == RequirementPriority.CRITICAL
        assert fr.review_notes == "Elevated priority for Q3 launch"

        # 4. Reset to draft
        fr.apply_decision(RequirementReviewDecision(target_id="FR-1", decision=ReviewDecision.RESET_TO_DRAFT))
        assert fr.review_status == ProposalReviewStatus.DRAFT

    def test_proposal_conversion_lifecycle_guard(self) -> None:
        """Draft or rejected proposals must not be convertible to RequirementCreate without explicit flag."""
        fr = ProposedFunctionalRequirement(
            id="FR-1",
            title="Export Reports",
            description="Export analytics reports to CSV and PDF.",
            expected_behavior="Generates downloadable PDF within 3 seconds.",
        )

        # In draft status: should raise ProposalLifecycleError
        with pytest.raises(ProposalLifecycleError, match="Cannot persist requirement proposal"):
            fr.to_requirement_create()

        # In rejected status: should raise ProposalLifecycleError
        fr.apply_decision(RequirementReviewDecision(target_id="FR-1", decision=ReviewDecision.REJECT))
        with pytest.raises(ProposalLifecycleError, match="Cannot persist requirement proposal"):
            fr.to_requirement_create()

        # In accepted status: converts cleanly
        fr.apply_decision(RequirementReviewDecision(target_id="FR-1", decision=ReviewDecision.ACCEPT))
        req_create = fr.to_requirement_create()
        assert isinstance(req_create, RequirementCreate)
        assert req_create.title == "Export Reports"
        assert req_create.type == RequirementType.FUNCTIONAL
        assert req_create.priority == RequirementPriority.MEDIUM

        # Explicit allow_draft flag
        fr_draft = ProposedFunctionalRequirement(
            id="FR-2",
            title="Draft Feature",
            description="Testing allow_draft override.",
            expected_behavior="Immediate conversion.",
        )
        forced_create = fr_draft.to_requirement_create(allow_draft=True)
        assert forced_create.title == "Draft Feature"

    def test_non_functional_requirement_creation_and_conversion(self) -> None:
        nfr = ProposedNonFunctionalRequirement(
            id="NFR-1",
            title="API Authentication Latency",
            description="OAuth token validation latency.",
            category=NFRCategory.PERFORMANCE,
            priority=RequirementPriority.HIGH,
            target_metric="p95 < 50ms under 1,000 req/sec",
            is_target_unresolved=False,
            acceptance_criteria=["Benchmark confirms p95 < 50ms"],
        )
        assert nfr.id == "NFR-1"
        assert nfr.category == NFRCategory.PERFORMANCE
        assert nfr.target_metric == "p95 < 50ms under 1,000 req/sec"
        assert nfr.is_target_unresolved is False

        # Apply accept decision
        nfr.apply_decision(RequirementReviewDecision(target_id="NFR-1", decision=ReviewDecision.ACCEPT))
        create_schema = convert_proposal_to_requirement_create(nfr)
        assert create_schema.title == "API Authentication Latency"
        assert create_schema.type == RequirementType.NON_FUNCTIONAL
        assert create_schema.priority == RequirementPriority.HIGH

    def test_unresolved_metric_flag(self) -> None:
        """When user does not specify target, model marks target as unresolved instead of inventing one."""
        nfr = ProposedNonFunctionalRequirement(
            id="NFR-2",
            title="Data Retention Compliance",
            description="GDPR customer data purge policy.",
            category=NFRCategory.COMPLIANCE,
            target_metric=None,
            is_target_unresolved=True,
        )
        assert nfr.target_metric is None
        assert nfr.is_target_unresolved is True


class TestAssociatedArtifacts:
    """Test User Stories, Business Rules, Dependencies, and Assumptions."""

    def test_user_story_agile_formatting(self) -> None:
        story = ProposedUserStory(
            id="US-1",
            title="User Password Reset",
            actor="Registered Customer",
            action="reset my forgotten password via a secure email link",
            benefit="regain access to my account without contacting customer support",
            acceptance_criteria=["Token expires in 15 minutes", "One-time use token"],
            related_requirement_ids=["FR-1"],
        )
        assert story.id == "US-1"
        expected = (
            "As a Registered Customer, I want to reset my forgotten password via a secure email link, "
            "so that regain access to my account without contacting customer support."
        )
        assert story.formatted_story == expected
        assert story.related_requirement_ids == ["FR-1"]

    def test_business_rule_provenance(self) -> None:
        rule_explicit = ProposedBusinessRule(
            id="BR-1",
            rule="Discounts cannot exceed 40% of the cart total.",
            provenance=RuleProvenance.USER_EXPLICIT,
            related_requirement_ids=["FR-2"],
        )
        assert rule_explicit.provenance == RuleProvenance.USER_EXPLICIT

        rule_inferred = ProposedBusinessRule(
            id="BR-2",
            rule="Session tokens expire after 2 hours of inactivity.",
            provenance=RuleProvenance.MODEL_INFERRED,
        )
        assert rule_inferred.provenance == RuleProvenance.MODEL_INFERRED

    def test_dependency_and_assumption(self) -> None:
        dep = ProposedDependency(
            id="DEP-1",
            source_id="FR-2",
            target_id="FR-1",
            description="FR-2 requires user session from FR-1",
        )
        assert dep.source_id == "FR-2"
        assert dep.target_id == "FR-1"

        asm = ProposedAssumption(
            id="ASM-1",
            statement="Database will be hosted in AWS eu-west-1.",
            category="infrastructure",
            is_unresolved=True,
        )
        assert asm.is_unresolved is True


class TestRequirementGenerationRequestAndResult:
    """Test full generation request, result validation, and integrity checks."""

    def test_generation_request_project_isolation(self, sample_context: ProjectContext) -> None:
        # 1. Matching project_id succeeds
        req = RequirementGenerationRequest(
            project_id=sample_context.project_id,
            project_context=sample_context,
            generation_instructions="Focus on real-time alerts.",
        )
        assert req.project_id == sample_context.project_id

        # 2. Mismatched project_id raises ValueError
        with pytest.raises(ValueError, match="Project ID mismatch in generation request"):
            RequirementGenerationRequest(
                project_id="different-project-id",
                project_context=sample_context,
            )

    def test_generation_request_to_llm_request(self, sample_context: ProjectContext) -> None:
        req = RequirementGenerationRequest(
            project_id=sample_context.project_id,
            project_context=sample_context,
            generation_instructions="Focus on performance.",
        )
        llm_req = req.to_llm_request(provider=LLMProviderID.GEMINI, model="gemini-2.0-flash")
        assert llm_req.provider == LLMProviderID.GEMINI
        assert llm_req.model == "gemini-2.0-flash"
        assert llm_req.structured_output is not None
        assert "properties" in llm_req.structured_output.json_schema
        assert len(llm_req.messages) == 1
        assert "AI Analytics Suite" in llm_req.messages[0].content

    def test_generation_result_referential_integrity_success(self) -> None:
        result = RequirementGenerationResult(
            project_id="proj-100",
            summary="Complete specification for AI analytics engine.",
            functional_requirements=[
                ProposedFunctionalRequirement(
                    id="FR-1",
                    title="Data Ingestion",
                    description="Ingest telemetry stream.",
                    expected_behavior="Consumes metrics stream.",
                ),
                ProposedFunctionalRequirement(
                    id="FR-2",
                    title="Alert Triggering",
                    description="Evaluate anomalies and trigger alerts.",
                    expected_behavior="Sends webhook alert within 500ms of anomaly.",
                    dependencies=["FR-1"],
                ),
            ],
            non_functional_requirements=[
                ProposedNonFunctionalRequirement(
                    id="NFR-1",
                    title="System Uptime",
                    description="99.9% uptime SLA.",
                    category=NFRCategory.AVAILABILITY,
                )
            ],
            user_stories=[
                ProposedUserStory(
                    id="US-1",
                    title="Anomaly Notification",
                    actor="DevOps Engineer",
                    action="receive an alert when error rate spikes",
                    benefit="mitigate downtime proactively",
                    related_requirement_ids=["FR-2"],
                )
            ],
            business_rules=[
                ProposedBusinessRule(
                    id="BR-1",
                    rule="Alerts cannot fire more than once per 5 minutes per metric.",
                    related_requirement_ids=["FR-2"],
                )
            ],
            dependencies=[
                ProposedDependency(
                    id="DEP-1",
                    source_id="FR-2",
                    target_id="FR-1",
                    description="Alerting depends on ingestion.",
                )
            ],
            clarification_questions=[
                ClarificationQuestion(
                    id="CQ-1",
                    question="Which webhook destinations should be supported?",
                    rationale="Required for alert dispatch architecture.",
                )
            ],
        )

        assert result.project_id == "proj-100"
        assert len(result.functional_requirements) == 2
        assert len(result.user_stories) == 1

        # Test apply decision and filter
        result.apply_review_decision(RequirementReviewDecision(target_id="FR-1", decision=ReviewDecision.ACCEPT))
        accepted = result.get_accepted_requirements()
        assert len(accepted) == 1
        assert accepted[0].id == "FR-1"

    def test_duplicate_identifiers_rejected(self) -> None:
        """Generation result must reject duplicate IDs across any collections."""
        with pytest.raises(ValueError, match="Duplicate identifier 'FR-1' detected"):
            RequirementGenerationResult(
                project_id="proj-100",
                summary="Specification with duplicate IDs.",
                functional_requirements=[
                    ProposedFunctionalRequirement(
                        id="FR-1",
                        title="Feature A",
                        description="Description A",
                        expected_behavior="Behavior A",
                    ),
                    ProposedFunctionalRequirement(
                        id="FR-1",
                        title="Feature B",
                        description="Description B",
                        expected_behavior="Behavior B",
                    ),
                ],
            )

    def test_referential_integrity_nonexistent_requirement_in_story(self) -> None:
        """User story referencing non-existent requirement ID must be rejected."""
        with pytest.raises(ValueError, match="Referential integrity failure: User Story 'US-1' references non-existent"):
            RequirementGenerationResult(
                project_id="proj-100",
                summary="Invalid story references.",
                functional_requirements=[
                    ProposedFunctionalRequirement(
                        id="FR-1",
                        title="Feature 1",
                        description="Desc 1",
                        expected_behavior="Behavior 1",
                    )
                ],
                user_stories=[
                    ProposedUserStory(
                        id="US-1",
                        title="Story 1",
                        actor="User",
                        action="do something",
                        benefit="gain value",
                        related_requirement_ids=["NON-EXISTENT-REQ-99"],
                    )
                ],
            )

    def test_referential_integrity_circular_dependency(self) -> None:
        """Self/circular dependency where source equals target must be rejected."""
        with pytest.raises(ValueError, match="Circular/self dependency detected in Dependency 'DEP-1'"):
            RequirementGenerationResult(
                project_id="proj-100",
                summary="Circular dependency.",
                functional_requirements=[
                    ProposedFunctionalRequirement(
                        id="FR-1",
                        title="Feature 1",
                        description="Desc 1",
                        expected_behavior="Behavior 1",
                    )
                ],
                dependencies=[
                    ProposedDependency(
                        id="DEP-1",
                        source_id="FR-1",
                        target_id="FR-1",
                    )
                ],
            )

    def test_empty_generation_result_rejected(self) -> None:
        """Generation result with 0 requirements and 0 clarification questions must be rejected."""
        with pytest.raises(ValueError, match="Generation result must contain at least one proposed requirement"):
            RequirementGenerationResult(
                project_id="proj-100",
                summary="Empty specification.",
                functional_requirements=[],
                non_functional_requirements=[],
                clarification_questions=[],
            )

    def test_from_llm_response_parsing(self) -> None:
        raw_result = {
            "summary": "AI generated specification.",
            "functional_requirements": [
                {
                    "id": "FR-1",
                    "title": "OAuth Login",
                    "description": "Authenticate users via Google OAuth.",
                    "expected_behavior": "Redirects to Google and returns JWT.",
                    "actor": "End User",
                    "priority": "high",
                    "acceptance_criteria": ["JWT valid for 1 hour"],
                }
            ],
            "non_functional_requirements": [],
            "user_stories": [],
            "business_rules": [],
            "assumptions": [],
            "dependencies": [],
            "clarification_questions": [],
        }

        # 1. Parsing from structured_output dictionary
        response_structured = LLMResponse(
            content="{}",
            provider=LLMProviderID.GEMINI,
            model="gemini-2.0-flash",
            structured_output=raw_result,
        )
        parsed_1 = RequirementGenerationResult.from_llm_response(response_structured, project_id="proj-100")
        assert parsed_1.project_id == "proj-100"
        assert parsed_1.functional_requirements[0].title == "OAuth Login"

        # 2. Parsing from markdown fenced JSON string
        response_markdown = LLMResponse(
            content=f"```json\n{json.dumps(raw_result)}\n```",
            provider=LLMProviderID.GROQ,
            model="llama-3.1-8b-instant",
        )
        parsed_2 = RequirementGenerationResult.from_llm_response(response_markdown, project_id="proj-100")
        assert parsed_2.project_id == "proj-100"
        assert parsed_2.functional_requirements[0].id == "FR-1"

        # 3. Invalid JSON string raises GenerationSchemaValidationError
        response_invalid = LLMResponse(
            content="This is not JSON text at all.",
            provider=LLMProviderID.OPENROUTER,
            model="meta-llama/llama-3.1-8b-instruct:free",
        )
        with pytest.raises(GenerationSchemaValidationError, match="Failed to parse LLM response as JSON"):
            RequirementGenerationResult.from_llm_response(response_invalid, project_id="proj-100")
