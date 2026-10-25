"""Xác thực BE → MAIN: `Authorization: Bearer <MAIN_SERVICE_TOKEN>` (hợp đồng BE v0, chốt Q-11)."""

import base64
import binascii
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


def basic_auth_user(authorization: str | None, password: str) -> str | None:
    """Chế độ chấm cho đối tác: `Authorization: Basic` với mật khẩu chung; tên đăng nhập = tên người chấm.

    Trả tên người chấm (đã cắt khoảng trắng, ≤ 60 ký tự) hoặc None khi thiếu / sai.
    """
    if not authorization or not authorization.lower().startswith("basic "):
        return None
    try:
        raw = base64.b64decode(authorization[6:].strip(), validate=True)
    except (binascii.Error, ValueError):
        return None
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    user, sep, given = text.partition(":")
    user = user.strip()
    if not sep or not user or len(user) > 60:
        return None
    if not secrets.compare_digest(given.encode("utf-8"), password.encode("utf-8")):
        return None
    return user
