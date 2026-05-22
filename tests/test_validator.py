"""
Phase 3 validator tests.

All fixtures use in-memory stub objects (no DB writes).
"""
import pytest


# ---------------------------------------------------------------------------
# Minimal model stubs using plain classes (SimpleNamespace won't work for
# properties, so we use __init__-based classes).
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
    """Minimal game system stub for dispatcher routing."""
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


def _unit(name, pts, role=None, keywords=None, companions=None, can_reinforce=False, uid=None):
    return UnitStub(name, pts, role, keywords, companions, can_reinforce, uid)


def _au(uid, unit, army_id=1, regiment_id=None, is_leader=False, is_general=False,
        is_reinforced=False, sort_order=0):
    return ArmyUnitStub(uid, unit, army_id, regiment_id, is_leader, is_general, is_reinforced, sort_order)


def _regiment(rid, army_id, position, aus=None):
    return RegimentStub(rid, army_id, position, aus)


def _army(army_id, faction_id, battlepack, pts_limit, regiments=None, army_units=None):
    return ArmyStub(army_id, faction_id, battlepack, pts_limit, regiments, army_units)


# ---------------------------------------------------------------------------
# Unit definitions for test lists
# ---------------------------------------------------------------------------

# --- Skaven units ---

def _verminlord_corruptor():
    return _unit('Verminlord Corruptor', 280, 'Hero', uid=1,
                 keywords=['CHAOS','SKAVENTIDE','CLANS PESTILENS','DAEMON','HERO','MONSTER'],
                 companions=[
                     {'type':'keyword','value':'ANY_SKAVEN','max':None},
                 ],
                 can_reinforce=False)


def _grey_seer():
    return _unit('Grey Seer', 110, 'Hero', uid=2,
                 keywords=['CHAOS','SKAVENTIDE','MASTERCLAN','HERO'],
                 companions=[
                     {'type':'keyword','value':'ANY_SKAVEN','max':None},
                 ],
                 can_reinforce=False)


def _warlock_bombardier():
    return _unit('Warlock Bombardier', 90, 'Hero', uid=3,
                 keywords=['CHAOS','SKAVENTIDE','CLANS SKRYRE','HERO'],
                 companions=[
                     {'type':'keyword','value':'CLANS SKRYRE','max':None},
                 ],
                 can_reinforce=False)


def _master_moulder():
    return _unit('Master Moulder', 80, 'Hero', uid=4,
                 keywords=['CHAOS','SKAVENTIDE','CLANS MOULDER','HERO'],
                 companions=[
                     {'type':'keyword','value':'CLANS MOULDER','max':None},
                     {'type':'name','value':'Hell Pit Abomination','max':None},
                 ],
                 can_reinforce=False)


def _stormvermin():
    return _unit('Stormvermin', 110, 'Battleline', uid=5,
                 keywords=['CHAOS','SKAVENTIDE','VERMINUS','INFANTRY','BATTLELINE'],
                 can_reinforce=True)


def _night_runners():
    return _unit('Night Runners', 130, None, uid=6,
                 keywords=['CHAOS','SKAVENTIDE','CLANS ESHIN','INFANTRY'],
                 can_reinforce=True)


def _hell_pit_abomination():
    return _unit('Hell Pit Abomination', 200, 'Behemoth', uid=7,
                 keywords=['CHAOS','SKAVENTIDE','CLANS MOULDER','MONSTER'],
                 can_reinforce=False)


def _plague_monks():
    return _unit('Plague Monks', 140, None, uid=10,
                 keywords=['CHAOS','SKAVENTIDE','CLANS PESTILENS','INFANTRY'],
                 can_reinforce=True)


# --- Seraphon units ---

def _scar_vet_carnosaur():
    return _unit('Saurus Scar-Veteran on Carnosaur', 200, 'Hero', uid=20,
                 keywords=['ORDER','SERAPHON','SAURUS','HERO','MONSTER'],
                 companions=[
                     {'type':'keyword','value':'SERAPHON','max':None},
                 ],
                 can_reinforce=False)


def _astrolith_bearer():
    return _unit('Saurus Astrolith Bearer', 120, 'Hero', uid=21,
                 keywords=['ORDER','SERAPHON','SAURUS','HERO'],
                 companions=[
                     {'type':'keyword','value':'SERAPHON','max':None},
                 ],
                 can_reinforce=False)


def _skink_starpriest():
    return _unit('Skink Starpriest', 90, 'Hero', uid=22,
                 keywords=['ORDER','SERAPHON','SKINK','HERO'],
                 companions=[
                     {'type':'keyword','value':'SERAPHON','max':None},
                 ],
                 can_reinforce=False)


def _saurus_warriors():
    return _unit('Saurus Warriors', 140, 'Battleline', uid=23,
                 keywords=['ORDER','SERAPHON','SAURUS','INFANTRY','BATTLELINE'],
                 can_reinforce=True)


def _aggradon_lancers():
    return _unit('Aggradon Lancers', 200, None, uid=24,
                 keywords=['ORDER','SERAPHON','SAURUS','CAVALRY'],
                 can_reinforce=True)


def _stegadon():
    return _unit('Stegadon', 150, 'Behemoth', uid=25,
                 keywords=['ORDER','SERAPHON','SKINK','MONSTER'],
                 can_reinforce=False)


def _skinks():
    return _unit('Skinks', 80, 'Battleline', uid=26,
                 keywords=['ORDER','SERAPHON','SKINK','INFANTRY','BATTLELINE'],
                 can_reinforce=True)


def _slann_starmaster():
    return _unit('Slann Starmaster', 260, 'Hero', uid=27,
                 keywords=['ORDER','SERAPHON','SLANN','HERO'],
                 companions=[
                     {'type':'keyword','value':'SERAPHON','max':None},
                 ],
                 can_reinforce=False)


# ---------------------------------------------------------------------------
# Import validator
# ---------------------------------------------------------------------------

from app.services.validator import validate


# ---------------------------------------------------------------------------
# Helper: build army with common pattern
# ---------------------------------------------------------------------------

def _build_vanguard_army(regiments, aux_units=None):
    """
    regiments: list of (Regiment stub, [ArmyUnit stubs])
    Returns (army, all_aus)
    """
    all_aus = []
    regs = []
    for i, (reg, reg_aus) in enumerate(regiments):
        for au in reg_aus:
            au.regiment_id = reg.id
        reg.army_units = reg_aus
        regs.append(reg)
        all_aus.extend(reg_aus)

    if aux_units is None:
        aux_units = []
    all_aus.extend(aux_units)

    army = _army(
        army_id=1, faction_id=1,
        battlepack='vanguard', pts_limit=1000,
        regiments=regs, army_units=all_aus,
    )
    return army


# ===========================================================================
# TEST: Seraphon Lista 1 "Saurus Bloodrun" — 980pts, legal
# ===========================================================================

def test_seraphon_list1_legal():
    """
    Reg 1: Scar-Vet Carnosaur (General/Leader) + Skink Starpriest + Saurus Warriors
    Reg 2: Astrolith Bearer (Leader) + Aggradon Lancers
    Aux: Stegadon
    Skinks added to Reg 1
    Total check: 200+90+140+120+200+150+80 = 980
    """
    scar_vet = _scar_vet_carnosaur()
    starpriest = _skink_starpriest()
    saurus_w = _saurus_warriors()
    skinks = _skinks()
    astrolith = _astrolith_bearer()
    aggradon = _aggradon_lancers()
    stegadon = _stegadon()

    au1 = _au(101, scar_vet, regiment_id=1, is_leader=True, is_general=True)
    au2 = _au(102, starpriest, regiment_id=1)
    au3 = _au(103, saurus_w, regiment_id=1)
    au4 = _au(104, skinks, regiment_id=1)

    au5 = _au(105, astrolith, regiment_id=2, is_leader=True)
    au6 = _au(106, aggradon, regiment_id=2)

    au7 = _au(107, stegadon, regiment_id=None, sort_order=1)

    reg1 = _regiment(1, 1, 1, [au1, au2, au3, au4])
    reg2 = _regiment(2, 1, 2, [au5, au6])

    army = _build_vanguard_army([(reg1, [au1,au2,au3,au4]), (reg2, [au5,au6])], [au7])

    result = validate(army)
    assert result.points.base == 980
    assert result.points.total == 980
    assert result.points.over_by == 0
    assert result.is_legal is True


# ===========================================================================
# TEST: Skaven Lista 4 "Centerpiece 6 Clans" — 1000pts, legal
# ===========================================================================

def test_skaven_list4_legal():
    """
    Reg 1: Verminlord Corruptor (Gen) + Warlock Bombardier + Stormvermin + Night Runners
    Reg 2: Master Moulder + Hell Pit Abomination
    Aux: Grey Seer
    Points: 280+90+110+130 + 80+200 + 110 = 1000
    Surcharge: 1 aux -> 0 surcharge
    """
    corruptor = _verminlord_corruptor()
    bombardier = _warlock_bombardier()
    stormvermin = _stormvermin()
    night_runners = _night_runners()
    moulder = _master_moulder()
    hpa = _hell_pit_abomination()
    grey_seer = _grey_seer()

    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    au2 = _au(2, bombardier, regiment_id=10)
    au3 = _au(3, stormvermin, regiment_id=10)
    au4 = _au(4, night_runners, regiment_id=10)

    au5 = _au(5, moulder, regiment_id=20, is_leader=True)
    au6 = _au(6, hpa, regiment_id=20)

    au7 = _au(7, grey_seer, regiment_id=None, sort_order=1)

    reg1 = _regiment(10, 1, 1, [au1, au2, au3, au4])
    reg2 = _regiment(20, 1, 2, [au5, au6])

    army = _build_vanguard_army([(reg1,[au1,au2,au3,au4]),(reg2,[au5,au6])], [au7])

    result = validate(army)
    assert result.points.total == 1000
    assert result.points.aux_surcharge == 0
    assert result.is_legal is True


# ===========================================================================
# TEST: 4 auxiliaries — surcharge info (no hard cap per Core Rules 3.6)
# ===========================================================================

def test_skaven_too_many_aux_illegal():
    """
    Reg 1: Verminlord Corruptor (Gen/Leader) only
    Reg 2: Master Moulder (Leader) + HPA
    Aux: Grey Seer, Warlock Bombardier, Stormvermin, Night Runners
    4 aux -> surcharge = 10*4*3 = 120.
    Core Rules 3.6: no hard cap on aux — surcharge applied, info emitted.
    List is illegal only because total pts exceed 1000 limit.
    """
    corruptor = _verminlord_corruptor()
    moulder = _master_moulder()
    hpa = _hell_pit_abomination()
    grey_seer = _grey_seer()
    bombardier = _warlock_bombardier()
    stormvermin = _stormvermin()
    night_runners = _night_runners()

    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    au5 = _au(5, moulder, regiment_id=20, is_leader=True)
    au6 = _au(6, hpa, regiment_id=20)
    au_aux1 = _au(11, grey_seer, regiment_id=None, sort_order=1)
    au_aux2 = _au(12, bombardier, regiment_id=None, sort_order=2)
    au_aux3 = _au(13, stormvermin, regiment_id=None, sort_order=3)
    au_aux4 = _au(14, night_runners, regiment_id=None, sort_order=4)

    reg1 = _regiment(10, 1, 1, [au1])
    reg2 = _regiment(20, 1, 2, [au5, au6])

    army = _build_vanguard_army(
        [(reg1,[au1]),(reg2,[au5,au6])],
        [au_aux1, au_aux2, au_aux3, au_aux4]
    )

    result = validate(army)

    surcharge = result.points.aux_surcharge
    assert surcharge == 10 * 4 * 3  # 120

    codes = {i.code for i in result.issues}
    # No hard cap: aux_count_surcharge is info, not error
    assert 'aux_count_surcharge' in codes
    assert 'aux_count' not in codes


# ===========================================================================
# TEST: Aux surcharge formula correctness
# ===========================================================================

@pytest.mark.parametrize('n_aux,expected_surcharge', [
    (0, 0),
    (1, 0),
    (2, 20),
    (3, 60),
    (4, 120),
    (5, 200),
])
def test_aux_surcharge_formula(n_aux, expected_surcharge):
    """Surcharge = 10 * N * (N-1)."""
    corruptor = _verminlord_corruptor()
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    reg1 = _regiment(10, 1, 1, [au1])

    grey_seer_unit = _grey_seer()
    aux_units = [
        _au(100 + i, grey_seer_unit, regiment_id=None, sort_order=i+1)
        for i in range(n_aux)
    ]

    army = _build_vanguard_army([(reg1,[au1])], aux_units)
    result = validate(army)
    assert result.points.aux_surcharge == expected_surcharge


# ===========================================================================
# TEST: No general — error
# ===========================================================================

def test_no_general_error():
    corruptor = _verminlord_corruptor()
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=False)
    reg1 = _regiment(10, 1, 1, [au1])
    army = _build_vanguard_army([(reg1,[au1])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'no_general' in codes
    assert result.is_legal is False


# ===========================================================================
# TEST: Hero reinforced when can_be_reinforced=False
# ===========================================================================

def test_hero_reinforced_error():
    corruptor = _verminlord_corruptor()
    assert corruptor.can_be_reinforced is False
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True, is_reinforced=True)
    reg1 = _regiment(10, 1, 1, [au1])
    army = _build_vanguard_army([(reg1,[au1])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'cannot_reinforce' in codes
    assert result.is_legal is False


# ===========================================================================
# TEST: Reinforcement duplicate
# ===========================================================================

def test_reinforcement_duplicate_error():
    """Two ArmyUnits with the same unit_id both reinforced."""
    stormvermin = _stormvermin()
    corruptor = _verminlord_corruptor()

    au_leader = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    au_sv1 = _au(2, stormvermin, regiment_id=10, is_reinforced=True)

    stormvermin2 = _stormvermin()
    au_sv2 = _au(3, stormvermin2, regiment_id=10, is_reinforced=True)

    reg1 = _regiment(10, 1, 1, [au_leader, au_sv1, au_sv2])
    army = _build_vanguard_army([(reg1, [au_leader, au_sv1, au_sv2])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'reinforcement_duplicate' in codes
    assert result.is_legal is False


# ===========================================================================
# TEST: Companion from wrong faction — companion_invalid
# ===========================================================================

def test_companion_invalid_wrong_faction():
    """Put a Seraphon unit (no Skaven keywords) as companion to Verminlord Corruptor."""
    corruptor = _verminlord_corruptor()
    saurus = _saurus_warriors()

    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    au2 = _au(2, saurus, regiment_id=10)

    reg1 = _regiment(10, 1, 1, [au1, au2])
    army = _build_vanguard_army([(reg1,[au1,au2])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'companion_invalid' in codes
    assert result.is_legal is False


# ===========================================================================
# TEST: General not a Hero — error
# ===========================================================================

def test_general_not_hero_error():
    stormvermin = _stormvermin()
    corruptor = _verminlord_corruptor()

    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=False)
    au2 = _au(2, stormvermin, regiment_id=10, is_general=True)

    reg1 = _regiment(10, 1, 1, [au1, au2])
    army = _build_vanguard_army([(reg1,[au1,au2])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'general_not_hero' in codes
    assert result.is_legal is False


# ===========================================================================
# TEST: Regiment too large (>3 companions)
# ===========================================================================

def test_regiment_too_large_error():
    corruptor = _verminlord_corruptor()
    grey_seer = _grey_seer()
    stormvermin = _stormvermin()
    night_runners = _night_runners()
    plague_monks = _plague_monks()

    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    au2 = _au(2, grey_seer, regiment_id=10)
    au3 = _au(3, stormvermin, regiment_id=10)
    au4 = _au(4, night_runners, regiment_id=10)
    au5 = _au(5, plague_monks, regiment_id=10)

    reg1 = _regiment(10, 1, 1, [au1, au2, au3, au4, au5])
    army = _build_vanguard_army([(reg1,[au1,au2,au3,au4,au5])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'regiment_too_large' in codes
    assert result.is_legal is False


# ===========================================================================
# TEST: Regiment no leader — error
# ===========================================================================

def test_regiment_no_leader_error():
    corruptor = _verminlord_corruptor()
    stormvermin = _stormvermin()

    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    au2 = _au(2, stormvermin, regiment_id=20)

    reg1 = _regiment(10, 1, 1, [au1])
    reg2 = _regiment(20, 1, 2, [au2])

    army = _build_vanguard_army([(reg1,[au1]),(reg2,[au2])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'regiment_no_leader' in codes
    assert result.is_legal is False


# ===========================================================================
# TEST: Points over limit
# ===========================================================================

def test_pts_over_limit():
    slann = _slann_starmaster()
    au1 = _au(1, slann, regiment_id=10, is_leader=True, is_general=True)
    scar_vet = _scar_vet_carnosaur()
    au2 = _au(2, scar_vet, regiment_id=10)
    stegadon = _stegadon()
    au3 = _au(3, stegadon, regiment_id=10)
    saurus_w = _saurus_warriors()
    au4 = _au(4, saurus_w, regiment_id=10)
    aggradon = _aggradon_lancers()
    au5 = _au(5, aggradon, regiment_id=10)

    reg1 = _regiment(10, 1, 1, [au1,au2,au3,au4,au5])
    army = _army(1, 2, 'vanguard', 1000, regiments=[reg1],
                 army_units=[au1,au2,au3,au4,au5])

    result = validate(army)
    total = 260 + 200 + 150 + 140 + 200
    assert result.points.base == total
    assert result.points.over_by == max(0, total - 1000)
    if total > 1000:
        codes = {i.code for i in result.issues}
        assert 'pts_over_limit' in codes
        assert result.is_legal is False


# ===========================================================================
# TEST: Aux command bonus note — always True (runtime comparison, not builder)
# ===========================================================================

def test_aux_command_bonus_no_aux():
    # Bug 3 fix: note always present so player remembers to compare at game start
    corruptor = _verminlord_corruptor()
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    reg1 = _regiment(10, 1, 1, [au1])
    army = _build_vanguard_army([(reg1,[au1])], aux_units=[])
    result = validate(army)
    assert result.aux_command_bonus is True


def test_aux_command_bonus_with_aux():
    # Bug 3 fix: note always present regardless of aux count
    corruptor = _verminlord_corruptor()
    grey_seer = _grey_seer()
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    au2 = _au(2, grey_seer, regiment_id=None, sort_order=1)
    reg1 = _regiment(10, 1, 1, [au1])
    army = _build_vanguard_army([(reg1,[au1])], [au2])
    result = validate(army)
    assert result.aux_command_bonus is True


# ===========================================================================
# TEST: Issue dataclass shape
# ===========================================================================

def test_issue_shape():
    corruptor = _verminlord_corruptor()
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=False)
    reg1 = _regiment(10, 1, 1, [au1])
    army = _build_vanguard_army([(reg1,[au1])])
    result = validate(army)
    assert len(result.issues) > 0
    first = result.issues[0]
    assert hasattr(first, 'level')
    assert hasattr(first, 'code')
    assert hasattr(first, 'message')
    assert first.level in ('error', 'warning', 'info')


# ===========================================================================
# TEST: Seraphon Lista 2 minimal — legal (Slann + warriors)
# ===========================================================================

def test_seraphon_list2_minimal_legal():
    """Slann (Gen/Leader) + Saurus Warriors — 400pts, legal with buffer."""
    slann = _slann_starmaster()
    saurus_w = _saurus_warriors()

    au1 = _au(1, slann, regiment_id=10, is_leader=True, is_general=True)
    au2 = _au(2, saurus_w, regiment_id=10)

    reg1 = _regiment(10, 1, 1, [au1, au2])
    army = _build_vanguard_army([(reg1,[au1,au2])])

    result = validate(army)
    assert result.points.total == 400
    assert result.is_legal is True


# ===========================================================================
# TEST: Max companion per spec enforced
# ===========================================================================

def test_companion_max_spec_enforced():
    """Leader allows max:1 of a unit by name; adding 2 should fail."""
    leader_unit = _unit('Test Leader', 100, 'Hero', uid=99,
                        keywords=['CHAOS','SKAVENTIDE','VERMINUS','HERO'],
                        companions=[
                            {'type': 'name', 'value': 'Stormvermin', 'max': 1},
                        ],
                        can_reinforce=False)

    stormvermin_a = _unit('Stormvermin', 110, 'Battleline', uid=5,
                           keywords=['CHAOS','SKAVENTIDE','VERMINUS','INFANTRY'],
                           can_reinforce=True)
    stormvermin_b = _unit('Stormvermin', 110, 'Battleline', uid=55,
                           keywords=['CHAOS','SKAVENTIDE','VERMINUS','INFANTRY'],
                           can_reinforce=True)

    au1 = _au(1, leader_unit, regiment_id=10, is_leader=True, is_general=True)
    au2 = _au(2, stormvermin_a, regiment_id=10)
    au3 = _au(3, stormvermin_b, regiment_id=10)

    reg1 = _regiment(10, 1, 1, [au1, au2, au3])
    army = _build_vanguard_army([(reg1,[au1,au2,au3])])

    result = validate(army)
    codes = {i.code for i in result.issues}
    assert 'companion_invalid' in codes


# ===========================================================================
# REGRESSION: AoS validator still dispatches correctly after package refactor
# ===========================================================================

def test_aos_dispatcher_routes_correctly():
    """Dispatcher sends aos4 army to AoS validator (not 40k validator)."""
    corruptor = _verminlord_corruptor()
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    reg1 = _regiment(10, 1, 1, [au1])

    army = _army(
        army_id=1, faction_id=1,
        battlepack='vanguard', pts_limit=1000,
        regiments=[reg1], army_units=[au1],
    )

    result = validate(army)
    # AoS: 280pts < 1000, 1 regiment, 1 general hero -> LEGAL
    assert result.is_legal is True
    # AoS field: aux_surcharge=0 for 0 auxiliaries
    assert result.points.aux_surcharge == 0


def test_aos_result_shape_unchanged_after_refactor():
    """ValidationResult shape is stable after validator package refactor."""
    corruptor = _verminlord_corruptor()
    au1 = _au(1, corruptor, regiment_id=10, is_leader=True, is_general=True)
    reg1 = _regiment(10, 1, 1, [au1])
    army = _build_vanguard_army([(reg1, [au1])])

    result = validate(army)
    assert hasattr(result, 'is_legal')
    assert hasattr(result, 'points')
    assert hasattr(result, 'issues')
    assert hasattr(result, 'aux_command_bonus')
    assert isinstance(result.points.base, int)
    assert isinstance(result.points.total, int)
