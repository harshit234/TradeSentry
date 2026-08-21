import os
from typing import Self

from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    app_name: str = "Trade Finance Intelligence Layer"
    version: str = "0.1.0"
    environment: str = "local"
    deployment: str = "local-compose"
    aws_region: str = "ap-south-1"
    database_url: str = "postgresql+asyncpg://tradesentry:change-me@localhost:5432/tradesentry"
    redis_url: str = "redis://localhost:6379/0"
    s3_bucket: str = "tradesentry-documents-local"
    s3_endpoint_url: str | None = "http://localhost:4566"
    s3_public_endpoint_url: str | None = None
    textract_endpoint_url: str | None = None
    s3_kms_key_id: str = "alias/tradesentry-local"
    service_check_mode: str = "stub"
    ocr_mode: str = "stub"
    max_upload_bytes: int = 50 * 1024 * 1024
    textract_confidence_threshold: float = 0.70
    textract_timeout_seconds: int = 120
    bedrock_model_id: str | None = None
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            app_name=os.getenv("APP_NAME", "Trade Finance Intelligence Layer"),
            version=os.getenv("APP_VERSION", "0.1.0"),
            environment=os.getenv("ENVIRONMENT", "local"),
            deployment=os.getenv("DEPLOYMENT", "local-compose"),
            aws_region=os.getenv("AWS_REGION", "ap-south-1"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://tradesentry:change-me@localhost:5432/tradesentry",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            s3_bucket=os.getenv("S3_BUCKET", "tradesentry-documents-local"),
            s3_endpoint_url=os.getenv("S3_ENDPOINT_URL", "http://localhost:4566"),
            s3_public_endpoint_url=os.getenv("S3_PUBLIC_ENDPOINT_URL"),
            textract_endpoint_url=os.getenv("TEXTRACT_ENDPOINT_URL"),
            s3_kms_key_id=os.getenv("S3_KMS_KEY_ID", "alias/tradesentry-local"),
            service_check_mode=os.getenv("SERVICE_CHECK_MODE", "stub"),
            ocr_mode=os.getenv("OCR_MODE", "stub"),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))),
            textract_confidence_threshold=float(os.getenv("TEXTRACT_CONFIDENCE_THRESHOLD", "0.70")),
            textract_timeout_seconds=int(os.getenv("TEXTRACT_TIMEOUT_SECONDS", "120")),
            bedrock_model_id=os.getenv("BEDROCK_MODEL_ID"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
