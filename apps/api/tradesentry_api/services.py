from dataclasses import dataclass
from typing import Protocol

import boto3  # type: ignore[import-untyped]
from botocore.exceptions import ClientError  # type: ignore[import-untyped]

from fraud_tbml import (
    MockEntityVerificationProvider,
    MockPriceBenchmarkProvider,
    MockSanctionsScreeningProvider,
    MockVesselVerificationProvider,
)

from .audit_store import AuditStore, InMemoryAuditStore, PostgresAuditStore
from .compliance_store import (
    ComplianceStore,
    InMemoryComplianceStore,
    PostgresComplianceStore,
)
from .config import Settings
from .cross_ibu_registry import (
    CrossIBURegistry,
    DynamoDBCrossIBURegistry,
    InMemoryCrossIBURegistry,
)
from .db import Database, InMemoryDatabase
from .dna_store import (
    InMemoryTransactionDNAStore,
    PostgresTransactionDNAStore,
    TransactionDNAStore,
)
from .fraud_tbml_runner import FraudTBMLToolRunner
from .investigation_store import (
    InMemoryInvestigationStore,
    InvestigationStore,
    PostgresInvestigationStore,
)
from .malware import MalwareScanner, MockMalwareScanner
from .ocr import (
    BedrockLLMFallback,
    LLMFallback,
    NoOpLLMFallback,
    OCRProvider,
    StubOCRProvider,
    TextractOCRProvider,
)
from .processor import DocumentProcessor
from .rate_limit import InMemoryRateLimiter, RateLimiter, RedisRateLimiter
from .redis_client import InMemoryRedis, RedisCache
from .repository import (
    DocumentRepository,
    InMemoryDocumentRepository,
    PostgresDocumentRepository,
)
from .review_store import InMemoryReviewStore, PostgresReviewStore, ReviewStore
from .s3 import InMemoryStorage, S3Storage, Storage


class Checkable(Protocol):
    async def check(self) -> bool: ...
    async def close(self) -> None: ...


class TextractCheck:
    def __init__(self, region: str, endpoint_url: str | None = None) -> None:
        self.is_emulator = endpoint_url is not None
        self.client = boto3.client("textract", region_name=region, endpoint_url=endpoint_url)

    async def check(self) -> bool:
        try:
            self.client.get_document_analysis(JobId="health-check")
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code")
            if error_code in {"InvalidJobIdException", "ValidationException"}:
                return True
            # LocalStack Community exposes the Textract endpoint but returns 501
            # for this operation. For local foundation checks, that still proves
            # endpoint connectivity; real AWS InternalFailure remains unhealthy.
            return self.is_emulator and error_code == "InternalFailure"
        return True

    async def close(self) -> None:
        return None


class StubCheck:
    async def check(self) -> bool:
        return True

    async def close(self) -> None:
        return None


@dataclass(slots=True)
class Services:
    db: Checkable
    redis: Checkable
    storage: Storage
    textract: Checkable
    repository: DocumentRepository
    processor: DocumentProcessor
    settings: Settings
    compliance_store: ComplianceStore
    dna_store: TransactionDNAStore
    cross_ibu_registry: CrossIBURegistry
    audit_store: AuditStore
    fraud_tbml_runner: FraudTBMLToolRunner
    investigation_store: InvestigationStore
    review_store: ReviewStore
    rate_limiter: RateLimiter
    malware_scanner: MalwareScanner

    @classmethod
    def build(cls, settings: Settings) -> "Services":
        database: Database | InMemoryDatabase
        storage: Storage
        repository: DocumentRepository
        textract: Checkable
        redis: RedisCache | InMemoryRedis
        if settings.service_check_mode == "live":
            database = Database(settings.database_url)
            storage = S3Storage(
                settings.s3_bucket,
                settings.aws_region,
                settings.s3_kms_key_id,
                settings.s3_endpoint_url,
                settings.s3_public_endpoint_url,
            )
            repository = PostgresDocumentRepository(database)
            textract = TextractCheck(settings.aws_region, settings.textract_endpoint_url)
            redis = RedisCache(settings.redis_url)
            rate_limiter: RateLimiter = RedisRateLimiter(redis.client)
            compliance_store: ComplianceStore = PostgresComplianceStore(database)
            dna_store: TransactionDNAStore = PostgresTransactionDNAStore(database)
            cross_ibu_registry: CrossIBURegistry = DynamoDBCrossIBURegistry(
                settings.cross_ibu_table_name,
                settings.aws_region,
                settings.dynamodb_endpoint_url,
            )
            audit_store: AuditStore = PostgresAuditStore(database)
            investigation_store: InvestigationStore = PostgresInvestigationStore(database)
            review_store: ReviewStore = PostgresReviewStore(database)
        else:
            database = InMemoryDatabase()
            storage = InMemoryStorage()
            repository = InMemoryDocumentRepository()
            textract = StubCheck()
            redis = InMemoryRedis()
            rate_limiter = InMemoryRateLimiter()
            compliance_store = InMemoryComplianceStore()
            dna_store = InMemoryTransactionDNAStore()
            cross_ibu_registry = InMemoryCrossIBURegistry()
            audit_store = InMemoryAuditStore()
            investigation_store = InMemoryInvestigationStore()
            review_store = InMemoryReviewStore()
        ocr: OCRProvider = (
            TextractOCRProvider(
                settings.aws_region,
                settings.textract_confidence_threshold,
                settings.textract_timeout_seconds,
                endpoint_url=settings.textract_endpoint_url,
            )
            if settings.ocr_mode == "live"
            else StubOCRProvider()
        )
        fallback: LLMFallback = (
            BedrockLLMFallback(settings.aws_region, settings.bedrock_model_id)
            if settings.bedrock_model_id
            else NoOpLLMFallback()
        )
        processor = DocumentProcessor(
            repository, ocr, fallback, settings.s3_bucket, audit_store
        )
        fraud_tbml_runner = FraudTBMLToolRunner(
            MockPriceBenchmarkProvider(),
            MockVesselVerificationProvider(),
            MockEntityVerificationProvider(),
            MockSanctionsScreeningProvider(),
            audit_store,
            timeout_seconds=settings.fraud_tool_timeout_seconds,
            retry_count=settings.fraud_tool_retry_count,
        )
        return cls(
            database,
            redis,
            storage,
            textract,
            repository,
            processor,
            settings,
            compliance_store,
            dna_store,
            cross_ibu_registry,
            audit_store,
            fraud_tbml_runner,
            investigation_store,
            review_store,
            rate_limiter,
            MockMalwareScanner(),
        )

    async def close(self) -> None:
        await self.db.close()
        await self.redis.close()
        await self.storage.close()
        await self.textract.close()
        await self.cross_ibu_registry.close()
