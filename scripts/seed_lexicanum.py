"""
Upsert Age of Sigmar factions + units from scripts/cache/lexicanum_manifest.json.

Idempotent — safe to re-run. Never overwrites fields that already have data.

GameSystem assumed code: 'aos4' (already in DB).
No new columns are added; fields not present in models are skipped.
"""

import sys
import os
import json
import re
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'cache', 'lexicanum_manifest.json',
)

# Static image base, relative to the app root (where app/static/ lives)
APP_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_IMG_BASE = os.path.join(APP_ROOT, 'app', 'static', 'img', 'aos')

# Fields NOT in the Unit model — skipped with a one-time warning
SKIPPED_FIELDS = set()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Lowercase, replace non-alphanumerics with hyphens, strip edges."""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def find_image_path(faction_slug: str, unit_slug: str):
    """
    Return a relative image_path string ('units/aos/<faction>/<unit>.ext')
    if a local file exists, otherwise None.
    """
    exts = ('jpg', 'jpeg', 'png', 'webp')
    dir_path = os.path.join(STATIC_IMG_BASE, faction_slug)
    for ext in exts:
        candidate = os.path.join(dir_path, f'{unit_slug}.{ext}')
        if os.path.isfile(candidate):
            return f'units/aos/{faction_slug}/{unit_slug}.{ext}'
    return None


def infer_grand_alliance(faction_name: str, manifest_units: list) -> str | None:
    """
    Infer grand_alliance for a faction by majority vote across its member units.
    Returns None if no units have a grand_alliance value.
    """
    tally: dict[str, int] = {}
    for u in manifest_units:
        ga = (u.get('grand_alliance') or '').strip()
        if ga:
            tally[ga] = tally.get(ga, 0) + 1
    if not tally:
        return None
    return max(tally, key=lambda k: tally[k])


# ---------------------------------------------------------------------------
# Main seed logic
# ---------------------------------------------------------------------------

def _do_seed(db, GameSystem, Faction, Unit):
    # -----------------------------------------------------------------------
    # Load manifest
    # -----------------------------------------------------------------------
    if not os.path.exists(MANIFEST_PATH):
        log.error('Manifest not found: %s', MANIFEST_PATH)
        return

    with open(MANIFEST_PATH, 'r', encoding='utf-8') as fh:
        manifest = json.load(fh)

    manifest_factions: dict[str, list] = manifest.get('factions', {})  # name -> [slug, ...]
    manifest_units: dict[str, dict] = manifest.get('units', {})         # slug -> unit_dict

    # -----------------------------------------------------------------------
    # Resolve GameSystem
    # -----------------------------------------------------------------------
    gs = GameSystem.query.filter_by(code='aos4').first()
    if gs is None:
        log.error('GameSystem aos4 not found — run seed_aos.py first.')
        return
    log.info('Using GameSystem: %s (id=%s)', gs.code, gs.id)

    # -----------------------------------------------------------------------
    # Pre-index: for each faction name, collect its member unit dicts
    # -----------------------------------------------------------------------
    faction_member_units: dict[str, list] = {}
    for faction_name, slugs in manifest_factions.items():
        member = [manifest_units[s] for s in slugs if s in manifest_units]
        faction_member_units[faction_name] = member

    # Also build a reverse map: unit_slug -> first faction name (for assigning primary)
    unit_primary_faction: dict[str, str] = {}
    for slug, u in manifest_units.items():
        factions_list = u.get('factions') or []
        if factions_list:
            unit_primary_faction[slug] = factions_list[0]

    # -----------------------------------------------------------------------
    # Upsert factions
    # -----------------------------------------------------------------------
    factions_created = 0
    factions_updated = 0

    # Build a lookup of existing faction rows by slug
    existing_factions_by_slug: dict[str, Faction] = {
        f.slug: f for f in Faction.query.filter_by(game_system_id=gs.id).all()
    }

    # Also keep a name→slug mapping for unit resolution later
    manifest_faction_slug_map: dict[str, str] = {}  # faction name -> slug we're using

    for faction_name, member_slugs in manifest_factions.items():
        fslug = slugify(faction_name)
        manifest_faction_slug_map[faction_name] = fslug

        inferred_ga = infer_grand_alliance(
            faction_name, faction_member_units.get(faction_name, [])
        )

        existing = existing_factions_by_slug.get(fslug)
        if existing is None:
            # CREATE — don't set blurb (no blurb data for factions in manifest)
            new_f = Faction(
                game_system_id=gs.id,
                code=fslug,
                slug=fslug,
                name=faction_name,
                grand_alliance=inferred_ga,
                blurb=None,
            )
            db.session.add(new_f)
            db.session.flush()
            existing_factions_by_slug[fslug] = new_f
            factions_created += 1
            log.info('  [faction] CREATED %s (ga=%s)', fslug, inferred_ga)
        else:
            updated = False
            # Only fill grand_alliance if currently null
            if existing.grand_alliance is None and inferred_ga:
                existing.grand_alliance = inferred_ga
                updated = True
                log.info('  [faction] UPDATED ga for %s -> %s', fslug, inferred_ga)
            # Never touch existing blurb
            if updated:
                factions_updated += 1

    db.session.flush()

    # Refresh lookup after flush (new rows now have real IDs)
    existing_factions_by_slug = {
        f.slug: f for f in Faction.query.filter_by(game_system_id=gs.id).all()
    }

    # -----------------------------------------------------------------------
    # Upsert units
    # -----------------------------------------------------------------------
    units_created = 0
    units_updated = 0
    units_with_image = 0
    units_no_image_file_missing = 0
    units_no_image_no_url = 0
    skipped_no_faction = 0

    # Pre-load all existing unit slugs for this game system
    existing_units_by_slug: dict[str, Unit] = {}
    for u in Unit.query.join(Faction).filter(Faction.game_system_id == gs.id).all():
        existing_units_by_slug[u.slug] = u

    # Also check units in other game systems to avoid slug collision issues
    all_unit_slugs_global: set[str] = {
        u.slug for u in Unit.query.all()
    }

    for unit_slug, udata in manifest_units.items():
        title = udata.get('title') or unit_slug
        blurb = (udata.get('blurb') or '').strip() or None
        thumb_url = (udata.get('thumb_url') or '').strip() or None
        grand_alliance = (udata.get('grand_alliance') or '').strip() or None

        # Determine primary faction
        factions_list = udata.get('factions') or []
        primary_faction_name = factions_list[0] if factions_list else None

        # Resolve faction row
        faction_obj = None
        if primary_faction_name:
            fslug = manifest_faction_slug_map.get(primary_faction_name) or slugify(primary_faction_name)
            faction_obj = existing_factions_by_slug.get(fslug)

        if faction_obj is None:
            # Try to find a faction by the unit's own GA if no faction match
            # Fallback: skip — we can't create a unit without a faction_id
            log.debug('  [unit] SKIP %s — no faction resolved (factions=%s)', unit_slug, factions_list)
            skipped_no_faction += 1
            continue

        # Determine image path
        image_path = find_image_path(faction_obj.slug, unit_slug)

        existing = existing_units_by_slug.get(unit_slug)

        if existing is None:
            # Check global slug collision (unit may already exist under different game system)
            if unit_slug in all_unit_slugs_global:
                log.warning('  [unit] SKIP %s — slug exists in another game system', unit_slug)
                skipped_no_faction += 1
                continue

            # CREATE — only set fields we know; points_cost required by model, default 0
            new_u = Unit(
                faction_id=faction_obj.id,
                slug=unit_slug,
                name=title,
                points_cost=0,          # required column; manifest has no points
                model_count=1,
                stats_json={},
                weapons_json=[],
                abilities_json=[],
                keywords_json=[],
                companions_json=[],
                image_path=image_path,
                image_source_url=thumb_url,
            )
            # Unit has no blurb column — log once
            if blurb and 'Unit.blurb' not in SKIPPED_FIELDS:
                log.info('  skipped: would need new column Unit.blurb (has blurb data)')
                SKIPPED_FIELDS.add('Unit.blurb')

            # lexicanum_url has no column — log once
            if 'Unit.lexicanum_url' not in SKIPPED_FIELDS:
                log.info('  skipped: would need new column Unit.lexicanum_url (url=%s)', udata.get('url'))
                SKIPPED_FIELDS.add('Unit.lexicanum_url')

            db.session.add(new_u)
            db.session.flush()
            existing_units_by_slug[unit_slug] = new_u
            all_unit_slugs_global.add(unit_slug)
            units_created += 1

            if image_path:
                units_with_image += 1
            elif thumb_url:
                units_no_image_file_missing += 1
            else:
                units_no_image_no_url += 1

        else:
            # UPDATE — only fill missing fields
            changed = False

            if not existing.image_path and image_path:
                existing.image_path = image_path
                changed = True

            if not existing.image_source_url and thumb_url:
                existing.image_source_url = thumb_url
                changed = True

            # blurb not on Unit model — skip silently (already logged above)

            if changed:
                units_updated += 1

            # Tally image stats for existing units
            final_img = existing.image_path or image_path
            if final_img:
                units_with_image += 1
            elif thumb_url:
                units_no_image_file_missing += 1
            else:
                units_no_image_no_url += 1

    db.session.commit()
    log.info('commit ok')

    # -----------------------------------------------------------------------
    # Stats
    # -----------------------------------------------------------------------
    total_manifest_units = len(manifest_units)
    total_processed = units_created + units_updated + (total_manifest_units - units_created - units_updated - skipped_no_faction)

    print()
    print('=' * 55)
    print('  seed_lexicanum.py — DONE')
    print('=' * 55)
    print(f'  Factions created : {factions_created}')
    print(f'  Factions updated : {factions_updated}')
    print(f'  Units created    : {units_created}')
    print(f'  Units updated    : {units_updated}')
    print(f'  Units skipped    : {skipped_no_faction}  (no resolvable faction)')
    print(f'  Units with image : {units_with_image}')
    print(f'  Units no image   : {units_no_image_file_missing + units_no_image_no_url}')
    print(f'    - file missing (has thumb_url)  : {units_no_image_file_missing}')
    print(f'    - no url at all                 : {units_no_image_no_url}')
    print('=' * 55)


def main():
    from app import create_app
    from app.extensions import db
    from app.models.game import GameSystem, Faction, Unit

    app = create_app()
    with app.app_context():
        _do_seed(db, GameSystem, Faction, Unit)


if __name__ == '__main__':
    main()
