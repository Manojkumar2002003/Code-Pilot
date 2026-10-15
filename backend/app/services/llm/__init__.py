"""LLM service layer — provider interface, adapters, registry, router, and service.

This package exposes:
- ``BaseLLMProvider``: Abstract base class for cloud provider adapters.
- ``LLMProviderRegistry``: Thread-safe registry for provider adapters.
- ``LLMService``: High-level service consumed by API routes and agents.
- ``ModelRegistry``: Catalog of verified models and capabilities.
- ``LLMRouter`` & ``CircuitBreaker``: Intelligent failover and routing coordinator.
- Concrete adapters for Gemini, OpenRouter, NVIDIA NIM, Groq, and Ollama Cloud.
"""

from app.services.llm.adapters import (
    GeminiAdapter,
    GroqAdapter,
    NvidiaNimAdapter,
    OllamaCloudAdapter,
    OpenRouterAdapter,
)
from app.services.llm.model_registry import ModelRegistry, get_model_registry
from app.services.llm.provider import BaseLLMProvider
from app.services.llm.registry import LLMProviderRegistry
from app.services.llm.router import CircuitBreaker, LLMRouter
from app.services.llm.service import LLMService, build_default_registry

__all__ = [
    "BaseLLMProvider",
    "CircuitBreaker",
    "GeminiAdapter",
    "GroqAdapter",
    "LLMProviderRegistry",
    "LLMRouter",
    "LLMService",
    "ModelRegistry",
    "NvidiaNimAdapter",
    "OllamaCloudAdapter",
    "OpenRouterAdapter",
    "build_default_registry",
    "get_model_registry",
]
