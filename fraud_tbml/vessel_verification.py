from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from models.fraud_tbml import VesselVerificationResult, VesselVerificationStatus

from .common import DataUnavailableError, load_json, retrieved_now

VESSEL_CAVEATS = [
    "Synthetic schedule data may be incomplete or delayed",
    "Port-call consistency is an investigation signal — not proof of fraud",
    "Human verification is required before any consequential action",
]


class VesselVerificationProvider(ABC):
    @abstractmethod
    async def verify(
        self,
        vessel_name: str,
        imo_number: str | None,
        voyage_number: str,
        stated_port: str,
        stated_date: date,
    ) -> VesselVerificationResult: ...


class MockVesselVerificationProvider(VesselVerificationProvider):
    def __init__(self) -> None:
        self.fixture = load_json("fixtures/vessel_schedules/ais_synthetic.json")

    async def verify(
        self,
        vessel_name: str,
        imo_number: str | None,
        voyage_number: str,
        stated_port: str,
        stated_date: date,
    ) -> VesselVerificationResult:
        normalized_name = vessel_name.upper().removeprefix("MV ").strip()
        record = next(
            (
                item
                for item in self.fixture["records"]
                if item["vessel_name"] == normalized_name
                or (imo_number is not None and item["imo_number"] == imo_number)
            ),
            None,
        )
        if record is None:
            return unavailable_vessel_result(
                vessel_name, imo_number, voyage_number, stated_port, stated_date, "Unknown vessel"
            )
        fixture_date = date.fromisoformat(record["port_date"])
        port_matches = record["port"].casefold() in stated_port.casefold()
        date_matches = abs((fixture_date - stated_date).days) <= 3
        consistent = port_matches and date_matches
        return VesselVerificationResult(
            vessel_name=vessel_name,
            imo_number=imo_number,
            voyage_number=voyage_number,
            stated_port=stated_port,
            stated_date=stated_date,
            verification_result=(
                VesselVerificationStatus.CONSISTENT
                if consistent
                else VesselVerificationStatus.ANOMALY
            ),
            data_source=str(self.fixture["data_source"]),
            source_version=str(self.fixture["version"]),
            details=(
                f"Fixture shows {record['vessel_name']} at {record['port']} on "
                f"{record['port_date']}; stated {stated_port} on {stated_date.isoformat()}."
            ),
            caveats=VESSEL_CAVEATS.copy(),
            confidence=float(record["confidence"]),
            retrieved_at=retrieved_now(),
        )


class ProductionVesselVerificationProvider(VesselVerificationProvider):
    async def verify(
        self,
        vessel_name: str,
        imo_number: str | None,
        voyage_number: str,
        stated_port: str,
        stated_date: date,
    ) -> VesselVerificationResult:
        raise DataUnavailableError("Production AIS provider is not configured")


def unavailable_vessel_result(
    vessel_name: str,
    imo_number: str | None,
    voyage_number: str,
    stated_port: str,
    stated_date: date,
    reason: str,
) -> VesselVerificationResult:
    return VesselVerificationResult(
        vessel_name=vessel_name,
        imo_number=imo_number,
        voyage_number=voyage_number,
        stated_port=stated_port,
        stated_date=stated_date,
        verification_result=VesselVerificationStatus.DATA_UNAVAILABLE,
        data_source="Provider unavailable",
        source_version="unavailable",
        details=reason,
        caveats=VESSEL_CAVEATS.copy(),
        confidence=0.0,
        retrieved_at=retrieved_now(),
    )

