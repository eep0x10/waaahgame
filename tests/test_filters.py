import pytest
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db as _db
from app.models.game import GameSystem, Faction, Unit


@pytest.fixture(scope='function')
def app_filters():
    test_app = create_app('dev', test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {
            'connect_args': {'check_same_thread': False},
            'poolclass': StaticPool,
        },
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': None,
    })
    with test_app.app_context():
        _db.create_all()

        gs_aos = GameSystem(code='aos4', name='Age of Sigmar', edition='4th', ruleset_label='GHB2025')
        gs_40k = GameSystem(code='w40k10', name='Warhammer 40,000', edition='10th', ruleset_label='Index 2024')
        _db.session.add_all([gs_aos, gs_40k])
        _db.session.flush()

        f_aos = Faction(game_system_id=gs_aos.id, code='sk', slug='skaven', name='Skaven',
                        grand_alliance='Chaos', blurb='rats')
        f_40k = Faction(game_system_id=gs_40k.id, code='sm', slug='space-marines', name='Space Marines',
                        grand_alliance=None, blurb='ultras')
        _db.session.add_all([f_aos, f_40k])
        _db.session.flush()

        u1 = Unit(faction_id=f_aos.id, slug='clanrats', name='Clanrats', points_cost=100,
                  unit_role='Battleline', keywords_json=['CHAOS'], stats_json={},
                  weapons_json=[], abilities_json=[])
        u2 = Unit(faction_id=f_aos.id, slug='stormvermin', name='Stormvermin', points_cost=150,
                  unit_role='Battleline', keywords_json=['CHAOS'], stats_json={},
                  weapons_json=[], abilities_json=[])
        u3 = Unit(faction_id=f_40k.id, slug='intercessors', name='Intercessors', points_cost=90,
                  unit_role='Infantry', keywords_json=['ADEPTUS ASTARTES'], stats_json={},
                  weapons_json=[], abilities_json=[])
        _db.session.add_all([u1, u2, u3])
        _db.session.commit()

        yield test_app, gs_aos, gs_40k, f_aos, f_40k, u1, u2, u3
        _db.drop_all()


@pytest.fixture
def client_f(app_filters):
    app, *_ = app_filters
    return app.test_client()


def test_factions_filter_by_system(client_f, app_filters):
    app, gs_aos, gs_40k, *_ = app_filters
    resp = client_f.get(f'/factions/?system={gs_aos.code}')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Skaven' in html
    assert 'Space Marines' not in html


def test_units_filter_by_keyword(client_f, app_filters):
    resp = client_f.get('/units/?q=storm')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Stormvermin' in html
    assert 'Clanrats' not in html


def test_units_filter_points_range(client_f, app_filters):
    resp = client_f.get('/units/?pts_min=100&pts_max=100')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Clanrats' in html
    assert 'Stormvermin' not in html
    assert 'Intercessors' not in html
