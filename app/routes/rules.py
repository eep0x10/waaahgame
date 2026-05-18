from flask import Blueprint, render_template

rules_bp = Blueprint('rules', __name__, url_prefix='/rules')


@rules_bp.route('/')
def index():
    return render_template('rules/index.html')


@rules_bp.route('/aos')
def aos_overview():
    return render_template('rules/aos/index.html')


@rules_bp.route('/aos/turn-structure')
def aos_turn():
    return render_template('rules/aos/turn.html')


@rules_bp.route('/aos/abilities')
def aos_abilities():
    return render_template('rules/aos/abilities.html')


@rules_bp.route('/aos/composition')
def aos_composition():
    return render_template('rules/aos/composition.html')
