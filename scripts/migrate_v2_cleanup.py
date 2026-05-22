"""
DB + image cleanup: v2 phase 2
- Delete old plural duplicate DB rows (singular rows already exist from prior migration)
- Rename 12 plural image files that only exist with plural name → singular
- Delete 41 plural image files where both plural+singular exist (singular is canonical)
- Handle 3 known renames where old slug still exists alongside new slug
  (black-knights, moonclan-grots, vampire-lord-on-zombie-dragon):
  - The new slug rows already exist in DB with correct data
  - Delete the old slug rows
  - Delete old image files (old slugs should stay deleted, not renamed since new row already has image)

Run inside container: python3 /app/scripts/migrate_v2_cleanup.py
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = "/app/instance/waaahgame.db"
IMG_BASE = "/app/app/static/img/units"

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = OFF")

log = []

def ts():
    return datetime.utcnow().isoformat()

pre_count = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
log.append(f"PRE-COUNT: {pre_count} units")

# ─────────────────────────────────────────────
# 1. Delete old plural DB rows (54+1 special)
#    Singular rows already exist — just remove old plural duplicates
# ─────────────────────────────────────────────
plural_delete_slugs = [
    ("seraphon", "aggradon-lancers"),
    ("stormcast-eternals", "annihilators"),
    ("maggotkin-of-nurgle", "beasts-of-nurgle"),
    ("nighthaunt", "bladegheist-revenants"),
    ("soulblight-gravelords", "blood-knights"),
    ("daughters-of-khaine", "blood-sisters"),
    ("daughters-of-khaine", "blood-stalkers"),
    ("nighthaunt", "chainrasps"),
    ("slaves-to-darkness", "chaos-knights"),
    ("slaves-to-darkness", "chaos-warriors"),
    ("skaven", "clanrats"),
    ("soulblight-gravelords", "dire-wolves"),
    ("daughters-of-khaine", "doomfire-warlocks"),
    ("sylvaneth", "dryads"),
    ("gloomspite-gitz", "fellwater-troggoths"),
    ("disciples-of-tzeentch", "flamers-of-tzeentch"),
    ("cities-of-sigmar", "freeguild-cavaliers"),
    ("cities-of-sigmar", "freeguild-steelhelms"),
    ("nighthaunt", "glaivewraith-stalkers"),
    ("nighthaunt", "grimghast-reapers"),
    ("skaven", "gutter-runners"),
    ("nighthaunt", "hexwraiths"),
    ("cities-of-sigmar", "irondrakes"),
    ("disciples-of-tzeentch", "kairic-acolytes"),
    ("ossiarch-bonereapers", "kavalos-deathriders"),
    ("daughters-of-khaine", "khinerai-lifetakers"),
    ("stormcast-eternals", "liberators"),
    ("ossiarch-bonereapers", "necropolis-stalkers"),
    ("skaven", "night-runners"),
    ("maggotkin-of-nurgle", "nurglings"),
    ("orruk-warclans", "orruk-weirdnob-shaman"),
    ("disciples-of-tzeentch", "pink-horrors-of-tzeentch"),
    ("skaven", "plague-censer-bearers"),
    ("skaven", "plague-monks"),
    ("stormcast-eternals", "praetors"),
    ("maggotkin-of-nurgle", "putrid-blightkings"),
    ("skaven", "rat-ogors"),
    ("gloomspite-gitz", "rockgut-troggoths"),
    ("seraphon", "saurus-warriors"),
    ("orruk-warclans", "savage-orruk-morboys"),
    ("disciples-of-tzeentch", "screamers-of-tzeentch"),
    ("daughters-of-khaine", "sisters-of-slaughter"),
    ("soulblight-gravelords", "skeleton-warriors"),  # special: deathrattle-skeleton is canonical
    ("seraphon", "skinks"),
    ("kharadron-overlords", "skywardens"),
    ("nighthaunt", "spirit-hosts"),
    ("sylvaneth", "spite-revenants"),
    ("gloomspite-gitz", "squig-hoppers"),
    ("skaven", "stormfiends"),
    ("sylvaneth", "tree-revenants"),
    ("disciples-of-tzeentch", "tzaangors"),
    ("soulblight-gravelords", "vargheists"),
    ("stormcast-eternals", "vindictors"),
    ("skaven", "warplock-jezzails"),
    ("daughters-of-khaine", "witch-aelves"),
]

deleted_plural_rows = 0
for faction_dir, old_slug in plural_delete_slugs:
    row = conn.execute("SELECT id FROM units WHERE slug=?", (old_slug,)).fetchone()
    if row:
        conn.execute("DELETE FROM units WHERE id=?", (row[0],))
        deleted_plural_rows += 1
        log.append(f"DELETE plural row: {old_slug} (id={row[0]})")
    else:
        log.append(f"SKIP delete (not found): {old_slug}")

log.append(f"Plural rows deleted: {deleted_plural_rows}")

# ─────────────────────────────────────────────
# 2. Handle 3 old-slug rows still in DB
#    (black-knights, moonclan-grots, vampire-lord-on-zombie-dragon)
#    New slug rows exist with correct data. Delete old rows + old image files.
# ─────────────────────────────────────────────
old_renames_cleanup = [
    ("soulblight-gravelords", "black-knights"),
    ("gloomspite-gitz", "moonclan-grots"),
    ("soulblight-gravelords", "vampire-lord-on-zombie-dragon"),
]
deleted_old_rows = 0
for faction_dir, old_slug in old_renames_cleanup:
    row = conn.execute("SELECT id, image_path FROM units WHERE slug=?", (old_slug,)).fetchone()
    if row:
        unit_id, img_path = row
        conn.execute("DELETE FROM units WHERE id=?", (unit_id,))
        log.append(f"DELETE old-slug row: {old_slug} (id={unit_id})")
        # Delete old image file
        for ext in [".jpg", ".png", ".webp"]:
            img_file = os.path.join(IMG_BASE, faction_dir, f"{old_slug}{ext}")
            if os.path.exists(img_file):
                os.remove(img_file)
                log.append(f"DELETE old img: {img_file}")
        deleted_old_rows += 1
    else:
        log.append(f"SKIP old-slug (not found): {old_slug}")

log.append(f"Old-slug rows deleted: {deleted_old_rows}")

# ─────────────────────────────────────────────
# 3. Image file cleanup: rename plural→singular where only plural exists
#    Also delete plural files where both exist (singular is canonical)
# ─────────────────────────────────────────────
plural_img_map = [
    ("seraphon", "aggradon-lancers", "aggradon-lancer"),
    ("stormcast-eternals", "annihilators", "annihilator"),
    ("maggotkin-of-nurgle", "beasts-of-nurgle", "beast-of-nurgle"),
    ("nighthaunt", "bladegheist-revenants", "bladegheist-revenant"),
    ("soulblight-gravelords", "blood-knights", "blood-knight"),
    ("daughters-of-khaine", "blood-sisters", "blood-sister"),
    ("daughters-of-khaine", "blood-stalkers", "blood-stalker"),
    ("nighthaunt", "chainrasps", "chainrasp"),
    ("slaves-to-darkness", "chaos-knights", "chaos-knight"),
    ("slaves-to-darkness", "chaos-warriors", "chaos-warrior"),
    ("skaven", "clanrats", "clanrat"),
    ("soulblight-gravelords", "dire-wolves", "dire-wolf"),
    ("daughters-of-khaine", "doomfire-warlocks", "doomfire-warlock"),
    ("sylvaneth", "dryads", "dryad"),
    ("gloomspite-gitz", "fellwater-troggoths", "fellwater-troggoth"),
    ("disciples-of-tzeentch", "flamers-of-tzeentch", "flamer-of-tzeentch"),
    ("cities-of-sigmar", "freeguild-cavaliers", "freeguild-cavalier"),
    ("cities-of-sigmar", "freeguild-steelhelms", "freeguild-steelhelm"),
    ("nighthaunt", "glaivewraith-stalkers", "glaivewraith-stalker"),
    ("nighthaunt", "grimghast-reapers", "grimghast-reaper"),
    ("skaven", "gutter-runners", "gutter-runner"),
    ("nighthaunt", "hexwraiths", "hexwraith"),
    ("cities-of-sigmar", "irondrakes", "irondrake"),
    ("disciples-of-tzeentch", "kairic-acolytes", "kairic-acolyte"),
    ("ossiarch-bonereapers", "kavalos-deathriders", "kavalos-deathrider"),
    ("daughters-of-khaine", "khinerai-lifetakers", "khinerai-lifetaker"),
    ("stormcast-eternals", "liberators", "liberator"),
    ("ossiarch-bonereapers", "necropolis-stalkers", "necropolis-stalker"),
    ("skaven", "night-runners", "night-runner"),
    ("maggotkin-of-nurgle", "nurglings", "nurgling"),
    ("orruk-warclans", "orruk-weirdnob-shaman", "weirdnob-shaman"),
    ("disciples-of-tzeentch", "pink-horrors-of-tzeentch", "pink-horror-of-tzeentch"),
    ("skaven", "plague-censer-bearers", "plague-censer-bearer"),
    ("skaven", "plague-monks", "plague-monk"),
    ("stormcast-eternals", "praetors", "praetor"),
    ("maggotkin-of-nurgle", "putrid-blightkings", "putrid-blightking"),
    ("skaven", "rat-ogors", "rat-ogor"),
    ("gloomspite-gitz", "rockgut-troggoths", "rockgut-troggoth"),
    ("seraphon", "saurus-warriors", "saurus-warrior"),
    ("orruk-warclans", "savage-orruk-morboys", "savage-orruk-morboy"),
    ("disciples-of-tzeentch", "screamers-of-tzeentch", "screamer-of-tzeentch"),
    ("daughters-of-khaine", "sisters-of-slaughter", "sister-of-slaughter"),
    ("soulblight-gravelords", "skeleton-warriors", "deathrattle-skeleton"),
    ("seraphon", "skinks", "skink"),
    ("kharadron-overlords", "skywardens", "skywarden"),
    ("nighthaunt", "spirit-hosts", "spirit-host"),
    ("sylvaneth", "spite-revenants", "spite-revenant"),
    ("gloomspite-gitz", "squig-hoppers", "squig-hopper"),
    ("skaven", "stormfiends", "stormfiend"),
    ("sylvaneth", "tree-revenants", "tree-revenant"),
    ("disciples-of-tzeentch", "tzaangors", "tzaangor"),
    ("soulblight-gravelords", "vargheists", "vargheist"),
    ("stormcast-eternals", "vindictors", "vindictor"),
    ("skaven", "warplock-jezzails", "warplock-jezzail"),
    ("daughters-of-khaine", "witch-aelves", "witch-aelf"),
]

imgs_renamed = 0
imgs_deleted_plural = 0
imgs_neither = []

for faction_dir, old_slug, new_slug in plural_img_map:
    old_file = os.path.join(IMG_BASE, faction_dir, f"{old_slug}.jpg")
    new_file = os.path.join(IMG_BASE, faction_dir, f"{new_slug}.jpg")
    old_exists = os.path.exists(old_file)
    new_exists = os.path.exists(new_file)

    if old_exists and new_exists:
        # Both exist: delete the plural (old) file, singular is canonical
        os.remove(old_file)
        imgs_deleted_plural += 1
        log.append(f"DELETE plural img (dup): {old_slug}.jpg [{faction_dir}]")
    elif old_exists and not new_exists:
        # Only plural exists: rename to singular
        os.rename(old_file, new_file)
        imgs_renamed += 1
        log.append(f"RENAME img: {old_slug}.jpg → {new_slug}.jpg [{faction_dir}]")
    elif not old_exists and new_exists:
        log.append(f"OK (singular already exists): {new_slug}.jpg [{faction_dir}]")
    else:
        imgs_neither.append(f"{faction_dir}/{new_slug}.jpg")
        log.append(f"NEITHER img exists: {faction_dir}/{old_slug}.jpg")

log.append(f"Imgs renamed: {imgs_renamed}, plural dups deleted: {imgs_deleted_plural}")
if imgs_neither:
    log.append(f"WARNING — no img for: {imgs_neither}")

# ─────────────────────────────────────────────
# 4. Commit
# ─────────────────────────────────────────────
conn.commit()
conn.execute("PRAGMA foreign_keys = ON")

post_count = conn.execute("SELECT COUNT(*) FROM units").fetchone()[0]
log.append(f"POST-COUNT: {post_count} units")
expected_delta = -(deleted_plural_rows + deleted_old_rows)
log.append(f"Delta: {post_count - pre_count} (expected ~{expected_delta})")

# ─────────────────────────────────────────────
# 5. Image consistency check on changed units
# ─────────────────────────────────────────────
broken = []
for _, _, new_slug in plural_img_map:
    row = conn.execute("SELECT slug, image_path FROM units WHERE slug=?", (new_slug,)).fetchone()
    if row:
        slug, img_path = row
        if img_path:
            full = os.path.join("/app/app/static", img_path)
            if not os.path.exists(full):
                broken.append(f"{slug}: {img_path} — FILE MISSING")

if broken:
    log.append(f"\nBroken image refs for renamed units: {len(broken)}")
    for b in broken:
        log.append(f"  {b}")
else:
    log.append("\nAll renamed unit image_path refs point to existing files.")

# Print
print("=" * 60)
print("CLEANUP REPORT — v2 phase 2")
print("=" * 60)
for line in log:
    print(line)

conn.close()
print("\nDone.")
