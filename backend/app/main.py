import hashlib
import json
import secrets
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi import status as http_status
from uuid import UUID

from .config import (
    APP_ENV,
    BROWSER_AGENT_URL,
    BROWSER_INTERNAL_TOKEN,
    CEREPATH_OWNER_TOKEN,
    OWNER_USER_ID,
    RUN_DB_MIGRATIONS,
    SESSION_COOKIE_NAME,
    SESSION_TTL_HOURS,
)
from .db import apply_migrations, connection
from .policy import validate_memory_proposal
from .schemas import ApprovalCreate, ApprovalDecision, BootstrapLogin, BrowserNavigate, ChatInput
from .security import require_owner


@asynccontextmanager
async def lifespan(_: FastAPI):
    if RUN_DB_MIGRATIONS:
        apply_migrations()
    yield


app = FastAPI(
    title="Cerepath API",
    version="0.3.0",
    description="Local personal intelligence platform with owner-controlled sessions and memory.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _serialize(row: dict) -> dict:
    return {key: _json_value(value) for key, value in row.items()}


def _hash_token(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=APP_ENV != "local",
        samesite="strict",
        max_age=SESSION_TTL_HOURS * 3600,
        path="/api",
    )


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "cerepath-api", "version": "0.3.0"}


@app.post("/api/auth/login", tags=["authentication"])
def login(body: BootstrapLogin, response: Response) -> dict:
    """Exchange the local bootstrap secret for a revocable, HTTP-only browser session."""
    if APP_ENV != "local":
        raise HTTPException(status_code=http_status.NOT_FOUND, detail="Local bootstrap login is disabled")
    if not secrets.compare_digest(body.owner_token, CEREPATH_OWNER_TOKEN):
        raise HTTPException(status_code=http_status.UNAUTHORIZED, detail="Invalid owner token")

    session_token = secrets.token_urlsafe(48)
    csrf_token = secrets.token_urlsafe(32)
    session_id = uuid.uuid4()
    with connection() as conn:
        owner = conn.execute(
            "SELECT id, email, display_name FROM users WHERE id = %s AND is_active = TRUE",
            (uuid.UUID(OWNER_USER_ID),),
        ).fetchone()
        if not owner:
            raise HTTPException(status_code=http_status.SERVICE_UNAVAILABLE, detail="Owner identity is not provisioned")
        conn.execute(
            """
            INSERT INTO sessions (id, user_id, token_hash, csrf_token_hash, expires_at)
            VALUES (%s, %s, %s, %s, NOW() + (%s * INTERVAL '1 hour'))
            """,
            (session_id, uuid.UUID(OWNER_USER_ID), _hash_token(session_token), _hash_token(csrf_token), SESSION_TTL_HOURS),
        )
    _set_session_cookie(response, session_token)
    return {
        "authenticated": True,
        "csrf_token": csrf_token,
        "expires_in": SESSION_TTL_HOURS * 3600,
        "user": {"id": str(owner["id"]), "email": owner["email"], "display_name": owner["display_name"]},
    }


@app.get("/api/auth/session", tags=["authentication"])
def current_session(user_id: UUID = Depends(require_owner)) -> dict:
    with connection() as conn:
        user = conn.execute(
            "SELECT id, email, display_name FROM users WHERE id = %s AND is_active = TRUE",
            (user_id,),
        ).fetchone()
    if not user:
        raise HTTPException(status_code=http_status.UNAUTHORIZED, detail="Owner identity is unavailable")
    return {"authenticated": True, "user": _serialize(user)}


@app.post("/api/auth/logout", tags=["authentication"])
def logout(request: Request, response: Response, user_id: UUID = Depends(require_owner)) -> dict:
    session_token = request.cookies.get(SESSION_COOKIE_NAME)
    if session_token:
        with connection() as conn:
            conn.execute(
                "UPDATE sessions SET revoked_at = NOW() WHERE token_hash = %s AND user_id = %s AND revoked_at IS NULL",
                (_hash_token(session_token), user_id),
            )
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/api",
        secure=APP_ENV != "local",
        httponly=True,
        samesite="strict",
    )
    return {"authenticated": False, "revoked": bool(session_token)}


@app.get("/api/status", tags=["system"])
def status(_: str = Depends(require_owner)) -> dict:
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {
        "status": "ready",
        "environment": APP_ENV,
        "authentication": "revocable_http_only_session",
        "model_provider": None,
        "external_model_calls_enabled": False,
        "memory_write_policy": "owner_approval_required",
        "browser_mode": "https_read_only_via_egress_proxy",
    }


@app.post("/api/chat", tags=["chat"])
def chat(body: ChatInput, user_id: UUID = Depends(require_owner)) -> dict:
    # Deliberately no LLM call and no persistence in milestone 1.
    return {
        "role": "assistant",
        "content": (
            "Cerepath's identity and session foundation is running. The reasoning model is not connected yet, "
            "so this message was not sent to an external AI provider or saved as memory."
        ),
        "received_characters": len(body.message),
        "persisted": False,
        "external_ai_called": False,
        "user_id": str(user_id),
    }


@app.get("/api/memories", tags=["memory"])
def list_memories(user_id: UUID = Depends(require_owner)) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, category, title, content, source, confidence, metadata, created_at, updated_at
            FROM memories WHERE user_id = %s ORDER BY updated_at DESC LIMIT 200
            """,
            (user_id,),
        ).fetchall()
    return {"items": [_serialize(dict(row)) for row in rows]}


@app.get("/api/approvals", tags=["approvals"])
def list_approvals(user_id: UUID = Depends(require_owner)) -> dict:
    with connection() as conn:
        rows = conn.execute(
            """
            SELECT id, action_type, target_id, payload, reason, status, requested_by, decided_by, created_at, decided_at
            FROM approvals WHERE user_id = %s ORDER BY created_at DESC LIMIT 100
            """,
            (user_id,),
        ).fetchall()
    return {"items": [_serialize(dict(row)) for row in rows]}


@app.post("/api/approvals", status_code=201, tags=["approvals"])
def create_approval(body: ApprovalCreate, user_id: UUID = Depends(require_owner)) -> dict:
    try:
        target_uuid = validate_memory_proposal(body.action_type, body.target_id, body.payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    approval_id = uuid.uuid4()
    with connection() as conn:
        if target_uuid is not None:
            exists = conn.execute(
                "SELECT 1 FROM memories WHERE id = %s AND user_id = %s",
                (target_uuid, user_id),
            ).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Target memory does not exist")
        conn.execute(
            """
            INSERT INTO approvals (id, user_id, action_type, target_id, payload, reason)
            VALUES (%s, %s, %s, %s, %s::jsonb, %s)
            """,
            (approval_id, user_id, body.action_type, target_uuid, json.dumps(body.payload), body.reason),
        )
        conn.execute(
            """
            INSERT INTO audit_events (user_id, actor, action, resource_type, resource_id, details)
            VALUES (%s, 'owner', 'approval.requested', 'approval', %s, %s::jsonb)
            """,
            (user_id, str(approval_id), json.dumps({"action_type": body.action_type, "reason": body.reason})),
        )
    return {
        "id": str(approval_id),
        "status": "pending",
        "action_type": body.action_type,
        "message": "Owner approval is required before this operation changes memory.",
    }


@app.post("/api/approvals/{approval_id}/decision", tags=["approvals"])
def decide_approval(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    user_id: UUID = Depends(require_owner),
) -> dict:
    with connection() as conn:
        approval = conn.execute(
            """
            SELECT id, action_type, target_id, payload, reason, status
            FROM approvals WHERE id = %s AND user_id = %s FOR UPDATE
            """,
            (approval_id, user_id),
        ).fetchone()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")
        if approval["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"Approval is already {approval['status']}")

        if body.decision == "reject":
            conn.execute(
                """
                UPDATE approvals SET status='rejected', decided_by='owner', decided_at=NOW()
                WHERE id=%s AND user_id=%s
                """,
                (approval_id, user_id),
            )
            conn.execute(
                """
                INSERT INTO audit_events (user_id, actor, action, resource_type, resource_id, details)
                VALUES (%s, 'owner', 'approval.rejected', 'approval', %s, %s::jsonb)
                """,
                (user_id, str(approval_id), json.dumps({"action_type": approval["action_type"]})),
            )
            return {"id": str(approval_id), "status": "rejected", "changed_memory": False}

        payload = approval["payload"] or {}
        action_type = approval["action_type"]
        target_id = approval["target_id"]
        if action_type == "memory.add":
            memory_id = uuid.uuid4()
            conn.execute(
                """
                INSERT INTO memories (id, user_id, category, title, content, source, confidence, metadata)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                """,
                (
                    memory_id, user_id, payload.get("category", "general"), payload["title"],
                    payload["content"], payload.get("source", "owner-approved"),
                    payload.get("confidence", 0.9), json.dumps(payload.get("metadata", {})),
                ),
            )
            resource_id = str(memory_id)
        elif action_type == "memory.update":
            current = conn.execute(
                "SELECT title, content FROM memories WHERE id=%s AND user_id=%s FOR UPDATE",
                (target_id, user_id),
            ).fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Target memory no longer exists")
            title = payload.get("title", current["title"])
            content = payload.get("content", current["content"])
            conn.execute(
                "UPDATE memories SET title=%s, content=%s, updated_at=NOW() WHERE id=%s AND user_id=%s",
                (title, content, target_id, user_id),
            )
            resource_id = str(target_id)
        elif action_type == "memory.delete":
            deleted = conn.execute(
                "DELETE FROM memories WHERE id=%s AND user_id=%s RETURNING id",
                (target_id, user_id),
            ).fetchone()
            if not deleted:
                raise HTTPException(status_code=404, detail="Target memory no longer exists")
            resource_id = str(target_id)
        else:
            raise HTTPException(status_code=422, detail="Unsupported action")

        conn.execute(
            "UPDATE approvals SET status='approved', decided_by='owner', decided_at=NOW() WHERE id=%s AND user_id=%s",
            (approval_id, user_id),
        )
        conn.execute(
            """
            INSERT INTO audit_events (user_id, actor, action, resource_type, resource_id, details)
            VALUES (%s, 'owner', %s, 'memory', %s, %s::jsonb)
            """,
            (
                user_id, f"{action_type}.approved_and_executed", resource_id,
                json.dumps({"approval_id": str(approval_id), "reason": approval["reason"]}),
            ),
        )
    return {"id": str(approval_id), "status": "approved", "changed_memory": True, "resource_id": resource_id}


@app.post("/api/browser/navigate", tags=["browser"])
async def browser_navigate(
    body: BrowserNavigate,
    _: str = Depends(require_owner),
) -> dict:
    """User-initiated, read-only navigation. The browser and egress proxy enforce network restrictions."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BROWSER_AGENT_URL}/navigate",
                json={"url": str(body.url)},
                headers={"Authorization": f"Bearer {BROWSER_INTERNAL_TOKEN}"},
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Browser service is unavailable") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", "Browser navigation failed")
        except ValueError:
            detail = "Browser navigation failed"
        raise HTTPException(status_code=response.status_code, detail=detail)
    result = response.json()
    screenshot = result.get("screenshot_b64", "")
    if len(screenshot) > 2_000_000:
        raise HTTPException(status_code=502, detail="Screenshot exceeded response limit")
    return result
