from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    DATABASE_URL: str = ""
    GOOGLE_MAPS_API_KEY: str | None = None
    GOOGLE_CLIENT_ID: str | None = None
    GOOGLE_CLIENT_SECRET: str | None = None
    TOKEN_ENCRYPTION_KEY: str | None = None
    OPENAI_API_KEY: str | None = None
    ELEVENLABS_API_KEY: str | None = None
    ELEVENLABS_AGENT_ID: str | None = None
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]
    DEBUG: bool = False


settings = Settings()
