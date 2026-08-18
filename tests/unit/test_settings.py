from juicebox.config.settings import Settings


def test_defaults():
    settings = Settings()
    assert settings.api_host == "0.0.0.0"
    assert settings.api_port == 8000
    assert settings.log_level == "INFO"
    assert settings.database_url.startswith("postgresql+asyncpg://")


def test_environment_overrides(monkeypatch):
    monkeypatch.setenv("JUICEBOX_API_PORT", "9000")
    assert Settings().api_port == 9000
