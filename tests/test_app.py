import pytest
from app import create_app
from app.extensions import db as _db


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Disable eventlet for testing
    SERVER_NAME = None


@pytest.fixture
def app():
    """Create application with test configuration."""
    test_app = create_app('dev')
    test_app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
        WTF_CSRF_ENABLED=False,
    )

    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def test_index_returns_200(client):
    """Smoke test: GET / should return 200 and contain 'waaahgame'."""
    response = client.get('/')
    assert response.status_code == 200
    assert b'waaahgame' in response.data
