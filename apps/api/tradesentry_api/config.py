import os
from typing import Self

from pydantic import BaseModel, ConfigDict, Field


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    app_name: str = "Trade Finance Intelligence Layer"
    version: str = "0.1.0"
    environment: str = "local"
    deployment: str = "local-compose"
    infrastructure_note: str = "Local development environment"
    aws_region: str = "ap-south-1"
    database_url: str = "postgresql+asyncpg://tradesentry:change-me@localhost:5432/tradesentry"
    redis_url: str = "redis://localhost:6379/0"
    s3_bucket: str = "tradesentry-documents-local"
    s3_endpoint_url: str | None = "http://localhost:4566"
    s3_public_endpoint_url: str | None = None
    textract_endpoint_url: str | None = None
    dynamodb_endpoint_url: str | None = None
    cross_ibu_table_name: str = "TradeFinanceRegistry"
    s3_kms_key_id: str = "alias/tradesentry-local"
    service_check_mode: str = "stub"
    ocr_mode: str = "stub"
    max_upload_bytes: int = 50 * 1024 * 1024
    textract_confidence_threshold: float = 0.70
    textract_timeout_seconds: int = 120
    fraud_tool_timeout_seconds: float = 30.0
    fraud_tool_retry_count: int = 1
    investigation_tool_timeout_seconds: float = Field(default=30.0, gt=0)
    investigation_tool_budget: int = Field(default=12, ge=0, le=12)
    price_triage_threshold_usd: float = Field(default=700.0, gt=0)
    bedrock_model_id: str | None = None
    jwt_public_key: str | None = None
    jwt_issuer: str = "tradesentry"
    jwt_audience: str = "tradesentry-dashboard"
    jwt_access_ttl_seconds: int = Field(default=3600, ge=60, le=3600)
    jwt_refresh_ttl_seconds: int = Field(default=86400, ge=3600, le=86400)
    rate_limit_ip_per_minute: int = Field(default=100, ge=1)
    rate_limit_user_per_minute: int = Field(default=200, ge=1)
    rate_limit_upload_per_minute: int = Field(default=10, ge=1)
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Self:
        return cls(
            app_name=os.getenv("APP_NAME", "Trade Finance Intelligence Layer"),
            version=os.getenv("APP_VERSION", "0.1.0"),
            environment=os.getenv("ENVIRONMENT", "local"),
            deployment=os.getenv("DEPLOYMENT", "local-compose"),
            infrastructure_note=os.getenv(
                "INFRASTRUCTURE_NOTE", "Local development environment"
            ),
            aws_region=os.getenv("AWS_REGION", "ap-south-1"),
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql+asyncpg://tradesentry:change-me@localhost:5432/tradesentry",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            s3_bucket=os.getenv("S3_BUCKET", "tradesentry-documents-local"),
            s3_endpoint_url=os.getenv("S3_ENDPOINT_URL") or None,
            s3_public_endpoint_url=os.getenv("S3_PUBLIC_ENDPOINT_URL"),
            textract_endpoint_url=os.getenv("TEXTRACT_ENDPOINT_URL"),
            dynamodb_endpoint_url=os.getenv("DYNAMODB_ENDPOINT_URL"),
            cross_ibu_table_name=os.getenv("CROSS_IBU_TABLE_NAME", "TradeFinanceRegistry"),
            s3_kms_key_id=os.getenv("S3_KMS_KEY_ID", "alias/tradesentry-local"),
            service_check_mode=os.getenv("SERVICE_CHECK_MODE", "stub"),
            ocr_mode=os.getenv("OCR_MODE", "stub"),
            max_upload_bytes=int(os.getenv("MAX_UPLOAD_BYTES", str(50 * 1024 * 1024))),
            textract_confidence_threshold=float(os.getenv("TEXTRACT_CONFIDENCE_THRESHOLD", "0.70")),
            textract_timeout_seconds=int(os.getenv("TEXTRACT_TIMEOUT_SECONDS", "120")),
            fraud_tool_timeout_seconds=float(os.getenv("FRAUD_TOOL_TIMEOUT_SECONDS", "30")),
            fraud_tool_retry_count=int(os.getenv("FRAUD_TOOL_RETRY_COUNT", "1")),
            investigation_tool_timeout_seconds=float(
                os.getenv("INVESTIGATION_TOOL_TIMEOUT_SECONDS", "30")
            ),
            investigation_tool_budget=int(os.getenv("INVESTIGATION_TOOL_BUDGET", "12")),
            price_triage_threshold_usd=float(
                os.getenv("PRICE_TRIAGE_THRESHOLD_USD", "700")
            ),
            bedrock_model_id=os.getenv("BEDROCK_MODEL_ID"),
            jwt_public_key=(
                os.getenv("JWT_PUBLIC_KEY", "").replace("\\n", "\n").strip() or None
            ),
            jwt_issuer=os.getenv("JWT_ISSUER", "tradesentry"),
            jwt_audience=os.getenv("JWT_AUDIENCE", "tradesentry-dashboard"),
            jwt_access_ttl_seconds=int(os.getenv("JWT_ACCESS_TTL_SECONDS", "3600")),
            jwt_refresh_ttl_seconds=int(os.getenv("JWT_REFRESH_TTL_SECONDS", "86400")),
            rate_limit_ip_per_minute=int(os.getenv("RATE_LIMIT_IP_PER_MINUTE", "100")),
            rate_limit_user_per_minute=int(os.getenv("RATE_LIMIT_USER_PER_MINUTE", "200")),
            rate_limit_upload_per_minute=int(
                os.getenv("RATE_LIMIT_UPLOAD_PER_MINUTE", "10")
            ),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
