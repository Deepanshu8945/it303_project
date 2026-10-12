from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    jwt_secret: str = Field(min_length=32)
    frontend_origin: str = "http://localhost:5173"
    storage_dir: Path = Path(".runtime/storage")
    mail_mode: Literal["local", "smtp", "brevo"] = "local"
    brevo_api_key: str = ""
    storage_backend: Literal["local", "supabase"] = "local"
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_storage_bucket: str = "converter-files"
    frontend_dist: Path | None = None
    environment: Literal["local", "production"] = "local"
    cleanup_interval_seconds: int = Field(default=30, ge=30)
    bootstrap_admin_email: str = ""
    bootstrap_admin_password: str = ""
    db_pool_size: int = Field(default=3, ge=1)
    db_max_overflow: int = Field(default=2, ge=0)
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_starttls: bool = False
    mail_from: str = "noreply@fileconverter.local"
    session_hours: int = 24
    retention_hours: int = 24
    max_upload_mb: int = 50
    nominal_threshold: int = 20
    weka_jar: Path = Path(".runtime/weka-3.8.6.jar")
    java_executable: str = "java"
    verification_timeout_seconds: int = Field(default=30, ge=1, le=120)

    @field_validator("frontend_dist", mode="before")
    @classmethod
    def empty_frontend_dist(cls, value):
        return value or None

    @model_validator(mode="after")
    def cloud_settings(self):
        if self.storage_backend == "supabase" and (
            not self.supabase_url.startswith("https://") or not self.supabase_service_role_key
        ):
            raise ValueError("Supabase storage requires HTTPS SUPABASE_URL and a server-side key.")
        if self.mail_mode == "brevo" and not self.brevo_api_key:
            raise ValueError("Brevo mail requires BREVO_API_KEY.")
        if self.environment == "production":
            if not self.frontend_origin.startswith("https://"):
                raise ValueError("Production FRONTEND_ORIGIN must use HTTPS.")
            if self.storage_backend != "supabase" or self.mail_mode != "brevo":
                raise ValueError(
                    "Free hosted deployment requires Supabase storage and Brevo email."
                )
        return self


@lru_cache
def settings():
    return Settings()
