import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Core application settings and configuration validator."""

    ENVIRONMENT: str = "development"
    APP_NAME: str = "SevaHealth AI"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Security & IAM
    SECRET_KEY: str = "sevahealth-insecure-dev-secret-change-in-production-min-32-chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DATABASE_URL: str = "sqlite:///./sevahealth.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # Object Storage / MinIO
    S3_ENDPOINT: str = "http://localhost:9000"
    S3_ACCESS_KEY: str = "minioadmin"
    S3_SECRET_KEY: str = "minioadmin"
    S3_BUCKET_NAME: str = "sevahealth-medical-vault"
    S3_USE_SSL: bool = False

    # AI Provider Settings
    AI_PROVIDER: str = "MOCK"  # MOCK | GEMINI | OPENAI
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    AI_MODEL_NAME: str = "gemini-1.5-pro"

    # OpenEHR & EHRbase
    EHRBASE_URL: str = "http://localhost:8080/ehrbase/rest/openehr/v1"
    EHRBASE_USER: str = "ehrbase-user"
    EHRBASE_PASSWORD: str = "SuperSecretPassword"
    CLINICAL_REPOSITORY_BACKEND: str = "hybrid"  # openehr | postgresql | hybrid

    # Interoperability & External EMRs (bezs-emr-gql, bezs-hms)
    EMR_GQL_URL: str = "http://localhost:8001/graphql"
    EMR_GQL_TIMEOUT_SEC: float = 5.0
    HMS_API_URL: str = "http://localhost:3000/api"
    HMS_API_TIMEOUT_SEC: float = 5.0
    ENABLE_FEDERATED_EMR: bool = True

    # Observability
    OTEL_ENABLED: bool = False
    LOG_LEVEL: str = "INFO"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
