"""
Seed Warhammer 40,000 10th ed data: GameSystem, Space Marines, Tyranids factions + units.

Idempotent — upserts by slug.
Stats schema uses 40k fields: move, toughness, save, wounds, leadership, oc
"""

import sys
import os
import re
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)


def _slug(name):
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


# ---------------------------------------------------------------------------
# Unit definitions
# (name, pts, role, can_be_general, can_be_reinforced, model_count, keywords, stats, abilities)
# ---------------------------------------------------------------------------

def _sm_stats(move, toughness, save, wounds, leadership, oc):
    return {'move': move, 'toughness': toughness, 'save': save,
            'wounds': wounds, 'leadership': leadership, 'oc': oc}


def _ty_stats(move, toughness, save, wounds, leadership, oc):
    return {'move': move, 'toughness': toughness, 'save': save,
            'wounds': wounds, 'leadership': leadership, 'oc': oc}


SPACE_MARINES_UNITS = [
    # (name, pts, role, can_general, can_reinforce, count, keywords_list, stats_dict, abilities_list, image_path)
    (
        'Captain in Power Armour', 80, 'Character', True, False, 1,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'CHARACTER', 'CAPTAIN'],
        _sm_stats('6"', 4, '3+', 4, '6+', 1),
        [{'name': 'Rites of Battle', 'description': 'Friendly Adeptus Astartes units within 6" can re-roll one Hit roll per turn.'}],
        'units/space-marines/captain-in-power-armour.jpg',
    ),
    (
        'Lieutenant', 65, 'Character', True, False, 1,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'CHARACTER', 'LIEUTENANT'],
        _sm_stats('6"', 4, '3+', 4, '6+', 1),
        [{'name': 'Tactical Precision', 'description': 'Friendly Adeptus Astartes Core units within 6" can re-roll Wound rolls of 1.'}],
        'units/space-marines/lieutenant.jpg',
    ),
    (
        'Apothecary', 50, 'Character', True, False, 1,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'CHARACTER', 'APOTHECARY'],
        _sm_stats('6"', 4, '3+', 4, '6+', 1),
        [{'name': 'Narthecium', 'description': 'Once per battle, at the end of any phase, you can return D3 slain models to one friendly Adeptus Astartes Infantry unit within 3".'}],
        'units/space-marines/apothecary.jpg',
    ),
    (
        'Tactical Squad', 75, 'Battleline', False, True, 10,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'BATTLELINE', 'TACTICAL SQUAD', 'CORE'],
        _sm_stats('6"', 4, '3+', 1, '6+', 2),
        [{'name': 'Objective Secured', 'description': 'While an enemy unit is contesting an objective that this unit is also contesting, that enemy unit is not in range of that objective.'}],
        'units/space-marines/tactical-squad.jpg',
    ),
    (
        'Intercessor Squad', 80, 'Battleline', False, True, 5,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'BATTLELINE', 'INTERCESSORS', 'CORE'],
        _sm_stats('6"', 4, '3+', 2, '6+', 2),
        [{'name': 'Objective Secured', 'description': 'While an enemy unit is contesting an objective that this unit is also contesting, that enemy unit is not in range of that objective.'}],
        'units/space-marines/intercessor-squad.jpg',
    ),
    (
        'Assault Intercessors', 75, 'Battleline', False, True, 5,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'BATTLELINE', 'ASSAULT INTERCESSORS', 'CORE'],
        _sm_stats('6"', 4, '3+', 2, '6+', 2),
        [{'name': 'Objective Secured', 'description': 'While an enemy unit is contesting an objective that this unit is also contesting, that enemy unit is not in range of that objective.'}],
        'units/space-marines/assault-intercessors.jpg',
    ),
    (
        'Hellblasters', 130, None, False, False, 5,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'HELLBLASTERS', 'CORE'],
        _sm_stats('6"', 4, '3+', 2, '6+', 2),
        [{'name': 'Plasma Incinerator', 'description': 'Supercharge: Each unmodified Hit roll of 1 slays the bearer; add 2 to the Damage characteristic.'}],
        'units/space-marines/hellblasters.jpg',
    ),
    (
        'Eradicators', 95, None, False, False, 3,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'ERADICATORS', 'CORE'],
        _sm_stats('6"', 4, '3+', 3, '6+', 1),
        [{'name': 'Melta Rifles', 'description': 'Melta: When this weapon targets a unit within half range, each Hit roll scores a Critical Hit on unmodified rolls of 5+.'}],
        'units/space-marines/eradicators.jpg',
    ),
    (
        'Outrider Squad', 90, None, False, False, 3,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'MOUNTED', 'OUTRIDERS', 'CORE'],
        _sm_stats('14"', 5, '3+', 3, '6+', 2),
        [{'name': 'Turbo-boost', 'description': 'When this unit Advances, add 6" to its Move characteristic for that Movement phase instead of rolling a dice.'}],
        'units/space-marines/outrider-squad.jpg',
    ),
    (
        'Terminator Squad', 170, None, False, False, 5,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'INFANTRY', 'TERMINATORS', 'CORE'],
        _sm_stats('5"', 5, '2+', 3, '6+', 1),
        [{'name': 'Teleport Strike', 'description': 'During deployment, this unit can be set up in teleportarium instead of on the battlefield.'}],
        'units/space-marines/terminator-squad.jpg',
    ),
    (
        'Redemptor Dreadnought', 210, 'Vehicle', False, False, 1,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'VEHICLE', 'WALKER', 'DREADNOUGHT'],
        _sm_stats('8"', 9, '2+', 12, '6+', 3),
        [{'name': 'Explodes', 'description': 'When this model is destroyed, roll one D6: on a 6 it explodes, and each unit within 9" suffers D3 mortal wounds.'}],
        'units/space-marines/redemptor-dreadnought.jpg',
    ),
    (
        'Repulsor', 180, 'Vehicle', False, False, 1,
        ['IMPERIUM', 'ADEPTUS ASTARTES', 'VEHICLE', 'TRANSPORT', 'REPULSOR'],
        _sm_stats('10"', 9, '3+', 16, '6+', 3),
        [{'name': 'Hover Tank', 'description': 'This model does not suffer the penalty for moving and firing Heavy weapons.'},
         {'name': 'Explodes', 'description': 'When this model is destroyed, roll one D6: on a 6 it explodes, and each unit within 9" suffers D3 mortal wounds.'}],
        'units/space-marines/repulsor.jpg',
    ),
]

TYRANIDS_UNITS = [
    (
        'Hive Tyrant', 195, 'Character', True, False, 1,
        ['TYRANIDS', 'MONSTER', 'CHARACTER', 'SYNAPSE', 'PSYKER', 'HIVE TYRANT'],
        _ty_stats('10"', 9, '2+', 10, '4+', 4),
        [{'name': 'The Horror', 'description': 'Enemy units within 12" of this model must subtract 1 from their Leadership characteristic.'},
         {'name': 'Synaptic Nexus', 'description': 'Friendly Tyranids units within 12" of this model can use this model\'s Leadership characteristic.'}],
        'units/tyranids/hive-tyrant.jpg',
    ),
    (
        'Neurotyrant', 105, 'Character', True, False, 1,
        ['TYRANIDS', 'MONSTER', 'CHARACTER', 'SYNAPSE', 'PSYKER', 'NEUROTYRANT'],
        _ty_stats('8"', 8, '4+', 8, '4+', 3),
        [{'name': 'Psychic Terror', 'description': 'Subtract 1 from the Leadership of enemy units within 12".'},
         {'name': 'Neuroparasite Infestation', 'description': 'Enemy units that fail a Morale test within 12" suffer D3 mortal wounds.'}],
        'units/tyranids/neurotyrant.jpg',
    ),
    (
        'Broodlord', 80, 'Character', True, False, 1,
        ['TYRANIDS', 'INFANTRY', 'CHARACTER', 'SYNAPSE', 'PSYKER', 'BROODLORD'],
        _ty_stats('8"', 6, '4+', 5, '4+', 1),
        [{'name': 'Hypnotic Gaze', 'description': 'At the start of the Fight phase, select one enemy model within 3": until the end of the phase, subtract 2 from that model\'s Attacks.'}],
        'units/tyranids/broodlord.jpg',
    ),
    (
        'Termagants', 60, 'Battleline', False, True, 10,
        ['TYRANIDS', 'INFANTRY', 'BATTLELINE', 'TERMAGANTS'],
        _ty_stats('6"', 3, '5+', 1, '4+', 2),
        [{'name': 'Instinctive Behaviour', 'description': 'Unless within 24" of a friendly Synapse unit, this unit cannot Fall Back and must charge if able.'}],
        'units/tyranids/termagants.jpg',
    ),
    (
        'Hormagaunts', 65, 'Battleline', False, True, 10,
        ['TYRANIDS', 'INFANTRY', 'BATTLELINE', 'HORMAGAUNTS'],
        _ty_stats('8"', 3, '5+', 1, '4+', 1),
        [{'name': 'Bounding Leap', 'description': 'Add 2" to this unit\'s Move characteristic when making a charge move.'}],
        'units/tyranids/hormagaunts.jpg',
    ),
    (
        'Tyranid Warriors with Melee', 85, 'Battleline', False, True, 3,
        ['TYRANIDS', 'INFANTRY', 'BATTLELINE', 'SYNAPSE', 'TYRANID WARRIORS'],
        _ty_stats('6"', 5, '4+', 3, '4+', 1),
        [{'name': 'Synapse', 'description': 'Friendly Tyranids units within 12" of this unit are not subject to Instinctive Behaviour.'}],
        'units/tyranids/tyranid-warriors-with-melee.jpg',
    ),
    (
        'Genestealers', 75, None, False, False, 5,
        ['TYRANIDS', 'INFANTRY', 'GENESTEALERS'],
        _ty_stats('8"', 4, '5+', 1, '4+', 1),
        [{'name': 'Lightning Reflexes', 'description': 'This unit has a 6+ invulnerable save.'},
         {'name': 'Blinding Venom', 'description': 'Enemy units cannot fire Overwatch at this unit.'}],
        'units/tyranids/genestealers.jpg',
    ),
    (
        'Zoanthropes', 110, None, False, False, 3,
        ['TYRANIDS', 'INFANTRY', 'PSYKER', 'SYNAPSE', 'ZOANTHROPES'],
        _ty_stats('5"', 4, '5+', 3, '4+', 1),
        [{'name': 'Warp Blast', 'description': 'Assault 1, 18", S10, AP-4, D D6. If this weapon misses, roll a dice; on a 1 the bearer suffers 1 mortal wound.'},
         {'name': 'Synapse', 'description': 'Friendly Tyranids units within 12" of this unit are not subject to Instinctive Behaviour.'}],
        'units/tyranids/zoanthropes.jpg',
    ),
    (
        'Carnifex', 105, None, False, False, 1,
        ['TYRANIDS', 'MONSTER', 'CARNIFEX'],
        _ty_stats('8"', 9, '3+', 8, '4+', 3),
        [{'name': 'Living Battering Ram', 'description': 'Add 1 to the Attack characteristic of this model when it makes a charge move in the Charge phase.'}],
        'units/tyranids/carnifex.jpg',
    ),
    (
        'Trygon', 175, None, False, False, 1,
        ['TYRANIDS', 'MONSTER', 'TRYGON'],
        _ty_stats('10"', 9, '3+', 14, '4+', 4),
        [{'name': 'Subterranean Assault', 'description': 'During deployment, set up this model underground instead of on the battlefield.'}],
        'units/tyranids/trygon.jpg',
    ),
    (
        'Lictor', 60, None, False, False, 1,
        ['TYRANIDS', 'INFANTRY', 'LICTOR'],
        _ty_stats('9"', 5, '4+', 4, '4+', 1),
        [{'name': 'Pheromone Trail', 'description': 'Once per battle, when reinforcements arrive, you may place one unit from Reserves within 6" of this model.'},
         {'name': 'Chameleonic Skin', 'description': 'This model may not be targeted by Overwatch.'}],
        'units/tyranids/lictor.jpg',
    ),
    (
        'Tyrannofex', 215, None, False, False, 1,
        ['TYRANIDS', 'MONSTER', 'TYRANNOFEX'],
        _ty_stats('8"', 10, '2+', 16, '4+', 5),
        [{'name': 'Acid Spray', 'description': 'Heavy D6, 24", S6, AP-1, D1. Does not require line of sight.'}],
        'units/tyranids/tyrannofex.jpg',
    ),
]

SPACE_MARINES_BLURB = (
    "Os Adeptus Astartes — Space Marines — são os maiores guerreiros da humanidade, soldados trans-humanos "
    "criados a partir do gene-seed dos Primarchs. Envolvidos em armadura de ceramite e empunhando as melhores "
    "armas que o Império pode produzir, eles são a última linha de defesa contra os horrores sem fim "
    "que ameaçam consumir a galáxia. Cada Capítulo é uma irmandade à parte, preservando doutrinas de batalha "
    "únicas e relíquias através de milênios de guerra contra xenos, hereges e o daemonico. "
    "Quando um Capítulo de Space Marines vai à guerra, mundos tremem."
)

TYRANIDS_BLURB = (
    "De além da orla da galáxia os Tyranids vêm — uma vasta e voraz mente-colmeia de predadores "
    "bio-engenheirados que consome tudo que está vivo em seu caminho. Cada organismo Tyranid é uma arma "
    "perfeitamente adaptada para o massacre, moldada pela Mente-Colmeia através de eons para superar "
    "qualquer obstáculo, romper qualquer defesa e reduzir um mundo à rocha nua. As Criaturas Sinapsia "
    "formam uma rede psíquica que coordena o enxame com precisão aterrorizante, enquanto Carnifexes "
    "gigantescos e Harpias voadoras lideram o avanço. Diante do Grande Devorador, nenhum mundo está seguro."
)


def seed():
    from app.extensions import db
    from app.models.game import GameSystem, Faction, Unit

    try:
        from flask import current_app
        current_app._get_current_object()
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
    # --- GameSystem ---
    gs = GameSystem.query.filter_by(code='w40k10').first()
    if not gs:
        gs = GameSystem(
            code='w40k10',
            name='Warhammer 40,000',
            edition='10th Edition (2023)',
            ruleset_label='Munitorum Field Manual 2025',
        )
        db.session.add(gs)
        db.session.flush()
        log.info('Created GameSystem w40k10')
    else:
        log.info('GameSystem w40k10 already exists')

    # --- Factions ---
    def upsert_faction(code, name, blurb, grand_alliance=None):
        f = Faction.query.filter_by(slug=code).first()
        if not f:
            f = Faction(
                game_system_id=gs.id,
                code=code,
                slug=code,
                name=name,
                grand_alliance=grand_alliance,
                blurb=blurb,
            )
            db.session.add(f)
            db.session.flush()
            log.info('Created Faction %s', code)
        else:
            f.blurb = blurb
            log.info('Faction %s already exists — updated blurb', code)
        return f

    sm = upsert_faction('space-marines', 'Adeptus Astartes', SPACE_MARINES_BLURB)
    ty = upsert_faction('tyranids', 'Tyranids', TYRANIDS_BLURB)

    # --- Units ---
    def upsert_units(faction_obj, units_list):
        count_new = 0
        count_upd = 0
        for row in units_list:
            name, pts, role, can_general, can_reinforce, model_count, kws, stats, abilities, img_path = row
            unit_slug = _slug(name)

            u = Unit.query.filter_by(slug=unit_slug).first()
            if not u:
                u = Unit(
                    faction_id=faction_obj.id,
                    slug=unit_slug,
                    name=name,
                    points_cost=pts,
                    unit_role=role,
                    can_be_general=can_general,
                    can_be_reinforced=can_reinforce,
                    model_count=model_count,
                    stats_json=stats,
                    weapons_json=[],
                    abilities_json=abilities,
                    keywords_json=kws,
                    companions_json=[],
                    image_path=img_path,
                )
                db.session.add(u)
                log.info('[+] %s', name)
                count_new += 1
            else:
                u.points_cost = pts
                u.unit_role = role
                u.can_be_general = can_general
                u.can_be_reinforced = can_reinforce
                u.model_count = model_count
                # Do NOT overwrite scraped JSON fields on existing rows
                # u.stats_json / u.abilities_json / u.keywords_json intentionally omitted
                if not u.image_path:
                    u.image_path = img_path
                log.info('[~] %s updated', name)
                count_upd += 1

        db.session.commit()
        return count_new, count_upd

    log.info('=== Seeding Space Marines (%d units) ===', len(SPACE_MARINES_UNITS))
    sm_new, sm_upd = upsert_units(sm, SPACE_MARINES_UNITS)

    log.info('=== Seeding Tyranids (%d units) ===', len(TYRANIDS_UNITS))
    ty_new, ty_upd = upsert_units(ty, TYRANIDS_UNITS)

    log.info('Done. Space Marines: %d new / %d updated. Tyranids: %d new / %d updated.',
             sm_new, sm_upd, ty_new, ty_upd)

    return {
        'space_marines_new': sm_new, 'space_marines_updated': sm_upd,
        'tyranids_new': ty_new, 'tyranids_updated': ty_upd,
    }


if __name__ == '__main__':
    seed()
