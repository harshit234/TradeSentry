try:
    from rapidfuzz import fuzz
except ImportError:
    import difflib
    class FuzzFallback:
        @staticmethod
        def token_sort_ratio(s1: str, s2: str) -> float:
            t1 = " ".join(sorted(str(s1).split()))
            t2 = " ".join(sorted(str(s2).split()))
            return difflib.SequenceMatcher(None, t1, t2).ratio() * 100.0
    fuzz = FuzzFallback()

from datetime import date

FIELD_WEIGHTS = {
    "bl_number_normalized":     1.00,
    "voyage_normalized":        0.25,
    "vessel_normalized":        0.20,
    "exporter_normalized":      0.20,
    "shipment_date_iso":        0.15,
    "loading_port_unlocode":    0.10,
    "discharge_port_unlocode":  0.10,
}
TOTAL_WEIGHT = sum(FIELD_WEIGHTS.values())  # 2.00

THRESHOLD_LIKELY_DUPLICATE = 0.95
THRESHOLD_POSSIBLE_MATCH   = 0.85

def field_similarity(field_name: str, val_a: str, val_b: str) -> float:
    if val_a is None or val_b is None:
        return 0.0

    if field_name == "bl_number_normalized":
        return 1.0 if str(val_a).upper() == str(val_b).upper() else 0.0

    if field_name == "shipment_date_iso":
        try:
            d_a = date.fromisoformat(str(val_a))
            d_b = date.fromisoformat(str(val_b))
            diff = abs((d_a - d_b).days)
            if diff == 0:   return 1.0
            if diff <= 7:   return 0.5
            return 0.0
        except ValueError:
            return 0.0

    return fuzz.token_sort_ratio(str(val_a).lower(), str(val_b).lower()) / 100.0


def weighted_similarity(tx_a: dict, tx_b: dict) -> tuple[float, list[str]]:
    if (tx_a.get("bl_number_normalized", "").upper() ==
        tx_b.get("bl_number_normalized", "").upper() and
        tx_a.get("bl_number_normalized")):
        return 1.0, list(FIELD_WEIGHTS.keys())

    score = 0.0
    matched_fields = []

    for field, weight in FIELD_WEIGHTS.items():
        if field == "bl_number_normalized":
            continue

        sim = field_similarity(field, tx_a.get(field, ""), tx_b.get(field, ""))
        score += weight * sim

        if sim >= 0.85:
            matched_fields.append(field)

    normalized_score = score / TOTAL_WEIGHT

    return round(normalized_score, 4), matched_fields


def classify_match(similarity: float) -> tuple[str, str]:
    if similarity >= 1.0:
        return "EXACT", "LIKELY_DUPLICATE"
    if similarity >= THRESHOLD_LIKELY_DUPLICATE:
        return "NEAR", "LIKELY_DUPLICATE"
    if similarity >= THRESHOLD_POSSIBLE_MATCH:
        return "NEAR", "POSSIBLE_MATCH"
    return "NONE", "NO_SIGNAL"
