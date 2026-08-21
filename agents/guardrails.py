from __future__ import annotations

import hashlib
import json
from typing import Any

from models.compliance import ComplianceResult
from rules.definitions import rule_definitions


class UnknownComplianceRuleError(ValueError):
    pass


def validate_compliance_rule_ids(result: ComplianceResult) -> ComplianceResult:
    approved = set(rule_definitions())
    unknown = sorted({finding.rule_id for finding in result.findings if finding.rule_id not in approved})
    if unknown:
        raise UnknownComplianceRuleError(f"Unknown compliance rule IDs rejected: {', '.join(unknown)}")
    return result


def safe_inputs_hash(values: dict[str, Any]) -> str:
    serialized = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()

