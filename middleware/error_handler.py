import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from utils.errors import AppError


logger = logging.getLogger(__name__)


async def app_error_handler(
    request: Request,
    exc: AppError,
):
    logger.warning(
        "[%s] %s",
        exc.code,
        exc.message,
    )

    response = {
        "success": False,
        "error": {
            "code": exc.code,
            "message": exc.message,
        },
    }

    if exc.details is not None:
        response["error"]["details"] = exc.details

    return JSONResponse(
        status_code=exc.status_code,
        content=response,
    )


async def unexpected_error_handler(
    request: Request,
    exc: Exception,
):
    logger.exception(
        "Unhandled application error",
        exc_info=exc,
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