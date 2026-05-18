import re
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

_USERNAME_RE = re.compile(r'^[a-zA-Z0-9_]{3,32}$')
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


@auth_bp.route('/register', methods=['GET'])
def register():
    return render_template('auth/register.html')


@auth_bp.route('/register', methods=['POST'])
def register_post():
    username = request.form.get('username', '').strip()
    email = request.form.get('email', '').strip().lower()
    display_name = request.form.get('display_name', '').strip() or None
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')

    errors = {}

    if not _USERNAME_RE.match(username):
        errors['username'] = 'Username must be 3-32 characters: letters, digits, or underscore.'

    if not _EMAIL_RE.match(email):
        errors['email'] = 'Enter a valid email address.'

    if len(password) < 8:
        errors['password'] = 'Password must be at least 8 characters.'

    if password != password_confirm:
        errors['password_confirm'] = 'Passwords do not match.'

    if not errors:
        if User.query.filter_by(username=username).first():
            errors['username'] = 'That username is already taken.'
        if User.query.filter_by(email=email).first():
            errors['email'] = 'That email is already registered.'

    if errors:
        return render_template('auth/register.html', errors=errors,
                               username=username, email=email, display_name=display_name), 200

    user = User(username=username, email=email, display_name=display_name)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    login_user(user)
    flash('Your banner has been forged. Welcome to the host!', 'success')
    return redirect(url_for('main.index'))


@auth_bp.route('/login', methods=['GET'])
def login():
    next_url = request.args.get('next', '')
    return render_template('auth/login.html', next=next_url)


@auth_bp.route('/login', methods=['POST'])
def login_post():
    identifier = request.form.get('identifier', '').strip()
    password = request.form.get('password', '')
    remember = bool(request.form.get('remember'))
    next_url = request.form.get('next', '')

    errors = {}

    if not identifier:
        errors['identifier'] = 'Enter your username or email.'
    if not password:
        errors['password'] = 'Enter your password.'

    user = None
    if not errors:
        if '@' in identifier:
            user = User.query.filter_by(email=identifier.lower()).first()
        else:
            user = User.query.filter_by(username=identifier).first()

        if user is None or not user.check_password(password):
            errors['identifier'] = 'Invalid credentials. Check your username/email and password.'

    if errors:
        return render_template('auth/login.html', errors=errors,
                               identifier=identifier, next=next_url), 200

    login_user(user, remember=remember)
    flash(f'Welcome back, {user.name}.', 'success')

    if next_url and next_url.startswith('/'):
        return redirect(next_url)
    return redirect(url_for('main.index'))


@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('You have left the war-host. Safe travels.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html')
