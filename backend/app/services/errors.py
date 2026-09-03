from __future__ import annotations


class ServiceError(Exception):
    """Domain error carrying the HTTP status code fixed by docs/CONTRACT.md."""

    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


class NotFound(ServiceError):
    def __init__(self, detail: str):
        super().__init__(404, detail)


class Conflict(ServiceError):
    def __init__(self, detail: str):
        super().__init__(409, detail)


class Unprocessable(ServiceError):
    def __init__(self, detail: str):
        super().__init__(422, detail)
