"""Unit tests for configuration safeguards (mock auth, feature flags)."""
from __future__ import annotations

from app.core.config import Settings

_SECRET = "test-secret-key-must-be-at-least-32-characters-long"


def _settings(**overrides: object) -> Settings:
    base: dict[str, object] = {
        "app_secret_key": _SECRET,
        "postgres_password": "x",
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


class TestMockAuthSafeguard:
    def test_enabled_in_development(self) -> None:
        s = _settings(app_env="development", mock_auth=True)
        assert s.mock_auth_enabled is True

    def test_enabled_in_test(self) -> None:
        s = _settings(app_env="test", mock_auth=True)
        assert s.mock_auth_enabled is True

    def test_hard_disabled_in_production(self) -> None:
        # Even explicitly set, mock auth is ignored in production.
        s = _settings(app_env="production", mock_auth=True)
        assert s.mock_auth_enabled is False

    def test_off_by_default(self) -> None:
        s = _settings(app_env="development")
        assert s.mock_auth is False
        assert s.mock_auth_enabled is False


class TestFeatureFlags:
    def test_defaults(self) -> None:
        s = _settings(app_env="development")
        assert s.feature_ai_chat_enabled is True
        assert s.feature_analytics_enabled is False
        assert s.feature_notifications_enabled is False

    def test_overridable(self) -> None:
        s = _settings(app_env="development", feature_analytics_enabled=True)
        assert s.feature_analytics_enabled is True
