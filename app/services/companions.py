"""
Companion predicate engine.

is_companion_valid(unit, leader_unit, regiment_units) -> (bool, reason | None)

Supports spec shapes:
  {"type": "keyword", "value": "VERMINUS", "max": null}
  {"type": "name",    "value": "Stormvermin", "max": 1}
  {"type": "any",     "value": null}

Wildcard values: "ANY", "ANY_SKAVEN", "ANY_SERAPHON" (any faction-same unit).
If companions_json is empty -> allow any same-faction unit.
"""


def _unit_keywords(unit):
    kws = unit.keywords_json or []
    return {k.upper() for k in kws}


_FACTION_WILDCARD_MAP = {
    'ANY': None,
    'ANY_FACTION': None,
    'ANY_SKAVEN': 'SKAVENTIDE',
    'ANY_SERAPHON': 'SERAPHON',
    'ANY_ORDER': 'ORDER',
    'ANY_CHAOS': 'CHAOS',
    'ANY_DESTRUCTION': 'DESTRUCTION',
    'ANY_DEATH': 'DEATH',
}


def _matches_spec(unit, spec):
    """Return True if unit satisfies a single companion spec (ignoring max)."""
    kind = (spec.get('type') or '').lower()
    value = spec.get('value') or ''

    if kind == 'any':
        return True

    if kind == 'keyword':
        val_upper = value.upper()
        if val_upper == 'ANY' or val_upper == 'ANY_FACTION':
            return True
        if val_upper in _FACTION_WILDCARD_MAP:
            required_kw = _FACTION_WILDCARD_MAP[val_upper]
            if required_kw is None:
                return True
            return required_kw in _unit_keywords(unit)
        return val_upper in _unit_keywords(unit)

    if kind == 'name':
        return unit.name.lower() == value.lower()

    return False


def count_matching_spec(spec, regiment_units):
    """Count how many units in regiment_units match a spec."""
    return sum(1 for u in regiment_units if _matches_spec(u, spec))


def is_companion_valid(unit, leader_unit, regiment_units):
    """
    Check if unit is a valid companion for leader_unit given existing regiment members.

    regiment_units should include unit itself (for max enforcement against total).
    Returns (True, None) or (False, reason_string).
    """
    specs = leader_unit.companions_json or []

    if not specs:
        return True, None

    if len(specs) == 1 and (specs[0].get('type') or '').lower() == 'any':
        return True, None

    for spec in specs:
        if _matches_spec(unit, spec):
            max_allowed = spec.get('max')
            if max_allowed is not None:
                count = count_matching_spec(spec, regiment_units)
                if count > max_allowed:
                    return False, (
                        f"max {max_allowed} of '{spec.get('value')}' per regiment "
                        f"(already {count})"
                    )
            return True, None

    return False, f"'{unit.name}' is not in the allowed companions list for '{leader_unit.name}'"
