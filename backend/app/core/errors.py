"""Dual-shape error envelope: {code, message, details, detail}.

Angular handleError reads error.error.detail (string) or error.error.message.
Keep `detail` as the FastAPI/Starlette field so existing clients keep working.
"""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _envelope(
    status_code: int,
    message: str,
    *,
    detail: object,
    details: dict[str, list[str]] | None = None,
) -> dict:
    return {
        "code": str(status_code),
        "message": message,
        "details": details,
        "detail": detail,
    }


def _json_safe(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return str(value)


def _validation_details(exc: RequestValidationError) -> tuple[str, dict[str, list[str]], object]:
    fields: dict[str, list[str]] = {}
    for err in exc.errors():
        loc = err.get("loc") or ()
        key = str(loc[-1]) if loc else "body"
        fields.setdefault(key, []).append(err.get("msg") or "Invalid value")
    first = next((msgs[0] for msgs in fields.values() if msgs), "Validation error")
    return first, fields, _json_safe(exc.errors())


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        if isinstance(exc.detail, str):
            body = _envelope(exc.status_code, exc.detail, detail=exc.detail)
        else:
            body = _envelope(
                exc.status_code,
                "Request failed",
                detail=exc.detail,
            )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
        message, details, raw = _validation_details(exc)
        body = _envelope(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            message,
            detail=raw,
            details=details,
        )
        return JSONResponse(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content=body)
