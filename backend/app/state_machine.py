from __future__ import annotations


class InvalidTransitionError(RuntimeError):
    pass


VALID_TRANSITIONS: dict[str, set[str]] = {
    "created": {"uploaded", "failed"},
    "uploaded": {"transcribing", "failed"},
    "transcribing": {"selecting", "failed"},
    "selecting": {"awaiting_review", "failed"},
    "awaiting_review": {"rendering", "failed"},
    "rendering": {"completed", "awaiting_review", "failed"},
    "completed": {"awaiting_review"},
    "failed": {"uploaded", "transcribing", "awaiting_review", "rendering"},
}


def ensure_transition(current: str, target: str) -> None:
    allowed = VALID_TRANSITIONS.get(current)
    if not allowed or target not in allowed:
        raise InvalidTransitionError(f"Cannot transition from {current} to {target}")


def advance(project, target: str, *, reset_error: bool = True) -> None:
    ensure_transition(project.status, target)
    project.status = target
    if reset_error and target != "failed":
        project.error_message = None


def fail(project, message: str) -> None:
    message = message[:1024]
    if project.status == "failed":
        project.error_message = message
        return
    advance(project, "failed", reset_error=False)
    project.error_message = message
