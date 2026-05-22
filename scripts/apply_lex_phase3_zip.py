"""Apply Lexicanum phase3 miniature photos from lex_phase3_minis.zip to live static dir.

Zip is FLAT (no faction folders) — entries are `<slug>.<ext>`. We match by Unit.slug
(unique across DB). For each matched DB unit:
  - back up ALL existing live images ONCE to units/_backup_pre_phase3/ before any writes
    (aborts if backup dir already exists to avoid double-backup)
  - find the existing file for that slug (any ext: jpg/jpeg/png/webp)
  - if extension differs, delete old file and write new with zip's extension
  - if same extension (or no existing file), just overwrite/write
  - NO image validation / resize — apply raw bytes as-is (Lexicanum minis are clean)

Run inside container:
  docker compose exec -T app python scripts/apply_lex_phase3_zip.py
"""
from __future__ import annotations

import shutil
import sys
import zipfile
from pathlib import Path

# Container paths
ROOT = Path("/app")
ZIP_PATH = Path("/app/scripts/_cache/lex_phase3_minis.zip")
UNITS_DIR = ROOT / "app" / "static" / "img" / "units"
BACKUP_DIR = UNITS_DIR / "_backup_pre_phase3"

KNOWN_EXTS = ("jpg", "jpeg", "png", "webp")


def stem_of(name: str) -> str:
    return name.rsplit(".", 1)[0]


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def main() -> int:
    if not ZIP_PATH.exists():
        print(f"FATAL: zip not found at {ZIP_PATH}")
        return 1

    # --- Backup gate: abort if backup dir already exists ---
    if BACKUP_DIR.exists():
        print(f"ERROR: backup dir already exists: {BACKUP_DIR}")
        print("       Refusing to double-backup. Remove it manually if you want to re-run.")
        return 1

    # Load Flask app + DB
    sys.path.insert(0, str(ROOT))
    from app import create_app  # type: ignore
    from app.extensions import db  # type: ignore  # noqa: F401 (needed for ORM)
    from app.models.game import Faction, Unit  # type: ignore

    app = create_app()
    with app.app_context():
        # ---- Step 1: Build a flat index of all existing slug -> Path ----
        existing_by_slug: dict[str, Path] = {}
        for faction_dir in UNITS_DIR.iterdir():
            if faction_dir.is_dir() and not faction_dir.name.startswith("_"):
                for f in faction_dir.iterdir():
                    if f.is_file() and f.suffix.lower().lstrip(".") in KNOWN_EXTS:
                        existing_by_slug[f.stem] = f

        # ---- Step 2: Create backup of ALL current unit images ----
        print(f"Creating backup at {BACKUP_DIR} ...")
        all_current: list[Path] = []
        for faction_dir in UNITS_DIR.iterdir():
            if faction_dir.is_dir() and not faction_dir.name.startswith("_"):
                for f in faction_dir.iterdir():
                    if f.is_file():
                        all_current.append(f)

        BACKUP_DIR.mkdir(parents=True, exist_ok=False)
        for f in all_current:
            dest = BACKUP_DIR / f.name
            shutil.copy2(f, dest)
        print(f"Backed up {len(all_current)} files.")

        # ---- Step 3: Build zip slug map ----
        zf = zipfile.ZipFile(ZIP_PATH)
        zip_names = [n for n in zf.namelist() if "/" not in n]
        zip_by_slug: dict[str, str] = {}
        for n in zip_names:
            if "." in n:
                s = stem_of(n)
                zip_by_slug[s] = n

        # ---- Step 4: Load DB units + faction map ----
        factions = {f.id: f for f in Faction.query.all()}
        units = Unit.query.all()
        units_by_slug = {u.slug: u for u in units}

        # ---- Step 5: Apply each zip entry ----
        n_replaced = 0
        n_ext_changed = 0
        n_new = 0
        n_errors = 0
        n_no_faction = 0

        for zip_slug, zip_entry in zip_by_slug.items():
            new_ext = ext_of(zip_entry)
            try:
                new_data = zf.read(zip_entry)
            except Exception as e:
                print(f"  [error] {zip_slug}: cannot read from zip: {e}")
                n_errors += 1
                continue

            existing_path = existing_by_slug.get(zip_slug)

            # Determine target path
            if existing_path is not None:
                # Use same faction dir as the existing file
                target_path = existing_path.parent / f"{zip_slug}.{new_ext}"
            else:
                # New slug — need faction from DB
                unit = units_by_slug.get(zip_slug)
                if unit is None:
                    print(f"  [skip] {zip_slug}: no DB unit and no existing file — cannot place")
                    n_errors += 1
                    continue
                fac = factions.get(unit.faction_id)
                if fac is None:
                    print(f"  [skip] {zip_slug}: no faction in DB")
                    n_no_faction += 1
                    continue
                faction_dir = UNITS_DIR / fac.slug
                faction_dir.mkdir(parents=True, exist_ok=True)
                target_path = faction_dir / f"{zip_slug}.{new_ext}"

            # If extension changed, remove old file
            if existing_path is not None and existing_path != target_path and existing_path.exists():
                old_ext = ext_of(existing_path.name)
                existing_path.unlink()
                target_path.write_bytes(new_data)
                print(f"  [apply] {zip_slug}: replaced .{old_ext} -> .{new_ext} (ext change, removed old)")
                n_ext_changed += 1
                n_replaced += 1
            elif existing_path is not None:
                # Same path (same ext) — overwrite
                target_path.write_bytes(new_data)
                print(f"  [apply] {zip_slug}: replaced .{new_ext} -> .{new_ext}")
                n_replaced += 1
            else:
                # New slug
                target_path.write_bytes(new_data)
                print(f"  [apply] new {zip_slug}.{new_ext}")
                n_new += 1

            # Update DB image_path if needed
            unit = units_by_slug.get(zip_slug)
            if unit is not None:
                fac = factions.get(unit.faction_id)
                if fac is not None:
                    new_rel = f"units/{fac.slug}/{zip_slug}.{new_ext}"
                    if unit.image_path != new_rel:
                        unit.image_path = new_rel

        db.session.commit()

        # ---- Summary ----
        print()
        print("=" * 60)
        print("PHASE3 APPLY SUMMARY")
        print("=" * 60)
        print(f"zip entries total        : {len(zip_names)}")
        print(f"zip unique slugs         : {len(zip_by_slug)}")
        print(f"replaced (same ext)      : {n_replaced - n_ext_changed}")
        print(f"replaced (ext changed)   : {n_ext_changed}")
        print(f"new (slug not in units)  : {n_new}")
        print(f"skipped (no faction/DB)  : {n_no_faction}")
        print(f"errors                   : {n_errors}")
        print(f"backed up files          : {len(all_current)}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
