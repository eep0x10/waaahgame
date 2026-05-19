#!/bin/sh -e

export FLASK_APP=app:create_app

flask db upgrade

python scripts/seed_aos.py
python scripts/seed_40k.py
python scripts/seed_aos_expansion.py
python scripts/seed_40k_expansion.py
python scripts/seed_battlepacks.py
python scripts/seed_army_templates.py

exec "$@"
