"""Tests for LLM configuration, validation, and defaults."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.core.llm_config import (
    GeminiConfig,
    GroqConfig,
    LLMSettings,
)
from app.schemas.llm import LLMProviderID


def test_default_llm_settings():
    settings = LLMSettings()

    assert settings.default_provider == LLMProviderID.GEMINI
    assert settings.default_timeout_seconds == 60.0
    assert settings.default_temperature == 0.7
    assert settings.default_max_output_tokens == 4096

    assert settings.gemini.default_model == "gemini-2.0-flash"
    assert settings.openrouter.default_model == "openai/gpt-4o"
    assert settings.nvidia_nim.default_model == "meta/llama-3.1-8b-instruct"
    assert settings.groq.default_model == "llama-3.1-8b-instant"
    assert settings.ollama_cloud.default_model == "llama3.1"


def test_missing_credentials_for_optional_providers():
    settings = LLMSettings()

    # None of the providers have API keys set by default
    for provider in LLMProviderID:
        assert settings.is_provider_configured(provider) is False


def test_provider_configuration_status():
    settings = LLMSettings(
        gemini=GeminiConfig(api_key="gemini-secret-test-key"),
        groq=GroqConfig(api_key="   "),  # Blank string should not count as configured
    )

    assert settings.is_provider_configured(LLMProviderID.GEMINI) is True
    assert settings.is_provider_configured(LLMProviderID.GROQ) is False
    assert settings.is_provider_configured(LLMProviderID.OPENROUTER) is False


def test_provider_enablement_toggle():
    settings = LLMSettings(
        gemini=GeminiConfig(api_key="valid-key", enabled=False),
    )

    # Even with an API key, if enabled=False, is_provider_configured is False
    assert settings.is_provider_configured(LLMProviderID.GEMINI) is False


def test_ollama_cloud_is_cloud_not_local():
    settings = LLMSettings()

    # Verify that default base URL for Ollama Cloud is a cloud endpoint, never localhost or 127.0.0.1
    assert "localhost" not in settings.ollama_cloud.base_url.lower()
    assert "127.0.0.1" not in settings.ollama_cloud.base_url.lower()
    assert settings.ollama_cloud.base_url.startswith("https://")


def test_environment_override_for_llm_settings(monkeypatch):
    monkeypatch.setenv("LLM_DEFAULT_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_DEFAULT_TIMEOUT_SECONDS", "30.0")
    monkeypatch.setenv("LLM_DEFAULT_TEMPERATURE", "0.2")
    monkeypatch.setenv("LLM_OPENROUTER_API_KEY", "test-or-key")
    monkeypatch.setenv("LLM_OPENROUTER_DEFAULT_MODEL", "anthropic/claude-3.5-sonnet")

    app_settings = Settings()
    llm_settings = app_settings.build_llm_settings()

    assert llm_settings.default_provider == LLMProviderID.OPENROUTER
    assert llm_settings.default_timeout_seconds == 30.0
    assert llm_settings.default_temperature == 0.2
    assert llm_settings.openrouter.api_key == "test-or-key"
    assert llm_settings.openrouter.default_model == "anthropic/claude-3.5-sonnet"
    assert llm_settings.is_provider_configured(LLMProviderID.OPENROUTER) is True


def test_invalid_provider_identifier_raises_validation_error():
    with pytest.raises(ValidationError):
        LLMSettings(default_provider="invalid_provider")  # type: ignore


def test_invalid_generation_parameters_raise_validation_error():
    with pytest.raises(ValidationError):
        LLMSettings(default_temperature=3.5)  # Max is 2.0

    with pytest.raises(ValidationError):
        LLMSettings(default_timeout_seconds=-10.0)

    with pytest.raises(ValidationError):
        LLMSettings(default_max_output_tokens=0)
