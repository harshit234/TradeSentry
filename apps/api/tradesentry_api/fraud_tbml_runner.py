from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime
from typing import TypeVar

from fraud_tbml.entity_verification import (
    EntityVerificationProvider,
    unavailable_entity_result,
)
from fraud_tbml.price_benchmark import PriceBenchmarkProvider, unavailable_price_result
from fraud_tbml.sanctions_screening import (
    SanctionsScreeningProvider,
    unavailable_sanctions_result,
)
from fraud_tbml.vessel_verification import (
    VesselVerificationProvider,
    unavailable_vessel_result,
)
from models.dna import TransactionDNA
from models.fraud_tbml import (
    EntityVerificationResult,
    PriceBenchmarkResult,
    SanctionsScreeningResult,
    VesselVerificationResult,
)

from .audit_store import AuditEvent, AuditStore

T = TypeVar("T")
PORT_COUNTRIES = {
    "INMUN": "India",
    "INNSA": "India",
    "INIXY": "India",
    "SGSIN": "Singapore",
}
PORT_NAMES = {
    "INMUN": "Mundra",
    "INNSA": "Nhava Sheva",
    "INIXY": "Kandla",
    "SGSIN": "Singapore",
}


class FraudTBMLToolRunner:
    """Runs allow-listed, read-only investigation tools with audit and timeout controls."""

    def __init__(
        self,
        price_provider: PriceBenchmarkProvider,
        vessel_provider: VesselVerificationProvider,
        entity_provider: EntityVerificationProvider,
        sanctions_provider: SanctionsScreeningProvider,
        audit_store: AuditStore,
        timeout_seconds: float = 30.0,
        retry_count: int = 1,
    ) -> None:
        self.price_provider = price_provider
        self.vessel_provider = vessel_provider
        self.entity_provider = entity_provider
        self.sanctions_provider = sanctions_provider
        self.audit_store = audit_store
        self.timeout_seconds = timeout_seconds
        self.retry_count = retry_count

    async def _audit(self, dna: TransactionDNA, tool: str, phase: str, status: str) -> None:
        await self.audit_store.record(
            AuditEvent(
                case_id=dna.case_id,
                actor_id="fraud-tbml-tool-runner",
                event_type=f"FRAUD_TBML_TOOL_{phase}",
                payload_ref=f"tool={tool};status={status};dna={dna.dna_fingerprint[:12]}",
                created_at=datetime.now(UTC),
            )
        )

    async def _execute(self, operation: Callable[[], Awaitable[T]]) -> T:
        last_error: BaseException | None = None
        for _attempt in range(self.retry_count + 1):
            try:
                return await asyncio.wait_for(operation(), timeout=self.timeout_seconds)
            except (TimeoutError, ConnectionError, OSError) as exc:
                last_error = exc
        if last_error is None:
            raise RuntimeError("Tool operation did not execute")
        raise last_error

    async def run_price_benchmark(self, dna: TransactionDNA) -> PriceBenchmarkResult:
        tool = "price_benchmark"
        await self._audit(dna, tool, "STARTED", "STARTED")
        hs_code = dna.hs_code_canonical or "UNKNOWN"
        origin = PORT_COUNTRIES.get(dna.loading_port_unlocode or "", "Unknown")
        destination = PORT_COUNTRIES.get(dna.discharge_port_unlocode or "", "Unknown")
        period = _quarter(dna.shipment_date_iso)
        unit_value = float(dna.unit_value_usd_per_unit or 0)
        try:
            result = await self._execute(
                lambda: self.price_provider.benchmark(
                    hs_code, origin, destination, period, unit_value, "USD"
                )
            )
        except Exception as exc:  # noqa: BLE001 - tools degrade to typed unavailable results
            result = unavailable_price_result(
                hs_code,
                f"{origin} → {destination}",
                period,
                unit_value,
                "USD",
                _safe_error(exc),
            )
        await self._audit(dna, tool, "COMPLETED", result.signal.value)
        return result

    async def run_vessel_verification(self, dna: TransactionDNA) -> VesselVerificationResult:
        tool = "vessel_verification"
        await self._audit(dna, tool, "STARTED", "STARTED")
        vessel = dna.vessel_normalized or dna.raw_vessel_name or "UNKNOWN"
        voyage = dna.voyage_normalized or dna.raw_voyage_number or "UNKNOWN"
        port = (
            PORT_NAMES.get(dna.loading_port_unlocode or "")
            or dna.raw_loading_port
            or "UNKNOWN"
        )
        stated_date = _date_or_epoch(dna.shipment_date_iso)
        try:
            result = await self._execute(
                lambda: self.vessel_provider.verify(
                    vessel, dna.imo_number, voyage, port, stated_date
                )
            )
        except Exception as exc:  # noqa: BLE001 - tools degrade to typed unavailable results
            result = unavailable_vessel_result(
                vessel, dna.imo_number, voyage, port, stated_date, _safe_error(exc)
            )
        await self._audit(dna, tool, "COMPLETED", result.verification_result.value)
        return result

    async def run_entity_verification(
        self, dna: TransactionDNA
    ) -> list[EntityVerificationResult]:
        tool = "entity_verification"
        await self._audit(dna, tool, "STARTED", "STARTED")
        entities = _entities(dna)

        async def verify_all() -> list[EntityVerificationResult]:
            return [
                await self.entity_provider.verify(name, country, entity_type)
                for name, country, entity_type in entities
            ]

        try:
            results = await self._execute(verify_all)
        except Exception as exc:  # noqa: BLE001 - tools degrade to typed unavailable results
            reason = _safe_error(exc)
            results = [
                unavailable_entity_result(name, country, entity_type, reason)
                for name, country, entity_type in entities
            ]
        await self._audit(dna, tool, "COMPLETED", "TYPED_RESULTS_RETURNED")
        return results

    async def run_sanctions_screening(self, dna: TransactionDNA) -> SanctionsScreeningResult:
        tool = "sanctions_screening"
        await self._audit(dna, tool, "STARTED", "STARTED")
        names = [name for name, _country, _entity_type in _entities(dna)]
        try:
            result = await self._execute(lambda: self.sanctions_provider.screen(names))
        except Exception as exc:  # noqa: BLE001 - tools degrade to typed unavailable results
            result = unavailable_sanctions_result(names, _safe_error(exc))
        statuses = sorted({item.match_status.value for item in result.screened_entities})
        await self._audit(dna, tool, "COMPLETED", ",".join(statuses) or "NO_ENTITIES")
        return result


def _quarter(value: str | None) -> str:
    parsed = _date_or_epoch(value)
    return f"{parsed.year}-Q{((parsed.month - 1) // 3) + 1}"


def _date_or_epoch(value: str | None) -> date:
    if value is None:
        return date(1970, 1, 1)
    try:
        return date.fromisoformat(value)
    except ValueError:
        return date(1970, 1, 1)


def _entities(dna: TransactionDNA) -> list[tuple[str, str, str]]:
    origin = PORT_COUNTRIES.get(dna.loading_port_unlocode or "", "Unknown")
    destination = PORT_COUNTRIES.get(dna.discharge_port_unlocode or "", "Unknown")
    values = [
        (dna.raw_exporter or dna.exporter_normalized, origin, "exporter"),
        (dna.raw_importer or dna.importer_normalized, destination, "importer"),
    ]
    return [(name, country, entity_type) for name, country, entity_type in values if name]


def _safe_error(exc: BaseException) -> str:
    if isinstance(exc, TimeoutError):
        return "Provider timeout"
    return f"Provider unavailable ({type(exc).__name__})"
