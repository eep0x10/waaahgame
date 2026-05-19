import pytest
from app.extensions import db
from app.models.user import User
from app.models.friendship import Friendship


def test_send_request(client_as_alice, app, two_users):
    alice, bob = two_users
    resp = client_as_alice.post('/friends/request', data={'username': 'bob'},
                                follow_redirects=False)
    assert resp.status_code == 302
    with app.app_context():
        fs = Friendship.query.filter_by(requester_id=alice.id, addressee_id=bob.id).first()
        assert fs is not None
        assert fs.status == 'pending'


def test_request_self(client_as_alice, app, two_users):
    resp = client_as_alice.post('/friends/request', data={'username': 'alice'},
                                follow_redirects=True)
    assert b'si mesmo' in resp.data
    with app.app_context():
        assert Friendship.query.count() == 0


def test_request_nonexistent_user(client_as_alice, app, two_users):
    resp = client_as_alice.post('/friends/request', data={'username': 'nobody'},
                                follow_redirects=True)
    assert b'encontrado' in resp.data
    with app.app_context():
        assert Friendship.query.count() == 0


def test_duplicate_request_rejected(client_as_alice, app, two_users):
    alice, bob = two_users
    client_as_alice.post('/friends/request', data={'username': 'bob'})
    resp = client_as_alice.post('/friends/request', data={'username': 'bob'},
                                follow_redirects=True)
    assert b'pendente' in resp.data
    with app.app_context():
        assert Friendship.query.count() == 1


def test_bob_accepts(client_as_alice, app, two_users):
    alice, bob = two_users
    client_as_alice.post('/friends/request', data={'username': 'bob'})

    with app.app_context():
        fs = Friendship.query.first()
        fs_id = fs.id

    client_as_alice.post('/auth/logout')
    client_as_alice.post('/auth/login', data={'identifier': 'bob', 'password': 'password456'})

    resp = client_as_alice.post(f'/friends/{fs_id}/accept', follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        fs = Friendship.query.get(fs_id)
        assert fs.status == 'accepted'


def test_bob_declines(client_as_alice, app, two_users):
    alice, bob = two_users
    client_as_alice.post('/friends/request', data={'username': 'bob'})

    with app.app_context():
        fs = Friendship.query.first()
        fs_id = fs.id

    client_as_alice.post('/auth/logout')
    client_as_alice.post('/auth/login', data={'identifier': 'bob', 'password': 'password456'})

    resp = client_as_alice.post(f'/friends/{fs_id}/decline', follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        assert Friendship.query.get(fs_id) is None


def test_alice_removes_accepted_friend(client_as_alice, app, two_users):
    alice, bob = two_users
    with app.app_context():
        fs = Friendship(requester_id=alice.id, addressee_id=bob.id, status='accepted')
        db.session.add(fs)
        db.session.commit()
        fs_id = fs.id

    resp = client_as_alice.post(f'/friends/{fs_id}/remove', follow_redirects=False)
    assert resp.status_code == 302

    with app.app_context():
        assert Friendship.query.get(fs_id) is None
