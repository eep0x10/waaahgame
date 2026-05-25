#!/usr/bin/env python3
"""
PDF Reconciliation Script – AoS4 DB vs April 2026 Battle Profiles PDF
Reads scripts/cache/aos_rules_extract/battle_profiles.clean.md and reconciles DB.
"""
import re
import sys
import os

PDF_PATH = '/app/scripts/cache/aos_rules_extract/battle_profiles.clean.md'

# ---------------------------------------------------------------------------
# STEP 1 – Parse the PDF extract into a structured list of unit records
# ---------------------------------------------------------------------------

def normalize(name):
    """Lowercase, strip leading/trailing whitespace, collapse internal spaces,
    remove OCR artefacts (✹), strip trailing punctuation variations.
    Normalizes Unicode apostrophes/quotes to ASCII equivalents."""
    name = name.strip()
    name = re.sub(r'[✹®\*]', '', name)
    # Normalize curly quotes and special apostrophes to straight ASCII
    name = name.replace('‘', "'").replace('’', "'")  # '' → '
    name = name.replace('“', '"').replace('”', '"')  # "" → "
    name = name.replace('′', "'")  # prime → '
    name = re.sub(r'\s+', ' ', name)
    name = name.strip().lower()
    # Strip trailing punctuation that sometimes appears
    name = name.rstrip('.,;:')
    return name


def parse_pdf(path):
    """
    Returns a dict:
      pdf_units[normalized_name] = {
          'raw_name': str,
          'section': 'main' | 'manifestation' | 'legends',
          'faction_slug': str,   # e.g. 'cities-of-sigmar'
      }
    When a name appears in both main and legends, main wins.
    """
    FACTION_SLUG = {
        # ORDER
        'CITIES OF SIGMAR': 'cities-of-sigmar',
        'DAUGHTERS OF KHAINE': 'daughters-of-khaine',
        'FYRESLAYERS': 'fyreslayers',
        'IDONETH DEEPKIN': 'idoneth-deepkin',
        'KHARADRON OVERLORDS': 'kharadron-overlords',
        'LUMINETH REALM-LORDS': 'lumineth-realm-lords',
        'SERAPHON': 'seraphon',
        'STORMCAST ETERNALS': 'stormcast-eternals',
        'SYLVANETH': 'sylvaneth',
        # CHAOS
        'BLADES OF KHORNE': 'blades-of-khorne',
        'DISCIPLES OF TZEENTCH': 'disciples-of-tzeentch',
        'HEDONITES OF SLAANESH': 'hedonites-of-slaanesh',
        'HELSMITHS OF HASHUT': 'helsmiths-of-hashut',
        'MAGGOTKIN OF NURGLE': 'maggotkin-of-nurgle',
        'SKAVEN': 'skaven',
        'SLAVES TO DARKNESS': 'slaves-to-darkness',
        'BEASTS OF CHAOS': 'beasts-of-chaos',
        # DEATH
        'FLESH-EATER COURTS': 'flesh-eater-courts',
        'NIGHTHAUNT': 'nighthaunt',
        'OSSIARCH BONEREAPERS': 'ossiarch-bonereapers',
        'SOULBLIGHT GRAVELORDS': 'soulblight-gravelords',
        # DESTRUCTION
        'GLOOMSPITE GITZ': 'gloomspite-gitz',
        'IRONJAWZ': 'ironjawz',
        'KRULEBOYZ': 'kruleboyz',
        'OGOR MAWTRIBES': 'ogor-mawtribes',
        'SONS OF BEHEMAT': 'sons-of-behemat',
        # LEGENDS ONLY (Bonesplitterz appear only in legends)
        'BONESPLITTERZ': 'bonesplitterz',
    }

    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # ---- First pass: find line numbers of section boundaries ----
    # The PDF has a CONTENTS page (pages 1-2) that mentions these headers
    # before the actual content. We need to skip the contents section.
    # Page markers are: <!-- page N -->
    # Pages 1-2 = contents. Actual sections start from page 3.
    # Strategy: track page number; only fire section transitions after page 2.

    current_section = 'preamble'  # will become 'main' once we pass page 2
    current_faction = None
    current_page = 0

    pdf_units = {}   # normalized_name -> record

    # These table-header-like lines must be skipped
    SKIP_LINES_UPPER = {
        'HEROES UNIT SIZE POINTS REGIMENT OPTIONS NOTES BASE SIZE',
        'UNITS UNIT SIZE POINTS RELEVANT KEYWORDS NOTES BASE SIZE',
        'LEGENDS HEROES UNIT SIZE POINTS REGIMENT OPTIONS NOTES BASE SIZE',
        'LEGENDS UNITS UNIT SIZE POINTS RELEVANT KEYWORDS NOTES BASE SIZE',
        'TYPE NAME POINTS NOTES',
        'NAME POINTS NOTES',
        'UNIT SUMMARY POINTS NOTES',
        'REGIMENTS',
        'ORDER', 'CHAOS', 'DEATH', 'DESTRUCTION', 'MERCENARY',
        'NEW', 'UPDATED',
    }

    # Patterns that indicate non-unit rows (Battle Formation, Heroic Trait, etc.)
    NON_UNIT_PREFIXES_LOWER = (
        'battle formation', 'heroic trait', 'artefact of power',
        'spell lore', 'prayer lore', 'manifestation lore', 'faction terrain',
        'great endrinworks', 'skyvessel upgrade', 'mark of vulcatrix',
        'monstrous trait', 'big name', 'ensorcelled banner',
        'scourge of ghyran',
        'type name', 'unit summary',
    )

    # Manifestation unit names from page 53
    MANIFESTATION_NAMES = {
        'krondspine incarnate',
        'forbidden power',
        'morbid conjuration',
        'aetherwrought machineries',
        'primal energy',
        'twilit sorceries',
    }

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Track page number
        page_match = re.match(r'^<!--\s*page\s+(\d+)\s*-->', line)
        if page_match:
            current_page = int(page_match.group(1))
            if current_page >= 3 and current_section == 'preamble':
                current_section = 'main'
            continue

        # Skip page markers and decorative lines
        if line.startswith('<!--') or line.startswith('---') or line.startswith('#') or line.startswith('®'):
            continue
        if line.startswith('APRIL 2026'):
            continue

        # Skip legal/copyright text
        if any(x in line for x in ['©', 'Games Workshop', 'warhammer-community.com',
                                     'Permission to download', 'This is a work of fiction',
                                     'With thanks', 'PRODUCED BY', 'Nottingham', 'Dublin',
                                     'Citadel Miniature', 'Battletome', 'winged-hammer']):
            continue

        line_upper = line.upper().strip()

        # Section transitions (only when past the contents pages)
        if current_page >= 3:
            if 'UNIVERSAL MANIFESTATION LORES' in line_upper:
                current_section = 'manifestation'
                current_faction = 'universal'
                continue
            # REGIMENTS OF RENOWN section (multiple sub-pages)
            if line_upper == 'REGIMENTS OF RENOWN':
                current_section = 'ror'
                current_faction = None
                continue
            # WARHAMMER LEGENDS sections (various sub-titles like "WARHAMMER LEGENDS – ORDER")
            # Must be a section header — either exactly "WARHAMMER LEGENDS" or contains "–" after it.
            # Exclude inline notes like "Warhammer Legends on 1 June 2026"
            if line_upper.startswith('WARHAMMER LEGENDS') and (
                    line_upper.strip() == 'WARHAMMER LEGENDS'
                    or '–' in line or '-' in line[17:]):
                current_section = 'legends'
                current_faction = None
                continue

        # In preamble/ror sections, skip everything for unit extraction
        if current_section in ('preamble', 'ror'):
            continue

        # Detect faction header: exact match to known faction names
        if line_upper in FACTION_SLUG:
            current_faction = FACTION_SLUG[line_upper]
            continue

        # Skip table headers
        if line_upper in SKIP_LINES_UPPER:
            continue

        # Skip non-unit rows by prefix
        line_lower = line.lower()
        skip = False
        for pfx in NON_UNIT_PREFIXES_LOWER:
            if line_lower.startswith(pfx):
                skip = True
                break
        if skip:
            continue

        # Skip continuation text lines
        if line.startswith('This Hero can') or line.startswith('This unit '):
            continue
        if line.startswith('You can include') or line.startswith('You cannot include'):
            continue
        if line.startswith('The following units'):
            continue
        if '→' in line and re.search(r'[A-Z].+→', line):
            continue  # replacement model lines

        if current_section not in ('main', 'manifestation', 'legends'):
            continue

        if current_faction is None:
            continue

        # ---- Extract unit name from the line ----
        # Unit table lines: UNIT NAME [spaces] [number] [more content]
        # Name can contain letters, spaces, hyphens, apostrophes, commas, parens, Æ
        # Stop at first standalone integer (unit size or points)
        # Also handle OCR artefacts like leading "✹ " or "✹ F " (OCR split)

        # Remove leading star/check marks and normalize OCR
        clean = re.sub(r'^[✹✹\*\s]+', '', line)
        # Fix OCR split like "F reeguild" → "Freeguild", "A ether" → "Aether"
        clean = re.sub(r'^([A-Z])\s+(?=[a-z])', r'\1', clean)
        clean = clean.strip()

        # Extract name: everything before the first number that appears
        # after at least 3 characters of name text
        # Allow curly apostrophes (‘’) and other Unicode name chars
        m = re.match(r'^([\w\s\'‘’\-\,\.ÆæÉé\(\)\/]+?)(?:\s+\d|\s*$)', clean)
        if not m:
            continue

        raw_name = m.group(1).strip()
        # Clean trailing punctuation
        raw_name = raw_name.rstrip('.,;:').strip()

        # Minimum validity checks
        if len(raw_name) < 3:
            continue
        if not re.search(r'[a-zA-Z]', raw_name):
            continue

        # Skip if name is a known non-unit keyword
        if raw_name.upper().strip() in SKIP_LINES_UPPER:
            continue

        norm = normalize(raw_name)
        if len(norm) < 3:
            continue

        # Manifestation section: only accept known manifestation names
        if current_section == 'manifestation':
            if norm in MANIFESTATION_NAMES:
                if norm not in pdf_units:
                    pdf_units[norm] = {
                        'raw_name': raw_name,
                        'section': 'manifestation',
                        'faction_slug': 'universal',
                    }
            continue

        # Deduplication: 'main' takes priority over 'legends'
        if norm in pdf_units:
            existing = pdf_units[norm]
            if existing['section'] == 'main' and current_section == 'legends':
                continue
            # If already legends and now main → upgrade
            if existing['section'] == 'legends' and current_section == 'main':
                pass  # fall through to update

        pdf_units[norm] = {
            'raw_name': raw_name,
            'section': current_section,
            'faction_slug': current_faction,
        }

    return pdf_units


# ---------------------------------------------------------------------------
# STEP 2 – Run the reconciliation against the DB
# ---------------------------------------------------------------------------

def run_reconciliation(dry_run=False):
    print("=" * 70)
    print("AoS4 PDF Reconciliation – April 2026 Battle Profiles")
    print("=" * 70)

    pdf_units = parse_pdf(PDF_PATH)
    print(f"\nPDF parsed: {len(pdf_units)} unique unit names found")
    # Show section breakdown
    from collections import Counter
    sections = Counter(v['section'] for v in pdf_units.values())
    print(f"  main={sections['main']}, manifestation={sections['manifestation']}, legends={sections['legends']}")

    # ---------------------------------------------------------------------------
    # Connect to DB
    # ---------------------------------------------------------------------------
    sys.path.insert(0, '/app')
    from app import create_app
    from app.models.game import Unit, Faction, GameSystem
    import sqlalchemy as sa

    app = create_app()

    with app.app_context():
        db = app.extensions['sqlalchemy']

        # Backup
        backup_path = '/app/instance/waaahgame.db.bak-pdf-reconcile'
        if not os.path.exists(backup_path):
            import shutil
            shutil.copy('/app/instance/waaahgame.db', backup_path)
            print(f"\nDB backed up to: {backup_path}")
        else:
            print(f"\nBackup already exists: {backup_path}")

        # Get FK-referenced unit IDs
        with db.engine.connect() as conn:
            r = conn.execute(sa.text('SELECT DISTINCT unit_id FROM army_units WHERE unit_id IS NOT NULL'))
            fk_unit_ids = set(row[0] for row in r.fetchall())
        print(f"\nFK-protected unit IDs (referenced in army_units): {fk_unit_ids}")

        # Snapshot DB
        s = GameSystem.query.filter_by(code='aos4').first()
        factions = {f.code: f for f in Faction.query.filter_by(game_system_id=s.id).all()}

        print(f"\nDB factions: {list(factions.keys())}")

        stats = {
            'promoted_regular': [],      # legends → regular
            'demoted_legends': [],        # regular → legends
            'set_manifestation': [],      # * → manifestation
            'deleted': [],               # removed from DB
            'fk_preserved': [],          # would delete but FK-blocked
            'not_in_pdf': [],            # in DB but no PDF match
            'not_in_db': [],             # in PDF but not in DB
            'ambiguous': [],             # OCR ambiguity - conservative skip
        }

        # Build DB unit map: normalized_name -> list of Unit objects
        db_unit_map = {}  # normalized_name -> [Unit, ...]
        for fc in factions.values():
            for u in fc.units:
                n = normalize(u.name)
                db_unit_map.setdefault(n, []).append(u)

        # ---------------------------------------------------------------------------
        # Conservative safelist: unit IDs confirmed to be in the PDF but whose
        # names don't match due to OCR multi-line splits, comma differences, or
        # name format mismatches. These are NEVER deleted even if pdf_lookup fails.
        # ---------------------------------------------------------------------------
        OCR_SAFELIST_IDS = {
            # Multi-line OCR splits – names ARE in PDF but split across lines
            1118,   # Saurus Scar-Veteran on Aggradon
            1724,   # Saurus Scar-Veteran on Carnosaur
            990,    # Lotann, Warden of the Soul Ledgers
            1736,   # Brokk Grungsson, Lord-Magnate of Barak-Nar
            157,    # Endrinmaster with Dirigible Suit
            1124,   # Vizzik Skour, Prophet of the Horned Rat
            1121,   # Plague Priest on Plague Furnace
            1729,   # Tahlia Vedra, Lioness of the Parch
            822,    # Pontifex Zenestra, Matriarch of the Great Wheel
            836,    # Battlemage on Celestial Hurricanum
            1673,   # Vanari Lord Regent on Lightcourser
            1719,   # Sloppity Bilepiper Herald of Nurgle
            1720,   # Spoilpox Scrivener Herald of Nurgle
            1713,   # Changecaster Herald of Tzeentch
            863,    # Fateskimmer, Herald of Tzeentch on Burning Chariot
            1743,   # Mannfred von Carstein, Mortarch of Night
            1174,   # Lady Annika, the Thirsting Blade
            1051,   # Kurdoss Valentian, the Craven King
            1064,   # Knight of Shrouds on Ethereal Steed
            1010,   # Killaboss on Corpse-rippa Vulcha
            1015,   # Breaka-boss on Mirebrute Troggoth
            991,    # Maw-grunta with Hakkin' Krew
            921,    # Frazzlegit Shaman on War-Wheela
            924,    # Webspinner Shaman on Arachnarok Spider
            926,    # Arachnarok Spider with Spiderfang Warparty
            # Name format differences (DB name vs PDF name differ slightly)
            1730,   # Freeguild Marshal (PDF: present as separate entry)
            1731,   # Freeguild Crossbowmen
            1738,   # Archaon the Everchosen (PDF: Archaon, the Everchosen – comma diff)
            1737,   # Thunderers (PDF: Grundstok Thunderers – name prefix diff)
            1758,   # Troggboss (PDF: Dankhold Troggboss – name differs)
            1744,   # Skeleton Warriors (PDF: Deathrattle Skeletons – name renamed)
            1722,   # Belladamma Volga First of the Vyrkos (DB missing comma)
            # Tzeentch Horror name variants – DB has "of Tzeentch" suffix PDF omits
            1741,   # Pink Horrors of Tzeentch
            1742,   # Blue Horrors of Tzeentch
            868,    # Blue Horrors and Brimstone Horrors (compound name)
            873,    # Fluxmaster, Herald of Tzeentch on Disc
            # Nagash appears in multiple factions
            1676,   # Nagash, Supreme Lord of the Undead (whichever instance)
            1747,   # Nagash duplicate/variant
            # Helsmiths weapon-specialist variants (split names in PDF)
            1628, 1629, 1630, 1631, 1632, 1633, 1634, 1635, 1636, 1637, 1638,
            # Gaunt Summoner on Disc of Tzeentch (in RoR/Legends section)
            1705,
            # Stormcast Eternals weapon variants – PDF has split entries
            65,     # Vanguard-Raptors with Longstrike Crossbows
            1195,   # Vanguard-Palladors with Starstrike Javelins
            1211,   # Vanguard-Palladors with Shock Handaxes
            1216,   # Vanguard-Raptors with Hurricane Crossbows
            1245,   # Annihilators with Meteoric Grandhammers
            1725,   # Knight-Vexillor with Banner of Apotheosis
            1200,   # Judicators with Boltstorm Crossbows (legends, split in PDF)
            1234,   # Lord-Arcanum on Celestial Dracoline (legends, split in PDF)
            # Daughters of Khaine weapon variants – PDF has split entries
            1655,   # Sisters of Slaughter with Bladed Bucklers
            1656,   # Sisters of Slaughter with Sacrificial Knives
            1723,   # Witch Aelves with Paired Sciansá
            1734,   # Witch Aelves (base unit without weapon suffix)
            1735,   # Sisters of Slaughter (base unit without weapon suffix)
            # Fyreslayers weapon variants – PDF has split entries
            911,    # Hearthguard Berzerkers with Flamestrike Poleaxes
            912,    # Vulkite Berzerkers with Fyresteel Weapons
            914,    # Vulkite Berzerkers with Bladed Slingshields
            1659,   # Hearthguard Berzerkers with Berzerker Broadaxes
            # Sylvaneth Kurnoth Hunters variants – PDF has split entries
            1683,   # Kurnoth Hunters with Kurnoth Greatbows
            1684,   # Kurnoth Hunters with Kurnoth Greatswords
            1685,   # Kurnoth Hunters with Kurnoth Scythes
            1726,   # Kurnoth Hunters with Greatswords (alt name variant)
            1727,   # Kurnoth Hunters with Greatbows (alt name variant)
            # Other units with PDF name splits or format differences
            1718,   # Infernal Enrapturess Herald of Slaanesh (split in PDF)
            1728,   # Mourngul (may be in Nighthaunt legends section with split)
            1733,   # Steam Tank with Commander (PDF: Steam Tank Commander – name diff)
        }

        def pdf_lookup(db_norm):
            """Look up a DB-normalized name in pdf_units, trying plural variants.
            Returns the pdf_rec dict or None.
            PDF typically uses plural nouns; DB typically uses singular."""
            rec = pdf_units.get(db_norm)
            if rec: return rec
            # Try plural: add 's'
            rec = pdf_units.get(db_norm + 's')
            if rec: return rec
            # Try plural: add 'es' (e.g. 'witch aelves' → already plural in PDF)
            # Reverse: strip trailing 's' from db_norm for PDF lookup
            if db_norm.endswith('s'):
                rec = pdf_units.get(db_norm[:-1])
                if rec: return rec
            return None

        # For each PDF unit, check DB
        for norm, pdf_rec in pdf_units.items():
            # Try exact match, singular match (strip s), or plural match
            found = (norm in db_unit_map
                     or (norm + 's') in db_unit_map
                     or (norm.endswith('s') and norm[:-1] in db_unit_map))
            if not found:
                stats['not_in_db'].append((pdf_rec['raw_name'], pdf_rec['faction_slug'], pdf_rec['section']))

        # For each DB unit, check PDF
        all_db_units = []
        for fc in factions.values():
            for u in fc.units:
                all_db_units.append((fc, u))

        for fc, unit in all_db_units:
            norm = normalize(unit.name)
            pdf_rec = pdf_lookup(norm)

            if pdf_rec is None:
                # Not in PDF at all → removal candidate (unless OCR safelist)
                if unit.id in OCR_SAFELIST_IDS:
                    stats['ambiguous'].append((fc.code, unit.id, unit.name, unit.unit_category))
                else:
                    stats['not_in_pdf'].append((fc.code, unit.id, unit.name, unit.unit_category))
            else:
                # In PDF – check category alignment
                target_section = pdf_rec['section']
                current_cat = unit.unit_category or 'regular'

                if target_section == 'manifestation':
                    if current_cat != 'manifestation':
                        stats['set_manifestation'].append((unit, current_cat, 'manifestation'))
                elif target_section == 'main':
                    if current_cat == 'legends':
                        stats['promoted_regular'].append((unit, 'legends', 'regular'))
                elif target_section == 'legends':
                    if current_cat != 'legends':
                        stats['demoted_legends'].append((unit, current_cat, 'legends'))

        print(f"\n{'='*70}")
        print("DIFF RESULTS (before applying changes)")
        print(f"{'='*70}")
        print(f"Units in PDF but missing from DB: {len(stats['not_in_db'])}")
        for raw, fslug, sec in stats['not_in_db']:
            print(f"  [MISSING-IN-DB] {raw} ({fslug}) [{sec}]")

        print(f"\nUnits in DB but not in PDF (removal candidates): {len(stats['not_in_pdf'])}")
        for fc_code, uid, uname, ucat in stats['not_in_pdf']:
            fk = '**FK-LOCKED**' if uid in fk_unit_ids else ''
            print(f"  [NOT-IN-PDF] faction={fc_code} id={uid} name={uname!r} cat={ucat} {fk}")

        print(f"\nUnits OCR-safelisted (in PDF but parser missed - conservatively kept): {len(stats['ambiguous'])}")
        for fc_code, uid, uname, ucat in stats['ambiguous']:
            print(f"  [OCR-SAFE] faction={fc_code} id={uid} name={uname!r} cat={ucat}")

        print(f"\nUnits to promote regular (currently legends, in PDF main): {len(stats['promoted_regular'])}")
        for u, old_cat, new_cat in stats['promoted_regular']:
            print(f"  [PROMOTE] id={u.id} {u.name!r}: {old_cat} → {new_cat}")

        print(f"\nUnits to demote to legends (in PDF legends section): {len(stats['demoted_legends'])}")
        for u, old_cat, new_cat in stats['demoted_legends']:
            print(f"  [DEMOTE] id={u.id} {u.name!r}: {old_cat} → {new_cat}")

        print(f"\nUnits to set manifestation: {len(stats['set_manifestation'])}")
        for u, old_cat, new_cat in stats['set_manifestation']:
            print(f"  [MANIFESTATION] id={u.id} {u.name!r}: {old_cat} → {new_cat}")

        if dry_run:
            print("\n[DRY RUN] No changes made.")
            return stats

        # ---------------------------------------------------------------------------
        # APPLY CHANGES
        # ---------------------------------------------------------------------------
        from app.models.game import db as sqldb
        print(f"\n{'='*70}")
        print("APPLYING CHANGES")
        print(f"{'='*70}")

        # 1. Recategorize: legends → regular (promoted)
        for u, old_cat, new_cat in stats['promoted_regular']:
            print(f"  PROMOTE id={u.id} {u.name!r}: {old_cat} → {new_cat}")
            u.unit_category = new_cat
            sqldb.session.add(u)

        # 2. Recategorize: regular → legends (demoted)
        for u, old_cat, new_cat in stats['demoted_legends']:
            print(f"  DEMOTE id={u.id} {u.name!r}: {old_cat} → {new_cat}")
            u.unit_category = new_cat
            sqldb.session.add(u)

        # 3. Set manifestation
        for u, old_cat, new_cat in stats['set_manifestation']:
            print(f"  MANIFESTATION id={u.id} {u.name!r}: {old_cat} → {new_cat}")
            u.unit_category = new_cat
            sqldb.session.add(u)

        # 4. Delete units not in PDF
        deleted_count = 0
        fk_preserved_count = 0
        deleted_by_faction = {}
        for fc_code, uid, uname, ucat in stats['not_in_pdf']:
            if uid in fk_unit_ids:
                print(f"  FK-PRESERVED id={uid} {uname!r} (referenced in army_units)")
                stats['fk_preserved'].append((fc_code, uid, uname, ucat))
                fk_preserved_count += 1
            else:
                u = Unit.query.get(uid)
                if u:
                    print(f"  DELETE id={uid} faction={fc_code} {uname!r} [{ucat}]")
                    sqldb.session.delete(u)
                    deleted_count += 1
                    deleted_by_faction.setdefault(fc_code, []).append(uname)

        sqldb.session.commit()
        print(f"\nCommit done.")

        # 5. Check empty factions
        print(f"\n{'='*70}")
        print("CHECKING EMPTY FACTIONS")
        print(f"{'='*70}")
        for fc_code, fc in list(factions.items()):
            remaining_units = Unit.query.filter_by(faction_id=fc.id).count()
            if remaining_units == 0:
                # Check if faction referenced in regiments_of_renown
                # RoR uses eligible_factions_json (JSON array of faction codes)
                with db.engine.connect() as conn:
                    r = conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM regiments_of_renown "
                            "WHERE eligible_factions_json LIKE :pat"
                        ),
                        {'pat': '%' + fc_code + '%'}
                    )
                    ror_count = r.fetchone()[0]
                if ror_count > 0:
                    print(f"  FACTION {fc_code} is empty but has {ror_count} RoR refs – preserved")
                else:
                    print(f"  FACTION {fc_code} is empty and has no RoR refs – DELETING")
                    sqldb.session.delete(fc)
                    sqldb.session.commit()

        sqldb.session.commit()

        # ---------------------------------------------------------------------------
        # FINAL REPORT
        # ---------------------------------------------------------------------------
        print(f"\n{'='*70}")
        print("FINAL REPORT")
        print(f"{'='*70}")
        print(f"Units promoted (legends → regular): {len(stats['promoted_regular'])}")
        print(f"Units demoted (regular → legends): {len(stats['demoted_legends'])}")
        print(f"Units set to manifestation: {len(stats['set_manifestation'])}")
        print(f"Units deleted: {deleted_count}")
        print(f"Units FK-preserved despite absent from PDF: {fk_preserved_count}")
        print(f"Units in PDF but missing from DB: {len(stats['not_in_db'])}")

        if deleted_by_faction:
            print(f"\nTop deletions by faction:")
            for fc_code, names in sorted(deleted_by_faction.items(), key=lambda x: -len(x[1])):
                print(f"  {fc_code}: {len(names)} units")
                for n in names[:5]:
                    print(f"    - {n}")

        if stats['fk_preserved']:
            print(f"\nFK-preserved units (kept despite absent from PDF):")
            for fc_code, uid, uname, ucat in stats['fk_preserved']:
                print(f"  id={uid} faction={fc_code} {uname!r} [{ucat}]")

        # Final per-faction count
        print(f"\nFinal per-faction unit counts:")
        for fc_code in sorted(factions.keys()):
            fc = Faction.query.filter_by(code=fc_code).first()
            if fc is None:
                print(f"  {fc_code}: DELETED")
                continue
            cnt_regular = Unit.query.filter_by(faction_id=fc.id, unit_category='regular').count()
            cnt_legends = Unit.query.filter_by(faction_id=fc.id, unit_category='legends').count()
            cnt_manifes = Unit.query.filter_by(faction_id=fc.id, unit_category='manifestation').count()
            cnt_other = Unit.query.filter_by(faction_id=fc.id).count() - cnt_regular - cnt_legends - cnt_manifes
            total = cnt_regular + cnt_legends + cnt_manifes + cnt_other
            print(f"  {fc_code}: total={total} regular={cnt_regular} legends={cnt_legends} manifestation={cnt_manifes} other={cnt_other}")

        return stats


if __name__ == '__main__':
    dry = '--dry-run' in sys.argv or '-n' in sys.argv
    run_reconciliation(dry_run=dry)
