#!/usr/bin/env python3
"""
apply_lex_targeted_fix.py
--------------------------
Fixes wrong images for ~70 user-specified units by extracting correct images
from the existing lex_phase3_minis.zip.

Each DB slug maps to a Lex slug (the filename stem in the zip).  The script:
  1. Creates a backup dir for any file it will overwrite.
  2. Extracts the Lex image from the zip into the faction subdir under
     app/static/img/units/, using the DB slug as the output filename.
  3. Removes any existing file with the same stem but a different extension.
  4. Prints per-unit status and a final summary.

Units NOT fixable from the zip are listed at the bottom with reasons.
"""

import os
import sys
import shutil
import zipfile
import json

# --- Paths ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(SCRIPT_DIR)
STATIC_UNITS = os.path.join(REPO_ROOT, "app", "static", "img", "units")
BACKUP_DIR = os.path.join(STATIC_UNITS, "_backup_targeted_fix")
ZIP_PATH = os.path.join(os.path.expanduser("~"), "Downloads", "lex_phase3_minis.zip")

# DB unit export (written earlier by docker compose exec)
DB_EXPORT = os.path.join(SCRIPT_DIR, "cache", "db_units_full_export.json")

# --- Mapping: DB_SLUG -> (LEX_SLUG_IN_ZIP, NOTE) ---
# Key   = slug used by the app DB (and the target filename stem)
# Value = (stem in zip, human note)
SLUG_MAP = {
    # Beasts of Chaos
    "bullgor-warrior":              ("bullgor",                    "DB slug is 'bullgor-warrior', Lex/zip uses 'bullgor'"),
    # Blades of Khorne — URL-encoded apostrophe vs -s-
    "garrek%27s-reavers":           ("garrek-s-reavers",           "URL-encoded apostrophe vs -s- in zip"),
    "kamandora%27s-blades":         ("kamandora-s-blades",         "URL-encoded apostrophe vs -s- in zip"),
    "magore%27s-fiends":            ("magore-s-fiends",            "URL-encoded apostrophe vs -s- in zip"),
    # Cities of Sigmar
    "battlemage":                   ("battlemage",                 "exact match (was only SVG, now has jpeg)"),
    "freeguild-cavaliers":          ("freeguild-cavalier",         "plural vs singular in zip"),
    "fusil-major-on-ogor-warhulk":  ("fusil-major",               "zip uses short name 'fusil-major'"),
    # Disciples of Tzeentch
    "kairic-acolytes":              ("kairic-acolyte",             "plural vs singular"),
    "pink-horrors-of-tzeentch":     ("pink-horror-of-tzeentch",   "plural vs singular"),
    "flamers-of-tzeentch":          ("flamer-of-tzeentch",        "plural vs singular"),
    "magister":                     ("magister",                   "exact match (was only SVG)"),
    "tzaangor-shaman":              ("tzaangor-shaman",            "exact match (was only SVG)"),
    # Soulblight Gravelords
    "zombie-dragon":                ("zombie-dragon",              "exact match (was only SVG)"),
    "skeleton-warrior":             ("deathrattle-skeleton",       "DB slug differs; Lex/zip slug is correct name"),
    "deadwalker-zombie":            ("zombie",                     "DB slug is 'deadwalker-zombie', zip is 'zombie'"),
    "blood-knights":                ("blood-knight",               "plural vs singular"),
    # Gloomspite Gitz
    "squig-hoppers":                ("squig-hopper",               "plural vs singular"),
    # Nighthaunt
    "hexwraiths":                   ("hexwraith",                  "plural vs singular"),
    # Skaven
    "night-runners":                ("night-runner",               "plural vs singular"),
    "plague-censer-bearers":        ("plague-censer-bearer",       "plural vs singular"),
    "plague-monks":                 ("plague-monk",                "plural vs singular"),
    # Slaves to Darkness
    "chaos-warriors":               ("chaos-warrior",              "plural vs singular"),
    # Stormcast Eternals
    "liberators":                   ("liberator",                  "plural vs singular"),
    "vindictors":                   ("vindictor",                  "plural vs singular"),
    "annihilators":                 ("annihilator",                "plural vs singular"),
    # Sylvaneth
    "dryads":                       ("dryad",                      "plural vs singular"),
    "spite-revenants":              ("spite-revenant",             "plural vs singular"),
    "tree-revenants":               ("tree-revenant",              "plural vs singular"),
    "kurnoth-hunters-with-greatbows":   ("kurnoth-hunter",         "weapon variant — zip only has generic kurnoth-hunter"),
    "kurnoth-hunters-with-greatswords": ("kurnoth-hunter",         "weapon variant — zip only has generic kurnoth-hunter (same image as greatbows)"),
    # Maggotkin of Nurgle
    "plague-drones":                ("plague-drone-of-nurgle",     "zip uses full name 'plague-drone-of-nurgle'"),
    # Seraphon
    "aggradon-lancers":             ("aggradon-lancer",            "plural vs singular"),
    "sunblood-pack":                ("saurus-sunblood",            "zip uses older 'saurus-sunblood' name"),
    # Ossiarch Bonereapers
    "kavalos-deathriders":          ("kavalos-deathrider",         "plural vs singular"),
    # Orruk Warclans
    "orruk-brutes":                 ("brute",                      "DB has 'orruk-' prefix, zip uses bare 'brute'"),
    "megaboss-on-maw-krusha":       ("megaboss",                   "zip uses short name 'megaboss'"),
    # Kharadron Overlords
    "endrinmaster-with-dirigible-suit": ("endrinmaster",           "zip uses short name 'endrinmaster'"),
}

# Units from the user list that are NOT in the zip and cannot be fixed
CANNOT_FIX = [
    ("freeguild-crossbowmen",               "Not in Lex lex_phase3_units.json, not in zip"),
    ("helblaster-volley-gun",               "Not in Lex lex_phase3_units.json, not in zip"),
    ("morathi-khaine",                      "Not in Lex lex_phase3_units.json, not in zip"),
    ("kairos-fateweaver",                   "Not in Lex lex_phase3_units.json, not in zip"),
    ("skragrott-the-loonking",              "Not in Lex lex_phase3_units.json, not in zip"),
    ("moonclan-grots",                      "Not in Lex lex_phase3_units.json, not in zip"),
    ("brokk-grungsson-lord-magnate-of-barak-nar", "Not in Lex lex_phase3_units.json, not in zip"),
    ("alarith-spirit-of-the-mountain",      "Not in Lex lex_phase3_units.json, not in zip"),
    ("alarith-stonemage",                   "Not in Lex lex_phase3_units.json, not in zip"),
    ("scinari-cathallar",                   "Not in Lex lex_phase3_units.json, not in zip"),
    ("the-light-of-eltharion",              "Not in Lex lex_phase3_units.json, not in zip"),
    ("vanari-lord-regent",                  "Not in Lex lex_phase3_units.json, not in zip"),
    ("alarith-stoneguard",                  "Not in Lex lex_phase3_units.json, not in zip"),
    ("vanari-auralan-wardens",              "Not in Lex lex_phase3_units.json, not in zip"),
    ("rotigus",                             "Not in Lex lex_phase3_units.json, not in zip"),
    ("gordrakk-the-fist-of-gork",          "Not in Lex lex_phase3_units.json, not in zip"),
    ("swampcalla-shaman-with-pot-grot",     "Not in Lex lex_phase3_units.json, not in zip"),
    ("kruleboyz-gutrippaz",                 "Not in Lex lex_phase3_units.json, not in zip"),
    ("nagash-supreme-lord-of-the-undead",   "Not in Lex lex_phase3_units.json, not in zip"),
    ("thanquol-on-boneripper",              "Not in Lex lex_phase3_units.json, not in zip"),
    ("archaon-the-everchosen",              "Not in Lex lex_phase3_units.json, not in zip"),
    ("be-lakor-the-dark-master",            "Not in Lex lex_phase3_units.json, not in zip"),
    ("black-knights",                       "Not in Lex lex_phase3_units.json, not in zip"),
    ("mannfred-von-carstein-mortarch-of-night", "Not in Lex lex_phase3_units.json, not in zip"),
    ("vampire-lord-on-zombie-dragon",       "Not in Lex lex_phase3_units.json, not in zip"),
    ("yndrasta-the-celestial-spear",        "Not in Lex lex_phase3_units.json, not in zip"),
    ("drycha-hamadreth",                    "Not in Lex lex_phase3_units.json, not in zip"),
]


def get_faction_dir(db_slug, db_rows_by_slug):
    """Derive the faction directory from the DB image_path."""
    row = db_rows_by_slug.get(db_slug)
    if row is None:
        return None
    img_path = row[1]  # e.g. "units/beasts-of-chaos/bullgor-warrior.jpg"
    if not img_path:
        return None
    parts = img_path.split("/")
    if len(parts) >= 2:
        faction = parts[1]
        return os.path.join(STATIC_UNITS, faction)
    return None


def remove_other_extensions(faction_dir, db_slug, keep_ext):
    """Remove any file with the same stem but a different extension."""
    removed = []
    for f in os.listdir(faction_dir):
        stem, ext = os.path.splitext(f)
        if stem == db_slug and ext.lower() != keep_ext.lower():
            full = os.path.join(faction_dir, f)
            os.remove(full)
            removed.append(f)
    return removed


def main():
    print("=" * 70)
    print("apply_lex_targeted_fix.py — fixing wrong unit images")
    print("=" * 70)

    # Verify zip exists
    if not os.path.exists(ZIP_PATH):
        print(f"ERROR: zip not found at {ZIP_PATH}", file=sys.stderr)
        sys.exit(1)

    # Load DB export for image path lookup
    db_rows_by_slug = {}
    if os.path.exists(DB_EXPORT):
        with open(DB_EXPORT) as f:
            rows = json.load(f)
        # rows = list of [slug, name, image_path, image_source_url]
        for row in rows:
            db_rows_by_slug[row[0]] = (row[1], row[2], row[3])
    else:
        print(f"WARNING: DB export not found at {DB_EXPORT} — faction dirs will be guessed", file=sys.stderr)

    # Open zip
    zf = zipfile.ZipFile(ZIP_PATH, "r")
    zip_stems = {n.rsplit(".", 1)[0]: n for n in zf.namelist()}

    # Create backup dir
    os.makedirs(BACKUP_DIR, exist_ok=True)

    fixed = []
    skipped = []
    errors = []

    for db_slug, (lex_slug, note) in SLUG_MAP.items():
        # Find the zip file
        zip_entry = zip_stems.get(lex_slug)
        if zip_entry is None:
            errors.append((db_slug, f"lex_slug '{lex_slug}' not found in zip"))
            continue

        # Derive target extension from zip entry
        zip_ext = "." + zip_entry.rsplit(".", 1)[-1]  # .jpg, .jpeg, .png

        # Find faction dir
        faction_dir = get_faction_dir(db_slug, db_rows_by_slug)
        if faction_dir is None:
            # Try to find by scanning all faction dirs
            found_faction = None
            for faction in os.listdir(STATIC_UNITS):
                fd = os.path.join(STATIC_UNITS, faction)
                if not os.path.isdir(fd) or faction.startswith("_"):
                    continue
                for f in os.listdir(fd):
                    if f.rsplit(".", 1)[0] == db_slug:
                        found_faction = fd
                        break
                if found_faction:
                    break
            faction_dir = found_faction

        if faction_dir is None:
            errors.append((db_slug, "could not determine faction dir"))
            continue

        if not os.path.isdir(faction_dir):
            errors.append((db_slug, f"faction dir does not exist: {faction_dir}"))
            continue

        target_path = os.path.join(faction_dir, db_slug + zip_ext)

        # Back up existing files with this stem
        backed_up = []
        for f in os.listdir(faction_dir):
            stem = f.rsplit(".", 1)[0]
            if stem == db_slug:
                src = os.path.join(faction_dir, f)
                dst = os.path.join(BACKUP_DIR, f"{db_slug}__{os.path.basename(faction_dir)}__{f}")
                shutil.copy2(src, dst)
                backed_up.append(f)

        # Remove all existing files with this stem (different extensions)
        removed_exts = remove_other_extensions(faction_dir, db_slug, zip_ext)

        # Extract from zip
        with zf.open(zip_entry) as src_f:
            with open(target_path, "wb") as dst_f:
                shutil.copyfileobj(src_f, dst_f)

        size_kb = os.path.getsize(target_path) // 1024
        backed_msg = f" (backed up: {', '.join(backed_up)})" if backed_up else " (no prior file)"
        removed_msg = f" removed ext: {removed_exts}" if removed_exts else ""
        print(f"  [OK] {db_slug}")
        print(f"       zip: {zip_entry} ({size_kb} KB) -> {os.path.relpath(target_path, REPO_ROOT)}")
        print(f"       note: {note}{backed_msg}{removed_msg}")
        fixed.append(db_slug)

    zf.close()

    print()
    print("=" * 70)
    print(f"FIXED: {len(fixed)}/{len(SLUG_MAP)}")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for slug, reason in errors:
            print(f"  {slug}: {reason}")

    print()
    print(f"CANNOT FIX — needs new scrape ({len(CANNOT_FIX)}):")
    for slug, reason in CANNOT_FIX:
        print(f"  {slug}: {reason}")

    total_attempted = len(SLUG_MAP)
    total_not_fixable = len(CANNOT_FIX)
    total_target = total_attempted + total_not_fixable
    print()
    print(
        f"SUMMARY: {len(fixed)} fixed | {len(errors)} errored | "
        f"{total_not_fixable} need new scrape | {total_target} total units targeted"
    )
    print(f"Backups written to: {BACKUP_DIR}")


if __name__ == "__main__":
    main()
