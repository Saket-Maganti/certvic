"""Project-specific exceptions."""


class CertVICError(Exception):
    """Base CertVIC error."""


class MissingOptionalDependencyError(CertVICError):
    """Raised when an optional dependency is required but unavailable."""


class ValidationFailure(CertVICError):
    """Raised when an artifact does not pass validation."""
