# rules/normalization.py
# Pure Python. No LLM. No ML. No fuzzy — exact deterministic transforms.

import re
import hashlib
from datetime import date
from decimal import Decimal
from typing import Optional

LEGAL_SUFFIXES = [
    r'\bprivate\s+limited\b', r'\bpvt\.?\s*ltd\.?\b',
    r'\blimited\b', r'\bltd\.?\b',
    r'\bpte\.?\s*ltd\.?\b', r'\bpte\.?\b',
    r'\bincorporated\b', r'\binc\.?\b',
    r'\bcorporation\b', r'\bcorp\.?\b',
    r'\bllc\.?\b', r'\bllp\.?\b',
    r'\bco\.?\b', r'\band\s+co\.?\b',
    r'\b&\s*co\.?\b', r'\bcompany\b',
    r'\benterprises?\b', r'\btrading\b',
    r'\bexports?\b', r'\bimports?\b',
    r'\bagro\b', r'\binternational\b',
    r'\bglobal\b', r'\bgroup\b',
]

def normalize_entity_name(raw: str) -> str:
    s = raw.lower().strip()
    s = re.sub(r'(?<=\b\w)\.(?=\w\b|\s|$)', '', s)
    for suffix in LEGAL_SUFFIXES:
        s = re.sub(suffix, '', s, flags=re.IGNORECASE)
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.replace(' ', '_')
    return s


PORT_LOOKUP = {
    "mundra":        "INMUN",
    "nhava sheva":   "INNSA",
    "jnpt":          "INNSA",
    "jawaharlal nehru port": "INNSA",
    "kandla":        "INKLA",
    "chennai":       "INMAA",
    "hazira":        "INHAZ",
    "cochin":        "INCOK",
    "kochi":         "INCOK",
    "vizag":         "INVTZ",
    "visakhapatnam": "INVTZ",
    "singapore":     "SGSIN",
    "port klang":    "MYPKG",
    "klang":         "MYPKG",
    "colombo":       "LKCMB",
    "jebel ali":     "AEJEA",
    "dubai":         "AEDXB",
    "rotterdam":     "NLRTM",
    "hamburg":       "DEHAM",
    "antwerp":       "BEANR",
    "shanghai":      "CNSHA",
    "ningbo":        "CNNGB",
    "guangzhou":     "CNGZU",
    "hong kong":     "HKHKG",
    "busan":         "KRPUS",
    "tokyo":         "JPTYO",
}

def normalize_port(raw: str) -> Optional[str]:
    clean = raw.lower().strip()
    clean = re.sub(r'\(.*?\)', '', clean).strip()

    if clean in PORT_LOOKUP:
        return PORT_LOOKUP[clean]

    for key, code in PORT_LOOKUP.items():
        if key in clean or clean in key:
            return code

    return clean.replace(' ', '_')


def normalize_hs_code(raw: str) -> str:
    digits = re.sub(r'[\s.\-]', '', raw)
    if len(digits) >= 6:
        return digits[:4] + '.' + digits[4:6] + (
            '.' + digits[6:] if len(digits) > 6 else ''
        )
    return digits


DATE_FORMATS = [
    "%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d",
    "%d %b %Y", "%d %B %Y",
    "%d-%m-%Y", "%d.%m.%Y",
    "%b %d, %Y", "%B %d, %Y",
]

def normalize_date(raw: str) -> date:
    from datetime import datetime
    clean = raw.strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(clean, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Cannot parse date: {raw!r}. Tried {len(DATE_FORMATS)} formats.")


QUANTITY_CONVERSIONS = {
    ("kg", "mt"):    Decimal("0.001"),
    ("kgs", "mt"):   Decimal("0.001"),
    ("g", "mt"):     Decimal("0.000001"),
    ("lbs", "mt"):   Decimal("0.000453592"),
    ("tons", "mt"):  Decimal("1"),
    ("tonnes", "mt"): Decimal("1"),
    ("mt", "mt"):    Decimal("1"),
}

def normalize_quantity(value: Decimal, unit: str) -> tuple[Decimal, str]:
    unit_lower = unit.lower().strip()
    for (from_unit, to_unit), factor in QUANTITY_CONVERSIONS.items():
        if unit_lower == from_unit:
            return value * factor, to_unit.upper()
    return value, unit_lower.upper()


def generate_dna_fingerprint(
    bl_number_normalized: str,
    vessel_normalized: str,
    voyage_normalized: str,
    exporter_normalized: str,
    loading_port_unlocode: str,
    discharge_port_unlocode: str,
    shipment_date_iso: str
) -> str:
    payload = "|".join([
        bl_number_normalized.upper(),
        vessel_normalized.lower(),
        voyage_normalized.lower(),
        exporter_normalized.lower(),
        loading_port_unlocode.upper(),
        discharge_port_unlocode.upper(),
        shipment_date_iso,
    ])
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"
