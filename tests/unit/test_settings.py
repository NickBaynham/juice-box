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


def test_ignores_unrelated_env_file_keys(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("ANTHROPIC_API_KEY=sk-fake\n")
    assert Settings().api_port == 8000
