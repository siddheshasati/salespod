from __future__ import annotations


class SalesPodError(Exception):
    """Base class for expected, user-facing application errors."""

    code = "SALES_POD_ERROR"


class ValidationError(SalesPodError):
    code = "VALIDATION_ERROR"


class NotFoundError(SalesPodError):
    code = "NOT_FOUND"


class ConflictError(SalesPodError):
    code = "CONFLICT"


class DuplicateRequestError(SalesPodError):
    code = "DUPLICATE_REQUEST"
