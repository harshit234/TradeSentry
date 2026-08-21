from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from tradesentry_api.config import Settings

_PRIVATE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PRIVATE_KEY_PEM = _PRIVATE_KEY.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption(),
).decode()
PUBLIC_KEY_PEM = _PRIVATE_KEY.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def secure_settings(**overrides: Any) -> Settings:
    return Settings(jwt_public_key=PUBLIC_KEY_PEM, **overrides)


def with_security(settings: Settings) -> Settings:
    return settings.model_copy(update={"jwt_public_key": PUBLIC_KEY_PEM})


def access_token(
    role: str = "ADMIN",
    ibu_id: str = "IBU-A",
    *,
    expires_delta: timedelta = timedelta(minutes=30),
    token_type: str = "access",
) -> str:
    now = datetime.now(UTC)
    return jwt.encode(
        {
            "officer_id": "test-officer-001",
            "role": role,
            "ibu_id": ibu_id,
            "iss": "tradesentry",
            "aud": "tradesentry-dashboard",
            "iat": now,
            "exp": now + expires_delta,
            "token_type": token_type,
        },
        PRIVATE_KEY_PEM,
        algorithm="RS256",
    )


def auth_headers(role: str = "ADMIN", ibu_id: str = "IBU-A") -> dict[str, str]:
    return {"Authorization": f"Bearer {access_token(role, ibu_id)}"}
