from __future__ import annotations

import hashlib
import importlib
import json
from datetime import date, datetime
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path
from types import ModuleType
from typing import Any, Protocol

from models.cross_ibu import CrossIBUMatch, MatchLevel, RegistryRegistration, RegistrySignal

rapidfuzz_fuzz: ModuleType | None
try:
    rapidfuzz_fuzz = importlib.import_module("rapidfuzz.fuzz")
except ModuleNotFoundError:  # pragma: no cover - production image installs RapidFuzz
    rapidfuzz_fuzz = None


class _Signal(Protocol):
    dna_fingerprint: str
    bl_number_normalized: str | None
    voyage_normalized: str | None
    vessel_normalized: str | None
    exporter_normalized: str | None
    shipment_date_iso: str | None
    loading_port_unlocode: str | None
    discharge_port_unlocode: str | None


@lru_cache(maxsize=1)
def matching_config() -> dict[str, Any]:
    path = Path(__file__).with_name("config") / "matching.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _token_sort_ratio(left: str, right: str) -> float:
    if rapidfuzz_fuzz is not None:
        return float(rapidfuzz_fuzz.token_sort_ratio(left, right)) / 100.0
    normalized_left = " ".join(sorted(left.casefold().replace("_", " ").split()))
    normalized_right = " ".join(sorted(right.casefold().replace("_", " ").split()))
    return SequenceMatcher(None, normalized_left, normalized_right).ratio()


def _date_similarity(left: str, right: str) -> float:
    first = date.fromisoformat(left)
    second = date.fromisoformat(right)
    difference = abs((first - second).days)
    if difference == 0:
        return 1.0
    return 0.5 if difference <= int(matching_config()["date_near_days"]) else 0.0


def weighted_similarity(query: _Signal, candidate: _Signal) -> tuple[float, list[str]]:
    weights: dict[str, str] = matching_config()["weights"]
    numerator = 0.0
    denominator = 0.0
    matched_fields: list[str] = []
    for field_name, raw_weight in weights.items():
        left = getattr(query, field_name)
        right = getattr(candidate, field_name)
        if left is None or right is None:
            continue
        weight = float(raw_weight)
        denominator += weight
        similarity = (
            _date_similarity(left, right)
            if field_name == "shipment_date_iso"
            else _token_sort_ratio(left, right)
        )
        numerator += weight * similarity
        if similarity == 1.0:
            matched_fields.append(field_name)
    return (numerator / denominator if denominator else 0.0), matched_fields


def _contextual(query: _Signal, candidate: _Signal) -> bool:
    required = (
        "exporter_normalized",
        "vessel_normalized",
        "voyage_normalized",
        "loading_port_unlocode",
        "discharge_port_unlocode",
    )
    return query.bl_number_normalized != candidate.bl_number_normalized and all(
        getattr(query, field) is not None and getattr(query, field) == getattr(candidate, field)
        for field in required
    )


def _match(
    query: RegistrySignal, candidate: RegistryRegistration, queried_at: datetime
) -> CrossIBUMatch:
    score, matched_fields = weighted_similarity(query, candidate)
    exact_fingerprint = query.dna_fingerprint == candidate.dna_fingerprint
    exact_bl = bool(
        query.bl_number_normalized and query.bl_number_normalized == candidate.bl_number_normalized
    )
    config = matching_config()
    false_positive = (
        query.exporter_normalized is not None
        and query.exporter_normalized == candidate.exporter_normalized
        and query.bl_number_normalized is not None
        and candidate.bl_number_normalized is not None
        and query.bl_number_normalized != candidate.bl_number_normalized
        and query.vessel_normalized is not None
        and candidate.vessel_normalized is not None
        and query.vessel_normalized != candidate.vessel_normalized
        and query.shipment_date_iso is not None
        and candidate.shipment_date_iso is not None
        and query.shipment_date_iso != candidate.shipment_date_iso
    )
    if exact_fingerprint or exact_bl:
        level = MatchLevel.EXACT
        score = 1.0
        explanation = (
            "Exact normalized fingerprint or B/L match. Potential duplicate-financing "
            "investigation signal; not proof of duplicate financing or fraud."
        )
    elif false_positive:
        level = MatchLevel.NONE
        explanation = (
            "Same exporter but different B/L, vessel, and shipment date. Suppressed as a "
            "legitimate repeat-customer pattern; no duplicate-financing alert generated."
        )
    elif score >= float(config["likely_duplicate_threshold"]):
        level = MatchLevel.NEAR
        explanation = "High-similarity shipment pattern; review as a likely-duplicate signal."
    elif score >= float(config["possible_match_threshold"]):
        level = MatchLevel.NEAR
        explanation = "Similar shipment pattern; review as a possible-match signal."
    elif _contextual(query, candidate):
        level = MatchLevel.CONTEXTUAL
        explanation = "Same shipment context with a different B/L; review documentation variants."
    else:
        level = MatchLevel.NONE
        explanation = "Insufficient shipment overlap; no duplicate-financing alert generated."
    digest = hashlib.sha256(
        f"{query.case_id}:{candidate.registration_id}:{queried_at.isoformat()}".encode()
    ).hexdigest()[:24]
    return CrossIBUMatch(
        match_id=f"match-{digest}",
        querying_ibu_id=query.ibu_id,
        querying_case_id=query.case_id,
        matched_registration_id=candidate.registration_id,
        matched_ibu_id=candidate.ibu_id,
        match_level=level,
        similarity_score=round(score, 6),
        matched_fields=matched_fields,
        explanation=explanation,
        is_false_positive_candidate=false_positive,
        evidence_ref=f"registry://{candidate.registration_id}",
        queried_at=queried_at,
    )


def find_best_match(
    query: RegistrySignal,
    candidates: list[RegistryRegistration],
    queried_at: datetime,
) -> CrossIBUMatch:
    if not candidates:
        digest = hashlib.sha256(
            f"{query.case_id}:none:{queried_at.isoformat()}".encode()
        ).hexdigest()[:24]
        return CrossIBUMatch(
            match_id=f"match-{digest}",
            querying_ibu_id=query.ibu_id,
            querying_case_id=query.case_id,
            match_level=MatchLevel.NONE,
            similarity_score=0.0,
            matched_fields=[],
            explanation="No comparable registry signals found; no alert generated.",
            is_false_positive_candidate=False,
            queried_at=queried_at,
        )
    matches = [_match(query, candidate, queried_at) for candidate in candidates]
    priority = {
        MatchLevel.EXACT: 3,
        MatchLevel.NEAR: 2,
        MatchLevel.CONTEXTUAL: 1,
        MatchLevel.NONE: 0,
    }
    return max(
        matches,
        key=lambda item: (
            priority[item.match_level],
            item.similarity_score,
            item.matched_ibu_id != query.ibu_id,
        ),
    )
