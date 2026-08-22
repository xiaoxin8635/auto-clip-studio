import pytest

from app.models import Project
from app.state_machine import InvalidTransitionError, advance, fail


def project(status="created"):
    item = Project(id="test", status=status)
    return item


def test_valid_primary_flow():
    item = project()
    for target in ["uploaded", "transcribing", "selecting", "awaiting_review", "rendering", "completed"]:
        advance(item, target)
    assert item.status == "completed"


def test_invalid_transition_is_rejected():
    with pytest.raises(InvalidTransitionError):
        advance(project("created"), "awaiting_review")


def test_failure_and_retry_states():
    item = project("transcribing")
    fail(item, "provider timeout")
    assert item.status == "failed"
    assert item.error_message == "provider timeout"
    advance(item, "awaiting_review")
    assert item.error_message is None
