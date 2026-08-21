from __future__ import annotations

from dataclasses import dataclass

import jwt
from fastapi import HTTPException

from .config import Settings

VIEW_ROLES = {"OFFICER", "COMPLIANCE_MANAGER", "AUDITOR", "ADMIN"}


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    role: str
    ibu_id: str


def authenticate(authorization: str | None, settings: Settings) -> Principal:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail="Valid bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = authorization.removeprefix("Bearer ").strip()
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["exp", "sub", "role", "ibu_id"]},
        )
        subject = str(claims["sub"]).strip()
        role = str(claims["role"]).strip().upper()
        ibu_id = str(claims["ibu_id"]).strip()
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if not subject or not role or not ibu_id:
        raise HTTPException(status_code=401, detail="Token identity claims are incomplete")
    return Principal(subject=subject, role=role, ibu_id=ibu_id)


def require_viewer(principal: Principal) -> None:
    if principal.role not in VIEW_ROLES:
        raise HTTPException(status_code=403, detail="Dashboard role access denied")


def require_officer(principal: Principal) -> None:
    if principal.role != "OFFICER":
        raise HTTPException(status_code=403, detail="Only an authenticated officer may decide")
