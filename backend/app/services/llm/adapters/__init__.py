"""Cloud LLM provider adapters for CodePilot."""

from app.services.llm.adapters.gemini import GeminiAdapter
from app.services.llm.adapters.groq import GroqAdapter
from app.services.llm.adapters.nvidia_nim import NvidiaNimAdapter
from app.services.llm.adapters.ollama_cloud import OllamaCloudAdapter
from app.services.llm.adapters.openrouter import OpenRouterAdapter

__all__ = [
    "GeminiAdapter",
    "GroqAdapter",
    "NvidiaNimAdapter",
    "OllamaCloudAdapter",
    "OpenRouterAdapter",
]
