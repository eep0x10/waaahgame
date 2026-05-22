"""Resolve unit data with ruleset overrides applied."""
from app.models.game import Unit, UnitVersion, Ruleset


_OVERRIDABLE = ('points_cost', 'stats_json', 'weapons_json',
                'abilities_json', 'keywords_json', 'companions_json')


def current_ruleset_for_system(game_system):
    """Return is_current ruleset for the system, or None."""
    if game_system is None:
        return None
    return next((r for r in game_system.rulesets if r.is_current), None) or \
           (game_system.rulesets[0] if game_system.rulesets else None)


def unit_view(unit, ruleset=None):
    """Return a UnitProxy with ruleset overrides applied (if any).

    Returns the original Unit instance if ruleset is None or no override exists.
    Otherwise returns a thin wrapper that proxies attribute access, swapping
    overridden fields with the UnitVersion values.
    """
    if ruleset is None:
        return unit
    uv = UnitVersion.query.filter_by(unit_id=unit.id, ruleset_id=ruleset.id).first()
    if uv is None:
        return unit
    return _UnitProxy(unit, uv, ruleset)


class _UnitProxy:
    __slots__ = ('_unit', '_version', '_ruleset', '_overrides')

    def __init__(self, unit, version, ruleset):
        self._unit = unit
        self._version = version
        self._ruleset = ruleset
        overrides = {}
        for f in _OVERRIDABLE:
            v = getattr(version, f)
            if v is not None:
                overrides[f] = v
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._unit, name)

    @property
    def version_notes(self):
        return self._version.notes_json

    @property
    def ruleset(self):
        return self._ruleset
