"""
Format → points-limit mapping per game system.

Delegates to the validator registry so adding a new wargame only requires
creating a validators/<system>.py file — no changes here.

Usage:
    from app.services.formats import SYSTEM_FORMATS, formats_for_system

    formats_for_system('aos4')   # -> {'vanguard': 1000, 'battlehost': 2000}
    formats_for_system('w40k10') # -> {'combat_patrol': 500, ...}
"""


def _get_registry():
    """Lazy import to avoid circular imports at module load time."""
    from app.services.validators.registry import get, all_systems
    return get, all_systems


def _get_system_formats() -> dict:
    """Build {code: {slug: pts}} from the live registry."""
    _, all_systems = _get_registry()
    return {code: dict(cls.formats) for code, cls in all_systems().items()}


def formats_for_system(system_code: str) -> dict:
    """Return {format_slug: points_limit} for the given system code."""
    get, _ = _get_registry()
    try:
        return dict(get(system_code).formats)
    except ValueError:
        return {}


def default_format(system_code: str) -> str:
    """Return the default format slug for the given system."""
    get, _ = _get_registry()
    try:
        return get(system_code).default_format
    except ValueError:
        return ""


def all_formats() -> dict:
    """Flat dict of all format slugs → points across all systems (legacy compat)."""
    _, all_systems = _get_registry()
    combined: dict = {}
    for cls in all_systems().values():
        combined.update(cls.formats)
    return combined


class _LazySystemFormats(dict):
    """
    Dict-like proxy that builds itself from the validator registry on first access.
    Supports `from app.services.formats import SYSTEM_FORMATS` callers that later
    read keys — same behaviour as the old hardcoded dict.
    """
    _loaded = False

    def _load(self):
        if not self._loaded:
            self.update(_get_system_formats())
            self._loaded = True

    def __getitem__(self, key):
        self._load()
        return super().__getitem__(key)

    def __iter__(self):
        self._load()
        return super().__iter__()

    def __len__(self):
        self._load()
        return super().__len__()

    def items(self):
        self._load()
        return super().items()

    def keys(self):
        self._load()
        return super().keys()

    def values(self):
        self._load()
        return super().values()

    def get(self, key, default=None):
        self._load()
        return super().get(key, default)

    def __contains__(self, key):
        self._load()
        return super().__contains__(key)


# Module-level dict for backward compat — lazy-loaded from registry
SYSTEM_FORMATS: dict = _LazySystemFormats()
