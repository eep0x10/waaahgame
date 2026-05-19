import pytest
from sqlalchemy.pool import StaticPool
from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.game import GameSystem, Faction, Unit
from app.models.army import Army, Regiment, ArmyUnit
from app.models.army_template import ArmyTemplate
from app.services.validator import validate


@pytest.fixture(scope='function')
def app_tmpl():
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
        _db.session.add(alice)
        _db.session.flush()

        faction = Faction(game_system_id=gs.id, code='sk', slug='skaven', name='Skaven',
                          grand_alliance='Chaos', blurb='rats')
        _db.session.add(faction)
        _db.session.flush()

        hero = Unit(faction_id=faction.id, slug='warlock-engineer', name='Warlock Engineer',
                    points_cost=100, unit_role='Hero', keywords_json=['HERO', 'CHAOS'],
                    stats_json={}, weapons_json=[], abilities_json=[],
                    can_be_general=True)
        troop = Unit(faction_id=faction.id, slug='clanrats', name='Clanrats',
                     points_cost=100, unit_role='Battleline', keywords_json=['CHAOS'],
                     stats_json={}, weapons_json=[], abilities_json=[])
        _db.session.add_all([hero, troop])
        _db.session.commit()

        yield test_app, gs, alice, faction, hero, troop
        _db.drop_all()


@pytest.fixture
def client_tmpl(app_tmpl):
    app, *_ = app_tmpl
    return app.test_client()


@pytest.fixture
def as_alice_tmpl(client_tmpl, app_tmpl):
    client_tmpl.post('/auth/login', data={'identifier': 'alice', 'password': 'pw'})
    return client_tmpl


def _make_template(app, gs_id, faction_id, hero_slug, troop_slug):
    with app.app_context():
        tmpl = ArmyTemplate(
            system_id=gs_id,
            faction_id=faction_id,
            slug='skaven-test-starter',
            name='Skaven Test Starter',
            format='vanguard',
            points_target=1000,
            units_json=[{'slug': hero_slug, 'count': 1}, {'slug': troop_slug, 'count': 2}],
            regiments_layout_json=[{
                'position': 1,
                'leader_slug': hero_slug,
                'companion_slugs': [troop_slug, troop_slug],
            }],
            summary='Test starter army.',
        )
        _db.session.add(tmpl)
        _db.session.commit()
        return tmpl.id


def test_seed_creates_templates(app_tmpl):
    app, gs, alice, faction, hero, troop = app_tmpl
    from scripts.seed_army_templates import _do_seed
    with app.app_context():
        result = _do_seed(_db, GameSystem, Faction, Unit, ArmyTemplate)
        n_created, n_updated = result
        assert isinstance(n_created, int)
        assert isinstance(n_updated, int)


def test_templates_list(as_alice_tmpl, app_tmpl):
    app, gs, alice, faction, hero, troop = app_tmpl
    _make_template(app, gs.id, faction.id, hero.slug, troop.slug)

    resp = as_alice_tmpl.get('/armies/templates')
    assert resp.status_code == 200
    html = resp.data.decode()
    assert 'Skaven Test Starter' in html


def test_clone_creates_new_army(as_alice_tmpl, app_tmpl):
    app, gs, alice, faction, hero, troop = app_tmpl
    tmpl_id = _make_template(app, gs.id, faction.id, hero.slug, troop.slug)

    resp = as_alice_tmpl.post(f'/armies/from-template/{tmpl_id}', follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        army = Army.query.filter_by(user_id=alice.id).first()
        assert army is not None
        assert army.name == 'Skaven Test Starter'
        assert len(army.regiments) == 1
        assert len(army.army_units) == 3  # 1 hero + 2 troops


def test_cloned_army_passes_validator(as_alice_tmpl, app_tmpl):
    app, gs, alice, faction, hero, troop = app_tmpl
    tmpl_id = _make_template(app, gs.id, faction.id, hero.slug, troop.slug)
    as_alice_tmpl.post(f'/armies/from-template/{tmpl_id}', follow_redirects=False)

    with app.app_context():
        army = Army.query.filter_by(user_id=alice.id).first()
        assert army is not None
        result = validate(army)
        assert result is not None
