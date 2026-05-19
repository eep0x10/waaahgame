import pytest
from app.extensions import db
from app.models.user import User


def test_register_valid_user(client, app):
    resp = client.post('/auth/register', data={
        'username': 'warrior1',
        'email': 'warrior1@example.com',
        'password': 'strongpass',
        'password_confirm': 'strongpass',
    }, follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        assert User.query.filter_by(username='warrior1').first() is not None


def test_register_duplicate_username(client, app):
    with app.app_context():
        u = User(username='taken', email='taken@example.com')
        u.set_password('password123')
        db.session.add(u)
        db.session.commit()
    resp = client.post('/auth/register', data={
        'username': 'taken',
        'email': 'new@example.com',
        'password': 'password123',
        'password_confirm': 'password123',
    })
    assert resp.status_code == 200
    assert b'em uso' in resp.data


def test_register_weak_password(client):
    resp = client.post('/auth/register', data={
        'username': 'newuser',
        'email': 'new@example.com',
        'password': 'short',
        'password_confirm': 'short',
    })
    assert resp.status_code == 200
    assert b'8 caracteres' in resp.data


def test_login_correct_creds_by_username(client, app):
    with app.app_context():
        u = User(username='knightly', email='knight@example.com')
        u.set_password('strongpass')
        db.session.add(u)
        db.session.commit()
    resp = client.post('/auth/login', data={
        'identifier': 'knightly',
        'password': 'strongpass',
    }, follow_redirects=False)
    assert resp.status_code == 302


def test_login_with_email(client, app):
    with app.app_context():
        u = User(username='emailuser', email='email@example.com')
        u.set_password('strongpass')
        db.session.add(u)
        db.session.commit()
    resp = client.post('/auth/login', data={
        'identifier': 'email@example.com',
        'password': 'strongpass',
    }, follow_redirects=False)
    assert resp.status_code == 302


def test_login_wrong_password(client, app):
    with app.app_context():
        u = User(username='wrongpass', email='wrong@example.com')
        u.set_password('correctpass')
        db.session.add(u)
        db.session.commit()
    resp = client.post('/auth/login', data={
        'identifier': 'wrongpass',
        'password': 'badpassword',
    })
    assert resp.status_code == 200
    assert b'Credenciais' in resp.data


def test_logout_while_logged_in(client, app):
    with app.app_context():
        u = User(username='logoutuser', email='logout@example.com')
        u.set_password('testpass1')
        db.session.add(u)
        db.session.commit()
    client.post('/auth/login', data={'identifier': 'logoutuser', 'password': 'testpass1'})
    resp = client.post('/auth/logout', follow_redirects=False)
    assert resp.status_code == 302


def test_profile_requires_login(client):
    resp = client.get('/auth/profile', follow_redirects=False)
    assert resp.status_code == 302
    assert '/auth/login' in resp.headers['Location']
