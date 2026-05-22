"""
purge_aos_orphans.py — Delete AoS orphan units not in the April 2026 Battle Profiles PDF.

Idempotent. Safe to re-run.

Steps:
  0. Backup DB.
  1. Build canonical (faction, unit_name) set from battle_profiles.clean.md.
     Also includes Faction Terrain / Manifestation lore entries as valid manifestation units.
     Also includes universal manifestation lore entries.
  2. Identify deletion candidates (with legacy-faction repointing logic).
  3. Check FK references (army_units, unit_versions).
  4. Execute in single transaction:
       a. Repoint legacy → 4ed faction
       b. Merge duplicates (repoint FK → canonical sibling, delete legacy row)
       c. Delete squatted / orphan units (cascade FK rows first)
       d. Delete now-empty legacy factions
  5. Print summary.
"""

import sys
import re
import shutil
import sqlite3
from collections import defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# ─── PATHS ────────────────────────────────────────────────────────────────────

DB_PATH           = Path("/app/instance/waaahgame.db")
BACKUP_PATH       = DB_PATH.with_suffix(".db.bak-orphan-purge")
PDF_PATH          = Path("/app/scripts/cache/aos_rules_extract/battle_profiles.clean.md")
CORE_RULES_PATH   = Path("/app/scripts/cache/aos_rules_extract/core_rules.clean.md")
GHB_PATH          = Path("/app/scripts/cache/aos_rules_extract/ghb.clean.md")

# ─── LEGACY FACTION MAP ───────────────────────────────────────────────────────

LEGACY_FACTION_MAP = {
    "Orruk Warclans":       ["Ironjawz", "Kruleboyz"],
    "Tzeentch Arcanites":   ["Disciples of Tzeentch"],
    "Slaanesh Sybarites":   ["Hedonites of Slaanesh"],
    "Deathlords":           ["Soulblight Gravelords", "Ossiarch Bonereapers"],
    "Beasts of the Grave":  ["Soulblight Gravelords"],
    "Beasts of Chaos":      [],      # squatted
    "Monsters of Chaos":    [],      # squatted
    "Bonesplitterz":        [],      # squatted
}

# ─── PDF KNOWN FACTIONS ───────────────────────────────────────────────────────

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

# ─── NORMALIZATION ────────────────────────────────────────────────────────────

def norm(s):
    s = str(s).strip()
    # Fix OCR mid-word space: "F reeguild" -> "Freeguild"
    s = re.sub(r'\b([A-Z])\s([a-z])', lambda m: m.group(1) + m.group(2), s)
    # Normalise smart quotes/apostrophes
    for bad, good in [('‘', "'"), ('’', "'"), ('–', '-'), ('—', '-')]:
        s = s.replace(bad, good)
    # HTML entities
    s = s.replace('&apos;', "'").replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
    # Normalise whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    s = s.lower()
    # Strip trailing 's' (plural normalisation matching audit_full.py)
    parts = s.split()
    if parts and len(parts[-1]) > 4 and parts[-1].endswith('s') and not parts[-1].endswith('ss'):
        parts[-1] = parts[-1][:-1]
        s = ' '.join(parts)
    return s

# ─── PDF PARSE HELPERS ────────────────────────────────────────────────────────

LEGENDS_START_RE = re.compile(r'^WARHAMMER\s+LEGENDS', re.IGNORECASE)
RENOWN_START_RE  = re.compile(r'^REGIMENTS\s+OF\s+RENOWN', re.IGNORECASE)
UNIVERSAL_MANIF  = re.compile(r'^UNIVERSAL\s+MANIFESTATION', re.IGNORECASE)
GRAND_ALLIANCE   = re.compile(r'^(ORDER|CHAOS|DEATH|DESTRUCTION)\s*$', re.IGNORECASE)

SKIP_RE = re.compile(
    r'^(HEROES\s+UNIT|UNITS\s+UNIT|TYPE\s+NAME|Battle Formation|Heroic Trait|Artefact of Power|'
    r'Spell Lore|Prayer Lore|Manifestation Lore|Mark of |Skyvessel Upgrade|'
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

NUM_FIRST_RE = re.compile(
    r'^(\d{1,2})\s+(\d{2,4})(?:\s*\([+-]\d+\))?\s*(.*)',
    re.UNICODE,
)

def clean_name(s):
    s = re.sub(r'\b([A-Z])\s([a-z])', lambda m: m.group(1) + m.group(2), s.strip())
    s = re.sub(r'^[✹✸*]\s*', '', s).strip()
    for bad, good in [('‘', "'"), ('’', "'"), ('–', '-'), ('—', '-')]:
        s = s.replace(bad, good)
    s = re.sub(r'\s+', ' ', s).strip()
    s = re.sub(r'\s+(?:Any |None\b|0-\d\b|This Hero\b|regiment\b).*$', '', s).strip()
    s = s.rstrip(',.').strip()
    return s

# ─── STEP 1: BUILD CANONICAL PDF SET ─────────────────────────────────────────

def parse_pdf_units(pdf_path):
    """Parse battle_profiles.clean.md — returns dict faction -> set of norm(name)."""
    with open(pdf_path, encoding="utf-8") as f:
        pdf_lines = f.read().split("\n")

    # Find section boundaries
    regular_end = None
    legends_start = None
    for idx, line in enumerate(pdf_lines):
        if regular_end is None and RENOWN_START_RE.match(line.strip()) and idx > 2000:
            regular_end = idx
        if legends_start is None and re.match(r'^WARHAMMER\s+LEGENDS\s*[–—\-]', line.strip(), re.IGNORECASE):
            legends_start = idx
            break

    pdf_factions = defaultdict(set)  # faction -> set of norm(name)

    def parse_section(line_range, is_legends=False):
        current_faction = None
        is_hero_table   = False
        in_scourge      = False
        pending_name    = None
        i   = line_range[0]
        end = line_range[1]

        while i < end:
            raw  = pdf_lines[i]
            line = raw.strip()
            line_upper = line.upper()
            i += 1

            if not is_legends:
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
                        pdf_factions[current_faction].add(norm(final_name))
                    pending_name = None
                    continue
                else:
                    pending_name = None

            if CONTINUATION_RE.match(line):
                continue

            m = UNIT_RE.match(line)
            if m:
                name_raw = m.group(1)
                points   = int(m.group(3))
                name     = clean_name(name_raw)
                if points > 0 and name and len(name) >= 3:
                    pdf_factions[current_faction].add(norm(name))
                continue

            if (re.match(r'^[✹✸*]?\s*[A-Z]', line)
                    and not re.search(r'\d', line)
                    and not SKIP_RE.match(line)
                    and not CONTINUATION_RE.match(line)
                    and len(line) > 3):
                j = i
                while j < end and not pdf_lines[j].strip():
                    j += 1
                if j < end:
                    next_stripped = pdf_lines[j].strip()
                    if NUM_FIRST_RE.match(next_stripped):
                        pending_name = line
                        continue

    parse_section((0, regular_end or len(pdf_lines)), is_legends=False)
    if legends_start:
        parse_section((legends_start, len(pdf_lines)), is_legends=True)

    return pdf_factions


def parse_faction_terrain_manifestations(pdf_path):
    """
    Parse Faction Terrain lines from the PDF (e.g. 'Faction Terrain Skull Altar 0 ...').
    Also parses Universal Manifestation Lore section.
    Returns a set of norm(name) — faction-agnostic (manifestations belong to any faction).
    """
    manif_names = set()
    with open(pdf_path, encoding="utf-8") as f:
        content = f.read()

    # Faction Terrain lines: "Faction Terrain <name> <pts> ..."
    for m in re.finditer(r'^✹?\s*Faction Terrain\s+(.+?)(?:\s+\d+|\s*$)', content, re.MULTILINE):
        name = m.group(1).strip().rstrip('0123456789 ')
        # Clean trailing numbers/whitespace
        name = re.sub(r'\s+\d+.*$', '', name).strip()
        if name:
            manif_names.add(norm(name))

    # Universal Manifestation Lore section lines (name only, no points parsing needed)
    in_universal = False
    for line in content.split('\n'):
        stripped = line.strip()
        if UNIVERSAL_MANIF.match(stripped):
            in_universal = True
            continue
        if in_universal:
            if stripped.startswith('---') or stripped.startswith('REGIMENTS') or stripped.startswith('WARHAMMER'):
                in_universal = False
                continue
            # Skip header / meta lines
            if not stripped or stripped in ('UPDATED', 'NEW') or stripped.startswith('NAME'):
                continue
            # Extract name: "✹ Krondspine Incarnate 0 (-20)" -> "Krondspine Incarnate"
            clean = re.sub(r'^[✹✸*]\s*', '', stripped)
            name = re.sub(r'\s+\d+.*$', '', clean).strip()
            if name and len(name) > 2:
                manif_names.add(norm(name))

    return manif_names


# ─── BUILD CANONICAL SET ──────────────────────────────────────────────────────

print("=== STEP 1: Building canonical PDF set ===")
pdf_factions = parse_pdf_units(PDF_PATH)
manif_set    = parse_faction_terrain_manifestations(PDF_PATH)

# Build flat canonical set (faction, norm_name) for regular units
pdf_canonical = set()   # set of (faction_display, norm_name)
pdf_all_names = set()   # all norm names across all factions (for cross-faction lookups)
for faction, names in pdf_factions.items():
    for n in names:
        pdf_canonical.add((faction, n))
        pdf_all_names.add(n)

print(f"  PDF factions: {len(pdf_factions)}")
print(f"  PDF regular units (norm, deduped): {len(pdf_all_names)}")
print(f"  Faction terrain / manifestation entries: {len(manif_set)}")

# ─── STEP 2: OPEN DB ─────────────────────────────────────────────────────────

print("\n=== STEP 0: Backup ===")
shutil.copy2(DB_PATH, BACKUP_PATH)
print(f"  Backup: {BACKUP_PATH}")

conn = sqlite3.connect(DB_PATH)
conn.execute("PRAGMA foreign_keys = OFF")  # We handle FKs manually
cur = conn.cursor()

# Load AoS game system id
cur.execute("SELECT id FROM game_systems WHERE name LIKE '%Sigmar%'")
row = cur.fetchone()
if not row:
    print("ERROR: AoS game system not found!")
    sys.exit(1)
AOS_GS_ID = row[0]
print(f"\nAoS game system id: {AOS_GS_ID}")

# Load all AoS units
cur.execute("""
    SELECT u.id, u.name, u.slug, u.unit_category, u.points_cost, f.name, f.id
    FROM units u
    JOIN factions f ON u.faction_id = f.id
    WHERE f.game_system_id = ?
    ORDER BY f.name, u.name
""", (AOS_GS_ID,))
all_aos_units = cur.fetchall()
# Columns: id, name, slug, unit_category, points_cost, faction_name, faction_id
print(f"Total AoS units in DB: {len(all_aos_units)}")

# Load faction id map: name -> id
cur.execute("SELECT id, name FROM factions WHERE game_system_id = ?", (AOS_GS_ID,))
faction_rows = cur.fetchall()
faction_id_map  = {r[1]: r[0] for r in faction_rows}   # name -> id
faction_name_map = {r[0]: r[1] for r in faction_rows}  # id -> name

# ─── STEP 2: IDENTIFY WHAT TO DO WITH EACH UNIT ──────────────────────────────

print("\n=== STEP 2: Classifying units ===")

to_repoint  = []  # (unit_id, new_faction_name) — legacy → 4ed, no conflict
to_merge    = []  # (unit_id, canonical_sibling_id) — legacy → existing canonical sibling
to_delete   = []  # unit_id — squatted or no 4ed equivalent
to_keep     = []  # unit_id — in PDF (or manifestation), keep as-is
to_skip_fk  = []  # (unit_id, reason) — ambiguous FK situation

for row in all_aos_units:
    uid, uname, slug, ucat, upts, fname, fid = row
    n = norm(uname)

    # ── Squatted legacy faction (no 4ed equivalent) ──
    # Check this FIRST before category checks: squatted factions delete everything
    # except manifestations (faction-independent supplemental content).
    if fname in LEGACY_FACTION_MAP and not LEGACY_FACTION_MAP[fname]:
        if ucat == 'manifestation':
            to_keep.append(uid)
        else:
            to_delete.append(uid)
        continue

    # ── Manifestation category ──
    # Manifestations are kept (supplemental, faction-independent, always keep)
    if ucat == 'manifestation':
        to_keep.append(uid)
        continue

    # ── Legends category ──
    # If already tagged legends and it's in the PDF legends section → keep
    # If tagged legends and NOT in PDF at all → delete (squatted)
    if ucat == 'legends':
        # Check if it appears in any PDF faction (including legends sections)
        if n in pdf_all_names:
            to_keep.append(uid)
        else:
            to_delete.append(uid)
        continue

    # ── Incomplete category ──
    # Incomplete units (missing data) — delete if not in PDF
    if ucat == 'incomplete':
        # Check PDF (any faction)
        if n in pdf_all_names:
            to_keep.append(uid)
        else:
            to_delete.append(uid)
        continue

    # ── Regular category ──
    # Check if it's in a legacy faction with 4ed targets
    if fname in LEGACY_FACTION_MAP:
        target_factions = LEGACY_FACTION_MAP[fname]
        # (squatted case already handled above — target_factions is non-empty here)
        if not target_factions:
            to_delete.append(uid)
            continue

        # Check if the unit exists in any of the target 4ed factions
        found_in = None
        for tf in target_factions:
            if (tf, n) in pdf_canonical:
                found_in = tf
                break
        # Also check norm(name) in pdf_all_names if faction-agnostic match needed
        if found_in is None:
            # Not in specific target faction PDF entries; check all PDF names
            if n not in pdf_all_names:
                to_delete.append(uid)
                continue

        if found_in is None:
            # Name exists somewhere in PDF but not in specific target factions
            # Find which PDF faction it belongs to
            for (pf, pn) in pdf_canonical:
                if pn == n:
                    found_in = pf
                    break

        # Now: unit should be repointed to found_in faction
        # Check if canonical sibling already exists in target faction in DB
        target_fid = faction_id_map.get(found_in)
        if target_fid is None:
            # Target faction doesn't exist in DB yet — just repoint faction name
            # (faction will need to be created — log as skip for now)
            to_skip_fk.append((uid, f"target faction '{found_in}' not in DB"))
            continue

        # Check if a sibling (same norm name) already exists in target faction
        cur.execute(
            "SELECT id FROM units WHERE faction_id = ? AND id != ?",
            (target_fid, uid)
        )
        siblings = [r[0] for r in cur.fetchall()]
        # Find sibling with matching norm name
        canonical_sibling = None
        for sib_id in siblings:
            cur.execute("SELECT name FROM units WHERE id = ?", (sib_id,))
            sib_name = cur.fetchone()[0]
            if norm(sib_name) == n:
                canonical_sibling = sib_id
                break

        if canonical_sibling:
            # Merge: repoint FKs to canonical sibling, delete legacy row
            to_merge.append((uid, canonical_sibling))
        else:
            # Repoint: change faction_id to target faction
            to_repoint.append((uid, found_in))

    else:
        # Non-legacy faction — check PDF
        # The faction name in DB should match PDF faction name (modulo case/normalisation)
        # Check exact faction match first
        in_faction = (fname, n) in pdf_canonical
        if not in_faction:
            # Check case-insensitive faction match
            for (pf, pn) in pdf_canonical:
                if pn == n and norm(pf) == norm(fname):
                    in_faction = True
                    break
        if in_faction:
            to_keep.append(uid)
        else:
            to_delete.append(uid)

print(f"  to_keep:    {len(to_keep)}")
print(f"  to_repoint: {len(to_repoint)}")
print(f"  to_merge:   {len(to_merge)}")
print(f"  to_delete:  {len(to_delete)}")
print(f"  to_skip_fk: {len(to_skip_fk)}")

# ─── STEP 3: FK CHECK ─────────────────────────────────────────────────────────

print("\n=== STEP 3: FK check ===")

delete_set = set(to_delete) | set(u for u, _ in to_merge)
merge_map  = {u: c for u, c in to_merge}  # legacy_id -> canonical_id

# army_units.unit_id
cur.execute("SELECT id, unit_id FROM army_units")
army_unit_refs = [(r[0], r[1]) for r in cur.fetchall()]
au_to_repoint  = [(auid, merge_map[unit_id]) for auid, unit_id in army_unit_refs if unit_id in merge_map]
au_to_delete   = [auid for auid, unit_id in army_unit_refs if unit_id in delete_set and unit_id not in merge_map]

# unit_versions.unit_id
cur.execute("SELECT id, unit_id FROM unit_versions")
uv_refs = [(r[0], r[1]) for r in cur.fetchall()]
uv_to_repoint = [(uvid, merge_map[uid]) for uvid, uid in uv_refs if uid in merge_map]
uv_to_delete  = [uvid for uvid, uid in uv_refs if uid in delete_set and uid not in merge_map]

print(f"  army_units: {len(au_to_repoint)} to repoint FK, {len(au_to_delete)} to delete")
print(f"  unit_versions: {len(uv_to_repoint)} to repoint FK, {len(uv_to_delete)} to delete")

# ─── STEP 4: EXECUTE ─────────────────────────────────────────────────────────

print("\n=== STEP 4: Execute ===")

try:
    conn.execute("BEGIN")

    # 4a. Repoint legacy → 4ed faction
    repoint_count = 0
    repoint_by_faction = defaultdict(list)
    for uid, new_fname in to_repoint:
        new_fid = faction_id_map[new_fname]
        cur.execute("SELECT name, faction_id FROM units WHERE id = ?", (uid,))
        r = cur.fetchone()
        old_fname = faction_name_map.get(r[1], '?')
        print(f"  [REPOINT] id={uid} '{r[0]}': {old_fname} → {new_fname}")
        cur.execute("UPDATE units SET faction_id = ? WHERE id = ?", (new_fid, uid))
        repoint_count += 1
        repoint_by_faction[new_fname].append(r[0])

    # 4b. Merge duplicates (repoint FK + delete legacy row)
    merge_count = 0
    for uid, canonical_id in to_merge:
        cur.execute("SELECT name, faction_id FROM units WHERE id = ?", (uid,))
        r = cur.fetchone()
        old_fname = faction_name_map.get(r[1], '?')
        cur.execute("SELECT name FROM units WHERE id = ?", (canonical_id,))
        can_r = cur.fetchone()
        print(f"  [MERGE] id={uid} '{r[0]}' ({old_fname}) → canonical id={canonical_id} '{can_r[0]}'")
        # Repoint army_units FK
        for auid, new_uid in au_to_repoint:
            if new_uid == canonical_id:
                cur.execute("UPDATE army_units SET unit_id = ? WHERE id = ?", (canonical_id, auid))
                print(f"    [FK-REPOINT] army_units id={auid} → unit {canonical_id}")
        # Repoint unit_versions FK (skip if duplicate uq_unit_ruleset constraint)
        for uvid, new_uid in uv_to_repoint:
            if new_uid == canonical_id:
                # Check if canonical already has a version for same ruleset
                cur.execute("SELECT ruleset_id FROM unit_versions WHERE id = ?", (uvid,))
                rs_id = cur.fetchone()[0]
                cur.execute("SELECT id FROM unit_versions WHERE unit_id = ? AND ruleset_id = ?",
                            (canonical_id, rs_id))
                conflict = cur.fetchone()
                if conflict:
                    print(f"    [FK-DELETE] unit_versions id={uvid} (conflict with canonical)")
                    cur.execute("DELETE FROM unit_versions WHERE id = ?", (uvid,))
                else:
                    cur.execute("UPDATE unit_versions SET unit_id = ? WHERE id = ?", (canonical_id, uvid))
                    print(f"    [FK-REPOINT] unit_versions id={uvid} → unit {canonical_id}")
        # Delete legacy row
        cur.execute("DELETE FROM units WHERE id = ?", (uid,))
        merge_count += 1

    # 4c. Delete squatted units
    delete_count  = 0
    fk_rows_total = 0
    for uid in to_delete:
        cur.execute("SELECT name, faction_id FROM units WHERE id = ?", (uid,))
        r = cur.fetchone()
        if not r:
            continue  # already deleted
        uname  = r[0]
        fname2 = faction_name_map.get(r[1], '?')
        print(f"  [DELETE] id={uid} '{uname}' ({fname2})")

        # Delete army_units referencing this unit
        for auid in au_to_delete:
            cur.execute("DELETE FROM army_units WHERE id = ? AND unit_id = ?", (auid, uid))
            print(f"    [CASCADE-FK] army_units id={auid}")
            fk_rows_total += 1

        # Delete unit_versions referencing this unit
        for uvid in uv_to_delete:
            cur.execute("DELETE FROM unit_versions WHERE id = ? AND unit_id = ?", (uvid, uid))
            print(f"    [CASCADE-FK] unit_versions id={uvid}")
            fk_rows_total += 1

        cur.execute("DELETE FROM units WHERE id = ?", (uid,))
        delete_count += 1

    # 4d. Delete now-empty legacy factions (and factions that are now empty)
    deleted_factions = []
    for legacy_fname in LEGACY_FACTION_MAP:
        fid = faction_id_map.get(legacy_fname)
        if fid is None:
            continue
        cur.execute("SELECT COUNT(*) FROM units WHERE faction_id = ?", (fid,))
        remaining = cur.fetchone()[0]
        if remaining == 0:
            print(f"  [DELETE-FACTION] '{legacy_fname}' (empty)")
            cur.execute("DELETE FROM factions WHERE id = ?", (fid,))
            deleted_factions.append(legacy_fname)

    conn.execute("COMMIT")
    print("\n  COMMIT OK")

except Exception as e:
    conn.execute("ROLLBACK")
    print(f"\n  ROLLBACK: {e}")
    raise

# ─── STEP 5: SUMMARY ─────────────────────────────────────────────────────────

print("\n=== STEP 5: Post-purge summary ===")

cur.execute("""
    SELECT f.name, COUNT(u.id)
    FROM units u
    JOIN factions f ON u.faction_id = f.id
    WHERE f.game_system_id = ?
    GROUP BY f.name ORDER BY f.name
""", (AOS_GS_ID,))
remaining_rows = cur.fetchall()
remaining_total = sum(r[1] for r in remaining_rows)

print(f"\nRepointed:      {repoint_count}")
if repoint_count:
    top5 = sorted(repoint_by_faction.items(), key=lambda x: -len(x[1]))[:5]
    for fname_t, units_t in top5:
        print(f"  → {fname_t}: {len(units_t)} units")

print(f"Merged:         {merge_count}")
print(f"Deleted:        {delete_count}")
print(f"FK rows touched:{fk_rows_total}")
print(f"Factions deleted: {deleted_factions}")
print(f"\nSkipped (ambiguous FK):")
for uid, reason in to_skip_fk:
    cur.execute("SELECT name FROM units WHERE id = ?", (uid,))
    r = cur.fetchone()
    uname = r[0] if r else '(gone)'
    print(f"  [SKIP-FK] id={uid} '{uname}': {reason}")

print(f"\nPost-purge AoS unit count: {remaining_total}")
print(f"Post-purge AoS factions:")
for fname_r, cnt in remaining_rows:
    print(f"  {fname_r}: {cnt}")

print(f"\nBackup: {BACKUP_PATH}")
print(f"Script: /app/scripts/purge_aos_orphans.py")

conn.close()
