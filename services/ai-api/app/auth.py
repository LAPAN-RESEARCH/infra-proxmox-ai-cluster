from __future__ import annotations

import hmac
from ipaddress import ip_address
from typing import Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings


bearer = HTTPBearer(auto_error=False)


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return host in {"localhost"}


def _validate_credentials(credentials: HTTPAuthorizationCredentials | None) -> None:
    settings = get_settings()
    if not settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI_API_KEY is not configured",
        )
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not hmac.compare_digest(credentials.credentials, settings.api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def require_auth(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)) -> None:
    _validate_credentials(credentials)


async def require_health_auth(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> None:
    settings = get_settings()
    if settings.allow_local_healthz and _is_loopback(request.client.host if request.client else None):
        return
    _validate_credentials(credentials)
