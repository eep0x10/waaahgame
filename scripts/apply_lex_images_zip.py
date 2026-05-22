"""Apply Lexicanum-extracted unit images from lex_images.zip to live static dir.

Zip is FLAT (no faction folders) — entries are `<slug>.<ext>`. We match by Unit.slug
(unique across DB). For each matched DB unit:
  - back up the existing live image once (under units/_backup_pre_lex/)
  - skip if byte-identical
  - else validate (Pillow >=200x200, >=5KB), resize to max 600px wide @ JPEG q85
  - write to app/static/img/units/<faction_slug>/<slug>.<ext>
  - if extension changed, delete old file and update Unit.image_path in DB

Run inside container:
  docker compose exec -T app python scripts/apply_lex_images_zip.py
"""
from __future__ import annotations

import io
import shutil
import sys
import zipfile
from pathlib import Path

from PIL import Image

# Container paths
ROOT = Path("/app")
ZIP_PATH = ROOT / "scripts" / "_cache" / "lex_images.zip"
UNITS_DIR = ROOT / "app" / "static" / "img" / "units"
BACKUP_DIR = UNITS_DIR / "_backup_pre_lex"

MIN_W, MIN_H = 200, 200
MIN_BYTES = 5 * 1024
MAX_W = 600
JPEG_Q = 85


def stem_of(name: str) -> str:
    return name.rsplit(".", 1)[0]


def ext_of(name: str) -> str:
    return name.rsplit(".", 1)[1].lower() if "." in name else ""


def main() -> int:
    if not ZIP_PATH.exists():
        print(f"FATAL: zip not found at {ZIP_PATH}")
        return 1

    # Load Flask app + DB
    sys.path.insert(0, str(ROOT))
    from app import create_app  # type: ignore
    from app.extensions import db  # type: ignore
    from app.models.game import Faction, Unit  # type: ignore

    app = create_app()
    with app.app_context():
        # Build zip slug -> (zip_inner_name, bytes-on-demand)
        zf = zipfile.ZipFile(ZIP_PATH)
        zip_names = zf.namelist()
        zip_by_slug: dict[str, str] = {}
        for n in zip_names:
            if "/" in n:
                continue  # ignore directory-like (none expected)
            s = stem_of(n)
            zip_by_slug[s] = n

        # Load DB units + faction map
        factions = {f.id: f for f in Faction.query.all()}
        units = Unit.query.all()

        matched: list[tuple[Unit, str]] = []  # (unit, zip_name)
        no_zip: list[Unit] = []
        for u in units:
            zn = zip_by_slug.get(u.slug)
            if zn:
                matched.append((u, zn))
            else:
                no_zip.append(u)

        matched_slugs = {u.slug for u, _ in matched}
        zip_unmatched = [n for s, n in zip_by_slug.items() if s not in matched_slugs]

        # Stats
        n_replaced = 0
        n_skipped_identical = 0
        n_skipped_validation = 0
        n_no_existing = 0
        n_ext_changed = 0
        n_backed_up = 0

        # Beastlord before
        beastlord_before = None
        beastlord_path = None
        for u in units:
            if u.slug == "beastlord":
                fac = factions[u.faction_id]
                # use image_path if present, else expected
                rel = u.image_path or f"units/{fac.slug}/{u.slug}.jpg"
                p = ROOT / "app" / "static" / "img" / rel
                beastlord_path = p
                if p.exists():
                    try:
                        im = Image.open(p)
                        beastlord_before = (im.size, p.stat().st_size, p.name)
                    except Exception:
                        beastlord_before = (("?", "?"), p.stat().st_size, p.name)
                break

        for u, zip_name in matched:
            fac = factions.get(u.faction_id)
            if fac is None:
                continue
            new_ext = ext_of(zip_name)
            new_data = zf.read(zip_name)

            # Determine existing path: from image_path if set + exists, else by convention
            existing_path: Path | None = None
            if u.image_path:
                cand = ROOT / "app" / "static" / "img" / u.image_path
                if cand.exists():
                    existing_path = cand
            if existing_path is None:
                # Try standard convention with a few common exts
                for try_ext in ("jpg", "jpeg", "png", "webp"):
                    cand = UNITS_DIR / fac.slug / f"{u.slug}.{try_ext}"
                    if cand.exists():
                        existing_path = cand
                        break

            # Validate new image
            try:
                im = Image.open(io.BytesIO(new_data))
                im.load()
            except Exception as e:
                n_skipped_validation += 1
                print(f"  [validation] {u.slug} ({zip_name}): cannot decode: {e}")
                continue
            if im.width < MIN_W or im.height < MIN_H or len(new_data) < MIN_BYTES:
                n_skipped_validation += 1
                print(f"  [validation] {u.slug}: {im.size} {len(new_data)}B below thresholds")
                continue

            # Resize + reencode to JPEG q85 (keep extension as zip-provided if not jpg-able; we standardise to jpg)
            # Strategy: always emit JPEG (small + uniform). image_path will be .jpg.
            target_w = MAX_W
            if im.width > target_w:
                new_h = int(im.height * (target_w / im.width))
                im_resized = im.convert("RGB").resize((target_w, new_h), Image.LANCZOS)
            else:
                im_resized = im.convert("RGB")

            out_buf = io.BytesIO()
            im_resized.save(out_buf, format="JPEG", quality=JPEG_Q, optimize=True)
            out_bytes = out_buf.getvalue()

            # Target path: always .jpg
            target_rel = f"units/{fac.slug}/{u.slug}.jpg"
            target_path = ROOT / "app" / "static" / "img" / target_rel
            target_path.parent.mkdir(parents=True, exist_ok=True)

            # Idempotency: compare re-encoded bytes to existing live file
            if existing_path is not None and existing_path == target_path and existing_path.exists():
                try:
                    if existing_path.read_bytes() == out_bytes:
                        n_skipped_identical += 1
                        # still ensure DB image_path is correct
                        if u.image_path != target_rel:
                            u.image_path = target_rel
                        continue
                except OSError:
                    pass

            # Backup the existing file once (if any)
            if existing_path is not None and existing_path.exists():
                rel_to_units = existing_path.relative_to(UNITS_DIR)
                backup_path = BACKUP_DIR / rel_to_units
                if not backup_path.exists():
                    backup_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(existing_path, backup_path)
                    n_backed_up += 1
            else:
                n_no_existing += 1

            # If existing extension differs, remove old file
            if existing_path is not None and existing_path != target_path and existing_path.exists():
                existing_path.unlink()
                n_ext_changed += 1

            target_path.write_bytes(out_bytes)
            n_replaced += 1

            # Update DB image_path if changed
            if u.image_path != target_rel:
                u.image_path = target_rel

        # DB sync: ensure every Unit.image_path points to an existing file
        n_db_fixed = 0
        for u in units:
            fac = factions.get(u.faction_id)
            if fac is None:
                continue
            cur_rel = u.image_path
            cur_exists = False
            if cur_rel:
                p = ROOT / "app" / "static" / "img" / cur_rel
                cur_exists = p.exists()
            if not cur_exists:
                # try common exts in faction dir
                for try_ext in ("jpg", "jpeg", "png", "webp"):
                    cand_rel = f"units/{fac.slug}/{u.slug}.{try_ext}"
                    cand_p = ROOT / "app" / "static" / "img" / cand_rel
                    if cand_p.exists():
                        if u.image_path != cand_rel:
                            u.image_path = cand_rel
                            n_db_fixed += 1
                        break

        db.session.commit()

        # Beastlord after
        beastlord_after = None
        if beastlord_path is not None:
            # use the unit's (possibly updated) image_path
            u = Unit.query.filter_by(slug="beastlord").first()
            if u and u.image_path:
                p = ROOT / "app" / "static" / "img" / u.image_path
                if p.exists():
                    try:
                        im = Image.open(p)
                        beastlord_after = (im.size, p.stat().st_size, p.name)
                    except Exception:
                        beastlord_after = (("?", "?"), p.stat().st_size, p.name)

        # ===== Stats report =====
        print()
        print("=" * 60)
        print("CAVEMAN REPORT")
        print("=" * 60)
        print(f"zip files                : {len(zip_names)}")
        print(f"zip unique slugs         : {len(zip_by_slug)}")
        print(f"db units                 : {len(units)}")
        print(f"matched (slug)           : {len(matched)}")
        print(f"  + backed up            : {n_backed_up}")
        print(f"  + no existing file     : {n_no_existing}")
        print(f"  + ext changed (deleted): {n_ext_changed}")
        print(f"replaced (new art)       : {n_replaced}")
        print(f"skipped (identical)      : {n_skipped_identical}")
        print(f"skipped (validation)     : {n_skipped_validation}")
        print(f"db image_path fixed      : {n_db_fixed}")
        print()
        print(f"DB units WITHOUT zip entry: {len(no_zip)} (first 20)")
        for u in no_zip[:20]:
            fac = factions.get(u.faction_id)
            print(f"  - {fac.slug if fac else '?'}/{u.slug}")
        print()
        print(f"ZIP entries UNMATCHED to DB: {len(zip_unmatched)} (first 20)")
        for n in zip_unmatched[:20]:
            print(f"  - {n}")
        print()
        print("BEASTLORD:")
        print(f"  before: {beastlord_before}")
        print(f"  after : {beastlord_after}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
