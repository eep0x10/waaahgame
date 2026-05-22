#!/bin/sh -e

export FLASK_APP=app:create_app

flask db upgrade

python scripts/seed_aos.py
python scripts/seed_40k.py
python scripts/seed_aos_expansion.py
python scripts/seed_40k_expansion.py
python scripts/seed_aos_wave5.py
python scripts/seed_battlepacks.py
python scripts/seed_rulesets.py
python scripts/seed_aos4_historical.py
python scripts/seed_army_templates.py
python scripts/fix_image_path_prefix.py

exec "$@"
