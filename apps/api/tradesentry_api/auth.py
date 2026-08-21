from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import HTTPException, Request

from .config import Settings

OFFICER = "OFFICER"
COMPLIANCE_MANAGER = "COMPLIANCE_MANAGER"
AUDITOR = "AUDITOR"
ADMIN = "ADMIN"
VIEW_ROLES = {OFFICER, COMPLIANCE_MANAGER, AUDITOR, ADMIN}


@dataclass(frozen=True, slots=True)
class Principal:
    officer_id: str
    role: str
    ibu_id: str

    @property
    def subject(self) -> str:
        return self.officer_id


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def authenticate(authorization: str | None, settings: Settings) -> Principal:
    if authorization is None or not authorization.startswith("Bearer "):
        raise _unauthorized("Valid bearer token required")
    if not settings.jwt_public_key:
        raise HTTPException(status_code=503, detail="JWT verification key is not configured")
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_public_key,
            algorithms=["RS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=30,
            options={
                "require": ["exp", "iat", "officer_id", "role", "ibu_id", "token_type"]
            },
        )
        officer_id = str(claims["officer_id"]).strip()
        role = str(claims["role"]).strip().upper()
        ibu_id = str(claims["ibu_id"]).strip()
        token_type = str(claims["token_type"]).strip().lower()
        issued_at = int(claims["iat"])
        expires_at = int(claims["exp"])
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise _unauthorized("Invalid or expired bearer token") from exc
    if token_type != "access":
        raise _unauthorized("Access token required")
    if expires_at - issued_at > settings.jwt_access_ttl_seconds:
        raise _unauthorized("Access token lifetime exceeds policy")
    if not officer_id or not role or not ibu_id:
        raise _unauthorized("Token identity claims are incomplete")
    return Principal(officer_id=officer_id, role=role, ibu_id=ibu_id)


def request_principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if not isinstance(principal, Principal):
        raise _unauthorized("Authenticated principal unavailable")
    return principal


def require_roles(principal: Principal, *roles: str) -> None:
    if principal.role not in roles:
        raise HTTPException(status_code=403, detail="Role access denied")


def require_viewer(principal: Principal) -> None:
    require_roles(principal, *VIEW_ROLES)


def require_officer(principal: Principal) -> None:
    require_roles(principal, OFFICER)
