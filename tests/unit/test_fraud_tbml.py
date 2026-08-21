from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from tradesentry_api.audit_store import InMemoryAuditStore
from tradesentry_api.fraud_tbml_runner import FraudTBMLToolRunner

from fraud_tbml.entity_verification import EntityVerificationProvider
from fraud_tbml.price_benchmark import MockPriceBenchmarkProvider, PriceBenchmarkProvider
from fraud_tbml.sanctions_screening import (
    MockSanctionsScreeningProvider,
    SanctionsScreeningProvider,
)
from fraud_tbml.vessel_verification import (
    MockVesselVerificationProvider,
    VesselVerificationProvider,
)
from models.dna import TransactionDNA
from models.fraud_tbml import (
    EntityVerificationResult,
    PriceBenchmarkResult,
    PriceSignal,
    SanctionsMatchStatus,
    SanctionsScreeningResult,
    VesselVerificationResult,
    VesselVerificationStatus,
)


def _dna(unit_value: Decimal = Decimal(450)) -> TransactionDNA:
    return TransactionDNA(
        transaction_id="txn-sprint-5",
        case_id="DEMO-CASE-A",
        presenting_ibu="IBU-A",
        raw_exporter="ABC Trading Ltd",
        raw_importer="XYZ Imports Pte Ltd",
        exporter_normalized="abc_trading",
        importer_normalized="xyz_imports",
        vessel_normalized="OCEAN STAR",
        imo_number="9876543",
        voyage_normalized="V123",
        loading_port_unlocode="INMUN",
        discharge_port_unlocode="SGSIN",
        shipment_date_iso="2024-08-14",
        hs_code_canonical="1006.30",
        unit_value_usd_per_unit=unit_value,
        dna_fingerprint="a" * 64,
        source_documents={},
        normalization_methods={},
        confidence_flags=[],
        conflicts=[],
        created_at=datetime(2024, 8, 14, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_price_case_a_is_review() -> None:
    result = await MockPriceBenchmarkProvider().benchmark(
        "1006.30", "India", "Singapore", "2024-Q2", 450, "USD"
    )
    assert result.signal is PriceSignal.REVIEW
    assert result.deviation_from_p50_pct == 47.5


@pytest.mark.asyncio
async def test_price_case_c_is_significant_anomaly() -> None:
    result = await MockPriceBenchmarkProvider().benchmark(
        "1006.30", "India", "Singapore", "2024-Q2", 810, "USD"
    )
    assert result.signal is PriceSignal.SIGNIFICANT_ANOMALY
    assert result.deviation_from_p50_pct == 165.6


@pytest.mark.asyncio
async def test_normal_price_is_normal() -> None:
    result = await MockPriceBenchmarkProvider().benchmark(
        "1006.30", "India", "Singapore", "2024-Q2", 300, "USD"
    )
    assert result.signal is PriceSignal.NORMAL


@pytest.mark.asyncio
async def test_price_caveats_are_always_present() -> None:
    provider = MockPriceBenchmarkProvider()
    available = await provider.benchmark(
        "1006.30", "India", "Singapore", "2024-Q2", 300, "USD"
    )
    unavailable = await provider.benchmark(
        "9999.99", "India", "Singapore", "2024-Q2", 300, "USD"
    )
    assert len(available.caveats) >= 5
    assert "not proof of fraud" in available.caveats[-1]
    assert len(unavailable.caveats) >= 5


@pytest.mark.asyncio
async def test_vessel_ocean_star_at_mundra_is_consistent() -> None:
    result = await MockVesselVerificationProvider().verify(
        "Ocean Star", "9876543", "V123", "Mundra", date(2024, 8, 14)
    )
    assert result.verification_result is VesselVerificationStatus.CONSISTENT


@pytest.mark.asyncio
async def test_impossible_vessel_position_is_anomaly() -> None:
    result = await MockVesselVerificationProvider().verify(
        "Ocean Star", "9876543", "V123", "Rotterdam", date(2024, 8, 14)
    )
    assert result.verification_result is VesselVerificationStatus.ANOMALY


@pytest.mark.asyncio
async def test_unknown_vessel_is_data_unavailable() -> None:
    result = await MockVesselVerificationProvider().verify(
        "Unknown Vessel", None, "V1", "Mundra", date(2024, 8, 14)
    )
    assert result.verification_result is VesselVerificationStatus.DATA_UNAVAILABLE


@pytest.mark.asyncio
async def test_exact_sanctions_name_is_confirmed_source_match() -> None:
    result = await MockSanctionsScreeningProvider().screen(["North Star Trading Company"])
    entity = result.screened_entities[0]
    assert entity.match_status is SanctionsMatchStatus.CONFIRMED_SOURCE_MATCH
    assert result.human_determination_required is True


@pytest.mark.asyncio
async def test_fuzzy_sanctions_name_is_possible_match_never_confirmed() -> None:
    result = await MockSanctionsScreeningProvider().screen(["North Star Tradng Company"])
    assert result.screened_entities[0].match_status is SanctionsMatchStatus.POSSIBLE_MATCH


@pytest.mark.asyncio
async def test_unrelated_sanctions_name_has_no_match() -> None:
    result = await MockSanctionsScreeningProvider().screen(["ABC Trading Ltd"])
    assert result.screened_entities[0].match_status is SanctionsMatchStatus.NO_MATCH


class SlowProvider(
    PriceBenchmarkProvider,
    VesselVerificationProvider,
    EntityVerificationProvider,
    SanctionsScreeningProvider,
):
    async def benchmark(
        self,
        hs_code: str,
        origin_country: str,
        destination_country: str,
        period: str,
        invoice_unit_value: float,
        currency: str,
    ) -> PriceBenchmarkResult:
        await asyncio.sleep(1)
        raise AssertionError("unreachable")

    async def verify(  # type: ignore[override]
        self, *args: object, **kwargs: object
    ) -> VesselVerificationResult | EntityVerificationResult:
        await asyncio.sleep(1)
        raise AssertionError("unreachable")

    async def screen(self, entity_names: list[str]) -> SanctionsScreeningResult:
        await asyncio.sleep(1)
        raise AssertionError("unreachable")


@pytest.mark.asyncio
async def test_all_provider_timeouts_return_typed_unavailable_results() -> None:
    slow = SlowProvider()
    runner = FraudTBMLToolRunner(
        slow,
        slow,
        slow,
        slow,
        InMemoryAuditStore(),
        timeout_seconds=0.001,
        retry_count=0,
    )
    price = await runner.run_price_benchmark(_dna())
    vessel = await runner.run_vessel_verification(_dna())
    entities = await runner.run_entity_verification(_dna())
    sanctions = await runner.run_sanctions_screening(_dna())
    assert price.signal is PriceSignal.DATA_UNAVAILABLE
    assert vessel.verification_result is VesselVerificationStatus.DATA_UNAVAILABLE
    assert all(item.confidence == 0 for item in entities)
    assert all(
        item.match_status is SanctionsMatchStatus.DATA_UNAVAILABLE
        for item in sanctions.screened_entities
    )


def _runner(audit: InMemoryAuditStore) -> FraudTBMLToolRunner:
    return FraudTBMLToolRunner(
        MockPriceBenchmarkProvider(),
        MockVesselVerificationProvider(),
        __import__("fraud_tbml").MockEntityVerificationProvider(),
        MockSanctionsScreeningProvider(),
        audit,
    )


@pytest.mark.asyncio
async def test_all_four_tools_are_isolated_and_every_call_is_audited() -> None:
    audit = InMemoryAuditStore()
    runner = _runner(audit)
    price = await runner.run_price_benchmark(_dna())
    vessel = await runner.run_vessel_verification(_dna())
    entities = await runner.run_entity_verification(_dna())
    sanctions = await runner.run_sanctions_screening(_dna())
    assert isinstance(price, PriceBenchmarkResult)
    assert isinstance(vessel, VesselVerificationResult)
    assert all(isinstance(item, EntityVerificationResult) for item in entities)
    assert isinstance(sanctions, SanctionsScreeningResult)
    assert await audit.count("FRAUD_TBML_TOOL_STARTED") == 4
    assert await audit.count("FRAUD_TBML_TOOL_COMPLETED") == 4
    assert all("ABC Trading Ltd" not in event.payload_ref for event in audit.events)


@pytest.mark.asyncio
async def test_idempotent_reads_repeat_the_same_decisions() -> None:
    runner = _runner(InMemoryAuditStore())
    first = await runner.run_price_benchmark(_dna())
    second = await runner.run_price_benchmark(_dna())
    assert first.signal == second.signal
    assert first.deviation_from_p50_pct == second.deviation_from_p50_pct
    assert first.reference_p90 == second.reference_p90

