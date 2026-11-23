from uuid import UUID

ALLOWED_MEMORY_ACTIONS = {"memory.add", "memory.update", "memory.delete"}


def validate_memory_proposal(action_type: str, target_id: str | None, payload: dict) -> UUID | None:
    """Allow only narrow memory proposals. No arbitrary tool or shell actions."""
    if action_type not in ALLOWED_MEMORY_ACTIONS:
        raise ValueError("Unsupported action type")

    if action_type == "memory.add":
        if target_id is not None:
            raise ValueError("memory.add must not specify a target_id")
        if not isinstance(payload.get("title"), str) or not payload["title"].strip():
            raise ValueError("A non-empty title is required")
        if not isinstance(payload.get("content"), str) or not payload["content"].strip():
            raise ValueError("Non-empty content is required")
        if len(payload["title"]) > 240 or len(payload["content"]) > 20000:
            raise ValueError("Memory title or content exceeds the allowed size")
        return None

    if not target_id:
        raise ValueError("An existing memory target_id is required")
    try:
        parsed_id = UUID(target_id)
    except (TypeError, ValueError) as exc:
        raise ValueError("target_id must be a valid UUID") from exc

    if action_type == "memory.update":
        if not payload or not ("title" in payload or "content" in payload):
            raise ValueError("Provide a title and/or content to update")
        if "title" in payload and (not isinstance(payload["title"], str) or not payload["title"].strip() or len(payload["title"]) > 240):
            raise ValueError("Updated title must be non-empty and at most 240 characters")
        if "content" in payload and (not isinstance(payload["content"], str) or not payload["content"].strip() or len(payload["content"]) > 20000):
            raise ValueError("Updated content must be non-empty and at most 20000 characters")
        return parsed_id

    if action_type == "memory.delete":
        if payload:
            raise ValueError("memory.delete must have an empty payload")
        return parsed_id

    raise ValueError("Unsupported action type")
