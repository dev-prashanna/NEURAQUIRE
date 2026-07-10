import os
import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    pass


@dataclass
class Settings:
    APP_NAME: str = "NeuraQuire"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    EMBEDDING_MODEL: str = "all-MiniLM-L12-v2"
    LLM_MODEL: str = "mimo-v2.5"
    LLM_BASE_URL: str = "https://api.xiaomimimo.com/v1"
    LLM_MAX_TOKENS: int = 1024
    LLM_TEMPERATURE: float = 0.3
    LLM_PRICE_PER_1K_TOKENS: float = 0.002

    CHUNK_SIZE: int = 500
    CHUNK_OVERLAP: int = 50
    TOP_K_RESULTS: int = 3

    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: tuple = (".pdf",)
    MAX_QUESTION_LENGTH: int = 500
    FILE_TTL_SECONDS: int = 3600

    RATE_LIMIT_MAX_REQUESTS: int = 10
    RATE_LIMIT_WINDOW_SECONDS: int = 60

    UPLOAD_DIR: str = "uploaded_papers"
    VECTOR_DB_DIR: str = "vector_db"
    LOG_DIR: str = "logs"
    LOG_FILE: str = "neuraquire.log"

    def __post_init__(self):
        self.DEBUG = os.getenv("NEURAQUIRE_DEBUG", "false").lower() == "true"
        self.LLM_BASE_URL = os.getenv("NEURAQUIRE_LLM_BASE_URL", self.LLM_BASE_URL)
        self.LLM_MODEL = os.getenv("NEURAQUIRE_LLM_MODEL", self.LLM_MODEL)
        self.EMBEDDING_MODEL = os.getenv("NEURAQUIRE_EMBEDDING_MODEL", self.EMBEDDING_MODEL)

        max_upload = os.getenv("NEURAQUIRE_MAX_UPLOAD_MB")
        if max_upload:
            try:
                self.MAX_UPLOAD_SIZE_MB = int(max_upload)
            except ValueError:
                raise ConfigError(f"Invalid NEURAQUIRE_MAX_UPLOAD_MB: {max_upload}")

        rate_limit = os.getenv("NEURAQUIRE_RATE_LIMIT")
        if rate_limit:
            try:
                self.RATE_LIMIT_MAX_REQUESTS = int(rate_limit)
            except ValueError:
                raise ConfigError(f"Invalid NEURAQUIRE_RATE_LIMIT: {rate_limit}")

        file_ttl = os.getenv("NEURAQUIRE_FILE_TTL")
        if file_ttl:
            try:
                self.FILE_TTL_SECONDS = int(file_ttl)
            except ValueError:
                raise ConfigError(f"Invalid NEURAQUIRE_FILE_TTL: {file_ttl}")

        chunk_size = os.getenv("NEURAQUIRE_CHUNK_SIZE")
        if chunk_size:
            try:
                self.CHUNK_SIZE = int(chunk_size)
            except ValueError:
                raise ConfigError(f"Invalid NEURAQUIRE_CHUNK_SIZE: {chunk_size}")

    def validate(self) -> list[str]:
        errors = []

        if self.LLM_MAX_TOKENS < 1 or self.LLM_MAX_TOKENS > 128000:
            errors.append(f"LLM_MAX_TOKENS must be 1-128000, got {self.LLM_MAX_TOKENS}")

        if not 0 <= self.LLM_TEMPERATURE <= 2:
            errors.append(f"LLM_TEMPERATURE must be 0-2, got {self.LLM_TEMPERATURE}")

        if self.MAX_UPLOAD_SIZE_MB < 1:
            errors.append(f"MAX_UPLOAD_SIZE_MB must be >= 1, got {self.MAX_UPLOAD_SIZE_MB}")

        if self.CHUNK_SIZE < 100:
            errors.append(f"CHUNK_SIZE must be >= 100, got {self.CHUNK_SIZE}")

        if self.RATE_LIMIT_MAX_REQUESTS < 1:
            errors.append(f"RATE_LIMIT_MAX_REQUESTS must be >= 1, got {self.RATE_LIMIT_MAX_REQUESTS}")

        return errors


def load_env_file(path: str = ".env"):
    if not os.path.exists(path):
        return

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()

            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]

            if key not in os.environ:
                os.environ[key] = value


def get_settings() -> Settings:
    load_env_file()
    settings = Settings()

    errors = settings.validate()
    if errors:
        for error in errors:
            logger.error(f"Config validation error: {error}")
        raise ConfigError(f"Invalid configuration: {'; '.join(errors)}")

    return settings


settings = get_settings()
