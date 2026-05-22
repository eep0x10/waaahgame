"""
Extract warscroll + faction rules from official AoS 4e faction pack PDFs.
Populates:
  units.stats_json, weapons_json, abilities_json, keywords_json, lore_pt_md
  factions.rules_json, description_pt_md, pdf_source, pdf_imported_at

Idempotent: checks pdf_imported_at; skips already-done factions unless --force.
Output: JSON audit artifact per faction → /app/scripts/cache/aos_pdf_extract/<slug>.json
       Translation dict   → /app/scripts/cache/aos_terms_pt.json

Usage (inside Docker):
  # Dry-run (extract + cache JSON, no DB writes):
  python3 /app/scripts/extract_aos_factionpacks.py --dry-run

  # Full ingest:
  python3 /app/scripts/extract_aos_factionpacks.py

  # Force re-import of specific faction:
  python3 /app/scripts/extract_aos_factionpacks.py --force --faction seraphon

  # All factions, force:
  python3 /app/scripts/extract_aos_factionpacks.py --force
"""

import os
import re
import sys
import json
import sqlite3
import argparse
import unicodedata
from datetime import datetime, timezone

try:
    import pdfplumber
except ImportError:
    print("[FATAL] pdfplumber not installed. Run: pip install pdfplumber")
    sys.exit(1)

# ─── Paths ──────────────────────────────────────────────────────────────────

DB_PATH      = '/app/instance/waaahgame.db'
PDF_DIR      = '/app/scripts/cache/aos_pdfs'
CACHE_DIR    = '/app/scripts/cache/aos_pdf_extract'
TERMS_PATH   = '/app/scripts/cache/aos_terms_pt.json'

os.makedirs(CACHE_DIR, exist_ok=True)

# ─── PDF → faction slug mapping ─────────────────────────────────────────────

PDF_MAP = {
    'hedonites-of-slaanesh': 'eng_17-12_aos_factionpack_hedonites_of_slaanesh-aqiq6c6xox-dxnbnrgjrq.pdf',
    'seraphon':               'eng_17-12_aos_factionpack_seraphon-5pxcca69i8-xejqhlx9si.pdf',
    'sylvaneth':              'eng_17_12_aos_factionpack_sylvaneth-rlhjfon8tw-ewm5srhnkq.pdf',
    'fyreslayers':            'eng_24-09_aos_faction_pack_fyreslayers-hkrrlzil6w-rbyqezivzz.pdf',
    'daughters-of-khaine':    'eng_29-10_aos_faction_pack_daughters_of_khaine-sdzsvehm67-el9yk0kuie.pdf',
    'cities-of-sigmar':       'eng_aos_faction_cities_of_sigmar_jul_25-wc3uhm662s-yw6cp52u8y.pdf',
    'ogor-mawtribes':         'eng_aos_faction_pack_ogor_mawtribes_feb_25-xlqlumgo3x-gmvmgwt5ga.pdf',
    'sons-of-behemat':        'eng_aos_faction_pack_sons_of_behemat_feb25-pgkslka5gn-cdoku9c3vl.pdf',
}

# ─── Translation helpers ─────────────────────────────────────────────────────

def load_terms():
    if os.path.exists(TERMS_PATH):
        with open(TERMS_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


TERMS = load_terms()
_PHASE_MAP = TERMS.get('phases', {})
_MECH_MAP  = TERMS.get('common_mechanics', {})

# Combined replacement map (phases + mechanics), sorted longest-first to avoid partial replacements
_TRANS_MAP = {**_PHASE_MAP, **_MECH_MAP}
_TRANS_KEYS_SORTED = sorted(_TRANS_MAP.keys(), key=len, reverse=True)


def translate_body(text: str) -> str:
    """Apply known term substitutions to rule body text. Leaves untranslated phrases intact."""
    if not text:
        return text
    result = text
    for en in _TRANS_KEYS_SORTED:
        pt = _TRANS_MAP[en]
        result = result.replace(en, pt)
    return result


def todo(text: str) -> str:
    """Wrap text with a TODO marker - used for large prose blocks we can't reliably translate."""
    return f"[TODO: translate] {text}"

# ─── Text normalization helpers ───────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """Collapse whitespace, strip null bytes and common PDF artifacts."""
    if not text:
        return ''
    # Remove vertical bars and repeated chars from PDF column duplication artifacts
    text = re.sub(r'[^\x09\x0A\x0D\x20-\x7E -￿]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def slugify(name: str) -> str:
    """Convert a name to a URL slug for DB matching."""
    s = name.lower()
    # Remove accents
    s = unicodedata.normalize('NFKD', s)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    # Drop apostrophes/quotes
    s = re.sub(r"[''`''\"']", '', s)
    # Replace non-alnum with hyphen
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def clean_pdf_text(text: str) -> str:
    """
    Remove garbled/repeated chars typical in these PDFs.
    Two types of PDF rendering artifacts observed:
      1. Each letter doubled: 'CChhaarrggee' → 'Charge'  (2-column rendering glitch)
      2. Each letter N-tupled: 'ggggrrrraaaa' → 'gra'    (different rendering glitch)

    Strategy:
      - Only de-duplicate when a sequence of 3+ chars in the pattern (char)(char)(char)...
        appears AND the doubling pattern is consistent (every letter doubled).
        We detect this by checking if a run of ≥4 chars is all doubled pairs.
      - For runs of 6+ identical chars, always reduce to one.

    Preserves newlines — only collapses runs of spaces/tabs within a line.
    """
    if not text:
        return text

    def _dedupe_doubled(line: str) -> str:
        """
        Fix 'CChhaargge' → 'Charge' style artifacts.
        Only triggers when we see a run of 4+ chars that are all doubled pairs.
        """
        # Pattern: at least 3 consecutive doubled-letter pairs, e.g. ((X)\1){3,}
        # Each pair is exactly 2 identical chars. This handles "CChh" = 2 pairs.
        def _replace_doubled(m):
            s = m.group(0)
            # Undouble: keep every other character
            return s[::2]
        # Match sequences of doubled chars: (aa)(bb)(cc)... 3+ pairs minimum
        line = re.sub(r'(?:([a-zA-Z])\1){3,}', _replace_doubled, line)
        # Also fix single-letter runs of 6+: 'aaaaaaa' → 'a'
        line = re.sub(r'([a-zA-Z])\1{5,}', lambda m: m.group(1), line)
        return line

    # Process line by line to preserve newline structure
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        line = _dedupe_doubled(line)
        # Collapse multiple spaces/tabs within a line (NOT newlines)
        line = re.sub(r'[ \t]+', ' ', line).strip()
        cleaned.append(line)
    return '\n'.join(cleaned)


# ─── Stat block extraction ────────────────────────────────────────────────────

# Pattern for the header layout in warscroll pages:
# "MOVE\n5"\n• FACTION WARSCROLL •\nUNIT NAME\n..."
# Stats appear as: Move, Health, Save, Control scattered around the header
_WARSCROLL_HEADER_RE = re.compile(
    r'WARSCROLL\s*[•·]\s*(.*?)\s*[•·]',
    re.IGNORECASE | re.DOTALL
)
_WARSCROLL_MARKER_RE = re.compile(
    r'(?:SERAPHON|FYRESLAYERS|HEDONITES|SLAANESH|SYLVANETH|DAUGHTERS OF KHAINE|DAUGHTERS-OF-KHAINE|'
    r'CITIES OF SIGMAR|OGOR MAWTRIBES|SONS OF BEHEMAT|AOS|SPEARHEAD)\s+WARSCROLL',
    re.IGNORECASE
)

def extract_stats_from_page(text: str) -> dict:
    """
    Extract Move/Health/Save/Control from the warscroll header region.

    The PDF renders the stat box as scattered tokens across 3-8 lines.
    Observed patterns:
      - Move appears on a line like '5"' or '10"' before/near WARSCROLL marker
      - Health+Save appear together: '2 4+A V', 'L 9 5+A', 'L T 14 4+', 'L14 4+A'
      - Control appears after CONTROL keyword or as digit near end of stat block

    Returns dict with keys: move, health, save, control (string values).
    """
    stats = {}

    # ── Move: first occurrence of \d+" near the top of the page ─────────────
    m = re.search(r'^(\d+)"', text, re.MULTILINE)
    if m:
        stats['move'] = m.group(1) + '"'
    else:
        m = re.search(r'(\d+)"\s*[•·]?\s*(?:\w+\s+)*?WARSCROLL', text, re.IGNORECASE)
        if m:
            stats['move'] = m.group(1) + '"'
        else:
            # fallback: any \d+" in first 200 chars
            m = re.search(r'(\d+)"', text[:200])
            if m:
                stats['move'] = m.group(1) + '"'

    # ── Health + Save: find the pattern "L <digits> <digits>+" or "L<digits> <digits>+" ──
    # Patterns seen: "L 9 5+A", "L 2 4+A V", "L T 14 4+ S A", "L14 4+A", "L 6 4+A V"
    hs_m = re.search(
        r'L\s*T?\s*(\d{1,3})\s+(\d[+])',
        text[:600]
    )
    if hs_m:
        stats['health'] = hs_m.group(1)
        stats['save'] = hs_m.group(2) + '+'  if not hs_m.group(2).endswith('+') else hs_m.group(2)
    else:
        # Fallback: health+save on same stat-block line "A L 2 4+A V"
        hs_m = re.search(r'\bL\s*(\d{1,3})\s+(\d[+])', text[:400])
        if hs_m:
            stats['health'] = hs_m.group(1)
            raw_save = hs_m.group(2)
            stats['save'] = raw_save if raw_save.endswith('+') else raw_save + '+'

    # Clean up save: "4+A" → "4+"
    if 'save' in stats:
        stats['save'] = re.sub(r'A$', '', stats['save']).strip()
        if not stats['save'].endswith('+'):
            stats['save'] += '+'

    # ── Control: digit after CONTROL keyword ────────────────────────────────
    ctrl_m = re.search(r'CONTROL\s*[\n\r]+\s*(\d+)', text, re.IGNORECASE)
    if ctrl_m:
        stats['control'] = ctrl_m.group(1)
    else:
        # The control value appears after the stat box cluster, often as lone digit
        # Look for digit on its own line after "H\n<digit>"
        ctrl_m = re.search(r'\bH\s*[\n\r]+\s*(\d+)\s*[\n\r]+\s*CONTROL', text, re.IGNORECASE)
        if ctrl_m:
            stats['control'] = ctrl_m.group(1)
        else:
            ctrl_m = re.search(r'\n(\d+)\nCONTROL', text, re.IGNORECASE)
            if ctrl_m:
                stats['control'] = ctrl_m.group(1)

    return stats


# ─── Weapon table extraction ──────────────────────────────────────────────────

_WEAPON_HEADER_RE = re.compile(
    r'(RANGED WEAPONS|MELEE WEAPONS)\s+'
    r'(?:Rng\s+)?Atk\s+Hit\s+Wnd\s+Rnd\s+Dmg\s+Ability',
    re.IGNORECASE
)

_RANGED_HEADER_RE = re.compile(
    r'RANGED WEAPONS\s+(?:Range|Rng)\s+(?:Attacks?|Atk)\s+Hit\s+(?:Wound|Wnd)\s+(?:Rend|Rnd)\s+(?:Damage|Dmg)\s+Ability',
    re.IGNORECASE
)

def parse_weapon_line(line: str, wtype: str) -> dict | None:
    """
    Parse a weapon profile line. Format:
      <Name> [Rng] Atk Hit Wnd Rnd Dmg Ability
    e.g.:
      Sunbolt Gauntlet 12" D6 3+ 3+ 1 1 Shoot in Combat
      Celestite Weapon 2 3+ 3+ 1 1 -
    Returns a dict or None if parse fails.
    """
    line = normalize_text(line)
    if not line or len(line) < 8:
        return None

    # The last 5 fields are: Atk Hit Wnd Rnd Dmg (plus optional Ability after)
    # For ranged, there's also a Range field (e.g. 12")
    # We parse from right-to-left using regex

    # Pattern: NAME [RANGE] ATK HIT WND RND DMG [ABILITY]
    # ATK can be digit, D3, D6, 2D6, 1D6+1, etc.
    # HIT/WND are like 2+, 3+, 4+, 5+
    # RND/DMG can be digit, D3, D6, 2

    dice_pat = r'(?:\d+D\d+|\d+|D\d+)'   # matches: 2, D3, D6, 2D6, etc.
    rend_pat = r'(?:\d+|-)'               # rend can be a digit or '-' (zero rend in AoS 4e)
    stat_pat = rf'({dice_pat})\s+(\d[+])\s+(\d[+])\s+({rend_pat})\s+({dice_pat})'

    if wtype == 'RANGED WEAPONS':
        # Try with range field
        m = re.search(
            r'^(.+?)\s+(\d+"\s+)?'  + stat_pat + r'\s*(.*?)$',
            line
        )
        if m:
            name = normalize_text(m.group(1))
            rng  = (m.group(2) or '').strip()
            atk  = m.group(3)
            hit  = m.group(4)
            wnd  = m.group(5)
            rnd  = m.group(6)
            dmg  = m.group(7)
            abil = normalize_text(m.group(8) or '').strip('-').strip()
            if name and atk:
                return {
                    'Name': name,
                    'Type': 'RANGED WEAPONS',
                    'Rng': rng,
                    'Atk': atk, 'Hit': hit, 'Wnd': wnd,
                    'Rnd': rnd, 'Dmg': dmg,
                    'Abilities': abil,
                }
    else:
        m = re.search(r'^(.+?)\s+' + stat_pat + r'\s*(.*?)$', line)
        if m:
            name = normalize_text(m.group(1))
            atk  = m.group(2)
            hit  = m.group(3)
            wnd  = m.group(4)
            rnd  = m.group(5)
            dmg  = m.group(6)
            abil = normalize_text(m.group(7) or '').strip('-').strip()
            if name and atk:
                return {
                    'Name': name,
                    'Type': 'MELEE WEAPONS',
                    'Atk': atk, 'Hit': hit, 'Wnd': wnd,
                    'Rnd': rnd, 'Dmg': dmg,
                    'Abilities': abil,
                }
    return None


def extract_weapons_from_page(text: str) -> list:
    """Extract weapon profiles from a warscroll page text."""
    weapons = []
    lines = text.split('\n')
    current_type = None
    in_weapons = False

    for line in lines:
        line_clean = normalize_text(line)
        ul = line_clean.upper()

        if 'RANGED WEAPONS' in ul and ('ATK' in ul or 'RNG' in ul or 'ATTACKS' in ul):
            current_type = 'RANGED WEAPONS'
            in_weapons = True
            continue
        if 'MELEE WEAPONS' in ul and ('ATK' in ul or 'HIT' in ul or 'ATTACKS' in ul):
            current_type = 'MELEE WEAPONS'
            in_weapons = True
            continue

        # Stop weapon parsing at KEYWORDS section or ability blocks
        if ul.startswith('KEYWORDS') or ul.startswith('PASSIVE') or ul.startswith('ONCE PER') or ul.startswith('REACTION'):
            in_weapons = False
            current_type = None
            continue

        if in_weapons and current_type:
            # Skip header repeat lines
            if re.match(r'^(?:Rng|Atk|Hit|Wnd|Rnd|Dmg|Ability|Range|Attacks|Wound|Rend|Damage)', line_clean, re.IGNORECASE):
                continue
            # Skip empty or very short lines
            if len(line_clean) < 5:
                continue
            # Skip lines that are purely stat headers
            if re.match(r'^[-•]$', line_clean):
                continue

            w = parse_weapon_line(line_clean, current_type)
            if w:
                weapons.append(w)

    return weapons


# ─── Ability extraction ───────────────────────────────────────────────────────

# Timing prefix patterns
_TIMING_PREFIXES = [
    r'Once Per Battle(?:\s*\(Army\))?,\s*[\w\s]+Phase',
    r'Once Per Turn(?:\s*\(Army\))?,\s*[\w\s]+Phase',
    r'Once Per Phase(?:\s*\(Army\))?',
    r'Once Per Battle(?:\s*\(Army\))?',
    r'Once Per Turn(?:\s*\(Army\))?',
    r'(?:Start|End) of (?:Any|Your|the) (?:Turn|Phase|Battle Round)',
    r'(?:Your|Any) (?:Hero|Movement|Shooting|Combat) Phase',
    r'Deployment Phase',
    r'Passive',
    r'Reaction:\s*[^\n]+',
]
_TIMING_RE = re.compile(
    r'^(' + '|'.join(_TIMING_PREFIXES) + r')',
    re.IGNORECASE
)


def extract_abilities_from_page(text: str) -> list:
    """
    Extract named abilities from a warscroll page.

    Format observed in AoS 4e PDFs (2-column layout):
      <timing>
      ABILITY NAME: body text inline, possibly spanning
      multiple lines.

    Or:
      <timing>
      ABILITY NAME
      body text on next line.
    """
    abilities = []
    lines = text.split('\n')

    i = 0
    while i < len(lines):
        line = normalize_text(lines[i])
        m = _TIMING_RE.match(line)
        if not m:
            i += 1
            continue

        timing = m.group(0).strip()
        rest_of_timing_line = line[m.end():].strip()

        name_candidate = ''
        body_lines = []

        # Check for inline name on the timing line itself
        if rest_of_timing_line:
            inline_m = re.match(r"^([A-Z][A-Z\s'\-:!?,]{3,60}):\s*(.*)", rest_of_timing_line)
            if inline_m:
                upper_ratio = sum(1 for c in inline_m.group(1) if c.isupper()) / max(len(inline_m.group(1)), 1)
                if upper_ratio > 0.7:
                    name_candidate = inline_m.group(1).rstrip(':').strip()
                    if inline_m.group(2):
                        body_lines.append(inline_m.group(2))
            elif re.match(r"^[A-Z][A-Z\s'\-:,!?]{3,}$", rest_of_timing_line) and len(rest_of_timing_line) <= 70:
                name_candidate = rest_of_timing_line.rstrip(':').strip()

        j = i + 1
        while j < len(lines) and j < i + 25:
            next_line = normalize_text(lines[j])
            if not next_line:
                j += 1
                continue

            # Stop at next timing block, KEYWORDS, or warscroll marker
            if _TIMING_RE.match(next_line):
                break
            if re.match(r'^KEYWORDS', next_line, re.IGNORECASE) or 'WARSCROLL' in next_line.upper():
                break

            if not name_candidate:
                # Check for inline name: "ABILITY NAME: body text"
                inline_m = re.match(r"^([A-Z][A-Z\s'\-:!?,]{3,60}):\s*(.*)", next_line)
                if inline_m:
                    upper_ratio = sum(1 for c in inline_m.group(1) if c.isupper()) / max(len(inline_m.group(1)), 1)
                    if upper_ratio > 0.7:
                        name_candidate = inline_m.group(1).rstrip(':').strip()
                        if inline_m.group(2):
                            body_lines.append(inline_m.group(2))
                        j += 1
                        continue
                # Plain ALL CAPS name (3-70 chars)
                if re.match(r"^[A-Z][A-Z\s'\-!?]{2,}$", next_line) and 3 <= len(next_line) <= 70:
                    name_candidate = next_line.rstrip(':').strip()
                    j += 1
                    continue

            body_lines.append(next_line)
            j += 1

        if name_candidate:
            body = ' '.join(body_lines).strip()
            body = normalize_text(body)
            name_clean = name_candidate.rstrip(':').strip()
            abilities.append({
                'name': name_clean,
                'timing': timing,
                'description': body,
                'description_pt': translate_body(body),
            })
        i = j

    return abilities


def extract_keywords_from_page(text: str) -> list:
    """Extract KEYWORDS line from warscroll page."""
    # Look for KEYWORDS section: typically "Infantry, Champion..." followed by "KEYWORDS\nOrder, Faction, ..."
    kws = []
    lines = text.split('\n')
    for idx, line in enumerate(lines):
        l = normalize_text(line)
        if l.upper().startswith('KEYWORDS'):
            # Keywords may be on same line or next line
            kw_text = l[len('KEYWORDS'):].strip().lstrip(':').strip()
            if not kw_text and idx + 1 < len(lines):
                kw_text = normalize_text(lines[idx + 1])
            if kw_text:
                # Split by comma, strip, uppercase
                for kw in kw_text.split(','):
                    kw = kw.strip().upper()
                    if kw and len(kw) < 50:
                        kws.append(kw)
            break

    # Also look for unit type keywords at the bottom (Infantry, Cavalry, etc.)
    unit_type_re = re.compile(r'^(Infantry|Cavalry|Monster|Warmaster|Hero|Behemoth)[,\s]', re.IGNORECASE)
    for line in lines:
        l = normalize_text(line)
        if unit_type_re.match(l):
            parts = re.split(r'[,\n]', l)
            for p in parts:
                p = p.strip().upper()
                if p and len(p) < 40 and p not in kws:
                    kws.append(p)
            break

    return list(dict.fromkeys(kws))  # deduplicate preserving order


# ─── Warscroll page detection ─────────────────────────────────────────────────

def is_warscroll_page(text: str) -> bool:
    """Return True if this page contains a warscroll."""
    return bool(re.search(r'WARSCROLL', text, re.IGNORECASE) and
                (re.search(r'MELEE WEAPONS|RANGED WEAPONS', text, re.IGNORECASE) or
                 re.search(r'KEYWORDS', text, re.IGNORECASE)))


def extract_unit_name_from_page(text: str) -> str | None:
    """
    Extract the unit name from a warscroll page.

    These PDFs render the 4-stat box (Move/Health/Save/Control) as a 2-column
    layout where the box-frame characters T, H, S, A, L, V, E appear as
    lone letters on lines mixed together with the unit name fragments.

    Two observed patterns after the '• FACTION WARSCROLL •' marker line:

    Pattern A (compact) — name on same stat line:
        A L <health> <save>A V <UNIT NAME>
        L T <health> <save> S A <UNIT NAME>

    Pattern B (split) — name split over 1-3 lines:
        T H S <NAME_PART1>
        L <health> <save>A
        A V
        E E
        H <NAME_PART2>   [optional continuation]
        <digit> <NAME_PART3>  [rare continuation like "WITH ARK OF SOTEK"]

    Strategy: find the WARSCROLL marker line, then scan the next ~8 lines.
    Strip: single-letter tokens (T,H,S,A,L,V,E), numbers, save patterns (N+, NA),
    move values (N"), the date header.
    Collect remaining uppercase text tokens and join them.
    """
    lines = text.split('\n')

    # Short words that are valid parts of unit names (must NOT be stripped)
    _NAME_KEEP_WORDS = {'OF', 'ON', 'THE', 'WITH', 'AND', 'AT', 'IN', 'TO'}

    # Tokens to strip from the stat box header region
    # NOTE: single/double uppercase letters are junk UNLESS they are in _NAME_KEEP_WORDS
    _STAT_JUNK_1_2_LETTER = re.compile(r'^[A-Z]{1,2}$')
    _STAT_JUNK_NUM_RE = re.compile(
        r'^('
        r'\d{1,2}"'            # move value: 5", 10", 14"
        r'|\d{1,2}[+]A?'       # save: 4+, 4+A, 5+A, 6+A
        r'|\d{1,3}'            # bare numbers (health, control values)
        r'|MOVE|CONTROL|SAVE|HEALTH'
        r'|December\s+\d{4}|January\s+\d{4}|February\s+\d{4}|March\s+\d{4}'
        r'|April\s+\d{4}|May\s+\d{4}|June\s+\d{4}|July\s+\d{4}'
        r'|August\s+\d{4}|September\s+\d{4}|October\s+\d{4}|November\s+\d{4}'
        r')$',
        re.IGNORECASE
    )
    # Box-frame single letter junk (stat box corners/labels that are NOT name words)
    _JUNK_SINGLE_LETTERS = set('THSALVEH')

    # Tokens that definitely mark the end of the header region
    _END_TOKENS = {'KEYWORDS', 'RANGED WEAPONS', 'MELEE WEAPONS', 'CONTROL'}

    # Find warscroll marker line index
    ws_idx = None
    for i, line in enumerate(lines):
        l = normalize_text(line)
        if re.search(r'[•·]\s*\w+[\w\s]*?WARSCROLL\s*[•·]', l, re.IGNORECASE):
            ws_idx = i
            break
    if ws_idx is None:
        return None

    # Collect name fragments from the next 10 lines
    name_parts = []
    skip_next_digit = False   # flag: next lone digit is control value, skip it
    for i in range(ws_idx + 1, min(len(lines), ws_idx + 14)):
        raw = normalize_text(lines[i])
        if not raw:
            continue
        # Stop hard at weapon tables, keywords, or CONTROL keyword
        if raw.upper() in _END_TOKENS or re.match(r'^(KEYWORDS|RANGED WEAPONS|MELEE WEAPONS|CONTROL)', raw, re.IGNORECASE):
            break
        # Skip lone digits (health/control values) but don't stop yet — variant suffix may follow
        if re.match(r'^\d+$', raw):
            continue

        # Strip stat-junk tokens from this line, token by token
        line_parts = []
        for token in re.split(r'\s+', raw):
            if not token:
                continue
            token_up = token.upper()

            # Preserve known name words even if short
            if token_up in _NAME_KEEP_WORDS:
                # Only include if we already have a name started or next to name parts
                line_parts.append(token_up)
                continue

            # Skip numeric junk
            if _STAT_JUNK_NUM_RE.match(token):
                continue
            # Skip stat-value tokens: "18", "4+", "4+A", "9"
            if re.match(r'^\d+[+]?A?$', token):
                continue

            # 1-2 letter ALL-CAPS tokens
            if _STAT_JUNK_1_2_LETTER.match(token_up):
                # Single junk letters (box frame decorations)
                if len(token_up) == 1 and token_up in _JUNK_SINGLE_LETTERS:
                    continue
                # Two-letter tokens that aren't name words: skip
                if len(token_up) == 2 and token_up not in _NAME_KEEP_WORDS:
                    continue
                # Keep others (rare)
                line_parts.append(token_up)
                continue

            # Keep uppercase words (3+ chars = real name tokens)
            if re.match(r'^[A-Z][A-Z\'\-]+$', token) or re.match(r'^[A-Z]{3,}$', token):
                line_parts.append(token)
            elif re.match(r'^[A-Z][A-Za-z\'\-]+$', token) and len(token) > 2:
                # Mixed-case → uppercase it
                line_parts.append(token.upper())

        if line_parts:
            name_parts.extend(line_parts)

    if not name_parts:
        return None

    # Join and clean
    name = ' '.join(name_parts)
    name = re.sub(r'\s+', ' ', name).strip()
    # Remove leading/trailing junk chars
    name = name.strip('-').strip()

    if 3 <= len(name) <= 80:
        return name
    return None


def extract_lore_from_page(text: str) -> str:
    """Extract the lore paragraph(s) from a warscroll page (if present)."""
    # Lore usually appears in the bottom-right corner of 2-column warscrolls
    # In text extraction it often appears after the keywords block
    lines = text.split('\n')
    after_keywords = False
    lore_lines = []

    for line in lines:
        l = normalize_text(line)
        if l.upper().startswith('KEYWORDS') or 'ORDER,' in l.upper() or 'CHAOS,' in l.upper():
            after_keywords = True
            continue
        if after_keywords and l and len(l) > 20:
            # Stop at next section header
            if re.match(r'^[A-Z\s]{10,}$', l) and l.isupper():
                break
            lore_lines.append(l)

    if lore_lines:
        return ' '.join(lore_lines[:5])  # cap at ~5 sentences
    return ''


# ─── Section extractors (battle traits, formations, lores) ───────────────────

def is_section_header(line: str, header: str) -> bool:
    return line.strip().upper().startswith(header.upper())


_MAJOR_SECTION_RE = re.compile(
    r'^(BATTLE TRAITS|BATTLE FORMATIONS|HEROIC TRAITS|ARTEFACTS? OF POWER|'
    r'SPELL LORE|PRAYER LORE|MANIFESTATION LORE|BATTLE TACTICS|'
    r'SUB-FACTIONS?|SPEARHEAD|REGIMENT ABILITIES|ENHANCEMENTS?)$',
    re.IGNORECASE
)


def extract_rules_section(pages_text: list, section_keyword: str) -> list:
    """
    Generic extractor for rule sections (battle traits, formations, lores, etc.)

    PDF format: two-column layout with ability entries structured as:
        <timing line>
        ABILITY NAME: Description text continues here and may span
        multiple lines...

    Or more compactly:
        <timing line>
        ALL CAPS NAME: body text inline

    Garbled text (doubled chars from PDF renderer) is cleaned before parsing.
    Returns list of {name, text_en, text_pt, refs} items.
    Deduplicates by name to avoid double-extracting two-column entries.
    """
    rules = []
    seen_names = set()  # deduplicate across pages (same ability on facing pages)

    for page_num, text in enumerate(pages_text, 1):
        if section_keyword.upper() not in text.upper():
            continue

        # Clean garbled doubled chars before processing
        text = clean_pdf_text(text)
        lines = text.split('\n')
        in_section = False
        current_timing = None
        current_name = None
        current_body_lines = []

        def _flush():
            nonlocal current_timing, current_name, current_body_lines
            if current_name and current_body_lines:
                name_key = current_name.upper().strip()
                if name_key not in seen_names:
                    seen_names.add(name_key)
                    body = ' '.join(current_body_lines).strip()
                    # Remove doubled chars in body (missed by earlier clean)
                    body = normalize_text(body)
                    timing_str = current_timing or ''
                    full_text = (f"[{timing_str}] {body}" if timing_str else body)
                    rules.append({
                        'name': current_name.strip(),
                        'timing': timing_str,
                        'text_en': full_text,
                        'text_pt': translate_body(full_text),
                        'refs': f'p.{page_num}',
                    })
            current_timing = None
            current_name = None
            current_body_lines = []

        for line in lines:
            l = normalize_text(line)
            if not l:
                continue

            # Detect section start
            if not in_section:
                if section_keyword.upper() in l.upper() and len(l) < 60:
                    in_section = True
                continue

            # Stop at next major section (different from current)
            if _MAJOR_SECTION_RE.match(l) and l.upper() != section_keyword.upper():
                _flush()
                break

            # Timing line → start new entry
            m = _TIMING_RE.match(l)
            if m:
                _flush()
                current_timing = l.strip()
                # Sometimes the ability name follows on same line after timing:
                # "Passive ABILITY NAME: ..." — handle inline
                rest = l[m.end():].strip()
                if rest:
                    # Check if rest starts with an ALL-CAPS ability name
                    name_m = re.match(r"^([A-Z][A-Z\s'\-:,!?]{3,60}):\s*(.*)", rest)
                    if name_m:
                        current_name = name_m.group(1).rstrip(':').strip()
                        body_rest = name_m.group(2).strip()
                        if body_rest:
                            current_body_lines.append(body_rest)
                continue

            # Ability name: ALL CAPS followed by colon + description inline
            # e.g. "THE GREAT PLAN: The Seraphon look to..."
            # e.g. "TIMBERRRRR!: A dying gargant..."
            name_inline_m = re.match(
                r"^([A-Z][A-Z\s'\-:!?,]{3,60}):\s*(.*)",
                l
            )
            if name_inline_m:
                candidate_name = name_inline_m.group(1).rstrip(':').strip()
                # Must be mostly uppercase (allow digits and punctuation)
                upper_ratio = sum(1 for c in candidate_name if c.isupper()) / max(len(candidate_name), 1)
                if upper_ratio > 0.7:
                    _flush()
                    current_name = candidate_name
                    body_rest = name_inline_m.group(2).strip()
                    if body_rest:
                        current_body_lines.append(body_rest)
                    continue

            # Plain ALL CAPS line (name without colon) — less common
            if re.match(r"^[A-Z][A-Z\s'\-!?]{3,60}$", l) and not current_name:
                _flush()
                current_name = l.strip()
                continue

            # Body text: accumulate if we have a current entry
            if current_name or current_timing:
                # Skip sub-headers that are all caps and short (section noise)
                if re.match(r'^[A-Z\s]{2,30}$', l) and len(l.split()) <= 3 and l.isupper():
                    # Looks like a sub-header noise line (e.g. "Keywords Asterism")
                    # unless it looks like a continuation of rule text
                    pass
                else:
                    current_body_lines.append(l)

        _flush()

    return rules


def extract_sub_factions(pages_text: list) -> list:
    """Extract sub-faction entries (lodges, temples, cities, etc.)"""
    sub = []
    sub_keywords = ['LODGE', 'TEMPLE', 'MAWTRIBE', 'CITY', 'GROVE', 'PROCESSION',
                    'GREATFRAY', 'CONSTELLATION', 'ENCLAVE', 'TRIBE']

    for page_num, text in enumerate(pages_text, 1):
        # Sub-factions often have their own named sections
        for kw in sub_keywords:
            if kw in text.upper():
                # Extract block
                m = re.search(rf'([A-Z\s]+{kw}[A-Z\s]*)\n', text, re.IGNORECASE)
                if m:
                    name = m.group(1).strip()
                    if 3 <= len(name) <= 60:
                        # Get following text as body
                        idx = text.find(m.group(0))
                        body_chunk = text[idx + len(m.group(0)):idx + 600]
                        body_chunk = normalize_text(body_chunk)
                        if not any(s['name'] == name for s in sub):
                            sub.append({
                                'name': name,
                                'text_en': body_chunk[:400],
                                'text_pt': translate_body(body_chunk[:400]),
                                'refs': f'p.{page_num}',
                            })

    return sub


def extract_faction_intro(pages_text: list) -> str:
    """
    Extract faction lore/intro text (usually first 1-2 non-rules pages).
    Returns raw English text with [TODO: translate] marker.
    """
    intro_chunks = []
    for i, text in enumerate(pages_text[:4]):
        if any(kw in text.upper() for kw in ['BATTLE TRAITS', 'BATTLE FORMATIONS', 'HEROIC TRAITS',
                                               'WARSCROLL', 'SPELL LORE', 'PRAYER LORE']):
            continue
        # Skip single-word title pages
        lines = [normalize_text(l) for l in text.split('\n') if normalize_text(l)]
        if len(lines) > 2:
            intro_chunks.append(' '.join(lines))

    if intro_chunks:
        combined = ' '.join(intro_chunks)
        return f"[TODO: translate]\n\n{combined[:1500]}"
    return ''


# ─── Full PDF extractor ───────────────────────────────────────────────────────

def extract_pdf(faction_slug: str, pdf_filename: str) -> dict:
    """
    Extract all content from one faction PDF.
    Returns a dict with:
      warscrolls: list of unit data dicts
      faction_rules: dict with battle_traits, formations, etc.
      faction_intro: string
    """
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    if not os.path.exists(pdf_path):
        print(f"  [SKIP] PDF not found: {pdf_path}")
        return {}

    print(f"\n  Opening {pdf_filename} ...")

    warscrolls = []
    pages_text = []

    with pdfplumber.open(pdf_path) as pdf:
        print(f"  Pages: {len(pdf.pages)}")
        for page_num, page in enumerate(pdf.pages, 1):
            try:
                text = page.extract_text() or ''
                pages_text.append(text)
            except Exception as e:
                print(f"    [WARN] Page {page_num} extract error: {e}")
                pages_text.append('')

    # ── Warscroll pages ──────────────────────────────────────────────────────
    for page_num, text in enumerate(pages_text, 1):
        if not is_warscroll_page(text):
            continue
        # Skip SPEARHEAD warscrolls (simplified versions)
        if 'SPEARHEAD WARSCROLL' in text.upper():
            continue

        unit_name = extract_unit_name_from_page(text)
        if not unit_name:
            continue

        # Clean garbled chars from the name (clean_pdf_text on single-line name)
        unit_name_lines = unit_name.split('\n')
        unit_name = clean_pdf_text(unit_name).split('\n')[0].strip()
        unit_name = re.sub(r'\s+', ' ', unit_name).strip()

        # Skip manifestation warscrolls (BANISHMENT suffix — these are summoned
        # entities, not army units, and don't exist in the DB)
        if unit_name.upper().endswith('BANISHMENT'):
            continue

        # Skip if name extraction looks garbled (very long with common stop-words mixed in)
        if len(unit_name.split()) > 8:
            # Likely a parser overrun — skip
            continue

        stats    = extract_stats_from_page(text)
        weapons  = extract_weapons_from_page(text)
        abilities = extract_abilities_from_page(text)
        keywords  = extract_keywords_from_page(text)
        lore      = extract_lore_from_page(text)

        warscrolls.append({
            'name': unit_name,
            'page': page_num,
            'stats': stats,
            'weapons': weapons,
            'abilities': abilities,
            'keywords': keywords,
            'lore_en': lore,
            'lore_pt': todo(lore) if lore else '',
        })

    # ── Faction rules ────────────────────────────────────────────────────────
    faction_rules = {
        'battle_traits':       extract_rules_section(pages_text, 'BATTLE TRAITS'),
        'formations':          extract_rules_section(pages_text, 'BATTLE FORMATIONS'),
        'heroic_traits':       extract_rules_section(pages_text, 'HEROIC TRAITS'),
        'artefacts':           extract_rules_section(pages_text, 'ARTEFACTS OF POWER'),
        'spell_lores':         extract_rules_section(pages_text, 'SPELL LORE'),
        'prayer_lores':        extract_rules_section(pages_text, 'PRAYER LORE'),
        'manifestation_lores': extract_rules_section(pages_text, 'MANIFESTATION LORE'),
        'battle_tactics':      extract_rules_section(pages_text, 'BATTLE TACTICS'),
        'sub_factions':        extract_sub_factions(pages_text),
    }

    faction_intro = extract_faction_intro(pages_text)

    print(f"  Warscrolls found: {len(warscrolls)}")
    for key, val in faction_rules.items():
        if val:
            print(f"  {key}: {len(val)} entries")

    return {
        'faction_slug': faction_slug,
        'pdf_filename': pdf_filename,
        'extracted_at': datetime.now(timezone.utc).isoformat(),
        'warscrolls': warscrolls,
        'faction_rules': faction_rules,
        'faction_intro': faction_intro,
    }


# ─── DB utilities ─────────────────────────────────────────────────────────────

def load_db_units(conn, faction_slug: str) -> dict:
    """
    Return {slug: unit_id} for a faction, plus prefix-slug entries.
    Also loads cross-faction units like Kragnos that appear in multiple faction PDFs.
    """
    row = conn.execute(
        "SELECT id FROM factions WHERE slug=?", (faction_slug,)
    ).fetchone()
    if row is None:
        return {}
    faction_id = row[0]

    db_units = conn.execute(
        "SELECT id, slug, name FROM units WHERE faction_id=?", (faction_id,)
    ).fetchall()

    slug_map = {}
    for uid, slug, name in db_units:
        slug_map[slug] = uid
        # Index by slugified name (e.g. "Kroxigor Warspawned" → "kroxigor-warspawned")
        ns = slugify(name)
        if ns not in slug_map:
            slug_map[ns] = uid
        # Index by prefix: if DB name has comma suffix like "Glutos Orscollion, Lord of Gluttony"
        # add an entry for just "glutos-orscollion"
        comma_idx = name.find(',')
        if comma_idx > 0:
            prefix_slug = slugify(name[:comma_idx])
            if prefix_slug not in slug_map:
                slug_map[prefix_slug] = uid

    # Also load well-known cross-faction units (appear in multiple faction PDFs)
    # These are units not owned by this faction but printed in the book
    cross_faction_names = [
        'Kragnos, the End of Empires',
    ]
    for cf_name in cross_faction_names:
        cf_slug = slugify(cf_name)
        if cf_slug not in slug_map:
            row2 = conn.execute(
                "SELECT id FROM units WHERE slug=?", (cf_slug,)
            ).fetchone()
            if row2:
                slug_map[cf_slug] = row2[0]
                # Also add the comma-prefix version
                comma_idx = cf_name.find(',')
                if comma_idx > 0:
                    prefix_slug = slugify(cf_name[:comma_idx])
                    if prefix_slug not in slug_map:
                        slug_map[prefix_slug] = row2[0]

    return slug_map


def match_warscroll_to_unit(ws_name: str, slug_map: dict,
                            conn=None) -> int | None:
    """
    Try multiple slug normalizations to match a warscroll name to a DB unit.
    Also does prefix matching for cases where PDF name is a prefix of DB slug.
    If conn is provided, falls back to a global DB search for cross-faction units.
    """
    ws_name_clean = ws_name.strip()

    attempts = [
        ws_name_clean,
        re.sub(r',.*$', '', ws_name_clean).strip(),          # "X, The Y" → "X"
        re.sub(r'\(.*?\)', '', ws_name_clean).strip(),        # Remove parentheticals
        re.sub(r'^The\s+', '', ws_name_clean, flags=re.IGNORECASE),   # Remove leading "The"
        ws_name_clean.replace(' and ', ' & '),
        ws_name_clean.replace(' & ', ' and '),
        ws_name_clean.replace("'", ''),
    ]

    for attempt in attempts:
        s = slugify(attempt)
        if s in slug_map:
            return slug_map[s]

    ws_slug = slugify(ws_name_clean)
    if len(ws_slug) >= 6:  # avoid spurious short-prefix matches
        for db_slug, uid in slug_map.items():
            # Case A: PDF name is prefix of DB slug
            # "infernal-enrapturess" matches "infernal-enrapturess-herald-of-slaanesh"
            if db_slug.startswith(ws_slug + '-') or db_slug == ws_slug:
                return uid
            # Case B: DB slug is prefix of PDF name
            # "sisters-of-slaughter" matches "sisters-of-slaughter-with-sacrificial-knives"
            if len(db_slug) >= 6 and ws_slug.startswith(db_slug + '-'):
                return uid

    # Cross-faction fallback: search globally for the unit slug
    if conn is not None and len(ws_slug) >= 6:
        row = conn.execute("SELECT id FROM units WHERE slug=?", (ws_slug,)).fetchone()
        if row:
            return row[0]
        # Also try prefix match globally
        row = conn.execute(
            "SELECT id FROM units WHERE slug LIKE ?", (ws_slug + '-%',)
        ).fetchone()
        if row:
            return row[0]

    return None


def ingest_faction(conn, extracted: dict, dry_run: bool = False) -> dict:
    """
    Write extracted data to DB for one faction.
    Returns a summary dict.
    """
    faction_slug = extracted['faction_slug']
    pdf_filename = extracted['pdf_filename']
    warscrolls   = extracted.get('warscrolls', [])
    faction_rules = extracted.get('faction_rules', {})
    faction_intro = extracted.get('faction_intro', '')

    slug_map = load_db_units(conn, faction_slug)
    if not slug_map:
        print(f"  [WARN] Faction '{faction_slug}' not found in DB")
        return {'faction': faction_slug, 'error': 'faction not found'}

    matched = []
    unmatched = []

    for ws in warscrolls:
        unit_id = match_warscroll_to_unit(ws['name'], slug_map, conn)
        if unit_id is None:
            unmatched.append(ws['name'])
            continue
        matched.append(ws['name'])

        if not dry_run:
            # Build abilities list for DB
            abilities_db = []
            for ab in ws.get('abilities', []):
                abilities_db.append({
                    'name': ab['name'],
                    'timing': ab.get('timing', ''),
                    'description': ab.get('description', ''),
                    'description_pt': ab.get('description_pt', ''),
                })

            # Update unit row
            conn.execute("""
                UPDATE units SET
                    stats_json     = ?,
                    weapons_json   = ?,
                    abilities_json = ?,
                    keywords_json  = ?,
                    lore_pt_md     = ?
                WHERE id = ?
            """, (
                json.dumps(ws['stats']),
                json.dumps(ws['weapons']),
                json.dumps(abilities_db),
                json.dumps(ws['keywords']),
                ws.get('lore_pt', ''),
                unit_id,
            ))

    if not dry_run:
        # Update faction row
        conn.execute("""
            UPDATE factions SET
                rules_json       = ?,
                description_pt_md = ?,
                pdf_source       = ?,
                pdf_imported_at  = ?
            WHERE slug = ?
        """, (
            json.dumps(faction_rules),
            faction_intro,
            pdf_filename,
            datetime.now(timezone.utc).isoformat(),
            faction_slug,
        ))
        conn.commit()

    summary = {
        'faction': faction_slug,
        'warscrolls_in_pdf': len(warscrolls),
        'matched': len(matched),
        'unmatched': len(unmatched),
        'unmatched_names': unmatched,
        'battle_traits': len(faction_rules.get('battle_traits', [])),
        'formations': len(faction_rules.get('formations', [])),
        'heroic_traits': len(faction_rules.get('heroic_traits', [])),
        'artefacts': len(faction_rules.get('artefacts', [])),
        'spell_lores': len(faction_rules.get('spell_lores', [])),
        'prayer_lores': len(faction_rules.get('prayer_lores', [])),
        'manifestation_lores': len(faction_rules.get('manifestation_lores', [])),
        'battle_tactics': len(faction_rules.get('battle_tactics', [])),
        'sub_factions': len(faction_rules.get('sub_factions', [])),
        'dry_run': dry_run,
    }

    action = 'DRY-RUN' if dry_run else 'INGESTED'
    print(f"  [{action}] {faction_slug}: matched={len(matched)}/{len(warscrolls)} warscrolls")
    print(f"    battle_traits={summary['battle_traits']} formations={summary['formations']} "
          f"spell_lores={summary['spell_lores']} prayer_lores={summary['prayer_lores']} "
          f"manifestation_lores={summary['manifestation_lores']}")
    if unmatched:
        print(f"    UNMATCHED ({len(unmatched)}): {unmatched}")

    return summary


# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Extract AoS faction PDFs into DB')
    parser.add_argument('--dry-run', action='store_true',
                        help='Extract and cache JSON but do not write to DB')
    parser.add_argument('--force', action='store_true',
                        help='Re-import even if pdf_imported_at is set')
    parser.add_argument('--faction', type=str, default=None,
                        help='Process only this faction slug (default: all)')
    args = parser.parse_args()

    start_time = datetime.now()
    print(f"=== extract_aos_factionpacks.py ===")
    print(f"DB: {DB_PATH}")
    print(f"PDF dir: {PDF_DIR}")
    print(f"Cache dir: {CACHE_DIR}")
    print(f"Mode: {'DRY-RUN' if args.dry_run else 'INGEST'}")
    if args.force:
        print("  --force: will re-import already-done factions")

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    # Check which factions already have pdf_imported_at
    already_done = set()
    if not args.force:
        rows = conn.execute(
            "SELECT slug FROM factions WHERE pdf_imported_at IS NOT NULL"
        ).fetchall()
        already_done = {r[0] for r in rows}

    factions_to_process = list(PDF_MAP.keys())
    if args.faction:
        factions_to_process = [f for f in factions_to_process if f == args.faction]
        if not factions_to_process:
            print(f"[ERROR] Unknown faction slug: {args.faction}")
            print(f"  Known: {', '.join(PDF_MAP.keys())}")
            sys.exit(1)

    all_summaries = []

    for faction_slug in factions_to_process:
        pdf_filename = PDF_MAP[faction_slug]
        print(f"\n{'='*60}")
        print(f"FACTION: {faction_slug}")
        print(f"PDF: {pdf_filename}")

        if faction_slug in already_done and not args.force:
            print(f"  [SKIP] Already imported (use --force to re-import)")
            all_summaries.append({'faction': faction_slug, 'skipped': True})
            continue

        # Check cache
        cache_path = os.path.join(CACHE_DIR, f'{faction_slug}.json')
        extracted = None

        if os.path.exists(cache_path) and not args.force:
            print(f"  [CACHE] Loading cached extract from {cache_path}")
            try:
                with open(cache_path, 'r', encoding='utf-8') as f:
                    extracted = json.load(f)
            except Exception as e:
                print(f"  [WARN] Cache load failed: {e} — re-extracting")
                extracted = None

        if extracted is None:
            extracted = extract_pdf(faction_slug, pdf_filename)
            if not extracted:
                all_summaries.append({'faction': faction_slug, 'error': 'extraction failed'})
                continue
            # Save to cache
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(extracted, f, indent=2, ensure_ascii=False)
            print(f"  [CACHE] Saved to {cache_path}")

        summary = ingest_faction(conn, extracted, dry_run=args.dry_run)
        all_summaries.append(summary)

    conn.close()

    elapsed = (datetime.now() - start_time).total_seconds()

    print(f"\n{'='*60}")
    print(f"SUMMARY — {'DRY-RUN' if args.dry_run else 'INGEST'}")
    print(f"{'='*60}")
    print(f"Total time: {elapsed:.1f}s")
    print()

    total_matched = 0
    total_ws = 0
    all_unmatched = {}

    for s in all_summaries:
        if s.get('skipped'):
            print(f"  {s['faction']}: SKIPPED (already imported)")
            continue
        if s.get('error'):
            print(f"  {s['faction']}: ERROR — {s['error']}")
            continue
        m  = s.get('matched', 0)
        ws = s.get('warscrolls_in_pdf', 0)
        total_matched += m
        total_ws += ws
        rate = f"{m}/{ws}" if ws else "0/0"
        print(f"  {s['faction']}: units={rate} | "
              f"bt={s.get('battle_traits',0)} form={s.get('formations',0)} "
              f"spell={s.get('spell_lores',0)} prayer={s.get('prayer_lores',0)} "
              f"manif={s.get('manifestation_lores',0)} "
              f"hero={s.get('heroic_traits',0)} art={s.get('artefacts',0)} "
              f"sub={s.get('sub_factions',0)}")
        if s.get('unmatched_names'):
            all_unmatched[s['faction']] = s['unmatched_names']

    print(f"\n  Total warscroll match: {total_matched}/{total_ws}")

    if all_unmatched:
        print(f"\nUNMATCHED WARSCROLLS (need manual review):")
        for faction, names in all_unmatched.items():
            print(f"  {faction}: {names}")

    # Save summary JSON
    summary_path = os.path.join(CACHE_DIR, '_summary.json')
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump({
            'run_at': datetime.now(timezone.utc).isoformat(),
            'mode': 'dry_run' if args.dry_run else 'ingest',
            'elapsed_seconds': elapsed,
            'summaries': all_summaries,
        }, f, indent=2, ensure_ascii=False)
    print(f"\nSummary saved: {summary_path}")

    if args.dry_run:
        print("\nDRY-RUN complete — no DB writes. Re-run without --dry-run to ingest.")
    else:
        print("\nINGEST complete.")

    # Post-ingest verification queries
    if not args.dry_run:
        print("\n=== VERIFICATION ===")
        conn2 = sqlite3.connect(DB_PATH)
        for faction_slug in [s['faction'] for s in all_summaries if not s.get('skipped') and not s.get('error')]:
            row = conn2.execute(
                "SELECT id FROM factions WHERE slug=?", (faction_slug,)
            ).fetchone()
            if not row:
                continue
            fid = row[0]
            total = conn2.execute("SELECT COUNT(*) FROM units WHERE faction_id=?", (fid,)).fetchone()[0]
            has_stats = conn2.execute(
                "SELECT COUNT(*) FROM units WHERE faction_id=? AND stats_json != '{}'", (fid,)
            ).fetchone()[0]
            has_abilities = conn2.execute(
                "SELECT COUNT(*) FROM units WHERE faction_id=? AND abilities_json != '[]'", (fid,)
            ).fetchone()[0]
            frow = conn2.execute(
                "SELECT pdf_source, rules_json FROM factions WHERE slug=?", (faction_slug,)
            ).fetchone()
            bt_count = 0
            if frow and frow[1]:
                try:
                    rj = json.loads(frow[1])
                    bt_count = len(rj.get('battle_traits', []))
                except Exception:
                    pass
            print(f"  {faction_slug}: {has_stats}/{total} units have stats, "
                  f"{has_abilities}/{total} have abilities, "
                  f"battle_traits={bt_count}, pdf_source={frow[0] if frow else 'None'}")
        conn2.close()


if __name__ == '__main__':
    main()
