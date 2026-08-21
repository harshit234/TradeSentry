from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date

from rapidfuzz.fuzz import ratio

from models.fraud_tbml import (
    EntityScreenResult,
    SanctionsMatchStatus,
    SanctionsScreeningResult,
)

from .common import DataUnavailableError, load_json, normalize_name, retrieved_now

SANCTIONS_CAVEATS = [
    "Fuzzy name similarity alone is only a possible match",
    "A human officer makes the final determination",
    "Screening results are investigation signals — not legal findings or proof of fraud",
]


class SanctionsScreeningProvider(ABC):
    @abstractmethod
    async def screen(self, entity_names: list[str]) -> SanctionsScreeningResult: ...


class MockSanctionsScreeningProvider(SanctionsScreeningProvider):
    def __init__(self) -> None:
        self.fixture = load_json("fixtures/sanctions/ofac_sdn_static_demo.json")

    async def screen(self, entity_names: list[str]) -> SanctionsScreeningResult:
        results = [self._screen_one(name) for name in entity_names]
        return SanctionsScreeningResult(screened_entities=results)

    def _screen_one(self, input_name: str) -> EntityScreenResult:
        normalized = normalize_name(input_name)
        best_record = max(
            self.fixture["records"],
            key=lambda item: ratio(normalized, normalize_name(item["name"])),
        )
        score = ratio(normalized, normalize_name(best_record["name"])) / 100.0
        exact = normalized == normalize_name(best_record["name"])
        if exact and best_record.get("source_identifier"):
            status = SanctionsMatchStatus.CONFIRMED_SOURCE_MATCH
            rationale = (
                "Exact normalized name matched a dated source record carrying source identifier "
                f"{best_record['source_identifier']}. Human officer determination is still required."
            )
        elif score >= float(self.fixture["possible_match_threshold"]):
            status = SanctionsMatchStatus.POSSIBLE_MATCH
            rationale = (
                "Fuzzy name similarity only; no corroborating input identifier was supplied. "
                "This cannot be treated as a confirmed match. Human review is required."
            )
        else:
            status = SanctionsMatchStatus.NO_MATCH
            rationale = "No material name similarity in the bundled fixture; human review remains authoritative."
        return EntityScreenResult(
            input_name=input_name,
            normalized_name=normalized,
            match_status=status,
            matched_list=best_record["list"] if status is not SanctionsMatchStatus.NO_MATCH else None,
            match_score=round(score, 4),
            match_rationale=rationale,
            data_source=str(self.fixture["data_source"]),
            source_version=str(self.fixture["version"]),
            list_date=date.fromisoformat(self.fixture["list_date"]),
            retrieved_at=retrieved_now(),
            caveats=SANCTIONS_CAVEATS.copy(),
        )


class ProductionSanctionsScreeningProvider(SanctionsScreeningProvider):
    async def screen(self, entity_names: list[str]) -> SanctionsScreeningResult:
        raise DataUnavailableError("Production sanctions provider is not configured")


def unavailable_sanctions_result(
    entity_names: list[str], reason: str
) -> SanctionsScreeningResult:
    results = [
        EntityScreenResult(
            input_name=name,
            normalized_name=normalize_name(name),
            match_status=SanctionsMatchStatus.DATA_UNAVAILABLE,
            matched_list=None,
            match_score=0.0,
            match_rationale=f"{reason}. Human officer determination is required.",
            data_source="Provider unavailable",
            source_version="unavailable",
            list_date=date(1970, 1, 1),
            retrieved_at=retrieved_now(),
            caveats=SANCTIONS_CAVEATS.copy(),
        )
        for name in entity_names
    ]
    return SanctionsScreeningResult(screened_entities=results)
