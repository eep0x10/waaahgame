"""
BaseValidator — base class for all wargame system validators.

Each system subclass declares class attributes that describe it,
so templates and routes can adapt UI without hardcoding system codes.
"""
from typing import ClassVar, Dict


class BaseValidator:
    # Canonical identifier matching GameSystem.code in DB
    code: ClassVar[str] = ""
    # Human-readable name
    name: ClassVar[str] = ""

    # Does this system organise units into groups (AoS regiments)?
    supports_groups: ClassVar[bool] = False
    # Does this system have a grand alliance / faction allegiance filter?
    supports_alliances: ClassVar[bool] = False

    # Labels used in templates when supports_groups is True
    group_label: ClassVar[str] = "Grupo"
    group_label_plural: ClassVar[str] = "Grupos"
    auxiliary_label: ClassVar[str] = "Auxiliar"

    # CSS accent colour for this system's theme
    color: ClassVar[str] = "#888888"

    # {format_slug: points_limit}
    formats: ClassVar[Dict[str, int]] = {}
    # Default format slug
    default_format: ClassVar[str] = ""

    def validate(self, army) -> "ValidationResult":  # noqa: F821
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement validate(army)"
        )

    def format_label(self, slug: str) -> str:
        """Human-readable label for a format slug (override if needed)."""
        return slug.replace("_", " ").title()
