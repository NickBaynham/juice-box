"""Application settings read from the environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration, overridable by JUICEBOX_-prefixed variables."""

    model_config = SettingsConfigDict(env_prefix="JUICEBOX_", env_file=".env")

    api_host: str = "0.0.0.0"
    api_port: int = 8000
    log_level: str = "INFO"
    database_url: str = "postgresql+asyncpg://juicebox:juicebox@localhost:5432/juicebox"
