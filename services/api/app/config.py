from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ORT API"
    app_env: str = "development"
    api_prefix: str = "/api/v1"
    database_url: str = Field(alias="DATABASE_URL")
    jwt_secret: str | None = Field(default=None, alias="JWT_SECRET")
    session_secret: str | None = Field(default=None, alias="SESSION_SECRET")
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    otp_dev_mode: bool = False
    twilio_account_sid: str | None = Field(default=None, alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str | None = Field(default=None, alias="TWILIO_AUTH_TOKEN")
    twilio_from_number: str | None = Field(default=None, alias="TWILIO_FROM_NUMBER")

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def signing_secret(self) -> str:
        secret = self.jwt_secret or self.session_secret
        if not secret:
            raise RuntimeError("JWT_SECRET or SESSION_SECRET must be configured")
        if self.app_env == "production" and len(secret) < 32:
            raise RuntimeError("JWT_SECRET must contain at least 32 characters in production")
        return secret

    @property
    def allowed_origins(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
