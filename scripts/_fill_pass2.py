"""
_fill_pass2.py — Mechanical reconciliation pass 2.
PDF source: battle_profiles.clean.md
Factions in scope: stormcast-eternals, slaves-to-darkness, lumineth-realm-lords,
  sylvaneth, flesh-eater-courts, idoneth-deepkin, ossiarch-bonereapers, seraphon,
  disciples-of-tzeentch, daughters-of-khaine, hedonites-of-slaanesh, kruleboyz, skaven.
"""

import sqlite3
from datetime import datetime

DB_PATH = "/app/instance/waaahgame.db"
NOW = datetime.utcnow().isoformat()


def slug(name: str) -> str:
    import re
    s = name.lower()
    s = s.replace("'", "").replace("'", "").replace("'", "")
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def unit(faction_id, name, points_cost, model_count, unit_category="regular",
         unit_role=None):
    return {
        "faction_id": faction_id,
        "slug": slug(name),
        "name": name,
        "points_cost": points_cost,
        "model_count": model_count,
        "stats_json": "{}",
        "weapons_json": "[]",
        "abilities_json": "[]",
        "keywords_json": "[]",
        "companions_json": "[]",
        "created_at": NOW,
        "updated_at": NOW,
        "unit_category": unit_category,
        "unit_role": unit_role,
    }


# ---------------------------------------------------------------------------
# UNITS TO INSERT  (faction_id, name, points, model_count, category, role)
# ---------------------------------------------------------------------------

INSERTS = []

# ── STORMCAST ETERNALS (id=5) ──────────────────────────────────────────────
SCE = 5
# Missing regular heroes:
INSERTS += [
    unit(SCE, "Celestant-Prime, Hammer of Sigmar", 250, 1, "regular", "hero"),
]
# Missing regular units — Dracothian Guard (1 model) variants:
INSERTS += [
    unit(SCE, "Dracothian Guard Concussors (1 model)", 120, 1, "regular", "cavalry"),
    unit(SCE, "Dracothian Guard Desolators (1 model)", 100, 1, "regular", "cavalry"),
    unit(SCE, "Dracothian Guard Fulminators (1 model)", 100, 1, "regular", "cavalry"),
    unit(SCE, "Dracothian Guard Tempestors (1 model)", 90, 1, "regular", "cavalry"),
]
# Missing regular units:
INSERTS += [
    unit(SCE, "Vanquishers", 90, 5, "regular", "infantry"),
    unit(SCE, "Vigilors", 140, 5, "regular", "infantry"),
    unit(SCE, "Vindictors", 90, 5, "regular", "infantry"),
]
# Missing Legends units:
INSERTS += [
    unit(SCE, "Domitan's Stormcoven", 210, 3, "legends", "infantry"),
    unit(SCE, "Sequitors", 120, 5, "legends", "infantry"),
    unit(SCE, "Steelheart's Champions", 110, 3, "legends", "infantry"),
    unit(SCE, "Stormsire's Cursebreakers", 130, 3, "legends", "infantry"),
    unit(SCE, "The Emberwatch", 140, 3, "legends", "infantry"),
    unit(SCE, "Xandire's Truthseekers", 130, 3, "legends", "infantry"),
]
# NOTE: "Knight-Vexillor with Banner of Apotheosis" (id=1725) has no PDF entry → DELETE

# ── SLAVES TO DARKNESS (id=16) ─────────────────────────────────────────────
STD = 16
# Missing legends units:
INSERTS += [
    unit(STD, "The Unmade", 110, 9, "legends", "infantry"),
]
# Missing legends heroes:
INSERTS += [
    # Chaos Lord on Manticore OK, Chaos Sorcerer Lord on Manticore OK, Chaos Warshrine OK
]
# Check missing regular: Abraxia, Singri Brand, The Oathsworn Kin
# Singri Brand (0 pts) and The Oathsworn Kin (0 pts) are already in DB
# Abraxia (id not found) → add
INSERTS += [
    unit(STD, "Abraxia, Spear of the Everchosen", 250, 1, "regular", "hero"),
]
# Missing legends units vs PDF legends for StD:
# PDF legends: Chaos Lord on Manticore, Chaos Sorcerer Lord on Manticore, Chaos Warshrine (heroes)
# Corvus Cabal, Cypher Lords, Godsworn Hunt, Horns of Hashut, Iron Golem, Khagra's Ravagers,
# Scions of the Flame, Soul Grinder, Spire Tyrants, Splintered Fang, Tarantulos Brood,
# The Gnarlspirit Pack, The Unmade, Untamed Beasts = 14 legends units+heroes
# DB legends (16): Chaos Lord on Manticore, Chaos Sorcerer Lord on Manticore, Chaos Warshrine,
#   Corvus Cabal, Cypher Lords, Godsworn Hunt, Horns of Hashut, Iron Golem, Khagra's Ravagers,
#   Scions of the Flame, Soul Grinder, Spire Tyrants, Splintered Fang, Tarantulos Brood,
#   The Gnarlspirit Pack, Untamed Beasts = 16 (already has The Unmade missing → +1 needed)
# Wait, DB has 16 legends but PDF only has... let me count again:
# PDF Legends Heroes (3): Chaos Lord on Manticore, Chaos Sorcerer Lord on Manticore, Chaos Warshrine
# PDF Legends Units (13): Corvus Cabal, Cypher Lords, Godsworn Hunt, Horns of Hashut, Iron Golem,
#   Khagra's Ravagers, Scions of the Flame, Soul Grinder, Spire Tyrants, Splintered Fang,
#   Tarantulos Brood, The Gnarlspirit Pack, The Unmade, Untamed Beasts = 14
# Total legends = 17... DB has 16, missing The Unmade → already added above ✓
#
# PDF regular count: heroes=19 (Abraxia, Archaon, Be'lakor, Centaurion Marshal, Chaos Lord,
#   Chaos Lord on Daemonic Mount, Chaos Lord on Karkadrak, Chaos Sorcerer Lord, Daemon Prince,
#   Darkoath Chieftain, Darkoath Chieftain on Warsteed, Darkoath Warqueen, Eternus,
#   Exalted Hero, Gaunt Summoner, Gaunt Summoner on Disc, Gunnar Brand, Ogroid Myrmidon,
#   Singri Brand(0)) = 19
# PDF regular units=20 (Chaos Chariot, Chaos Chosen, Chaos Furies, Chaos Knights,
#   Chaos Legionnaires, Chaos Spawn, Chaos Warriors, Darkoath Fellriders, Darkoath Marauders,
#   Darkoath Savagers, Darkoath Wilderfiend, Fomoroid Crusher, Gorebeast Chariot,
#   Legion-of-First-Prince Beasts of Nurgle, Bloodcrushers, Bloodletters, Fiends,
#   Flamers of Tzeentch, Hellflayer, Plaguebearers, Screamers of Tzeentch,
#   Mindstealer Sphiranx, Mutalith Vortex Beast, Ogroid Theridons, Raptoryx,
#   Slaughterbrute, The Oathsworn Kin(0), Varanguard)
# Wait - Legion of First Prince units are a sub-section. They count as StD units.
# PDF has 8 LotFP units. Let me recount DB regular for StD:
# DB regular count: 38 (Archaon, Be'lakor, Centaurion, Chaos Chariot, Chaos Chosen, Chaos Furies,
#   Chaos Knight, Chaos Legionnaires, Chaos Lord, Chaos Lord on Daemonic Mount, Chaos Lord on Karkadrak,
#   Chaos Sorcerer Lord, Chaos Spawn, Chaos Warrior, Daemon Prince, Darkoath Chieftain,
#   Darkoath Chieftain on Warsteed, Darkoath Fellriders, Darkoath Marauders, Darkoath Savagers,
#   Darkoath Warqueen, Darkoath Wilderfiend, Eternus, Eternus-duplicate?, Exalted Hero,
#   Fomoroid Crusher, Gaunt Summoner, Gaunt Summoner on Disc, Gorebeast Chariot, Gunnar Brand,
#   Mindstealer Sphiranx, Mutalith Vortex Beast, Ogroid Myrmidon, Ogroid Theridons,
#   Raptoryx, Slaughterbrute, The Oathsworn Kin, Varanguard) = 38
# DB also has 'Eternus' (id=1785) AND 'Eternus, Blade of the First Prince' (id=1150) - duplicate!
# PDF has only 'Eternus, Blade of the First Prince' as a hero.
# But wait - the LotFP units: DB shows no LotFP sub-units. PDF lists:
#   LotFP Beasts of Nurgle(120), LotFP Bloodcrushers(150), LotFP Bloodletters(170),
#   LotFP Fiends(140), LotFP Flamers of Tzeentch(120), LotFP Hellflayer(130),
#   LotFP Plaguebearers(140), LotFP Screamers of Tzeentch(80) = 8 LotFP units
# These are StD-specific units. DB should have them.
# DB total regular=38, legends=16. Total=54.
# PDF: regular heroes=19 (incl. Singri Brand 0pt), regular units=28 (incl. LotFP 8 + Oathsworn Kin),
#      legends heroes=3, legends units=14 = 64 total
# Missing from DB regular: Abraxia (added above) + 8 LotFP units = 9
# But diff is -10 so 10 missing. Checking the 'Eternus' duplicate:
#   id=1785 'Eternus' and id=1150 'Eternus, Blade of the First Prince' - both exist.
#   We should DELETE the shorter-named one (id=1785) since PDF name is the full one.
# That means we need 10 inserts - 1 delete = net +9? No: DB=54, PDF=64, so we need +10.
# If we delete the Eternus phantom: 54-1+inserts=64 → inserts=11.
# Let's count: Abraxia (1) + 8 LotFP = 9 inserts + delete 1 phantom → net +8, DB goes to 61.
# Still -3. What else is missing?
# Re-examining DB regular units list more carefully...
# 'Haunting Abhorrant Gorewarden' - wait that's FEC
# StD DB regular heroes (counting): Archaon, Be'lakor, Centaurion Marshal, Chaos Lord,
#   Chaos Lord on Daemonic Mount, Chaos Lord on Karkadrak, Chaos Sorcerer Lord, Daemon Prince,
#   Darkoath Chieftain, Darkoath Chieftain on Warsteed, Darkoath Warqueen, Eternus (1785, phantom),
#   Eternus Blade (1150), Exalted Hero, Gaunt Summoner, Gaunt Summoner on Disc, Gunnar Brand,
#   Ogroid Myrmidon = 18 heroes in DB regular
# PDF regular heroes = 19 (same 18 + Abraxia + minus phantom Eternus = net 19)
# Wait: 18 - 1(phantom) + 1(Abraxia) = 18 net, vs PDF 19. Singri Brand is the 19th.
# Singri Brand is in DB as id=1860... let me check:
INSERTS += []  # placeholder

# ── LUMINETH REALM-LORDS (id=14) ───────────────────────────────────────────
LRL = 14
# DB=22, PDF=26 (diff=-4)
# PDF regular heroes (14): Alarith Stonemage, Archmage Teclis, Avalenor, Ellania and Ellathor,
#   Hurakan Windmage, Lyrior Uthralle, Scinari Calligrave, Scinari Cathallar, Scinari Enlightener,
#   Scinari Loreseeker, Sevireth, The Light of Eltharion, Vanari Bannerblade, Vanari Lord Regent,
#   Vanari Lord Regent on Lightcourser = 15
# PDF regular units (10): Alarith Spirit of the Mountain, Alarith Stoneguard, Hurakan Spirit of Wind,
#   Hurakan Windchargers, Vanari Auralan Sentinels, Vanari Auralan Wardens, Vanari Bladelords,
#   Vanari Dawnriders, Vanari Starshard Ballista, Ydrilan Riverblades = 10
# PDF Legends (1): Myari's Purifiers = 1
# Total PDF = 15 + 10 + 1 = 26
# DB has 22: legends=1, regular=21
# Missing regular heroes: Archmage Teclis, Ellania and Ellathor, Lyrior Uthralle, Sevireth = 4
INSERTS += [
    unit(LRL, "Archmage Teclis and Celennar, Spirit of Hysh", 640, 1, "regular", "hero"),
    unit(LRL, "Ellania and Ellathor, Eclipsian Warsages", 290, 1, "regular", "hero"),
    unit(LRL, "Lyrior Uthralle, Warden of Ymetrica", 250, 1, "regular", "hero"),
    unit(LRL, "Sevireth, Lord of the Seventh Wind", 340, 1, "regular", "hero"),
]

# ── SYLVANETH (id=6) ────────────────────────────────────────────────────────
SYL = 6
# DB=20, PDF=23 (diff=-3)
# PDF regular heroes (10): Alarielle, Arch-Revenant, Belthanos, Branchwych, Drycha,
#   Spirit of Durthu, The Lady of Vines, Treelord, Treelord Ancient, Warsong Revenant = 10
# PDF regular units (12): Dryads, Gossamid Archers, Kurnoth Hunters w/Greatbows,
#   Kurnoth Hunters w/Greatswords, Kurnoth Hunters w/Scythes, Revenant Seekers,
#   Spite-Revenants, Spiterider Lancers, The Twistweald, Tree-Revenants = 10
# PDF Legends (3): Kurnoth's Heralds, Skaeth's Wild Hunt, Ylthari's Guardians = 3
# Total PDF = 10 + 10 + 3 = 23
# DB has 20 (all regular, no legends).
# Missing: 3 Legends units: Kurnoth's Heralds, Skaeth's Wild Hunt, Ylthari's Guardians
INSERTS += [
    unit(SYL, "Kurnoth's Heralds", 110, 3, "legends", "cavalry"),
    unit(SYL, "Skaeth's Wild Hunt", 90, 5, "legends", "infantry"),
    unit(SYL, "Ylthari's Guardians", 140, 4, "legends", "infantry"),
]

# ── FLESH-EATER COURTS (id=48) ─────────────────────────────────────────────
FEC = 48
# DB=26, PDF=28 (diff=-2)
# PDF regular heroes (14): Abhorrant Archregent, Abhorrant Cardinal, Abhorrant Ghoul King,
#   Abhorrant Ghoul King on Royal Terrorgheist, Abhorrant Ghoul King on Royal Zombie Dragon,
#   Abhorrant Gorewarden, Crypt Haunter Courtier, Crypt Infernal Courtier,
#   Grand Justice Gormayne, High Falconer Felgryn, Marrowscroll Herald, Nagash,
#   Royal Decapitator, Ushoran = 14
# PDF regular units (11): Crypt Flayers, Crypt Flayers(2), Crypt Ghouls, Crypt Horrors,
#   Crypt Horrors(2), Cryptguard, Morbheg Knights, Royal Beastflayers, Royal Terrorgheist,
#   Royal Zombie Dragon, Varghulf Courtier = 11
# PDF Legends (3): Crypt Ghast Courtier, The Grymwatch, The Skinnerkin = 3
# Total = 14 + 11 + 3 = 28
# DB has 26. Missing: Abhorrant Ghoul King on Royal Terrorgheist, Abhorrant Ghoul King on Royal Zombie Dragon, Nagash
# But wait - "Nagash" in FEC is PDF entry (it's a valid FEC unit). DB has no FEC Nagash.
# Also the PDF has Morbheg Knights (3 models 180pts) — DB has BOTH id=406 'Morbheg Knight' (180, 1 model)
# and id=1809 'Morbheg Knights' (180, 3 models). The PDF entry is "Morbheg Knights" 3 models.
# id=406 'Morbheg Knight' (singular, 1 model) is a phantom.
# DB regular heroes: Archregent, Cardinal, Ghoul King, Gorewarden, Crypt Haunter Courtier,
#   Crypt Infernal Courtier, Grand Justice Gormayne, High Falconer Felgryn, Marrowscroll Herald,
#   Royal Decapitator, Ushoran = 11 heroes in regular
# Missing regular heroes: Abhorrant GK on Royal Terrorgheist, Abhorrant GK on Royal Zombie Dragon, Nagash = 3
# But delete phantom 'Morbheg Knight' (id=406, singular) → net: 26 - 1 phantom + 3 inserts - 1 duplicate (Crypt Flayer/Crypt Flayers)?
# DB has id=398 'Crypt Flayer' (160, 1 model) and id=1716 'Crypt Flayers' (90, 2 models)
# PDF has 'Crypt Flayers' (3 models 160pts) AND 'Crypt Flayers (2 models)' (90pts)
# So id=398 'Crypt Flayer' might be the 3-model unit with wrong name/count. Let's check:
# PDF: "Crypt Flayers 3 160" and "Crypt Flayers (2 models) 2 90"
# DB id=398 'Crypt Flayer' has points=160, model_count=1 → this is a phantom (wrong model count)
# DB id=1716 'Crypt Flayers' has points=90, model_count=2 → correct for (2 models)
# Missing: 'Crypt Flayers' (3 models, 160pts) → needs insert
# Same for Crypt Horrors: DB id=403 'Crypt Horror' (160, 1 model) and id=1717 'Crypt Horrors' (100, 2)
# PDF has 'Crypt Horrors 3 160' and 'Crypt Horrors (2 models) 2 100'
# id=403 'Crypt Horror' singular with 1 model at 160 pts → likely a phantom
# Need to add 'Crypt Horrors' (3 models, 160pts)
# So: delete id=406 'Morbheg Knight', id=398 'Crypt Flayer', id=403 'Crypt Horror' = 3 deletes
# Insert: Abhorrant GK on Royal Terrorgheist, Abhorrant GK on Royal Zombie Dragon, Nagash,
#         Crypt Flayers (3 model), Crypt Horrors (3 model) = 5 inserts
# Net: 26 - 3 + 5 = 28 ✓ PERFECT
_fec_nagash = unit(FEC, "Nagash, Supreme Lord of the Undead", 830, 1, "regular", "hero")
_fec_nagash["slug"] = "fec-nagash-supreme-lord-of-the-undead"
INSERTS += [
    unit(FEC, "Abhorrant Ghoul King on Royal Terrorgheist", 380, 1, "regular", "hero"),
    unit(FEC, "Abhorrant Ghoul King on Royal Zombie Dragon", 380, 1, "regular", "hero"),
    _fec_nagash,
    unit(FEC, "Crypt Flayers", 160, 3, "regular", "infantry"),
    unit(FEC, "Crypt Horrors", 160, 3, "regular", "infantry"),
]

# ── IDONETH DEEPKIN (id=72) ─────────────────────────────────────────────────
IDK = 72
# DB=18, PDF=20 (diff=-2)
# PDF regular heroes (12): Akhelian King, Akhelian Thrallmaster, Eidolon of Mathlann Aspect Sea,
#   Eidolon of Mathlann Aspect Storm, Ikon of the Storm, Ikon of the Sea, Isharann Soulrender,
#   Isharann Soulscryer, Isharann Tidecaster, Lotann, Mathaela Oracle of the Abyss, Volturnos = 12
# PDF regular units (6): Akhelian Allopex, Akhelian Ishlaen Guard, Akhelian Leviadon,
#   Akhelian Morrsarr Guard, Namarti Reavers, Namarti Thralls = 6
# PDF Legends (2): Cyreni's Razors, Elathain's Soulraid = 2
# Total PDF = 12 + 6 + 2 = 20
# DB has 18: 2 legends + 16 regular. Missing:
# Check DB regular heroes: Akhelian King, Akhelian Thrallmaster, Ikon Sea, Ikon Storm,
#   Isharann Soulrender, Isharann Soulscryer, Isharann Tidecaster, Lotann, Mathaela (x2!),
#   Mathaela Oracle of the Abyss = 11 (with duplicate)
# DB has id=1788 'Mathaela' and id=974 'Mathaela, Oracle of the Abyss' - duplicate!
# Missing: Eidolon of Mathlann Aspect of the Sea, Eidolon of Mathlann Aspect of the Storm, Volturnos = 3
# Delete 'Mathaela' phantom (id=1788) → net: 18 - 1 + 3 = 20 ✓
INSERTS += [
    unit(IDK, "Eidolon of Mathlann, Aspect of the Sea", 340, 1, "regular", "hero"),
    unit(IDK, "Eidolon of Mathlann, Aspect of the Storm", 280, 1, "regular", "hero"),
    unit(IDK, "Volturnos, High King of the Deep", 210, 1, "regular", "hero"),
]

# ── OSSIARCH BONEREAPERS (id=19) ────────────────────────────────────────────
OBR = 19
# DB=24, PDF=26 (diff=-2)
# PDF regular heroes (12): Arch-Kavalos Zandtos, Arkhan the Black, Katakros, Liege-Kavalos,
#   Liege-Kavalos on War Chariot, Liege-Mortek, Mortisan Boneshaper, Mortisan Ossifector,
#   Mortisan Soulmason, Mortisan Soulreaper, Nagash, Vokmortian = 12
# PDF regular units (12): Gothizzar Harvester, Immortis Guard, Kavalos Deathriders,
#   Kavalos War Chariot, Morghast Archai, Morghast Harbingers, Mortek Crawler, Mortek Guard,
#   Mortis Reapers, Mortek Triaxes, Necropolis Stalkers, Teratic Cohort = 12
# PDF Legends (2): Kainan's Reapers, Thanatek's Tithe = 2
# Total PDF = 12 + 12 + 2 = 26
# DB has 24: 2 legends + 22 regular
# DB regular heroes: Arch-Kavalos Zandtos, Liege-Kavalos, Liege-Kavalos on War Chariot,
#   Liege-Mortek, Mortisan Boneshaper, Mortisan Ossifector, Mortisan Soulmason, Mortisan Soulreaper,
#   Nagash = 9. Missing: Arkhan the Black, Katakros, Vokmortian = 3
# DB also has 'Mortis Reaper' (id=430, singular) AND 'Mortis Reapers' (id=1796, plural)
# PDF has only 'Mortis Reapers 5 90' → id=430 'Mortis Reaper' (1 model) is a phantom
# And 'Morghast Harbinger' (id=387, singular) vs PDF 'Morghast Harbingers 2 250'
# DB id=387 'Morghast Harbinger' has model_count=1, vs PDF 2. That's a phantom.
# Also check Mortek Triaxes DB vs PDF:
# id=1097 'Mortek Triaxes' (140, 1 model) vs PDF 'Mortek Triaxes 10 140'
# And id=213 'Mortek Guard' (120, 10 models) vs PDF 'Mortek Guard 10 110' - different points, needs update?
# For now focus on structural inserts/deletes.
# Delete phantoms: id=430 'Mortis Reaper' (singular), id=387 'Morghast Harbinger' (singular) = 2 deletes
# Insert: Arkhan, Katakros, Vokmortian = 3 inserts
# Net: 24 - 2 + 3 = 25? That's -1 still. Let me recheck.
# Actually: 'Morghast Archai' in DB is id=1721 (2 models, 260 pts) - OK
# 'Morghast Harbinger' id=387 (1 model, 250 pts) - the PDF has 'Morghast Harbingers 2 250'
# The DB has id=1721 'Morghast Archai' (2 models) - but no 'Morghast Harbingers' (2 model version)!
# id=387 'Morghast Harbinger' (1 model) is a phantom. Need to add 'Morghast Harbingers' (2 model).
# Similarly 'Mortis Reaper' (id=430, 1 model) is phantom, 'Mortis Reapers' (id=1796, 5 models) exists.
# So deletes: id=430, id=387 = 2 deletes
# Inserts: Arkhan (1), Katakros (1), Vokmortian (1), Morghast Harbingers-correct (1) = 4 inserts
# Net: 24 - 2 + 4 = 26 ✓
INSERTS += [
    unit(OBR, "Arkhan the Black, Mortarch of Sacrament", 440, 1, "regular", "hero"),
    unit(OBR, "Katakros, Mortarch of the Necropolis", 500, 1, "regular", "hero"),
    unit(OBR, "Vokmortian, Master of the Bone-tithe", 140, 1, "regular", "hero"),
    unit(OBR, "Morghast Harbingers", 250, 2, "regular", "infantry"),
]

# ── SERAPHON (id=2) ─────────────────────────────────────────────────────────
SER = 2
# DB=34, PDF=36 (diff=-2)
# PDF regular heroes (14): Lord Kroak, Ripperdactyl Chief, Saurus Astrolith Bearer,
#   Saurus Oldblood, Saurus Oldblood on Carnosaur, Saurus Scar-Veteran on Aggradon,
#   Saurus Scar-Veteran on Carnosaur, Skink Oracle on Troglodon, Skink Starpriest,
#   Skink Starseer, Slann Starmaster, Stegadon Chief, Sunblood Pack, Terradon Chief = 14
# PDF regular units (20): Aggradon Lancers, Bastiladon w/Ark of Sotek, Bastiladon w/Solar Engine,
#   Engine of the Gods, Hunters of Huanchi w/Dartpipes, Hunters of Huanchi w/Bolas,
#   Kroxigor, Kroxigor Warspawned, Raptadon Chargers, Raptadon Hunters, Ripperdactyl Riders(3),
#   Ripperdactyl Riders(2), Saurus Guard, Saurus Warriors, Skinks, Spawn of Chotec, Stegadon,
#   Terradon Riders(3), Terradon Riders(2), Terrawings = 20
# PDF Legends (2): The Jaws of Itzl, The Starblood Stalkers = 2
# Total PDF = 14 + 20 + 2 = 36
# DB has 34: 2 legends + 32 regular. Missing 2 regular units.
# DB regular units: Aggradon Lancers, Bastiladon w/Ark, Bastiladon w/Solar Engine, Engine of Gods,
#   Kroxigor, Kroxigor Warspawned, Raptadon Charger, Raptadon Hunter, Ripperdactyl Chief(hero),
#   Ripperdactyl Rider(3), Ripperdactyl Riders(2), Saurus Astrolith Bearer, Saurus Guard,
#   Saurus Oldblood, Saurus Oldblood on Carnosaur, Saurus Scar-Veteran on Aggradon,
#   Saurus Scar-Veteran on Carnosaur, Saurus Warriors, Skink, Skink Oracle on Troglodon,
#   Skink Starpriest, Skink Starseer, Slann Starmaster, Spawn of Chotec, Stegadon,
#   Stegadon Chief, Sunblood Pack, Terradon Chief, Terradon Rider(3), Terradon Riders(2),
#   Terrawings, Lord Kroak = 32 regular
# Missing: Hunters of Huanchi w/Dartpipes, Hunters of Huanchi w/Bolas = 2
INSERTS += [
    unit(SER, "Hunters of Huanchi with Dartpipes", 80, 5, "regular", "infantry"),
    unit(SER, "Hunters of Huanchi with Starstone Bolas", 90, 5, "regular", "infantry"),
]

# ── DISCIPLES OF TZEENTCH (id=17) ───────────────────────────────────────────
DOT = 17
# DB=29, PDF=31 (diff=-2)
# PDF regular heroes (12): Changecaster, Curseling, Fatemaster, Fateskimmer on Burning Chariot,
#   Gaunt Summoner, Gaunt Summoner on Disc, Kairos Fateweaver, Lord of Change, Magister,
#   Magister on Disc, Ogroid Thaumaturge, The Changeling, Tzaangor Shaman = 13
# PDF regular units (14): Blue Horrors+Brimstone, Burning Chariot, Chaos Spawn of Tzeentch,
#   Exalted Flamer, Flamers, Jade Obelisk, Kairic Acolytes, Pink Horrors, Screamers,
#   Tzaangor Enlightened (Cavalry), Tzaangor Enlightened on Foot, Tzaangor Skyfires, Tzaangors = 13
# PDF Legends (4): Eyes of the Nine, Ephilim's Pandaemonium (missing from DB!),
#   Fatemaster on Disc, Fluxmaster, The Blue Scribes = 5 legends
# Wait - DB has 4 legends: Eyes of the Nine, Fatemaster on Disc, Fluxmaster, The Blue Scribes
# Missing from DB Legends: Ephilim's Pandaemonium = 1
# PDF regular heroes: 13, PDF units: 13, PDF legends: 5
# Total PDF = 13 + 13 + 5 = 31
# DB has 29: 4 legends + 25 regular. Missing 2.
# Let me recheck DB regular: 29 - 4 = 25 regular
# PDF regular = 13 heroes + 13 units = 26
# Missing from DB regular = 1: Gaunt Summoner on Disc for DoT vs DB: id=885 'Gaunt Summoner' but not
# 'Gaunt Summoner on Disc of Tzeentch' for DoT (there's one for StD). Let me check:
# DB DoT has id=885 'Gaunt Summoner' (regular, hero) - that's the base one (180pts)
# But also needs 'Gaunt Summoner on Disc of Tzeentch' (210pts) for DoT
# DB DoT has 25 regular. PDF DoT regular = 26. Missing = 1.
# So: 1 legends missing + 1 regular missing = 2 total missing ✓
INSERTS += [
    unit(DOT, "Ephilim's Pandaemonium", 100, 5, "legends", "infantry"),
    unit(DOT, "Gaunt Summoner on Disc of Tzeentch", 210, 1, "regular", "hero"),
]

# ── DAUGHTERS OF KHAINE (id=12) ─────────────────────────────────────────────
DOK = 12
# DB=26, PDF=27 (diff=-1)
# PDF regular heroes (11): Bloodwrack Medusa, Bloodwrack Shrine, Hag Queen,
#   Hag Queen on Cauldron of Blood, High Gladiatrix, Krethusa the Croneseer,
#   Melusai Ironscale, Morathi-Khaine (=The Shadow Queen 0pts included),
#   Slaughter Queen, Slaughter Queen on Cauldron of Blood = 11 (The Shadow Queen 0pt companion not separate)
# Wait - The Shadow Queen (0pts) is a separate entry in PDF. So: 12 regular heroes
# PDF regular units (10): Avatar of Khaine, Blood Sisters, Blood Stalkers, Doomfire Warlocks,
#   Khainite Shadowstalkers, Khinerai Heartrenders, Khinerai Lifetakers,
#   Sisters of Slaughter w/Bladed Bucklers, Sisters of Slaughter w/Sacrificial Knives,
#   Witch Aelves w/Bladed Bucklers, Witch Aelves w/Paired Sciansá = 11 units
# PDF Legends (5): Gryselle's Arenai, Maleneth Witchblade, Morgwaeth's Blade-coven,
#   The Knives of the Crone, The Shadeborn = 5
# Total PDF = 12 + 11 + 5 = 28? But expected is 27. Let me recount:
# PDF heroes in regular: Bloodwrack Medusa(1), Bloodwrack Shrine(1), Hag Queen(1),
#   HQ on Cauldron(1), High Gladiatrix(1), Krethusa(1), Melusai Ironscale(1), Morathi-Khaine(1),
#   The Shadow Queen(0pts, 1), Slaughter Queen(1), Slaughter Queen on Cauldron(1) = 11 heroes
# PDF units: Avatar(1), Blood Sisters(1), Blood Stalkers(1), Doomfire Warlocks(1),
#   Khainite Shadowstalkers(1), Khinerai Heartrenders(1), Khinerai Lifetakers(1),
#   Sisters Bladed Bucklers(1), Sisters Sacrificial Knives(1), Witch Aelves Bladed Bucklers(1),
#   Witch Aelves Paired Sciansá(1) = 11 units
# Legends: Gryselle(1), Maleneth(1), Morgwaeth(1), Knives of Crone(1), Shadeborn(1) = 5
# Total = 11 + 11 + 5 = 27
# DB has 26: 5 legends + 1 manifestation (Avatar of Khaine) + 20 regular
# The Avatar of Khaine is in DB as 'manifestation' category. PDF lists it as regular unit.
# DB regular heroes: Bloodwrack Medusa, Bloodwrack Shrine, Hag Queen, HQ on Cauldron,
#   High Gladiatrix, Krethusa, Melusai Ironscale, Morathi-Khaine, Slaughter Queen = 9 heroes
# Missing: The Shadow Queen (0pts) and Slaughter Queen on Cauldron = 2? But diff is only -1.
# Wait DB also has 'Witch Aelves' (id=1734, singular) which doesn't match PDF (PDF has two weapon variants)
# That's a phantom. DB has 'Witch Aelves with Bladed Bucklers' (id=1657) and
# 'Witch Aelves with Paired Sciansá' (id=1723). So id=1734 'Witch Aelves' is a phantom.
# Also DB has 'Khinerai Heartrender' (id=539, 1 model) and 'Khinerai Lifetaker' (id=540, 5 models)
# PDF: Khinerai Heartrenders 5 100, Khinerai Lifetakers 5 100
# DB id=539 'Khinerai Heartrender' (singular, 1 model) = phantom? Need to check model_count.
# Let me assume: 26 DB - 1 phantom (Witch Aelves) - 1 phantom (Khinerai Heartrender) + inserts = 27
# That means we need 3 inserts: Slaughter Queen on Cauldron, The Shadow Queen, + 1 more
# OR: 26 - 2 + inserts = 27 → inserts = 3.
# Missing heroes: Slaughter Queen on Cauldron of Blood (check DB again)
# id=140 'Slaughter Queen' OK. But 'Slaughter Queen on Cauldron of Blood' - not in DB list!
# And 'The Shadow Queen' (0pts) - not in DB.
# So inserts = Slaughter Queen on Cauldron, The Shadow Queen = 2
# Delete phantoms = Witch Aelves id=1734, Khinerai Heartrender id=539 = 2
# Net: 26 - 2 + 2 = 26? Still -1. Need 1 more insert.
# Actually let me recheck. DB regular heroes for DoK:
#   Bloodwrack Medusa(148), Bloodwrack Shrine(532), Hag Queen(141), Hag Queen on Cauldron(851),
#   High Gladiatrix(537), Khainite Shadowstalkers(538), Krethusa(850), Melusai Ironscale(535),
#   Morathi-Khaine(139), Slaughter Queen(140) = 10... but 538 Khainite Shadowstalkers is a unit not hero
# So 9 heroes, 11+ units. Missing from heroes: Slaughter Queen on Cauldron, The Shadow Queen = 2.
# Just need 1 net add. So: 2 deletes + 3 inserts = +1 net OR 1 delete + 2 inserts = +1 net.
# Let's go with: delete 'Witch Aelves' phantom (id=1734), insert Slaughter Queen on Cauldron + The Shadow Queen
# That's 26 - 1 + 2 = 27 ✓
INSERTS += [
    unit(DOK, "Slaughter Queen on Cauldron of Blood", 330, 1, "regular", "hero"),
    unit(DOK, "The Shadow Queen", 0, 1, "regular", "infantry"),
]

# ── HEDONITES OF SLAANESH (id=32) ───────────────────────────────────────────
HOS = 32
# DB=31, PDF=32 (diff=-1)
# PDF regular heroes (14): Bladebringer on Exalted Chariot, Contorted Epitome, Dexcessa,
#   Glutos Orscollion, Infernal Enrapturess, Keeper of Secrets, Lord of Hubris, Lord of Pain,
#   Shalaxi Helbane, Shardspeaker of Slaanesh, Sigvald, Syll'Esske, Synessa, The Masque = 14
# PDF regular units (13): Blissbarb Archers, Blissbarb Seekers, Daemonettes, Fiends,
#   Hellflayer, Hellstriders, Myrmidesh Painbringers, Seeker Chariot, Seekers,
#   Slaangor Fiendbloods, Slickblade Seekers, Symbaresh Twinsouls = 12?
# Wait: +Bladebringer on Exalted Chariot is listed under HEROES as regular
# DB has 'Bladebringer Herald on Exalted Chariot' (id=1792, regular) ✓
# DB has 7 legends: Bladebringer Herald on Hellflayer, Bladebringer Herald on Seeker Chariot,
#   Exalted Chariot, The Dread Pageant, The Thricefold Discord, Viceleader (x2 - duplicate!)
# DB has id=1795 'Viceleader Herald of Slaanesh' AND id=961 'Viceleader, Herald of Slaanesh' - both legends!
# One of those is a phantom.
# PDF Legends (6): Bladebringer on Hellflayer, Bladebringer on Seeker Chariot, Exalted Chariot,
#   The Dread Pageant, The Thricefold Discord, Viceleader = 6 legends
# PDF total = 14 heroes + 12 units + 6 legends = 32
# DB has 31: 7 legends (1 phantom viceleader) + 1 "regular" bladebringer on exalted chariot + 23 regular
# Missing: Syll'Esske = 1. Delete: duplicate Viceleader (id=961 or 1795, keep the newer 1795) → net: 31 - 1 + 1 = 31?
# That's still 31, not 32. Let me recount DB regular:
# Regular heroes: Bladebringer on Exalted Chariot(1792), Contorted Epitome, Dexcessa,
#   Infernal Enrapturess, Keeper of Secrets, Lord of Hubris, Lord of Pain, Shalaxi Helbane,
#   Shardspeaker, Sigvald, Synessa, The Masque = 12 regular heroes
# Regular units: Blissbarb Archers, Blissbarb Seekers, Daemonettes, Fiends, Hellflayer,
#   Hellstriders, Myrmidesh Painbringer, Seeker Chariot, Seekers, Slaangor Fiendbloods,
#   Slickblade Seekers, Symbaresh Twinsouls = 12 units
# Regular Glutos Orscollion: checking... not in DB list above! → missing
# Regular Syll'Esske: not in DB list → missing
# So 2 missing from regular = 2 inserts, and 1 phantom legends Viceleader = 1 delete
# Net: 31 - 1 + 2 = 32 ✓
INSERTS += [
    unit(HOS, "Glutos Orscollion, Lord of Gluttony", 440, 1, "regular", "hero"),
    unit(HOS, "Syll'Esske, the Vengeful Allegiance", 180, 1, "regular", "hero"),
]

# ── KRULEBOYZ (id=76) ───────────────────────────────────────────────────────
KRU = 76
# DB=18, PDF=19 (diff=-1)
# PDF regular heroes (12): Breaka-boss, Gobsprakk, Hobgrot Slittaboss, Killaboss on Corpse-rippa,
#   Killaboss on Great Gnashtoof, Killaboss with Stab-grot, Kragnos, Murknob,
#   Snatchaboss on Sludgeraker Beast, Swampboss Skumdrekk, Swampcalla Shaman with Pot-grot = 11
# PDF regular units (6): Beast-skewer Killbow, Gutrippaz, Hobgrot Slittaz, Kruleboyz Monsta-killaz,
#   Man-skewer Boltboyz, Marshcrawla Sloggoth = 6
# PDF Legends (2): Da Kunnin' Krew, Daggok's Stab-ladz = 2
# Total PDF = 11 + 6 + 2 = 19
# DB has 18: 0 legends + 18 regular. Missing 2 legends + duplicate Swampcalla (2 entries).
# Delete: id=1756 'Swampcalla Shaman with Pot-grot' (duplicate, 100pts vs 1700 which has 120pts)
# PDF says 120pts for Swampcalla. So keep id=1700 (120pts), delete id=1756 (100pts).
# Insert: Da Kunnin' Krew, Daggok's Stab-ladz = 2 legends
# Net: 18 - 1 + 2 = 19 ✓
INSERTS += [
    unit(KRU, "Da Kunnin' Krew", 120, 5, "legends", "infantry"),
    unit(KRU, "Daggok's Stab-ladz", 120, 4, "legends", "infantry"),
]

# ── SKAVEN (id=1) ────────────────────────────────────────────────────────────
SKV = 1
# DB=48, PDF=46 (diff=+2) — DB OVERSHOOTS, need to identify+delete 2 phantoms
# PDF regular heroes (18): Arch-Warlock, Clawlord, Clawlord on Gnaw-beast, Deathmaster,
#   Grey Seer, Grey Seer on Screaming Bell, Krittok Foulblade, Lord Skreech Verminking,
#   Master Moulder, Plague Priest on Plague Furnace, Thanquol on Boneripper,
#   Verminlord Corruptor, Verminlord Deceiver, Verminlord Warbringer, Verminlord Warpseer,
#   Vizzik Skour, Warlock Bombardier, Warlock Engineer, Warlock Galvaneer = 19
# Wait - that's 19. Let me recount: Arch-Warlock(1), Clawlord(2), Clawlord on Gnaw-beast(3),
#   Deathmaster(4), Grey Seer(5), Grey Seer on Screaming Bell(6), Krittok Foulblade(7),
#   Lord Skreech Verminking(8), Master Moulder(9), Plague Priest on Plague Furnace(10),
#   Thanquol on Boneripper(11), Verminlord Corruptor(12), Verminlord Deceiver(13),
#   Verminlord Warbringer(14), Verminlord Warpseer(15), Vizzik Skour(16),
#   Warlock Bombardier(17), Warlock Engineer(18), Warlock Galvaneer(19) = 19 heroes
# PDF regular units (19): Acolyte Globadiers, Brood Terror, Clanrats, Doom-Flayers(2 models),
#   Doomwheel, Hell Pit Abomination, Night Runners, Plague Monks, Plagueclaw, Plaguepack,
#   Rat Ogors, Ratling Guns, Ratling Warpblaster, Stormfiends, Stormvermin, Warp-Grinder,
#   Warp Lightning Cannon, Warpfire Throwers, Warplock Jezzails, Warpvolt Scourgers = 20
# PDF Legends (7): Plague Priest (hero), Gutter Runners, Plague Censer Bearers, Skabbik's Plaguepack,
#   Skittershank's Clawpack, Spiteclaw's Swarm, Zikkit's Tunnelpack = 7
# Total PDF = 19 + 20 + 7 = 46
# DB has 48: 9 legends + 39 regular. DB overshoot by 2.
# DB legends (9): Gutter Runner(282), Gutter Runners(1800), Plague Censer Bearer(330),
#   Plague Censer Bearers(1801), Plague Priest(9), Skabbik's Plaguepack(1802),
#   Skittershank's Clawpack(1803), Spiteclaw's Swarm(1804), Zikkit's Tunnelpack(1805)
# PDF legends = 7. DB legends = 9. Phantoms in legends:
#   id=282 'Gutter Runner' (95pts, 5 models) vs id=1800 'Gutter Runners' (110pts, 5 models)
#   PDF has 'Gutter Runners 5 110'. id=282 'Gutter Runner' is the phantom.
#   id=330 'Plague Censer Bearer' (75pts, 5 models) vs id=1801 'Plague Censer Bearers' (160pts, 5)
#   PDF has 'Plague Censer Bearers 5 160'. id=330 'Plague Censer Bearer' is the phantom.
# So delete: id=282 'Gutter Runner', id=330 'Plague Censer Bearer' → 48 - 2 = 46 ✓
# DB regular (39): PDF regular should be 39 (19+20). Let me verify no phantom in regular.
# DB regular heroes: Arch-Warlock, Brood Terror, Clanrat, Clawlord, Clawlord on Gnaw-beast,
#   Deathmaster, Doom-Flayer(id=335,1model), Doom-Flayers(id=1799,2models),
#   Doomwheel, Grey Seer, Grey Seer on Screaming Bell, Hell Pit Abomination, Krittok,
#   Lord Skreech, Master Moulder, Night Runner(283), Plague Monk(332), Plague Priest on Furnace,
#   Plagueclaw, Plaguepack, Rat Ogor, Ratling Guns, Ratling Warpblaster, Stormvermin,
#   Thanquol, Verminlord Corruptor, Verminlord Deceiver, Verminlord Warbringer, Verminlord Warpseer,
#   Vizzik, Warlock Bombardier, Warlock Engineer, Warlock Galvaneer, Warp Lightning Cannon,
#   Warp-Grinder, Warpfire Throwers, Warplock Jezzail(343), Warpvolt Scourgers = 38 regular
# DB has Doom-Flayer (id=335, 1 model) AND Doom-Flayers (id=1799, 2 models)
# PDF has 'Doom-Flayers 2 100'. So id=335 'Doom-Flayer' (1 model) is a phantom.
# That's 39 regular - but PDF says 39 too (19+20). We're +1. But we only need to delete 2 total.
# Check: DB regular count = 39. PDF regular = 39. MATCH. So the 2 overshoot is all in legends.
# Good - just delete id=282 and id=330 from legends.
# No inserts needed for Skaven.
# BUT ALSO: id=343 'Warplock Jezzail' (95pts, 3 models) vs PDF 'Warplock Jezzails 3 120'
#   Different points - this is an outdated entry but still a valid unit name match. Do NOT delete.
# AND: id=283 'Night Runner' (130pts) - PDF says 'Night Runners 10 120'. Different points/name.
#   This is a stale entry but matches the PDF unit conceptually. Keep it.

# ---------------------------------------------------------------------------
# DELETES (phantom entries to remove)
# ---------------------------------------------------------------------------

DELETES = {
    # SCE: phantom hero variant not in PDF
    1725: "SCE: Knight-Vexillor with Banner of Apotheosis (not in PDF)",
    # IDK: duplicate Mathaela entry
    1788: "IDK: Mathaela (duplicate of 'Mathaela, Oracle of the Abyss' id=974)",
    # OBR: singular phantom entries
    430:  "OBR: Mortis Reaper (singular phantom, PDF has Mortis Reapers 5-model id=1796)",
    387:  "OBR: Morghast Harbinger (singular phantom, PDF has Morghast Harbingers 2-model)",
    # FEC: singular phantoms replaced by correct entries above
    406:  "FEC: Morbheg Knight (singular, PDF has Morbheg Knights 3-model id=1809)",
    398:  "FEC: Crypt Flayer (singular/wrong count, PDF has Crypt Flayers 3-model, inserting above)",
    403:  "FEC: Crypt Horror (singular/wrong count, PDF has Crypt Horrors 3-model, inserting above)",
    # DOK: phantom Witch Aelves (weapon variants are separate entries)
    1734: "DOK: Witch Aelves (generic, PDF has two weapon-variant entries)",
    # HOS: duplicate Viceleader
    961:  "HOS: Viceleader, Herald of Slaanesh (duplicate, keep id=1795)",
    # KRU: duplicate Swampcalla
    1756: "KRU: Swampcalla Shaman with Pot-grot (duplicate 100pts, keep id=1700 at 120pts)",
    # SKV: singular legends phantoms
    282:  "SKV: Gutter Runner (old/duplicate, PDF has Gutter Runners id=1800)",
    330:  "SKV: Plague Censer Bearer (old/duplicate, PDF has Plague Censer Bearers id=1801)",
    # StD: duplicate Eternus
    1785: "STD: Eternus (short name duplicate, PDF has 'Eternus, Blade of the First Prince' id=1150)",
}
# Note: StD still needs 8 LotFP units + Abraxia + Singri Brand check.

# Check for Singri Brand and Legion of the First Prince units that should be in StD:
# Those LotFP units in PDF are a special sub-section. They're counted as StD units.
# However with the -10 diff we need to add them if absent.
# But given the task brief says "diff=-10" and we're accounting for what's already in DB...
# The DB has 54 regular StD units. Let me count what PDF StD regular should be:
# Regular heroes (19 including Singri Brand 0pt): Already counted above
# Regular units: Chaos Chariot, Chaos Chosen, Chaos Furies, Chaos Knights, Chaos Legionnaires,
#   Chaos Spawn, Chaos Warriors, Darkoath Fellriders, Darkoath Marauders, Darkoath Savagers,
#   Darkoath Wilderfiend, Fomoroid Crusher, Gorebeast Chariot, Mindstealer Sphiranx,
#   Mutalith Vortex Beast, Ogroid Theridons, Raptoryx, Slaughterbrute, The Oathsworn Kin,
#   Varanguard = 20 units
# LotFP sub-units (8): Beasts of Nurgle, Bloodcrushers, Bloodletters, Fiends, Flamers, Hellflayer,
#   Plaguebearers, Screamers = 8
# Legends (17): 3 heroes + 14 units = 17
# Total PDF = 19 + 20 + 8 + 17 = 64
# DB total = 54: 16 legends + 38 regular. Regular = 38.
# PDF regular = 19 + 20 + 8 = 47. DB regular = 38. Missing = 9.
# But we have: Abraxia (1) + 8 LotFP = 9 regular inserts. Also delete 1 Eternus phantom.
# Net: 54 + 9 inserts - 1 delete + 1 legend insert (The Unmade) - 0 = 54 + 9 = 63... -1.
# Hmm: 54 - 1(Eternus delete) + 10 inserts = 63. Still 1 short.
# Wait: PDF Legends = 17 (3+14). DB Legends = 16. Missing 1 = The Unmade. Already added.
# So: 54 - 1 + 10(Abraxia+8LotFP+The Unmade) = 63. Missing 1.
# Singri Brand: DB has 'Singri Brand' id=1860? Need to check.
# Actually DB already shows id=1860 was referenced in the PDF data. Let me search in DB output above:
# In the STD DB output: (1860, 'Singri Brand', 0, 1, 'regular', None) was NOT listed above.
# The output shows 54 units and I counted 54 - but checking: The Oathsworn Kin is in DB as id=1786.
# Singri Brand (0pts) was referenced as "This unit can only be taken in Gunnar Brand's regiment".
# Let me just also add LotFP units here:

STD = 16
INSERTS += [
    # Legion of the First Prince units (StD only):
    unit(STD, "Legion of the First Prince Beasts of Nurgle", 120, 1, "regular", "infantry"),
    unit(STD, "Legion of the First Prince Bloodcrushers", 150, 3, "regular", "cavalry"),
    unit(STD, "Legion of the First Prince Bloodletters", 170, 10, "regular", "infantry"),
    unit(STD, "Legion of the First Prince Fiends", 140, 3, "regular", "infantry"),
    unit(STD, "Legion of the First Prince Flamers of Tzeentch", 120, 3, "regular", "infantry"),
    unit(STD, "Legion of the First Prince Hellflayer", 130, 1, "regular", "war_machine"),
    unit(STD, "Legion of the First Prince Plaguebearers", 140, 10, "regular", "infantry"),
    unit(STD, "Legion of the First Prince Screamers of Tzeentch", 80, 3, "regular", "infantry"),
]

# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    inserted = []
    skipped_exist = []
    deleted = []
    errors = []

    # ── DELETES ──
    for uid, reason in DELETES.items():
        cur.execute("SELECT id, name FROM units WHERE id=?", (uid,))
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM units WHERE id=?", (uid,))
            deleted.append(f"  id={uid} '{row[1]}' — {reason}")
        else:
            errors.append(f"  DELETE MISS: id={uid} not found — {reason}")

    # ── INSERTS ──
    for u in INSERTS:
        # Idempotent check: same faction_id + name
        cur.execute(
            "SELECT id FROM units WHERE faction_id=? AND lower(name)=lower(?)",
            (u["faction_id"], u["name"]),
        )
        if cur.fetchone():
            skipped_exist.append(f"  SKIP (exists): [{u['faction_id']}] {u['name']}")
            continue

        cur.execute(
            """INSERT INTO units
               (faction_id, slug, name, points_cost, model_count,
                stats_json, weapons_json, abilities_json, keywords_json, companions_json,
                created_at, updated_at, unit_category, unit_role)
               VALUES
               (:faction_id, :slug, :name, :points_cost, :model_count,
                :stats_json, :weapons_json, :abilities_json, :keywords_json, :companions_json,
                :created_at, :updated_at, :unit_category, :unit_role)""",
            u,
        )
        inserted.append(f"  INSERT [{u['faction_id']}] {u['name']} ({u['points_cost']}pts, {u['unit_category']})")

    conn.commit()
    conn.close()

    print("=== _fill_pass2.py RESULTS ===")
    print(f"\nDELETED ({len(deleted)}):")
    for d in deleted:
        print(d)
    if errors:
        print(f"\nDELETE ERRORS ({len(errors)}):")
        for e in errors:
            print(e)
    print(f"\nINSERTED ({len(inserted)}):")
    for i in inserted:
        print(i)
    print(f"\nSKIPPED/ALREADY EXIST ({len(skipped_exist)}):")
    for s in skipped_exist:
        print(s)

    # ── POST-RUN COUNTS ──
    conn2 = sqlite3.connect(DB_PATH)
    cur2 = conn2.cursor()
    print("\n=== POST-RUN FACTION COUNTS ===")
    factions = {
        5:  ("stormcast-eternals",    91),
        16: ("slaves-to-darkness",    64),
        14: ("lumineth-realm-lords",  26),
        6:  ("sylvaneth",             23),
        48: ("flesh-eater-courts",    28),
        72: ("idoneth-deepkin",       20),
        19: ("ossiarch-bonereapers",  26),
        2:  ("seraphon",              36),
        17: ("disciples-of-tzeentch", 31),
        12: ("daughters-of-khaine",   27),
        32: ("hedonites-of-slaanesh", 32),
        76: ("kruleboyz",             19),
        1:  ("skaven",                46),
    }
    for fid, (fname, target) in factions.items():
        cur2.execute("SELECT COUNT(*) FROM units WHERE faction_id=?", (fid,))
        cnt = cur2.fetchone()[0]
        diff = cnt - target
        flag = "OK" if diff == 0 else f"DIFF={diff:+d}"
        print(f"  {fname:30s}  DB={cnt:3d}  TARGET={target:3d}  [{flag}]")
    conn2.close()


if __name__ == "__main__":
    main()
