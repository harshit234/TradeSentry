from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from pathlib import Path
from typing import Any


class NormalizationError(ValueError):
    pass


@lru_cache(maxsize=1)
def normalization_config() -> dict[str, Any]:
    path = Path(__file__).with_name("config") / "normalization.json"
    return dict(json.loads(path.read_text(encoding="utf-8")))


def _words(raw: str) -> str:
    value = raw.casefold().replace(".", "")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return " ".join(value.split())


def normalize_entity_name(raw: str) -> str:
    tokens = _words(raw).split()
    suffixes = set(normalization_config()["legal_suffixes"])
    while tokens and tokens[-1] in suffixes:
        tokens.pop()
    return "_".join(tokens)


def normalize_port(raw: str) -> str | None:
    normalized = _words(raw)
    if not normalized:
        return None
    aliases: dict[str, str] = normalization_config()["port_aliases"]
    supplied_code = normalized.upper()
    if supplied_code in aliases.values():
        return supplied_code
    return aliases.get(normalized, normalized)


def normalize_hs_code(raw: str) -> str:
    compact = re.sub(r"[^A-Za-z0-9]", "", raw).upper()
    if len(compact) <= 4:
        return compact
    groups = [compact[:4]]
    groups.extend(compact[index : index + 2] for index in range(4, len(compact), 2))
    return ".".join(groups)


def normalize_date(raw: str) -> date:
    value = raw.strip()
    try:
        return date.fromisoformat(value)
    except ValueError:
        pass
    for pattern in ("%d/%m/%Y", "%m-%d-%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(value, pattern).date()  # noqa: DTZ007 - date-only value
        except ValueError:
            continue
    raise NormalizationError("Unsupported date format")


def normalize_quantity(value: Decimal, unit: str) -> tuple[Decimal, str]:
    normalized_unit = re.sub(r"[^A-Za-z0-9]", "", unit).upper()
    if normalized_unit in {"MT", "MTS", "METRICTON", "METRICTONS", "TONNE", "TONNES"}:
        return value, "MT"
    if normalized_unit in {"KG", "KGS", "KILOGRAM", "KILOGRAMS"}:
        return value / Decimal(1000), "MT"
    if normalized_unit in {"G", "GRAM", "GRAMS"}:
        return value / Decimal(1000000), "MT"
    if normalized_unit in {"L", "LTR", "LITRE", "LITRES", "LITER", "LITERS"}:
        return value, "L"
    if normalized_unit in {"M3", "CBM", "CUBICMETER", "CUBICMETERS"}:
        return value, "M3"
    if normalized_unit in {"UNIT", "UNITS", "PCS", "PIECE", "PIECES"}:
        return value, "UNITS"
    raise NormalizationError("Unsupported quantity unit")


def normalize_identifier(raw: str) -> str:
    return re.sub(r"\s+", "", raw).upper()


def normalize_free_text(raw: str) -> str:
    return "_".join(_words(raw).split())


def convert_currency_to_usd(value: Decimal, currency: str) -> Decimal | None:
    rates: dict[str, str] = normalization_config()["currency_to_usd"]
    rate = rates.get(currency.strip().upper())
    return value * Decimal(rate) if rate is not None else None
