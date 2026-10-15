"""Tests for the Model Registry and capability verification."""


from app.schemas.llm import (
    CapabilitySupport,
    LLMProviderID,
    ModelCapabilities,
    ModelMetadata,
)
from app.services.llm.model_registry import ModelRegistry, get_model_registry


def test_verified_models_catalog_loaded():
    registry = get_model_registry()
    models = registry.list_models()

    assert len(models) >= 5

    # Check presence of verified models for each provider
    providers_present = {m.provider for m in models}
    assert providers_present == {
        LLMProviderID.GEMINI,
        LLMProviderID.OPENROUTER,
        LLMProviderID.NVIDIA_NIM,
        LLMProviderID.GROQ,
        LLMProviderID.OLLAMA_CLOUD,
    }


def test_model_capabilities_and_metadata_retrieval():
    registry = get_model_registry()

    gemini_flash = registry.get_model(LLMProviderID.GEMINI, "gemini-2.0-flash")
    assert gemini_flash.model_id == "gemini-2.0-flash"
    assert gemini_flash.context_window_tokens == 1_048_576
    assert gemini_flash.max_output_tokens == 8_192
    assert gemini_flash.capabilities.text_generation == CapabilitySupport.SUPPORTED
    assert gemini_flash.capabilities.structured_json_output == CapabilitySupport.SUPPORTED
    assert gemini_flash.pricing_tier == "free_tier_available"
    assert "https://ai.google.dev" in gemini_flash.source_url


def test_unknown_custom_model_representation():
    registry = get_model_registry()

    # When querying an unverified custom model ID, capabilities must default to UNKNOWN
    custom_model = registry.get_model(LLMProviderID.GROQ, "custom-unreleased-model-xyz")
    assert custom_model.model_id == "custom-unreleased-model-xyz"
    assert custom_model.capabilities.structured_json_output == CapabilitySupport.UNKNOWN
    assert custom_model.capabilities.text_generation == CapabilitySupport.UNKNOWN
    assert custom_model.context_window_tokens is None
    assert custom_model.pricing_tier == "unknown"


def test_custom_model_registration():
    registry = ModelRegistry()

    new_model = ModelMetadata(
        provider=LLMProviderID.NVIDIA_NIM,
        model_id="custom-nim-model",
        display_name="Custom NIM Model",
        capabilities=ModelCapabilities(
            text_generation=CapabilitySupport.SUPPORTED,
            structured_json_output=CapabilitySupport.UNSUPPORTED,
        ),
        context_window_tokens=32000,
        max_output_tokens=2048,
    )

    registry.register_model(new_model)

    retrieved = registry.get_model(LLMProviderID.NVIDIA_NIM, "custom-nim-model")
    assert retrieved.display_name == "Custom NIM Model"
    assert retrieved.capabilities.structured_json_output == CapabilitySupport.UNSUPPORTED


def test_fits_context_window():
    registry = get_model_registry()

    # Model with 128k context
    # 50,000 tokens should fit
    assert registry.fits_context(LLMProviderID.OPENROUTER, "openai/gpt-4o", 50000) is True

    # 200,000 tokens should NOT fit in 128k context
    assert registry.fits_context(LLMProviderID.OPENROUTER, "openai/gpt-4o", 200000) is False

    # Model with unknown context window should return True (safe fallback)
    assert registry.fits_context(LLMProviderID.GROQ, "unknown-model", 500000) is True
