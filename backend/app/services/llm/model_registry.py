"""Configurable Model Registry for CodePilot LLM providers.

Maintains verified model metadata for all five supported cloud providers
(Gemini, OpenRouter, NVIDIA NIM, Groq, Ollama Cloud) including context
windows, output limits, capabilities, pricing tiers, and verification sources.

Allows registering or querying custom models dynamically so the application
does not require code changes whenever models are updated or retired.
"""

from __future__ import annotations

import threading
from typing import Sequence

from app.schemas.llm import (
    CapabilitySupport,
    LLMProviderID,
    ModelCapabilities,
    ModelMetadata,
)

# ---------------------------------------------------------------------------
# Verified Model Catalog (as verified from official provider documentation)
# ---------------------------------------------------------------------------

_VERIFIED_MODELS: list[ModelMetadata] = [
    # Google Gemini
    ModelMetadata(
        provider=LLMProviderID.GEMINI,
        model_id="gemini-2.0-flash",
        display_name="Google Gemini 2.0 Flash",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=1_048_576,
            max_output_tokens=8_192,
        ),
        context_window_tokens=1_048_576,
        max_output_tokens=8_192,
        supported_parameters=["temperature", "max_output_tokens", "system_instruction", "response_mime_type"],
        pricing_tier="free_tier_available",
        source_url="https://ai.google.dev/gemini-api/docs/models",
        last_verified_date="2026-03-01",
    ),
    ModelMetadata(
        provider=LLMProviderID.GEMINI,
        model_id="gemini-1.5-flash",
        display_name="Google Gemini 1.5 Flash",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=1_048_576,
            max_output_tokens=8_192,
        ),
        context_window_tokens=1_048_576,
        max_output_tokens=8_192,
        supported_parameters=["temperature", "max_output_tokens", "system_instruction", "response_mime_type"],
        pricing_tier="free_tier_available",
        source_url="https://ai.google.dev/gemini-api/docs/models",
        last_verified_date="2026-03-01",
    ),
    ModelMetadata(
        provider=LLMProviderID.GEMINI,
        model_id="gemini-1.5-pro",
        display_name="Google Gemini 1.5 Pro",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=2_097_152,
            max_output_tokens=8_192,
        ),
        context_window_tokens=2_097_152,
        max_output_tokens=8_192,
        supported_parameters=["temperature", "max_output_tokens", "system_instruction", "response_mime_type"],
        pricing_tier="free_tier_available",
        source_url="https://ai.google.dev/gemini-api/docs/models",
        last_verified_date="2026-03-01",
    ),

    # OpenRouter
    ModelMetadata(
        provider=LLMProviderID.OPENROUTER,
        model_id="openai/gpt-4o",
        display_name="OpenAI GPT-4o (OpenRouter)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=128_000,
            max_output_tokens=4_096,
        ),
        context_window_tokens=128_000,
        max_output_tokens=4_096,
        supported_parameters=["temperature", "max_tokens", "messages", "response_format"],
        pricing_tier="usage_based",
        source_url="https://openrouter.ai/models/openai/gpt-4o",
        last_verified_date="2026-03-01",
    ),
    ModelMetadata(
        provider=LLMProviderID.OPENROUTER,
        model_id="anthropic/claude-3.5-sonnet",
        display_name="Anthropic Claude 3.5 Sonnet (OpenRouter)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=200_000,
            max_output_tokens=8_192,
        ),
        context_window_tokens=200_000,
        max_output_tokens=8_192,
        supported_parameters=["temperature", "max_tokens", "messages", "response_format"],
        pricing_tier="usage_based",
        source_url="https://openrouter.ai/models/anthropic/claude-3.5-sonnet",
        last_verified_date="2026-03-01",
    ),
    ModelMetadata(
        provider=LLMProviderID.OPENROUTER,
        model_id="meta-llama/llama-3.1-8b-instruct:free",
        display_name="Llama 3.1 8B Instruct (OpenRouter Free)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=131_072,
            max_output_tokens=8_192,
        ),
        context_window_tokens=131_072,
        max_output_tokens=8_192,
        supported_parameters=["temperature", "max_tokens", "messages"],
        pricing_tier="free_tier_available",
        source_url="https://openrouter.ai/models/meta-llama/llama-3.1-8b-instruct:free",
        last_verified_date="2026-03-01",
    ),

    # NVIDIA NIM
    ModelMetadata(
        provider=LLMProviderID.NVIDIA_NIM,
        model_id="meta/llama-3.1-8b-instruct",
        display_name="Meta Llama 3.1 8B Instruct (NVIDIA NIM)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=131_072,
            max_output_tokens=4_096,
        ),
        context_window_tokens=131_072,
        max_output_tokens=4_096,
        supported_parameters=["temperature", "max_tokens", "messages"],
        pricing_tier="free_tier_available",
        source_url="https://build.nvidia.com/meta/llama-3_1-8b-instruct",
        last_verified_date="2026-03-01",
    ),
    ModelMetadata(
        provider=LLMProviderID.NVIDIA_NIM,
        model_id="meta/llama-3.1-70b-instruct",
        display_name="Meta Llama 3.1 70B Instruct (NVIDIA NIM)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=131_072,
            max_output_tokens=4_096,
        ),
        context_window_tokens=131_072,
        max_output_tokens=4_096,
        supported_parameters=["temperature", "max_tokens", "messages"],
        pricing_tier="free_tier_available",
        source_url="https://build.nvidia.com/meta/llama-3_1-70b-instruct",
        last_verified_date="2026-03-01",
    ),

    # Groq
    ModelMetadata(
        provider=LLMProviderID.GROQ,
        model_id="llama-3.1-8b-instant",
        display_name="Llama 3.1 8B Instant (Groq)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=131_072,
            max_output_tokens=8_192,
        ),
        context_window_tokens=131_072,
        max_output_tokens=8_192,
        supported_parameters=["temperature", "max_tokens", "messages", "response_format"],
        pricing_tier="free_tier_available",
        source_url="https://console.groq.com/docs/models",
        last_verified_date="2026-03-01",
    ),
    ModelMetadata(
        provider=LLMProviderID.GROQ,
        model_id="llama-3.3-70b-versatile",
        display_name="Llama 3.3 70B Versatile (Groq)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=131_072,
            max_output_tokens=32_768,
        ),
        context_window_tokens=131_072,
        max_output_tokens=32_768,
        supported_parameters=["temperature", "max_tokens", "messages", "response_format"],
        pricing_tier="free_tier_available",
        source_url="https://console.groq.com/docs/models",
        last_verified_date="2026-03-01",
    ),

    # Ollama Cloud (Remote Cloud Service)
    ModelMetadata(
        provider=LLMProviderID.OLLAMA_CLOUD,
        model_id="llama3.1",
        display_name="Meta Llama 3.1 (Ollama Cloud)",
        enabled=True,
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.SUPPORTED,
            tool_calling=CapabilitySupport.SUPPORTED,
            streaming=CapabilitySupport.SUPPORTED,
            context_window_tokens=131_072,
            max_output_tokens=4_096,
        ),
        context_window_tokens=131_072,
        max_output_tokens=4_096,
        supported_parameters=["temperature", "num_predict", "messages", "format"],
        pricing_tier="cloud_hosted",
        source_url="https://ollama.com/library/llama3.1",
        last_verified_date="2026-03-01",
    ),
]


class ModelRegistry:
    """Thread-safe centralized Model Registry for cloud LLM providers."""

    def __init__(self, initial_models: Sequence[ModelMetadata] | None = None) -> None:
        self._lock = threading.Lock()
        self._models: dict[tuple[LLMProviderID, str], ModelMetadata] = {}

        models_to_load = initial_models if initial_models is not None else _VERIFIED_MODELS
        for model in models_to_load:
            self.register_model(model)

    def register_model(self, model: ModelMetadata) -> None:
        """Register or update a model entry."""
        with self._lock:
            self._models[(model.provider, model.model_id)] = model

    def get_model(self, provider: LLMProviderID, model_id: str) -> ModelMetadata:
        """Return metadata for the requested model.

        If the model is not in the verified catalog, a fallback entry is generated
        with unknown capabilities rather than inventing metadata.
        """
        key = (provider, model_id)
        with self._lock:
            if key in self._models:
                return self._models[key]

        # Dynamically support configured / custom model IDs without guessing capabilities
        return ModelMetadata(
            provider=provider,
            model_id=model_id,
            display_name=f"{model_id} ({provider.value})",
            enabled=True,
            capabilities=ModelCapabilities(),  # Defaults to unknown
            context_window_tokens=None,
            max_output_tokens=None,
            supported_parameters=[],
            pricing_tier="unknown",
            source_url=None,
            last_verified_date=None,
        )

    def list_models(self, provider: LLMProviderID | None = None) -> list[ModelMetadata]:
        """List registered models, optionally filtered by provider."""
        with self._lock:
            all_models = list(self._models.values())

        if provider is not None:
            return [m for m in all_models if m.provider == provider]
        return all_models

    def has_model(self, provider: LLMProviderID, model_id: str) -> bool:
        """Check if a model is explicitly registered."""
        with self._lock:
            return (provider, model_id) in self._models

    def supports_capability(
        self,
        provider: LLMProviderID,
        model_id: str,
        capability: str,
    ) -> CapabilitySupport:
        """Query support for a capability (e.g. 'structured_json_output', 'tool_calling')."""
        model = self.get_model(provider, model_id)
        caps = model.capabilities
        if capability == "structured_json_output":
            return caps.structured_json_output
        elif capability == "tool_calling":
            return caps.tool_calling
        elif capability == "streaming":
            return caps.streaming
        elif capability == "text_generation":
            return caps.text_generation
        return CapabilitySupport.UNKNOWN

    def fits_context(
        self,
        provider: LLMProviderID,
        model_id: str,
        estimated_token_count: int,
    ) -> bool:
        """Verify whether an estimated token count fits within the model's context window.

        Returns True if the context window is unknown (caller must proceed with caution)
        or if estimated_token_count <= context_window_tokens.
        Returns False if the context window is known and exceeded.
        """
        model = self.get_model(provider, model_id)
        if model.context_window_tokens is None:
            return True
        return estimated_token_count <= model.context_window_tokens


# Global default singleton instance
_GLOBAL_MODEL_REGISTRY = ModelRegistry()


def get_model_registry() -> ModelRegistry:
    """Return the global ModelRegistry singleton."""
    return _GLOBAL_MODEL_REGISTRY


__all__ = [
    "ModelRegistry",
    "get_model_registry",
]
