from flask import Blueprint, render_template
from app.models.game import Unit

units_bp = Blueprint('units', __name__, url_prefix='/units')


@units_bp.route('/<unit_slug>')
def detail(unit_slug):
    unit = Unit.query.filter_by(slug=unit_slug).first_or_404()
    return render_template('units/detail.html', unit=unit)
