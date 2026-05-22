#!/usr/bin/env python3
"""
D4 — Import Regiments of Renown from battle_profiles.clean.md
Idempotent: backs up DB to .bak-d4, full refresh on regiments_of_renown table.

Strategy:
  - Use BOILERPLATE line as anchor for each regiment block
  - Identify regiment name+points from nearby non-bullet lines
  - Collect unit bullets from ±10 line window
  - Collect factions from lines after BOILERPLATE
  - Manual overrides for OCR-garbled and split-name entries
"""
import json
import os
import re
import shutil
import sqlite3
import sys
from datetime import datetime, timezone

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
CLEAN_MD = os.path.join(SCRIPT_DIR, 'cache', 'aos_rules_extract', 'battle_profiles.clean.md')
DB_PATH = os.path.join(PROJECT_ROOT, 'instance', 'waaahgame.db')
BAK_PATH = DB_PATH + '.bak-d4'

NEW_MARKER = chr(0x2739)
BOILERPLATE = 'This Regiment of Renown can be included in the following factions:'

SECTION_ALLIANCES = {
    'MERCENARY': 'Mercenary', 'ORDER': 'Order', 'CHAOS': 'Chaos',
    'DEATH': 'Death', 'DESTRUCTION': 'Destruction',
}

NOISE_PATS = [
    r'^<!--', r'^\s*[®]\s*$', r'^APRIL 20\d\d\s*$', r'^REGIMENTS OF RENOWN\s*$',
    r'^NEW\s*$', r'^UNIT SUMMARY POINTS NOTES\s*$', r'^REGIMENTS\s*$',
    r'^---\s*$', r'^\s*$',
]

BULLET_PAT = re.compile(r'^\s*[•·]\s*(.+)')
POINTS_PAT = re.compile(r'\b(\d{3,4})\b')


def normalize_apostrophe(s):
    """Normalize curly/smart apostrophes to straight apostrophe."""
    # U+2018 LEFT SINGLE QUOTATION MARK, U+2019 RIGHT SINGLE QUOTATION MARK
    return s.replace(chr(0x2018), "'").replace(chr(0x2019), "'")

def is_noise(s):
    return any(re.match(p, s.strip()) for p in NOISE_PATS)

def is_bullet(s):
    return bool(BULLET_PAT.match(s.strip()))

def has_points(s):
    return bool(POINTS_PAT.search(s))

def strip_markers(s):
    return s.strip().lstrip(NEW_MARKER + '* \t').strip()

def split_factions(text):
    text = re.sub(r'\s+', ' ', text).strip().rstrip('.')
    parts = [p.strip() for p in re.split(r',\s*', text) if p.strip()]
    return [p for p in parts if len(p) >= 4 and '•' not in p
            and p[0].isupper() and not has_points(p) and len(p.split()) <= 6]

def extract_unit_from_bullet(s):
    """Clean up a bullet line content: strip faction text and boilerplate."""
    if BOILERPLATE in s:
        s = s[:s.index(BOILERPLATE)].strip()
    # Remove trailing faction text after points number
    m = POINTS_PAT.search(s)
    if m:
        after = s[m.end():].strip()
        # If after the points number there's text that looks like a faction list
        if after and after[0].isupper() and (',' in after or after.endswith('.')):
            s = s[:m.end()].strip()
        else:
            # Just trim the points too (unit name doesn't include points)
            s = s[:m.start()].strip()
    return s.rstrip(',. ').strip()


# ── Manual overrides: entries that resist algorithmic parsing ─────────────────
# OCR garbage, PDF column-split names, etc.
# These will be merged with parsed results (name-match replaces parsed entry,
# missing entries are appended).
MANUAL_OVERRIDES = {
    # OCR garbage for Mask of the Deceiver
    'Mask of the Deceiver': {
        'points_cost': 170, 'alliance': 'Chaos', 'is_new': True,
        'units': ['Changeling (use The Mask of the Deceiver model)'],
        'eligible_factions': [
            'Cities of Sigmar', 'Daughters of Khaine', 'Flesh-eater Courts', 'Fyreslayers',
            'Gloomspite Gitz', 'Idoneth Deepkin', 'Ironjawz', 'Kharadron Overlords',
            'Kruleboyz', 'Lumineth Realm-lords', 'Maggotkin of Nurgle', 'Nighthaunt',
            'Ogor Mawtribes', 'Ossiarch Bonereapers', 'Seraphon', 'Skaven',
            'Slaves to Darkness', 'Soulblight Gravelords', 'Stormcast Eternals', 'Sylvaneth',
        ],
    },
    # Name split across columns; parser catches "Everchosen" only
    'Squires of the Everchosen': {
        'points_cost': 280, 'alliance': 'Mercenary', 'is_new': False,
        'units': ['1 Varghulf Courtier', '3 Morbheg Knights'],
        'eligible_factions': [
            'Blades of Khorne', 'Disciples of Tzeentch', 'Maggotkin of Nurgle',
            'Hedonites of Slaanesh', 'Slaves to Darkness',
        ],
    },
    # Name split: "Blades of the" + "Hollow King 260"
    'Blades of the Hollow King': {
        'points_cost': 260, 'alliance': 'Death', 'is_new': False,
        'units': ['Blades of the Hollow King'],
        'eligible_factions': ['Flesh-eater Courts', 'Nighthaunt', 'Ossiarch Bonereapers'],
    },
    # Name split: "Craventhrone" + "Executioners"
    'Craventhrone Executioners': {
        'points_cost': 290, 'alliance': 'Death', 'is_new': False,
        'units': ['1 Scriptor Mortis', '5 Craventhrone Guard', '5 Craventhrone Guard'],
        'eligible_factions': ['Flesh-eater Courts', 'Ossiarch Bonereapers', 'Soulblight Gravelords'],
    },
    # Name split: "The Beast of Castle" + "Sternieste"
    'The Beast of Castle Sternieste': {
        'points_cost': 190, 'alliance': 'Death', 'is_new': False,
        'units': ['1 Revenant Draconith'],
        'eligible_factions': ['Flesh-eater Courts', 'Nighthaunt', 'Ossiarch Bonereapers'],
    },
    # Name split: "The Horror of" + "Hallow's Watch"
    "The Horror of Hallow's Watch": {
        'points_cost': 230, 'alliance': 'Death', 'is_new': False,
        'units': ['1 Royal Terrorgheist'],
        'eligible_factions': ['Nighthaunt', 'Ossiarch Bonereapers', 'Soulblight Gravelords'],
    },
    # Name split: "The Scions of the" + "Necropolis"
    'The Scions of the Necropolis': {
        'points_cost': None, 'alliance': 'Death', 'is_new': False,
        'units': ['Katakros, Mortarch of the Necropolis', '3 Immortis Guard', '3 Immortis Guard'],
        'eligible_factions': ['Flesh-eater Courts', 'Nighthaunt', 'Soulblight Gravelords'],
    },
    # Name split: "The Summerking's" + "Entourage"
    "The Summerking's Entourage": {
        'points_cost': 640, 'alliance': 'Death', 'is_new': False,
        'units': ['Ushoran, Mortarch of Delusion', '3 Morbheg Knights', '10 Cryptguard'],
        'eligible_factions': ['Nighthaunt', 'Ossiarch Bonereapers', 'Soulblight Gravelords'],
    },
    # Name split: "Karahtet's Siege" + "Breaker"
    "Karahtet's Siege Breaker": {
        'points_cost': 360, 'alliance': 'Death', 'is_new': True,
        'units': ['1 Mortisan Ossifector', '1 Mortek Crawler'],
        'eligible_factions': ['Flesh-eater Courts', 'Nighthaunt', 'Soulblight Gravelords'],
    },
    # Name split: "Phulgoth's" + "Shudderhood"
    "Phulgoth's Shudderhood": {
        'points_cost': 530, 'alliance': 'Chaos', 'is_new': False,
        'units': ['1 Harbinger of Decay', '5 Putrid Blightkings', '2 Pusgoyle Blightlords'],
        'eligible_factions': [
            'Beasts of Chaos', 'Blades of Khorne', 'Disciples of Tzeentch',
            'Hedonites of Slaanesh', 'Helsmiths of Hashut', 'Slaves to Darkness', 'Skaven',
        ],
    },
    # Name split: "Seeker of the" + "Dread Dirge"
    'Seeker of the Dread Dirge': {
        'points_cost': 260, 'alliance': 'Chaos', 'is_new': False,
        'units': ['1 Ashen Elder', '1 Dominator Engine with Bane Maces'],
        'eligible_factions': [
            'Blades of Khorne', 'Disciples of Tzeentch', 'Maggotkin of Nurgle',
            'Hedonites of Slaanesh', 'Slaves to Darkness', 'Skaven',
        ],
    },
    # Name partially parsed by algo as "Dawnrider Lance Lightcourser" — correct it
    'Dawnrider Lance': {
        'points_cost': 260, 'alliance': 'Order', 'is_new': True,
        'units': ['1 Vanari Lord Regent on Lightcourser', '5 Vanari Dawnriders'],
        'eligible_factions': [
            'Cities of Sigmar', 'Daughters of Khaine', 'Fyreslayers', 'Idoneth Deepkin',
            'Kharadron Overlords', 'Seraphon', 'Stormcast Eternals', 'Sylvaneth',
        ],
    },
    # "Fjori's Flamebearers" — parser garbles name with unit text
    "Fjori's Flamebearers": {
        'points_cost': 420, 'alliance': 'Order', 'is_new': False,
        'units': [
            '1 Grimhold Exile', '5 Auric Hearthguard',
            '5 Hearthguard Berzerkers with Flamestrike Poleaxes',
            '10 Vulkite Berzerkers with Fyresteel Weapons',
        ],
        'eligible_factions': [
            'Cities of Sigmar', 'Daughters of Khaine', 'Idoneth Deepkin',
            'Kharadron Overlords', 'Lumineth Realm-lords', 'Seraphon',
            'Stormcast Eternals', 'Sylvaneth',
        ],
    },
    # Alliance fix: Volt-Klaw's Enginecoven is Chaos not Death
    "Volt-Klaw's Enginecoven": {
        'points_cost': 410, 'alliance': 'Chaos', 'is_new': False,
        'units': ['1 Warlock Galvaneer', '3 Warpvolt Scourgers', '1 Ratling Warpblaster'],
        'eligible_factions': [
            'Beasts of Chaos', 'Blades of Khorne', 'Disciples of Tzeentch',
            'Maggotkin of Nurgle', 'Hedonites of Slaanesh', 'Slaves to Darkness',
        ],
    },
    # Alliance fix: Veremord's Shamblers is Death not Destruction
    "Veremord's Shamblers": {
        'points_cost': 210, 'alliance': 'Death', 'is_new': False,
        'units': ['1 Corpse Cart', '20 Deadwalker Zombies'],
        'eligible_factions': [
            'Flesh-eater Courts', 'Nighthaunt', 'Ossiarch Bonereapers',
        ],
    },
    # Missing from algo: The Shinestealaz (Destruction page)
    'The Shinestealaz': {
        'points_cost': 500, 'alliance': 'Destruction', 'is_new': False,
        'units': [
            '1 Snarlboss', '2 Wolfgit Retinue',
            '3 Snarlpack Cavalry', '3 Snarlpack Cavalry', '2 Sunsteala Wheelas',
        ],
        'eligible_factions': [
            'Ironjawz', 'Kruleboyz', 'Ogor Mawtribes', 'Sons of Behemat',
        ],
    },
}

# Names that algorithm produces but are wrong — map algo name → correct name
ALGO_NAME_REMAP = {
    'Everchosen': 'Squires of the Everchosen',
    'Karahtet': "Karahtet's Siege Breaker",  # algo may produce this
    "Karahtet's Siege": "Karahtet's Siege Breaker",
    'Ma N sk E o W f t he Deceiver': 'Mask of the Deceiver',
    'Dawnrider Lance Lightcourser': 'Dawnrider Lance',
    "Fjori's Flamebearers Flamestrike Poleaxes": "Fjori's Flamebearers",
}

# Names to DROP from algo results (will be replaced by MANUAL_OVERRIDES)
# NOTE: apostrophes here must be straight ' (not curly) — names are normalized
_AP = chr(0x27)  # straight apostrophe, avoids editor curly-quote injection
ALGO_NAMES_DROP = set(ALGO_NAME_REMAP.keys()) | {
    'Shudderhood',
    'Dread Dirge',
    'Fjori' + _AP + 's Flamebearers Flamestrike Poleaxes Cities of Sigmar',
    'Fjori' + _AP + 's Flamebearers Flamestrike Poleaxes',
    'Dawnrider Lance Lightcourser Cities of Sigmar',
    'Dawnrider Lance Lightcourser',
}


# ── Main parser ────────────────────────────────────────────────────────────────

def parse_ror_section(text):
    lines = text.splitlines()

    # Find section boundaries
    ror_start = None
    ror_end = len(lines)
    for i, line in enumerate(lines):
        s = line.strip()
        if s == 'REGIMENTS OF RENOWN' and ror_start is None:
            for j in range(i+1, min(i+6, len(lines))):
                if lines[j].strip() in SECTION_ALLIANCES:
                    ror_start = i
                    break
        if ror_start is not None and re.match(r'^WARHAMMER LEGENDS\s*[–-]', s):
            ror_end = i
            break

    if ror_start is None:
        print("ERROR: cannot find REGIMENTS OF RENOWN section")
        return []

    section = lines[ror_start:ror_end]

    # Build cleaned line list with alliance tags
    cur_alliance = 'Mercenary'
    cleaned = []
    for raw in section:
        s = normalize_apostrophe(raw.strip())
        if s in SECTION_ALLIANCES:
            cur_alliance = SECTION_ALLIANCES[s]
            continue
        if is_noise(raw):
            continue
        cleaned.append({'raw': s, 'alliance': cur_alliance})

    n = len(cleaned)
    bp_indices = [i for i, e in enumerate(cleaned) if BOILERPLATE in e['raw']]

    regiments = []

    for bp_i in bp_indices:
        bp_entry = cleaned[bp_i]
        alliance = bp_entry['alliance']
        bp_line = bp_entry['raw']

        # ── Collect factions ──
        inline_faction = bp_line[bp_line.index(BOILERPLATE)+len(BOILERPLATE):].strip()
        faction_parts = [inline_faction] if inline_faction else []

        # Pre-boilerplate faction lines (PDF right column may appear before in text)
        k = bp_i - 1
        pre_factions = []
        while k >= max(0, bp_i - 6):
            nk = cleaned[k]['raw']
            if BOILERPLATE in nk:
                break
            # Pure faction continuation: starts with capital, has commas, no bullet, no points
            if (nk and nk[0].isupper() and ',' in nk
                    and not is_bullet(nk) and not has_points(nk) and not is_noise(nk)):
                pre_factions.insert(0, nk)
                k -= 1
            else:
                break

        # Post-boilerplate faction lines
        j = bp_i + 1
        while j < n and j <= bp_i + 8:
            nj = cleaned[j]['raw']
            if BOILERPLATE in nj:
                break
            if is_bullet(nj):
                # Faction text can appear inline with bullet after BOILERPLATE
                bc = BULLET_PAT.match(nj).group(1).strip()
                # Heuristic: faction text comes after the unit name in bullet
                # We look for ", FactionName" pattern
                faction_suffix = re.search(r'(?<=[a-z0-9])\s+([A-Z][A-Za-z\s\-\']+(?:,\s*[A-Za-z][A-Za-z\s\-\']+)*)\.?\s*$', bc)
                if faction_suffix:
                    faction_parts.append(faction_suffix.group(1))
                j += 1
            elif nj and nj[0].isupper() and not has_points(nj) and not is_noise(nj):
                faction_parts.append(nj)
                j += 1
            else:
                j += 1

        all_faction_text = ' '.join(pre_factions + faction_parts)
        eligible_factions = split_factions(all_faction_text)

        # ── Find regiment name + points ──
        name = None
        points = None
        is_new = False

        # Search backwards for a non-bullet line with points (the name line)
        for k in range(bp_i - 1, max(-1, bp_i - 12), -1):
            nk = cleaned[k]['raw']
            if BOILERPLATE in nk:
                break
            if is_noise(nk):
                continue
            if not is_bullet(nk) and has_points(nk):
                is_new = NEW_MARKER in nk
                pts = extract_points_from_line(nk)
                raw_name = extract_name_from_line(nk)
                if raw_name and len(raw_name) >= 2 and raw_name[0].isupper():
                    name = raw_name
                    points = pts
                    break

        if name is None:
            # Check if boilerplate line itself has name+points before BOILERPLATE
            before_bp = bp_line[:bp_line.index(BOILERPLATE)].strip()
            if before_bp and not is_bullet(before_bp) and has_points(before_bp):
                is_new = NEW_MARKER in before_bp
                points = extract_points_from_line(before_bp)
                name = extract_name_from_line(before_bp)

        if name is None:
            # Layout: BOILERPLATE on line N, name AFTER (forward search)
            # e.g. "This Regiment of Renown..."  then "Big Drogg • unit 450 factions..."
            for k in range(bp_i + 1, min(n, bp_i + 5)):
                nk = cleaned[k]['raw']
                if BOILERPLATE in nk:
                    break
                if not is_bullet(nk) and has_points(nk) and nk and nk[0].isupper():
                    is_new = NEW_MARKER in nk
                    points = extract_points_from_line(nk)
                    raw_name = extract_name_from_line(nk)
                    if raw_name and len(raw_name) >= 2 and raw_name[0].isupper():
                        name = raw_name
                        # Also collect factions from this line (inline after points)
                        m = POINTS_PAT.search(nk)
                        if m:
                            inline_after = nk[m.end():].strip()
                            if inline_after and inline_after[0].isupper():
                                faction_parts.insert(0, inline_after)
                                # Recalculate factions
                                all_faction_text = ' '.join(pre_factions + faction_parts)
                                eligible_factions = split_factions(all_faction_text)
                        break

        if name is None:
            # Some single-unit regiments: points on bullet, name on non-bullet line
            # Check backward for non-bullet line (no points required)
            for k in range(bp_i - 1, max(-1, bp_i - 8), -1):
                nk = cleaned[k]['raw']
                if BOILERPLATE in nk:
                    break
                if not is_bullet(nk) and not is_noise(nk) and nk and nk[0].isupper():
                    raw_name = strip_markers(nk)
                    if raw_name and len(raw_name) >= 3:
                        name = raw_name
                        # Get points from nearby bullet
                        for kk in range(max(0, bp_i-4), min(n, bp_i+4)):
                            if BOILERPLATE in cleaned[kk]['raw']:
                                continue
                            if has_points(cleaned[kk]['raw']):
                                points = extract_points_from_line(cleaned[kk]['raw'])
                                if points:
                                    break
                        break

        if name is None:
            continue

        # Clean up name
        name = re.sub(r'\s+', ' ', name).strip()

        # ── Collect bullet units in window ──
        all_units = []
        for k in range(max(0, bp_i - 10), min(n, bp_i + 10)):
            nk = cleaned[k]['raw']
            if k > bp_i and BOILERPLATE in nk:
                break  # stop at next regiment's boilerplate
            if is_bullet(nk):
                bc = BULLET_PAT.match(nk).group(1).strip()
                u = extract_unit_from_bullet(bc)
                if u and len(u) > 2:
                    all_units.append(u)
            elif k > bp_i and has_points(nk) and not is_bullet(nk):
                # Name line after boilerplate — extract inline bullet units
                inline_units = re.findall(r'[•·]\s*([^•·]+?)(?=[•·]|\d{3,4}|$)', nk)
                for iu in inline_units:
                    u = extract_unit_from_bullet(iu.strip())
                    if u and len(u) > 2:
                        all_units.append(u)

        # Deduplicate
        seen = set()
        units_final = []
        for u in all_units:
            if u not in seen:
                seen.add(u)
                units_final.append(u)

        regiments.append({
            'name': name,
            'points_cost': points,
            'alliance': alliance,
            'units': units_final,
            'eligible_factions': eligible_factions,
            'is_new': is_new,
        })

    # ── Apply remap + drop ──
    final = []
    for r in regiments:
        n_raw = r['name']
        if n_raw in ALGO_NAMES_DROP:
            continue  # replaced by manual
        if n_raw in ALGO_NAME_REMAP:
            correct = ALGO_NAME_REMAP[n_raw]
            if correct in MANUAL_OVERRIDES:
                mo = MANUAL_OVERRIDES[correct]
                r = {'name': correct, **mo}
            else:
                r['name'] = correct
        final.append(r)

    # ── Add manual entries not produced by algo ──
    existing_names = {r['name'] for r in final}
    for mname, mdata in MANUAL_OVERRIDES.items():
        if mname not in existing_names:
            final.append({'name': mname, **mdata})

    # ── Normalize apostrophes in all names ──
    for r in final:
        r['name'] = normalize_apostrophe(r['name'])

    # ── Final dedup by name (keep first occurrence, prefer manual) ──
    deduped = {}
    # First pass: manual overrides take priority (normalize keys too)
    for mname, mdata in MANUAL_OVERRIDES.items():
        norm_name = normalize_apostrophe(mname)
        deduped[norm_name] = {'name': norm_name, **mdata}
    # Second pass: algo results (skip if name already in manual)
    for r in final:
        if r['name'] not in deduped:
            deduped[r['name']] = r

    # Filter out garbage names (too short, starts lowercase, contains bullet chars)
    cleaned_final = []
    for name, r in deduped.items():
        if not name or len(name) < 3:
            continue
        if not name[0].isupper():
            continue
        if '•' in name or '·' in name:
            continue
        # Skip if name looks like faction text fragment
        if name.endswith('.') and ',' in name:
            continue
        cleaned_final.append(r)

    return cleaned_final


def extract_points_from_line(s):
    nums = POINTS_PAT.findall(s)
    return int(nums[-1]) if nums else None

def extract_unit_from_bullet(s):
    """Clean bullet content: remove BOILERPLATE and trailing faction text."""
    if BOILERPLATE in s:
        s = s[:s.index(BOILERPLATE)].strip()
    m = POINTS_PAT.search(s)
    if m:
        after = s[m.end():].strip()
        if after and after[0].isupper() and (',' in after or after.endswith('.')):
            s = s[:m.end()].strip()
        else:
            s = s[:m.start()].strip()
    return s.rstrip(',. ').strip()

def extract_name_from_line(s):
    """
    Given a line like "Big Drogg Fort-kicker • 1 Gatebreaker Mega-Gargant 450 Bonesplitterz, ..."
    or "✹ Heralds of the Bone-tithe 510 This Regiment..."
    extract just the regiment name.
    """
    # Strip NEW marker and literal
    s = strip_markers(s)
    s = re.sub(r'^NEW\s+', '', s).strip()

    # Remove BOILERPLATE
    if BOILERPLATE in s:
        s = s[:s.index(BOILERPLATE)].strip()

    # Split on first bullet marker — name is before bullets
    name_part = re.split(r'\s*[•·]', s)[0].strip()

    # Keep everything UP TO the points number — that's the regiment name
    pts = extract_points_from_line(name_part)
    if pts:
        # Everything before the points number
        m = POINTS_PAT.search(name_part)
        if m:
            name_part = name_part[:m.start()].strip()

    # Remove trailing commas / periods
    name_part = name_part.rstrip(',. ').strip()

    # If name still has a comma (e.g. residual faction text), split at first comma
    if ',' in name_part:
        name_part = name_part[:name_part.find(',')].strip()

    return name_part or None


# ── DB upsert ─────────────────────────────────────────────────────────────────

def upsert_regiments(db_path, regiments):
    now = datetime.now(timezone.utc).isoformat()
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    cur.execute('DELETE FROM regiments_of_renown')
    for r in regiments:
        cur.execute(
            'INSERT INTO regiments_of_renown '
            '(name, points_cost, alliance, units_json, eligible_factions_json, is_new, created_at, updated_at) '
            'VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (r['name'], r['points_cost'], r['alliance'],
             json.dumps(r['units'], ensure_ascii=False),
             json.dumps(r['eligible_factions'], ensure_ascii=False),
             1 if r['is_new'] else 0, now, now)
        )
    con.commit()
    cur.execute('SELECT COUNT(*) FROM regiments_of_renown')
    total = cur.fetchone()[0]
    breakdown = {}
    for alliance in ('Mercenary', 'Order', 'Chaos', 'Death', 'Destruction'):
        cur.execute('SELECT COUNT(*) FROM regiments_of_renown WHERE alliance=?', (alliance,))
        breakdown[alliance] = cur.fetchone()[0]
    con.close()
    return total, breakdown


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    if os.path.exists(DB_PATH):
        shutil.copy2(DB_PATH, BAK_PATH)
        print(f"[D4] Backup → {BAK_PATH}")

    with open(CLEAN_MD, encoding='utf-8') as f:
        text = f.read()

    regiments = parse_ror_section(text)
    print(f"[D4] Parsed {len(regiments)} regiments from PDF")

    for r in regiments:
        pts_str = str(r['points_cost']) if r['points_cost'] else '???'
        flag = ' [NEW]' if r['is_new'] else ''
        print(f"  [{r['alliance']:12s}] {r['name']!r:52s} {pts_str:>4s}pts "
              f"u={len(r['units'])} f={len(r['eligible_factions'])}{flag}")

    total, breakdown = upsert_regiments(DB_PATH, regiments)
    print(f"\n[D4] Total regiments_of_renown rows: {total}")
    for alliance, cnt in breakdown.items():
        print(f"       {alliance}: {cnt}")


if __name__ == '__main__':
    main()
