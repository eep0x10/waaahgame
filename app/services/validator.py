"""
Backwards-compatibility shim.

All callers that do:
    from app.services.validator import validate, ValidationResult, Issue, PointsBreakdown
continue to work unchanged.
"""
from app.services.validators import validate, validator_for  # noqa: F401
from app.services.validators._types import Issue, PointsBreakdown, ValidationResult  # noqa: F401

__all__ = ['validate', 'validator_for', 'ValidationResult', 'Issue', 'PointsBreakdown']
