"""Xác thực BE → MAIN: `Authorization: Bearer <MAIN_SERVICE_TOKEN>` (hợp đồng BE v0, chốt Q-11)."""

import secrets

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from drawing_checker.config import Settings, get_settings

_bearer = HTTPBearer(auto_error=False)


async def require_service_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    settings: Settings = Depends(get_settings),
) -> None:
    """Dependency cho các route BE gọi. Sai/thiếu token → 401."""
    if credentials is None or not secrets.compare_digest(credentials.credentials, settings.service_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "UNAUTHORIZED", "message": "Thiếu hoặc sai token dịch vụ"},
            headers={"WWW-Authenticate": "Bearer"},
        )
