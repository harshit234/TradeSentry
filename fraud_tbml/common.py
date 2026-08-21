from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


class DataUnavailableError(RuntimeError):
    """Raised by a provider when its external data source is unavailable."""


def load_json(relative_path: str) -> dict[str, Any]:
    path = ROOT / relative_path
    return dict(json.loads(path.read_text(encoding="utf-8")))


def retrieved_now() -> datetime:
    return datetime.now(UTC)


def normalize_name(value: str) -> str:
    return " ".join("".join(character.lower() if character.isalnum() else " " for character in value).split())

