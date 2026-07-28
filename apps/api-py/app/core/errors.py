from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error, mapped to a JSON error response."""

    def __init__(self, message: str, status_code: int = 400, code: str = "app_error") -> None:
        self.message = message
        self.status_code = status_code
        self.code = code
        super().__init__(message)


class NotFoundError(AppError):
    """Raised when a record does not exist or is not owned by the caller.

    Mirrors the Node backend's NotFoundError: ownership failures are reported
    as 404 so the API never leaks the existence of another user's rows.
    """

    def __init__(self, message: str = "Not found", code: str = "not_found") -> None:
        super().__init__(message, status_code=404, code=code)


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )
