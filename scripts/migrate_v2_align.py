"""
DB + image file migration: v2 alignment
- 3 known renames from audit appendix
- 2 known deletes from audit appendix
- 54 plural→singular slug renames (Section 3)
  + 1 special case: skeleton-warriors → deathrattle-skeleton
- 10 missing Chaos GA units (Section 1, added with best-effort points/data)

Run inside container: python3 /app/scripts/migrate_v2_align.py
"""

import sqlite3
import os
import shutil
from datetime import datetime

DB_PATH = "/app/instance/waaahgame.db"
IMG_BASE = "/app/app/static/img/units"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = OFF")  # safe for renames; re-enable after

log = []

def ts():
    return datetime.utcnow().isoformat()

# ─────────────────────────────────────────────
# 0. PRE-COUNT
# ─────────────────────────────────────────────
pre_count = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
log.append(f"PRE-COUNT: {pre_count} units")

# ─────────────────────────────────────────────
# 1. KNOWN RENAMES (3 from v1 appendix)
# ─────────────────────────────────────────────
known_renames = [
    # (old_slug, new_slug, new_name, faction_subdir)
    ("black-knights",                "barrow-knight",   "Barrow Knight",                 "soulblight-gravelords"),
    ("moonclan-grots",               "stabba",           "Stabba",                        "gloomspite-gitz"),
    ("vampire-lord-on-zombie-dragon","vampire-lord",     "Vampire Lord on Zombie Dragon",  "soulblight-gravelords"),
    # NOTE: vampire-lord already exists as separate unit (id=200, foot version)
    # vampire-lord-on-zombie-dragon should become its own slug → we'll skip if target exists
]

renamed_known = 0
skipped_known = []
for old_slug, new_slug, new_name, faction_dir in known_renames:
    existing_old = conn.execute("SELECT id, image_path FROM units WHERE slug=?", (old_slug,)).fetchone()
    if not existing_old:
        skipped_known.append(f"{old_slug}: not found in DB")
        continue
    existing_new = conn.execute("SELECT id FROM units WHERE slug=?", (new_slug,)).fetchone()
    if existing_new:
        # Target slug already exists — skip to avoid unique constraint violation
        skipped_known.append(f"{old_slug} → {new_slug}: target slug already exists (id={existing_new[0]}), skipping DB rename. Old row left as-is.")
        log.append(f"SKIP rename {old_slug} → {new_slug}: target exists")
        continue

    unit_id = existing_old[0]
    old_img = existing_old[1]

    # Rename DB slug + name + image_path
    new_img = f"units/{faction_dir}/{new_slug}.jpg" if old_img else None
    conn.execute(
        "UPDATE units SET slug=?, name=?, image_path=?, updated_at=? WHERE id=?",
        (new_slug, new_name, new_img, ts(), unit_id)
    )

    # Rename image file if it exists
    if old_img:
        ext = os.path.splitext(old_img)[1] or ".jpg"
        old_file = os.path.join(IMG_BASE, faction_dir, f"{old_slug}{ext}")
        new_file = os.path.join(IMG_BASE, faction_dir, f"{new_slug}{ext}")
        if os.path.exists(old_file) and not os.path.exists(new_file):
            os.rename(old_file, new_file)
            log.append(f"IMG RENAME: {old_file} → {new_file}")
        elif os.path.exists(new_file):
            log.append(f"IMG target exists, keeping: {new_file}")

    renamed_known += 1
    log.append(f"DB RENAME: {old_slug} → {new_slug}")

log.append(f"Known renames done: {renamed_known}, skipped: {len(skipped_known)}")
for s in skipped_known:
    log.append(f"  SKIP: {s}")

# ─────────────────────────────────────────────
# 2. KNOWN DELETES (2 from v1 appendix)
# ─────────────────────────────────────────────
known_deletes = [
    ("freeguild-crossbowmen",  "cities-of-sigmar"),
    ("helblaster-volley-gun",  "cities-of-sigmar"),
]

deleted_known = 0
for slug, faction_dir in known_deletes:
    row = conn.execute("SELECT id, image_path FROM units WHERE slug=?", (slug,)).fetchone()
    if not row:
        log.append(f"DELETE SKIP: {slug} not found")
        continue
    unit_id, img_path = row

    # Delete DB row (cascade: army_units rows referencing this unit will be orphaned; acceptable)
    conn.execute("DELETE FROM units WHERE id=?", (unit_id,))
    log.append(f"DB DELETE: {slug} (id={unit_id})")

    # Delete image file
    if img_path:
        ext = os.path.splitext(img_path)[1] or ".jpg"
        img_file = os.path.join(IMG_BASE, faction_dir, f"{slug}{ext}")
        if os.path.exists(img_file):
            os.remove(img_file)
            log.append(f"IMG DELETE: {img_file}")

    deleted_known += 1

log.append(f"Known deletes done: {deleted_known}")

# ─────────────────────────────────────────────
# 3. PLURAL → SINGULAR RENAMES (54 + 1 special)
# ─────────────────────────────────────────────
# Format: (faction_subdir, old_slug, new_slug, new_name)
plural_renames = [
    ("seraphon",               "aggradon-lancers",         "aggradon-lancer",           "Aggradon Lancer"),
    ("stormcast-eternals",     "annihilators",              "annihilator",               "Annihilator"),
    ("maggotkin-of-nurgle",    "beasts-of-nurgle",          "beast-of-nurgle",           "Beast of Nurgle"),
    ("nighthaunt",             "bladegheist-revenants",     "bladegheist-revenant",      "Bladegheist Revenant"),
    ("soulblight-gravelords",  "blood-knights",             "blood-knight",              "Blood Knight"),
    ("daughters-of-khaine",    "blood-sisters",             "blood-sister",              "Blood Sister"),
    ("daughters-of-khaine",    "blood-stalkers",            "blood-stalker",             "Blood Stalker"),
    ("nighthaunt",             "chainrasps",                "chainrasp",                 "Chainrasp"),
    ("slaves-to-darkness",     "chaos-knights",             "chaos-knight",              "Chaos Knight"),
    ("slaves-to-darkness",     "chaos-warriors",            "chaos-warrior",             "Chaos Warrior"),
    ("skaven",                 "clanrats",                  "clanrat",                   "Clanrat"),
    ("soulblight-gravelords",  "dire-wolves",               "dire-wolf",                 "Dire Wolf"),
    ("daughters-of-khaine",    "doomfire-warlocks",         "doomfire-warlock",          "Doomfire Warlock"),
    ("sylvaneth",              "dryads",                    "dryad",                     "Dryad"),
    ("gloomspite-gitz",        "fellwater-troggoths",       "fellwater-troggoth",        "Fellwater Troggoth"),
    ("disciples-of-tzeentch",  "flamers-of-tzeentch",       "flamer-of-tzeentch",        "Flamer of Tzeentch"),
    ("cities-of-sigmar",       "freeguild-cavaliers",       "freeguild-cavalier",        "Freeguild Cavalier"),
    ("cities-of-sigmar",       "freeguild-steelhelms",      "freeguild-steelhelm",       "Freeguild Steelhelm"),
    ("nighthaunt",             "glaivewraith-stalkers",     "glaivewraith-stalker",      "Glaivewraith Stalker"),
    ("nighthaunt",             "grimghast-reapers",         "grimghast-reaper",          "Grimghast Reaper"),
    ("skaven",                 "gutter-runners",            "gutter-runner",             "Gutter Runner"),
    ("nighthaunt",             "hexwraiths",                "hexwraith",                 "Hexwraith"),
    ("cities-of-sigmar",       "irondrakes",                "irondrake",                 "Irondrake"),
    ("disciples-of-tzeentch",  "kairic-acolytes",           "kairic-acolyte",            "Kairic Acolyte"),
    ("ossiarch-bonereapers",   "kavalos-deathriders",       "kavalos-deathrider",        "Kavalos Deathrider"),
    ("daughters-of-khaine",    "khinerai-lifetakers",       "khinerai-lifetaker",        "Khinerai Lifetaker"),
    ("stormcast-eternals",     "liberators",                "liberator",                 "Liberator"),
    ("ossiarch-bonereapers",   "necropolis-stalkers",       "necropolis-stalker",        "Necropolis Stalker"),
    ("skaven",                 "night-runners",             "night-runner",              "Night Runner"),
    ("maggotkin-of-nurgle",    "nurglings",                 "nurgling",                  "Nurgling"),
    ("orruk-warclans",         "orruk-weirdnob-shaman",     "weirdnob-shaman",           "Weirdnob Shaman"),
    ("disciples-of-tzeentch",  "pink-horrors-of-tzeentch",  "pink-horror-of-tzeentch",   "Pink Horror of Tzeentch"),
    ("skaven",                 "plague-censer-bearers",     "plague-censer-bearer",      "Plague Censer Bearer"),
    ("skaven",                 "plague-monks",              "plague-monk",               "Plague Monk"),
    ("stormcast-eternals",     "praetors",                  "praetor",                   "Praetor"),
    ("maggotkin-of-nurgle",    "putrid-blightkings",        "putrid-blightking",         "Putrid Blightking"),
    ("skaven",                 "rat-ogors",                 "rat-ogor",                  "Rat Ogor"),
    ("gloomspite-gitz",        "rockgut-troggoths",         "rockgut-troggoth",          "Rockgut Troggoth"),
    ("seraphon",               "saurus-warriors",           "saurus-warrior",            "Saurus Warrior"),
    ("orruk-warclans",         "savage-orruk-morboys",      "savage-orruk-morboy",       "Savage Orruk Morboy"),
    ("disciples-of-tzeentch",  "screamers-of-tzeentch",     "screamer-of-tzeentch",      "Screamer of Tzeentch"),
    ("daughters-of-khaine",    "sisters-of-slaughter",      "sister-of-slaughter",       "Sister of Slaughter"),
    # Special: skeleton-warriors → deathrattle-skeleton (name change too)
    ("soulblight-gravelords",  "skeleton-warriors",         "deathrattle-skeleton",      "Deathrattle Skeleton"),
    ("seraphon",               "skinks",                    "skink",                     "Skink"),
    ("kharadron-overlords",    "skywardens",                "skywarden",                 "Skywarden"),
    ("nighthaunt",             "spirit-hosts",              "spirit-host",               "Spirit Host"),
    ("sylvaneth",              "spite-revenants",           "spite-revenant",            "Spite-Revenant"),
    ("gloomspite-gitz",        "squig-hoppers",             "squig-hopper",              "Squig Hopper"),
    ("skaven",                 "stormfiends",               "stormfiend",                "Stormfiend"),
    ("sylvaneth",              "tree-revenants",            "tree-revenant",             "Tree-Revenant"),
    ("disciples-of-tzeentch",  "tzaangors",                 "tzaangor",                  "Tzaangor"),
    ("soulblight-gravelords",  "vargheists",                "vargheist",                 "Vargheist"),
    ("stormcast-eternals",     "vindictors",                "vindictor",                 "Vindictor"),
    ("skaven",                 "warplock-jezzails",         "warplock-jezzail",          "Warplock Jezzail"),
    ("daughters-of-khaine",    "witch-aelves",              "witch-aelf",                "Witch Aelf"),
]

renamed_plural = 0
skipped_plural = []
img_missing_after = []

for faction_dir, old_slug, new_slug, new_name in plural_renames:
    row = conn.execute("SELECT id, image_path FROM units WHERE slug=?", (old_slug,)).fetchone()
    if not row:
        skipped_plural.append(f"{old_slug}: not in DB")
        continue
    unit_id, old_img = row

    existing_new = conn.execute("SELECT id FROM units WHERE slug=?", (new_slug,)).fetchone()
    if existing_new:
        skipped_plural.append(f"{old_slug} → {new_slug}: target exists (id={existing_new[0]})")
        continue

    # Determine image extension
    img_ext = ".jpg"
    if old_img:
        img_ext = os.path.splitext(old_img)[1] or ".jpg"

    new_img = f"units/{faction_dir}/{new_slug}{img_ext}"

    conn.execute(
        "UPDATE units SET slug=?, name=?, image_path=?, updated_at=? WHERE id=?",
        (new_slug, new_name, new_img, ts(), unit_id)
    )

    # Rename image file
    old_file = os.path.join(IMG_BASE, faction_dir, f"{old_slug}{img_ext}")
    new_file = os.path.join(IMG_BASE, faction_dir, f"{new_slug}{img_ext}")
    if os.path.exists(old_file):
        if not os.path.exists(new_file):
            os.rename(old_file, new_file)
            log.append(f"IMG RENAME: {old_slug}{img_ext} → {new_slug}{img_ext} [{faction_dir}]")
        else:
            log.append(f"IMG target exists already: {new_file}")
    else:
        img_missing_after.append(f"{faction_dir}/{new_slug}{img_ext}")
        log.append(f"IMG NOT FOUND: {old_file}")

    renamed_plural += 1

log.append(f"Plural renames done: {renamed_plural}, skipped: {len(skipped_plural)}")
for s in skipped_plural:
    log.append(f"  SKIP: {s}")

# ─────────────────────────────────────────────
# 4. ADD 10 MISSING CHAOS UNITS
# ─────────────────────────────────────────────
# Faction IDs from DB:
#   disciples-of-tzeentch = 17
#   maggotkin-of-nurgle   = 15
#   slaves-to-darkness    = 16
#   nighthaunt            = 7
#   gloomspite-gitz       = 21
#   hedonites-of-slaanesh = 32

# Points are AoS4 GHB 2025-26 canonical where known, else 0 (TODO placeholder)
# beastrider: Beastclaw Raiders → no faction in DB → use destruction closest: ogor-mawtribes (56)?
#   Lex says "Beastclaw Raiders" which maps to ogor-mawtribes. Use faction_id=56.
# burning-chariot: disciples-of-tzeentch (17) — but DB already has burning-chariot-of-tzeentch
#   Lex slug is "burning-chariot" which is different from DB "burning-chariot-of-tzeentch"
#   Add new row with slug "burning-chariot"
# chaos-lord: slug collision with 40k Chaos Space Marines (id=116, faction=10)
#   AoS unit needs unique slug; use "chaos-lord-aos" — flag as TODO to confirm correct slug
# disc-of-tzeentch: disciples-of-tzeentch (17) — a mount entry
# ethereal-steed: nighthaunt (7) — mount entry
# grot-scuttling: gloomspite-gitz (21)
# herald-of-nurgle: maggotkin-of-nurgle (15)
# karkadrak: slaves-to-darkness (16) — mount creature
# seeker-chariot: hedonites-of-slaanesh (32)
# tzeentch-sorcerer-lord: disciples-of-tzeentch (17) — but DB has chaos-sorcerer-lord in StD;
#   This is specifically a Tzeentch version, slug is canonical per Lex

NOW = ts()

new_units = [
    # (slug, name, faction_id, points_cost, unit_role, can_be_general, can_be_reinforced, keywords_note)
    ("beastrider",           "Beastrider",            56, 0,   "Behemoth", 0, 0, "BEASTCLAW RAIDERS mount — TODO: verify points"),
    ("burning-chariot",      "Burning Chariot",       17, 0,   "Behemoth", 0, 0, "Daemons of Tzeentch — TODO: verify points"),
    # chaos-lord slug conflict: use chaos-lord-aos to avoid 40k collision
    ("chaos-lord-aos",       "Chaos Lord",            16, 115, "Hero",     1, 0, "Slaves to Darkness foot version — TODO: confirm slug"),
    ("disc-of-tzeentch",     "Disc of Tzeentch",      17, 0,   None,       0, 0, "Mount/creature — TODO: verify if standalone unit or mount-only"),
    ("ethereal-steed",       "Ethereal Steed",        7,  0,   None,       0, 0, "Mount — TODO: verify if standalone unit or mount-only"),
    ("grot-scuttling",       "Grot Scuttling",        21, 0,   None,       0, 0, "Gloomspite Gitz — TODO: verify points + role"),
    ("herald-of-nurgle",     "Herald of Nurgle",      15, 130, "Hero",     1, 0, "Daemons of Nurgle — TODO: verify points"),
    ("karkadrak",            "Karkadrak",             16, 0,   None,       0, 0, "Mount creature — TODO: verify if standalone unit"),
    ("seeker-chariot",       "Seeker Chariot",        32, 120, "Behemoth", 0, 0, "Hedonites of Slaanesh — TODO: verify points"),
    ("tzeentch-sorcerer-lord","Tzeentch Sorcerer Lord",17, 130, "Hero",    1, 0, "Disciples of Tzeentch — TODO: verify points"),
]

added_units = 0
skipped_add = []
needs_photo = []

import json

for slug, name, faction_id, pts, role, gen, reinf, note in new_units:
    existing = conn.execute("SELECT id FROM units WHERE slug=?", (slug,)).fetchone()
    if existing:
        skipped_add.append(f"{slug}: already exists (id={existing[0]})")
        continue

    conn.execute("""
        INSERT INTO units (
            faction_id, slug, name, points_cost, base_size_mm, model_count,
            unit_role, can_be_general, can_be_reinforced,
            stats_json, weapons_json, abilities_json, keywords_json, companions_json,
            image_path, image_source_url, wahapedia_url,
            created_at, updated_at
        ) VALUES (?, ?, ?, ?, NULL, 1, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
    """, (
        faction_id, slug, name, pts, role, bool(gen), bool(reinf),
        json.dumps({}),    # stats_json
        json.dumps([]),    # weapons_json
        json.dumps([]),    # abilities_json
        json.dumps([note]), # keywords_json — store TODO note here
        json.dumps([]),    # companions_json
        NOW, NOW
    ))
    needs_photo.append(slug)
    added_units += 1
    log.append(f"INSERT: {slug} ({name}) faction_id={faction_id} pts={pts}")

log.append(f"Units added: {added_units}, skipped: {len(skipped_add)}")
for s in skipped_add:
    log.append(f"  SKIP: {s}")

# ─────────────────────────────────────────────
# 5. COMMIT
# ─────────────────────────────────────────────
conn.commit()
conn.execute("PRAGMA foreign_keys = ON")

# ─────────────────────────────────────────────
# 6. POST-COUNT
# ─────────────────────────────────────────────
post_count = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
log.append(f"POST-COUNT: {post_count} units")
log.append(f"Delta: {post_count - pre_count} (expected: +{added_units} - {deleted_known} = +{added_units - deleted_known})")

# ─────────────────────────────────────────────
# 7. IMAGE CONSISTENCY CHECK
# ─────────────────────────────────────────────
# Verify new image_path files exist for all renamed units
broken_img = []
rows = conn.execute("SELECT slug, image_path FROM units WHERE image_path IS NOT NULL").fetchall()
for slug, img_path in rows:
    full_path = os.path.join("/app/app/static", img_path)
    if not os.path.exists(full_path):
        broken_img.append(f"{slug}: {img_path}")

log.append(f"\nBroken image_path references post-migration: {len(broken_img)}")
for b in broken_img[:30]:
    log.append(f"  BROKEN: {b}")
if len(broken_img) > 30:
    log.append(f"  ... and {len(broken_img)-30} more")

# ─────────────────────────────────────────────
# 8. PRINT REPORT
# ─────────────────────────────────────────────
print("=" * 60)
print("MIGRATION REPORT — v2 align")
print("=" * 60)
for line in log:
    print(line)

print("\n--- NEEDS PHOTO (new inserts, no image yet) ---")
for p in needs_photo:
    print(f"  {p}")

print("\n--- SKIPPED PLURAL RENAMES ---")
for s in skipped_plural:
    print(f"  {s}")

print("\n--- SKIPPED ADDS ---")
for s in skipped_add:
    print(f"  {s}")

conn.close()
print("\nDone.")
