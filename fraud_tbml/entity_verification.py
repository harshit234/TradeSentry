from __future__ import annotations

from abc import ABC, abstractmethod

from models.fraud_tbml import EntityVerificationResult, EntityVerificationStatus

from .common import DataUnavailableError, load_json, normalize_name, retrieved_now

ENTITY_CAVEATS = [
    "Synthetic registry data is incomplete and provided for demonstration only",
    "An unverified entity is not evidence of wrongdoing",
    "Human verification is required before any consequential action",
]


class EntityVerificationProvider(ABC):
    @abstractmethod
    async def verify(
        self, entity_name: str, country: str, entity_type: str
    ) -> EntityVerificationResult: ...


class MockEntityVerificationProvider(EntityVerificationProvider):
    def __init__(self) -> None:
        self.fixture = load_json("fixtures/entities/entity_registry_synthetic.json")

    async def verify(
        self, entity_name: str, country: str, entity_type: str
    ) -> EntityVerificationResult:
        normalized = normalize_name(entity_name)
        record = next(
            (
                item
                for item in self.fixture["records"]
                if normalize_name(item["name"]) == normalized
                and item["country"].casefold() == country.casefold()
            ),
            None,
        )
        status = (
            EntityVerificationStatus.VERIFIED
            if record is not None
            else EntityVerificationStatus.UNVERIFIED
        )
        return EntityVerificationResult(
            raw_name=entity_name,
            normalized_name=normalized,
            country=country,
            entity_type=entity_type,
            verification_status=status,
            known_relationships=[] if record is None else list(record["known_relationships"]),
            data_source=str(self.fixture["data_source"]),
            source_version=str(self.fixture["version"]),
            caveats=ENTITY_CAVEATS.copy(),
            confidence=0.9 if record is not None else 0.2,
            retrieved_at=retrieved_now(),
        )


class ProductionEntityVerificationProvider(EntityVerificationProvider):
    async def verify(
        self, entity_name: str, country: str, entity_type: str
    ) -> EntityVerificationResult:
        raise DataUnavailableError("Production entity-intelligence provider is not configured")


def unavailable_entity_result(
    entity_name: str, country: str, entity_type: str, reason: str
) -> EntityVerificationResult:
    return EntityVerificationResult(
        raw_name=entity_name,
        normalized_name=normalize_name(entity_name),
        country=country,
        entity_type=entity_type,
        verification_status=EntityVerificationStatus.UNVERIFIED,
        known_relationships=[],
        data_source="Provider unavailable",
        source_version="unavailable",
        caveats=[*ENTITY_CAVEATS, reason],
        confidence=0.0,
        retrieved_at=retrieved_now(),
    )

