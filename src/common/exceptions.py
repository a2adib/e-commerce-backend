from typing import Any, Optional
from pydantic import BaseModel
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class APIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        code: Optional[str] = None,
        headers: Optional[dict[str, str]] = None,
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code or f"HTTP_{status_code}"


def http_400(detail: str = "Bad request", code: str = "BAD_REQUEST") -> APIError:
    return APIError(status_code=400, detail=detail, code=code)


def http_401(detail: str = "Unauthorized", code: str = "UNAUTHORIZED") -> APIError:
    return APIError(status_code=401, detail=detail, code=code)


def http_403(detail: str = "Forbidden", code: str = "FORBIDDEN") -> APIError:
    return APIError(status_code=403, detail=detail, code=code)


def http_404(detail: str = "Resource not found", code: str = "NOT_FOUND") -> APIError:
    return APIError(status_code=404, detail=detail, code=code)


def http_409(detail: str = "Conflict", code: str = "CONFLICT") -> APIError:
    return APIError(status_code=409, detail=detail, code=code)


def http_422(detail: str = "Unprocessable Entity", code: str = "UNPROCESSABLE_ENTITY") -> APIError:
    return APIError(status_code=422, detail=detail, code=code)


async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": exc.code},
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "code": f"HTTP_{exc.status_code}"},
        headers=exc.headers,
    )
