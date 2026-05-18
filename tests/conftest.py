import pytest
from app import create_app
from app.extensions import db as _db
from app.models.user import User


@pytest.fixture(scope='function')
def app():
    test_app = create_app('dev', test_config={
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_ENGINE_OPTIONS': {'connect_args': {'check_same_thread': False}},
        'WTF_CSRF_ENABLED': False,
        'SERVER_NAME': None,
    })
    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def two_users(app):
    alice = User(username='alice', email='alice@example.com')
    alice.set_password('password123')
    bob = User(username='bob', email='bob@example.com')
    bob.set_password('password456')
    _db.session.add_all([alice, bob])
    _db.session.commit()
    return alice, bob


@pytest.fixture(scope='function')
def client_as_alice(client, two_users):
    alice, bob = two_users
    client.post('/auth/login', data={'identifier': 'alice', 'password': 'password123'})
    return client
