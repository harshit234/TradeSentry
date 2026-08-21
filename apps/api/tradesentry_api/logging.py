import contextvars
import json
import logging
import re
from datetime import UTC, datetime

correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "correlation_id", default="system"
)
case_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("case_id", default="system")
ibu_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("ibu_id", default="system")
event_type_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "event_type", default="APPLICATION_LOG"
)

SENSITIVE_PATTERNS = (
    re.compile(r"(?i)bearer\s+[A-Za-z0-9._~-]+"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?i)(api[_-]?key|secret|token|password)=([^\s,;]+)"),
    re.compile(r"https?://[^\s]+[?&]X-Amz-Signature=[^\s]+", re.IGNORECASE),
)


def redact_log_message(message: str) -> str:
    redacted = message
    for pattern in SENSITIVE_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
                "timestamp": datetime.now(UTC).isoformat(),
                "level": record.levelname,
                "logger": record.name,
                "message": redact_log_message(record.getMessage()),
                "correlation_id": correlation_id_var.get(),
                "case_id": case_id_var.get(),
                "event_type": event_type_var.get(),
                "ibu_id": ibu_id_var.get(),
        }
        for field in (
            "case_processing_latency_ms",
            "tool_call_latency_ms",
            "risk_band",
            "extraction_confidence",
            "cross_ibu_match_rate",
            "tool_name",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, separators=(",", ":"))


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
