"""
Format → points-limit mapping per game system.

Usage:
    from app.services.formats import SYSTEM_FORMATS, formats_for_system

    formats_for_system('aos4')   # -> {'vanguard': 1000, 'battlehost': 2000, 'spearhead': 1000}
    formats_for_system('w40k10') # -> {'combat_patrol': 500, ...}
"""

SYSTEM_FORMATS = {
    # Age of Sigmar 4e
    'aos4': {
        'vanguard':   1000,
        'battlehost': 2000,
        'spearhead':  1000,
    },
    # Warhammer 40,000 10e
    'w40k10': {
        'combat_patrol': 500,
        'incursion':     1000,
        'strike_force':  2000,
        'onslaught':     3000,
    },
}

# Aliases so callers can use any of the known slugs
_ALIASES = {
    'aos':              'aos4',
    'age_of_sigmar':    'aos4',
    'age-of-sigmar':    'aos4',
    '40k':              'w40k10',
    'wh40k':            'w40k10',
    'warhammer-40000':  'w40k10',
    'warhammer_40000':  'w40k10',
}

# Default fallback when system is unknown
_DEFAULT = 'aos4'


def formats_for_system(system_code: str) -> dict:
    """Return {format_slug: points_limit} for the given system code/slug."""
    key = _ALIASES.get(system_code, system_code)
    return SYSTEM_FORMATS.get(key, SYSTEM_FORMATS[_DEFAULT])


def default_format(system_code: str) -> str:
    """Return the first (default) format slug for the given system."""
    return next(iter(formats_for_system(system_code)))


def all_formats() -> dict:
    """Flat dict of all format slugs → points across all systems (for legacy compat)."""
    combined = {}
    for fmts in SYSTEM_FORMATS.values():
        combined.update(fmts)
    return combined
