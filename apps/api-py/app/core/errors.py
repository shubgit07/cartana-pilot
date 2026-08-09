from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error, mapped to a JSON error response."""

    def __init__(self, message: str, status_code: int = 400, code: str = "app_error") -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class ValidationError(AppError):
    """Raised for requests the service layer cannot accept (HTTP 400).

    FastAPI already rejects malformed bodies with 422; this covers checks that
    need database or domain context, such as a source that belongs to another
    project.
    """

    def __init__(self, message: str = "Invalid request", code: str = "validation_error") -> None:
        super().__init__(message, status_code=400, code=code)


class NotFoundError(AppError):
    """Raised when a record does not exist or is not owned by the caller.

    Mirrors the Node backend's NotFoundError: ownership failures are reported
    as 404 so the API never leaks the existence of another user's rows.
    """

    def __init__(self, message: str = "Not found", code: str = "not_found") -> None:
        super().__init__(message, status_code=404, code=code)


class PayloadTooLargeError(AppError):
    """Raised when an upload exceeds the configured size limit (HTTP 413)."""

    def __init__(self, message: str = "Payload too large", code: str = "payload_too_large") -> None:
        super().__init__(message, status_code=413, code=code)


class LLMServiceError(AppError):
    """Raised when an LLM call is required but unavailable or returns unusable output.

    The decomposed PR verification pipeline never degrades to keyword
    heuristics: if the LLM cannot produce a structured verdict the request
    fails loudly (HTTP 502) rather than returning fabricated results.
    """

    def __init__(
        self,
        message: str = "LLM verification unavailable",
        code: str = "llm_service_error",
    ) -> None:
        super().__init__(message, status_code=502, code=code)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
