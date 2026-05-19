"""
Wave 3 AoS expansion tests: Stormcast Eternals, Sylvaneth, Nighthaunt.

Seed count tests use in-memory DB. Validator tests use pure stubs (no DB).
"""

import pytest
from app import create_app
from app.extensions import db as _db
from app.models.game import GameSystem, Faction, Unit
from app.services.validator import validate


# ---------------------------------------------------------------------------
# In-memory DB fixture with expansion seed applied
# ---------------------------------------------------------------------------

@pytest.fixture(scope='function')
def app_seeded():
    test_app = create_app('dev')
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        SERVER_NAME=None,
    )
    with test_app.app_context():
        _db.create_all()

        # Run base seed first (provides aos4 GameSystem + skaven/seraphon)
        from scripts.seed_aos import _do_seed as base_seed
        base_seed(_db, GameSystem, Faction, Unit)

        # Run expansion seed
        from scripts.seed_aos_expansion import _do_seed as expand_seed
        expand_seed(_db, GameSystem, Faction, Unit)

        yield test_app


# ---------------------------------------------------------------------------
# Stub classes (same pattern as test_validator.py)
# ---------------------------------------------------------------------------

class UnitStub:
    def __init__(self, name, pts, role=None, keywords=None, companions=None,
                 can_reinforce=False, uid=None):
        self.id = uid if uid is not None else (hash(name) % 100000)
        self.name = name
        self.points_cost = pts
        self.unit_role = role
        self.keywords_json = keywords or []
        self.companions_json = companions or []
        self.can_be_reinforced = can_reinforce


class ArmyUnitStub:
    def __init__(self, uid, unit, army_id=1, regiment_id=None, is_leader=False,
                 is_general=False, is_reinforced=False, sort_order=0):
        self.id = uid
        self.army_id = army_id
        self.unit_id = unit.id
        self.unit = unit
        self.regiment_id = regiment_id
        self.is_leader = is_leader
        self.is_general = is_general
        self.is_reinforced = is_reinforced
        self.sort_order = sort_order

    @property
    def points(self):
        return self.unit.points_cost * 2 if self.is_reinforced else self.unit.points_cost

    @property
    def slot_kind(self):
        if self.regiment_id is None:
            return 'auxiliary'
        return 'leader' if self.is_leader else 'companion'


class RegimentStub:
    def __init__(self, rid, army_id, position, aus=None):
        self.id = rid
        self.army_id = army_id
        self.position = position
        self.army_units = aus or []

    @property
    def leader(self):
        return next((a for a in self.army_units if a.is_leader), None)


class _GameSystemStub:
    def __init__(self, code='aos4'):
        self.code = code


class _FactionStub:
    def __init__(self, code='aos4'):
        self.game_system = _GameSystemStub(code)


class ArmyStub:
    def __init__(self, army_id, faction_id, battlepack, pts_limit, regiments=None,
                 army_units=None, system_code='aos4'):
        self.id = army_id
        self.faction_id = faction_id
        self.battlepack = battlepack
        self.points_limit = pts_limit
        self.regiments = regiments or []
        self.army_units = army_units or []
        self.faction = _FactionStub(system_code)


def _u(name, pts, role=None, keywords=None, companions=None, can_reinforce=False, uid=None):
    return UnitStub(name, pts, role, keywords, companions, can_reinforce, uid)


def _au(uid, unit, army_id=1, regiment_id=None, is_leader=False, is_general=False,
        is_reinforced=False, sort_order=0):
    return ArmyUnitStub(uid, unit, army_id, regiment_id, is_leader, is_general, is_reinforced, sort_order)


def _regiment(rid, army_id, position, aus=None):
    return RegimentStub(rid, army_id, position, aus)


def _army(army_id, faction_id, battlepack, pts_limit, regiments=None, army_units=None):
    return ArmyStub(army_id, faction_id, battlepack, pts_limit, regiments, army_units)


def _build_vanguard(regiments, aux_units=None):
    all_aus = []
    regs = []
    for reg, reg_aus in regiments:
        for au in reg_aus:
            au.regiment_id = reg.id
        reg.army_units = reg_aus
        regs.append(reg)
        all_aus.extend(reg_aus)
    aux_units = aux_units or []
    all_aus.extend(aux_units)
    return ArmyStub(1, 1, 'vanguard', 1000, regs, all_aus)


# ---------------------------------------------------------------------------
# Unit stub factories for the three factions
# ---------------------------------------------------------------------------

# --- Stormcast Eternals ---

def _lord_imperatant():
    return _u('Lord-Imperatant', 140, 'Hero', uid=201,
              keywords=['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'HERO'],
              companions=[{'type': 'keyword', 'value': 'ANY_STORMCAST_ETERNALS', 'max': None}])


def _vindictors():
    return _u('Vindictors', 130, 'Infantry', uid=202,
              keywords=['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'INFANTRY', 'BATTLELINE'],
              can_reinforce=True)


def _liberators():
    return _u('Liberators', 110, 'Infantry', uid=203,
              keywords=['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'INFANTRY', 'BATTLELINE'],
              can_reinforce=True)


def _yndrasta():
    return _u('Yndrasta, the Celestial Spear', 280, 'Hero', uid=204,
              keywords=['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'UNIQUE', 'HERO', 'MONSTER'],
              companions=[{'type': 'keyword', 'value': 'ANY_STORMCAST_ETERNALS', 'max': None}])


# --- Sylvaneth ---

def _branchwych():
    return _u('Branchwych', 100, 'Hero', uid=301,
              keywords=['ORDER', 'SYLVANETH', 'HERO', 'WIZARD'],
              companions=[{'type': 'keyword', 'value': 'ANY_SYLVANETH', 'max': None}])


def _dryads():
    return _u('Dryads', 110, 'Infantry', uid=302,
              keywords=['ORDER', 'SYLVANETH', 'INFANTRY', 'BATTLELINE'],
              can_reinforce=True)


def _tree_revenants():
    return _u('Tree-Revenants', 120, 'Infantry', uid=303,
              keywords=['ORDER', 'SYLVANETH', 'INFANTRY', 'BATTLELINE'],
              can_reinforce=True)


# --- Nighthaunt ---

def _guardian_of_souls():
    return _u('Guardian of Souls', 150, 'Hero', uid=401,
              keywords=['DEATH', 'NIGHTHAUNT', 'MALIGNANT', 'HERO', 'WIZARD'],
              companions=[{'type': 'keyword', 'value': 'ANY_NIGHTHAUNT', 'max': None}])


def _chainrasps():
    return _u('Chainrasps', 115, 'Infantry', uid=402,
              keywords=['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'INFANTRY', 'BATTLELINE'],
              can_reinforce=True)


def _grimghast_reapers():
    return _u('Grimghast Reapers', 180, 'Infantry', uid=403,
              keywords=['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'INFANTRY'],
              can_reinforce=True)


# Cross-faction stub (Skaven) for illegal companion test
def _stormvermin():
    return _u('Stormvermin', 110, 'Battleline', uid=501,
              keywords=['CHAOS', 'SKAVENTIDE', 'VERMINUS', 'INFANTRY', 'BATTLELINE'],
              can_reinforce=True)


# ---------------------------------------------------------------------------
# 1. Seed creates 3 factions + 36 new units
# ---------------------------------------------------------------------------

def test_seed_faction_count(app_seeded):
    with app_seeded.app_context():
        for slug in ('stormcast-eternals', 'sylvaneth', 'nighthaunt'):
            f = Faction.query.filter_by(slug=slug).first()
            assert f is not None, f'Faction {slug} not found'


def test_seed_unit_count(app_seeded):
    with app_seeded.app_context():
        expansion_slugs = ['stormcast-eternals', 'sylvaneth', 'nighthaunt']
        count = (
            Unit.query.join(Faction)
            .filter(Faction.slug.in_(expansion_slugs))
            .count()
        )
        assert count == 36, f'Expected 36 expansion units, got {count}'


# ---------------------------------------------------------------------------
# 2. Lord-Imperatant has ANY_STORMCAST_ETERNALS companion spec
# ---------------------------------------------------------------------------

def test_lord_imperatant_companion_spec(app_seeded):
    with app_seeded.app_context():
        unit = Unit.query.filter_by(slug='lord-imperatant').first()
        assert unit is not None
        values = [s.get('value') for s in (unit.companions_json or [])]
        assert 'ANY_STORMCAST_ETERNALS' in values


# ---------------------------------------------------------------------------
# 3. Legal Stormcast Vanguard list (1 hero + 2 infantry)
# ---------------------------------------------------------------------------

def test_stormcast_vanguard_legal():
    lord = _lord_imperatant()
    vindictors = _vindictors()
    liberators = _liberators()

    au1 = _au(1, lord, regiment_id=1, is_leader=True, is_general=True)
    au2 = _au(2, vindictors, regiment_id=1)
    au3 = _au(3, liberators, regiment_id=1)

    reg = _regiment(1, 1, 1, [au1, au2, au3])
    army = _build_vanguard([(reg, [au1, au2, au3])])

    result = validate(army)
    assert result.is_legal is True


# ---------------------------------------------------------------------------
# 4. Legal Sylvaneth Vanguard list
# ---------------------------------------------------------------------------

def test_sylvaneth_vanguard_legal():
    branch = _branchwych()
    dryads = _dryads()
    revenants = _tree_revenants()

    au1 = _au(1, branch, regiment_id=1, is_leader=True, is_general=True)
    au2 = _au(2, dryads, regiment_id=1)
    au3 = _au(3, revenants, regiment_id=1)

    reg = _regiment(1, 1, 1, [au1, au2, au3])
    army = _build_vanguard([(reg, [au1, au2, au3])])

    result = validate(army)
    assert result.is_legal is True


# ---------------------------------------------------------------------------
# 5. Legal Nighthaunt Vanguard list
# ---------------------------------------------------------------------------

def test_nighthaunt_vanguard_legal():
    guardian = _guardian_of_souls()
    chains = _chainrasps()
    grimghast = _grimghast_reapers()

    au1 = _au(1, guardian, regiment_id=1, is_leader=True, is_general=True)
    au2 = _au(2, chains, regiment_id=1)
    au3 = _au(3, grimghast, regiment_id=1)

    reg = _regiment(1, 1, 1, [au1, au2, au3])
    army = _build_vanguard([(reg, [au1, au2, au3])])

    result = validate(army)
    assert result.is_legal is True


# ---------------------------------------------------------------------------
# 6. Cross-faction companion blocked: Stormcast hero + Skaven companion
# ---------------------------------------------------------------------------

def test_stormcast_hero_skaven_companion_invalid():
    lord = _lord_imperatant()
    sv = _stormvermin()

    from app.services.companions import is_companion_valid
    valid, reason = is_companion_valid(sv, lord, [sv])
    assert valid is False
    assert reason is not None


# ---------------------------------------------------------------------------
# 7. ANY_NIGHTHAUNT wildcard matches a NIGHTHAUNT-keyworded unit
# ---------------------------------------------------------------------------

def test_any_nighthaunt_wildcard_matches():
    guardian = _guardian_of_souls()
    chains = _chainrasps()

    from app.services.companions import is_companion_valid
    valid, reason = is_companion_valid(chains, guardian, [chains])
    assert valid is True
    assert reason is None
