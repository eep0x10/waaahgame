"""
Warhammer 40,000 10th edition validator tests.

All fixtures use in-memory stub objects (no DB writes).
"""
import pytest


# ---------------------------------------------------------------------------
# Stubs (mirroring test_validator.py pattern)
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
        self.regiment_id = None   # 40k = flat list
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _unit(name, pts, keywords=None, slug=None, uid=None):
    return UnitStub(name, pts, keywords, slug, uid)


def _au(uid, unit, is_general=False):
    return ArmyUnitStub(uid, unit, is_general)


def _character(name='Captain', pts=80, uid=None):
    return _unit(name, pts, ['ADEPTUS ASTARTES', 'CHARACTER', 'INFANTRY'],
                 slug=name.lower().replace(' ', '-'), uid=uid)


def _battleline(name='Intercessors', pts=80, uid=None):
    return _unit(name, pts, ['ADEPTUS ASTARTES', 'BATTLELINE', 'INFANTRY'],
                 slug=name.lower().replace(' ', '-'), uid=uid)


def _troop(name='Hellblasters', pts=130, uid=None):
    return _unit(name, pts, ['ADEPTUS ASTARTES', 'INFANTRY'],
                 slug=name.lower().replace(' ', '-'), uid=uid)


def _epic_hero(name='Marneus Calgar', pts=200, uid=None):
    return _unit(name, pts, ['ADEPTUS ASTARTES', 'CHARACTER', 'INFANTRY', 'EPIC_HERO'],
                 slug=name.lower().replace(' ', '-'), uid=uid)


# ---------------------------------------------------------------------------
# Import validator
# ---------------------------------------------------------------------------

from app.services.validator import validate


# ===========================================================================
# TEST 1: Strike Force 2000 with 1 warlord + valid units -> LEGAL
# ===========================================================================

def test_strike_force_valid_legal():
    """
    Warlord (CHARACTER) + 4 battleline squads + 2 troops.
    Total: 80 + 4*80 + 2*130 = 80 + 320 + 260 = 660pts. Under 2000 -> LEGAL.
    """
    captain = _character('Captain', 80, uid=1)
    bl1 = _battleline('Intercessors A', 80, uid=2)
    bl2 = _battleline('Intercessors B', 80, uid=3)
    bl3 = _battleline('Intercessors C', 80, uid=4)
    bl4 = _battleline('Intercessors D', 80, uid=5)
    hb1 = _troop('Hellblasters A', 130, uid=6)
    hb2 = _troop('Hellblasters B', 130, uid=7)

    aus = [
        _au(1, captain, is_general=True),
        _au(2, bl1), _au(3, bl2), _au(4, bl3), _au(5, bl4),
        _au(6, hb1), _au(7, hb2),
    ]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is True
    assert result.points.total == 660
    assert result.points.over_by == 0


# ===========================================================================
# TEST 2: No warlord -> no_general
# ===========================================================================

def test_no_warlord_error():
    captain = _character('Captain', 80, uid=1)
    bl = _battleline('Intercessors', 80, uid=2)

    aus = [_au(1, captain, is_general=False), _au(2, bl, is_general=False)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'no_general' in codes


# ===========================================================================
# TEST 3: Two warlords -> multiple_generals
# ===========================================================================

def test_two_warlords_error():
    cap1 = _character('Captain A', 80, uid=1)
    cap2 = _character('Captain B', 80, uid=2)

    aus = [_au(1, cap1, is_general=True), _au(2, cap2, is_general=True)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'multiple_generals' in codes


# ===========================================================================
# TEST 4: Warlord without CHARACTER keyword -> general_not_character
# ===========================================================================

def test_warlord_not_character_error():
    trooper = _unit('Tactical Marine', 75,
                    keywords=['ADEPTUS ASTARTES', 'INFANTRY', 'BATTLELINE'],
                    slug='tactical-marine', uid=1)
    aus = [_au(1, trooper, is_general=True)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'general_not_character' in codes


# ===========================================================================
# TEST 5: Points over limit -> pts_over_limit
# ===========================================================================

def test_strike_force_over_limit():
    captain = _character('Captain', 80, uid=1)
    # 20 heavy units at 130pts = 2600 + 80 = 2680 > 2000
    troops = [_troop(f'Hellblasters {i}', 130, uid=10 + i) for i in range(20)]

    aus = [_au(1, captain, is_general=True)] + [_au(10 + i, t) for i, t in enumerate(troops)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'pts_over_limit' in codes


# ===========================================================================
# TEST 6: Same non-battleline unit 4 copies -> unit_max_copies
# ===========================================================================

def test_non_battleline_4_copies_illegal():
    captain = _character('Captain', 80, uid=1)
    # 4 copies of same unit slug
    unit = _troop('Hellblasters', 130, uid=50)
    aus = [_au(1, captain, is_general=True)] + [_au(10 + i, unit) for i in range(4)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'unit_max_copies' in codes


# ===========================================================================
# TEST 7: BATTLELINE unit 6 copies -> LEGAL (just at cap)
# ===========================================================================

def test_battleline_6_copies_legal():
    captain = _character('Captain', 80, uid=1)
    unit = _battleline('Tactical Squad', 75, uid=50)
    # 6 copies * 75 = 450 + 80 = 530 < 2000
    aus = [_au(1, captain, is_general=True)] + [_au(10 + i, unit) for i in range(6)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    codes = {i.code for i in result.issues if i.level == 'error'}
    assert 'unit_max_copies' not in {c for c in codes}
    assert result.is_legal is True


# ===========================================================================
# TEST 8: BATTLELINE unit 7 copies -> unit_max_copies
# ===========================================================================

def test_battleline_7_copies_illegal():
    captain = _character('Captain', 80, uid=1)
    unit = _battleline('Tactical Squad', 75, uid=50)
    aus = [_au(1, captain, is_general=True)] + [_au(10 + i, unit) for i in range(7)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'unit_max_copies' in codes


# ===========================================================================
# TEST 9: Combat Patrol 500 with valid micro army -> LEGAL
# ===========================================================================

def test_combat_patrol_valid_legal():
    captain = _character('Captain', 80, uid=1)
    bl = _battleline('Intercessors', 80, uid=2)
    troop = _troop('Eradicators', 95, uid=3)
    # 80 + 80 + 95 = 255 < 500
    aus = [_au(1, captain, is_general=True), _au(2, bl), _au(3, troop)]
    army = ArmyStub('combat_patrol', 500, aus)
    result = validate(army)
    assert result.is_legal is True
    assert result.points.total == 255
    assert result.points.limit == 500


# ===========================================================================
# TEST 10: Incursion 1000 over limit -> pts_over_limit
# ===========================================================================

def test_incursion_over_limit():
    captain = _character('Captain', 80, uid=1)
    # 10 terminators at 170 = 1700 + 80 = 1780 > 1000
    unit = _unit('Terminators', 170,
                 keywords=['ADEPTUS ASTARTES', 'INFANTRY'],
                 slug='terminators', uid=50)
    aus = [_au(1, captain, is_general=True)] + [_au(10 + i, unit) for i in range(10)]
    army = ArmyStub('incursion', 1000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'pts_over_limit' in codes


# ===========================================================================
# TEST 11: EPIC_HERO max 1 each: 2 of same epic hero -> epic_hero_duplicate
# ===========================================================================

def test_epic_hero_duplicate_error():
    captain = _character('Captain', 80, uid=1)
    eh = _epic_hero('Marneus Calgar', 200, uid=10)  # same slug both times
    aus = [
        _au(1, captain, is_general=True),
        _au(2, eh),
        _au(3, eh),  # duplicate EPIC_HERO
    ]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.is_legal is False
    codes = {i.code for i in result.issues}
    assert 'epic_hero_duplicate' in codes


# ===========================================================================
# TEST 12: PointsBreakdown has zero aux_surcharge for 40k
# ===========================================================================

def test_40k_no_aux_surcharge():
    captain = _character('Captain', 80, uid=1)
    aus = [_au(1, captain, is_general=True)]
    army = ArmyStub('strike_force', 2000, aus)
    result = validate(army)
    assert result.points.aux_surcharge == 0
    assert result.aux_command_bonus is False
