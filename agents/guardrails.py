from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from models.compliance import ComplianceResult
from rules.definitions import rule_definitions


class UnknownComplianceRuleError(ValueError):
    pass


_PROMPT_INJECTION_PATTERNS = (
    re.compile(r"\bsystem\s*:\s*ignore\b", re.IGNORECASE),
    re.compile(r"\bignore\s+(all\s+)?previous\s+instructions\b", re.IGNORECASE),
    re.compile(r"\bapprove\s+(this\s+)?case\s+immediately\b", re.IGNORECASE),
    re.compile(r"\bcall\s+(an?\s+)?(?:unapproved|arbitrary|settlement)\s+tool\b", re.IGNORECASE),
)


def prompt_injection_fingerprint(document_text: str) -> str | None:
    """Return only an opaque hash when adversarial instruction-like content is detected."""
    if not any(pattern.search(document_text) for pattern in _PROMPT_INJECTION_PATTERNS):
        return None
    return hashlib.sha256(document_text.encode()).hexdigest()


def validate_compliance_rule_ids(result: ComplianceResult) -> ComplianceResult:
    approved = set(rule_definitions())
    unknown = sorted({finding.rule_id for finding in result.findings if finding.rule_id not in approved})
    if unknown:
        raise UnknownComplianceRuleError(f"Unknown compliance rule IDs rejected: {', '.join(unknown)}")
    return result


def safe_inputs_hash(values: dict[str, Any]) -> str:
    serialized = json.dumps(values, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()
