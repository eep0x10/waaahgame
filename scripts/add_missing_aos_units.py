"""
Add 68 missing AoS units (April 2026 Battle Profiles) to the DB.

Source: scripts/cache/aos_units_audit.md (generated 2026-05-22)
PDF:    scripts/cache/aos_rules_extract/battle_profiles.clean.md

Idempotent: SELECT-before-INSERT, safe to re-run.
"""

import re
import sys
import os

# Allow running from project root inside Docker: /app
sys.path.insert(0, '/app')

from app import create_app
from app.extensions import db
from app.models.game import Faction, Unit

app = create_app()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def slugify(name: str) -> str:
    """Convert unit name to URL-safe slug (mirrors seed script convention)."""
    s = name.lower()
    s = re.sub(r"['’]", '', s)   # drop apostrophes
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def faction_id(code: str, faction_map: dict) -> int:
    fid = faction_map.get(code)
    if fid is None:
        raise ValueError(f"Faction code not found: {code}")
    return fid


# ---------------------------------------------------------------------------
# Unit data  (faction_code, name, points_cost, model_count, keywords, unit_role, can_be_general)
# Fields not listed default to: base_size_mm=None, can_be_reinforced=False,
#   stats_json={}, weapons_json=[], abilities_json=[], companions_json=[],
#   unit_category='regular'
# ---------------------------------------------------------------------------
# Legend for keywords (mirroring sibling-unit keyword style in each faction):
#   HERO units get: ['HERO', grand_alliance, FACTION_NAME, ...type]
#   Infantry units: ['INFANTRY', 'CHAMPION', grand_alliance, FACTION_NAME, ...]
#   Cavalry units:  ['CAVALRY', 'CHAMPION', grand_alliance, FACTION_NAME, ...]
#   Monster units:  ['MONSTER', grand_alliance, FACTION_NAME, ...]
# ---------------------------------------------------------------------------

MISSING_UNITS = [

    # ---- Daughters of Khaine (fid=12, ORDER) ----
    # Audit note: existing DB has 'Sisters of Slaughter' (110pts) and 'Witch Aelves' (110pts)
    # as generic; the PDF has 4 weapon-variant entries as distinct warscrolls.
    {
        'faction': 'daughters-of-khaine',
        'name': 'Sisters of Slaughter with Bladed Bucklers',
        'points_cost': 120,
        'model_count': 10,
        'keywords': ['ORDER', 'DAUGHTERS OF KHAINE', 'AELF', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': None,
    },
    {
        'faction': 'daughters-of-khaine',
        'name': 'Sisters of Slaughter with Sacrificial Knives',
        'points_cost': 110,
        'model_count': 10,
        'keywords': ['ORDER', 'DAUGHTERS OF KHAINE', 'AELF', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': None,
    },
    {
        'faction': 'daughters-of-khaine',
        'name': 'Witch Aelves with Bladed Bucklers',
        'points_cost': 120,
        'model_count': 10,
        'keywords': ['ORDER', 'DAUGHTERS OF KHAINE', 'AELF', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': None,
    },
    {
        'faction': 'daughters-of-khaine',
        'name': 'Witch Aelves with Paired Sciansa',  # FLAG: PDF uses "Sciansá" — ASCII-safe version
        'points_cost': 120,
        'model_count': 10,
        'keywords': ['ORDER', 'DAUGHTERS OF KHAINE', 'AELF', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF name has accent: "Witch Aelves with Paired Sciansá" — inserted without accent for slug safety; user should verify display name.',
    },

    # ---- Disciples of Tzeentch (fid=17, CHAOS) ----
    # Note: DB has 'Changecaster, Herald of Tzeentch' (with comma) as orphan; PDF has
    # 'Changecaster Herald of Tzeentch' (no comma). Adding the PDF version as a new entry.
    {
        'faction': 'disciples-of-tzeentch',
        'name': 'Changecaster Herald of Tzeentch',
        'points_cost': 130,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'DAEMON', 'INFANTRY', 'WARD (6+)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'DB orphan "Changecaster, Herald of Tzeentch" uses old naming; this is the PDF-canonical name.',
    },
    {
        'faction': 'disciples-of-tzeentch',
        'name': 'Fatemaster',
        'points_cost': 150,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'MORTAL', 'INFANTRY', 'ARCANITE'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'disciples-of-tzeentch',
        'name': 'Jade Obelisk',
        'points_cost': 100,
        'model_count': 5,
        'keywords': ['CHAOS', 'DISCIPLES OF TZEENTCH', 'MORTAL', 'INFANTRY', 'ARCANITE'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF keywords: Arcanite, Infantry. Model count 5 per warscroll baseline.',
    },
    {
        'faction': 'disciples-of-tzeentch',
        'name': 'Magister',
        'points_cost': 140,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'MORTAL', 'INFANTRY', 'ARCANITE', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'disciples-of-tzeentch',
        'name': 'Ogroid Thaumaturge',
        'points_cost': 130,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'MORTAL', 'INFANTRY', 'ARCANITE', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'disciples-of-tzeentch',
        'name': 'Tzaangor Enlightened',
        'points_cost': 200,
        'model_count': 3,
        'keywords': ['CHAOS', 'DISCIPLES OF TZEENTCH', 'MORTAL', 'INFANTRY', 'ARCANITE'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Arcanite keyword; 3-model warscroll baseline.',
    },
    {
        'faction': 'disciples-of-tzeentch',
        'name': 'Tzaangor Shaman',
        'points_cost': 130,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'MORTAL', 'INFANTRY', 'ARCANITE', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },

    # ---- Flesh-eater Courts (fid=48, DEATH) ----
    # PDF: "Crypt Flayers (2 models)" and "Crypt Horrors (2 models)" — these are the 2-model
    # min-size warscrolls; DB already has 'Crypt Flayer' mc=1 (orphan) and 'Crypt Horror' mc=1 (orphan).
    {
        'faction': 'flesh-eater-courts',
        'name': 'Crypt Flayers',
        'points_cost': 90,
        'model_count': 2,
        'keywords': ['DEATH', 'FLESH-EATER COURTS', 'WARD (6+)', 'INFANTRY', 'CHAMPION', 'FLY'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: 2-model warscroll baseline (Knights, Infantry). Separate from orphaned mc=1 entry.',
    },
    {
        'faction': 'flesh-eater-courts',
        'name': 'Crypt Horrors',
        'points_cost': 100,
        'model_count': 2,
        'keywords': ['DEATH', 'FLESH-EATER COURTS', 'WARD (6+)', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: 2-model warscroll baseline (Knights, Infantry). Separate from orphaned mc=1 entry.',
    },

    # ---- Fyreslayers (fid=71, ORDER) ----
    {
        'faction': 'fyreslayers',
        'name': 'Hearthguard Berzerkers with Berzerker Broadaxes',
        'points_cost': 110,
        'model_count': 5,
        'keywords': ['ORDER', 'FYRESLAYERS', 'DUARDIN', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': None,
    },

    # ---- Gloomspite Gitz (fid=21, DESTRUCTION) ----
    # Kragnos is shared across multiple factions; slug must be unique per faction.
    {
        'faction': 'gloomspite-gitz',
        'name': 'Kragnos, the End of Empires',
        'points_cost': 580,
        'model_count': 1,
        'keywords': ['DESTRUCTION', 'GLOOMSPITE GITZ', 'HERO', 'MONSTER', 'UNIQUE', 'WARMASTER'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'Shared cross-faction HERO; slug will be faction-prefixed to avoid collision.',
        'slug_override': 'gloomspite-gitz-kragnos-the-end-of-empires',
    },

    # ---- Hedonites of Slaanesh (fid=32, CHAOS) ----
    # DB orphan 'Infernal Enrapturess, Herald of Slaanesh' (with comma) exists;
    # PDF canonical: 'Infernal Enrapturess Herald of Slaanesh' (no comma).
    {
        'faction': 'hedonites-of-slaanesh',
        'name': 'Infernal Enrapturess Herald of Slaanesh',
        'points_cost': 90,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'HEDONITES OF SLAANESH', 'DAEMON', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'DB orphan uses old comma-name; this is PDF-canonical.',
    },
    {
        'faction': 'hedonites-of-slaanesh',
        'name': 'Lord of Hubris',
        'points_cost': 100,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'HEDONITES OF SLAANESH', 'MORTAL', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'hedonites-of-slaanesh',
        'name': 'Lord of Pain',
        'points_cost': 110,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'HEDONITES OF SLAANESH', 'MORTAL', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'hedonites-of-slaanesh',
        'name': 'Shardspeaker of Slaanesh',
        'points_cost': 120,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'HEDONITES OF SLAANESH', 'MORTAL', 'INFANTRY', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },

    # ---- Ironjawz (fid=75, DESTRUCTION) ----
    {
        'faction': 'ironjawz',
        'name': 'Ardboy Big Boss',
        'points_cost': 100,
        'model_count': 1,
        'keywords': ['HERO', 'DESTRUCTION', 'IRONJAWZ', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'ironjawz',
        'name': 'Gordrakk, the Fist of Gork',
        'points_cost': 340,
        'model_count': 1,
        'keywords': ['HERO', 'MONSTER', 'UNIQUE', 'WARMASTER', 'DESTRUCTION', 'IRONJAWZ', 'MAW-KRUSHA'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'ironjawz',
        'name': 'Kragnos, the End of Empires',
        'points_cost': 580,
        'model_count': 1,
        'keywords': ['DESTRUCTION', 'IRONJAWZ', 'HERO', 'MONSTER', 'UNIQUE', 'WARMASTER'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'Shared cross-faction HERO; slug prefixed.',
        'slug_override': 'ironjawz-kragnos-the-end-of-empires',
    },
    {
        'faction': 'ironjawz',
        'name': 'Maw-grunta with Hakkin Krew',  # PDF: "Maw-grunta with Hakkin' Krew"
        'points_cost': 240,
        'model_count': 1,
        'keywords': ['MONSTER', 'DESTRUCTION', 'IRONJAWZ', 'MAW-GRUNTA'],
        'unit_role': None,
        'can_be_general': False,
        # DB already has "Maw-grunta with Hakkin' Krew" as orphan regular (HTML entity name).
        # PDF canonical version uses apostrophe. The orphan has the same name but the audit
        # flags it as a naming mismatch. Inserting clean version.
        'note': "PDF name: \"Maw-grunta with Hakkin' Krew\" — apostrophe stripped in slug. DB already has HTML-entity orphan; this is the clean canonical entry.",
        'slug_override': 'ironjawz-maw-grunta-with-hakkin-krew',
    },
    {
        'faction': 'ironjawz',
        'name': 'Megaboss',
        'points_cost': 140,
        'model_count': 1,
        'keywords': ['HERO', 'DESTRUCTION', 'IRONJAWZ', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'ironjawz',
        'name': 'Megaboss on Maw-krusha',
        'points_cost': 330,
        'model_count': 1,
        'keywords': ['HERO', 'MONSTER', 'DESTRUCTION', 'IRONJAWZ', 'MAW-KRUSHA'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'ironjawz',
        'name': 'Warchanter',
        'points_cost': 110,
        'model_count': 1,
        'keywords': ['HERO', 'DESTRUCTION', 'IRONJAWZ', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'ironjawz',
        'name': 'Weirdnob Shaman',
        'points_cost': 110,
        'model_count': 1,
        'keywords': ['HERO', 'DESTRUCTION', 'IRONJAWZ', 'INFANTRY', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },

    # ---- Kruleboyz (fid=76, DESTRUCTION) ----
    {
        'faction': 'kruleboyz',
        'name': 'Kragnos, the End of Empires',
        'points_cost': 580,
        'model_count': 1,
        'keywords': ['DESTRUCTION', 'KRULEBOYZ', 'HERO', 'MONSTER', 'UNIQUE', 'WARMASTER'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'Shared cross-faction HERO; slug prefixed.',
        'slug_override': 'kruleboyz-kragnos-the-end-of-empires',
    },
    {
        'faction': 'kruleboyz',
        'name': 'Kruleboyz Monsta-killaz',
        'points_cost': 120,
        'model_count': 5,
        'keywords': ['INFANTRY', 'CHAMPION', 'DESTRUCTION', 'KRULEBOYZ'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF keywords: Infantry. 5-model baseline.',
    },
    {
        'faction': 'kruleboyz',
        'name': 'Swampcalla Shaman with Pot-grot',
        'points_cost': 120,
        'model_count': 1,
        'keywords': ['HERO', 'DESTRUCTION', 'KRULEBOYZ', 'INFANTRY', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },

    # ---- Lumineth Realm-lords (fid=14, ORDER) ----
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Avalenor, the Stoneheart King',
        'points_cost': 420,
        'model_count': 1,
        'keywords': ['HERO', 'MONSTER', 'UNIQUE', 'ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'ALARITH'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Hurakan Spirit of the Wind',
        'points_cost': 270,
        'model_count': 1,
        'keywords': ['MONSTER', 'ORDER', 'LUMINETH REALM-LORDS', 'HURAKAN'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Hurakan, Monster.',
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Hurakan Windmage',
        'points_cost': 140,
        'model_count': 1,
        'keywords': ['HERO', 'ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'HURAKAN', 'INFANTRY', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Scinari Calligrave',
        'points_cost': 130,
        'model_count': 1,
        'keywords': ['HERO', 'ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'SCINARI', 'INFANTRY', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Scinari Enlightener',
        'points_cost': 180,
        'model_count': 1,
        'keywords': ['HERO', 'ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'SCINARI', 'INFANTRY', 'WIZARD (1)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Scinari Loreseeker',
        'points_cost': 140,
        'model_count': 1,
        'keywords': ['HERO', 'ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'SCINARI', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Vanari Bannerblade',
        'points_cost': 140,
        'model_count': 1,
        'keywords': ['HERO', 'ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'VANARI', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Vanari Bladelords',
        'points_cost': 150,
        'model_count': 5,
        'keywords': ['ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'VANARI', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Aelf, Vanari, Infantry.',
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Vanari Lord Regent on Lightcourser',
        'points_cost': 150,
        'model_count': 1,
        'keywords': ['HERO', 'ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'VANARI', 'CAVALRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Vanari Starshard Ballista',
        'points_cost': 120,
        'model_count': 1,
        'keywords': ['ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'VANARI', 'WAR MACHINE'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Vanari, War Machine.',
    },
    {
        'faction': 'lumineth-realm-lords',
        'name': 'Ydrilan Riverblades',
        'points_cost': 140,
        'model_count': 5,
        'keywords': ['ORDER', 'LUMINETH REALM-LORDS', 'AELF', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Aelf, Infantry.',
    },

    # ---- Maggotkin of Nurgle (fid=15, CHAOS) ----
    # DB orphans 'Sloppity Bilepiper, Herald of Nurgle' and 'Spoilpox Scrivener, Herald of Nurgle' (with comma)
    # PDF canonical: no comma in name.
    {
        'faction': 'maggotkin-of-nurgle',
        'name': 'Pusgoyle Blightlords',
        'points_cost': 110,
        'model_count': 1,
        'keywords': ['CHAOS', 'MAGGOTKIN OF NURGLE', 'ROTBRINGERS', 'CAVALRY', 'FLY'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: 1-model Rotbringers warscroll (different from existing multi-model if any).',
    },
    {
        'faction': 'maggotkin-of-nurgle',
        'name': 'Sloppity Bilepiper Herald of Nurgle',
        'points_cost': 100,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'MAGGOTKIN OF NURGLE', 'DAEMON', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'PDF canonical name (no comma). DB orphan has comma variant.',
    },
    {
        'faction': 'maggotkin-of-nurgle',
        'name': 'Spoilpox Scrivener Herald of Nurgle',
        'points_cost': 80,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'MAGGOTKIN OF NURGLE', 'DAEMON', 'INFANTRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'PDF canonical name (no comma). DB orphan has comma variant.',
    },

    # ---- Nighthaunt (fid=7, DEATH) ----
    {
        'faction': 'nighthaunt',
        'name': 'Nagash, Supreme Lord of the Undead',
        'points_cost': 840,
        'model_count': 1,
        'keywords': ['DEATH', 'HERO', 'MONSTER', 'UNIQUE', 'WARMASTER', 'NIGHTHAUNT', 'WIZARD (9)', 'WARD (6+)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'DB has Nagash under Ossiarch Bonereapers (895pts, old). PDF lists 840pts under Nighthaunt too. Slug prefixed.',
        'slug_override': 'nighthaunt-nagash-supreme-lord-of-the-undead',
    },

    # ---- Ogor Mawtribes (fid=56, DESTRUCTION) ----
    {
        'faction': 'ogor-mawtribes',
        'name': 'Kragnos, the End of Empires',
        'points_cost': 580,
        'model_count': 1,
        'keywords': ['DESTRUCTION', 'OGOR MAWTRIBES', 'HERO', 'MONSTER', 'UNIQUE', 'WARMASTER'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'Shared cross-faction HERO; slug prefixed.',
        'slug_override': 'ogor-mawtribes-kragnos-the-end-of-empires',
    },

    # ---- Ossiarch Bonereapers (fid=19, DEATH) ----
    {
        'faction': 'ossiarch-bonereapers',
        'name': 'Morghast Archai',
        'points_cost': 260,
        'model_count': 2,
        'keywords': ['DEATH', 'OSSIARCH BONEREAPERS', 'MORGHAST', 'INFANTRY', 'CHAMPION', 'FLY'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Infantry. 2-model warscroll baseline.',
    },

    # ---- Seraphon (fid=2, ORDER) ----
    {
        'faction': 'seraphon',
        'name': 'Ripperdactyl Riders',
        'points_cost': 70,
        'model_count': 2,
        'keywords': ['ORDER', 'SERAPHON', 'SKINK', 'CAVALRY', 'CHAMPION', 'FLY'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: 2-model Skink Cavalry warscroll baseline.',
    },
    {
        'faction': 'seraphon',
        'name': 'Terradon Riders',
        'points_cost': 70,
        'model_count': 2,
        'keywords': ['ORDER', 'SERAPHON', 'SKINK', 'CAVALRY', 'CHAMPION', 'FLY'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: 2-model Skink Cavalry warscroll baseline.',
    },

    # ---- Skaven (fid=1, CHAOS) ----
    {
        'faction': 'skaven',
        'name': 'Ratling Guns',
        'points_cost': 170,
        'model_count': 3,
        'keywords': ['CHAOS', 'SKAVEN', 'SKAVENTIDE', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF keywords not fully listed in audit; 3-model warscroll baseline inferred from Rat Ogor pattern.',
    },

    # ---- Slaves to Darkness (fid=16, CHAOS) ----
    # Note: DB has 'Archaon the Everchosen' (no comma, 870pts) as orphan;
    # PDF has 'Archaon, the Everchosen' (comma, 810pts). Different name+pts = new entry.
    {
        'faction': 'slaves-to-darkness',
        'name': 'Archaon, the Everchosen',
        'points_cost': 810,
        'model_count': 1,
        'keywords': ['HERO', 'MONSTER', 'UNIQUE', 'WARMASTER', 'CHAOS', 'SLAVES TO DARKNESS', 'DAEMON', 'WARRIORS OF CHAOS', 'WARD (5+)', 'FLY', 'WIZARD (2)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'April 2026 PDF: 810pts. DB orphan "Archaon the Everchosen" (870pts) is old version.',
    },
    {
        'faction': 'slaves-to-darkness',
        'name': 'Chaos Lord',
        'points_cost': 100,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'SLAVES TO DARKNESS', 'MORTAL', 'INFANTRY', 'WARRIORS OF CHAOS'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'slaves-to-darkness',
        'name': 'Gaunt Summoner',
        'points_cost': 160,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'SLAVES TO DARKNESS', 'MORTAL', 'INFANTRY', 'WIZARD (2)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'PDF distinguishes foot Gaunt Summoner (160pts) from Disc version (190pts).',
    },
    {
        'faction': 'slaves-to-darkness',
        'name': 'Gaunt Summoner on Disc of Tzeentch',
        'points_cost': 190,
        'model_count': 1,
        'keywords': ['HERO', 'CHAOS', 'SLAVES TO DARKNESS', 'MORTAL', 'CAVALRY', 'FLY', 'WIZARD (2)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },
    {
        'faction': 'slaves-to-darkness',
        'name': 'Mutalith Vortex Beast',
        'points_cost': 160,
        'model_count': 1,
        'keywords': ['CHAOS', 'SLAVES TO DARKNESS', 'DAEMON', 'MONSTER'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Daemon, Monster.',
    },
    {
        'faction': 'slaves-to-darkness',
        'name': 'Slaughterbrute',
        'points_cost': 200,
        'model_count': 1,
        'keywords': ['CHAOS', 'SLAVES TO DARKNESS', 'DAEMON', 'MONSTER'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Daemon, Monster.',
    },

    # ---- Sons of Behemat (fid=77, DESTRUCTION) ----
    {
        'faction': 'sons-of-behemat',
        'name': 'Kragnos, the End of Empires',
        'points_cost': 590,
        'model_count': 1,
        # NOTE: 590pts for Sons of Behemat vs 580pts in Ironjawz/Kruleboyz/Gloomspite/Ogor —
        # the audit shows 590 for Sons of Behemat specifically (different force org slot costs)
        'keywords': ['DESTRUCTION', 'SONS OF BEHEMAT', 'HERO', 'MONSTER', 'UNIQUE', 'WARMASTER'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'Shared cross-faction HERO; 590pts (Sons of Behemat specific cost). Slug prefixed.',
        'slug_override': 'sons-of-behemat-kragnos-the-end-of-empires',
    },

    # ---- Soulblight Gravelords (fid=18, DEATH) ----
    # DB has 'Belladamma Volga, First of the Vyrkos' with comma as orphan;
    # PDF: 'Belladamma Volga First of the Vyrkos' (no comma)
    {
        'faction': 'soulblight-gravelords',
        'name': 'Belladamma Volga First of the Vyrkos',
        'points_cost': 220,
        'model_count': 1,
        'keywords': ['HERO', 'UNIQUE', 'DEATH', 'SOULBLIGHT GRAVELORDS', 'VYRKOS DYNASTY', 'INFANTRY', 'WIZARD (2)'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': 'PDF canonical name (no comma). DB orphan has comma variant.',
    },
    {
        'faction': 'soulblight-gravelords',
        'name': 'Deadwalker Zombies',
        'points_cost': 130,
        'model_count': 10,
        'keywords': ['DEATH', 'SOULBLIGHT GRAVELORDS', 'DEADWALKERS', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Deadwalkers, Infantry. DB orphan "Zombie" (130pts) is old naming.',
    },
    {
        'faction': 'soulblight-gravelords',
        'name': 'Fell Bats',
        'points_cost': 80,
        'model_count': 3,
        'keywords': ['DEATH', 'SOULBLIGHT GRAVELORDS', 'DEADWALKERS', 'BEAST', 'FLY'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Deadwalkers, Beast. DB orphan "Fell Bat" (80pts, mc=1) is old entry.',
    },
    {
        'faction': 'soulblight-gravelords',
        'name': 'Revenant Draconith',
        'points_cost': 190,
        'model_count': 1,
        'keywords': ['DEATH', 'SOULBLIGHT GRAVELORDS', 'MONSTER', 'FLY'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: Monster. New unit in April 2026 profiles.',
    },
    {
        'faction': 'soulblight-gravelords',
        'name': 'Terrorgheist',
        'points_cost': 220,
        'model_count': 1,
        'keywords': ['DEATH', 'SOULBLIGHT GRAVELORDS', 'MONSTER', 'FLY', 'WARD (6+)'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: 220pts under Soulblight. Note: FEC also has Terrorgheist (230pts) — different faction entry.',
        'slug_override': 'soulblight-gravelords-terrorgheist',
    },
    {
        'faction': 'soulblight-gravelords',
        'name': 'Wight King on Skeletal Steed',
        'points_cost': 180,
        'model_count': 1,
        'keywords': ['HERO', 'DEATH', 'SOULBLIGHT GRAVELORDS', 'DEATHRATTLE', 'CAVALRY'],
        'unit_role': 'Hero',
        'can_be_general': True,
        'note': None,
    },

    # ---- Stormcast Eternals (fid=5, ORDER) ----
    # DB has 'Stormdrake Guard' (mc=1, 310pts orphan? audit says pts drift 310->340);
    # PDF has 'Stormdrake Guard (1 model)' meaning the 1-model warscroll costs 160pts.
    {
        'faction': 'stormcast-eternals',
        'name': 'Stormdrake Guard (1 model)',
        'points_cost': 160,
        'model_count': 1,
        'keywords': ['ORDER', 'STORMCAST ETERNALS', 'FLY', 'MONSTER', 'EXTREMIS CHAMBER'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'PDF: 160pts for 1-model warscroll. Existing DB entry "Stormdrake Guard" (310pts) is the 2-model version.',
    },

    # ---- Sylvaneth (fid=6, ORDER) ----
    # DB has old naming 'Kurnoth Hunters with Greatbows' / 'Kurnoth Hunters with Greatswords' (240pts orphans)
    # PDF has updated 2026 names and pts: Greatbows 200pts, Greatswords 200pts, Scythes 190pts
    {
        'faction': 'sylvaneth',
        'name': 'Kurnoth Hunters with Kurnoth Greatbows',
        'points_cost': 200,
        'model_count': 3,
        'keywords': ['ORDER', 'SYLVANETH', 'KURNOTHI', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'April 2026 name (Kurnoth prefix). DB orphan "Kurnoth Hunters with Greatbows" (240pts) is old version.',
    },
    {
        'faction': 'sylvaneth',
        'name': 'Kurnoth Hunters with Kurnoth Greatswords',
        'points_cost': 200,
        'model_count': 3,
        'keywords': ['ORDER', 'SYLVANETH', 'KURNOTHI', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'April 2026 name (Kurnoth prefix). DB orphan "Kurnoth Hunters with Greatswords" (240pts) is old version.',
    },
    {
        'faction': 'sylvaneth',
        'name': 'Kurnoth Hunters with Kurnoth Scythes',
        'points_cost': 190,
        'model_count': 3,
        'keywords': ['ORDER', 'SYLVANETH', 'KURNOTHI', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        'note': 'New April 2026 weapon variant. No prior DB entry.',
    },
    {
        'faction': 'sylvaneth',
        'name': 'The Twistweald',
        'points_cost': 100,
        'model_count': 5,
        'keywords': ['ORDER', 'SYLVANETH', 'INFANTRY', 'CHAMPION'],
        'unit_role': None,
        'can_be_general': False,
        # DB has orphan 'Twistweald' (120pts regular) — different pts, possibly old version.
        'note': 'April 2026: 100pts. DB orphan "Twistweald" (120pts) is old entry.',
        'slug_override': 'sylvaneth-the-twistweald',
    },
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    with app.app_context():
        # Build faction_map: code -> id
        factions = Faction.query.all()
        faction_map = {f.code: f.id for f in factions}

        inserted = 0
        skipped = 0
        errors = 0
        error_details = []
        faction_insert_count = {}

        for u_data in MISSING_UNITS:
            faction_code = u_data['faction']
            name = u_data['name']
            try:
                fid = faction_id(faction_code, faction_map)
            except ValueError as e:
                errors += 1
                error_details.append(str(e))
                continue

            # Determine slug
            slug = u_data.get('slug_override') or slugify(name)

            # Idempotency check — by slug (globally unique)
            existing_by_slug = Unit.query.filter_by(slug=slug).first()
            # Also check by faction_id + name for safety
            existing_by_name = Unit.query.filter_by(faction_id=fid, name=name).first()

            if existing_by_slug or existing_by_name:
                skipped += 1
                continue

            try:
                unit = Unit(
                    faction_id=fid,
                    slug=slug,
                    name=name,
                    points_cost=u_data['points_cost'],
                    model_count=u_data.get('model_count', 1),
                    base_size_mm=u_data.get('base_size_mm', None),
                    unit_role=u_data.get('unit_role', None),
                    can_be_general=u_data.get('can_be_general', False),
                    can_be_reinforced=u_data.get('can_be_reinforced', False),
                    stats_json={},
                    weapons_json=[],
                    abilities_json=[],
                    keywords_json=u_data.get('keywords', []),
                    companions_json=[],
                    unit_category='regular',
                )
                db.session.add(unit)
                db.session.flush()  # catch constraint errors early before commit
                inserted += 1
                faction_insert_count[faction_code] = faction_insert_count.get(faction_code, 0) + 1
            except Exception as e:
                db.session.rollback()
                errors += 1
                error_details.append(f"{name}: {e}")
                # Re-open session for next unit
                db.session = db.session  # noqa

        # Commit all successful inserts in one transaction
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"COMMIT FAILED: {e}")
            return

        print("\n=== add_missing_aos_units.py ===")
        print(f"Inserted:  {inserted}")
        print(f"Skipped (already present): {skipped}")
        print(f"Errors:    {errors}")
        if error_details:
            print("Error details:")
            for d in error_details:
                print(f"  - {d}")
        print("\nInserted by faction:")
        for faction, count in sorted(faction_insert_count.items(), key=lambda x: -x[1]):
            print(f"  {faction}: {count}")

        # Post-insert total
        total_aos = Unit.query.join(Faction).filter(
            Faction.game_system_id == 1,
            Unit.unit_category == 'regular'
        ).count()
        total_all = Unit.query.join(Faction).filter(Faction.game_system_id == 1).count()
        print(f"\nPost-insert AoS regular units: {total_aos}")
        print(f"Post-insert AoS total (all categories): {total_all}")


if __name__ == '__main__':
    main()
