import os
import re
import click
from flask import Flask
from markupsafe import Markup
from .config import get_config
from .extensions import db, migrate, socketio, login_manager, csrf


def _simple_md(text):
    """Minimal markdown-to-HTML: paragraphs, bold, italic, h1-h3.
    No external dependency required."""
    if not text:
        return Markup('')
    import html as _html
    # Escape HTML first
    text = _html.escape(text)
    # Headers (##, ###, #)
    text = re.sub(r'^### (.+)$', r'<h4 class="faction-rules-md-h3">\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$',  r'<h3 class="faction-rules-md-h2">\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^# (.+)$',   r'<h2 class="faction-rules-md-h1">\1</h2>', text, flags=re.MULTILINE)
    # Bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'\*(.+?)\*',   r'<em>\1</em>', text)
    # Paragraphs: split on blank lines
    blocks = re.split(r'\n{2,}', text.strip())
    parts = []
    for block in blocks:
        b = block.strip()
        if not b:
            continue
        if b.startswith('<h'):
            parts.append(b)
        else:
            # turn single newlines into <br> inside paragraph
            b = b.replace('\n', '<br>')
            parts.append(f'<p>{b}</p>')
    return Markup('\n'.join(parts))


def create_app(config_name='dev', test_config=None):
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    app.config.from_object(get_config(config_name))
    app.config.setdefault('WTF_CSRF_HEADERS', ['X-CSRFToken'])

    # Apply test overrides BEFORE db.init_app so the engine uses the right URI
    if test_config is not None:
        app.config.update(test_config)

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Jinja2 filters
    app.jinja_env.filters['simple_md'] = _simple_md

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Sign in to enter the war-host.'

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from .routes.friends import friends_bp
    app.register_blueprint(friends_bp)

    from .routes.rules import rules_bp
    app.register_blueprint(rules_bp)

    from .routes.units import units_bp
    app.register_blueprint(units_bp)

    from .routes.armies import armies_bp
    app.register_blueprint(armies_bp)

    from .routes.matches import matches_bp
    app.register_blueprint(matches_bp)

    from .routes.stats import stats_bp
    app.register_blueprint(stats_bp)

    # Register sockets
    from .sockets import register_sockets
    register_sockets(socketio)

    # Import models so Alembic sees them
    from . import models  # noqa: F401

    # CLI commands
    @app.cli.command('seed-aos')
    def seed_aos_cmd():
        """Seed AoS 4ed game system, Skaven, and Seraphon data."""
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scripts.seed_aos import _do_seed
        from app.extensions import db as _db
        from app.models.game import GameSystem, Faction, Unit
        result = _do_seed(_db, GameSystem, Faction, Unit)
        click.echo(
            f'Seeded AoS. '
            f'Skaven: {result["skaven_full"]} full / {result["skaven_stub"]} stub. '
            f'Seraphon: {result["seraphon_full"]} full / {result["seraphon_stub"]} stub.'
        )

    @app.cli.command('scrape-images')
    @click.option('--faction', default=None, help='Faction slug to scrape')
    @click.option('--all', 'all_factions', is_flag=True, default=False, help='Scrape all factions')
    @click.option('--force', is_flag=True, default=False, help='Re-download existing images')
    @click.option(
        '--source',
        default='all',
        type=click.Choice(['fandom', 'lexicanum', 'all']),
        help='Image source to use (default: all)',
    )
    def scrape_images_cmd(faction, all_factions, force, source):
        """Scrape unit images from community wikis (Fandom + Lexicanum)."""
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from scripts.scrape_wiki_images import scrape
        scraped, skipped, failed = scrape(faction=faction, force=force, source=source)
        click.echo(f'Image scrape complete. Scraped={scraped}, Skipped={skipped}, Failed={failed}')

    @app.cli.command('make-admin')
    @click.argument('username')
    def make_admin_cmd(username):
        """Grant admin privileges to an existing user."""
        from app.models.user import User
        user = User.query.filter_by(username=username).first()
        if not user:
            click.echo(f'Error: user "{username}" not found.', err=True)
            return
        user.is_admin = True
        db.session.commit()
        click.echo(f'User "{username}" is now an admin.')

    return app
