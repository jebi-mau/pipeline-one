"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, RedisDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Pipeline One"
    app_env: Literal["development", "production", "testing"] = "development"
    debug: bool = True

    # API Server
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "svo2_analyzer"
    postgres_password: str = "svo2_analyzer_dev"
    postgres_db: str = "svo2_analyzer"
    database_url: PostgresDsn | None = None

    @field_validator("database_url", mode="before")
    @classmethod
    def assemble_db_connection(cls, v: str | None, info) -> str:
        if v is not None:
            return v
        return (
            f"postgresql+asyncpg://{info.data['postgres_user']}:"
            f"{info.data['postgres_password']}@{info.data['postgres_host']}:"
            f"{info.data['postgres_port']}/{info.data['postgres_db']}"
        )

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_url: RedisDsn | None = None

    @field_validator("redis_url", mode="before")
    @classmethod
    def assemble_redis_connection(cls, v: str | None, info) -> str:
        if v is not None:
            return v
        return f"redis://{info.data['redis_host']}:{info.data['redis_port']}/{info.data['redis_db']}"

    # Celery
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"

    # Data Paths
    data_root: Path = Field(default=Path("/home/atlas/dev/pipe1/data"))
    svo2_directory: Path | None = None
    output_directory: Path | None = None
    models_directory: Path | None = None
    cache_directory: Path | None = None

    @field_validator("svo2_directory", "output_directory", "models_directory", "cache_directory", mode="before")
    @classmethod
    def set_default_paths(cls, v: Path | str | None, info) -> Path:
        if v is not None:
            return Path(v) if isinstance(v, str) else v
        field_name = info.field_name
        subdir_map = {
            "svo2_directory": "svo2",
            "output_directory": "output",
            "models_directory": "models",
            "cache_directory": "cache",
        }
        return info.data.get("data_root", Path("/home/atlas/dev/pipe1/data")) / subdir_map[field_name]

    # SAM 3 Configuration
    sam3_model_variant: str = "sam3_hiera_large"
    sam3_model_path: Path | None = None
    sam3_default_confidence: float = 0.5
    sam3_default_iou: float = 0.7
    sam3_default_batch_size: int = 8

    # GPU Configuration
    cuda_visible_devices: str = "0"
    torch_compile_enabled: bool = True

    # ZED SDK
    zed_sdk_path: Path = Field(default=Path("/usr/local/zed"))

    # Logging
    log_level: str = "INFO"
    log_file: Path | None = None

    # Frontend
    frontend_url: str = "http://localhost:3000"

    # Storage optimization
    # Point cloud format: "ply" (ASCII, large), "ply_binary" (binary, ~7x smaller), "npy", "bin"
    default_point_cloud_format: str = "ply_binary"

    # Disk space thresholds (in GB)
    disk_space_error_threshold_gb: float = 10.0  # Block job creation below this
    disk_space_warning_threshold_gb: float = 50.0  # Warn but allow

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def is_testing(self) -> bool:
        return self.app_env == "testing"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
