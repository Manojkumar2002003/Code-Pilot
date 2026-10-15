"""Tests for LLM contracts: Request, Response, Capabilities, and Error models."""

import pytest
from pydantic import ValidationError

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
    StructuredOutputRequirement,
    TokenUsage,
    UnsupportedCapabilityError,
)


def test_request_contract_valid():
    req = LLMRequest(
        provider=LLMProviderID.GEMINI,
        model="gemini-2.0-flash",
        system_instruction="You are a helpful coding assistant.",
        messages=[
            ConversationMessage(role=MessageRole.USER, content="Hello!"),
            ConversationMessage(role=MessageRole.ASSISTANT, content="Hi there!"),
            ConversationMessage(role=MessageRole.USER, content="Explain async in Python."),
        ],
        temperature=0.5,
        max_output_tokens=1024,
        structured_output=StructuredOutputRequirement(
            json_schema={"type": "object", "properties": {"summary": {"type": "string"}}},
            description="A JSON summary",
        ),
        timeout_seconds=30.0,
        metadata={"agent": "architect", "step": 1},
    )

    assert req.provider == LLMProviderID.GEMINI
    assert req.model == "gemini-2.0-flash"
    assert len(req.messages) == 3
    assert req.temperature == 0.5
    assert req.max_output_tokens == 1024
    assert req.structured_output is not None
    assert req.metadata == {"agent": "architect", "step": 1}


def test_request_contract_invalid_temperature():
    with pytest.raises(ValidationError):
        LLMRequest(
            provider=LLMProviderID.GROQ,
            model="llama-3.1-8b-instant",
            temperature=2.5,  # Exceeds max 2.0
        )


def test_response_contract_valid():
    resp = LLMResponse(
        content="Here is the explanation.",
        provider=LLMProviderID.GROQ,
        model="llama-3.1-8b-instant",
        token_usage=TokenUsage(
            prompt_tokens=25,
            completion_tokens=150,
            total_tokens=175,
        ),
        duration_seconds=0.42,
        finish_reason="stop",
        structured_output=None,
        metadata={"request_id": "req-123"},
    )

    assert resp.content == "Here is the explanation."
    assert resp.provider == LLMProviderID.GROQ
    assert resp.token_usage.total_tokens == 175
    assert resp.duration_seconds == 0.42
    assert resp.finish_reason == "stop"
    assert resp.created_at is not None


def test_capabilities_representation_defaults_to_unknown():
    caps = ModelCapabilities()

    assert caps.text_generation == CapabilitySupport.UNKNOWN
    assert caps.structured_json_output == CapabilitySupport.UNKNOWN
    assert caps.tool_calling == CapabilitySupport.UNKNOWN
    assert caps.streaming == CapabilitySupport.UNKNOWN
    assert caps.context_window_tokens is None
    assert caps.max_output_tokens is None


def test_capabilities_explicit_declaration():
    caps = ModelCapabilities(
        text_generation=CapabilitySupport.SUPPORTED,
        structured_json_output=CapabilitySupport.SUPPORTED,
        tool_calling=CapabilitySupport.UNSUPPORTED,
        streaming=CapabilitySupport.SUPPORTED,
        context_window_tokens=128000,
        max_output_tokens=8192,
    )

    assert caps.text_generation == CapabilitySupport.SUPPORTED
    assert caps.structured_json_output == CapabilitySupport.SUPPORTED
    assert caps.tool_calling == CapabilitySupport.UNSUPPORTED
    assert caps.context_window_tokens == 128000
    assert caps.max_output_tokens == 8192


def test_llm_error_retryability():
    # Retryable errors
    err_rate_limit = LLMError(LLMErrorCode.RATE_LIMIT_EXCEEDED, "Rate limit reached")
    assert err_rate_limit.is_retryable is True

    err_timeout = LLMError(LLMErrorCode.REQUEST_TIMEOUT, "Timed out")
    assert err_timeout.is_retryable is True

    err_network = LLMError(LLMErrorCode.NETWORK_ERROR, "Network unreachable")
    assert err_network.is_retryable is True

    err_outage = LLMError(LLMErrorCode.PROVIDER_OUTAGE, "Service unavailable")
    assert err_outage.is_retryable is True

    # Non-retryable errors
    err_auth = LLMError(LLMErrorCode.INVALID_CREDENTIALS, "Invalid auth token")
    assert err_auth.is_retryable is False

    err_model = LLMError(LLMErrorCode.UNSUPPORTED_MODEL, "Model not supported")
    assert err_model.is_retryable is False

    err_param = LLMError(LLMErrorCode.UNSUPPORTED_PARAMETER, "Invalid parameter")
    assert err_param.is_retryable is False


def test_llm_error_secret_redaction():
    # If an exception message inadvertently contains a secret keyword
    leak_attempt = "Error communicating with upstream: api_key=sk-1234567890abcdef failed"
    err = LLMError(LLMErrorCode.INVALID_CREDENTIALS, leak_attempt)

    assert "sk-1234567890abcdef" not in str(err)
    assert "[REDACTED]" in str(err)

    safe_dict = err.to_safe_dict()
    assert "sk-1234567890abcdef" not in safe_dict["message"]
    assert "[REDACTED]" in safe_dict["message"]
    assert safe_dict["code"] == "INVALID_CREDENTIALS"


def test_unsupported_capability_error():
    err = UnsupportedCapabilityError(
        capability="tool_calling",
        provider=LLMProviderID.NVIDIA_NIM,
        model="meta/llama-3.1-8b-instruct",
    )

    assert err.code == LLMErrorCode.UNSUPPORTED_CAPABILITY
    assert err.capability == "tool_calling"
    assert err.provider == LLMProviderID.NVIDIA_NIM
    assert err.model == "meta/llama-3.1-8b-instruct"
    assert err.is_retryable is False
    assert "tool_calling" in str(err)
