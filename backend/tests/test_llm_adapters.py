"""Comprehensive tests for the five cloud LLM provider adapters."""

import pytest
import httpx

from app.core.llm_config import (
    GeminiConfig,
    GroqConfig,
    NvidiaNimConfig,
    OllamaCloudConfig,
    OpenRouterConfig,
)
from app.schemas.llm import (
    ConversationMessage,
    LLMError,
    LLMErrorCode,
    LLMProviderID,
    LLMRequest,
    MessageRole,
    ProviderHealthState,
    StructuredOutputRequirement,
)
from app.services.llm.adapters import (
    GeminiAdapter,
    GroqAdapter,
    NvidiaNimAdapter,
    OllamaCloudAdapter,
    OpenRouterAdapter,
)


# ===========================================================================
# Gemini Adapter Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_gemini_adapter_generation_success():
    mock_response_data = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Hello from Gemini!"}],
                    "role": "model",
                },
                "finishReason": "STOP",
            }
        ],
        "usageMetadata": {
            "promptTokenCount": 10,
            "candidatesTokenCount": 15,
            "totalTokenCount": 25,
        },
        "modelVersion": "gemini-2.0-flash",
    }

    captured_request = None

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_request
        captured_request = request
        assert request.headers.get("x-goog-api-key") == "test-gemini-key"
        assert "models/gemini-2.0-flash:generateContent" in str(request.url)
        return httpx.Response(200, json=mock_response_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        config = GeminiConfig(api_key="test-gemini-key", default_model="gemini-2.0-flash")
        adapter = GeminiAdapter(config=config, http_client=client)

        req = LLMRequest(
            provider=LLMProviderID.GEMINI,
            model="gemini-2.0-flash",
            system_instruction="You are a helpful assistant.",
            messages=[ConversationMessage(role=MessageRole.USER, content="Hello")],
            temperature=0.4,
            max_output_tokens=500,
            structured_output=StructuredOutputRequirement(description="JSON format"),
        )

        resp = await adapter.generate(req)

        assert resp.content == "Hello from Gemini!"
        assert resp.provider == LLMProviderID.GEMINI
        assert resp.model == "gemini-2.0-flash"
        assert resp.token_usage is not None
        assert resp.token_usage.total_tokens == 25
        assert resp.finish_reason == "STOP"
        assert resp.metadata.get("modelVersion") == "gemini-2.0-flash"


@pytest.mark.asyncio
async def test_gemini_adapter_rate_limit_and_quota_error():
    # 1. Standard rate limit 429
    def rate_limit_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "Resource has been exhausted (rate limit)"}})

    transport = httpx.MockTransport(rate_limit_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiAdapter(config=GeminiConfig(api_key="key"), http_client=client)
        with pytest.raises(LLMError) as exc_info:
            await adapter.generate(LLMRequest(provider=LLMProviderID.GEMINI, model="gemini-2.0-flash"))
        assert exc_info.value.code == LLMErrorCode.RATE_LIMIT_EXCEEDED

    # 2. Quota limit 429
    def quota_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": {"message": "You have exceeded your daily quota limit."}})

    transport = httpx.MockTransport(quota_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiAdapter(config=GeminiConfig(api_key="key"), http_client=client)
        with pytest.raises(LLMError) as exc_info:
            await adapter.generate(LLMRequest(provider=LLMProviderID.GEMINI, model="gemini-2.0-flash"))
        assert exc_info.value.code == LLMErrorCode.QUOTA_EXHAUSTED


@pytest.mark.asyncio
async def test_gemini_adapter_health_check():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"models": [{"name": "models/gemini-2.0-flash"}]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GeminiAdapter(config=GeminiConfig(api_key="key"), http_client=client)
        status = await adapter.check_health()
        assert status == ProviderHealthState.AVAILABLE


# ===========================================================================
# OpenRouter Adapter Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_openrouter_adapter_generation_success():
    mock_data = {
        "id": "gen-12345",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Hello from OpenRouter!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 8, "completion_tokens": 12, "total_tokens": 20},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer or-key-123"
        assert request.headers.get("HTTP-Referer") == "https://codepilot.dev"
        assert request.headers.get("X-Title") == "CodePilot"
        assert "/chat/completions" in str(request.url)
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        config = OpenRouterConfig(api_key="or-key-123", default_model="openai/gpt-4o")
        adapter = OpenRouterAdapter(config=config, http_client=client)

        req = LLMRequest(
            provider=LLMProviderID.OPENROUTER,
            model="openai/gpt-4o",
            messages=[ConversationMessage(role=MessageRole.USER, content="Hi")],
        )
        resp = await adapter.generate(req)

        assert resp.content == "Hello from OpenRouter!"
        assert resp.provider == LLMProviderID.OPENROUTER
        assert resp.model == "openai/gpt-4o"
        assert resp.token_usage.total_tokens == 20


@pytest.mark.asyncio
async def test_openrouter_insufficient_credits_402():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(402, json={"error": {"message": "Insufficient credits"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenRouterAdapter(config=OpenRouterConfig(api_key="key"), http_client=client)
        with pytest.raises(LLMError) as exc_info:
            await adapter.generate(LLMRequest(provider=LLMProviderID.OPENROUTER, model="openai/gpt-4o"))
        assert exc_info.value.code == LLMErrorCode.QUOTA_EXHAUSTED


@pytest.mark.asyncio
async def test_openrouter_health_check():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/key" in str(request.url)
        return httpx.Response(200, json={"data": {"label": "CodePilot Key", "limit": 100}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = OpenRouterAdapter(config=OpenRouterConfig(api_key="key"), http_client=client)
        status = await adapter.check_health()
        assert status == ProviderHealthState.AVAILABLE


# ===========================================================================
# NVIDIA NIM Adapter Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_nvidia_nim_adapter_generation_success():
    mock_data = {
        "id": "nim-999",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Hello from NVIDIA NIM!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 15, "completion_tokens": 20, "total_tokens": 35},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer nvapi-test"
        assert "/chat/completions" in str(request.url)
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        config = NvidiaNimConfig(api_key="nvapi-test", default_model="meta/llama-3.1-8b-instruct")
        adapter = NvidiaNimAdapter(config=config, http_client=client)

        req = LLMRequest(
            provider=LLMProviderID.NVIDIA_NIM,
            model="meta/llama-3.1-8b-instruct",
            messages=[ConversationMessage(role=MessageRole.USER, content="Hello")],
        )
        resp = await adapter.generate(req)

        assert resp.content == "Hello from NVIDIA NIM!"
        assert resp.provider == LLMProviderID.NVIDIA_NIM
        assert resp.token_usage.total_tokens == 35


@pytest.mark.asyncio
async def test_nvidia_nim_health_check():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/models" in str(request.url)
        return httpx.Response(200, json={"data": [{"id": "meta/llama-3.1-8b-instruct"}]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = NvidiaNimAdapter(config=NvidiaNimConfig(api_key="key"), http_client=client)
        status = await adapter.check_health()
        assert status == ProviderHealthState.AVAILABLE


# ===========================================================================
# Groq Adapter Tests
# ===========================================================================

@pytest.mark.asyncio
async def test_groq_adapter_generation_success():
    mock_data = {
        "id": "chatcmpl-groq",
        "choices": [
            {
                "message": {"role": "assistant", "content": "Lightning fast Groq!"},
                "finish_reason": "stop",
            }
        ],
        "usage": {"prompt_tokens": 5, "completion_tokens": 10, "total_tokens": 15},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer gsk-key"
        assert "/chat/completions" in str(request.url)
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        config = GroqConfig(api_key="gsk-key", default_model="llama-3.1-8b-instant")
        adapter = GroqAdapter(config=config, http_client=client)

        req = LLMRequest(
            provider=LLMProviderID.GROQ,
            model="llama-3.1-8b-instant",
            messages=[ConversationMessage(role=MessageRole.USER, content="Speed test")],
        )
        resp = await adapter.generate(req)

        assert resp.content == "Lightning fast Groq!"
        assert resp.provider == LLMProviderID.GROQ
        assert resp.token_usage.total_tokens == 15


@pytest.mark.asyncio
async def test_groq_adapter_rate_limit_with_retry_after():
    def handler(request: httpx.Request) -> httpx.Response:
        headers = {"retry-after": "5.5"}
        return httpx.Response(429, headers=headers, json={"error": {"message": "Rate limit exceeded (TPM)"}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        adapter = GroqAdapter(config=GroqConfig(api_key="key"), http_client=client)
        with pytest.raises(LLMError) as exc_info:
            await adapter.generate(LLMRequest(provider=LLMProviderID.GROQ, model="llama-3.1-8b-instant"))

        assert exc_info.value.code == LLMErrorCode.RATE_LIMIT_EXCEEDED
        assert exc_info.value.retry_after == 5.5


# ===========================================================================
# Ollama Cloud Adapter Tests
# ===========================================================================

def test_ollama_cloud_rejects_localhost_endpoint():
    # Local Ollama must be strictly rejected
    for invalid_url in [
        "http://localhost:11434",
        "http://127.0.0.1:11434",
        "http://0.0.0.0:11434",
        "http://192.168.1.50:11434",
    ]:
        with pytest.raises(LLMError) as exc_info:
            OllamaCloudAdapter(config=OllamaCloudConfig(api_key="cloud-key", base_url=invalid_url))
        assert exc_info.value.code == LLMErrorCode.INVALID_REQUEST
        assert "Local Ollama endpoints are not supported" in str(exc_info.value)


@pytest.mark.asyncio
async def test_ollama_cloud_adapter_generation_success():
    mock_data = {
        "model": "llama3.1",
        "message": {"role": "assistant", "content": "Hello from Ollama Cloud!"},
        "done": True,
        "done_reason": "stop",
        "prompt_eval_count": 14,
        "eval_count": 22,
        "total_duration": 1500000000,
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers.get("Authorization") == "Bearer oc-key"
        assert "api.ollama.com" in str(request.url)
        assert "/api/chat" in str(request.url)
        return httpx.Response(200, json=mock_data)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        config = OllamaCloudConfig(
            api_key="oc-key",
            base_url="https://api.ollama.com",
            default_model="llama3.1",
        )
        adapter = OllamaCloudAdapter(config=config, http_client=client)

        req = LLMRequest(
            provider=LLMProviderID.OLLAMA_CLOUD,
            model="llama3.1",
            messages=[ConversationMessage(role=MessageRole.USER, content="Hello")],
        )
        resp = await adapter.generate(req)

        assert resp.content == "Hello from Ollama Cloud!"
        assert resp.provider == LLMProviderID.OLLAMA_CLOUD
        assert resp.token_usage.prompt_tokens == 14
        assert resp.token_usage.completion_tokens == 22
        assert resp.token_usage.total_tokens == 36
        assert resp.finish_reason == "stop"


@pytest.mark.asyncio
async def test_ollama_cloud_health_check():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "/api/tags" in str(request.url)
        return httpx.Response(200, json={"models": [{"name": "llama3.1"}]})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        config = OllamaCloudConfig(api_key="key", base_url="https://api.ollama.com")
        adapter = OllamaCloudAdapter(config=config, http_client=client)
        status = await adapter.check_health()
        assert status == ProviderHealthState.AVAILABLE
