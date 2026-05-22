#!/usr/bin/env python3
"""
Replace unit images in the Flask app with Lexicanum art.

Source: scripts/cache/lexicanum_manifest.json (already extracted).
Convention:
  - Files at app/static/img/units/<faction>/<unit-slug>.<ext>
  - DB Unit.image_path = 'units/<faction>/<slug>.<ext>'

Idempotent: skips overwrite when new image byte-content is near-identical
to existing (size delta < 5% AND first 256 bytes match).

Backs up replaced files to app/static/img/units/_backup_lex/<faction>/<slug>.<ext>.

Politeness: 0.3s spacing, real User-Agent, Referer header for MediaWiki.

Synchronous. No background. No fallback to non-Lex sources.
"""

import io
import json
import re
import shutil
import sys
import time
from pathlib import Path

import requests
from PIL import Image

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

MANIFEST_PATH = REPO_ROOT / "scripts" / "cache" / "lexicanum_manifest.json"
UNITS_DIR     = REPO_ROOT / "app" / "static" / "img" / "units"
BACKUP_DIR    = UNITS_DIR / "_backup_lex"

# ---------------------------------------------------------------------------
# Politeness
# ---------------------------------------------------------------------------

USER_AGENT = "waaahgame/0.7 (educational; contact: yhextt@gmail.com)"
REFERER    = "https://ageofsigmar.lexicanum.com/"
REQ_DELAY  = 0.3
REQ_TIMEOUT = 30

# ---------------------------------------------------------------------------
# Validation thresholds
# ---------------------------------------------------------------------------

MIN_DIM_PX   = 300
MIN_BYTES    = 10 * 1024
MAX_WIDTH_PX = 600
JPEG_QUALITY = 85

# ---------------------------------------------------------------------------
# Lexicanum faction-name -> DB faction-slug map.
# Lex 'factions' list usually contains *parent* factions (e.g. Brayherds + Beasts
# of Chaos). DB has subfaction slugs for some units. We map both directions.
# ---------------------------------------------------------------------------

# Direct slugify of Lex faction name -> DB faction slug (when they differ).
LEX_FACTION_TO_DB: dict[str, str] = {
    # AoS subfactions -> DB subfaction slug (DB carries the subfaction)
    "brayherds":              "beasts-of-chaos",
    "warherds":               "beasts-of-chaos",
    "thunderscorn":           "beasts-of-chaos",
    "monsters-of-chaos":      "monsters-of-chaos",
    "tzeentch-arcanites":     "tzeentch-arcanites",
    "daemons-of-tzeentch":    "disciples-of-tzeentch",
    "khorne-bloodbound":      "blades-of-khorne",
    "daemons-of-khorne":      "blades-of-khorne",
    "nurgle-rotbringers":     "maggotkin-of-nurgle",
    "daemons-of-nurgle":      "maggotkin-of-nurgle",
    "slaanesh-sybarites":     "slaanesh-sybarites",
    "daemons-of-slaanesh":    "hedonites-of-slaanesh",
    "everchosen":             "slaves-to-darkness",
    "warriors-of-chaos":      "slaves-to-darkness",
    "daemons-of-chaos":       "slaves-to-darkness",
    "eshin":                  "skaven",
    "moulder":                "skaven",
    "skryre":                 "skaven",
    "pestilens":              "skaven",
    "verminus":               "skaven",
    "masterclan":             "skaven",
    "skaventide":             "skaventide",
    "beasts-of-the-grave":    "beasts-of-the-grave",
    "deathlords":             "deathlords",
    "flesh-eater-courts":     "flesh-eater-courts",
    "soulblight-gravelords":  "soulblight-gravelords",
    "nighthaunt":             "nighthaunt",
    "ossiarch-bonereapers":   "ossiarch-bonereapers",
    "stormcast-eternals":     "stormcast-eternals",
    "cities-of-sigmar":       "cities-of-sigmar",
    "ironweld-arsenal":       "cities-of-sigmar",
    "freeguild":              "cities-of-sigmar",
    "collegiate-arcane":      "cities-of-sigmar",
    "devoted-of-sigmar":      "cities-of-sigmar",
    "daughters-of-khaine":    "daughters-of-khaine",
    "fyreslayers":            "fyreslayers",
    "idoneth-deepkin":        "idoneth-deepkin",
    "kharadron-overlords":    "kharadron-overlords",
    "lumineth-realm-lords":   "lumineth-realm-lords",
    "seraphon":               "seraphon",
    "sylvaneth":              "sylvaneth",
    "gloomspite-gitz":        "gloomspite-gitz",
    "ogor-mawtribes":         "ogor-mawtribes",
    "gutbusters":             "ogor-mawtribes",
    "beastclaw-raiders":      "ogor-mawtribes",
    "orruk-warclans":         "orruk-warclans",
    "ironjawz":               "orruk-warclans",
    "bonesplitterz":          "orruk-warclans",
    "kruleboyz":              "orruk-warclans",
    "beasts-of-chaos":        "beasts-of-chaos",
    "blades-of-khorne":       "blades-of-khorne",
    "disciples-of-tzeentch":  "disciples-of-tzeentch",
    "hedonites-of-slaanesh":  "hedonites-of-slaanesh",
    "maggotkin-of-nurgle":    "maggotkin-of-nurgle",
    "skaven":                 "skaven",
    "slaves-to-darkness":     "slaves-to-darkness",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """lowercase, hyphenize, strip non [a-z0-9-]."""
    n = name.lower()
    n = re.sub(r"['']", "", n)
    n = re.sub(r"[^a-z0-9]+", "-", n)
    return n.strip("-")


def _stem(n: str) -> str:
    """Crude stemmer: handle common English plural endings consistently in both directions.
    Goal: produce a key that's the same for both 'wolves'/'wolf', 'drones'/'drone', 'aelves'/'aelf'."""
    if len(n) <= 3:
        return n
    # 'ves' -> 'f' (wolves -> wolf, knives -> knife, aelves -> aelf)
    if n.endswith("ves") and len(n) > 4:
        return n[:-3] + "f"
    # 'ies' -> 'y'
    if n.endswith("ies") and len(n) > 4:
        return n[:-3] + "y"
    # 'sses'/'shes'/'ches'/'xes'/'zes' -> drop 'es' (real -es plurals)
    if n.endswith("ses") or n.endswith("shes") or n.endswith("ches") or n.endswith("xes") or n.endswith("zes"):
        return n[:-2]
    # plain 's' -> '' (covers 'drones' -> 'drone', 'orcs' -> 'orc')
    if n.endswith("s") and len(n) > 3:
        return n[:-1]
    return n


def normalize_for_match(name: str) -> str:
    """Aggressive normalisation for matching: lowercase, strip non-alnum, stem trailing plural markers."""
    n = re.sub(r"[^a-z0-9]+", "", name.lower())
    return _stem(n)


# Trailing modifier suffixes to strip when fuzzy-matching (DB unit names often
# include hardware/equipment variants that Lex doesn't enumerate as separate units).
TRAILING_STRIP_PATTERNS = [
    r"-pack$",
    r"-squad$",
    r"-with-.*$",
    r"-and-.*$",
    r"-on-.*$",
    r"^orruk-",  # 'orruk-warchanter' -> 'warchanter'
    r"^aos-",
]


def _per_token_stem(name: str) -> str:
    """Lowercase, split on non-alnum, stem each token, join (no separator)."""
    tokens = re.split(r"[^a-z0-9]+", name.lower())
    tokens = [_stem(t) for t in tokens if t]
    return "".join(tokens)


def variants_for_match(slug: str, name: str) -> list[str]:
    """Generate alternative normalized keys for matching."""
    out = []
    out.append(normalize_for_match(slug))
    out.append(normalize_for_match(name))
    out.append(_per_token_stem(slug))
    out.append(_per_token_stem(name))
    # strip trailing modifiers from slug
    s = slug
    for pat in TRAILING_STRIP_PATTERNS:
        s2 = re.sub(pat, "", s)
        if s2 and s2 != s:
            out.append(normalize_for_match(s2))
            out.append(_per_token_stem(s2))
            s = s2
    # also strip leading words from name (e.g., "Orruk Warchanter" -> "Warchanter")
    parts = name.split()
    for i in range(1, len(parts)):
        sub = " ".join(parts[i:])
        out.append(normalize_for_match(sub))
        out.append(_per_token_stem(sub))
    # comma-separated: take part before the comma (e.g., "Yndrasta, the Celestial Spear" -> "Yndrasta")
    if "," in name:
        first = name.split(",")[0]
        out.append(normalize_for_match(first))
        out.append(_per_token_stem(first))
    # strip trailing " of X" / " on X" / " with X" from name
    for pat in [r"\s+of\s+.+$", r"\s+on\s+.+$", r"\s+with\s+.+$", r"\s+and\s+.+$"]:
        trimmed = re.sub(pat, "", name, flags=re.IGNORECASE)
        if trimmed and trimmed != name:
            out.append(normalize_for_match(trimmed))
            out.append(_per_token_stem(trimmed))
    # dedup keeping order
    seen = set()
    uniq = []
    for v in out:
        if v and v not in seen:
            seen.add(v)
            uniq.append(v)
    return uniq


def derive_db_faction_candidates(lex_factions: list[str]) -> list[str]:
    """Given Lex 'factions' list, return prioritized DB faction-slug candidates."""
    out = []
    for f in lex_factions:
        s = slugify(f)
        mapped = LEX_FACTION_TO_DB.get(s)
        if mapped and mapped not in out:
            out.append(mapped)
        # also include the raw slug in case it matches a DB faction directly
        if s not in out:
            out.append(s)
    return out


def http_get_bytes(url: str) -> bytes | None:
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT, "Referer": REFERER},
            timeout=REQ_TIMEOUT,
        )
        if resp.status_code != 200:
            print(f"  ! HTTP {resp.status_code} {url}", flush=True)
            return None
        return resp.content
    except Exception as e:
        print(f"  ! ERR {e} {url}", flush=True)
        return None


def process_image(raw: bytes) -> tuple[bytes, tuple[int, int]] | None:
    """Validate (>=300x300, >=10KB), resize (<=600w), JPEG q85.
    Returns (jpeg_bytes, original_size) or None.
    """
    if len(raw) < MIN_BYTES:
        print(f"  ! image bytes too small: {len(raw)}", flush=True)
        return None
    try:
        im = Image.open(io.BytesIO(raw))
        im.load()
    except Exception as e:
        print(f"  ! PIL open fail: {e}", flush=True)
        return None
    w, h = im.size
    if w < MIN_DIM_PX or h < MIN_DIM_PX:
        print(f"  ! image too small: {w}x{h}", flush=True)
        return None
    orig_size = (w, h)
    # ensure RGB
    if im.mode in ("RGBA", "LA", "P"):
        bg = Image.new("RGB", im.size, (255, 255, 255))
        if im.mode == "P":
            im = im.convert("RGBA")
        bg.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
        im = bg
    elif im.mode != "RGB":
        im = im.convert("RGB")
    if w > MAX_WIDTH_PX:
        new_h = int(round(h * (MAX_WIDTH_PX / w)))
        im = im.resize((MAX_WIDTH_PX, new_h), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=JPEG_QUALITY, optimize=True)
    return buf.getvalue(), orig_size


def is_near_identical(existing_path: Path, new_bytes: bytes) -> bool:
    """Idempotency check: size delta < 5% AND first 256 bytes match."""
    if not existing_path.exists():
        return False
    existing = existing_path.read_bytes()
    if len(existing) == 0:
        return False
    delta = abs(len(existing) - len(new_bytes)) / max(len(existing), 1)
    if delta >= 0.05:
        return False
    if existing[:256] != new_bytes[:256]:
        return False
    return True


def backup_file(src: Path, faction_slug: str, slug: str, ext: str) -> None:
    dest_dir = BACKUP_DIR / faction_slug
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"{slug}{ext}"
    shutil.copy2(src, dest)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print(f"[*] Loading manifest: {MANIFEST_PATH}")
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    lex_units = manifest["units"]
    lex_with_img = {k: v for k, v in lex_units.items() if v.get("full_image_url")}
    print(f"[*] Lex units total: {len(lex_units)}  with image: {len(lex_with_img)}")

    # Build slug -> lex entry
    lex_by_slug = {slug: v for slug, v in lex_with_img.items()}
    # Build normalized-name -> lex entry (fallback). Use multiple keys per entry.
    lex_by_norm: dict[str, dict] = {}
    for slug, v in lex_with_img.items():
        title = v.get("title", slug)
        for key in variants_for_match(slug, title):
            lex_by_norm.setdefault(key, v)

    # Lazy import so the script can be linted outside container
    from app import create_app
    from app.extensions import db
    from app.models import Unit, Faction

    app = create_app()
    app.app_context().push()

    db_units = Unit.query.all()
    print(f"[*] DB units total: {len(db_units)}")

    matched_pairs: list[tuple[Unit, dict]] = []
    unmatched_db: list[Unit] = []
    skipped_no_image_in_db: list[Unit] = []

    for u in db_units:
        if not u.image_path:
            skipped_no_image_in_db.append(u)
            continue
        # match: try exact slug, then expanded normalized variants
        lex = lex_by_slug.get(u.slug)
        if not lex:
            for k in variants_for_match(u.slug, u.name):
                lex = lex_by_norm.get(k)
                if lex:
                    break
        if not lex:
            unmatched_db.append(u)
            continue
        # Confirm faction alignment: at least one lex faction maps to db faction slug
        db_faction_slug = u.faction.slug
        candidates = derive_db_faction_candidates(lex.get("factions", []))
        if db_faction_slug not in candidates:
            # Not a strong faction match; still allow if slug match was exact + Lex has no faction info
            # but skip if both have factions and they diverge to a *different* known faction.
            # Conservative: leave unmatched.
            unmatched_db.append(u)
            continue
        matched_pairs.append((u, lex))

    print(f"[*] Matched pairs: {len(matched_pairs)}")
    print(f"[*] Unmatched DB units (no Lex entry / faction mismatch): {len(unmatched_db)}")
    print(f"[*] DB units skipped (no existing image): {len(skipped_no_image_in_db)}")

    # Beastlord BEFORE snapshot
    bl_unit = Unit.query.filter_by(slug="beastlord").first()
    if bl_unit and bl_unit.image_path:
        bl_path = REPO_ROOT / "app" / "static" / "img" / bl_unit.image_path
        if bl_path.exists():
            from PIL import Image as _Im
            try:
                im = _Im.open(bl_path)
                print(f"[Beastlord BEFORE] {bl_unit.image_path}  size={im.size}  bytes={bl_path.stat().st_size}")
            except Exception as e:
                print(f"[Beastlord BEFORE] PIL fail: {e}")
        else:
            print(f"[Beastlord BEFORE] file missing: {bl_path}")

    # ---------------------------------------------------------------------
    # Download + replace
    # ---------------------------------------------------------------------
    replaced = 0
    skipped_idempotent = 0
    skipped_download_fail = 0
    skipped_validate_fail = 0
    db_changed = 0

    for idx, (u, lex) in enumerate(matched_pairs, 1):
        url = lex["full_image_url"]
        faction_slug = u.faction.slug

        # derive target path from DB image_path (preserve directory)
        # but ext will be .jpg after processing
        current_rel = u.image_path  # e.g. 'units/beasts-of-chaos/beastlord.jpg'
        current_path = REPO_ROOT / "app" / "static" / "img" / current_rel
        current_ext = Path(current_rel).suffix.lower()

        if idx % 25 == 0 or idx == 1:
            print(f"[{idx}/{len(matched_pairs)}] {u.slug} ({faction_slug}) <- {url}", flush=True)

        time.sleep(REQ_DELAY)
        raw = http_get_bytes(url)
        if raw is None:
            skipped_download_fail += 1
            continue

        processed = process_image(raw)
        if processed is None:
            skipped_validate_fail += 1
            continue
        new_bytes, orig_dims = processed

        # Determine target path: always .jpg after processing
        target_rel = f"units/{faction_slug}/{u.slug}.jpg"
        target_path = REPO_ROOT / "app" / "static" / "img" / target_rel
        target_path.parent.mkdir(parents=True, exist_ok=True)

        # Idempotency check against target (or current if same)
        check_path = target_path if target_path.exists() else current_path
        if is_near_identical(check_path, new_bytes):
            skipped_idempotent += 1
            continue

        # Backup existing
        if current_path.exists():
            backup_file(current_path, faction_slug, u.slug, current_ext)

        # If target differs from current (extension change), delete old
        if current_path.exists() and current_path.resolve() != target_path.resolve():
            try:
                current_path.unlink()
            except Exception as e:
                print(f"  ! could not delete old {current_path}: {e}")

        # Write target
        target_path.write_bytes(new_bytes)
        replaced += 1

        # Update DB if image_path changed
        if u.image_path != target_rel:
            u.image_path = target_rel
            db_changed += 1

        # set image_source_url to Lex url for provenance
        try:
            if hasattr(u, "image_source_url"):
                u.image_source_url = url
        except Exception:
            pass

    if db_changed > 0 or replaced > 0:
        db.session.commit()

    print()
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Lex manifest units with image : {len(lex_with_img)}")
    print(f"  DB units total                : {len(db_units)}")
    print(f"  Matched pairs                 : {len(matched_pairs)}")
    print(f"  Replaced (new art landed)     : {replaced}")
    print(f"  Skipped (already current)     : {skipped_idempotent}")
    print(f"  Skipped (download failed)     : {skipped_download_fail}")
    print(f"  Skipped (validation failed)   : {skipped_validate_fail}")
    print(f"  DB image_path updated         : {db_changed}")
    print(f"  Unmatched DB units            : {len(unmatched_db)}")
    print(f"  DB units skipped (no image)   : {len(skipped_no_image_in_db)}")

    # Beastlord AFTER
    if bl_unit:
        # re-query for fresh state
        bl_unit = Unit.query.filter_by(slug="beastlord").first()
        bl_path = REPO_ROOT / "app" / "static" / "img" / bl_unit.image_path
        if bl_path.exists():
            from PIL import Image as _Im
            try:
                im = _Im.open(bl_path)
                print(f"[Beastlord AFTER]  {bl_unit.image_path}  size={im.size}  bytes={bl_path.stat().st_size}")
            except Exception as e:
                print(f"[Beastlord AFTER] PIL fail: {e}")
        else:
            print(f"[Beastlord AFTER] file missing: {bl_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
