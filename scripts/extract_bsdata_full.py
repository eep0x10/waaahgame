"""
Extract full warscroll data from BSData .cat files and populate units JSON columns.
Handles both AoS 4e (Library .cat files) and 40K 10e (standalone .cat files).

JSON columns updated on units table:
  stats_json    — unit profile stats (Move/Health/Save/Control for AoS; M/T/Sv/W/Ld/OC for 40K)
  weapons_json  — melee + ranged weapon profiles
  abilities_json — named abilities with timing/description
  keywords_json — category link names

Idempotent: always overwrites non-empty rows; skips units not in DB (no insert of new units).
Only processes units that are already in the DB (matched by slug or name-slug).

Run inside Docker:
  docker compose exec app python3 /app/scripts/extract_bsdata_full.py
"""
import xml.etree.ElementTree as ET
import sqlite3
import os
import re
import json
from collections import defaultdict

DB_PATH = '/app/instance/waaahgame.db'
BSAOS_DIR = '/app/scripts/cache/bsdata/aos'
BS40K_DIR = '/app/scripts/cache/bsdata/40k'

# ─── Helpers ────────────────────────────────────────────────────────────────

def slugify(name):
    s = name.lower()
    s = s.replace('&apos;', "'").replace('&amp;', '&').replace('&#39;', "'")
    s = re.sub(r"[''`’‘]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def get_ns(root):
    tag = root.tag
    return tag.split('}')[0] + '}' if '{' in tag else ''


def get_chars(profile_el, ns):
    """Return {char_name: char_text} for a profile element."""
    result = {}
    chars_el = profile_el.find(f'{ns}characteristics')
    if chars_el is not None:
        for c in chars_el:
            name = c.get('name', '').strip()
            text = (c.text or '').strip()
            result[name] = text
    return result


def clean_text(s):
    """Strip BSData markup artifacts from ability text."""
    if not s:
        return s
    # Remove ^^...^^ bold markers
    s = re.sub(r'\^\^([^^\n]+)\^\^', r'\1', s)
    # Normalize whitespace
    s = re.sub(r'\s+', ' ', s).strip()
    return s


# ─── AoS 4e Parser ──────────────────────────────────────────────────────────

def parse_aos_library(cat_path):
    """
    Parse an AoS 4e Library .cat file.
    Returns list of unit dicts:
      {name, stats, weapons, abilities, keywords}
    """
    try:
        tree = ET.parse(cat_path, parser=ET.XMLParser(encoding='utf-8'))
        root = tree.getroot()
    except Exception as e:
        print(f"  [SKIP] Parse error {cat_path}: {e}")
        return []

    ns = get_ns(root)
    units = []

    for se in root.iter(f'{ns}selectionEntry'):
        if se.get('type') not in ('unit', 'model'):
            continue
        unit_name = se.get('name', '').strip()
        if not unit_name:
            continue

        stats = {}
        abilities = []
        weapons = []
        keywords = []

        # ── Profiles directly on the unit entry ──────────────────────────
        profiles_el = se.find(f'{ns}profiles')
        if profiles_el is not None:
            for p in profiles_el:
                tn = p.get('typeName', '')
                pname = p.get('name', '').strip()
                chars = get_chars(p, ns)

                if tn == 'Unit':
                    # Stats: Move, Health, Save, Control
                    stats = {k: v for k, v in chars.items() if v}

                elif tn in ('Ability (Passive)', 'Ability (Activated)', 'Ability (Command)',
                            'Ability (Spell)', 'Ability (Prayer)', 'Ability (Fate)'):
                    timing = chars.get('Timing', '')
                    if not timing:
                        # Passive abilities have no Timing field
                        if tn == 'Ability (Passive)':
                            timing = 'Passive'
                        else:
                            timing = tn.replace('Ability (', '').rstrip(')')
                    abilities.append({
                        'name': pname,
                        'timing': clean_text(timing),
                        'description': clean_text(chars.get('Effect', '') or chars.get('Description', '')),
                        'declare': clean_text(chars.get('Declare', '')),
                        'keywords': clean_text(chars.get('Keywords', '')),
                    })

        # ── Weapon profiles live in child upgrade selectionEntries ───────
        # Recurse into all descendant selectionEntries to find upgrade type entries
        for child_se in se.iter(f'{ns}selectionEntry'):
            if child_se is se:
                continue
            if child_se.get('type') != 'upgrade':
                continue
            child_profiles = child_se.find(f'{ns}profiles')
            if child_profiles is None:
                continue
            for p in child_profiles:
                tn = p.get('typeName', '')
                if tn not in ('Melee Weapon', 'Ranged Weapon'):
                    continue
                pname = p.get('name', '').strip()
                chars = get_chars(p, ns)
                w = {
                    'Name': pname,
                    'Type': 'MELEE WEAPONS' if tn == 'Melee Weapon' else 'RANGED WEAPONS',
                    'Atk': chars.get('Atk', ''),
                    'Hit': chars.get('Hit', ''),
                    'Wnd': chars.get('Wnd', ''),
                    'Rnd': chars.get('Rnd', ''),
                    'Dmg': chars.get('Dmg', ''),
                    'Abilities': chars.get('Ability', ''),
                }
                if tn == 'Ranged Weapon':
                    w['Rng'] = chars.get('Rng', '')
                weapons.append(w)

        # ── Keywords from categoryLinks ───────────────────────────────────
        cats_el = se.find(f'{ns}categoryLinks')
        if cats_el is not None:
            for cl in cats_el:
                kw = cl.get('name', '').strip()
                if kw:
                    keywords.append(kw.upper())

        if stats or weapons or abilities or keywords:
            units.append({
                'name': unit_name,
                'stats': stats,
                'weapons': weapons,
                'abilities': abilities,
                'keywords': keywords,
            })

    return units


# ─── 40K 10e Parser ─────────────────────────────────────────────────────────

def build_id_map(root, ns):
    """Build id → selectionEntry element map for resolving entryLinks."""
    id_map = {}
    for se in root.iter(f'{ns}selectionEntry'):
        eid = se.get('id', '')
        if eid:
            id_map[eid] = se
    for seg in root.iter(f'{ns}selectionEntryGroup'):
        eid = seg.get('id', '')
        if eid:
            id_map[eid] = seg
    return id_map


def extract_weapon_profiles_from_entry(se, ns):
    """Extract Melee Weapons / Ranged Weapons profiles from an entry element."""
    weapons = []
    for p in se.iter(f'{ns}profile'):
        tn = p.get('typeName', '')
        if tn not in ('Melee Weapons', 'Ranged Weapons'):
            continue
        pname = p.get('name', '').strip()
        chars = get_chars(p, ns)
        if tn == 'Ranged Weapons':
            weapons.append({
                'Name': pname,
                'Type': 'Ranged',
                'Range': chars.get('Range', ''),
                'A': chars.get('A', ''),
                'BS': chars.get('BS', ''),
                'S': chars.get('S', ''),
                'AP': chars.get('AP', ''),
                'D': chars.get('D', ''),
                'Keywords': chars.get('Keywords', ''),
            })
        else:
            weapons.append({
                'Name': pname,
                'Type': 'Melee',
                'Range': 'Melee',
                'A': chars.get('A', ''),
                'WS': chars.get('WS', ''),
                'S': chars.get('S', ''),
                'AP': chars.get('AP', ''),
                'D': chars.get('D', ''),
                'Keywords': chars.get('Keywords', ''),
            })
    return weapons


def resolve_linked_weapons(unit_se, ns, id_map, visited=None):
    """
    Follow entryLinks within the unit entry to collect weapon profiles from
    shared selectionEntry elements (referenced by targetId).
    """
    if visited is None:
        visited = set()
    weapons = []
    for el in unit_se.iter(f'{ns}entryLink'):
        target_id = el.get('targetId', '')
        if not target_id or target_id in visited:
            continue
        visited.add(target_id)
        target = id_map.get(target_id)
        if target is None:
            continue
        # Extract weapon profiles from resolved entry
        weapons.extend(extract_weapon_profiles_from_entry(target, ns))
    return weapons


def parse_40k_cat(cat_path):
    """
    Parse a 40K 10e .cat file.
    Returns list of unit dicts: {name, stats, weapons, abilities, keywords}
    """
    try:
        tree = ET.parse(cat_path, parser=ET.XMLParser(encoding='utf-8'))
        root = tree.getroot()
    except Exception as e:
        print(f"  [SKIP] Parse error {cat_path}: {e}")
        return []

    ns = get_ns(root)
    # Build id map for entryLink resolution
    id_map = build_id_map(root, ns)
    units = []

    for se in root.iter(f'{ns}selectionEntry'):
        if se.get('type') != 'unit':
            continue
        unit_name = se.get('name', '').strip()
        if not unit_name:
            continue

        stats = {}
        abilities = []
        weapons = []
        keywords = []

        # All profiles nested anywhere inside this unit entry
        for p in se.iter(f'{ns}profile'):
            tn = p.get('typeName', '')
            pname = p.get('name', '').strip()
            chars = get_chars(p, ns)

            if tn == 'Unit':
                # M, T, SV, W, LD, OC
                stats = {
                    'move': chars.get('M', ''),
                    'toughness': chars.get('T', ''),
                    'save': chars.get('SV', ''),
                    'wounds': chars.get('W', ''),
                    'leadership': chars.get('LD', ''),
                    'oc': chars.get('OC', ''),
                }
                stats = {k: v for k, v in stats.items() if v}

            elif tn == 'Ranged Weapons':
                weapons.append({
                    'Name': pname,
                    'Type': 'Ranged',
                    'Range': chars.get('Range', ''),
                    'A': chars.get('A', ''),
                    'BS': chars.get('BS', ''),
                    'S': chars.get('S', ''),
                    'AP': chars.get('AP', ''),
                    'D': chars.get('D', ''),
                    'Keywords': chars.get('Keywords', ''),
                })

            elif tn == 'Melee Weapons':
                weapons.append({
                    'Name': pname,
                    'Type': 'Melee',
                    'Range': 'Melee',
                    'A': chars.get('A', ''),
                    'WS': chars.get('WS', ''),
                    'S': chars.get('S', ''),
                    'AP': chars.get('AP', ''),
                    'D': chars.get('D', ''),
                    'Keywords': chars.get('Keywords', ''),
                })

            elif tn == 'Abilities':
                desc = chars.get('Description', '')
                abilities.append({
                    'name': pname,
                    'description': clean_text(desc),
                })

        # Resolve linked weapons from entryLinks (units that reference shared weapon entries)
        if not weapons:
            linked = resolve_linked_weapons(se, ns, id_map)
            # De-duplicate by name
            seen_names = set()
            for w in linked:
                if w['Name'] not in seen_names:
                    weapons.append(w)
                    seen_names.add(w['Name'])

        # Keywords from categoryLinks
        cats_el = se.find(f'{ns}categoryLinks')
        if cats_el is not None:
            for cl in cats_el:
                kw = cl.get('name', '').strip()
                if kw:
                    keywords.append(kw.upper())

        if stats or weapons or abilities or keywords:
            units.append({
                'name': unit_name,
                'stats': stats,
                'weapons': weapons,
                'abilities': abilities,
                'keywords': keywords,
            })

    return units


# ─── DB Updater ─────────────────────────────────────────────────────────────

def update_db(conn, units_data, game_system_code, source_label):
    """
    Match each unit to DB row by slug, update JSON columns.
    Returns (matched, not_matched) counts.
    """
    # Build slug → unit_id map for this game system
    sys_id = conn.execute(
        "SELECT id FROM game_systems WHERE code=?", (game_system_code,)
    ).fetchone()
    if sys_id is None:
        print(f"  [WARN] Game system '{game_system_code}' not found in DB")
        return 0, 0
    sys_id = sys_id[0]

    db_units = conn.execute("""
        SELECT u.id, u.slug, u.name FROM units u
        JOIN factions f ON f.id = u.faction_id
        WHERE f.game_system_id = ?
    """, (sys_id,)).fetchall()

    # Build lookups: slug → id, name-slug → id
    slug_to_id = {}
    nameslug_to_id = {}
    for row in db_units:
        slug_to_id[row[1]] = row[0]
        nameslug_to_id[slugify(row[2])] = row[0]

    matched = 0
    not_matched = 0

    for unit in units_data:
        name = unit['name']
        # Try slug match
        unit_id = slug_to_id.get(slugify(name))
        if unit_id is None:
            unit_id = nameslug_to_id.get(slugify(name))
        # Try stripping trailing qualifiers like ", The"
        if unit_id is None:
            base = re.sub(r',.*$', '', name).strip()
            unit_id = slug_to_id.get(slugify(base))
        if unit_id is None:
            not_matched += 1
            continue

        # Merge: don't overwrite non-empty with empty
        existing = conn.execute(
            "SELECT stats_json, weapons_json, abilities_json, keywords_json FROM units WHERE id=?",
            (unit_id,)
        ).fetchone()

        def load_json(val):
            if val is None:
                return None
            try:
                return json.loads(val)
            except Exception:
                return None

        ex_stats = load_json(existing[0])
        ex_weapons = load_json(existing[1])
        ex_abilities = load_json(existing[2])
        ex_keywords = load_json(existing[3])

        new_stats = unit['stats'] if unit['stats'] else (ex_stats or {})
        new_weapons = unit['weapons'] if unit['weapons'] else (ex_weapons or [])
        new_abilities = unit['abilities'] if unit['abilities'] else (ex_abilities or [])
        new_keywords = unit['keywords'] if unit['keywords'] else (ex_keywords or [])

        conn.execute("""
            UPDATE units SET
                stats_json = ?,
                weapons_json = ?,
                abilities_json = ?,
                keywords_json = ?
            WHERE id = ?
        """, (
            json.dumps(new_stats),
            json.dumps(new_weapons),
            json.dumps(new_abilities),
            json.dumps(new_keywords),
            unit_id,
        ))
        matched += 1

    conn.commit()
    print(f"  [{source_label}] matched={matched} not_matched={not_matched}")
    return matched, not_matched


# ─── Main ────────────────────────────────────────────────────────────────────

def run_aos():
    """Parse all AoS Library .cat files and update DB."""
    print("\n=== AoS 4e: parsing Library .cat files ===")
    conn = sqlite3.connect(DB_PATH)

    all_units = {}  # name → unit dict (first-wins from Library files)

    for fname in sorted(os.listdir(BSAOS_DIR)):
        if not fname.endswith('.cat'):
            continue
        # Prefer Library files; also try non-library as fallback
        path = os.path.join(BSAOS_DIR, fname)
        try:
            units = parse_aos_library(path)
        except Exception as e:
            print(f"  [SKIP] {fname}: {e}")
            continue
        if not units:
            continue
        added = 0
        for u in units:
            key = u['name']
            if key not in all_units:
                all_units[key] = u
                added += 1
            else:
                # Merge: if existing lacks weapons/abilities, fill in
                ex = all_units[key]
                if not ex['weapons'] and u['weapons']:
                    ex['weapons'] = u['weapons']
                if not ex['abilities'] and u['abilities']:
                    ex['abilities'] = u['abilities']
                if not ex['stats'] and u['stats']:
                    ex['stats'] = u['stats']
                if not ex['keywords'] and u['keywords']:
                    ex['keywords'] = u['keywords']
        print(f"  {fname}: {len(units)} entries (new: {added})")

    print(f"\nTotal AoS unique units from BSData: {len(all_units)}")
    total_matched, total_not = update_db(conn, list(all_units.values()), 'aos4', 'AoS')
    conn.close()
    return total_matched, total_not


def run_40k():
    """Parse all 40K .cat files and update DB."""
    print("\n=== 40K 10e: parsing .cat files ===")
    conn = sqlite3.connect(DB_PATH)

    all_units = {}  # name → unit dict

    for fname in sorted(os.listdir(BS40K_DIR)):
        if not fname.endswith('.cat'):
            continue
        path = os.path.join(BS40K_DIR, fname)
        try:
            units = parse_40k_cat(path)
        except Exception as e:
            print(f"  [SKIP] {fname}: {e}")
            continue
        if not units:
            continue
        added = 0
        for u in units:
            key = u['name']
            if key not in all_units:
                all_units[key] = u
                added += 1
            else:
                ex = all_units[key]
                if not ex['weapons'] and u['weapons']:
                    ex['weapons'] = u['weapons']
                if not ex['abilities'] and u['abilities']:
                    ex['abilities'] = u['abilities']
                if not ex['stats'] and u['stats']:
                    ex['stats'] = u['stats']
                if not ex['keywords'] and u['keywords']:
                    ex['keywords'] = u['keywords']
        print(f"  {fname}: {len(units)} entries (new: {added})")

    print(f"\nTotal 40K unique units from BSData: {len(all_units)}")
    total_matched, total_not = update_db(conn, list(all_units.values()), 'w40k10', '40K')
    conn.close()
    return total_matched, total_not


def print_final_stats():
    """Report fill rates from DB after extraction."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    print("\n=== FINAL DB FILL RATES ===")
    for sys_code in ('aos4', 'w40k10'):
        total = conn.execute("""
            SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id
            JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code=?
        """, (sys_code,)).fetchone()[0]
        has_stats = conn.execute("""
            SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id
            JOIN game_systems gs ON gs.id=f.game_system_id
            WHERE gs.code=? AND u.stats_json != '{}' AND u.stats_json IS NOT NULL
        """, (sys_code,)).fetchone()[0]
        has_weapons = conn.execute("""
            SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id
            JOIN game_systems gs ON gs.id=f.game_system_id
            WHERE gs.code=? AND u.weapons_json != '[]' AND u.weapons_json IS NOT NULL
        """, (sys_code,)).fetchone()[0]
        has_abilities = conn.execute("""
            SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id
            JOIN game_systems gs ON gs.id=f.game_system_id
            WHERE gs.code=? AND u.abilities_json != '[]' AND u.abilities_json IS NOT NULL
        """, (sys_code,)).fetchone()[0]
        has_full = conn.execute("""
            SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id
            JOIN game_systems gs ON gs.id=f.game_system_id
            WHERE gs.code=? AND u.stats_json != '{}' AND u.stats_json IS NOT NULL
              AND u.weapons_json != '[]' AND u.weapons_json IS NOT NULL
              AND u.abilities_json != '[]' AND u.abilities_json IS NOT NULL
        """, (sys_code,)).fetchone()[0]

        print(f"\n{sys_code}: total={total}")
        print(f"  stats: {has_stats}/{total} ({round(100*has_stats/total,1)}%)")
        print(f"  weapons: {has_weapons}/{total} ({round(100*has_weapons/total,1)}%)")
        print(f"  abilities: {has_abilities}/{total} ({round(100*has_abilities/total,1)}%)")
        print(f"  full (all 3): {has_full}/{total} ({round(100*has_full/total,1)}%)")
        partial = has_stats - has_full
        none_ = total - has_stats
        print(f"  partial: {partial} | none: {none_}")

    conn.close()


def spot_check(unit_slug):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    u = conn.execute("SELECT * FROM units WHERE slug=?", (unit_slug,)).fetchone()
    if not u:
        print(f"  [SPOT] {unit_slug}: NOT FOUND")
        conn.close()
        return
    stats = json.loads(u['stats_json'] or '{}')
    weapons = json.loads(u['weapons_json'] or '[]')
    abilities = json.loads(u['abilities_json'] or '[]')
    keywords = json.loads(u['keywords_json'] or '[]')
    print(f"\n  [SPOT] {unit_slug}")
    print(f"    stats: {stats}")
    print(f"    weapons: {len(weapons)} ({', '.join(w['Name'] for w in weapons[:3])}{'...' if len(weapons)>3 else ''})")
    print(f"    abilities: {len(abilities)} ({', '.join(a['name'] for a in abilities[:3])}{'...' if len(abilities)>3 else ''})")
    print(f"    keywords: {keywords[:8]}")
    conn.close()


if __name__ == '__main__':
    print("=== extract_bsdata_full.py ===")
    print(f"DB: {DB_PATH}")
    print(f"AoS dir: {BSAOS_DIR}")
    print(f"40K dir: {BS40K_DIR}")

    aos_matched, aos_not = run_aos()
    k40_matched, k40_not = run_40k()

    print_final_stats()

    print("\n=== SPOT CHECKS ===")
    # AoS
    for slug in ('liberators', 'bloodthirster', 'nagash-mortarch-of-death', 'stormdrake-guard', 'vindictors'):
        spot_check(slug)
    # 40K
    for slug in ('custodian-guard', 'termagants', 'captain-in-power-armour'):
        spot_check(slug)
