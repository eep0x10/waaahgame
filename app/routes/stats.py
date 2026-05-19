from flask import Blueprint, render_template
from flask_login import login_required, current_user
from app.services.stats import compute_stats

stats_bp = Blueprint('stats', __name__, url_prefix='/stats')


@stats_bp.route('/')
@login_required
def index():
    data = compute_stats(current_user.id)
    return render_template('stats/index.html', stats=data)
