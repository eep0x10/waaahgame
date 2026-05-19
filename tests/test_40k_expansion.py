import pytest
from app import create_app
from app.extensions import db as _db
from app.models.game import GameSystem, Faction, Unit
from app.services.validator import validate


# ---------------------------------------------------------------------------
# In-memory DB fixture
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

        from scripts.seed_40k import _do_seed as base_seed
        base_seed(_db, GameSystem, Faction, Unit)

        from scripts.seed_40k_expansion import _do_seed as expand_seed
        expand_seed(_db, GameSystem, Faction, Unit)

        yield test_app


# ---------------------------------------------------------------------------
# Stubs (mirror test_validator_40k.py)
# ---------------------------------------------------------------------------

class UnitStub:
    def __init__(self, name, pts, keywords=None, slug=None, uid=None):
        self.id = uid if uid is not None else (hash(name) % 100000)
        self.name = name
        self.slug = slug or name.lower().replace(' ', '-')
        self.points_cost = pts
        self.unit_role = None
        self.keywords_json = keywords or []
        self.companions_json = []
        self.can_be_reinforced = False


class ArmyUnitStub:
    def __init__(self, uid, unit, is_general=False):
        self.id = uid
        self.army_id = 1
        self.unit_id = unit.id
        self.unit = unit
        self.regiment_id = None
        self.is_leader = False
        self.is_general = is_general
        self.is_reinforced = False
        self.sort_order = uid

    @property
    def points(self):
        return self.unit.points_cost


class GameSystemStub:
    def __init__(self, code):
        self.code = code


class FactionStub:
    def __init__(self, system_code='w40k10'):
        self.game_system = GameSystemStub(system_code)


class ArmyStub:
    def __init__(self, battlepack, pts_limit, army_units=None):
        self.id = 1
        self.faction = FactionStub()
        self.faction_id = 1
        self.battlepack = battlepack
        self.points_limit = pts_limit
        self.regiments = []
        self.army_units = army_units or []


def _u(name, pts, keywords=None, slug=None, uid=None):
    return UnitStub(name, pts, keywords, slug, uid)


def _au(uid, unit, is_general=False):
    return ArmyUnitStub(uid, unit, is_general)


# ---------------------------------------------------------------------------
# 1. Seed creates 3 factions
# ---------------------------------------------------------------------------

def test_expansion_factions_exist(app_seeded):
    with app_seeded.app_context():
        for slug in ('necrons', 'aeldari', 'chaos-space-marines'):
            f = Faction.query.filter_by(slug=slug).first()
            assert f is not None, f'Faction {slug} missing'


# ---------------------------------------------------------------------------
# 2. Seed creates 36 expansion units
# ---------------------------------------------------------------------------

def test_expansion_unit_count(app_seeded):
    with app_seeded.app_context():
        count = (
            Unit.query.join(Faction)
            .filter(Faction.slug.in_(['necrons', 'aeldari', 'chaos-space-marines']))
            .count()
        )
        assert count == 36, f'Expected 36, got {count}'


# ---------------------------------------------------------------------------
# 3. Necron Overlord has CHARACTER keyword
# ---------------------------------------------------------------------------

def test_necron_overlord_has_character(app_seeded):
    with app_seeded.app_context():
        unit = Unit.query.filter_by(slug='necron-overlord').first()
        assert unit is not None
        kws = [k.upper() for k in (unit.keywords_json or [])]
        assert 'CHARACTER' in kws


# ---------------------------------------------------------------------------
# 4. Legal Strike Force with Necrons
# ---------------------------------------------------------------------------

def test_necrons_strike_force_legal():
    overlord = _u('Necron Overlord', 85,
                  ['NECRONS', 'INFANTRY', 'CHARACTER', 'NOBLE'],
                  slug='necron-overlord', uid=1)
    warriors_a = _u('Necron Warriors A', 110,
                    ['NECRONS', 'INFANTRY', 'BATTLELINE', 'CORE'],
                    slug='necron-warriors-a', uid=2)
    warriors_b = _u('Necron Warriors B', 110,
                    ['NECRONS', 'INFANTRY', 'BATTLELINE', 'CORE'],
                    slug='necron-warriors-b', uid=3)
    immortals = _u('Immortals', 80,
                   ['NECRONS', 'INFANTRY', 'BATTLELINE', 'CORE'],
                   slug='immortals', uid=4)
    wraiths = _u('Canoptek Wraiths', 115,
                 ['NECRONS', 'BEAST', 'FLY'],
                 slug='canoptek-wraiths', uid=5)

    # Total: 85 + 110 + 110 + 80 + 115 = 500 < 2000
    aus = [
        _au(1, overlord, is_general=True),
        _au(2, warriors_a),
        _au(3, warriors_b),
        _au(4, immortals),
        _au(5, wraiths),
    ]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is True
    assert result.points.total == 500


# ---------------------------------------------------------------------------
# 5. Legal Strike Force with Aeldari
# ---------------------------------------------------------------------------

def test_aeldari_strike_force_legal():
    farseer = _u('Farseer', 80,
                 ['AELDARI', 'INFANTRY', 'CHARACTER', 'PSYKER'],
                 slug='farseer', uid=10)
    guardians_a = _u('Guardian Defenders A', 90,
                     ['AELDARI', 'INFANTRY', 'BATTLELINE', 'CORE'],
                     slug='guardian-defenders-a', uid=11)
    guardians_b = _u('Guardian Defenders B', 90,
                     ['AELDARI', 'INFANTRY', 'BATTLELINE', 'CORE'],
                     slug='guardian-defenders-b', uid=12)
    dire = _u('Dire Avengers', 85,
              ['AELDARI', 'INFANTRY', 'BATTLELINE', 'CORE'],
              slug='dire-avengers', uid=13)
    wraithknight = _u('Wraithknight', 430,
                      ['AELDARI', 'TITANIC', 'VEHICLE', 'WALKER'],
                      slug='wraithknight', uid=14)

    # Total: 80 + 90 + 90 + 85 + 430 = 775 < 2000
    aus = [
        _au(10, farseer, is_general=True),
        _au(11, guardians_a),
        _au(12, guardians_b),
        _au(13, dire),
        _au(14, wraithknight),
    ]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is True
    assert result.points.total == 775


# ---------------------------------------------------------------------------
# 6. Legal Strike Force with Chaos Space Marines
# ---------------------------------------------------------------------------

def test_csm_strike_force_legal():
    chaos_lord = _u('Chaos Lord', 80,
                    ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'CHARACTER'],
                    slug='chaos-lord', uid=20)
    legionaries_a = _u('Legionaries A', 90,
                       ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'BATTLELINE', 'CORE'],
                       slug='legionaries-a', uid=21)
    legionaries_b = _u('Legionaries B', 90,
                       ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'BATTLELINE', 'CORE'],
                       slug='legionaries-b', uid=22)
    cultists = _u('Chaos Cultists', 50,
                  ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'BATTLELINE'],
                  slug='chaos-cultists', uid=23)
    helbrute = _u('Helbrute', 140,
                  ['CHAOS', 'CHAOS_SPACE_MARINES', 'VEHICLE', 'WALKER'],
                  slug='helbrute', uid=24)

    # Total: 80 + 90 + 90 + 50 + 140 = 450 < 2000
    aus = [
        _au(20, chaos_lord, is_general=True),
        _au(21, legionaries_a),
        _au(22, legionaries_b),
        _au(23, cultists),
        _au(24, helbrute),
    ]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is True
    assert result.points.total == 450


# ---------------------------------------------------------------------------
# 7. Cross-faction warlord: Necron warlord + Aeldari units
#    Validator has no faction homogeneity check -> produces a result (not crash)
# ---------------------------------------------------------------------------

def test_cross_faction_produces_result():
    overlord = _u('Necron Overlord', 85,
                  ['NECRONS', 'INFANTRY', 'CHARACTER'],
                  slug='necron-overlord', uid=30)
    guardians = _u('Guardian Defenders', 90,
                   ['AELDARI', 'INFANTRY', 'BATTLELINE'],
                   slug='guardian-defenders', uid=31)

    aus = [
        _au(30, overlord, is_general=True),
        _au(31, guardians),
    ]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result is not None
    assert result.points.total == 175


# ---------------------------------------------------------------------------
# 8. Idempotent re-seed does not duplicate units
# ---------------------------------------------------------------------------

def test_seed_idempotent(app_seeded):
    with app_seeded.app_context():
        from scripts.seed_40k_expansion import _do_seed as expand_seed
        expand_seed(_db, GameSystem, Faction, Unit)
        count = (
            Unit.query.join(Faction)
            .filter(Faction.slug.in_(['necrons', 'aeldari', 'chaos-space-marines']))
            .count()
        )
        assert count == 36
