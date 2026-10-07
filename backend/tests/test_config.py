from app.core.config import Settings, get_settings


def test_default_settings_are_loaded():
    settings = Settings()

    assert settings.app_name == "CodePilot API"
    assert settings.app_env == "development"
    assert settings.debug is True
    assert settings.api_prefix == "/api"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_settings_can_be_overridden_via_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("PORT", "9000")

    settings = Settings()

    assert settings.app_env == "test"
    assert settings.port == 9000


def test_get_settings_returns_singleton_like_object():
    first = get_settings()
    second = get_settings()

    assert first is second
