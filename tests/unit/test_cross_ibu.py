from __future__ import annotations

import asyncio
import hashlib
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from time import perf_counter

from fastapi.testclient import TestClient
from tradesentry_api.config import Settings
from tradesentry_api.cross_ibu_registry import (
    DynamoDBCrossIBURegistry,
    InMemoryCrossIBURegistry,
)
from tradesentry_api.main import create_app
from tradesentry_api.services import Services

from cross_ibu import find_best_match, signal_from_dna
from models.cross_ibu import MatchLevel
from models.dna import TransactionDNA

NOW = datetime(2026, 8, 21, 12, 0, tzinfo=UTC)


def _fingerprint(values: tuple[str | None, ...]) -> str:
    return hashlib.sha256("".join(value or "" for value in values).encode()).hexdigest()


def _dna(
    case_id: str,
    ibu_id: str = "IBU-A",
    bl: str | None = "BL789456",
    vessel: str = "ocean_star",
    voyage: str = "V123",
    exporter: str = "abc_trading",
    loading: str = "INMUN",
    discharge: str = "SGSIN",
    shipped: str = "2024-08-14",
) -> TransactionDNA:
    fingerprint = _fingerprint((bl, vessel, voyage, loading, discharge, shipped, exporter))
    return TransactionDNA(
        transaction_id=f"txn-{case_id.lower()}",
        case_id=case_id,
        presenting_ibu=ibu_id,
        bl_number_normalized=bl,
        vessel_normalized=vessel,
        voyage_normalized=voyage,
        exporter_normalized=exporter,
        loading_port_unlocode=loading,
        discharge_port_unlocode=discharge,
        shipment_date_iso=shipped,
        commodity_normalized="rice",
        quantity_canonical=Decimal(500),
        unit_canonical="MT",
        dna_fingerprint=fingerprint,
        source_documents={},
        normalization_methods={},
        confidence_flags=[],
        conflicts=[],
        created_at=NOW,
    )


def _services_with(*items: TransactionDNA) -> Services:
    services = Services.build(Settings())
    for item in items:
        asyncio.run(services.dna_store.save(item))
    return services


def _post(client: TestClient, path: str, case_id: str, ibu_id: str = "IBU-A"):
    return client.post(path, json={"case_id": case_id}, headers={"X-IBU-ID": ibu_id})


def test_t1_register_then_query_exact_match() -> None:
    services = _services_with(_dna("CASE-REGISTERED", "IBU-C"), _dna("CASE-QUERY", "IBU-A"))
    with TestClient(create_app(Settings(), services)) as client:
        registered = _post(client, "/cross-ibu/register", "CASE-REGISTERED", "IBU-C")
        matched = _post(client, "/cross-ibu/query", "CASE-QUERY", "IBU-A")
    assert registered.status_code == 200
    assert matched.json()["match_level"] == "EXACT"
    assert matched.json()["similarity_score"] == 1.0
    assert asyncio.run(services.audit_store.count("CROSS_IBU_REGISTERED")) == 1
    assert asyncio.run(services.audit_store.count("CROSS_IBU_QUERIED")) == 1


def test_t2_near_duplicate_meets_prototype_threshold() -> None:
    registry = InMemoryCrossIBURegistry()
    original = signal_from_dna(_dna("ORIGINAL", "IBU-C"))
    query = signal_from_dna(_dna("NEAR", bl="BL789457"))
    asyncio.run(registry.register(original, NOW))
    candidates = asyncio.run(registry.find_candidates(query))
    result = find_best_match(query, candidates, NOW)
    assert result.match_level is MatchLevel.NEAR
    assert result.similarity_score >= 0.85


def test_t3_same_exporter_different_shipment_returns_none() -> None:
    registry = InMemoryCrossIBURegistry()
    original = signal_from_dna(_dna("ORIGINAL", "IBU-C"))
    legitimate = signal_from_dna(
        _dna(
            "LEGIT",
            bl="BL-LEGIT-099",
            vessel="sea_breeze",
            voyage="V900",
            discharge="LKCMB",
            shipped="2024-09-01",
        )
    )
    asyncio.run(registry.register(original, NOW))
    result = find_best_match(legitimate, asyncio.run(registry.find_candidates(legitimate)), NOW)
    assert result.match_level is MatchLevel.NONE
    assert result.is_false_positive_candidate is True
    assert "no duplicate-financing alert" in result.explanation


def test_t4_completely_different_entity_returns_none() -> None:
    registry = InMemoryCrossIBURegistry()
    asyncio.run(registry.register(signal_from_dna(_dna("ORIGINAL", "IBU-C")), NOW))
    different = signal_from_dna(
        _dna(
            "DIFFERENT",
            bl="BL-404",
            vessel="atlantic",
            voyage="V999",
            exporter="unrelated_exports",
            loading="INNSA",
            discharge="DEHAM",
            shipped="2025-01-01",
        )
    )
    result = find_best_match(different, asyncio.run(registry.find_candidates(different)), NOW)
    assert result.match_level is MatchLevel.NONE


def test_t5_same_ibu_fingerprint_registration_is_idempotent() -> None:
    registry = InMemoryCrossIBURegistry()
    signal = signal_from_dna(_dna("IDEMPOTENT"))
    first = asyncio.run(registry.register(signal, NOW))
    second = asyncio.run(registry.register(signal, NOW + timedelta(minutes=1)))
    assert first.registration_id == second.registration_id
    assert len(asyncio.run(registry.list_all())) == 1


def test_t6_missing_bl_uses_level_two_without_crashing() -> None:
    registry = InMemoryCrossIBURegistry()
    asyncio.run(registry.register(signal_from_dna(_dna("ORIGINAL", "IBU-C")), NOW))
    query = signal_from_dna(_dna("NO-BL", bl=None, shipped="2024-08-15"))
    result = find_best_match(query, asyncio.run(registry.find_candidates(query)), NOW)
    assert result.match_level is MatchLevel.NEAR


def test_t7_tenant_cannot_query_foreign_case() -> None:
    services = _services_with(_dna("FOREIGN", "IBU-B"))
    with TestClient(create_app(Settings(), services)) as client:
        response = _post(client, "/cross-ibu/query", "FOREIGN", "IBU-A")
    assert response.status_code == 403
    assert response.json()["detail"] == "IBU tenant access denied"
    assert asyncio.run(services.audit_store.count("CROSS_IBU_QUERY_DENIED")) == 1


def test_t8_every_query_is_audited() -> None:
    services = _services_with(_dna("AUDITED"))
    with TestClient(create_app(Settings(), services)) as client:
        _post(client, "/cross-ibu/query", "AUDITED")
    assert asyncio.run(services.audit_store.count("CROSS_IBU_QUERIED")) == 1


def test_t9_dynamodb_gsi_bl_candidate_lookup_is_under_50ms() -> None:
    signal = signal_from_dna(_dna("LATENCY", "IBU-A"))
    seed_registry = InMemoryCrossIBURegistry()
    registration = asyncio.run(
        seed_registry.register(signal_from_dna(_dna("REGISTERED", "IBU-C")), NOW)
    )

    class FakeTable:
        def __init__(self) -> None:
            self.queried_indexes: list[str] = []

        def get_item(self, **_kwargs: object) -> dict[str, object]:
            return {}

        def query(self, **kwargs: object) -> dict[str, object]:
            index = str(kwargs.get("IndexName"))
            self.queried_indexes.append(index)
            items = (
                [DynamoDBCrossIBURegistry._item(registration)] if index == "gsi_bl_number" else []
            )
            return {"Items": items}

    registry = object.__new__(DynamoDBCrossIBURegistry)
    registry.table = FakeTable()
    started = perf_counter()
    candidates = asyncio.run(registry.find_candidates(signal))
    elapsed_ms = (perf_counter() - started) * 1000
    assert candidates
    assert "gsi_bl_number" in registry.table.queried_indexes
    assert elapsed_ms < 50


def test_t10_every_registration_has_90_day_ttl_and_no_raw_fields() -> None:
    registry = InMemoryCrossIBURegistry()
    registration = asyncio.run(registry.register(signal_from_dna(_dna("TTL")), NOW))
    assert registration.ttl == int((NOW + timedelta(days=90)).timestamp())
    assert not any(name.startswith("raw_") for name in type(registration).model_fields)
