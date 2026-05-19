"""
Validator dispatcher.

validate(army) -> ValidationResult
Dispatches to the appropriate system validator based on army.faction.game_system.slug (or .code).
"""
from app.services.validators._types import Issue, PointsBreakdown, ValidationResult
from app.services.validators.aos import validate_aos
from app.services.validators.wh40k import validate_wh40k


def _get_system_slug(army):
    """Extract system slug from army. Supports both faction.game_system and army.system."""
    try:
        return army.faction.game_system.code  # GameSystem.code e.g. 'aos4', 'w40k10'
    except AttributeError:
        pass
    try:
        return army.system.slug
    except AttributeError:
        return 'aos'


# Codes that map to AoS validator
_AOS_CODES = {'aos4', 'aos', 'age_of_sigmar', 'age-of-sigmar'}
# Codes that map to 40k validator
_40K_CODES = {'40k', 'w40k10', 'wh40k', 'warhammer-40000', 'warhammer_40000'}


def validate(army):
    """
    Dispatch to the appropriate system validator.

    Routing:
      - GameSystem.code in _AOS_CODES  → validate_aos
      - GameSystem.code in _40K_CODES  → validate_wh40k
      - Default (unknown)              → validate_aos (safe fallback)
    """
    slug = _get_system_slug(army)
    slug_lower = (slug or '').lower()

    if slug_lower in _40K_CODES:
        return validate_wh40k(army)

    # AoS or default
    return validate_aos(army)


__all__ = ['validate', 'ValidationResult', 'Issue', 'PointsBreakdown']
