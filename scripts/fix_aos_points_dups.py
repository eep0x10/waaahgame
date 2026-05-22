"""
fix_aos_points_dups.py
======================
Step 1: Fix HTML-entity duplicate unit names.
Step 2: Fix points drift against April 2026 Battle Profiles.
Step 3: Re-run audit and compare counts.

Run inside Docker:
    docker exec waaahgame-app-1 python scripts/fix_aos_points_dups.py
"""

import sys
import os
import re
import html
import json
import shutil
import sqlite3
from collections import defaultdict
from datetime import date

sys.stdout.reconfigure(encoding="utf-8")

# ── Paths ──────────────────────────────────────────────────────────────────────

DB_PATH      = "instance/waaahgame.db"
DB_BAK_PATH  = "instance/waaahgame.db.bak-points-fix"
PDF_PATH     = "scripts/cache/aos_rules_extract/battle_profiles.clean.md"
AUDIT_PATH   = "scripts/cache/aos_units_audit.md"
AUDIT_OUT    = "scripts/cache/aos_units_audit.md"

# ── Backup ─────────────────────────────────────────────────────────────────────

print(f"Backing up DB → {DB_BAK_PATH}")
shutil.copy2(DB_PATH, DB_BAK_PATH)
print(f"Backup done: {DB_BAK_PATH}")
print()

# ── PDF parser (same approach as audit_full.py) ────────────────────────────────

def norm(s):
    s = str(s).strip()
    s = re.sub(r'\b([A-Z])\s([a-z])', lambda m: m.group(1) + m.group(2), s)
    for bad, good in [('‘', "'"), ('’', "'"), ('–', '-'), ('—', '-')]:
        s = s.replace(bad, good)
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.lower()
    parts = s.split()
    if parts and len(parts[-1]) > 4 and parts[-1].endswith('s') and not parts[-1].endswith('ss'):
        parts[-1] = parts[-1][:-1]
        s = ' '.join(parts)
    return s


FACTION_NAMES_UPPER = [
    "CITIES OF SIGMAR", "DAUGHTERS OF KHAINE", "FYRESLAYERS", "IDONETH DEEPKIN",
    "KHARADRON OVERLORDS", "LUMINETH REALM-LORDS", "SERAPHON", "STORMCAST ETERNALS",
    "SYLVANETH", "BLADES OF KHORNE", "DISCIPLES OF TZEENTCH", "HEDONITES OF SLAANESH",
    "HELSMITHS OF HASHUT", "MAGGOTKIN OF NURGLE", "SKAVEN", "SLAVES TO DARKNESS",
    "FLESH-EATER COURTS", "NIGHTHAUNT", "OSSIARCH BONEREAPERS", "SOULBLIGHT GRAVELORDS",
    "GLOOMSPITE GITZ", "IRONJAWZ", "KRULEBOYZ", "OGOR MAWTRIBES", "SONS OF BEHEMAT",
]
FACTION_DISPLAY = {
    "CITIES OF SIGMAR": "Cities of Sigmar",
    "DAUGHTERS OF KHAINE": "Daughters of Khaine",
    "FYRESLAYERS": "Fyreslayers",
    "IDONETH DEEPKIN": "Idoneth Deepkin",
    "KHARADRON OVERLORDS": "Kharadron Overlords",
    "LUMINETH REALM-LORDS": "Lumineth Realm-lords",
    "SERAPHON": "Seraphon",
    "STORMCAST ETERNALS": "Stormcast Eternals",
    "SYLVANETH": "Sylvaneth",
    "BLADES OF KHORNE": "Blades of Khorne",
    "DISCIPLES OF TZEENTCH": "Disciples of Tzeentch",
    "HEDONITES OF SLAANESH": "Hedonites of Slaanesh",
    "HELSMITHS OF HASHUT": "Helsmiths of Hashut",
    "MAGGOTKIN OF NURGLE": "Maggotkin of Nurgle",
    "SKAVEN": "Skaven",
    "SLAVES TO DARKNESS": "Slaves to Darkness",
    "FLESH-EATER COURTS": "Flesh-eater Courts",
    "NIGHTHAUNT": "Nighthaunt",
    "OSSIARCH BONEREAPERS": "Ossiarch Bonereapers",
    "SOULBLIGHT GRAVELORDS": "Soulblight Gravelords",
    "GLOOMSPITE GITZ": "Gloomspite Gitz",
    "IRONJAWZ": "Ironjawz",
    "KRULEBOYZ": "Kruleboyz",
    "OGOR MAWTRIBES": "Ogor Mawtribes",
    "SONS OF BEHEMAT": "Sons of Behemat",
}
FACTION_UPPER_SET = set(FACTION_NAMES_UPPER)

LEGENDS_START_RE = re.compile(r'^WARHAMMER\s+LEGENDS', re.IGNORECASE)
RENOWN_START_RE  = re.compile(r'^REGIMENTS\s+OF\s+RENOWN', re.IGNORECASE)
UNIVERSAL_MANIF  = re.compile(r'^UNIVERSAL\s+MANIFESTATION', re.IGNORECASE)
GRAND_ALLIANCE   = re.compile(r'^(ORDER|CHAOS|DEATH|DESTRUCTION)\s*$', re.IGNORECASE)

SKIP_RE = re.compile(
    r'^(HEROES\s+UNIT|UNITS\s+UNIT|TYPE\s+NAME|Battle Formation|Heroic Trait|Artefact of Power|'
    r'Spell Lore|Prayer Lore|Manifestation Lore|Faction Terrain|Mark of |Skyvessel Upgrade|'
    r'Great Endrinworks|UPDATED\s*$|NEW\s*$|---|\<\!--|^®$|APRIL 202|CONTENTS\s*$|'
    r'PRODUCED BY|With thanks|© Copyright|Permission|This is a work of|Pictures used|'
    r'Certain Citadel|Games Workshop Ltd|Nottingham|Unit 3,|Every Citadel|'
    r'Extracted \d+|^# )',
    re.IGNORECASE | re.UNICODE,
)
CONTINUATION_RE = re.compile(
    r'^(This (Hero|unit|shows|is a)|Any |regiment|eligible|battlepack\.|'
    r'Play for battles|General\'s Handbook|battles fought|Matched|'
    r'On the following|of Sigmar\.|All units in your|When we republish|'
    r'we have to stop|we still|This is where|use them|More recent|'
    r'You cannot include|Units in a Regiment|If an ability|'
    r'Alliances:|four Grand|then, an unfortunate|it is,|made indefinitely\.|'
    r'Warhammer Legends on|\d+ June 202|1 June|Legion of the First Prince|'
    r'of Renown\.|Cannot be|Unique|can only be|'
    r'\d+mm|\d+ × \d+|• )',
    re.IGNORECASE | re.UNICODE,
)

UNIT_RE = re.compile(
    r'^(?:[✹✸*]\s*)?'
    r'(.+?)'
    r'\s+(\d{1,2})\s+'
    r'(\d{2,4})'
    r'(?:\s*\([+-]\d+\))?'
    r'\s*(.*)',
    re.UNICODE,
)
NUM_FIRST_RE = re.compile(r'^(\d{1,2})\s+(\d{2,4})(?:\s*\([+-]\d+\))?\s*(.*)', re.UNICODE)


def clean_name(s):
    s = re.sub(r'\b([A-Z])\s([a-z])', lambda m: m.group(1) + m.group(2), s.strip())
    s = re.sub(r'^[✹✸*]\s*', '', s).strip()
    for bad, good in [(chr(0x2018), "'"), (chr(0x2019), "'"), (chr(0x2013), '-'), (chr(0x2014), '-')]:
        s = s.replace(bad, good)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+(?:Any |None\b|0-\d\b|This Hero\b|regiment\b).*$', '', s).strip()
    s = s.rstrip(',.').strip()
    return s


def extract_keywords(rest):
    kw_tokens = []
    m = re.match(r'^([A-Z][A-Za-z\s,]+?)(?:\s{2,}|\s+This\s|\s+\d{2,3}mm|\s+\d{3}|\s*$)', rest)
    if m:
        raw = m.group(1).strip().rstrip(',')
        for k in raw.split(','):
            k = k.strip()
            if k and re.match(r'^[A-Z][a-zA-Z]+(\s[A-Z][a-zA-Z]+)?(\s[A-Z][a-zA-Z]+)?$', k):
                kw_tokens.append(k)
    return kw_tokens


def parse_pdf(pdf_path):
    with open(pdf_path, encoding="utf-8") as f:
        pdf_lines = f.read().split("\n")

    regular_end = None
    legends_start = None
    for idx, line in enumerate(pdf_lines):
        if regular_end is None and RENOWN_START_RE.match(line.strip()) and idx > 2000:
            regular_end = idx
        if legends_start is None and re.match(r'^WARHAMMER\s+LEGENDS\s*[–—\-]', line.strip(), re.IGNORECASE):
            legends_start = idx
            break

    pdf_factions = defaultdict(list)

    def parse_section(line_range, is_legends_section=False):
        current_faction = None
        is_hero_table = False
        in_scourge = False
        pending_name = None
        i = line_range[0]
        end = line_range[1]

        while i < end:
            raw = pdf_lines[i]
            line = raw.strip()
            line_upper = line.upper()
            i += 1

            if not is_legends_section:
                if RENOWN_START_RE.match(line) and i > 2000:
                    break
                if UNIVERSAL_MANIF.match(line):
                    current_faction = None
                    continue

            if re.match(r'^WARHAMMER\s+LEGENDS\s*[–—\-]', line, re.IGNORECASE):
                current_faction = None
                pending_name = None
                continue

            if GRAND_ALLIANCE.match(line):
                current_faction = None
                pending_name = None
                continue

            if line == "Scourge of Ghyran" or re.match(r'^(?:[✹✸*]\s*)?Scourge of Ghyran', line):
                in_scourge = True
                pending_name = None
                continue
            if in_scourge:
                if line_upper in FACTION_UPPER_SET or re.match(r'^(?:LEGENDS\s+)?(?:HEROES|UNITS)\s+UNIT SIZE', line):
                    in_scourge = False
                else:
                    continue

            if line_upper in FACTION_UPPER_SET:
                current_faction = FACTION_DISPLAY[line_upper]
                in_scourge = False
                pending_name = None
                continue

            if current_faction is None:
                pending_name = None
                continue

            if re.match(r'^(?:LEGENDS\s+)?HEROES\s+UNIT SIZE', line):
                is_hero_table = True
                pending_name = None
                continue
            if re.match(r'^(?:LEGENDS\s+)?UNITS\s+UNIT SIZE', line):
                is_hero_table = False
                pending_name = None
                continue

            if SKIP_RE.match(line):
                pending_name = None
                continue

            if not line:
                pending_name = None
                continue

            if pending_name is not None:
                m = NUM_FIRST_RE.match(line)
                if m:
                    points = int(m.group(2))
                    rest = m.group(3).strip()
                    keywords = extract_keywords(rest) if not is_hero_table else ["HERO"]
                    j2 = i
                    while j2 < end and not pdf_lines[j2].strip():
                        j2 += 1
                    name_suffix = ""
                    if j2 < end:
                        nxt = pdf_lines[j2].strip()
                        nxt_clean = clean_name(nxt)
                        if (nxt and not re.search(r'\d', nxt)
                                and re.match(r'^[A-Za-z]', nxt)
                                and len(nxt.split()) <= 8
                                and nxt.upper() not in FACTION_UPPER_SET
                                and not SKIP_RE.match(nxt)
                                and not CONTINUATION_RE.match(nxt)
                                and not re.match(r'^(?:LEGENDS\s+)?(?:HEROES|UNITS)\s+UNIT SIZE', nxt)
                                and not re.match(r'^WARHAMMER\s+LEGENDS', nxt)
                                and nxt_clean):
                            name_suffix = " " + nxt_clean
                            i = j2 + 1
                    if points > 0:
                        raw_name = clean_name(pending_name) + name_suffix
                        final_name = re.sub(r'\s+', ' ', raw_name).strip()
                        pdf_factions[current_faction].append({
                            "name": final_name,
                            "points": points,
                            "is_legends": is_legends_section,
                            "is_scourge": in_scourge,
                        })
                    pending_name = None
                    continue
                else:
                    pending_name = None

            if CONTINUATION_RE.match(line):
                continue

            m = UNIT_RE.match(line)
            if m:
                name_raw = m.group(1)
                points = int(m.group(3))
                name = clean_name(name_raw)
                if points > 0 and name and len(name) >= 3:
                    pdf_factions[current_faction].append({
                        "name": name,
                        "points": points,
                        "is_legends": is_legends_section,
                        "is_scourge": in_scourge,
                    })
                continue

            if (re.match(r'^[✹✸*]?\s*[A-Z]', line) and
                    not re.search(r'\d', line) and
                    not SKIP_RE.match(line) and
                    not CONTINUATION_RE.match(line) and
                    len(line) > 3):
                j = i
                while j < end and not pdf_lines[j].strip():
                    j += 1
                if j < end and NUM_FIRST_RE.match(pdf_lines[j].strip()):
                    pending_name = line
                    continue

    parse_section((0, regular_end or len(pdf_lines)), is_legends_section=False)
    if legends_start:
        parse_section((legends_start, len(pdf_lines)), is_legends_section=True)

    return pdf_factions


# Build PDF map: (norm_faction, norm_unit_name) → points
# Only regular (non-legends, non-scourge) units; deduplicate scourge
def build_pdf_map(pdf_factions):
    pdf_map = {}  # (faction_display, norm_name) → points
    faction_units = {}  # faction_display → {norm_name: (name, points)}
    for faction_display, units in pdf_factions.items():
        seen = {}
        for u in units:
            if u["is_legends"]:
                continue
            n = norm(u["name"])
            if n not in seen:
                seen[n] = u
            else:
                # prefer non-scourge
                if u["is_scourge"] and not seen[n]["is_scourge"]:
                    pass
                elif not u["is_scourge"] and seen[n]["is_scourge"]:
                    seen[n] = u
        faction_units[faction_display] = seen
        for n, u in seen.items():
            pdf_map[(faction_display, n)] = u["points"]
    return pdf_map, faction_units


# ── Faction merge map for legacy DB factions ──────────────────────────────────
# Maps DB legacy faction name → list of candidate PDF factions to try
# If unit name resolves unambiguously to one PDF faction → safe to update
# If ambiguous (found in multiple PDF factions) → skip and log

FACTION_MERGE_MAP = {
    # Orruk Warclans split into Ironjawz and Kruleboyz in 4ed
    "Orruk Warclans": ["Ironjawz", "Kruleboyz"],
    # Tzeentch Arcanites merged into Disciples of Tzeentch
    "Tzeentch Arcanites": ["Disciples of Tzeentch"],
    # Slaanesh Sybarites merged into Hedonites of Slaanesh
    "Slaanesh Sybarites": ["Hedonites of Slaanesh"],
    # Bonesplitterz dissolved; heroes went to Ironjawz/Kruleboyz
    "Bonesplitterz": ["Ironjawz", "Kruleboyz"],
    # Deathlords merged into Ossiarch Bonereapers
    "Deathlords": ["Ossiarch Bonereapers", "Nighthaunt", "Soulblight Gravelords"],
    # Beasts of the Grave → Soulblight Gravelords (Revenant Draconith)
    "Beasts of the Grave": ["Soulblight Gravelords"],
    # Monsters of Chaos → Slaves to Darkness
    "Monsters of Chaos": ["Slaves to Darkness"],
    # Beasts of Chaos → no direct PDF equivalent (faction removed); all orphans
    "Beasts of Chaos": [],
}


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 1: HTML-entity dup fix
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("STEP 1: HTML-entity name cleanup")
print("=" * 60)

ENTITY_PATTERNS = ["&apos;", "&amp;", "&quot;", "&lt;", "&gt;", "&#39;", "&#34;"]

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Build WHERE clause
entity_clause = " OR ".join(f"name LIKE '%{e}%'" for e in ENTITY_PATTERNS)
cur.execute(f"SELECT id, name, slug, faction_id, points_cost, unit_category FROM units WHERE {entity_clause}")
entity_rows = cur.fetchall()
print(f"Found {len(entity_rows)} units with HTML entities in name\n")

merged_count  = 0
renamed_count = 0

try:
    for row in entity_rows:
        uid      = row["id"]
        raw_name = row["name"]
        decoded  = html.unescape(raw_name)
        faction_id = row["faction_id"]

        # Check for canonical sibling (same decoded name, same faction)
        cur.execute(
            "SELECT id, name, slug, points_cost, unit_category FROM units WHERE name=? AND faction_id=? AND id!=?",
            (decoded, faction_id, uid),
        )
        sibling = cur.fetchone()

        if sibling:
            # ── Merge: repoint FKs → canonical, then delete entity row ──
            canonical_id = sibling["id"]

            # Check / repoint army_units
            cur.execute("SELECT COUNT(*) FROM army_units WHERE unit_id=?", (uid,))
            au_count = cur.fetchone()[0]
            if au_count:
                cur.execute("UPDATE army_units SET unit_id=? WHERE unit_id=?", (canonical_id, uid))

            # Check / repoint unit_versions
            cur.execute("SELECT COUNT(*) FROM unit_versions WHERE unit_id=?", (uid,))
            uv_count = cur.fetchone()[0]
            if uv_count:
                cur.execute("UPDATE unit_versions SET unit_id=? WHERE unit_id=?", (canonical_id, uid))

            # Delete entity row
            cur.execute("DELETE FROM units WHERE id=?", (uid,))
            merged_count += 1
            print(f"  entity dup merged: {raw_name!r} → {decoded!r} (canonical id={canonical_id}, repointed army_units={au_count}, unit_versions={uv_count})")
        else:
            # ── Rename: just update name (and slug) ──
            new_slug = re.sub(r"[^a-z0-9]+", "-", decoded.lower()).strip("-")
            # Ensure slug uniqueness
            base_slug = new_slug
            suffix = 0
            while True:
                cur.execute("SELECT id FROM units WHERE slug=? AND id!=?", (new_slug, uid))
                if not cur.fetchone():
                    break
                suffix += 1
                new_slug = f"{base_slug}-{suffix}"

            cur.execute("UPDATE units SET name=?, slug=? WHERE id=?", (decoded, new_slug, uid))
            renamed_count += 1
            print(f"  entity name fixed: {raw_name!r} → {decoded!r} (slug: {new_slug!r})")

    conn.commit()
    print(f"\nStep 1 done: {merged_count} merged, {renamed_count} renamed\n")

except Exception as e:
    conn.rollback()
    print(f"ERROR in Step 1, rolled back: {e}")
    conn.close()
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 2: Points drift fix
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("STEP 2: Points drift fix")
print("=" * 60)

print("Parsing PDF...")
pdf_factions_data = parse_pdf(PDF_PATH)
pdf_map, faction_unit_map = build_pdf_map(pdf_factions_data)
print(f"PDF map: {len(pdf_map)} unit entries across {len(faction_unit_map)} factions\n")

# Load all AoS units from DB with their faction name
# (only AoS factions — game_system code 'aos4')
cur.execute("""
    SELECT u.id, u.name, u.points_cost, u.unit_category,
           f.name as faction_name, f.id as faction_id
    FROM units u
    JOIN factions f ON u.faction_id = f.id
    JOIN game_systems gs ON f.game_system_id = gs.id
    WHERE gs.code = 'aos4'
""")
db_units = cur.fetchall()
print(f"DB AoS units: {len(db_units)}\n")

updated_count    = 0
skip_no_pdf      = 0
skip_ambiguous   = 0
ambiguous_cases  = []

sample_updates = []  # collect first 5 for report

try:
    for row in db_units:
        uid          = row["id"]
        db_name      = row["name"]
        db_pts       = row["points_cost"]
        db_faction   = row["faction_name"]
        unit_cat     = row["unit_category"]

        # Decode any remaining entity names (post Step 1 rename)
        db_name_clean = html.unescape(db_name)

        n = norm(db_name_clean)

        # ── Try direct faction match ──────────────────────────────────────
        # PDF faction display names vs DB faction names may differ slightly
        # Build a normalised lookup: norm(pdf_faction) → pdf_faction_display
        pdf_faction_norm_map = {norm(fn): fn for fn in faction_unit_map.keys()}
        db_faction_norm = norm(db_faction)

        pdf_faction = pdf_faction_norm_map.get(db_faction_norm)
        pdf_pts = None

        if pdf_faction:
            fn_units = faction_unit_map[pdf_faction]
            if n in fn_units:
                pdf_pts = fn_units[n]["points"]
        else:
            # ── Try faction merge map ─────────────────────────────────────
            candidate_factions = FACTION_MERGE_MAP.get(db_faction, None)
            if candidate_factions is None:
                # Unknown legacy faction — skip silently
                skip_no_pdf += 1
                continue
            if len(candidate_factions) == 0:
                # Beasts of Chaos — no PDF equivalent
                skip_no_pdf += 1
                continue

            matches = []
            for cf in candidate_factions:
                cf_units = faction_unit_map.get(cf, {})
                if n in cf_units:
                    matches.append((cf, cf_units[n]["points"]))

            if len(matches) == 0:
                skip_no_pdf += 1
                continue
            elif len(matches) == 1:
                pdf_pts = matches[0][1]
                pdf_faction = matches[0][0]
            else:
                # Ambiguous: same unit name in multiple PDF factions
                skip_ambiguous += 1
                ambiguous_cases.append({
                    "db_faction": db_faction,
                    "unit": db_name_clean,
                    "matches": matches,
                })
                continue

        # ── Update if drift found ─────────────────────────────────────────
        if pdf_pts is not None and db_pts != pdf_pts:
            cur.execute("UPDATE units SET points_cost=? WHERE id=?", (pdf_pts, uid))
            updated_count += 1
            msg = f"  updated: {db_faction} / {db_name_clean}: {db_pts} → {pdf_pts}"
            print(msg)
            if len(sample_updates) < 5:
                sample_updates.append({
                    "faction": db_faction,
                    "unit": db_name_clean,
                    "old": db_pts,
                    "new": pdf_pts,
                })
        elif pdf_pts is None:
            skip_no_pdf += 1

    conn.commit()
    print(f"\nStep 2 done:")
    print(f"  updated:                  {updated_count}")
    print(f"  skipped (no PDF match):   {skip_no_pdf}")
    print(f"  skipped (ambiguous):      {skip_ambiguous}")
    if ambiguous_cases:
        print(f"\n  Ambiguous faction cases:")
        for ac in ambiguous_cases:
            print(f"    {ac['db_faction']} / {ac['unit']!r} → {ac['matches']}")

except Exception as e:
    conn.rollback()
    print(f"ERROR in Step 2, rolled back: {e}")
    conn.close()
    sys.exit(1)

conn.close()
print()


# ═══════════════════════════════════════════════════════════════════════════════
# STEP 3: Re-run audit (inline, same logic as audit_full.py)
# ═══════════════════════════════════════════════════════════════════════════════

print("=" * 60)
print("STEP 3: Re-running audit")
print("=" * 60)

# Read old audit summary for comparison
old_pts_drift    = 118  # from original audit
old_orphan_count = 337

# Load fresh DB state
conn2 = sqlite3.connect(DB_PATH)
conn2.row_factory = sqlite3.Row
cur2 = conn2.cursor()

cur2.execute("""
    SELECT u.name, u.points_cost, u.unit_category,
           f.name as faction
    FROM units u
    JOIN factions f ON u.faction_id = f.id
    JOIN game_systems gs ON f.game_system_id = gs.id
    WHERE gs.code = 'aos4'
""")
fresh_units = cur2.fetchall()
conn2.close()

db_factions_fresh = defaultdict(list)
for u in fresh_units:
    db_factions_fresh[u["faction"]].append({
        "name": u["name"],
        "points": u["points_cost"],
        "unit_category": u["unit_category"],
    })

# Build fresh PDF map (already parsed above)
def build_db_unit_map_norm(faction_units):
    result = {}
    for u in faction_units:
        result[norm(html.unescape(u["name"]))] = u
    return result

pdf_faction_norm_map = {norm(fn): fn for fn in faction_unit_map.keys()}

total_pts_drift_new  = 0
total_orphans_new    = 0
total_missing_new    = 0

faction_results_new = {}
unmatched_db_new = []

for pdf_fn in sorted(faction_unit_map.keys()):
    fn_pdf_units = faction_unit_map[pdf_fn]
    db_fn_norm = None
    for n_db, db_fn_candidate in {norm(fn): fn for fn in db_factions_fresh.keys()}.items():
        if norm(pdf_fn) == n_db:
            db_fn_norm = db_fn_candidate
            break

    db_unit_map = build_db_unit_map_norm(db_factions_fresh.get(db_fn_norm, []))

    missing   = [u for n, u in fn_pdf_units.items() if n not in db_unit_map]
    orphans   = [u for n, u in db_unit_map.items() if n not in fn_pdf_units]
    pts_drift = []
    for n, pdf_u in fn_pdf_units.items():
        if n in db_unit_map:
            db_u = db_unit_map[n]
            if pdf_u["points"] != db_u["points"]:
                pts_drift.append({
                    "name": pdf_u["name"],
                    "pdf_pts": pdf_u["points"],
                    "db_pts":  db_u["points"],
                })

    total_pts_drift_new  += len(pts_drift)
    total_orphans_new    += len(orphans)
    total_missing_new    += len(missing)

# Also count DB-only faction units as orphans (unchanged — we don't touch those)
all_pdf_db_fns = {norm(fn) for fn in faction_unit_map.keys()}
for db_fn, units in db_factions_fresh.items():
    if norm(db_fn) not in all_pdf_db_fns:
        total_orphans_new += len(units)

print(f"\nAudit comparison:")
print(f"  Points drift:  {old_pts_drift} → {total_pts_drift_new}  (delta: {old_pts_drift - total_pts_drift_new:+d})")
print(f"  Orphan count:  {old_orphan_count} → {total_orphans_new}  (delta: {old_orphan_count - total_orphans_new:+d})")
print(f"  Missing count: (was 68) now ~{total_missing_new}")
print()

# ── Final summary ──────────────────────────────────────────────────────────────

print("=" * 60)
print("SUMMARY")
print("=" * 60)
print(f"DB backup:         {DB_BAK_PATH}")
print()
print(f"Step 1 (HTML dup):")
print(f"  Merged:  {merged_count}")
print(f"  Renamed: {renamed_count}")
print()
print(f"Step 2 (Points):")
print(f"  Updated:              {updated_count}")
print(f"  Skipped (no PDF):     {skip_no_pdf}")
print(f"  Skipped (ambiguous):  {skip_ambiguous}")
print()
print(f"Step 3 (Post-fix audit):")
print(f"  Points drift:  {old_pts_drift} → {total_pts_drift_new}")
print(f"  Orphans:       {old_orphan_count} → {total_orphans_new}")
print(f"  Missing:       68 → {total_missing_new}")
print()
if sample_updates:
    print(f"Sample updates (first {len(sample_updates)}):")
    for su in sample_updates:
        print(f"  {su['faction']} / {su['unit']}: {su['old']} → {su['new']}")
print()
if ambiguous_cases:
    print(f"Ambiguous faction cases needing user decision ({len(ambiguous_cases)}):")
    for ac in ambiguous_cases:
        print(f"  {ac['db_faction']} / {ac['unit']!r}")
        for cf, pts in ac['matches']:
            print(f"    {cf}: {pts} pts")
print()
print("Done.")
