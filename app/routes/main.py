from flask import Blueprint, render_template, jsonify

main_bp = Blueprint('main', __name__)


@main_bp.get('/healthz')
def healthz():
    return jsonify(ok=True), 200


@main_bp.route('/')
def index():
    return render_template('index.html')
