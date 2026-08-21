from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from models.compliance import RuleDefinition


@lru_cache(maxsize=1)
def rule_definitions() -> dict[str, RuleDefinition]:
    path = Path(__file__).with_name("config") / "ucp600_rules.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    definitions = [RuleDefinition.model_validate(item) for item in payload["rules"]]
    return {definition.rule_id: definition for definition in definitions if definition.enabled}


def rule(rule_id: str) -> RuleDefinition:
    return rule_definitions()[rule_id]


def decimal_parameter(rule_id: str, name: str) -> str:
    return rule(rule_id).parameters[name]
