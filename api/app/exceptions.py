from fastapi import HTTPException, status


class NotFoundException(HTTPException):
    """Resource not found exception (404)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class ConflictException(HTTPException):
    """Resource conflict exception (409)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class ValidationException(HTTPException):
    """Validation error exception (422)."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


# ===== Workflow-specific Exceptions =====


class TimerAlreadyRunningException(ConflictException):
    """Timer is already running (409)."""

    def __init__(self, detail: str = "Timer is already running"):
        super().__init__(detail)


class TimerNotRunningException(ConflictException):
    """No timer is currently running (409)."""

    def __init__(self, detail: str = "No timer is currently running"):
        super().__init__(detail)


class DependencyCycleException(ValidationException):
    """Dependency cycle detected (422)."""

    def __init__(self, detail: str = "Dependency cycle detected"):
        super().__init__(detail)


class TaskAlreadyCompletedException(ValidationException):
    """Task is already completed (422)."""

    def __init__(self, detail: str = "Task is already completed"):
        super().__init__(detail)


class ExternalAPIException(HTTPException):
    """Base class for external API errors (502)."""

    def __init__(self, detail: str, service: str):
        super().__init__(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"{service} API error: {detail}",
        )


class ClaudeAPIException(ExternalAPIException):
    """Claude API error (502)."""

    def __init__(self, detail: str):
        super().__init__(detail, "Claude")


class GoogleCalendarAPIException(ExternalAPIException):
    """Google Calendar API error (502)."""

    def __init__(self, detail: str):
        super().__init__(detail, "Google Calendar")
