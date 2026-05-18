import json
import pytest
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.friendship import Friendship
from app.models.game import GameSystem
from app.models.army import Army, Regiment
from app.models.match import Match, FORMAT_POINTS


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='function')
def app_matches():
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
        alice.set_password('password123')
        bob = User(username='bob', email='bob@example.com')
        bob.set_password('password456')
        carol = User(username='carol', email='carol@example.com')
        carol.set_password('password789')
        _db.session.add_all([alice, bob, carol])
        _db.session.flush()

        # alice <-> bob are friends
        fs = Friendship(requester_id=alice.id, addressee_id=bob.id, status='accepted')
        _db.session.add(fs)

        from app.models.game import Faction
        faction = Faction(game_system_id=gs.id, code='sk', slug='skaven', name='Skaven',
                          grand_alliance='Chaos', blurb='rats')
        _db.session.add(faction)
        _db.session.flush()

        army_alice = Army(user_id=alice.id, faction_id=faction.id, name="Alice's Army",
                          battlepack='vanguard', points_limit=1000)
        army_bob = Army(user_id=bob.id, faction_id=faction.id, name="Bob's Army",
                        battlepack='vanguard', points_limit=1000)
        _db.session.add_all([army_alice, army_bob])
        _db.session.flush()

        reg_a = Regiment(army_id=army_alice.id, position=1)
        reg_b = Regiment(army_id=army_bob.id, position=1)
        _db.session.add_all([reg_a, reg_b])
        _db.session.commit()

        yield test_app, gs, alice, bob, carol, army_alice, army_bob
        _db.drop_all()


@pytest.fixture
def client_matches(app_matches):
    app, *_ = app_matches
    return app.test_client()


@pytest.fixture
def as_alice(client_matches):
    client_matches.post('/auth/login', data={'identifier': 'alice', 'password': 'password123'})
    return client_matches


@pytest.fixture
def as_bob(app_matches):
    app, *_ = app_matches
    c = app.test_client()
    c.post('/auth/login', data={'identifier': 'bob', 'password': 'password456'})
    return c


@pytest.fixture
def as_carol(app_matches):
    app, *_ = app_matches
    c = app.test_client()
    c.post('/auth/login', data={'identifier': 'carol', 'password': 'password789'})
    return c


def _create_match(app, alice_id, bob_id, gs_id, army_alice_id, status='pending', army_bob_id=None):
    with app.app_context():
        m = Match(
            host_id=alice_id,
            opponent_id=bob_id,
            system_id=gs_id,
            format='vanguard',
            points_limit=1000,
            army_host_id=army_alice_id,
            army_opponent_id=army_bob_id,
            status=status,
        )
        _db.session.add(m)
        _db.session.commit()
        return m.id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_create_requires_accepted_friend(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    resp = as_alice.post('/matches/new', data={
        'opponent_id': carol.id,
        'system_id': gs.id,
        'format': 'vanguard',
        'army_host_id': army_alice.id,
    })
    assert resp.status_code in (302, 400)
    with app.app_context():
        assert Match.query.count() == 0


def test_cannot_invite_self(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    resp = as_alice.post('/matches/new', data={
        'opponent_id': alice.id,
        'system_id': gs.id,
        'format': 'vanguard',
        'army_host_id': army_alice.id,
    })
    assert resp.status_code in (302, 400)
    with app.app_context():
        assert Match.query.count() == 0


def test_cannot_use_others_army(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    resp = as_alice.post('/matches/new', data={
        'opponent_id': bob.id,
        'system_id': gs.id,
        'format': 'vanguard',
        'army_host_id': army_bob.id,
    })
    assert resp.status_code in (302, 403, 400)
    with app.app_context():
        assert Match.query.count() == 0


def test_cannot_create_army_over_points(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    with app.app_context():
        small_army = Army(user_id=alice.id, faction_id=army_alice.faction_id, name='Small',
                          battlepack='vanguard', points_limit=500)
        _db.session.add(small_army)
        _db.session.commit()
        small_id = small_army.id
    resp = as_alice.post('/matches/new', data={
        'opponent_id': bob.id,
        'system_id': gs.id,
        'format': 'battlehost',
        'army_host_id': small_id,
    })
    assert resp.status_code in (302, 400)
    with app.app_context():
        assert Match.query.count() == 0


def test_accept_flips_to_army_select(as_bob, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id)
    resp = as_bob.post(f'/matches/{mid}/accept')
    assert resp.status_code == 302
    with app.app_context():
        m = _db.session.get(Match, mid)
        assert m.status == 'army_select'


def test_decline_flips_to_cancelled(as_bob, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id)
    resp = as_bob.post(f'/matches/{mid}/decline')
    assert resp.status_code == 302
    with app.app_context():
        m = _db.session.get(Match, mid)
        assert m.status == 'cancelled'


def test_opponent_chooses_army(as_bob, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select')
    resp = as_bob.post(f'/matches/{mid}/choose-army', data={'army_opponent_id': army_bob.id})
    assert resp.status_code == 302
    with app.app_context():
        m = _db.session.get(Match, mid)
        assert m.army_opponent_id == army_bob.id


def test_host_starts_match(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select',
                        army_bob_id=army_bob.id)
    resp = as_alice.post(f'/matches/{mid}/start')
    assert resp.status_code == 302
    with app.app_context():
        m = _db.session.get(Match, mid)
        assert m.status == 'active'
        assert m.current_round == 1
        assert m.current_phase == 'hero'
        assert m.active_player_id == alice.id


def test_advance_phase_cycles(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select',
                        army_bob_id=army_bob.id)
    as_alice.post(f'/matches/{mid}/start')
    # advance hero -> move
    as_alice.post(f'/matches/{mid}/advance-phase')
    with app.app_context():
        m = _db.session.get(Match, mid)
        assert m.current_phase == 'move'


def test_advance_after_end_switches_player(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select',
                        army_bob_id=army_bob.id)
    as_alice.post(f'/matches/{mid}/start')
    phases = ['hero', 'move', 'shoot', 'charge', 'combat', 'end']
    for _ in phases:
        as_alice.post(f'/matches/{mid}/advance-phase')
    with app.app_context():
        m = _db.session.get(Match, mid)
        # after end of alice's turn, switches to bob
        assert m.active_player_id == bob.id
        assert m.current_phase == 'hero'
        assert m.current_round == 1


def test_advance_second_player_end_increments_round(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select',
                        army_bob_id=army_bob.id)
    r_start = as_alice.post(f'/matches/{mid}/start')
    assert r_start.status_code == 302, f'start failed: {r_start.status_code} {r_start.data[:200]}'
    # alice does full turn (hero->move->shoot->charge->combat->end->switches to bob)
    for _ in range(6):
        as_alice.post(f'/matches/{mid}/advance-phase')
    # host (alice) advances bob's full turn — route allows host to advance any phase
    for i in range(6):
        r = as_alice.post(f'/matches/{mid}/advance-phase')
        assert r.status_code in (200, 302), f'bob turn advance {i+1} failed: {r.status_code} {r.data[:200]}'
    with app.app_context():
        m = _db.session.get(Match, mid)
        assert m.current_round == 2
        assert m.active_player_id == alice.id


def test_score_updates_vp(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select',
                        army_bob_id=army_bob.id)
    as_alice.post(f'/matches/{mid}/start')
    resp = as_alice.post(f'/matches/{mid}/score', data={'vp': 3, 'cp': 0})
    assert resp.status_code in (200, 302)
    with app.app_context():
        m = _db.session.get(Match, mid)
        scores = m.get_scores()
        assert scores['host']['vp'] == 3


def test_finish_sets_status(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select',
                        army_bob_id=army_bob.id)
    as_alice.post(f'/matches/{mid}/start')
    resp = as_alice.post(f'/matches/{mid}/finish')
    assert resp.status_code == 302
    with app.app_context():
        m = _db.session.get(Match, mid)
        assert m.status == 'finished'
        assert m.finished_at is not None


def test_non_participant_gets_403(as_carol, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id, status='army_select',
                        army_bob_id=army_bob.id)
    resp = as_carol.post(f'/matches/{mid}/accept')
    assert resp.status_code in (403, 302)


def test_public_token_route_no_auth(app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    # create match and get its token via direct DB access inside fixture context
    token = None
    mid = _create_match(app, alice.id, bob.id, gs.id, army_alice.id)
    with app.app_context():
        m = _db.session.get(Match, mid)
        token = m.public_token
    assert token is not None
    anon = app.test_client()
    resp = anon.get(f'/matches/m/{token}')
    assert resp.status_code == 200


def test_create_match_success(as_alice, app_matches):
    app, gs, alice, bob, carol, army_alice, army_bob = app_matches
    resp = as_alice.post('/matches/new', data={
        'opponent_id': bob.id,
        'system_id': gs.id,
        'format': 'vanguard',
        'army_host_id': army_alice.id,
    })
    assert resp.status_code == 302
    with app.app_context():
        m = Match.query.first()
        assert m is not None
        assert m.status == 'pending'
        assert m.host_id == alice.id
        assert m.opponent_id == bob.id
