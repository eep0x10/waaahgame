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
from app.models.match_dice_roll import MatchDiceRoll
from app.models.match_message import MatchMessage


@pytest.fixture(scope='function')
def app_dice():
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

        gs = GameSystem(code='aos4', name='AoS', edition='4th', ruleset_label='GHB2025')
        _db.session.add(gs)
        _db.session.flush()

        alice = User(username='alice', email='alice@example.com')
        alice.set_password('pw')
        bob = User(username='bob', email='bob@example.com')
        bob.set_password('pw')
        carol = User(username='carol', email='carol@example.com')
        carol.set_password('pw')
        _db.session.add_all([alice, bob, carol])
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

        import json as _json
        from datetime import datetime, timezone
        m = Match(
            host_id=alice.id,
            opponent_id=bob.id,
            system_id=gs.id,
            format='vanguard',
            points_limit=1000,
            army_host_id=army_a.id,
            army_opponent_id=army_b.id,
            status='active',
            current_round=1,
            current_phase='hero',
            active_player_id=alice.id,
            started_at=datetime.now(timezone.utc),
            scores_json=_json.dumps({'host': {'vp': 0, 'cp': 1}, 'opponent': {'vp': 0, 'cp': 0}}),
        )
        _db.session.add(m)
        _db.session.commit()

        yield test_app, m.id, alice, bob, carol
        _db.drop_all()


@pytest.fixture
def as_alice(app_dice):
    app, *_ = app_dice
    c = app.test_client()
    c.post('/auth/login', data={'identifier': 'alice', 'password': 'pw'})
    return c


@pytest.fixture
def as_bob(app_dice):
    app, *_ = app_dice
    c = app.test_client()
    c.post('/auth/login', data={'identifier': 'bob', 'password': 'pw'})
    return c


@pytest.fixture
def as_carol(app_dice):
    app, *_ = app_dice
    c = app.test_client()
    c.post('/auth/login', data={'identifier': 'carol', 'password': 'pw'})
    return c


# --- Dice roll tests ---

def test_valid_roll_persists(as_alice, app_dice):
    app, match_id, *_ = app_dice
    resp = as_alice.post(f'/matches/{match_id}/roll', data={'formula': '2d6'})
    assert resp.status_code in (200, 302)
    with app.app_context():
        roll = MatchDiceRoll.query.filter_by(match_id=match_id).first()
        assert roll is not None
        assert roll.formula == '2d6'
        results = json.loads(roll.results_json)
        assert len(results) == 2
        assert all(1 <= r <= 6 for r in results)
        assert roll.total == sum(results)


def test_invalid_formula_400(as_alice, app_dice):
    _, match_id, *_ = app_dice
    resp = as_alice.post(f'/matches/{match_id}/roll', data={'formula': 'notaformula'})
    assert resp.status_code == 400


def test_nonparticipant_roll_403(as_carol, app_dice):
    _, match_id, *_ = app_dice
    resp = as_carol.post(f'/matches/{match_id}/roll', data={'formula': '1d6'})
    assert resp.status_code == 403


# --- Message tests ---

def test_valid_message_persists(as_alice, app_dice):
    app, match_id, *_ = app_dice
    resp = as_alice.post(f'/matches/{match_id}/message', data={'body': 'Waaagh!'})
    assert resp.status_code in (200, 302)
    with app.app_context():
        msg = MatchMessage.query.filter_by(match_id=match_id).first()
        assert msg is not None
        assert msg.body == 'Waaagh!'


def test_nonparticipant_message_403(as_carol, app_dice):
    _, match_id, *_ = app_dice
    resp = as_carol.post(f'/matches/{match_id}/message', data={'body': 'Interloper!'})
    assert resp.status_code == 403


# --- Replay tests ---

def test_replay_only_when_finished(as_alice, app_dice):
    app, match_id, alice, bob, carol = app_dice
    # active match — should 403
    resp = as_alice.get(f'/matches/{match_id}/replay')
    assert resp.status_code == 403


def test_public_replay_accessible_without_auth(app_dice):
    import json as _json
    from datetime import datetime, timezone

    app, _, alice, bob, carol = app_dice
    with app.app_context():
        gs = GameSystem.query.first()
        army_a = Army.query.filter_by(user_id=alice.id).first()
        army_b = Army.query.filter_by(user_id=bob.id).first()
        m = Match(
            host_id=alice.id,
            opponent_id=bob.id,
            system_id=gs.id,
            format='vanguard',
            points_limit=1000,
            army_host_id=army_a.id,
            army_opponent_id=army_b.id,
            status='finished',
            current_round=5,
            current_phase='end',
            active_player_id=alice.id,
            started_at=datetime.now(timezone.utc),
            finished_at=datetime.now(timezone.utc),
            scores_json=_json.dumps({'host': {'vp': 10, 'cp': 2}, 'opponent': {'vp': 8, 'cp': 1}}),
        )
        _db.session.add(m)
        _db.session.commit()
        token = m.public_token

    c = app.test_client()
    resp = c.get(f'/matches/m/{token}/replay')
    assert resp.status_code == 200
    assert b'Replay' in resp.data or b'replay' in resp.data
