"""
Idempotent migration: strip 'img/' prefix from Unit.image_path values.

Convention: image_path in DB must always be 'units/<faction>/<slug>.ext'
            (no leading 'img/'). Templates prepend 'img/' via url_for.

Run:
    python scripts/fix_image_path_prefix.py
    or invoked from docker-entrypoint.sh after seeds.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.extensions import db
from app.models.game import Unit  # noqa: F401 — needed for query


def run():
    app = create_app()
    with app.app_context():
        units = Unit.query.all()
        fixed = 0
        for unit in units:
            if unit.image_path and unit.image_path.startswith('img/'):
                unit.image_path = unit.image_path[4:]  # strip leading 'img/'
                fixed += 1
        if fixed:
            db.session.commit()
        print(f'[fix_image_path_prefix] Fixed {fixed} units (total scanned: {len(units)}).')


if __name__ == '__main__':
    run()
