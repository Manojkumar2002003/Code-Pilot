"""Tests for LLM API endpoints and LLM exception handlers."""

from fastapi.testclient import TestClient

from app.api.llm import get_llm_service
from app.core.llm_config import GeminiConfig, LLMSettings
from app.main import app
from app.schemas.llm import LLMError, LLMErrorCode, LLMProviderID
from app.services.llm.service import LLMService

client = TestClient(app)


def test_llm_status_endpoint_returns_expected_structure():
    response = client.get("/api/llm/status")
    assert response.status_code == 200

    data = response.json()
    assert "default_provider" in data
    assert "default_model" in data
    assert "providers" in data
    assert isinstance(data["providers"], list)

    # Must contain exactly the 5 planned cloud providers
    provider_ids = [p["provider"] for p in data["providers"]]
    assert set(provider_ids) == {
        "gemini",
        "openrouter",
        "nvidia_nim",
        "groq",
        "ollama_cloud",
    }

    # Verify no secrets or localhost URLs exist in response
    response_str = response.text.lower()
    assert "api_key" not in response_str
    assert "secret" not in response_str
    assert "localhost" not in response_str
    assert "127.0.0.1" not in response_str


def test_llm_status_endpoint_reports_configured_provider():
    # Configure custom settings with one provider configured
    custom_settings = LLMSettings(
        gemini=GeminiConfig(api_key="gemini-secret-test-key", default_model="gemini-2.0-flash"),
    )
    custom_service = LLMService(settings=custom_settings)

    app.dependency_overrides[get_llm_service] = lambda: custom_service
    try:
        response = client.get("/api/llm/status")
        assert response.status_code == 200
        data = response.json()

        gemini_entry = next(p for p in data["providers"] if p["provider"] == "gemini")
        assert gemini_entry["configured"] is True
        assert gemini_entry["default_model"] == "gemini-2.0-flash"

        groq_entry = next(p for p in data["providers"] if p["provider"] == "groq")
        assert groq_entry["configured"] is False

        # Confirm the secret was NOT returned
        assert "gemini-secret-test-key" not in response.text
    finally:
        app.dependency_overrides.pop(get_llm_service, None)


def test_llm_error_exception_handler_status_codes():
    test_cases = [
        (LLMErrorCode.INVALID_CREDENTIALS, 401),
        (LLMErrorCode.UNSUPPORTED_PROVIDER, 400),
        (LLMErrorCode.UNSUPPORTED_MODEL, 400),
        (LLMErrorCode.INVALID_REQUEST, 400),
        (LLMErrorCode.UNSUPPORTED_CAPABILITY, 400),
        (LLMErrorCode.PROVIDER_NOT_CONFIGURED, 400),
        (LLMErrorCode.RATE_LIMIT_EXCEEDED, 429),
        (LLMErrorCode.QUOTA_EXHAUSTED, 429),
        (LLMErrorCode.REQUEST_TIMEOUT, 504),
        (LLMErrorCode.NETWORK_ERROR, 502),
        (LLMErrorCode.INVALID_RESPONSE, 502),
        (LLMErrorCode.PROVIDER_OUTAGE, 503),
        (LLMErrorCode.INTERNAL_ERROR, 500),
    ]

    for err_code, expected_status in test_cases:
        def raise_llm_error():
            raise LLMError(
                code=err_code,
                message=f"Simulated error for {err_code.value}",
                provider=LLMProviderID.GEMINI,
            )

        endpoint_path = f"/debug-llm-error-{err_code.value.lower()}"
        app.add_api_route(endpoint_path, raise_llm_error, methods=["GET"])

        response = client.get(endpoint_path)
        assert response.status_code == expected_status, (
            f"Expected {expected_status} for {err_code.value}, got {response.status_code}"
        )

        payload = response.json()
        assert "error" in payload
        assert payload["error"]["code"] == err_code.value
        assert "Simulated error" in payload["error"]["message"]


def test_llm_models_endpoint():
    response = client.get("/api/llm/models")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5

    # Check model attributes
    first = data[0]
    assert "provider" in first
    assert "model_id" in first
    assert "capabilities" in first
    assert "display_name" in first

    # Filtering by provider
    filtered_resp = client.get("/api/llm/models?provider=gemini")
    assert filtered_resp.status_code == 200
    filtered_data = filtered_resp.json()
    assert all(m["provider"] == "gemini" for m in filtered_data)


def test_llm_health_check_endpoint():
    response = client.post("/api/llm/health/check")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)
    assert "gemini" in data
    assert "openrouter" in data


def test_llm_generate_endpoint_with_mock_service():
    from app.schemas.llm import LLMResponse, TokenUsage

    custom_settings = LLMSettings()
    custom_service = LLMService(settings=custom_settings)

    async def mock_generate(request):
        return LLMResponse(
            content="Mocked response content",
            provider=LLMProviderID.GEMINI,
            model="gemini-2.0-flash",
            token_usage=TokenUsage(total_tokens=42),
            finish_reason="stop",
        )

    custom_service.generate = mock_generate

    app.dependency_overrides[get_llm_service] = lambda: custom_service
    try:
        payload = {
            "messages": [{"role": "user", "content": "Hello"}],
            "temperature": 0.5,
        }
        response = client.post("/api/llm/generate", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Mocked response content"
        assert data["provider"] == "gemini"
        assert data["token_usage"]["total_tokens"] == 42
    finally:
        app.dependency_overrides.pop(get_llm_service, None)
