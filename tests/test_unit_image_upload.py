"""
Tests for admin-gated unit image upload route.
"""

import io
import os
import tempfile
import shutil
import pytest
from PIL import Image as PILImage

from app import create_app
from app.extensions import db as _db
from app.models.user import User
from app.models.game import GameSystem, Faction, Unit


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope='function')
def tmp_static(tmp_path, monkeypatch):
    """
    Redirect STATIC_DIR used by the upload route to a temp folder so we do not
    pollute the real static tree during tests.
    """
    import app.routes.units as units_mod
    original = units_mod.STATIC_DIR
    units_mod.STATIC_DIR = str(tmp_path)
    yield tmp_path
    units_mod.STATIC_DIR = original


@pytest.fixture(scope='function')
def app_with_data(tmp_static):
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
            code='aos4', name='Age of Sigmar',
            edition='4th Edition', ruleset_label='GHB 2025-26',
        )
        _db.session.add(gs)
        _db.session.flush()

        skaven = Faction(
            game_system_id=gs.id, code='skaven', slug='skaven',
            name='Skaven', grand_alliance='Chaos',
        )
        _db.session.add(skaven)
        _db.session.flush()

        unit = Unit(
            faction_id=skaven.id,
            slug='stormvermin',
            name='Stormvermin',
            points_cost=110,
            stats_json={},
            weapons_json=[],
            abilities_json=[],
            keywords_json=[],
            companions_json=[],
        )
        _db.session.add(unit)

        # Normal user
        normal = User(username='normal_user', email='normal@example.com')
        normal.set_password('password123')
        _db.session.add(normal)

        # Admin user
        admin = User(username='admin_user', email='admin@example.com', is_admin=True)
        admin.set_password('adminpass1')
        _db.session.add(admin)

        _db.session.commit()
        yield test_app
        _db.drop_all()


@pytest.fixture(scope='function')
def client(app_with_data):
    return app_with_data.test_client()


def _login(client, username, password):
    client.post('/auth/login', data={'identifier': username, 'password': password})


def _tiny_png_bytes():
    """Create a minimal 300x300 PNG in memory."""
    buf = io.BytesIO()
    img = PILImage.new('RGB', (300, 300), color=(180, 50, 50))
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf.read()


def _tiny_txt_bytes():
    return b'this is not an image'


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_upload_get_anonymous_redirects(client):
    """Unauthenticated user hitting GET /upload-image gets redirect to login."""
    resp = client.get('/units/stormvermin/upload-image')
    assert resp.status_code in (302, 401)


def test_upload_get_non_admin_returns_403(client):
    """Non-admin authenticated user gets 403."""
    _login(client, 'normal_user', 'password123')
    resp = client.get('/units/stormvermin/upload-image')
    assert resp.status_code == 403


def test_upload_get_admin_returns_200(client):
    """Admin user can access the upload form."""
    _login(client, 'admin_user', 'adminpass1')
    resp = client.get('/units/stormvermin/upload-image')
    assert resp.status_code == 200
    assert b'Set Banner Image' in resp.data or b'FORGE BANNER' in resp.data


def test_upload_post_admin_valid_png_sets_image(client, app_with_data, tmp_static):
    """Admin uploading a valid PNG populates unit.image_path and saves file."""
    _login(client, 'admin_user', 'adminpass1')
    data = {
        'image': (io.BytesIO(_tiny_png_bytes()), 'test.png', 'image/png'),
    }
    resp = client.post(
        '/units/stormvermin/upload-image',
        data=data,
        content_type='multipart/form-data',
    )
    # Should redirect to unit detail on success
    assert resp.status_code == 302

    with app_with_data.app_context():
        unit = Unit.query.filter_by(slug='stormvermin').first()
        assert unit.image_path is not None
        dest = os.path.join(str(tmp_static), 'img', unit.image_path)
        assert os.path.exists(dest)


def test_upload_post_admin_txt_rejected(client):
    """Admin uploading a .txt file gets rejected with flash."""
    _login(client, 'admin_user', 'adminpass1')
    data = {
        'image': (io.BytesIO(_tiny_txt_bytes()), 'bad.txt', 'text/plain'),
    }
    resp = client.post(
        '/units/stormvermin/upload-image',
        data=data,
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    # Should return form again (redirect back to upload page) with error flash
    assert resp.status_code == 200
    assert b'Invalid file type' in resp.data or b'Set Banner Image' in resp.data


def test_upload_post_non_admin_returns_403(client):
    """Non-admin POST is rejected with 403."""
    _login(client, 'normal_user', 'password123')
    data = {
        'image': (io.BytesIO(_tiny_png_bytes()), 'test.png', 'image/png'),
    }
    resp = client.post(
        '/units/stormvermin/upload-image',
        data=data,
        content_type='multipart/form-data',
    )
    assert resp.status_code == 403
