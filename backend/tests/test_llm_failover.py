"""Comprehensive tests for intelligent LLM provider selection, routing, and failover."""

import pytest

from app.core.llm_config import (
    GeminiConfig,
    GroqConfig,
    LLMSettings,
    OpenRouterConfig,
)
from app.schemas.llm import (
    CapabilitySupport,
    ConversationMessage,
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    MessageRole,
    ModelCapabilities,
    ModelMetadata,
    StructuredOutputRequirement,
)
from app.services.llm.model_registry import ModelRegistry
from app.services.llm.provider import BaseLLMProvider
from app.services.llm.registry import LLMProviderRegistry
from app.services.llm.router import CircuitBreaker
from app.services.llm.service import LLMService


class MockProviderAdapter(BaseLLMProvider):
    """Test fake provider allowing configured responses and error triggers."""

    def __init__(
        self,
        provider_id: LLMProviderID,
        configured: bool = True,
        side_effect: Exception | str | None = None,
        capabilities: ModelCapabilities | None = None,
    ) -> None:
        self._provider_id = provider_id
        self._configured = configured
        self._side_effect = side_effect
        self._capabilities = capabilities or ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
        )
        self.call_count = 0
        self.last_request: LLMRequest | None = None

    @property
    def provider_id(self) -> LLMProviderID:
        return self._provider_id

    def is_configured(self) -> bool:
        return self._configured

    async def get_capabilities(self, model: str | None = None) -> ModelCapabilities:
        return self._capabilities

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        self.last_request = request

        if isinstance(self._side_effect, Exception):
            raise self._side_effect

        content = self._side_effect if isinstance(self._side_effect, str) else f"Response from {self._provider_id.value}"
        return LLMResponse(
            content=content,
            provider=self._provider_id,
            model=request.model or "default-model",
            finish_reason="stop",
        )


@pytest.fixture
def base_settings() -> LLMSettings:
    return LLMSettings(
        default_provider=LLMProviderID.GEMINI,
        provider_priority=[
            LLMProviderID.GEMINI,
            LLMProviderID.OPENROUTER,
            LLMProviderID.GROQ,
        ],
        failover_enabled=True,
        max_failover_attempts=3,
        total_request_deadline_seconds=10.0,
        circuit_breaker_cooldown_seconds=60.0,
        gemini=GeminiConfig(api_key="gemini-key"),
        openrouter=OpenRouterConfig(api_key="or-key"),
        groq=GroqConfig(api_key="groq-key"),
    )


@pytest.mark.asyncio
async def test_primary_succeeds_without_failover(base_settings):
    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(LLMProviderID.GEMINI, side_effect="Gemini success")
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="OR success")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Hello")])
    resp = await service.generate(req)

    assert resp.content == "Gemini success"
    assert resp.provider == LLMProviderID.GEMINI
    assert gemini_mock.call_count == 1
    assert openrouter_mock.call_count == 0

    failover_meta = resp.metadata.get("failover")
    assert failover_meta is not None
    assert failover_meta["total_attempts"] == 1
    assert failover_meta["failover_occurred"] is False


@pytest.mark.asyncio
async def test_rate_limit_failover_to_secondary(base_settings):
    registry = LLMProviderRegistry()
    # Primary hits rate limit
    gemini_mock = MockProviderAdapter(
        LLMProviderID.GEMINI,
        side_effect=LLMError(LLMErrorCode.RATE_LIMIT_EXCEEDED, "Rate limit reached", provider=LLMProviderID.GEMINI),
    )
    # Secondary succeeds
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="OpenRouter success")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Hello")])
    resp = await service.generate(req)

    assert resp.content == "OpenRouter success"
    assert resp.provider == LLMProviderID.OPENROUTER
    assert gemini_mock.call_count == 1
    assert openrouter_mock.call_count == 1

    failover_meta = resp.metadata.get("failover")
    assert failover_meta is not None
    assert failover_meta["total_attempts"] == 2
    assert failover_meta["failover_occurred"] is True
    assert failover_meta["initial_provider"] == "gemini"
    assert failover_meta["final_provider"] == "openrouter"
    assert "RATE_LIMIT_EXCEEDED" in failover_meta["failover_reason"]


@pytest.mark.asyncio
async def test_quota_exhaustion_failover(base_settings):
    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(
        LLMProviderID.GEMINI,
        side_effect=LLMError(LLMErrorCode.QUOTA_EXHAUSTED, "Daily quota exhausted", provider=LLMProviderID.GEMINI),
    )
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="OpenRouter success")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Test")])
    resp = await service.generate(req)

    assert resp.provider == LLMProviderID.OPENROUTER
    failover_meta = resp.metadata.get("failover")
    assert failover_meta["failover_occurred"] is True


@pytest.mark.asyncio
async def test_timeout_failover(base_settings):
    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(
        LLMProviderID.GEMINI,
        side_effect=LLMError(LLMErrorCode.REQUEST_TIMEOUT, "Upstream timeout", provider=LLMProviderID.GEMINI),
    )
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="OpenRouter success")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Test")])
    resp = await service.generate(req)

    assert resp.provider == LLMProviderID.OPENROUTER
    assert resp.metadata["failover"]["failover_occurred"] is True


@pytest.mark.asyncio
async def test_invalid_request_does_not_failover(base_settings):
    # Invalid request (400) should fail immediately without switching providers
    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(
        LLMProviderID.GEMINI,
        side_effect=LLMError(LLMErrorCode.INVALID_REQUEST, "Malformed JSON schema", provider=LLMProviderID.GEMINI),
    )
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="Should not be called")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Test")])
    with pytest.raises(LLMError) as exc_info:
        await service.generate(req)

    assert exc_info.value.code == LLMErrorCode.INVALID_REQUEST
    assert gemini_mock.call_count == 1
    assert openrouter_mock.call_count == 0


@pytest.mark.asyncio
async def test_invalid_credentials_does_not_loop_uncontrolled(base_settings):
    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(
        LLMProviderID.GEMINI,
        side_effect=LLMError(LLMErrorCode.INVALID_CREDENTIALS, "Invalid API key", provider=LLMProviderID.GEMINI),
    )
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="Should not be called")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Test")])
    with pytest.raises(LLMError) as exc_info:
        await service.generate(req)

    assert exc_info.value.code == LLMErrorCode.INVALID_CREDENTIALS
    assert gemini_mock.call_count == 1
    assert openrouter_mock.call_count == 0


@pytest.mark.asyncio
async def test_max_attempts_limit_enforced(base_settings):
    # max_failover_attempts = 2
    settings = base_settings.model_copy(update={"max_failover_attempts": 2})

    registry = LLMProviderRegistry()
    p1 = MockProviderAdapter(LLMProviderID.GEMINI, side_effect=LLMError(LLMErrorCode.RATE_LIMIT_EXCEEDED, "Err 1"))
    p2 = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect=LLMError(LLMErrorCode.RATE_LIMIT_EXCEEDED, "Err 2"))
    p3 = MockProviderAdapter(LLMProviderID.GROQ, side_effect="Groq should not be reached")

    registry.register(p1)
    registry.register(p2)
    registry.register(p3)

    service = LLMService(settings=settings, registry=registry)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Test")])
    with pytest.raises(LLMError) as exc_info:
        await service.generate(req)

    assert exc_info.value.code == LLMErrorCode.RATE_LIMIT_EXCEEDED
    assert p1.call_count == 1
    assert p2.call_count == 1
    assert p3.call_count == 0


@pytest.mark.asyncio
async def test_failover_disabled_via_request_metadata(base_settings):
    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(
        LLMProviderID.GEMINI,
        side_effect=LLMError(LLMErrorCode.RATE_LIMIT_EXCEEDED, "Rate limit reached"),
    )
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="Should not run")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry)

    req = LLMRequest(
        provider=LLMProviderID.GEMINI,
        messages=[ConversationMessage(role=MessageRole.USER, content="Test")],
        metadata={"disallow_failover": True},
    )

    with pytest.raises(LLMError) as exc_info:
        await service.generate(req)

    assert exc_info.value.code == LLMErrorCode.RATE_LIMIT_EXCEEDED
    assert gemini_mock.call_count == 1
    assert openrouter_mock.call_count == 0


@pytest.mark.asyncio
async def test_circuit_breaker_skips_cooldown_provider(base_settings):
    circuit_breaker = CircuitBreaker(default_cooldown_seconds=60.0)
    # Manually mark Gemini in cooldown
    circuit_breaker.record_failure(LLMProviderID.GEMINI, LLMErrorCode.RATE_LIMIT_EXCEEDED, "Rate limit", cooldown_seconds=60.0)

    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(LLMProviderID.GEMINI, side_effect="Gemini available")
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="OpenRouter success")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(settings=base_settings, registry=registry, circuit_breaker=circuit_breaker)

    req = LLMRequest(messages=[ConversationMessage(role=MessageRole.USER, content="Hello")])
    resp = await service.generate(req)

    # Gemini was skipped because of active cooldown
    assert resp.provider == LLMProviderID.OPENROUTER
    assert gemini_mock.call_count == 0
    assert openrouter_mock.call_count == 1


@pytest.mark.asyncio
async def test_capability_mismatch_skips_incompatible_provider(base_settings):
    # Model Registry where Gemini does NOT support structured_json_output, OpenRouter DOES
    custom_model_registry = ModelRegistry([])
    custom_model_registry.register_model(
        ModelMetadata(
            provider=LLMProviderID.GEMINI,
            model_id="gemini-2.0-flash",
            display_name="Gemini Flash",
            capabilities=ModelCapabilities(
                text_generation=CapabilitySupport.SUPPORTED,
                structured_json_output=CapabilitySupport.UNSUPPORTED,  # Gemini cannot do structured output
            ),
        )
    )
    custom_model_registry.register_model(
        ModelMetadata(
            provider=LLMProviderID.OPENROUTER,
            model_id="openai/gpt-4o",
            display_name="GPT-4o",
            capabilities=ModelCapabilities(
                text_generation=CapabilitySupport.SUPPORTED,
                structured_json_output=CapabilitySupport.SUPPORTED,  # OpenRouter can
            ),
        )
    )

    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(LLMProviderID.GEMINI, side_effect="Gemini text")
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect='{"result": "ok"}')

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(
        settings=base_settings,
        registry=registry,
        model_registry=custom_model_registry,
    )

    req = LLMRequest(
        messages=[ConversationMessage(role=MessageRole.USER, content="Output JSON")],
        structured_output=StructuredOutputRequirement(description="JSON output"),
    )

    resp = await service.generate(req)

    # Gemini was skipped due to capability mismatch; routed to OpenRouter
    assert resp.provider == LLMProviderID.OPENROUTER
    assert gemini_mock.call_count == 0
    assert openrouter_mock.call_count == 1


@pytest.mark.asyncio
async def test_context_limit_skips_smaller_context_model(base_settings):
    # Gemini has 10k context, OpenRouter has 100k context
    custom_model_registry = ModelRegistry([])
    custom_model_registry.register_model(
        ModelMetadata(
            provider=LLMProviderID.GEMINI,
            model_id="gemini-2.0-flash",
            display_name="Gemini Small",
            context_window_tokens=10000,
        )
    )
    custom_model_registry.register_model(
        ModelMetadata(
            provider=LLMProviderID.OPENROUTER,
            model_id="openai/gpt-4o",
            display_name="OpenRouter Large",
            context_window_tokens=100000,
        )
    )

    registry = LLMProviderRegistry()
    gemini_mock = MockProviderAdapter(LLMProviderID.GEMINI, side_effect="Gemini text")
    openrouter_mock = MockProviderAdapter(LLMProviderID.OPENROUTER, side_effect="OpenRouter text")

    registry.register(gemini_mock)
    registry.register(openrouter_mock)

    service = LLMService(
        settings=base_settings,
        registry=registry,
        model_registry=custom_model_registry,
    )

    # Request with estimated 25,000 tokens (exceeds Gemini's 10k)
    req = LLMRequest(
        messages=[ConversationMessage(role=MessageRole.USER, content="Big prompt")],
        metadata={"estimated_tokens": 25000},
    )

    resp = await service.generate(req)

    # Gemini skipped; routed to OpenRouter without truncation
    assert resp.provider == LLMProviderID.OPENROUTER
    assert gemini_mock.call_count == 0
    assert openrouter_mock.call_count == 1
