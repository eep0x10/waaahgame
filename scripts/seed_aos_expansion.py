import sys
import os
import re
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

WAHAPEDIA_BASE = 'https://wahapedia.ru/aos4/factions'


def _slug(name):
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


# ---------------------------------------------------------------------------
# Unit data
# ---------------------------------------------------------------------------

# (name, pts, role, can_be_general, can_be_reinforced, model_count, keywords, companions, stats)

STORMCAST_UNITS = [
    (
        'Lord-Imperatant', 140, 'Hero', True, False, 1,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_STORMCAST_ETERNALS', 'max': None}],
        {'move': '5"', 'save': '3+', 'control': '2', 'health': '6'},
    ),
    (
        'Knight-Vexillor with Banner of Apotheosis', 120, 'Hero', True, False, 1,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_STORMCAST_ETERNALS', 'max': None}],
        {'move': '5"', 'save': '3+', 'control': '2', 'health': '5'},
    ),
    (
        'Lord-Castellant', 130, 'Hero', True, False, 1,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_STORMCAST_ETERNALS', 'max': None}],
        {'move': '5"', 'save': '3+', 'control': '2', 'health': '6'},
    ),
    (
        'Lord-Relictor', 140, 'Hero', True, False, 1,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'PRIEST', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_STORMCAST_ETERNALS', 'max': None}],
        {'move': '5"', 'save': '3+', 'control': '2', 'health': '6'},
    ),
    (
        'Yndrasta, the Celestial Spear', 280, 'Hero', True, False, 1,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'UNIQUE', 'HERO', 'MONSTER'],
        [{'type': 'keyword', 'value': 'ANY_STORMCAST_ETERNALS', 'max': None}],
        {'move': '12"', 'save': '3+', 'control': '5', 'health': '12'},
    ),
    (
        'Liberators', 110, 'Infantry', False, True, 5,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'INFANTRY', 'BATTLELINE'],
        [],
        {'move': '5"', 'save': '3+', 'control': '1', 'health': '2'},
    ),
    (
        'Vindictors', 130, 'Infantry', False, True, 5,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'INFANTRY', 'BATTLELINE'],
        [],
        {'move': '5"', 'save': '3+', 'control': '1', 'health': '2'},
    ),
    (
        'Annihilators', 180, 'Infantry', False, False, 3,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'INFANTRY'],
        [],
        {'move': '4"', 'save': '2+', 'control': '1', 'health': '3'},
    ),
    (
        'Praetors', 200, 'Infantry', False, False, 3,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'INFANTRY'],
        [],
        {'move': '5"', 'save': '3+', 'control': '1', 'health': '3'},
    ),
    (
        'Vanguard-Raptors with Longstrike Crossbows', 210, 'Infantry', False, False, 3,
        ['ORDER', 'STORMCAST_ETERNALS', 'VANGUARD_CHAMBER', 'INFANTRY'],
        [],
        {'move': '5"', 'save': '4+', 'control': '1', 'health': '2'},
    ),
    (
        'Stormdrake Guard', 340, 'Cavalry', False, False, 2,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'CAVALRY', 'MONSTER'],
        [],
        {'move': '10"', 'save': '3+', 'control': '2', 'health': '8'},
    ),
    (
        'Celestar Ballista', 140, 'War Machine', False, False, 1,
        ['ORDER', 'STORMCAST_ETERNALS', 'WARRIOR_CHAMBER', 'WAR_MACHINE'],
        [],
        {'move': '3"', 'save': '4+', 'control': '1', 'health': '8'},
    ),
]

SYLVANETH_UNITS = [
    (
        'Drycha Hamadreth', 290, 'Hero', True, False, 1,
        ['ORDER', 'SYLVANETH', 'UNIQUE', 'HERO', 'MONSTER'],
        [{'type': 'keyword', 'value': 'ANY_SYLVANETH', 'max': None}],
        {'move': '7"', 'save': '4+', 'control': '5', 'health': '12'},
    ),
    (
        'Treelord Ancient', 290, 'Hero', True, False, 1,
        ['ORDER', 'SYLVANETH', 'HERO', 'MONSTER'],
        [{'type': 'keyword', 'value': 'ANY_SYLVANETH', 'max': None}],
        {'move': '7"', 'save': '4+', 'control': '5', 'health': '12'},
    ),
    (
        'Branchwych', 100, 'Hero', True, False, 1,
        ['ORDER', 'SYLVANETH', 'HERO', 'WIZARD'],
        [{'type': 'keyword', 'value': 'ANY_SYLVANETH', 'max': None}],
        {'move': '7"', 'save': '5+', 'control': '2', 'health': '5'},
    ),
    (
        'Arch-Revenant', 120, 'Hero', True, False, 1,
        ['ORDER', 'SYLVANETH', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_SYLVANETH', 'max': None}],
        {'move': '7"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Spirit of Durthu', 370, 'Hero', True, False, 1,
        ['ORDER', 'SYLVANETH', 'HERO', 'MONSTER'],
        [{'type': 'keyword', 'value': 'ANY_SYLVANETH', 'max': None}],
        {'move': '7"', 'save': '3+', 'control': '5', 'health': '14'},
    ),
    (
        'Dryads', 110, 'Infantry', False, True, 10,
        ['ORDER', 'SYLVANETH', 'INFANTRY', 'BATTLELINE'],
        [],
        {'move': '7"', 'save': '5+', 'control': '1', 'health': '1'},
    ),
    (
        'Tree-Revenants', 120, 'Infantry', False, True, 5,
        ['ORDER', 'SYLVANETH', 'INFANTRY', 'BATTLELINE'],
        [],
        {'move': '7"', 'save': '5+', 'control': '1', 'health': '1'},
    ),
    (
        'Spite-Revenants', 110, 'Infantry', False, True, 10,
        ['ORDER', 'SYLVANETH', 'INFANTRY'],
        [],
        {'move': '7"', 'save': '5+', 'control': '1', 'health': '1'},
    ),
    (
        'Kurnoth Hunters with Greatswords', 240, 'Infantry', False, False, 3,
        ['ORDER', 'SYLVANETH', 'KURNOTH_HUNTERS', 'INFANTRY'],
        [],
        {'move': '5"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Kurnoth Hunters with Greatbows', 240, 'Infantry', False, False, 3,
        ['ORDER', 'SYLVANETH', 'KURNOTH_HUNTERS', 'INFANTRY'],
        [],
        {'move': '5"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Treelord', 240, 'Behemoth', False, False, 1,
        ['ORDER', 'SYLVANETH', 'MONSTER'],
        [],
        {'move': '7"', 'save': '4+', 'control': '5', 'health': '12'},
    ),
    (
        'Revenant Seekers', 200, 'Cavalry', False, True, 5,
        ['ORDER', 'SYLVANETH', 'CAVALRY'],
        [],
        {'move': '10"', 'save': '5+', 'control': '1', 'health': '2'},
    ),
]

NIGHTHAUNT_UNITS = [
    (
        'Krulghast Cruciator', 150, 'Hero', True, False, 1,
        ['DEATH', 'NIGHTHAUNT', 'MALIGNANT', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_NIGHTHAUNT', 'max': None}],
        {'move': '8"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Spirit Torment', 110, 'Hero', True, False, 1,
        ['DEATH', 'NIGHTHAUNT', 'MALIGNANT', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_NIGHTHAUNT', 'max': None}],
        {'move': '8"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Guardian of Souls', 150, 'Hero', True, False, 1,
        ['DEATH', 'NIGHTHAUNT', 'MALIGNANT', 'HERO', 'WIZARD'],
        [{'type': 'keyword', 'value': 'ANY_NIGHTHAUNT', 'max': None}],
        {'move': '8"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Lord Executioner', 110, 'Hero', True, False, 1,
        ['DEATH', 'NIGHTHAUNT', 'MALIGNANT', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_NIGHTHAUNT', 'max': None}],
        {'move': '8"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Knight of Shrouds', 100, 'Hero', True, False, 1,
        ['DEATH', 'NIGHTHAUNT', 'MALIGNANT', 'HERO'],
        [{'type': 'keyword', 'value': 'ANY_NIGHTHAUNT', 'max': None}],
        {'move': '8"', 'save': '4+', 'control': '2', 'health': '5'},
    ),
    (
        'Chainrasps', 115, 'Infantry', False, True, 10,
        ['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'INFANTRY', 'BATTLELINE'],
        [],
        {'move': '8"', 'save': '5+', 'control': '1', 'health': '1'},
    ),
    (
        'Bladegheist Revenants', 180, 'Infantry', False, True, 10,
        ['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'INFANTRY'],
        [],
        {'move': '8"', 'save': '4+', 'control': '1', 'health': '1'},
    ),
    (
        'Grimghast Reapers', 180, 'Infantry', False, True, 10,
        ['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'INFANTRY'],
        [],
        {'move': '8"', 'save': '4+', 'control': '1', 'health': '1'},
    ),
    (
        'Hexwraiths', 150, 'Cavalry', False, True, 5,
        ['DEATH', 'NIGHTHAUNT', 'CAVALRY', 'BATTLELINE'],
        [],
        {'move': '12"', 'save': '4+', 'control': '1', 'health': '2'},
    ),
    (
        'Spirit Hosts', 150, 'Infantry', False, True, 3,
        ['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'INFANTRY'],
        [],
        {'move': '8"', 'save': '4+', 'control': '1', 'health': '3'},
    ),
    (
        'Glaivewraith Stalkers', 110, 'Infantry', False, True, 4,
        ['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'INFANTRY'],
        [],
        {'move': '8"', 'save': '4+', 'control': '1', 'health': '1'},
    ),
    (
        'Mourngul', 220, 'Behemoth', False, False, 1,
        ['DEATH', 'NIGHTHAUNT', 'SUMMONABLE', 'MONSTER'],
        [],
        {'move': '10"', 'save': '4+', 'control': '5', 'health': '12'},
    ),
]

STORMCAST_BLURB = (
    "Forged in Azyr, the God-King Sigmar's heaven realm, the Stormcast Eternals are his immortal "
    "warriors — human souls chosen for their valour, reforged in the Celestine Vale into warriors "
    "clad in sigmarite armour and hurled across the Mortal Realms on bolts of holy lightning. "
    "They are the hammer of the God-King, his answer to the tyranny of Chaos that has plagued "
    "creation since the Age of Chaos. Organised into Stormhosts and subdivided into chambers, "
    "each Stormcast Eternal is warrior, scholar, and missionary alike — tasked not just to defeat "
    "the enemy but to reclaim civilisation for the peoples of the Mortal Realms."
)

SYLVANETH_BLURB = (
    "Children of the goddess Alarielle and the life-magic of the Mortal Realms, the Sylvaneth are "
    "a race of living wooden beings — graceful yet terrible, ancient yet ever-renewing. Dryads, "
    "Treelords and Kurnoth Hunters emerge from the sacred Wyldwoods to defend the realmroots and "
    "punish those who defile the natural order. Each Sylvaneth carries a soul-pod singing with "
    "memories of past lives, and their groves are places of immense spiritual power. When roused "
    "to war, the forest itself rises: branches become blades, roots become snares, and the very "
    "land sings with Alarielle's fury."
)

NIGHTHAUNT_BLURB = (
    "The Nighthaunt are a spectral host of tormented dead, the Undying King Nagash's cruelest "
    "punishment made manifest — the souls of the wicked and the unrepentant reshaped into "
    "shrieking, chain-wrapped wraiths. Where they pass, warmth and hope drain away, replaced "
    "by the cold certainty of death. Chainrasps, Grimghast Reapers and Bladegheist Revenants "
    "glide across the battlefield with unnatural speed, while their lords — Spirit Torments and "
    "Guardians of Souls — drive the horde ever onward. No wall can stop them, no fortress contain "
    "them; the dead do not rest until Nagash wills it."
)


# ---------------------------------------------------------------------------
# Seed
# ---------------------------------------------------------------------------

def seed():
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import GameSystem, Faction, Unit
        return _do_seed(db, GameSystem, Faction, Unit)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db as _db
        from app.models.game import GameSystem as GS, Faction as F, Unit as U
        return _do_seed(_db, GS, F, U)


def _do_seed(db, GameSystem, Faction, Unit):
    gs = GameSystem.query.filter_by(code='aos4').first()
    if not gs:
        log.error('GameSystem aos4 not found — run seed_aos.py first')
        return {}

    def upsert_faction(code, name, alliance, blurb):
        f = Faction.query.filter_by(slug=code).first()
        if not f:
            f = Faction(
                game_system_id=gs.id,
                code=code,
                slug=code,
                name=name,
                grand_alliance=alliance,
                blurb=blurb,
            )
            db.session.add(f)
            db.session.flush()
            log.info('Created Faction %s', code)
        else:
            f.blurb = blurb
            log.info('Faction %s already exists — updated blurb', code)
        return f

    stormcast = upsert_faction('stormcast-eternals', 'Stormcast Eternals', 'Order', STORMCAST_BLURB)
    sylvaneth = upsert_faction('sylvaneth', 'Sylvaneth', 'Order', SYLVANETH_BLURB)
    nighthaunt = upsert_faction('nighthaunt', 'Nighthaunt', 'Death', NIGHTHAUNT_BLURB)

    total = 0

    def upsert_units(faction_obj, units_data, faction_wahapedia_slug):
        count = 0
        for row in units_data:
            name, pts, role, hero, reinforceable, model_count, keywords, companions, stats = row
            unit_slug = _slug(name)
            image_path = f'img/units/{faction_obj.slug}/{unit_slug}.jpg'
            wahapedia_url = f'{WAHAPEDIA_BASE}/{faction_wahapedia_slug}/{name.replace(" ", "-")}'

            u = Unit.query.filter_by(slug=unit_slug).first()
            if not u:
                u = Unit(
                    faction_id=faction_obj.id,
                    slug=unit_slug,
                    name=name,
                    points_cost=pts,
                    unit_role=role,
                    can_be_general=hero,
                    can_be_reinforced=reinforceable,
                    model_count=model_count,
                    stats_json=stats,
                    weapons_json=[],
                    abilities_json=[],
                    keywords_json=keywords,
                    companions_json=companions,
                    wahapedia_url=wahapedia_url,
                    image_path=image_path,
                )
                db.session.add(u)
                log.info('[+] %s', name)
            else:
                u.points_cost = pts
                u.unit_role = role
                u.model_count = model_count
                u.stats_json = stats
                u.keywords_json = keywords
                u.companions_json = companions
                u.image_path = image_path
                log.info('[~] %s (updated)', name)
            count += 1
        db.session.commit()
        return count

    sc = upsert_units(stormcast, STORMCAST_UNITS, 'stormcast-eternals')
    sy = upsert_units(sylvaneth, SYLVANETH_UNITS, 'sylvaneth')
    nh = upsert_units(nighthaunt, NIGHTHAUNT_UNITS, 'nighthaunt')
    total = sc + sy + nh

    log.info('Done. Stormcast=%d Sylvaneth=%d Nighthaunt=%d Total=%d', sc, sy, nh, total)
    return {'stormcast': sc, 'sylvaneth': sy, 'nighthaunt': nh, 'total': total}


if __name__ == '__main__':
    seed()
