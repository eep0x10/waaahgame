#!/usr/bin/env python3
"""
D2: Import base_size_mm + unit_role for AoS units from battle_profiles.clean.md
Idempotent — safe to re-run.
"""
import os
import re
import sys
import shutil
from pathlib import Path

sys.path.insert(0, '/app')
from app import create_app, db
from app.models import Unit, Faction

app = create_app()

BATTLE_PROFILES_PATH = '/app/scripts/cache/aos_rules_extract/battle_profiles.clean.md'
DB_PATH = '/app/instance/waaahgame.db'

# ── Backup DB ────────────────────────────────────────────────────────────────
bak = DB_PATH + '.bak-metadata'
if not os.path.exists(bak):
    shutil.copy2(DB_PATH, bak)
    print(f'[backup] {bak}')
else:
    print(f'[backup] already exists: {bak}')

# ── Read PDF ─────────────────────────────────────────────────────────────────
pdf_text = Path(BATTLE_PROFILES_PATH).read_text(encoding='utf-8')
lines = pdf_text.splitlines()

# ── Helpers ──────────────────────────────────────────────────────────────────
def normalise(s):
    return re.sub(r'\s+', ' ', s).strip().lower()

def parse_base_size(raw):
    raw = raw.strip()
    mx = re.search(r'(\d+(?:\.\d+)?)\s*[×xX]\s*(\d+(?:\.\d+)?)\s*mm', raw, re.IGNORECASE)
    if mx:
        suffix = ' oval' if 'oval' in raw.lower() else ''
        return f'{mx.group(1)}x{mx.group(2)}mm{suffix}'
    mx = re.search(r'(\d+(?:\.\d+)?)\s*mm', raw, re.IGNORECASE)
    if mx:
        return f'{mx.group(1)}mm'
    return None

BASE_PAT = re.compile(
    r'((?:\d+(?:\.\d+)?)\s*[×xX]\s*(?:\d+(?:\.\d+)?)\s*mm(?:\s+(?:oval|round))?'
    r'|(?:\d+(?:\.\d+)?)\s*mm(?:\s+(?:oval|round))?)'
    r'(?:\s*\[\d+\].*)?$',
    re.IGNORECASE
)
BASE_ANY = re.compile(
    r'(?:\d+(?:\.\d+)?)\s*[×xX]\s*(?:\d+(?:\.\d+)?)\s*mm|(?:\d+(?:\.\d+)?)\s*mm',
    re.IGNORECASE
)
# Data line: starts with unit-size (1-20) then points (50-999)
DATA_START_PAT = re.compile(r'^\d{1,2}\s+\d{2,4}')

HEROES_HDR = re.compile(r'^HEROES\s+UNIT SIZE', re.IGNORECASE)
UNITS_HDR  = re.compile(r'^UNITS\s+UNIT SIZE', re.IGNORECASE)
# Match "WARHAMMER LEGENDS – ORDER/CHAOS/DEATH/DESTRUCTION" (grand-alliance suffix REQUIRED)
# These appear as page headers starting around page 59
LEGEND_SECTION_HDR = re.compile(r'^WARHAMMER LEGENDS\s*[–-]\s*(ORDER|CHAOS|DEATH|DESTRUCTION)', re.IGNORECASE)
EOHDR = re.compile(r'^TYPE\s+NAME\s+POINTS', re.IGNORECASE)

KNOWN_FACTIONS = {
    'CITIES OF SIGMAR', 'DAUGHTERS OF KHAINE', 'FYRESLAYERS', 'IDONETH DEEPKIN',
    'KHARADRON OVERLORDS', 'LUMINETH REALM-LORDS', 'SERAPHON', 'STORMCAST ETERNALS',
    'SYLVANETH', 'BLADES OF KHORNE', 'DISCIPLES OF TZEENTCH', 'HEDONITES OF SLAANESH',
    'HELSMITHS OF HASHUT', 'MAGGOTKIN OF NURGLE', 'SKAVEN', 'SLAVES TO DARKNESS',
    'FLESH-EATER COURTS', 'NIGHTHAUNT', 'OSSIARCH BONEREAPERS', 'SOULBLIGHT GRAVELORDS',
    'GLOOMSPITE GITZ', 'IRONJAWZ', 'KRULEBOYZ', 'OGOR MAWTRIBES', 'SONS OF BEHEMAT',
    'BEASTS OF CHAOS',
}

# ── Pre-process: join multi-line wrapped entries ──────────────────────────────
# Pattern A: "Name prefix" / "data+base" / optional "name suffix"
# Detect: line has words (starts with letter/✹), no base size, next line starts with \d{1,2} \d{2,4}
def _is_name_prefix(s):
    """Line that looks like a name fragment (words, no unit-size+points data start)."""
    s = s.strip()
    if not s:
        return False
    # Strip leading special chars (U+2739 ✹, U+2713 ✓, *, whitespace) then check for a letter
    # Use ord() to avoid source encoding issues with special characters
    stripped = s.lstrip(''.join([chr(0x2739), chr(0x2713), '*', ' ', '\t']))
    if not stripped or not re.match(r'^[A-Za-z]', stripped):
        return False
    if DATA_START_PAT.match(s):
        return False
    return True

def _is_name_suffix(s):
    """Short continuation line that is part of a unit name (not data, not a note line)."""
    s = s.strip()
    if not s:
        return False
    if DATA_START_PAT.match(s):
        return False
    if re.match(r'^(This unit|This Hero|®|APRIL|UPDATED|regiment as|battlepack|Play for|General)', s, re.IGNORECASE):
        return False
    if re.match(r'^\d', s):
        return False
    # Must be short (real name suffixes are short: "Plague Furnace", "Aggradon", "Greatbows")
    words = s.split()
    return len(words) <= 4

joined_lines = []
skip_next = set()
for i, raw in enumerate(lines):
    if i in skip_next:
        continue
    sl = raw.strip()
    nxt = lines[i+1].strip() if i+1 < len(lines) else ''
    nxt2 = lines[i+2].strip() if i+2 < len(lines) else ''

    # Pattern A: name-prefix line, next is data+base, optional name-suffix after
    if (_is_name_prefix(sl)
            and not BASE_ANY.search(sl)
            and DATA_START_PAT.match(nxt)
            and BASE_ANY.search(nxt)):
        # Check if line after data is a name suffix
        if _is_name_suffix(nxt2) and not BASE_ANY.search(nxt2):
            # 3-part: prepend name_prefix, append name_suffix
            joined = sl + ' __SUFFIX__ ' + nxt + ' ' + nxt2
            skip_next.add(i+1)
            skip_next.add(i+2)
        else:
            joined = sl + ' ' + nxt
            skip_next.add(i+1)
        joined_lines.append(joined)
        continue

    joined_lines.append(raw)

lines = joined_lines

# ── Pre-process pass 2: join data+no-base lines with next base-only line ──────
# Pattern B: line has name+data (unit-size+points) but NO base size,
# next line is ONLY a base size token (e.g. "32mm [1]")
BASE_ONLY_PAT = re.compile(
    r'^\s*(?:\d+(?:\.\d+)?(?:\s*[xX×]\s*\d+(?:\.\d+)?)?)\s*mm\s*(?:\[\d+\].*)?$',
    re.IGNORECASE
)
DATA_LINE_PAT = re.compile(r'\b\d{1,2}\s+\d{2,4}\b')

joined_lines2 = []
skip_set2 = set()
for i, raw in enumerate(lines):
    if i in skip_set2:
        continue
    sl = raw.strip()
    nxt = lines[i+1].strip() if i+1 < len(lines) else ''
    has_data = bool(DATA_LINE_PAT.search(sl))
    has_base = bool(BASE_ANY.search(sl))
    nxt_base_only = bool(BASE_ONLY_PAT.match(nxt))
    if has_data and not has_base and nxt_base_only:
        joined2 = sl + ' ' + nxt
        skip_set2.add(i+1)
        joined_lines2.append(joined2)
        continue
    joined_lines2.append(raw)

lines = joined_lines2
print(f'[preprocess] {len(lines)} logical lines after joining multi-line entries')

# ── Parse ─────────────────────────────────────────────────────────────────────
pdf_data = {}
legends_base_data = {}  # base_size only from legends section (no role override)
current_faction = None
current_section = None
in_legends = False

for i, raw_line in enumerate(lines):
    line = raw_line.strip()
    upper = line.upper().replace('–', '-')

    # Standalone Legends section header (page ~59 onward)
    if LEGEND_SECTION_HDR.match(line):
        in_legends = True
        current_section = None
        continue

    if in_legends:
        # Still extract base sizes from legends — just don't assign role
        m = BASE_PAT.search(line)
        if m:
            base_size = parse_base_size(m.group(1))
            STRIP_CHARS2 = chr(0x2739) + chr(0x2713) + '* \t'
            clean = line.strip().lstrip(STRIP_CHARS2).strip()
            nm = re.match(r'^(.*?)\s+(\d{1,2})\s+(\d{2,4})(?:\s*\([+-]\d+\))?\s', clean)
            if nm:
                name = nm.group(1).strip()
            else:
                name = clean[:m.start()].strip()
                name = re.sub(r'\s+\d+\s*$', '', name).strip()
            if name and not re.match(r'^\d+$', name) and len(name) >= 3 and base_size:
                key = normalise(name)
                if key not in legends_base_data:
                    legends_base_data[key] = base_size
        continue

    if upper in KNOWN_FACTIONS:
        current_faction = upper
        current_section = None
        continue

    if HEROES_HDR.match(line):
        current_section = 'HEROES'
        continue

    if UNITS_HDR.match(line):
        current_section = 'UNITS'
        continue

    if EOHDR.match(line):
        current_section = None
        continue

    # Skip note lines
    if re.match(r'^(This unit|This Hero|®|APRIL|UPDATED)', line, re.IGNORECASE):
        continue

    # Skip Scourge of Ghyran subsection lines (same units with different pts)
    if re.match(r'^(Scourge of Ghyran|✹ Scourge)', line, re.IGNORECASE):
        continue

    STRIP_CHARS = chr(0x2739) + chr(0x2713) + '* \t'  # ✹✓* and whitespace
    if current_section and current_faction and line:
        # Handle 3-part suffix marker FIRST (before BASE_PAT which requires $ anchor)
        # Format: "Name prefix __SUFFIX__ data+base name_suffix"
        suffix_name = None
        if '__SUFFIX__' in line:
            parts = line.split('__SUFFIX__', 1)
            name_prefix = parts[0].strip().lstrip(STRIP_CHARS).strip()
            remainder = parts[1]
            # Find base size in remainder (no $ anchor needed)
            suffix_m = BASE_ANY.search(remainder)
            if suffix_m:
                after_base = remainder[suffix_m.end():].strip()
                # Strip footnote noise like [1], [2]
                after_base = re.sub(r'^[\s,\[\d\]]+', '', after_base).strip()
                suffix_name = (name_prefix + ' ' + after_base).strip() if after_base else name_prefix
                base_size = parse_base_size(suffix_m.group(0))
            else:
                suffix_name = name_prefix
                base_size = None
            # Set line to the data part so role detection works
            line = remainder.strip()
            # Create a dummy m with base_size already set — just need a truthy m
            m = suffix_m
            if not m:
                continue
        else:
            m = BASE_PAT.search(line)
            if not m:
                continue
            base_size = parse_base_size(m.group(1))

        clean = line.strip().lstrip(STRIP_CHARS).strip()
        # Fix OCR split: "F reeguild" → "Freeguild"
        clean = re.sub(r'\bF\s+reeguild\b', 'Freeguild', clean)

        if suffix_name:
            name = suffix_name
        else:
            # Name = text before the first "small_int  points_int" pattern
            # Unit size is always a small integer (1–20), followed by points (50–999)
            nm = re.match(r'^(.*?)\s+(\d{1,2})\s+(\d{2,4})(?:\s*\([+-]\d+\))?\s', clean)
            if nm:
                name = nm.group(1).strip()
            else:
                name = clean[:m.start()].strip()
                name = re.sub(r'\s+\d+\s*$', '', name).strip()
                name = re.sub(r'\s+\d+\s*$', '', name).strip()

        if not name or re.match(r'^\d+$', name) or len(name) < 3:
            continue

        if current_section == 'HEROES':
            role = 'hero'
        else:
            lo = line.lower()
            if 'monster' in lo:
                role = 'monster'
            elif 'cavalry' in lo:
                role = 'cavalry'
            elif 'war machine' in lo:
                role = 'war_machine'
            else:
                role = 'infantry'

        key = normalise(name)
        if key not in pdf_data:
            pdf_data[key] = {'base_size': base_size, 'role': role, 'raw_name': name}
            # Also add singular form if key ends in 's' (for DB lookup with singular names)
            if key.endswith('s') and len(key) > 3:
                sing = key[:-1]
                if sing not in pdf_data:
                    pdf_data[sing] = {'base_size': base_size, 'role': role, 'raw_name': name}

print(f'[parse] Extracted {len(pdf_data)} unit entries from PDF')
for k, v in list(pdf_data.items())[:12]:
    print(f'  {k!r}: {v["base_size"]}, {v["role"]}')

# ── Update DB ─────────────────────────────────────────────────────────────────
with app.app_context():
    print('\n[db] Starting unit metadata import...')
    aos_fids = {f.id for f in Faction.query.filter(Faction.grand_alliance != None).all()}
    units = Unit.query.filter(Unit.faction_id.in_(aos_fids)).all()
    print(f'[db] AoS units: {len(units)}')

    updated_base = 0
    updated_role = 0
    not_found = []
    faction_stats = {}

    # Known name aliases: DB name → PDF key
    ALIASES = {
        'freeguild marshal and relic envoy': 'freeguild marshal and relic envoy',
        'hunters of huanchi with dartpipes': 'hunters of huanchi with dartpipes',
        'hunters of huanchi with starstone bolas': 'hunters of huanchi with starstone bolas',
        'saurus scar-veteran on aggradon': 'saurus scar-veteran on aggradon',
        'plague priest on plague furnace': 'plague priest on plague furnace',
        'vizzik skour, prophet of the horned rat': 'vizzik skour, prophet of the horned rat',
        'kurnoth hunters with kurnoth greatbows': 'kurnoth hunters with kurnoth greatbows',
        'kurnoth hunters with kurnoth greatswords': 'kurnoth hunters with kurnoth greatswords',
        'kurnoth hunters with kurnoth scythes': 'kurnoth hunters with kurnoth scythes',
        'archmage teclis and celennar, spirit of hysh': 'archmage teclis and celennar, spirit of hysh',
        'ellania and ellathor, eclipsian warsages': 'ellania and ellathor, eclipsian warsages',
        'brokk grungsson, lord-magnate of barak-nar': 'brokk grungsson, lord-magnate of barak-nar',
        'lord-imperatant': 'lord-imperatant',
        'knight-judicator with gryph-hounds': 'knight-judicator with gryph-hounds',
        'slaughter queen on cauldron of blood': 'slaughter queen on cauldron of blood',
        'herald of khorne on blood throne': 'herald of khorne on blood throne',
        'fateskimmer, herald of tzeentch on burning chariot': 'fateskimmer, herald of tzeentch on burning chariot',
        'gaunt summoner on disc of tzeentch': 'gaunt summoner on disc of tzeentch',
        'glutos orscollion, lord of gluttony': 'glutos orscollion, lord of gluttony',
        'bladebringer, herald on exalted chariot': 'bladebringer, herald on exalted chariot',
        'sevireth, lord of the seventh wind': 'sevireth, lord of the seventh wind',
        'lyrior uthralle, warden of ymetrica': 'lyrior uthralle, warden of ymetrica',
        'vanari lord regent on lightcourser': 'vanari lord regent on lightcourser',
        'lotann, warden of the soul ledgers': 'lotann, warden of the soul ledgers',
        'eidolon of mathlann, aspect of the sea': 'eidolon of mathlann, aspect of the sea',
        'battlemage on celestial hurricanum': 'battlemage on celestial hurricanum',
        'infernal enrapturess, herald of slaanesh': 'infernal enrapturess, herald of slaanesh',
        'spoilpox scrivener, herald of nurgle': 'spoilpox scrivener, herald of nurgle',
        'sloppity bilepiper, herald of nurgle': 'sloppity bilepiper, herald of nurgle',
        'vanguard-raptors with longstrike crossbows': 'vanguard-raptors with longstrike crossbows',
        'vanguard-raptors with hurricane crossbows': 'vanguard-raptors with hurricane crossbows',
        'vanguard-palladors with shock handaxes': 'vanguard-palladors with shock handaxes',
        'vanguard-palladors with starstrike javelins': 'vanguard-palladors with starstrike javelins',
        'annihilators with meteoric grandhammers': 'annihilators with meteoric grandhammers',
        'blue horrors and brimstone horrors': 'blue horrors and brimstone horrors',
        'sisters of slaughter with bladed bucklers': 'sisters of slaughter with bladed bucklers',
        'sisters of slaughter with sacrificial knives': 'sisters of slaughter with sacrificial knives',
        'witch aelves with paired sciansá': 'witch aelves with paired sciansá',
        'vulkite berzerkers with bladed slingshields': 'vulkite berzerkers with bladed slingshields',
        'vulkite berzerkers with fyresteel weapons': 'vulkite berzerkers with fyresteel weapons',
        'infernal razers with blunderbusses': 'infernal razers with blunderbusses',
        'dominator engine with bane maces': 'dominator engine with bane maces',
        'changecaster, herald of tzeentch': 'changecaster, herald of tzeentch',
        'freeguild fusiliers': 'freeguild fusiliers',
        'freeguild steelhelms': 'freeguild steelhelms',
        # Legends / name-mismatch extras
        'lord-castellant': 'lord-castellant',
        'celestar ballista': 'celestar ballista',
        'vanguard-raptors with longstrike crossbows': 'vanguard-raptors with longstrike crossbows',
        'pink horrors of tzeentch': 'pink horrors',
        'blue horrors of tzeentch': 'blue horrors of tzeentch',
        'witch aelves': 'witch aelves with bladed bucklers',
        'sisters of slaughter': 'sisters of slaughter with bladed bucklers',
        'troggboss': 'dankhold troggboss',
        'orruk warchanter': 'warchanter',
        'orruk weirdnob shaman': 'weirdnob shaman',
        'orruk brutes': 'brutes',
        'orruk ardboys': 'ardboys',
        'orruk gore-gruntas': 'gore-gruntas',
        'kruleboyz gutrippaz': 'gutrippaz',
        'savage orruk morboys': 'savage orruk morboys',
        'freeguild marshal': 'freeguild marshal and relic envoy',
        'freeguild crossbowmen': 'freeguild crossbowmen',
        'aether-khemist': 'aether-khemist',
        'arkanaut company': 'arkanaut company',
        'endrinmaster with dirigible suit': 'endrinmaster with dirigible suit',
        'thunderers': 'grundstok thunderers',
        'sloppity bilepiper herald of nurgle': 'sloppity bilepiper, herald of nurgle',
        'spoilpox scrivener herald of nurgle': 'spoilpox scrivener, herald of nurgle',
        "be'lakor, the dark master": "be'lakor, the dark master",
        'archaon the everchosen': 'archaon, the everchosen',
        'belladamma volga first of the vyrkos': 'belladamma volga,',
        'mannfred von carstein, mortarch of night': 'mannfred von carstein,',
        'valkia the bloody': 'valkia the bloody',
    }

    def lookup(key):
        """Try multiple key variants to find PDF entry."""
        # Direct
        e = pdf_data.get(key)
        if e: return e
        # Known alias
        alias = ALIASES.get(key)
        if alias:
            e = pdf_data.get(alias)
            if e: return e
        # Without trailing 's' (plural in PDF, singular in DB)
        e = pdf_data.get(key + 's')
        if e: return e
        e = pdf_data.get(key + 'es')
        if e: return e
        e = pdf_data.get(key + 'ers')
        if e: return e
        # Without leading 'the '
        e = pdf_data.get(re.sub(r'^the\s+', '', key).strip())
        if e: return e
        # Without 'with ...' suffix
        e = pdf_data.get(re.sub(r'\s+with\b.*$', '', key).strip())
        if e: return e
        # Without parentheticals
        e = pdf_data.get(re.sub(r'\s*\(.*?\)\s*', ' ', key).strip())
        if e: return e
        # Collapse spaces (handle 'F reeguild' type OCR splits)
        e = pdf_data.get(re.sub(r'\s+', '', key))
        if e: return e
        # Fuzzy: key without last word
        parts = key.rsplit(' ', 1)
        if len(parts) > 1:
            e = pdf_data.get(parts[0])
            if e: return e
        return None

    def lookup_legends_base(key):
        """Try to find base_size in legends section data."""
        b = legends_base_data.get(key)
        if b: return b
        alias = ALIASES.get(key)
        if alias:
            b = legends_base_data.get(alias)
            if b: return b
        # without 'the '
        b = legends_base_data.get(re.sub(r'^the\s+', '', key).strip())
        if b: return b
        # without 'with ...'
        b = legends_base_data.get(re.sub(r'\s+with\b.*$', '', key).strip())
        if b: return b
        return None

    for unit in units:
        key = normalise(unit.name)
        entry = lookup(key)

        fname = unit.faction.name if unit.faction else '?'
        faction_stats.setdefault(fname, {'found': 0, 'not_found': 0})

        if not entry:
            # Fallback: try legends section for base_size only
            legends_base = lookup_legends_base(key)
            if legends_base and not unit.base_size_mm:
                unit.base_size_mm = legends_base
                updated_base += 1
                faction_stats[fname]['found'] += 1
            else:
                not_found.append((unit.name, fname))
                faction_stats[fname]['not_found'] += 1
            continue

        faction_stats[fname]['found'] += 1
        if entry['base_size'] and not unit.base_size_mm:
            unit.base_size_mm = entry['base_size']
            updated_base += 1
        if entry['role'] and not unit.unit_role:
            unit.unit_role = entry['role']
            updated_role += 1

    db.session.commit()

    print(f'\n[result] Updated base_size_mm: {updated_base}')
    print(f'[result] Updated unit_role:     {updated_role}')
    print(f'[result] Not matched:           {len(not_found)}')

    print('\n── Per-faction summary ──')
    for fname, stats in sorted(faction_stats.items()):
        print(f'  {fname}: found={stats["found"]}, not_found={stats["not_found"]}')

    if not_found:
        print(f'\n── Unmatched ({len(not_found)}) ──')
        for uname, fname in not_found[:20]:
            print(f'  [{fname}] {uname}')

    total_base = Unit.query.filter(Unit.faction_id.in_(aos_fids), Unit.base_size_mm.isnot(None)).count()
    total_role = Unit.query.filter(Unit.faction_id.in_(aos_fids), Unit.unit_role.isnot(None)).count()
    total = Unit.query.filter(Unit.faction_id.in_(aos_fids)).count()
    print(f'\n[final] base_size_mm: {total_base}/{total}')
    print(f'[final] unit_role:     {total_role}/{total}')
