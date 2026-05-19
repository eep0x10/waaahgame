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
from app.models.battlepack import Battlepack


@pytest.fixture(scope='function')
def app_bp():
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
def client_bp(app_bp):
    app, *_ = app_bp
    return app.test_client()


@pytest.fixture
def as_alice_bp(client_bp, app_bp):
    client_bp.post('/auth/login', data={'identifier': 'alice', 'password': 'pw'})
    return client_bp


def test_seed_creates_battlepack_rows(app_bp):
    app, gs, *_ = app_bp
    from scripts.seed_battlepacks import _do_seed
    with app.app_context():
        n_created, n_updated = _do_seed(_db, GameSystem, Battlepack)
        assert n_created + n_updated > 0
        assert Battlepack.query.count() > 0


def test_match_can_be_assigned_battlepack(app_bp):
    app, gs, alice, bob, army_a, army_b = app_bp
    with app.app_context():
        bp = Battlepack(
            system_id=gs.id,
            slug='test-mission',
            name='Test Mission',
            format='vanguard',
            summary='A test.',
            primary_objective='Hold the line.',
            secondary_objectives_json=['Score 2 VP.'],
            deployment_text='Deploy within 12".',
            special_rules_text='None.',
        )
        _db.session.add(bp)
        _db.session.flush()

        m = Match(
            host_id=alice.id,
            opponent_id=bob.id,
            system_id=gs.id,
            format='vanguard',
            points_limit=1000,
            army_host_id=army_a.id,
            status='pending',
            battlepack_id=bp.id,
        )
        _db.session.add(m)
        _db.session.commit()
        mid = m.id
        bp_id = bp.id

    with app.app_context():
        m2 = _db.session.get(Match, mid)
        assert m2.battlepack_id == bp_id
        assert m2.battlepack is not None
        assert m2.battlepack.name == 'Test Mission'


def test_match_new_form_lists_battlepacks(as_alice_bp, app_bp):
    app, gs, alice, bob, army_a, army_b = app_bp
    with app.app_context():
        bp = Battlepack(
            system_id=gs.id,
            slug='listed-mission',
            name='Listed Mission',
            format='vanguard',
            summary='x',
            primary_objective='y',
            secondary_objectives_json=[],
            deployment_text='z',
            special_rules_text='w',
        )
        _db.session.add(bp)
        _db.session.commit()

    resp = as_alice_bp.get('/matches/new')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Listed Mission' in html
