from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import or_, and_
from app.extensions import db
from app.models.user import User
from app.models.friendship import Friendship

friends_bp = Blueprint('friends', __name__, url_prefix='/friends')


def _get_friends_data():
    uid = current_user.id
    accepted = Friendship.query.filter(
        or_(
            and_(Friendship.requester_id == uid, Friendship.status == 'accepted'),
            and_(Friendship.addressee_id == uid, Friendship.status == 'accepted'),
        )
    ).all()
    incoming = Friendship.query.filter_by(addressee_id=uid, status='pending').all()
    outgoing = Friendship.query.filter_by(requester_id=uid, status='pending').all()
    return accepted, incoming, outgoing


@friends_bp.route('/')
@login_required
def index():
    accepted, incoming, outgoing = _get_friends_data()
    return render_template('friends/index.html',
                           accepted=accepted,
                           incoming=incoming,
                           outgoing=outgoing)


@friends_bp.route('/request', methods=['POST'])
@login_required
def send_request():
    username = request.form.get('username', '').strip()

    if username == current_user.username:
        flash('You cannot dispatch an envoy to yourself.', 'error')
        return redirect(url_for('friends.index'))

    target = User.query.filter_by(username=username).first()
    if not target:
        flash(f'No warrior named "{username}" found in the realm.', 'error')
        return redirect(url_for('friends.index'))

    uid = current_user.id
    tid = target.id
    existing = Friendship.query.filter(
        or_(
            and_(Friendship.requester_id == uid, Friendship.addressee_id == tid),
            and_(Friendship.requester_id == tid, Friendship.addressee_id == uid),
        )
    ).first()

    if existing:
        if existing.status == 'accepted':
            flash(f'You are already war-brothers with {username}.', 'info')
        elif existing.status == 'blocked':
            flash('Cannot send a request at this time.', 'error')
        else:
            flash(f'A pledge to {username} is already pending.', 'info')
        return redirect(url_for('friends.index'))

    friendship = Friendship(requester_id=uid, addressee_id=tid, status='pending')
    db.session.add(friendship)
    db.session.commit()
    flash(f'Envoy dispatched to {username}.', 'success')
    return redirect(url_for('friends.index'))


@friends_bp.route('/<int:friendship_id>/accept', methods=['POST'])
@login_required
def accept(friendship_id):
    fs = Friendship.query.get_or_404(friendship_id)
    if fs.addressee_id != current_user.id or fs.status != 'pending':
        abort(403)
    fs.status = 'accepted'
    db.session.commit()
    if request.headers.get('HX-Request'):
        return render_template('friends/_friend_row.html',
                               friendship=fs,
                               section='accepted')
    flash('War-bond accepted.', 'success')
    return redirect(url_for('friends.index'))


@friends_bp.route('/<int:friendship_id>/decline', methods=['POST'])
@login_required
def decline(friendship_id):
    fs = Friendship.query.get_or_404(friendship_id)
    if fs.addressee_id != current_user.id or fs.status != 'pending':
        abort(403)
    db.session.delete(fs)
    db.session.commit()
    if request.headers.get('HX-Request'):
        return '', 200
    flash('Request declined.', 'info')
    return redirect(url_for('friends.index'))


@friends_bp.route('/<int:friendship_id>/remove', methods=['POST'])
@login_required
def remove(friendship_id):
    fs = Friendship.query.get_or_404(friendship_id)
    uid = current_user.id
    if (fs.requester_id != uid and fs.addressee_id != uid) or fs.status != 'accepted':
        abort(403)
    db.session.delete(fs)
    db.session.commit()
    if request.headers.get('HX-Request'):
        return '', 200
    flash('War-bond dissolved.', 'info')
    return redirect(url_for('friends.index'))


@friends_bp.route('/<int:friendship_id>/block', methods=['POST'])
@login_required
def block(friendship_id):
    fs = Friendship.query.get_or_404(friendship_id)
    uid = current_user.id
    if fs.requester_id != uid and fs.addressee_id != uid:
        abort(403)
    fs.status = 'blocked'
    db.session.commit()
    if request.headers.get('HX-Request'):
        return '', 200
    flash('Warrior has been blocked.', 'info')
    return redirect(url_for('friends.index'))
