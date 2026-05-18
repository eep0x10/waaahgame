"""
Phase 3 army builder route tests.
"""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.game import GameSystem, Faction, Unit
from app.models.army import Army, Regiment, ArmyUnit


@pytest.fixture(scope='function')
def app_armies():
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
            edition='4th Edition',
            ruleset_label='GHB 2025-26',
        )
        _db.session.add(gs)
        _db.session.flush()

        skaven = Faction(
            game_system_id=gs.id,
            code='skaven',
            slug='skaven',
            name='Skaven',
            grand_alliance='Chaos',
            blurb='Ratmen.',
        )
        seraphon = Faction(
            game_system_id=gs.id,
            code='seraphon',
            slug='seraphon',
            name='Seraphon',
            grand_alliance='Order',
            blurb='Lizards.',
        )
        _db.session.add_all([skaven, seraphon])
        _db.session.flush()

        corruptor = Unit(
            faction_id=skaven.id,
            slug='verminlord-corruptor',
            name='Verminlord Corruptor',
            points_cost=280,
            unit_role='Hero',
            can_be_general=True,
            can_be_reinforced=False,
            model_count=1,
            stats_json={},
            weapons_json=[],
            abilities_json=[],
            keywords_json=['CHAOS','SKAVENTIDE','HERO','DAEMON','MONSTER'],
            companions_json=[{'type':'keyword','value':'ANY_SKAVEN','max':None}],
        )
        stormvermin = Unit(
            faction_id=skaven.id,
            slug='stormvermin',
            name='Stormvermin',
            points_cost=110,
            unit_role='Battleline',
            can_be_general=False,
            can_be_reinforced=True,
            model_count=10,
            stats_json={},
            weapons_json=[],
            abilities_json=[],
            keywords_json=['CHAOS','SKAVENTIDE','VERMINUS','INFANTRY','BATTLELINE'],
            companions_json=[],
        )
        _db.session.add_all([corruptor, stormvermin])

        alice = User(username='alice', email='alice@example.com')
        alice.set_password('password123')
        bob = User(username='bob', email='bob@example.com')
        bob.set_password('password456')
        _db.session.add_all([alice, bob])
        _db.session.commit()

        yield test_app, skaven, seraphon, corruptor, stormvermin, alice, bob
        _db.drop_all()


@pytest.fixture
def client_armies(app_armies):
    app, *_ = app_armies
    return app.test_client()


@pytest.fixture
def client_as_alice(client_armies, app_armies):
    _, skaven, seraphon, corruptor, stormvermin, alice, bob = app_armies
    client_armies.post('/auth/login', data={'identifier': 'alice', 'password': 'password123'})
    return client_armies


# ---------------------------------------------------------------------------
# Index
# ---------------------------------------------------------------------------

def test_armies_index_requires_login(client_armies):
    resp = client_armies.get('/armies/')
    assert resp.status_code in (302, 401)


def test_armies_index_logged_in(client_as_alice):
    resp = client_as_alice.get('/armies/')
    assert resp.status_code == 200
    assert b'My Armies' in resp.data or b'armies' in resp.data.lower()


# ---------------------------------------------------------------------------
# New army
# ---------------------------------------------------------------------------

def test_armies_new_get(client_as_alice):
    resp = client_as_alice.get('/armies/new')
    assert resp.status_code == 200
    assert b'Raise New Army' in resp.data or b'faction' in resp.data.lower()


def test_armies_new_post_creates_army_and_redirects(client_as_alice, app_armies):
    app, skaven, *_ = app_armies
    resp = client_as_alice.post('/armies/new', data={
        'name': 'Test Army',
        'faction_id': skaven.id,
        'battlepack': 'vanguard',
    })
    assert resp.status_code == 302
    assert '/armies/' in resp.headers.get('Location', '')

    with app.app_context():
        army = Army.query.filter_by(name='Test Army').first()
        assert army is not None
        assert army.battlepack == 'vanguard'
        assert army.points_limit == 1000
        regs = Regiment.query.filter_by(army_id=army.id).all()
        assert len(regs) == 1
        assert regs[0].position == 1


# ---------------------------------------------------------------------------
# Show / builder page
# ---------------------------------------------------------------------------

def test_armies_show_page(client_as_alice, app_armies):
    app, skaven, *_ = app_armies
    resp = client_as_alice.post('/armies/new', data={
        'name': 'Show Test',
        'faction_id': skaven.id,
        'battlepack': 'vanguard',
    })
    location = resp.headers.get('Location', '')
    army_id = int(location.rstrip('/').split('/')[-1])
    resp2 = client_as_alice.get(f'/armies/{army_id}')
    assert resp2.status_code == 200
    assert b'Show Test' in resp2.data or b'Regiment' in resp2.data


def test_armies_show_other_user_404(client_as_alice, app_armies):
    app, skaven, seraphon, corruptor, stormvermin, alice, bob = app_armies

    with app.app_context():
        bob_user = User.query.filter_by(username='bob').first()
        army = Army(
            user_id=bob_user.id,
            faction_id=skaven.id,
            name="Bob's Army",
            battlepack='vanguard',
            points_limit=1000,
        )
        _db.session.add(army)
        _db.session.flush()
        reg = Regiment(army_id=army.id, position=1)
        _db.session.add(reg)
        _db.session.commit()
        army_id = army.id

    resp = client_as_alice.get(f'/armies/{army_id}')
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Add unit
# ---------------------------------------------------------------------------

def test_add_unit_to_regiment(client_as_alice, app_armies):
    app, skaven, seraphon, corruptor, stormvermin, alice, bob = app_armies

    resp = client_as_alice.post('/armies/new', data={
        'name': 'Add Unit Test',
        'faction_id': skaven.id,
        'battlepack': 'vanguard',
    })
    location = resp.headers.get('Location', '')
    army_id = int(location.rstrip('/').split('/')[-1])

    with app.app_context():
        reg = Regiment.query.filter_by(army_id=army_id).first()
        reg_id = reg.id

    resp2 = client_as_alice.post(f'/armies/{army_id}/units', data={
        'unit_slug': 'verminlord-corruptor',
        'target': f'reg-{reg_id}',
    })
    assert resp2.status_code in (200, 302)

    with app.app_context():
        aus = ArmyUnit.query.filter_by(army_id=army_id).all()
        assert len(aus) == 1
        assert aus[0].unit.name == 'Verminlord Corruptor'
        assert aus[0].is_leader is True
        assert aus[0].is_general is True


def test_add_unit_htmx_response(client_as_alice, app_armies):
    app, skaven, *_ = app_armies

    resp = client_as_alice.post('/armies/new', data={
        'name': 'HTMX Test',
        'faction_id': skaven.id,
        'battlepack': 'vanguard',
    })
    army_id = int(resp.headers['Location'].rstrip('/').split('/')[-1])

    with app.app_context():
        reg = Regiment.query.filter_by(army_id=army_id).first()
        reg_id = reg.id

    resp2 = client_as_alice.post(
        f'/armies/{army_id}/units',
        data={'unit_slug': 'verminlord-corruptor', 'target': f'reg-{reg_id}'},
        headers={'HX-Request': 'true'},
    )
    assert resp2.status_code == 200
    assert b'army-summary' in resp2.data


# ---------------------------------------------------------------------------
# Delete army
# ---------------------------------------------------------------------------

def test_delete_army(client_as_alice, app_armies):
    app, skaven, *_ = app_armies

    resp = client_as_alice.post('/armies/new', data={
        'name': 'Delete Me',
        'faction_id': skaven.id,
        'battlepack': 'vanguard',
    })
    army_id = int(resp.headers['Location'].rstrip('/').split('/')[-1])

    resp2 = client_as_alice.post(f'/armies/{army_id}/delete')
    assert resp2.status_code == 302

    with app.app_context():
        army = db.session.get(Army, army_id)
        assert army is None


# ---------------------------------------------------------------------------
# Publish / public view
# ---------------------------------------------------------------------------

def test_publish_and_public_view(client_as_alice, app_armies):
    app, skaven, *_ = app_armies

    resp = client_as_alice.post('/armies/new', data={
        'name': 'Public Army',
        'faction_id': skaven.id,
        'battlepack': 'vanguard',
    })
    army_id = int(resp.headers['Location'].rstrip('/').split('/')[-1])

    resp2 = client_as_alice.post(f'/armies/{army_id}/publish')
    assert resp2.status_code == 302

    with app.app_context():
        army = db.session.get(Army, army_id)
        token = army.public_token
        assert token is not None

    pub_resp = client_armies_anon(app).get(f'/armies/p/{token}')
    assert pub_resp.status_code == 200
    assert b'Public Army' in pub_resp.data


def client_armies_anon(app):
    return app.test_client()


# ---------------------------------------------------------------------------
# Remove unit
# ---------------------------------------------------------------------------

def test_remove_unit(client_as_alice, app_armies):
    app, skaven, *_ = app_armies

    resp = client_as_alice.post('/armies/new', data={
        'name': 'Remove Test',
        'faction_id': skaven.id,
        'battlepack': 'vanguard',
    })
    army_id = int(resp.headers['Location'].rstrip('/').split('/')[-1])

    with app.app_context():
        reg = Regiment.query.filter_by(army_id=army_id).first()
        reg_id = reg.id

    client_as_alice.post(f'/armies/{army_id}/units', data={
        'unit_slug': 'verminlord-corruptor',
        'target': f'reg-{reg_id}',
    })

    with app.app_context():
        au = ArmyUnit.query.filter_by(army_id=army_id).first()
        au_id = au.id

    resp2 = client_as_alice.post(f'/armies/{army_id}/units/{au_id}/remove')
    assert resp2.status_code in (200, 302)

    with app.app_context():
        aus = ArmyUnit.query.filter_by(army_id=army_id).all()
        assert len(aus) == 0


# re-import db for get
from app.extensions import db
