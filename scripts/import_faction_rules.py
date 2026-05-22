#!/usr/bin/env python3
"""
D3: Backfill Faction.rules_json for 18 missing AoS factions.
    Also fixes Cities of Sigmar (2 -> 6 formations).

Data source: scripts/cache/aos_rules_extract/battle_profiles.clean.md
  - Parses the TYPE NAME POINTS section at the end of each faction block.
  - Populates formations, heroic_traits, artefacts, spell_lores, prayer_lores,
    manifestation_lores keys with names only (no rules text).
  - Factions that already have rules_json from faction pack PDFs are NOT
    overwritten (idempotent), EXCEPT for the formations list which is updated
    to match the authoritative PDF count.

Idempotent: safe to re-run.
"""
import os
import re
import sys
import json
import shutil
from pathlib import Path

sys.path.insert(0, '/app')
from app import create_app, db
from app.models import Faction

app = create_app()

BATTLE_PROFILES_PATH = '/app/scripts/cache/aos_rules_extract/battle_profiles.clean.md'
DB_PATH = '/app/instance/waaahgame.db'

# ── Backup DB ────────────────────────────────────────────────────────────────
bak = DB_PATH + '.bak-d3'
if not os.path.exists(bak):
    shutil.copy2(DB_PATH, bak)
    print(f'[backup] {bak}')
else:
    print(f'[backup] already exists: {bak}')

# ── Read PDF ─────────────────────────────────────────────────────────────────
pdf_text = Path(BATTLE_PROFILES_PATH).read_text(encoding='utf-8')
lines = pdf_text.splitlines()

# ── Faction name normalisation ────────────────────────────────────────────────
KNOWN_FACTIONS = {
    'CITIES OF SIGMAR', 'DAUGHTERS OF KHAINE', 'FYRESLAYERS', 'IDONETH DEEPKIN',
    'KHARADRON OVERLORDS', 'LUMINETH REALM-LORDS', 'SERAPHON', 'STORMCAST ETERNALS',
    'SYLVANETH', 'BLADES OF KHORNE', 'DISCIPLES OF TZEENTCH', 'HEDONITES OF SLAANESH',
    'HELSMITHS OF HASHUT', 'MAGGOTKIN OF NURGLE', 'SKAVEN', 'SLAVES TO DARKNESS',
    'FLESH-EATER COURTS', 'NIGHTHAUNT', 'OSSIARCH BONEREAPERS', 'SOULBLIGHT GRAVELORDS',
    'GLOOMSPITE GITZ', 'IRONJAWZ', 'KRULEBOYZ', 'OGOR MAWTRIBES', 'SONS OF BEHEMAT',
    'BEASTS OF CHAOS',
}

# DB faction name -> PDF faction name
FACTION_PDF_MAP = {
    'Cities of Sigmar':      'CITIES OF SIGMAR',
    'Daughters of Khaine':   'DAUGHTERS OF KHAINE',
    'Fyreslayers':           'FYRESLAYERS',
    'Idoneth Deepkin':       'IDONETH DEEPKIN',
    'Kharadron Overlords':   'KHARADRON OVERLORDS',
    'Lumineth Realm-Lords':  'LUMINETH REALM-LORDS',
    'Seraphon':              'SERAPHON',
    'Stormcast Eternals':    'STORMCAST ETERNALS',
    'Sylvaneth':             'SYLVANETH',
    'Blades of Khorne':      'BLADES OF KHORNE',
    'Disciples of Tzeentch': 'DISCIPLES OF TZEENTCH',
    'Hedonites of Slaanesh': 'HEDONITES OF SLAANESH',
    'Helsmiths of Hashut':   'HELSMITHS OF HASHUT',
    'Maggotkin of Nurgle':   'MAGGOTKIN OF NURGLE',
    'Skaven':                'SKAVEN',
    'Slaves to Darkness':    'SLAVES TO DARKNESS',
    'Flesh-Eater Courts':    'FLESH-EATER COURTS',
    'Nighthaunt':            'NIGHTHAUNT',
    'Ossiarch Bonereapers':  'OSSIARCH BONEREAPERS',
    'Soulblight Gravelords': 'SOULBLIGHT GRAVELORDS',
    'Gloomspite Gitz':       'GLOOMSPITE GITZ',
    'Ironjawz':              'IRONJAWZ',
    'Kruleboyz':             'KRULEBOYZ',
    'Ogor Mawtribes':        'OGOR MAWTRIBES',
    'Sons of Behemat':       'SONS OF BEHEMAT',
    'Beasts of Chaos':       'BEASTS OF CHAOS',
    # Orruk Warclans covers both IRONJAWZ and KRULEBOYZ — handled separately
}

# ── Patterns ──────────────────────────────────────────────────────────────────
LEGEND_SECTION_HDR = re.compile(r'^WARHAMMER LEGENDS\s*[–-]\s*(ORDER|CHAOS|DEATH|DESTRUCTION)', re.IGNORECASE)
EOHDR = re.compile(r'^TYPE\s+NAME\s+POINTS', re.IGNORECASE)
# Enhancement line: TYPE is one of these exact strings
ENHANCEMENT_TYPES = {
    'Battle Formation', 'Heroic Trait', 'Artefact of Power', 'Spell Lore',
    'Prayer Lore', 'Manifestation Lore', 'Faction Terrain', 'Battle Tactic',
    'Grand Strategy',
}
ENH_LINE_PAT = re.compile(
    r'^(Battle Formation|Heroic Trait|Artefact of Power|Spell Lore|Prayer Lore'
    r'|Manifestation Lore|Faction Terrain|Battle Tactic|Grand Strategy)'
    r'\s+(.+?)\s+(\d+(?:\s*\(\S+\))?)\s+(.*?)$',
    re.IGNORECASE
)

# ── Parse enhancements per faction ────────────────────────────────────────────
faction_enhancements = {}  # pdf_faction_key -> {type -> [name]}
current_faction = None
in_legends = False
in_eoh = False  # in enhancements-of-honour table

for i, raw_line in enumerate(lines):
    line = raw_line.strip()
    upper = line.upper().replace('–', '-')

    if LEGEND_SECTION_HDR.match(line):
        in_legends = True
        continue
    if in_legends:
        continue

    if upper in KNOWN_FACTIONS:
        current_faction = upper
        in_eoh = False
        continue

    if EOHDR.match(line) and current_faction:
        in_eoh = True
        continue

    # End of enhancement block: blank line or page boundary or new faction
    if in_eoh and (not line or line.startswith('---') or line.startswith('<!--')):
        in_eoh = False
        continue

    if in_eoh and current_faction:
        m = ENH_LINE_PAT.match(line)
        if m:
            etype = m.group(1).strip()
            ename = m.group(2).strip()
            faction_enhancements.setdefault(current_faction, {}).setdefault(etype, [])
            faction_enhancements[current_faction][etype].append(ename)

print(f'[parse] Factions with enhancements: {len(faction_enhancements)}')
for fname, etypes in sorted(faction_enhancements.items()):
    counts = {t: len(n) for t, n in etypes.items()}
    print(f'  {fname}: {counts}')

# ── Map enhancement types to rules_json keys ─────────────────────────────────
TYPE_TO_KEY = {
    'Battle Formation':    'formations',
    'Heroic Trait':        'heroic_traits',
    'Artefact of Power':   'artefacts',
    'Spell Lore':          'spell_lores',
    'Prayer Lore':         'prayer_lores',
    'Manifestation Lore':  'manifestation_lores',
    'Battle Tactic':       'battle_tactics',
    'Faction Terrain':     None,  # not stored in rules_json
    'Grand Strategy':      None,  # not stored in rules_json
}

def build_rules_json_stub(pdf_key):
    """Build minimal rules_json dict from PDF enhancement names only."""
    enhs = faction_enhancements.get(pdf_key, {})
    rj = {
        'battle_traits':        [],
        'formations':           [],
        'heroic_traits':        [],
        'artefacts':            [],
        'spell_lores':          [],
        'prayer_lores':         [],
        'manifestation_lores':  [],
        'battle_tactics':       [],
        'sub_factions':         [],
    }
    for etype, names in enhs.items():
        key = TYPE_TO_KEY.get(etype)
        if not key:
            continue
        if key == 'formations':
            rj['formations'] = [{'name': n, 'units': '', 'text_pt': ''} for n in names]
        elif key == 'heroic_traits':
            rj['heroic_traits'] = [{'name': n} for n in names]
        elif key == 'artefacts':
            rj['artefacts'] = [{'name': n} for n in names]
        elif key in ('spell_lores', 'prayer_lores', 'manifestation_lores'):
            rj[key] = [{'name': n} for n in names]
        elif key == 'battle_tactics':
            rj['battle_tactics'] = [{'name': n} for n in names]
    return rj

# ── Update DB ─────────────────────────────────────────────────────────────────
with app.app_context():
    print('\n[db] Starting faction rules backfill...')
    aos_factions = Faction.query.filter(Faction.grand_alliance != None).all()
    print(f'[db] AoS factions: {len(aos_factions)}')

    updated_new = 0
    updated_formations = 0
    skipped = 0
    orruk_warclans = None

    for faction in aos_factions:
        pdf_key = FACTION_PDF_MAP.get(faction.name)
        if pdf_key is None:
            # Orruk Warclans = IRONJAWZ + KRULEBOYZ combined
            if faction.name == 'Orruk Warclans':
                orruk_warclans = faction
            continue

        pdf_data = faction_enhancements.get(pdf_key, {})
        if not pdf_data:
            print(f'  [skip] {faction.name}: no PDF data found')
            skipped += 1
            continue

        if faction.rules_json:
            # Already has rules — only update formations count
            existing = json.loads(faction.rules_json)
            pdf_formations = pdf_data.get('Battle Formation', [])
            if pdf_formations:
                new_formations = [{'name': n, 'units': '', 'text_pt': ''} for n in pdf_formations]
                if len(new_formations) != len(existing.get('formations', [])):
                    old_count = len(existing.get('formations', []))
                    existing['formations'] = new_formations
                    faction.rules_json = json.dumps(existing, ensure_ascii=False)
                    updated_formations += 1
                    print(f'  [update-formations] {faction.name}: {old_count} -> {len(new_formations)}')
            skipped += 1
        else:
            # New faction — build stub from PDF
            stub = build_rules_json_stub(pdf_key)
            faction.rules_json = json.dumps(stub, ensure_ascii=False)
            updated_new += 1
            f_counts = {k: len(v) for k, v in stub.items() if v}
            print(f'  [new] {faction.name}: {f_counts}')

    # Orruk Warclans: combine IRONJAWZ + KRULEBOYZ
    if orruk_warclans:
        ironjawz_data = faction_enhancements.get('IRONJAWZ', {})
        kruleboyz_data = faction_enhancements.get('KRULEBOYZ', {})
        combined = {}
        for etype in set(list(ironjawz_data.keys()) + list(kruleboyz_data.keys())):
            names = list(ironjawz_data.get(etype, [])) + list(kruleboyz_data.get(etype, []))
            if names:
                combined[etype] = names
        if combined:
            # Build stub from combined data
            rj = {
                'battle_traits': [], 'formations': [], 'heroic_traits': [],
                'artefacts': [], 'spell_lores': [], 'prayer_lores': [],
                'manifestation_lores': [], 'battle_tactics': [], 'sub_factions': [],
            }
            for etype, names in combined.items():
                key = TYPE_TO_KEY.get(etype)
                if not key: continue
                if key == 'formations':
                    rj['formations'] = [{'name': n, 'units': '', 'text_pt': ''} for n in names]
                elif key == 'heroic_traits':
                    rj['heroic_traits'] = [{'name': n} for n in names]
                elif key == 'artefacts':
                    rj['artefacts'] = [{'name': n} for n in names]
                elif key in ('spell_lores', 'prayer_lores', 'manifestation_lores'):
                    rj[key] = [{'name': n} for n in names]
                elif key == 'battle_tactics':
                    rj['battle_tactics'] = [{'name': n} for n in names]
            orruk_warclans.rules_json = json.dumps(rj, ensure_ascii=False)
            updated_new += 1
            print(f'  [new] Orruk Warclans (combined): formations={len(rj["formations"])} heroic_traits={len(rj["heroic_traits"])} artefacts={len(rj["artefacts"])}')

    db.session.commit()

    print(f'\n[result] New rules_json:      {updated_new}')
    print(f'[result] Updated formations:  {updated_formations}')
    print(f'[result] Skipped (unchanged): {skipped}')

    # Summary
    total_with = Faction.query.filter(
        Faction.grand_alliance != None,
        Faction.rules_json != None
    ).count()
    total = Faction.query.filter(Faction.grand_alliance != None).count()
    print(f'\n[final] Factions with rules_json: {total_with}/{total}')
