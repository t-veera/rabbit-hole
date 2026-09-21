from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://rabbithole:rabbithole@localhost:5433/rabbithole"

    anthropic_api_key: str | None = None
    unpaywall_email: str = "you@example.com"
    openalex_mailto: str | None = None
    ncbi_api_key: str | None = None
    semantic_scholar_api_key: str | None = None
    core_api_key: str | None = None

    cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
