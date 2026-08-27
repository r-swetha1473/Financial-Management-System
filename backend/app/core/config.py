"""Application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Default matches Docker Compose (.env.docker, host port 5433).
    # Override with DATABASE_URL. Vercel/Supabase may also inject POSTGRES_URL.
    database_url: str = "postgresql+asyncpg://bfms:bfms_dev_password@localhost:5433/bfms"
    postgres_url: str | None = None
    postgres_url_non_pooling: str | None = None
    secret_key: str = "dev-secret-change-in-production"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7
    cors_origins: str = "http://localhost:4200"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def sqlalchemy_database_url(self) -> str:
        """Accept postgres:// or postgresql:// from hosted providers; local URLs already include +asyncpg."""
        local_default = "postgresql+asyncpg://bfms:bfms_dev_password@localhost:5433/bfms"
        hosted = (self.postgres_url or "").strip() or (self.postgres_url_non_pooling or "").strip()
        explicit = (self.database_url or "").strip()
        url = explicit
        if hosted and (not url or url == local_default):
            url = hosted
        if not url:
            url = local_default
        if url.startswith("postgres://"):
            url = "postgresql://" + url[len("postgres://") :]
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://") :]
        return url


settings = Settings()
