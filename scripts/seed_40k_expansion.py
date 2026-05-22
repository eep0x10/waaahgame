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


def _stats(move, toughness, save, wounds, leadership, oc):
    return {'move': move, 'toughness': toughness, 'save': save,
            'wounds': wounds, 'leadership': leadership, 'oc': oc}


# ---------------------------------------------------------------------------
# Necrons
# ---------------------------------------------------------------------------

NECRONS_UNITS = [
    (
        'Necron Overlord', 85, 'Character', True, False, 1,
        ['NECRONS', 'INFANTRY', 'CHARACTER', 'NOBLE', 'OVERLORD'],
        _stats('5"', 5, '3+', 5, '6+', 1),
        [{'name': 'My Will Be Done', 'description': 'Friendly Necrons Core units within 6" can re-roll one Hit roll per turn.'},
         {'name': 'Living Metal', 'description': 'At the start of your turn, this model regains 1 lost wound.'}],
        'units/necrons/necron-overlord.jpg',
    ),
    (
        'Necron Lord', 70, 'Character', True, False, 1,
        ['NECRONS', 'INFANTRY', 'CHARACTER', 'NOBLE', 'LORD'],
        _stats('5"', 5, '3+', 4, '6+', 1),
        [{'name': 'Lord of the Undying Legions', 'description': 'At the end of any phase, roll a D6 for each friendly Necrons Infantry unit within 6"; on a 5+ return 1 slain model.'},
         {'name': 'Living Metal', 'description': 'At the start of your turn, this model regains 1 lost wound.'}],
        'units/necrons/necron-lord.jpg',
    ),
    (
        'Royal Warden', 75, 'Character', True, False, 1,
        ['NECRONS', 'INFANTRY', 'CHARACTER', 'NOBLE', 'ROYAL WARDEN'],
        _stats('5"', 5, '3+', 4, '6+', 1),
        [{'name': 'Adaptive Strategy', 'description': 'Once per battle, at the end of your opponent\'s Charge phase, one friendly Necrons Infantry unit within 6" can Fall Back as if it were your Movement phase.'}],
        'units/necrons/royal-warden.jpg',
    ),
    (
        'Cryptek', 70, 'Character', True, False, 1,
        ['NECRONS', 'INFANTRY', 'CHARACTER', 'CRYPTEK'],
        _stats('5"', 4, '4+', 4, '6+', 1),
        [{'name': 'Technomancer', 'description': 'Friendly Necrons units within 3" of this model ignore the penalty for using Quantum Shielding; add 1 to repair rolls.'},
         {'name': 'Living Metal', 'description': 'At the start of your turn, this model regains 1 lost wound.'}],
        'units/necrons/cryptek.jpg',
    ),
    (
        'Necron Warriors', 110, 'Battleline', False, True, 10,
        ['NECRONS', 'INFANTRY', 'BATTLELINE', 'CORE', 'WARRIOR'],
        _stats('5"', 4, '4+', 1, '6+', 2),
        [{'name': 'Reanimation Protocols', 'description': 'At the start of your turn, roll a D6 for each slain model in this unit; on a 5+ that model is returned to the unit.'}],
        'units/necrons/necron-warriors.jpg',
    ),
    (
        'Immortals', 80, 'Battleline', False, False, 5,
        ['NECRONS', 'INFANTRY', 'BATTLELINE', 'CORE', 'IMMORTAL'],
        _stats('5"', 4, '3+', 2, '6+', 2),
        [{'name': 'Reanimation Protocols', 'description': 'At the start of your turn, roll a D6 for each slain model; on a 5+ that model is returned.'},
         {'name': 'Objective Secured', 'description': 'While an enemy is contesting an objective this unit also contests, that enemy is not in range of that objective.'}],
        'units/necrons/immortals.jpg',
    ),
    (
        'Lychguard', 170, None, False, False, 5,
        ['NECRONS', 'INFANTRY', 'CORE', 'LYCHGUARD'],
        _stats('5"', 5, '3+', 3, '6+', 1),
        [{'name': 'Warscythe', 'description': 'Add 1 to wound rolls made with this unit\'s melee weapons.'},
         {'name': 'Dispersion Shield', 'description': 'This unit has a 4+ invulnerable save against ranged attacks.'}],
        'units/necrons/lychguard.jpg',
    ),
    (
        'Triarch Praetorians', 120, None, False, False, 5,
        ['NECRONS', 'INFANTRY', 'CORE', 'TRIARCH PRAETORIANS'],
        _stats('8"', 5, '3+', 2, '6+', 1),
        [{'name': 'Eternal Hunters', 'description': 'This unit does not suffer the penalty for moving and firing Assault weapons.'},
         {'name': 'Reanimation Protocols', 'description': 'At the start of your turn, roll a D6 for each slain model; on a 5+ return it.'}],
        'units/necrons/triarch-praetorians.jpg',
    ),
    (
        'Deathmarks', 85, None, False, False, 5,
        ['NECRONS', 'INFANTRY', 'CORE', 'DEATHMARK'],
        _stats('5"', 4, '3+', 1, '6+', 1),
        [{'name': 'Hunters from Hyperspace', 'description': 'When this unit arrives from Deep Strike, select one enemy unit — add 1 to wound rolls made by this unit against the selected unit for the rest of the battle.'}],
        'units/necrons/deathmarks.jpg',
    ),
    (
        'Doomstalker', 140, None, False, False, 1,
        ['NECRONS', 'VEHICLE', 'WALKER', 'DOOMSTALKER'],
        _stats('8"', 9, '3+', 9, '6+', 3),
        [{'name': 'Doomsday Blaster', 'description': 'Heavy D6+3, 48", S14, AP-4, D D3+3. On a Hit roll of 6+, it scores 2 hits.'},
         {'name': 'Living Metal', 'description': 'At the start of your turn, this model regains 1 lost wound.'}],
        'units/necrons/doomstalker.jpg',
    ),
    (
        'Canoptek Wraiths', 115, None, False, False, 3,
        ['NECRONS', 'BEAST', 'FLY', 'CANOPTEK', 'WRAITH'],
        _stats('10"', 5, '4+', 3, '6+', 1),
        [{'name': 'Wraith Form', 'description': 'This unit can move through other models and terrain features as if they were not there.'},
         {'name': 'Phase Shifter', 'description': 'This unit has a 4+ invulnerable save.'}],
        'units/necrons/canoptek-wraiths.jpg',
    ),
    (
        'Monolith', 340, None, False, False, 1,
        ['NECRONS', 'VEHICLE', 'TITANIC', 'CORE', 'MONOLITH'],
        _stats('6"', 12, '2+', 20, '6+', 8),
        [{'name': 'Eternity Gate', 'description': 'Once per battle round, one friendly Necrons Infantry unit can be teleported to within 3" of this model and more than 9" from enemy models.'},
         {'name': 'Living Metal', 'description': 'At the start of your turn, this model regains 1 lost wound.'},
         {'name': 'Ponderous', 'description': 'This model cannot Fall Back and cannot Advance.'}],
        'units/necrons/monolith.jpg',
    ),
]

# ---------------------------------------------------------------------------
# Aeldari
# ---------------------------------------------------------------------------

AELDARI_UNITS = [
    (
        'Farseer', 80, 'Character', True, False, 1,
        ['AELDARI', 'INFANTRY', 'CHARACTER', 'PSYKER', 'FARSEER'],
        _stats('7"', 3, '6+', 4, '6+', 1),
        [{'name': 'Guide', 'description': 'Target friendly Aeldari unit within 18" can re-roll all Hit rolls until the end of the next Shooting phase.'},
         {'name': 'Doom', 'description': 'Target enemy unit within 18" — until the end of your next turn, friendly Aeldari units can re-roll wound rolls against it.'}],
        'units/aeldari/farseer.jpg',
    ),
    (
        'Warlock', 55, 'Character', True, False, 1,
        ['AELDARI', 'INFANTRY', 'CHARACTER', 'PSYKER', 'WARLOCK'],
        _stats('7"', 3, '6+', 2, '6+', 1),
        [{'name': 'Conceal/Reveal', 'description': 'Conceal: Friendly Aeldari Infantry within 6" gain Light Cover. Reveal: Enemy units within 18" lose Light Cover bonuses until your next turn.'}],
        'units/aeldari/warlock.jpg',
    ),
    (
        'Autarch', 75, 'Character', True, False, 1,
        ['AELDARI', 'INFANTRY', 'CHARACTER', 'AUTARCH'],
        _stats('7"', 3, '5+', 4, '6+', 1),
        [{'name': 'Path of Command', 'description': 'Once per battle round, one friendly Aeldari unit within 6" can make a free Stratagem action that costs 1 CP without spending that CP.'}],
        'units/aeldari/autarch.jpg',
    ),
    (
        'Spiritseer', 70, 'Character', True, False, 1,
        ['AELDARI', 'INFANTRY', 'CHARACTER', 'PSYKER', 'SPIRITSEER'],
        _stats('7"', 3, '6+', 3, '6+', 1),
        [{'name': 'Spirit Mark', 'description': 'Friendly Wraithguard and Wraithblades within 12" of this model can re-roll Hit rolls of 1.'},
         {'name': 'Empower', 'description': 'Add 1 to the Strength of a friendly Aeldari Infantry unit within 12" until the end of the phase.'}],
        'units/aeldari/spiritseer.jpg',
    ),
    (
        'Guardian Defenders', 90, 'Battleline', False, True, 10,
        ['AELDARI', 'INFANTRY', 'BATTLELINE', 'CORE', 'GUARDIAN'],
        _stats('7"', 3, '5+', 1, '6+', 2),
        [{'name': 'Shuriken Catapult', 'description': 'Assault 2, 12", S4, AP-1. Each unmodified wound roll of 6 causes 1 mortal wound in addition to normal damage.'}],
        'units/aeldari/guardian-defenders.jpg',
    ),
    (
        'Dire Avengers', 85, 'Battleline', False, False, 5,
        ['AELDARI', 'INFANTRY', 'BATTLELINE', 'CORE', 'ASPECT WARRIOR', 'DIRE AVENGER'],
        _stats('7"', 3, '5+', 1, '6+', 2),
        [{'name': 'Battle Fortune', 'description': 'This unit has a 5+ invulnerable save.'},
         {'name': 'Avenger\'s Fury', 'description': 'Add 1 to the Attacks characteristic of this unit\'s Avenger Shuriken Catapults on any turn this unit did not move.'}],
        'units/aeldari/dire-avengers.jpg',
    ),
    (
        'Howling Banshees', 85, None, False, False, 5,
        ['AELDARI', 'INFANTRY', 'CORE', 'ASPECT WARRIOR', 'HOWLING BANSHEE'],
        _stats('8"', 3, '5+', 1, '6+', 1),
        [{'name': 'Banshee Mask', 'description': 'Enemy units cannot fire Overwatch against this unit and subtract 1 from their Hit rolls in the Fight phase while within 6".'}],
        'units/aeldari/howling-banshees.jpg',
    ),
    (
        'Striking Scorpions', 85, None, False, False, 5,
        ['AELDARI', 'INFANTRY', 'CORE', 'ASPECT WARRIOR', 'STRIKING SCORPION'],
        _stats('7"', 3, '5+', 1, '6+', 1),
        [{'name': 'Infiltrators', 'description': 'During deployment this unit may be set up anywhere on the battlefield more than 9" from the enemy deployment zone and enemy models.'},
         {'name': 'Mandiblasters', 'description': 'At the start of each Fight phase, this unit deals 1 mortal wound to each enemy unit within 1".'}],
        'units/aeldari/striking-scorpions.jpg',
    ),
    (
        'Fire Dragons', 120, None, False, False, 5,
        ['AELDARI', 'INFANTRY', 'CORE', 'ASPECT WARRIOR', 'FIRE DRAGON'],
        _stats('7"', 3, '5+', 1, '6+', 1),
        [{'name': 'Fusion Gun', 'description': 'Assault 1, 12", S8, AP-4, D D6. Melt: Within half range, each Hit roll scores a Critical Hit on 5+.'},
         {'name': 'Tank Hunters', 'description': 'Add 1 to wound rolls made by this unit against Vehicle and Monster units.'}],
        'units/aeldari/fire-dragons.jpg',
    ),
    (
        'Wraithlord', 120, None, False, False, 1,
        ['AELDARI', 'WALKER', 'VEHICLE', 'WRAITH CONSTRUCT', 'WRAITHLORD'],
        _stats('8"', 8, '3+', 10, '6+', 3),
        [{'name': 'Ghostglaive', 'description': 'Melee, S+4, AP-3, D D3+3.'},
         {'name': 'Ancient Dread', 'description': 'Enemy units subtract 1 from their Leadership within 6" of this model.'}],
        'units/aeldari/wraithlord.jpg',
    ),
    (
        'War Walkers', 75, None, False, False, 1,
        ['AELDARI', 'WALKER', 'VEHICLE', 'WAR WALKER'],
        _stats('8"', 6, '4+', 5, '6+', 2),
        [{'name': 'Scout', 'description': 'After deployment but before the first battle round, this unit can make a Normal Move of up to 7".'},
         {'name': 'Eldar Missile Launcher', 'description': 'Heavy 1, 48", S8, AP-2, D D6 (Krak) or S4, AP0, D1 Blast (Shuriken).'}],
        'units/aeldari/war-walkers.jpg',
    ),
    (
        'Wraithknight', 430, None, False, False, 1,
        ['AELDARI', 'TITANIC', 'VEHICLE', 'WALKER', 'WRAITH CONSTRUCT', 'WRAITHKNIGHT'],
        _stats('12"', 12, '3+', 22, '6+', 8),
        [{'name': 'Ghostglaive Strike', 'description': 'Melee, S18, AP-4, D6+6. On an unmodified wound roll of 6 the target suffers an additional D3 mortal wounds.'},
         {'name': 'Titanic Feet', 'description': 'This model can move over and through models and obstacles up to 4" high.'},
         {'name': 'Supreme Fortitude', 'description': 'This model has a 5+ invulnerable save.'}],
        'units/aeldari/wraithknight.jpg',
    ),
]

# ---------------------------------------------------------------------------
# Chaos Space Marines
# ---------------------------------------------------------------------------

CHAOS_SM_UNITS = [
    (
        'Chaos Lord', 80, 'Character', True, False, 1,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'CHARACTER', 'CHAOS LORD'],
        _stats('6"', 4, '3+', 5, '6+', 1),
        [{'name': 'Warlord of Chaos', 'description': 'Friendly Chaos Space Marines Core units within 6" can re-roll one Hit roll per turn.'},
         {'name': 'Aura of Dark Glory', 'description': 'This model has a 4+ invulnerable save.'}],
        'units/chaos-space-marines/chaos-lord.jpg',
    ),
    (
        'Master of Possession', 90, 'Character', True, False, 1,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'CHARACTER', 'PSYKER', 'MASTER OF POSSESSION'],
        _stats('6"', 4, '3+', 5, '6+', 1),
        [{'name': 'Malefic Ritual', 'description': 'At the end of your Movement phase, this model can attempt to summon one unit of Daemons to the battlefield.'},
         {'name': 'Empyric Overcharge', 'description': 'Add 1 to the Strength of friendly Possessed units within 6".'}],
        'units/chaos-space-marines/master-of-possession.jpg',
    ),
    (
        'Sorcerer in Terminator Armour', 95, 'Character', True, False, 1,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'CHARACTER', 'PSYKER', 'TERMINATOR', 'SORCERER'],
        _stats('5"', 5, '2+', 5, '6+', 1),
        [{'name': 'Warptime', 'description': 'Select a friendly Chaos Space Marines unit within 18" — that unit can make an additional Normal Move.'},
         {'name': 'Death Hex', 'description': 'Select an enemy unit within 24" — that unit has no invulnerable saves until your next Psychic phase.'}],
        'units/chaos-space-marines/sorcerer-in-terminator-armour.jpg',
    ),
    (
        'Dark Apostle', 70, 'Character', True, False, 1,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'CHARACTER', 'DARK APOSTLE'],
        _stats('6"', 4, '3+', 4, '6+', 1),
        [{'name': 'Dark Zealotry', 'description': 'Add 1 to Advance and charge rolls made for friendly Chaos Space Marines Infantry units within 6".'},
         {'name': 'Prayers to the Dark Gods', 'description': 'At the start of your Command phase, attempt to manifest one Prayer; on a 2+ the Prayer takes effect.'}],
        'units/chaos-space-marines/dark-apostle.jpg',
    ),
    (
        'Legionaries', 90, 'Battleline', False, True, 5,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'BATTLELINE', 'CORE', 'LEGIONARY'],
        _stats('6"', 4, '3+', 2, '6+', 2),
        [{'name': 'Objective Secured', 'description': 'While an enemy unit is contesting an objective this unit also contests, that enemy unit is not in range of that objective.'},
         {'name': 'Despoilers', 'description': 'Add 1 to the Attacks of this unit\'s melee weapons when targeting Infantry units.'}],
        'units/chaos-space-marines/legionaries.jpg',
    ),
    (
        'Chaos Cultists', 50, 'Battleline', False, True, 10,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'BATTLELINE', 'CHAOS CULTIST'],
        _stats('6"', 3, '6+', 1, '6+', 2),
        [{'name': 'Frenzied Charge', 'description': 'Add 1 to the Attacks characteristic of this unit in any turn it made a charge move.'}],
        'units/chaos-space-marines/chaos-cultists.jpg',
    ),
    (
        'Possessed', 170, None, False, False, 5,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'DAEMON', 'CORE', 'POSSESSED'],
        _stats('7"', 5, '3+', 3, '6+', 1),
        [{'name': 'Daemonic Mutations', 'description': 'At the start of each Fight phase, roll a D3; this unit gains +1 Attacks, +1 Strength, or a 4+ invulnerable save until the end of the phase (result determines which).'},
         {'name': 'Fell Hunger', 'description': 'Ignore Morale tests for this unit while it is within 3" of an enemy unit.'}],
        'units/chaos-space-marines/possessed.jpg',
    ),
    (
        'Chaos Terminators', 180, None, False, False, 5,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'TERMINATOR', 'CORE', 'CHAOS TERMINATOR'],
        _stats('5"', 5, '2+', 3, '6+', 1),
        [{'name': 'Teleport Strike', 'description': 'During deployment, this unit can be set up in the Warp rather than on the battlefield; at the end of any of your Movement phases set them up anywhere more than 9" from enemy units.'},
         {'name': 'Chaos Icons', 'description': 'Add 1 to this unit\'s Advance and charge rolls.'}],
        'units/chaos-space-marines/chaos-terminators.jpg',
    ),
    (
        'Chosen', 150, None, False, False, 5,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'CORE', 'CHOSEN'],
        _stats('6"', 4, '3+', 2, '6+', 1),
        [{'name': 'Veterans of the Long War', 'description': 'Add 1 to wound rolls made by this unit against Adeptus Astartes and Adeptus Mechanicus units.'},
         {'name': 'Cruel Tacticians', 'description': 'When a Chosen unit is set up, all enemy units within 18" must take a Morale test.'}],
        'units/chaos-space-marines/chosen.jpg',
    ),
    (
        'Raptors', 85, None, False, False, 5,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'INFANTRY', 'JUMP PACK', 'CORE', 'RAPTOR'],
        _stats('12"', 4, '3+', 2, '6+', 1),
        [{'name': 'Death from Above', 'description': 'During deployment, this unit can be set up high in the skies. At the end of any of your Movement phases set them up anywhere more than 9" from enemy units.'},
         {'name': 'Headhunters', 'description': 'Add 1 to wound rolls made by this unit when targeting Character units.'}],
        'units/chaos-space-marines/raptors.jpg',
    ),
    (
        'Helbrute', 140, None, False, False, 1,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'VEHICLE', 'WALKER', 'DAEMON', 'HELBRUTE'],
        _stats('8"', 8, '3+', 9, '6+', 3),
        [{'name': 'Crazed', 'description': 'Each time this model loses a wound, roll a D6; on a 6 this model immediately shoots as if it were your Shooting phase or makes a charge move.'},
         {'name': 'Explodes', 'description': 'When this model is destroyed roll one D6: on a 6 it explodes and each unit within 6" suffers D3 mortal wounds.'}],
        'units/chaos-space-marines/helbrute.jpg',
    ),
    (
        'Forgefiend', 180, None, False, False, 1,
        ['CHAOS', 'CHAOS_SPACE_MARINES', 'VEHICLE', 'DAEMON', 'HELFORGED', 'FORGEFIEND'],
        _stats('8"', 8, '3+', 12, '6+', 3),
        [{'name': 'Ectoplasma Cannons', 'description': 'Heavy 2, 24", S7, AP-1, D D3. On a Hit roll of 6+ it scores 2 hits.'},
         {'name': 'Daemonic Regeneration', 'description': 'At the start of your turn this model regains D3 lost wounds.'}],
        'units/chaos-space-marines/forgefiend.jpg',
    ),
]

NECRONS_BLURB = (
    "Guerreiros imortais de metal frio e energia gauss crepitante, os Necrons dormitaram em seus mundos-tumba "
    "por sessenta milhões de anos. Agora eles acordam para reconquistar uma galáxia que outrora governaram "
    "em fogo e silêncio. Liderados por Overlords e Phaerons de vontade terrível, suas legiões marcham sem "
    "medo ou misericórdia — cada guerreiro caído se reanima para erguer-se novamente. Contra os Necrons "
    "não há vitória final, apenas o avanço contínuo de um império que se recusa a morrer."
)

AELDARI_BLURB = (
    "Antigos além de qualquer contagem, os Aeldari foram outrora mestres de um império que abrangia a galáxia, "
    "cuja queda rasgou a realidade e gerou um deus do caos. Agora se agarram à sobrevivência a bordo de "
    "vastos craftworldes, suas vidas seguindo rígidos Caminhos de especialização para conter a paixão que "
    "destruiu seus semelhantes. Em batalha, seus guerreiros são incomparáveis — rápidos, precisos e guiados "
    "por Farseers que lêem os fios do destino. Cada guerra é planejada séculos de antecedência, cada "
    "sacrifício calculado para preservar a espécie."
)

CHAOS_SM_BLURB = (
    "Os Chaos Space Marines são o espelho sombrio dos Adeptus Astartes — legiões traidoras que se voltaram "
    "contra o Imperador dez mil anos atrás e agora servem às Ruinous Powers em guerra eterna. Envoltos em "
    "armadura corrompida distorcida por influência daemônica, trazem ódio e crueldade a todo campo de batalha. "
    "Onde os filhos do Império lutam com disciplina e honra, os Heretic Astartes lutam com "
    "raiva amarga e a promessa de sombrias recompensas dos deuses que servem."
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

    def upsert_faction(code, name, blurb):
        f = Faction.query.filter_by(slug=code).first()
        if not f:
            f = Faction(
                game_system_id=gs.id,
                code=code,
                slug=code,
                name=name,
                grand_alliance=None,
                blurb=blurb,
            )
            db.session.add(f)
            db.session.flush()
            log.info('Created Faction %s', code)
        else:
            f.blurb = blurb
            log.info('Faction %s already exists', code)
        return f

    necrons = upsert_faction('necrons', 'Necrons', NECRONS_BLURB)
    aeldari = upsert_faction('aeldari', 'Aeldari', AELDARI_BLURB)
    csm = upsert_faction('chaos-space-marines', 'Chaos Space Marines', CHAOS_SM_BLURB)

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

    log.info('=== Seeding Necrons (%d units) ===', len(NECRONS_UNITS))
    ne_new, ne_upd = upsert_units(necrons, NECRONS_UNITS)

    log.info('=== Seeding Aeldari (%d units) ===', len(AELDARI_UNITS))
    ae_new, ae_upd = upsert_units(aeldari, AELDARI_UNITS)

    log.info('=== Seeding Chaos Space Marines (%d units) ===', len(CHAOS_SM_UNITS))
    csm_new, csm_upd = upsert_units(csm, CHAOS_SM_UNITS)

    log.info('Done. Necrons: %d new / %d updated. Aeldari: %d new / %d updated. CSM: %d new / %d updated.',
             ne_new, ne_upd, ae_new, ae_upd, csm_new, csm_upd)

    return {
        'necrons_new': ne_new, 'necrons_updated': ne_upd,
        'aeldari_new': ae_new, 'aeldari_updated': ae_upd,
        'csm_new': csm_new, 'csm_updated': csm_upd,
    }


if __name__ == '__main__':
    seed()
