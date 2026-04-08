from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    SECRET_KEY: str = "dev-secret-key-change-in-production"
    DEFAULT_ADMIN_USERNAME: str = "admin"
    DEFAULT_ADMIN_PASSWORD: str = "admin"
    DATABASE_URL: str = "sqlite+aiosqlite:///./stockpilot.db"


settings = Settings()