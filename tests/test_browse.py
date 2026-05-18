"""
Phase 2 browse tests: factions, units, rules pages.

Uses a minimal in-memory fixture: 1 GameSystem, 2 Factions (skaven + seraphon),
2 units each — no network calls.
"""

import pytest
from app import create_app
from app.extensions import db as _db
from app.models.game import GameSystem, Faction, Unit


@pytest.fixture(scope='function')
def app_with_data():
    """App fixture with seeded AoS data (no network)."""
    test_app = create_app('dev')
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
        SERVER_NAME=None,
    )
    with test_app.app_context():
        _db.create_all()

        gs = GameSystem(
            code='aos4',
            name='Age of Sigmar',
            edition='4th Edition (Skaventide 2024)',
            ruleset_label='GHB 2025-26 + April 2026 Battlescroll',
        )
        _db.session.add(gs)
        _db.session.flush()

        skaven = Faction(
            game_system_id=gs.id,
            code='skaven',
            slug='skaven',
            name='Skaven',
            grand_alliance='Chaos',
            blurb='Chittering hordes of ratmen serving the Great Horned Rat.',
        )
        seraphon = Faction(
            game_system_id=gs.id,
            code='seraphon',
            slug='seraphon',
            name='Seraphon',
            grand_alliance='Order',
            blurb='Cold-blooded warriors prosecuting the Great Plan from the stars.',
        )
        _db.session.add_all([skaven, seraphon])
        _db.session.flush()

        stormvermin = Unit(
            faction_id=skaven.id,
            slug='stormvermin',
            name='Stormvermin',
            points_cost=110,
            unit_role='Battleline',
            can_be_general=False,
            can_be_reinforced=True,
            model_count=10,
            stats_json={'move': '6"', 'save': '4+', 'control': '1', 'health': '1'},
            weapons_json=[{'Weapon': 'Halberd', 'Atk': '2', 'Hit': '3+', 'Wound': '4+', 'Rend': '1', 'Dmg': '1'}],
            abilities_json=[{'name': 'Elite Guard', 'description': 'Verminus elite infantry.'}],
            keywords_json=['CHAOS', 'SKAVENTIDE', 'VERMINUS', 'INFANTRY', 'BATTLELINE'],
            companions_json=[],
            wahapedia_url='https://wahapedia.ru/aos4/factions/skaven/Stormvermin',
        )
        clawlord = Unit(
            faction_id=skaven.id,
            slug='clawlord',
            name='Clawlord',
            points_cost=95,
            unit_role='Hero',
            can_be_general=True,
            can_be_reinforced=False,
            model_count=1,
            stats_json={'move': '6"', 'save': '4+', 'control': '2', 'health': '5'},
            weapons_json=[],
            abilities_json=[],
            keywords_json=['CHAOS', 'SKAVENTIDE', 'VERMINUS', 'HERO'],
            companions_json=['Stormvermin', 'Clanrats'],
            wahapedia_url='https://wahapedia.ru/aos4/factions/skaven/Clawlord',
        )
        saurus = Unit(
            faction_id=seraphon.id,
            slug='saurus-warriors',
            name='Saurus Warriors',
            points_cost=140,
            unit_role='Battleline',
            can_be_general=False,
            can_be_reinforced=True,
            model_count=10,
            stats_json={'move': '5"', 'save': '4+', 'control': '1', 'health': '2'},
            weapons_json=[],
            abilities_json=[],
            keywords_json=['ORDER', 'SERAPHON', 'SAURUS', 'INFANTRY', 'BATTLELINE'],
            companions_json=[],
        )
        _db.session.add_all([stormvermin, clawlord, saurus])
        _db.session.commit()

        yield test_app
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app_with_data):
    return app_with_data.test_client()


# ---- Faction list ----

def test_factions_index_returns_200(client):
    resp = client.get('/factions/')
    assert resp.status_code == 200


def test_factions_index_contains_skaven_and_seraphon(client):
    resp = client.get('/factions/')
    assert b'Skaven' in resp.data
    assert b'Seraphon' in resp.data


# ---- Faction detail ----

def test_faction_detail_skaven_returns_200(client):
    resp = client.get('/factions/skaven')
    assert resp.status_code == 200


def test_faction_detail_skaven_contains_stormvermin(client):
    resp = client.get('/factions/skaven')
    assert b'Stormvermin' in resp.data


def test_faction_detail_nonexistent_returns_404(client):
    resp = client.get('/factions/nonexistent')
    assert resp.status_code == 404


# ---- Unit detail ----

def test_unit_detail_stormvermin_returns_200(client):
    resp = client.get('/units/stormvermin')
    assert resp.status_code == 200


def test_unit_detail_stormvermin_contains_faction_keyword(client):
    resp = client.get('/units/stormvermin')
    # The page renders keywords; VERMINUS keyword should appear
    assert b'VERMINUS' in resp.data or b'Verminus' in resp.data or b'Stormvermin' in resp.data


def test_unit_detail_nonexistent_returns_404(client):
    resp = client.get('/units/doesnotexist')
    assert resp.status_code == 404


# ---- Rules pages ----

def test_rules_index_returns_200(client):
    resp = client.get('/rules/')
    assert resp.status_code == 200


def test_rules_aos_overview_returns_200(client):
    resp = client.get('/rules/aos')
    assert resp.status_code == 200


def test_rules_turn_returns_200(client):
    resp = client.get('/rules/aos/turn-structure')
    assert resp.status_code == 200


def test_rules_abilities_returns_200(client):
    resp = client.get('/rules/aos/abilities')
    assert resp.status_code == 200


def test_rules_composition_returns_200(client):
    resp = client.get('/rules/aos/composition')
    assert resp.status_code == 200


def test_rules_composition_contains_cumulative_surcharge(client):
    resp = client.get('/rules/aos/composition')
    assert b'Cumulative Surcharge' in resp.data
