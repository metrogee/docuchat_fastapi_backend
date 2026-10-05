class AppError(Exception):
    def __init__(
        self,
        message: str,
        status_code: int,
        code: str,
        details=None,
    ):
        super().__init__(message)

        self.message = message
        self.status_code = status_code
        self.code = code
        self.is_operational = True
        self.details = details


class ValidationError(AppError):
    def __init__(self, message: str, details=None):
        super().__init__(
            message,
            400,
            "VALIDATION_ERROR",
            details,
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message,
            401,
            "UNAUTHORIZED",
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Access denied"):
        super().__init__(
            message,
            403,
            "FORBIDDEN",
        )


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(
            message,
            404,
            "NOT_FOUND",
        )


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(
            message,
            409,
            "CONFLICT",
        )