"""Tests for LLM service, provider registry, and dependency injection."""

import pytest

from app.core.llm_config import GeminiConfig, LLMSettings
from app.schemas.llm import (
    CapabilitySupport,
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMRequest,
    LLMResponse,
    ModelCapabilities,
)
from app.services.llm.provider import BaseLLMProvider
from app.services.llm.registry import LLMProviderRegistry
from app.services.llm.service import LLMService


class FakeLLMProvider(BaseLLMProvider):
    """Test fake provider for dependency injection."""

    def __init__(
        self,
        provider_id: LLMProviderID = LLMProviderID.GEMINI,
        configured: bool = True,
        response_text: str = "Fake generated content",
    ) -> None:
        self._provider_id = provider_id
        self._configured = configured
        self._response_text = response_text
        self.last_request: LLMRequest | None = None

    @property
    def provider_id(self) -> LLMProviderID:
        return self._provider_id

    async def generate(self, request: LLMRequest) -> LLMResponse:
        self.last_request = request
        return LLMResponse(
            content=self._response_text,
            provider=self._provider_id,
            model=request.model,
            finish_reason="stop",
        )

    async def get_capabilities(self, model: str | None = None) -> ModelCapabilities:
        return ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
        )

    def is_configured(self) -> bool:
        return self._configured


@pytest.mark.asyncio
async def test_registry_operations():
    registry = LLMProviderRegistry()
    assert len(registry.list_providers()) == 0

    fake = FakeLLMProvider(LLMProviderID.GEMINI)
    registry.register(fake)

    assert registry.has(LLMProviderID.GEMINI) is True
    assert registry.get(LLMProviderID.GEMINI) is fake
    assert registry.list_providers() == [LLMProviderID.GEMINI]

    registry.unregister(LLMProviderID.GEMINI)
    assert registry.has(LLMProviderID.GEMINI) is False

    with pytest.raises(LLMError) as exc_info:
        registry.get(LLMProviderID.GEMINI)
    assert exc_info.value.code == LLMErrorCode.UNSUPPORTED_PROVIDER


@pytest.mark.asyncio
async def test_llm_service_generation_with_fake_provider():
    settings = LLMSettings(
        gemini=GeminiConfig(api_key="valid-key"),
        default_temperature=0.8,
        default_max_output_tokens=2048,
        default_timeout_seconds=45.0,
    )
    registry = LLMProviderRegistry()
    fake = FakeLLMProvider(LLMProviderID.GEMINI, response_text="Hello from fake Gemini!")
    registry.register(fake)

    service = LLMService(settings=settings, registry=registry)

    req = LLMRequest(
        provider=LLMProviderID.GEMINI,
        model="gemini-2.0-flash",
    )

    resp = await service.generate(req)

    assert resp.content == "Hello from fake Gemini!"
    assert resp.provider == LLMProviderID.GEMINI
    assert resp.model == "gemini-2.0-flash"

    # Check that defaults were filled in
    assert fake.last_request is not None
    assert fake.last_request.temperature == 0.8
    assert fake.last_request.max_output_tokens == 2048
    assert fake.last_request.timeout_seconds == 45.0


@pytest.mark.asyncio
async def test_llm_service_raises_when_provider_not_registered():
    settings = LLMSettings()
    registry = LLMProviderRegistry()
    service = LLMService(settings=settings, registry=registry)

    req = LLMRequest(
        provider=LLMProviderID.GROQ,
        model="llama-3.1-8b-instant",
    )

    with pytest.raises(LLMError) as exc_info:
        await service.generate(req)

    assert exc_info.value.code == LLMErrorCode.UNSUPPORTED_PROVIDER


@pytest.mark.asyncio
async def test_llm_service_raises_when_provider_not_configured():
    settings = LLMSettings()
    registry = LLMProviderRegistry()
    unconfigured_fake = FakeLLMProvider(LLMProviderID.GEMINI, configured=False)
    registry.register(unconfigured_fake)

    service = LLMService(settings=settings, registry=registry)

    req = LLMRequest(
        provider=LLMProviderID.GEMINI,
        model="gemini-2.0-flash",
    )

    with pytest.raises(LLMError) as exc_info:
        await service.generate(req)

    assert exc_info.value.code == LLMErrorCode.PROVIDER_NOT_CONFIGURED


@pytest.mark.asyncio
async def test_llm_service_capabilities_delegation():
    settings = LLMSettings()
    registry = LLMProviderRegistry()
    fake = FakeLLMProvider(LLMProviderID.GEMINI)
    registry.register(fake)

    service = LLMService(settings=settings, registry=registry)

    caps = await service.get_capabilities(LLMProviderID.GEMINI)
    assert caps.text_generation == CapabilitySupport.SUPPORTED
    assert caps.streaming == CapabilitySupport.SUPPORTED
    assert caps.tool_calling == CapabilitySupport.UNKNOWN
