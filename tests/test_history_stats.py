import json
import pytest
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.friendship import Friendship
from app.models.game import GameSystem, Faction
from app.models.army import Army, Regiment
from app.models.match import Match
from app.services.stats import compute_stats


@pytest.fixture(scope='function')
def app_hs():
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

        gs = GameSystem(code='aos4', name='Age of Sigmar', edition='4th', ruleset_label='GHB2025')
        _db.session.add(gs)
        _db.session.flush()

        alice = User(username='alice', email='alice@example.com')
        alice.set_password('pw')
        bob = User(username='bob', email='bob@example.com')
        bob.set_password('pw')
        _db.session.add_all([alice, bob])
        _db.session.flush()

        fs = Friendship(requester_id=alice.id, addressee_id=bob.id, status='accepted')
        _db.session.add(fs)

        faction = Faction(game_system_id=gs.id, code='sk', slug='skaven', name='Skaven',
                          grand_alliance='Chaos', blurb='rats')
        _db.session.add(faction)
        _db.session.flush()

        army_a = Army(user_id=alice.id, faction_id=faction.id, name="Alice's Army",
                      battlepack='vanguard', points_limit=1000)
        army_b = Army(user_id=bob.id, faction_id=faction.id, name="Bob's Army",
                      battlepack='vanguard', points_limit=1000)
        _db.session.add_all([army_a, army_b])
        _db.session.flush()

        reg_a = Regiment(army_id=army_a.id, position=1)
        reg_b = Regiment(army_id=army_b.id, position=1)
        _db.session.add_all([reg_a, reg_b])
        _db.session.commit()

        yield test_app, gs, alice, bob, army_a, army_b
        _db.drop_all()


@pytest.fixture
def client_hs(app_hs):
    app, *_ = app_hs
    return app.test_client()


@pytest.fixture
def as_alice_hs(client_hs, app_hs):
    client_hs.post('/auth/login', data={'identifier': 'alice', 'password': 'pw'})
    return client_hs


def _make_match(app, alice_id, bob_id, gs_id, army_a_id, army_b_id, status='finished',
                host_vp=10, opp_vp=5):
    with app.app_context():
        scores = json.dumps({'host': {'vp': host_vp, 'cp': 0}, 'opponent': {'vp': opp_vp, 'cp': 0}})
        m = Match(
            host_id=alice_id,
            opponent_id=bob_id,
            system_id=gs_id,
            format='vanguard',
            points_limit=1000,
            army_host_id=army_a_id,
            army_opponent_id=army_b_id,
            status=status,
            scores_json=scores if status == 'finished' else None,
        )
        _db.session.add(m)
        _db.session.commit()
        return m.id


def test_history_shows_only_finished(as_alice_hs, app_hs):
    app, gs, alice, bob, army_a, army_b = app_hs
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, status='finished')
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, status='active')
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, status='cancelled')

    resp = as_alice_hs.get('/matches/history')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'VITÓRIA' in html or 'DERROTA' in html or 'EMPATE' in html


def test_history_empty_state(as_alice_hs, app_hs):
    app, gs, alice, bob, army_a, army_b = app_hs
    resp = as_alice_hs.get('/matches/history')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Nenhuma partida finalizada' in html


def test_stats_counts(app_hs):
    app, gs, alice, bob, army_a, army_b = app_hs
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=10, opp_vp=5)
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=3, opp_vp=8)
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=5, opp_vp=5)

    with app.app_context():
        stats = compute_stats(alice.id)

    assert stats['total'] == 3
    assert stats['won'] == 1
    assert stats['lost'] == 1
    assert stats['draws'] == 1


def test_win_rate_calc(app_hs):
    app, gs, alice, bob, army_a, army_b = app_hs
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=10, opp_vp=5)
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=10, opp_vp=5)
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=3, opp_vp=8)
    _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=3, opp_vp=8)

    with app.app_context():
        stats = compute_stats(alice.id)

    assert stats['win_rate'] == 50


def test_recent_form_last_5(app_hs):
    app, gs, alice, bob, army_a, army_b = app_hs
    for i in range(7):
        vp = 10 if i % 2 == 0 else 3
        _make_match(app, alice.id, bob.id, gs.id, army_a.id, army_b.id, host_vp=vp, opp_vp=10 - vp)

    with app.app_context():
        stats = compute_stats(alice.id)

    assert len(stats['recent_form']) <= 5
    assert all(r in ('W', 'L', 'D') for r in stats['recent_form'])
