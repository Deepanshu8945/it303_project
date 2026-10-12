from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str
    jwt_secret: str = Field(min_length=32)
    frontend_origin: str = "http://localhost:5173"
    storage_dir: Path = Path(".runtime/storage")
    mail_mode: str = "local"
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


@lru_cache
def settings():
    return Settings()
