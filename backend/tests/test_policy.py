import pytest

from app.policy import validate_memory_proposal


def test_memory_add_requires_content_and_no_target():
    validate_memory_proposal("memory.add", None, {"title": "Java", "content": "Collections"})
    with pytest.raises(ValueError):
        validate_memory_proposal("memory.add", None, {"title": "Java"})
    with pytest.raises(ValueError):
        validate_memory_proposal("memory.add", "00000000-0000-0000-0000-000000000001", {"title": "x", "content": "y"})


def test_memory_update_requires_uuid_and_fields():
    target = "a4e4d69b-c965-4d4b-9f01-7a2eb7b88f22"
    assert str(validate_memory_proposal("memory.update", target, {"content": "Updated"})) == target
    with pytest.raises(ValueError):
        validate_memory_proposal("memory.update", target, {})
    with pytest.raises(ValueError):
        validate_memory_proposal("memory.update", "not-a-uuid", {"title": "Updated"})


def test_memory_delete_requires_empty_payload():
    target = "a4e4d69b-c965-4d4b-9f01-7a2eb7b88f22"
    assert str(validate_memory_proposal("memory.delete", target, {})) == target
    with pytest.raises(ValueError):
        validate_memory_proposal("memory.delete", target, {"force": True})


def test_arbitrary_actions_are_not_allowed():
    for action in ("shell.exec", "github.merge", "email.send", "cloud.deploy", "file.write"):
        with pytest.raises(ValueError):
            validate_memory_proposal(action, None, {})
