import base64
import json
import uuid
from datetime import datetime
from typing import Any

import httpx
from fastapi import Depends, FastAPI, HTTPException

from .config import BROWSER_AGENT_URL, BROWSER_INTERNAL_TOKEN
from .db import connection
from .policy import validate_memory_proposal
from .schemas import ApprovalCreate, ApprovalDecision, BrowserNavigate, ChatInput
from .security import require_owner

app = FastAPI(
    title="Aakash AI API",
    version="0.1.0",
    description="Local-first personal intelligence scaffold. No external model provider is configured.",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
    redoc_url="/api/redoc",
)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def _serialize(row: dict) -> dict:
    return {key: _json_value(value) for key, value in row.items()}


@app.get("/api/health", tags=["system"])
def health() -> dict:
    return {"status": "ok", "service": "aakash-ai-api", "version": "0.1.0"}


@app.get("/api/status", tags=["system"], dependencies=[Depends(require_owner)])
def status() -> dict:
    try:
        with connection() as conn:
            conn.execute("SELECT 1")
    except Exception as exc:  # health detail is returned without leaking credentials
        raise HTTPException(status_code=503, detail="Database is not ready") from exc
    return {
        "status": "ready",
        "environment": "local",
        "model_provider": None,
        "external_model_calls_enabled": False,
        "memory_write_policy": "owner_approval_required",
        "browser_mode": "public_read_only",
    }


@app.post("/api/chat", tags=["chat"], dependencies=[Depends(require_owner)])
def chat(body: ChatInput) -> dict:
    # Deliberately no LLM call and no persistence in milestone 0.
    return {
        "role": "assistant",
        "content": (
            "Aakash AI's local foundation is running. The reasoning model is not connected yet, "
            "so I have not sent this message to any external AI provider or saved it as memory. "
            "The next milestone is the model adapter and reviewed personal knowledge ingestion."
        ),
        "received_characters": len(body.message),
        "persisted": False,
        "external_ai_called": False,
    }


@app.get("/api/memories", tags=["memory"], dependencies=[Depends(require_owner)])
def list_memories() -> dict:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, category, title, content, source, confidence, metadata, created_at, updated_at "
            "FROM memories ORDER BY updated_at DESC LIMIT 200"
        ).fetchall()
    return {"items": [_serialize(dict(row)) for row in rows]}


@app.get("/api/approvals", tags=["approvals"], dependencies=[Depends(require_owner)])
def list_approvals() -> dict:
    with connection() as conn:
        rows = conn.execute(
            "SELECT id, action_type, target_id, payload, reason, status, requested_by, decided_by, created_at, decided_at "
            "FROM approvals ORDER BY created_at DESC LIMIT 100"
        ).fetchall()
    return {"items": [_serialize(dict(row)) for row in rows]}


@app.post("/api/approvals", status_code=201, tags=["approvals"], dependencies=[Depends(require_owner)])
def create_approval(body: ApprovalCreate) -> dict:
    try:
        target_uuid = validate_memory_proposal(body.action_type, body.target_id, body.payload)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    approval_id = uuid.uuid4()
    with connection() as conn:
        if target_uuid is not None:
            exists = conn.execute("SELECT 1 FROM memories WHERE id = %s", (target_uuid,)).fetchone()
            if not exists:
                raise HTTPException(status_code=404, detail="Target memory does not exist")
        conn.execute(
            "INSERT INTO approvals (id, action_type, target_id, payload, reason) "
            "VALUES (%s, %s, %s, %s::jsonb, %s)",
            (approval_id, body.action_type, target_uuid, json.dumps(body.payload), body.reason),
        )
        conn.execute(
            "INSERT INTO audit_events (actor, action, resource_type, resource_id, details) "
            "VALUES ('owner', 'approval.requested', 'approval', %s, %s::jsonb)",
            (str(approval_id), json.dumps({"action_type": body.action_type, "reason": body.reason})),
        )
    return {"id": str(approval_id), "status": "pending", "action_type": body.action_type, "message": "Owner approval is required before this operation changes memory."}


@app.post("/api/approvals/{approval_id}/decision", tags=["approvals"], dependencies=[Depends(require_owner)])
def decide_approval(approval_id: uuid.UUID, body: ApprovalDecision) -> dict:
    with connection() as conn:
        approval = conn.execute(
            "SELECT id, action_type, target_id, payload, reason, status FROM approvals WHERE id = %s FOR UPDATE",
            (approval_id,),
        ).fetchone()
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")
        if approval["status"] != "pending":
            raise HTTPException(status_code=409, detail=f"Approval is already {approval['status']}")

        if body.decision == "reject":
            conn.execute(
                "UPDATE approvals SET status='rejected', decided_by='owner', decided_at=NOW() WHERE id=%s",
                (approval_id,),
            )
            conn.execute(
                "INSERT INTO audit_events (actor, action, resource_type, resource_id, details) "
                "VALUES ('owner', 'approval.rejected', 'approval', %s, %s::jsonb)",
                (str(approval_id), json.dumps({"action_type": approval["action_type"]})),
            )
            return {"id": str(approval_id), "status": "rejected", "changed_memory": False}

        payload = approval["payload"] or {}
        action_type = approval["action_type"]
        target_id = approval["target_id"]
        if action_type == "memory.add":
            memory_id = uuid.uuid4()
            conn.execute(
                "INSERT INTO memories (id, category, title, content, source, confidence, metadata) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)",
                (memory_id, payload.get("category", "general"), payload["title"], payload["content"],
                 payload.get("source", "owner-approved"), payload.get("confidence", 0.9),
                 json.dumps(payload.get("metadata", {}))),
            )
            resource_id = str(memory_id)
        elif action_type == "memory.update":
            current = conn.execute("SELECT title, content FROM memories WHERE id=%s FOR UPDATE", (target_id,)).fetchone()
            if not current:
                raise HTTPException(status_code=404, detail="Target memory no longer exists")
            title = payload.get("title", current["title"])
            content = payload.get("content", current["content"])
            conn.execute(
                "UPDATE memories SET title=%s, content=%s, updated_at=NOW() WHERE id=%s",
                (title, content, target_id),
            )
            resource_id = str(target_id)
        elif action_type == "memory.delete":
            deleted = conn.execute("DELETE FROM memories WHERE id=%s RETURNING id", (target_id,)).fetchone()
            if not deleted:
                raise HTTPException(status_code=404, detail="Target memory no longer exists")
            resource_id = str(target_id)
        else:  # Defense in depth: the schema and proposal validator also enforce this allowlist.
            raise HTTPException(status_code=422, detail="Unsupported action")

        conn.execute(
            "UPDATE approvals SET status='approved', decided_by='owner', decided_at=NOW() WHERE id=%s",
            (approval_id,),
        )
        conn.execute(
            "INSERT INTO audit_events (actor, action, resource_type, resource_id, details) "
            "VALUES ('owner', %s, 'memory', %s, %s::jsonb)",
            (f"{action_type}.approved_and_executed", resource_id,
             json.dumps({"approval_id": str(approval_id), "reason": approval["reason"]})),
        )
    return {"id": str(approval_id), "status": "approved", "changed_memory": True, "resource_id": resource_id}


@app.post("/api/browser/navigate", tags=["browser"], dependencies=[Depends(require_owner)])
async def browser_navigate(body: BrowserNavigate) -> dict:
    """User-initiated, read-only navigation. The browser service applies network restrictions."""
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
    # Keep a bounded screenshot payload; frontend renders it as a data URL.
    screenshot = result.get("screenshot_b64", "")
    if len(screenshot) > 2_000_000:
        raise HTTPException(status_code=502, detail="Screenshot exceeded response limit")
    return result
