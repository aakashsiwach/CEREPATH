import hashlib
import hmac
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import APP_ENV, CEREPATH_OWNER_TOKEN, OWNER_USER_ID, SESSION_COOKIE_NAME
from .db import connection

_bearer = HTTPBearer(auto_error=False)


def _sha256(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def require_owner(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> UUID:
    """Resolve the local owner or a live browser session to an isolated user ID."""
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        with connection() as conn:
            session = conn.execute(
                """
                SELECT s.user_id, s.csrf_token_hash, u.is_active
                FROM sessions AS s
                JOIN users AS u ON u.id = s.user_id
                WHERE s.token_hash = %s
                  AND s.revoked_at IS NULL
                  AND s.expires_at > NOW()
                """,
                (_sha256(session_token),),
            ).fetchone()
            if not session or not session["is_active"]:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired or revoked")
            if request.method.upper() not in {"GET", "HEAD", "OPTIONS"}:
                supplied_csrf = request.headers.get("X-CSRF-Token", "")
                if not supplied_csrf or not hmac.compare_digest(
                    _sha256(supplied_csrf), session["csrf_token_hash"]
                ):
                    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF validation failed")
            conn.execute(
                "UPDATE sessions SET last_seen_at = NOW() WHERE token_hash = %s AND revoked_at IS NULL",
                (_sha256(session_token),),
            )
        return UUID(str(session["user_id"]))

    # Transitional single-owner bootstrap authentication is deliberately local-only.
    if APP_ENV == "local" and credentials and credentials.scheme.lower() == "bearer":
        if hmac.compare_digest(credentials.credentials, CEREPATH_OWNER_TOKEN):
            return UUID(OWNER_USER_ID)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Owner session required. Sign in to create a local session.",
    )
