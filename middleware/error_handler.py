
import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from utils.errors import AppError
from utils.secret_redaction import (
    redact_text,
    redact_sensitive_data,
)


logger = logging.getLogger(__name__)


async def app_error_handler(
    request: Request,
    exc: AppError,
):
    safe_message = redact_text(exc.message)
    safe_details = redact_sensitive_data(exc.details)

    logger.warning(
        "[%s] %s",
        exc.code,
        safe_message,
    )

    response = {
        "success": False,
        "error": {
            "code": exc.code,
            "message": safe_message,
        },
    }

    if safe_details is not None:
        response["error"]["details"] = safe_details

    return JSONResponse(
        status_code=exc.status_code,
        content=response,
    )


async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    # Avoid logging raw exception tracebacks that may
    # contain credentials or connection strings.
    logger.error(
        "Unhandled application error: %s",
        redact_text(str(exc)),
    )

    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
            },
        },
    )
