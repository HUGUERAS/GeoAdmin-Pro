import pytest

from core.config import Settings


def _settings(**overrides):
    settings = Settings()
    settings.APP_ENV = "production"
    settings.SUPABASE_URL = "https://example.supabase.co"
    settings.SUPABASE_ANON_KEY = "anon"
    settings.SUPABASE_SERVICE_ROLE_KEY = "service"
    settings.SUPABASE_JWT_SECRET = ""

    for key, value in overrides.items():
        setattr(settings, key, value)

    return settings


def test_validate_production_does_not_require_unused_jwt_secret():
    _settings(SUPABASE_JWT_SECRET="").validate()


def test_validate_production_still_requires_service_role_key():
    settings = _settings(SUPABASE_SERVICE_ROLE_KEY="")

    with pytest.raises(ValueError, match="SUPABASE_SERVICE_ROLE_KEY"):
        settings.validate()
