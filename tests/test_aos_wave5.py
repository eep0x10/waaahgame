"""
Wave 5 AoS tests: 10 new factions + Gloomspite Gitz bonus.
Seed count tests use in-memory DB. Validator tests use pure stubs.
"""

import pytest
from app import create_app
from app.extensions import db as _db
from app.models.game import GameSystem, Faction, Unit
from app.services.validator import validate


@pytest.fixture(scope='function')
def app_wave5():
    test_app = create_app('dev')
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        SERVER_NAME=None,
    )
    with test_app.app_context():
        _db.create_all()

        from scripts.seed_aos import _do_seed as base_seed
        base_seed(_db, GameSystem, Faction, Unit)

        from scripts.seed_aos_expansion import _do_seed as expand_seed
        expand_seed(_db, GameSystem, Faction, Unit)

        from scripts.seed_aos_wave5 import _do_seed as wave5_seed
        wave5_seed(_db, GameSystem, Faction, Unit)

        yield test_app


# ---------------------------------------------------------------------------
# Stub helpers (reuse pattern from test_aos_expansion.py)
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


def _build_vanguard(regiments, aux_units=None):
    all_aus = []
    regs = []
    for reg, reg_aus in regiments:
        for au in reg_aus:
            au.regiment_id = reg.id
        reg.army_units = reg_aus
        regs.append(reg)
        all_aus.extend(reg_aus)
    all_aus.extend(aux_units or [])
    return ArmyStub(1, 1, 'vanguard', 1000, regs, all_aus)


# ---------------------------------------------------------------------------
# 1. All 11 wave5 factions seeded
# ---------------------------------------------------------------------------

def test_wave5_factions_present(app_wave5):
    with app_wave5.app_context():
        expected = [
            'cities-of-sigmar', 'daughters-of-khaine', 'kharadron-overlords',
            'lumineth-realm-lords', 'maggotkin-of-nurgle', 'slaves-to-darkness',
            'disciples-of-tzeentch', 'soulblight-gravelords', 'ossiarch-bonereapers',
            'orruk-warclans', 'gloomspite-gitz',
        ]
        for slug in expected:
            f = Faction.query.filter_by(slug=slug).first()
            assert f is not None, f'Faction {slug} not seeded'


# ---------------------------------------------------------------------------
# 2. Total AoS factions >= 15 (5 original + 10 wave5 + bonus = 16)
# ---------------------------------------------------------------------------

def test_wave5_total_faction_count(app_wave5):
    with app_wave5.app_context():
        gs = GameSystem.query.filter_by(code='aos4').first()
        count = Faction.query.filter_by(game_system_id=gs.id).count()
        assert count >= 15, f'Expected >= 15 AoS factions, got {count}'


# ---------------------------------------------------------------------------
# 3. At least 100 new units seeded across wave5 factions
# ---------------------------------------------------------------------------

def test_wave5_unit_count(app_wave5):
    with app_wave5.app_context():
        wave5_slugs = [
            'cities-of-sigmar', 'daughters-of-khaine', 'kharadron-overlords',
            'lumineth-realm-lords', 'maggotkin-of-nurgle', 'slaves-to-darkness',
            'disciples-of-tzeentch', 'soulblight-gravelords', 'ossiarch-bonereapers',
            'orruk-warclans', 'gloomspite-gitz',
        ]
        count = (
            Unit.query.join(Faction)
            .filter(Faction.slug.in_(wave5_slugs))
            .count()
        )
        assert count >= 100, f'Expected >= 100 wave5 units, got {count}'


# ---------------------------------------------------------------------------
# 4. Wildcard entries present in companions module
# ---------------------------------------------------------------------------

def test_wildcard_map_entries():
    from app.services.companions import _FACTION_WILDCARD_MAP
    expected_keys = [
        'ANY_CITIES_OF_SIGMAR', 'ANY_DAUGHTERS_OF_KHAINE', 'ANY_KHARADRON_OVERLORDS',
        'ANY_LUMINETH_REALM_LORDS', 'ANY_MAGGOTKIN_OF_NURGLE', 'ANY_SLAVES_TO_DARKNESS',
        'ANY_DISCIPLES_OF_TZEENTCH', 'ANY_SOULBLIGHT_GRAVELORDS', 'ANY_OSSIARCH_BONEREAPERS',
        'ANY_ORRUK_WARCLANS', 'ANY_GLOOMSPITE_GITZ',
    ]
    for key in expected_keys:
        assert key in _FACTION_WILDCARD_MAP, f'Missing wildcard key: {key}'


# ---------------------------------------------------------------------------
# 5. Hero wildcard correctly matches faction units
# ---------------------------------------------------------------------------

def test_any_nurgle_wildcard_matches():
    lord = _u('Lord of Plagues', 110, 'Hero', uid=600,
              keywords=['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'MORTAL', 'ROTBRINGERS', 'HERO'],
              companions=[{'type': 'keyword', 'value': 'ANY_MAGGOTKIN_OF_NURGLE', 'max': None}])
    blightkings = _u('Putrid Blightkings', 200, 'Infantry', uid=601,
                     keywords=['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'MORTAL', 'ROTBRINGERS', 'INFANTRY', 'BATTLELINE'])

    from app.services.companions import is_companion_valid
    valid, reason = is_companion_valid(blightkings, lord, [blightkings])
    assert valid is True


def test_any_soulblight_wildcard_matches():
    vamp = _u('Vampire Lord', 120, 'Hero', uid=700,
              keywords=['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'HERO', 'WIZARD'],
              companions=[{'type': 'keyword', 'value': 'ANY_SOULBLIGHT_GRAVELORDS', 'max': None}])
    blood_k = _u('Blood Knights', 200, 'Cavalry', uid=701,
                 keywords=['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'CAVALRY'])

    from app.services.companions import is_companion_valid
    valid, reason = is_companion_valid(blood_k, vamp, [blood_k])
    assert valid is True


# ---------------------------------------------------------------------------
# 6. Cross-faction companion rejected
# ---------------------------------------------------------------------------

def test_nurgle_hero_orruk_companion_invalid():
    lord = _u('Lord of Plagues', 110, 'Hero', uid=800,
              keywords=['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'MORTAL', 'ROTBRINGERS', 'HERO'],
              companions=[{'type': 'keyword', 'value': 'ANY_MAGGOTKIN_OF_NURGLE', 'max': None}])
    ardboys = _u('Orruk Ardboys', 120, 'Infantry', uid=801,
                 keywords=['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'INFANTRY', 'BATTLELINE'])

    from app.services.companions import is_companion_valid
    valid, reason = is_companion_valid(ardboys, lord, [ardboys])
    assert valid is False


# ---------------------------------------------------------------------------
# 7. Legal Soulblight Vanguard list
# ---------------------------------------------------------------------------

def test_soulblight_vanguard_legal():
    vamp = _u('Vampire Lord', 120, 'Hero', uid=900,
              keywords=['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'HERO', 'WIZARD'],
              companions=[{'type': 'keyword', 'value': 'ANY_SOULBLIGHT_GRAVELORDS', 'max': None}])
    blood_k = _u('Blood Knights', 200, 'Cavalry', uid=901,
                 keywords=['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'CAVALRY'])
    skeles = _u('Skeleton Warriors', 110, 'Infantry', uid=902,
                keywords=['DEATH', 'SOULBLIGHT_GRAVELORDS', 'DEADWALKER', 'SKELETON', 'INFANTRY', 'BATTLELINE'],
                can_reinforce=True)

    au1 = _au(1, vamp, regiment_id=1, is_leader=True, is_general=True)
    au2 = _au(2, blood_k, regiment_id=1)
    au3 = _au(3, skeles, regiment_id=1)

    reg = _regiment(1, 1, 1, [au1, au2, au3])
    army = _build_vanguard([(reg, [au1, au2, au3])])
    result = validate(army)
    assert result.is_legal is True


# ---------------------------------------------------------------------------
# 8. Legal Orruk Warclans Vanguard list
# ---------------------------------------------------------------------------

def test_orruk_vanguard_legal():
    warchanter = _u('Orruk Warchanter', 110, 'Hero', uid=1000,
                    keywords=['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'HERO', 'PRIEST'],
                    companions=[{'type': 'keyword', 'value': 'ANY_ORRUK_WARCLANS', 'max': None}])
    ardboys = _u('Orruk Ardboys', 120, 'Infantry', uid=1001,
                 keywords=['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'INFANTRY', 'BATTLELINE'],
                 can_reinforce=True)
    brutes = _u('Orruk Brutes', 160, 'Infantry', uid=1002,
                keywords=['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'INFANTRY', 'BATTLELINE'])

    au1 = _au(1, warchanter, regiment_id=1, is_leader=True, is_general=True)
    au2 = _au(2, ardboys, regiment_id=1)
    au3 = _au(3, brutes, regiment_id=1)

    reg = _regiment(1, 1, 1, [au1, au2, au3])
    army = _build_vanguard([(reg, [au1, au2, au3])])
    result = validate(army)
    assert result.is_legal is True


# ---------------------------------------------------------------------------
# 9. Legal Tzeentch Vanguard list
# ---------------------------------------------------------------------------

def test_tzeentch_vanguard_legal():
    magister = _u('Magister', 90, 'Hero', uid=1100,
                  keywords=['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'MORTAL', 'ARCANITE', 'HERO', 'WIZARD'],
                  companions=[{'type': 'keyword', 'value': 'ANY_DISCIPLES_OF_TZEENTCH', 'max': None}])
    horrors = _u('Pink Horrors of Tzeentch', 120, 'Infantry', uid=1101,
                 keywords=['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'DAEMON', 'HORROR', 'INFANTRY', 'BATTLELINE'],
                 can_reinforce=True)
    tzaangors = _u('Tzaangors', 120, 'Infantry', uid=1102,
                   keywords=['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'MORTAL', 'ARCANITE', 'TZAANGOR', 'INFANTRY', 'BATTLELINE'],
                   can_reinforce=True)

    au1 = _au(1, magister, regiment_id=1, is_leader=True, is_general=True)
    au2 = _au(2, horrors, regiment_id=1)
    au3 = _au(3, tzaangors, regiment_id=1)

    reg = _regiment(1, 1, 1, [au1, au2, au3])
    army = _build_vanguard([(reg, [au1, au2, au3])])
    result = validate(army)
    assert result.is_legal is True


# ---------------------------------------------------------------------------
# 10. Per-faction unit spot-checks from DB
# ---------------------------------------------------------------------------

def test_wave5_spot_checks_db(app_wave5):
    with app_wave5.app_context():
        checks = [
            ('cities-of-sigmar', 'freeguild-marshal'),
            ('daughters-of-khaine', 'witch-aelves'),
            ('kharadron-overlords', 'arkanaut-company'),
            ('lumineth-realm-lords', 'vanari-auralan-wardens'),
            ('maggotkin-of-nurgle', 'putrid-blightkings'),
            ('slaves-to-darkness', 'chaos-warriors'),
            ('disciples-of-tzeentch', 'pink-horrors-of-tzeentch'),
            ('soulblight-gravelords', 'blood-knights'),
            ('ossiarch-bonereapers', 'mortek-guard'),
            ('orruk-warclans', 'orruk-ardboys'),
            ('gloomspite-gitz', 'moonclan-grots'),
        ]
        for faction_slug, unit_slug in checks:
            u = (
                Unit.query.join(Faction)
                .filter(Faction.slug == faction_slug, Unit.slug == unit_slug)
                .first()
            )
            assert u is not None, f'Unit {unit_slug} in {faction_slug} not found'
