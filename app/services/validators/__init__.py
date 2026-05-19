"""
Validator dispatcher.

validate(army) -> ValidationResult
validator_for(system_code) -> BaseValidator instance

Dispatches to the appropriate system validator via the registry.
Unknown system codes raise ValueError (no silent fallback).
"""
from app.services.validators._types import Issue, PointsBreakdown, ValidationResult
from app.services.validators.base import BaseValidator
from app.services.validators.registry import register, get, all_systems

# Import validators so their @register decorators run
from app.services.validators import aos, wh40k  # noqa: F401


def validate(army) -> ValidationResult:
    """
    Dispatch to the appropriate system validator.

    Routing: army.faction.game_system.code → registry lookup.
    Raises ValueError if the system is unknown or missing.
    """
    code = None
    try:
        code = army.faction.game_system.code
    except AttributeError:
        pass

    if not code:
        raise ValueError(
            f"Army {getattr(army, 'id', '?')} has no game_system — "
            f"cannot determine validator."
        )

    return get(code)().validate(army)


def validator_for(system_code: str) -> BaseValidator:
    """Return an instantiated validator for the given system code."""
    return get(system_code)()


__all__ = [
    "validate",
    "validator_for",
    "register",
    "get",
    "all_systems",
    "BaseValidator",
    "ValidationResult",
    "Issue",
    "PointsBreakdown",
]
