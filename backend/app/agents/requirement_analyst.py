"""Requirement Analyst Agent for CodePilot.

Core AI agent responsible for transforming project context into a structured,
validated software requirements specification using the cloud LLM foundation,
model registry, and intelligent failover routing.
"""

from __future__ import annotations

from collections.abc import Sequence
import time

from app.agents.prompts import (
    build_analyst_user_prompt,
    build_repair_feedback_prompt,
    get_analyst_system_instruction,
)
from app.schemas.llm import (
    ConversationMessage,
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    MessageRole,
    StructuredOutputRequirement,
)
from app.schemas.project_context import ClarificationAnswer, ProjectContext
from app.schemas.requirement_generation import (
    ContextWindowExceededError,
    GenerationExecutionMetadata,
    GenerationMode,
    GenerationSchemaValidationError,
    InsufficientContextError,
    NFRCategory,
    RequirementGenerationRequest,
    RequirementGenerationResult,
)
from app.services.llm.service import LLMService
from app.services.project_context_builder import ProjectContextBuilder


class RequirementAnalystAgent:
    """Core AI agent that generates and refines software requirement specifications."""

    def __init__(
        self,
        llm_service: LLMService,
        context_builder: ProjectContextBuilder | None = None,
        max_repair_attempts: int = 1,
    ) -> None:
        self._llm_service = llm_service
        self._context_builder = context_builder
        self._max_repair_attempts = max_repair_attempts

    @property
    def llm_service(self) -> LLMService:
        return self._llm_service

    @property
    def context_builder(self) -> ProjectContextBuilder | None:
        return self._context_builder

    def _validate_context_sufficiency(self, context: ProjectContext) -> None:
        """Ensure context has sufficient substance to perform meaningful analysis."""
        desc = (context.project_description or "").strip()
        has_goals = any(bool(str(g).strip()) for g in context.goals)
        has_clarifications = len(context.user_clarifications) > 0

        # Description must be at least 10 chars, or explicit goals/clarifications must be provided
        if len(desc) < 10 and not has_goals and not has_clarifications:
            raise InsufficientContextError(
                f"Project '{context.project_name}' contains insufficient detail for requirement generation. "
                f"Please provide a substantive project description (at least 10 characters), "
                f"stated goals, or user clarification answers."
            )

    def _check_context_window_budget(
        self,
        prompt_text: str,
        provider: LLMProviderID | None,
        model: str | None,
    ) -> None:
        """Estimate prompt tokens and verify against target model context limit."""
        target_provider = provider or self._llm_service.settings.default_provider
        target_model = model or getattr(
            self._llm_service.settings, f"{target_provider.value}_model", None
        )

        if not target_model:
            return

        model_meta = self._llm_service.model_registry.get(target_provider, target_model)
        if model_meta and model_meta.context_window_tokens:
            # Conservative token estimation: ~4 chars per token
            estimated_prompt_tokens = len(prompt_text) // 4
            max_out = self._llm_service.settings.max_output_tokens or 4096
            if estimated_prompt_tokens + max_out > model_meta.context_window_tokens:
                raise ContextWindowExceededError(
                    f"Estimated prompt tokens ({estimated_prompt_tokens}) plus max output tokens ({max_out}) "
                    f"exceeds model '{target_model}' context limit of {model_meta.context_window_tokens} tokens."
                )

    async def generate_requirements(
        self,
        project_id: str | None = None,
        *,
        context: ProjectContext | None = None,
        mode: GenerationMode = GenerationMode.INITIAL,
        instructions: str | None = None,
        target_categories: list[NFRCategory] | None = None,
        user_clarifications: Sequence[ClarificationAnswer] | None = None,
        include_approved_requirements: bool = False,
        goals: Sequence[str] | None = None,
        provider: LLMProviderID | None = None,
        model: str | None = None,
        temperature: float | None = None,
    ) -> RequirementGenerationResult:
        """Execute requirement generation workflow with validation and bounded repair.

        Args:
            project_id: Target project identifier (required if context is not provided).
            context: Pre-built ProjectContext (optional if project_id and context_builder provided).
            mode: Generation mode (initial, refinement, or regeneration).
            instructions: Optional specific focus instructions from user.
            target_categories: Optional subset of NFR categories.
            user_clarifications: Optional clarification answers.
            include_approved_requirements: Whether to load approved requirements (auto-enabled for regeneration).
            goals: Optional explicit goals.
            provider: Optional explicit LLM provider override.
            model: Optional explicit model ID override.
            temperature: Optional sampling temperature.

        Returns:
            A validated RequirementGenerationResult containing proposed artifacts and telemetry.

        Raises:
            InsufficientContextError: If the project context has insufficient details.
            ContextWindowExceededError: If the context exceeds model limits.
            GenerationSchemaValidationError: If the model output fails validation after repair attempts.
            LLMError: If provider communication or failover fails.
        """
        # 1. Obtain or validate project context
        if context is None:
            if project_id is None:
                raise ValueError("Either 'project_id' or a pre-built 'context' must be provided.")
            if self._context_builder is None:
                raise ValueError(
                    "ProjectContextBuilder was not supplied to RequirementAnalystAgent; "
                    "a pre-built 'context' is required."
                )
            load_approved = include_approved_requirements or (mode == GenerationMode.REGENERATION)
            context = self._context_builder.build_context(
                project_id=project_id,
                user_clarifications=user_clarifications,
                include_approved_requirements=load_approved,
                goals=goals,
            )

        # 2. Validate input sufficiency
        self._validate_context_sufficiency(context)

        # 3. Construct generation request and system instruction
        sys_instruction = get_analyst_system_instruction(mode)
        user_prompt = build_analyst_user_prompt(context=context, instructions=instructions)

        gen_request = RequirementGenerationRequest(
            project_id=context.project_id,
            project_context=context,
            generation_instructions=instructions,
            target_categories=target_categories or [],
            mode=mode,
        )

        llm_request = LLMRequest(
            provider=provider,
            model=model,
            system_instruction=sys_instruction,
            messages=[ConversationMessage(role=MessageRole.USER, content=user_prompt)],
            temperature=temperature,
            structured_output=StructuredOutputRequirement(
                json_schema=RequirementGenerationResult.model_json_schema(),
                description="RequirementGenerationResult JSON Schema",
            ),
        )

        # 4. Check context window limits
        self._check_context_window_budget(
            prompt_text=sys_instruction + user_prompt,
            provider=provider,
            model=model,
        )

        # 5. Execute LLM call
        start_time = time.perf_counter()
        response: LLMResponse = await self._llm_service.generate(llm_request)
        duration = time.perf_counter() - start_time

        # 6. Parse and validate with bounded repair
        repair_attempts = 0
        result: RequirementGenerationResult | None = None
        last_error: Exception | None = None

        try:
            result = RequirementGenerationResult.from_llm_response(
                response, project_id=context.project_id
            )
        except (GenerationSchemaValidationError, ValueError) as exc:
            last_error = exc

            # Bounded repair attempt
            if self._max_repair_attempts > 0:
                repair_attempts += 1
                repair_request = self._build_repair_request(
                    original_llm_request=llm_request,
                    malformed_response=response,
                    error_message=str(exc),
                )
                try:
                    repair_response = await self._llm_service.generate(repair_request)
                    result = RequirementGenerationResult.from_llm_response(
                        repair_response, project_id=context.project_id
                    )
                    # Update response to repair response for telemetry
                    response = repair_response
                except Exception as repair_exc:
                    last_error = repair_exc

        if result is None:
            raise GenerationSchemaValidationError(
                f"Requirement generation output failed schema validation after {repair_attempts} "
                f"repair attempt(s): {str(last_error)}"
            )

        # 7. Record execution and failover telemetry
        init_provider = llm_request.provider or self._llm_service.settings.default_provider
        init_model = llm_request.model or getattr(
            self._llm_service.settings, f"{init_provider.value}_model", None
        )
        failover_meta = (response.metadata or {}).get("failover_occurred", False)
        failover_occurred = failover_meta or (response.provider != init_provider)

        result.execution_metadata = GenerationExecutionMetadata(
            generation_mode=mode,
            initial_provider=init_provider,
            initial_model=init_model,
            final_provider=response.provider,
            final_model=response.model,
            failover_occurred=failover_occurred,
            duration_seconds=round(duration, 3),
            repair_attempts=repair_attempts,
            structured_output_validated=True,
            token_usage=response.token_usage,
        )

        return result

    def _build_repair_request(
        self,
        original_llm_request: LLMRequest,
        malformed_response: LLMResponse,
        error_message: str,
    ) -> LLMRequest:
        """Construct a bounded repair request with feedback on the validation failure."""
        repair_sys = (
            "You are CodePilot's Requirement Analyst. Your previous output failed schema validation. "
            "Correct the identified errors and return the complete, valid JSON specification "
            "conforming strictly to the schema."
        )

        original_prompt = (
            original_llm_request.messages[0].content
            if original_llm_request.messages
            else "Generate requirement specification."
        )

        repair_messages = [
            ConversationMessage(role=MessageRole.USER, content=original_prompt),
            ConversationMessage(role=MessageRole.ASSISTANT, content=malformed_response.content),
            ConversationMessage(
                role=MessageRole.USER,
                content=build_repair_feedback_prompt(error_message),
            ),
        ]

        return LLMRequest(
            provider=original_llm_request.provider,
            model=original_llm_request.model,
            system_instruction=repair_sys,
            messages=repair_messages,
            temperature=0.2,  # Low temperature for deterministic schema adherence
            structured_output=StructuredOutputRequirement(
                json_schema=RequirementGenerationResult.model_json_schema(),
                description="RequirementGenerationResult JSON Schema",
            ),
        )


__all__ = [
    "RequirementAnalystAgent",
]
