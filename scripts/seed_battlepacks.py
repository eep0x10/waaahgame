"""Seed Battlepack scenarios. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

BATTLEPACKS_DATA = [
    # AoS Vanguard
    {
        'system_code': 'aos4',
        'slug': 'aos-vanguard-first-blood',
        'name': 'First Blood',
        'format': 'vanguard',
        'summary': 'A swift engagement where both warbands clash in the open field. The first to seize ground claims the day.',
        'primary_objective': 'Score 2 VP at the end of each battle round for each objective marker you control. The player who controls the most objectives at the end of round 5 scores an additional 5 VP.',
        'secondary_objectives': [
            'Slay the Warlord: Score 3 VP if the enemy general is destroyed.',
            'First Strike: Score 2 VP if you destroy an enemy unit in the first battle round.',
            'Hold the Flank: Score 1 VP at the end of each round you control the objective in your opponent\'s deployment zone.',
        ],
        'deployment_text': 'Place objectives at the centre and on the left and right flanks, 9" from the centreline. Each player deploys within 12" of their table edge.',
        'special_rules_text': 'Both players roll-off; the winner chooses which player deploys and takes the first turn. Triumph rolls apply as per the Core Rules.',
    },
    {
        'system_code': 'aos4',
        'slug': 'aos-vanguard-the-vice',
        'name': 'The Vice',
        'format': 'vanguard',
        'summary': 'Two forces close from opposite sides, each trying to encircle the other. Mobility and aggression decide this battle.',
        'primary_objective': 'Score 3 VP at the end of each battle round for each objective you control that is within your opponent\'s territory. Score 1 VP for each objective in your own territory.',
        'secondary_objectives': [
            'Death or Glory: Score 3 VP if you win a combat against an enemy unit with more than 10 models.',
            'Encircle: Score 2 VP if you have at least one unit in the enemy deployment zone at the end of round 3.',
            'Deny Ground: Score 1 VP at the end of each round the enemy controls no objectives in your territory.',
        ],
        'deployment_text': 'Objectives are placed in a diagonal pattern across the board. Players deploy in opposite corners within a 12" triangle.',
        'special_rules_text': 'The Pincer rule: Units that begin a charge action within 3" of a friendly unit gain +1 to their charge roll.',
    },
    {
        'system_code': 'aos4',
        'slug': 'aos-vanguard-hold-the-center',
        'name': 'Hold the Center',
        'format': 'vanguard',
        'summary': 'A single central relic draws both forces into a grinding melee. Neither side can afford to yield the middle ground.',
        'primary_objective': 'Place one objective at the exact centre of the battlefield. Score 4 VP at the end of each battle round you control it. Score 2 VP at the end of each round you contest it.',
        'secondary_objectives': [
            'Defender of the Realm: Score 3 VP if you control the centre objective for three consecutive rounds.',
            'Blunt the Assault: Score 2 VP if you destroy more enemy units than you lose in a single round.',
            'Sacred Ground: Score 1 VP each round no enemy model is within 6" of the centre objective.',
        ],
        'deployment_text': 'Players deploy on opposite long table edges within 6". A single objective is placed at the centre of the board.',
        'special_rules_text': 'The central objective is contested if both players have a unit within 3" of it at the end of a round; neither player scores primary VP in that case.',
    },
    # AoS Battlehost
    {
        'system_code': 'aos4',
        'slug': 'aos-battlehost-battlelines-drawn',
        'name': 'Battlelines Drawn',
        'format': 'battlehost',
        'summary': 'Two fully-mustered hosts face each other across a wide front. Attrition and tactical mastery determine the victor.',
        'primary_objective': 'Five objectives are placed across the board. Score 2 VP per objective controlled at the end of each round. Score an additional 3 VP if you control three or more.',
        'secondary_objectives': [
            'Annihilation: Score 1 VP for each enemy unit you destroy, to a maximum of 6 VP.',
            'Break the Line: Score 4 VP if you have a unit in the enemy deployment zone at the end of round 4 or 5.',
            'Rally the Standard: Score 2 VP if a unit with the Leader keyword holds an objective for two consecutive rounds.',
        ],
        'deployment_text': 'Players deploy in their respective halves within 12" of their table edge. Objectives are placed at the centre and 12" in from each short edge at the midline, plus one in each deployment zone.',
        'special_rules_text': 'Grand Tactics apply. Each player selects one Grand Tactic at the start of the game from those available to their faction.',
    },
    {
        'system_code': 'aos4',
        'slug': 'aos-battlehost-tooth-and-nail',
        'name': 'Tooth and Nail',
        'format': 'battlehost',
        'summary': 'A savage close-range brawl where no quarter is given. Brute force and determination carry the day.',
        'primary_objective': 'Score 3 VP at the end of each round for each objective you control. Objectives can only be captured by units that have fought in combat this round.',
        'secondary_objectives': [
            'Savage Momentum: Score 3 VP if you charge and destroy an enemy unit in the same round.',
            'No Retreat: Score 2 VP each round you have more models in the enemy half than the opponent.',
            'Butcher\'s Count: Score 1 VP for every 5 wounds you inflict, to a maximum of 5 VP total.',
        ],
        'deployment_text': 'The board is divided into three bands. Players deploy within 6" of their table edge; all objectives are within 6" of the centre band.',
        'special_rules_text': 'All charges in this scenario gain the Savage keyword. Units that successfully charge add 1 to attack rolls until the end of that combat phase.',
    },
    # 40k Strike Force
    {
        'system_code': 'w40k10',
        'slug': '40k-strike-force-take-and-hold',
        'name': 'Take and Hold',
        'format': 'strike_force',
        'summary': 'Both forces race to seize and hold key strategic locations. The side that controls the most ground at battle end claims supremacy.',
        'primary_objective': 'Score 4 VP at the end of your Command phase for each objective marker you control, plus 5 VP at the end of the battle for each objective you control.',
        'secondary_objectives': [
            'Engage on All Fronts: Score 3 VP at the end of each round you have units in at least three different table quarters.',
            'Retrieve Battlefield Data: Score 4 VP each time one of your units performs this action at an objective you control.',
            'Storm Hostile Objective: Score 3 VP the first time you seize an objective that was previously under enemy control.',
        ],
        'deployment_text': 'Standard deployment as per the Strike Force rules. Four objectives placed at the midline at intervals, plus one in each deployment zone.',
        'special_rules_text': 'Tactical Reserves: Up to half your army may be held in Strategic Reserves. Units arriving from reserve may not score objectives the turn they arrive.',
    },
    {
        'system_code': 'w40k10',
        'slug': '40k-strike-force-scorched-earth',
        'name': 'Scorched Earth',
        'format': 'strike_force',
        'summary': 'Rather than seize objectives intact, each side seeks to deny them to the enemy through destruction. A pyrrhic struggle of attrition.',
        'primary_objective': 'Score 5 VP at the end of the battle for each objective you control. Score 3 VP each time you destroy an objective in your opponent\'s half.',
        'secondary_objectives': [
            'Demolitions Expert: Score 4 VP the first time you destroy two or more objectives in a single round.',
            'Last Stand: Score 3 VP if at least one of your units survives in the enemy deployment zone at the end of round 5.',
            'Blood and Fire: Score 2 VP each round you destroy at least one enemy unit.',
        ],
        'deployment_text': 'Diagonal deployment; players set up in opposite table corners within 12" triangles. Objectives placed along the centreline and in mid-field.',
        'special_rules_text': 'Objectives may be destroyed by a unit in base contact by spending 1 CP and taking a Demolish action. Destroyed objectives are removed.',
    },
    {
        'system_code': 'w40k10',
        'slug': '40k-strike-force-tipping-point',
        'name': 'Tipping Point',
        'format': 'strike_force',
        'summary': 'A battle of momentum. Seize key objectives to shift the balance, then hold them long enough to claim victory.',
        'primary_objective': 'Score 3 VP at the end of your Command phase for each objective. Score a bonus 3 VP if you control more objectives than your opponent.',
        'secondary_objectives': [
            'Surgical Strike: Score 4 VP the first time you destroy an enemy Character unit.',
            'Domination: Score 3 VP at the end of each round you control all objectives in your deployment zone and at least one enemy-zone objective.',
            'Ceaseless Advance: Score 2 VP for each round a selected unit ends the Movement phase further from your deployment edge than the previous round.',
        ],
        'deployment_text': 'Standard long-edge deployment within 12". Five objectives: one centre, two midfield flanks, one in each deployment zone.',
        'special_rules_text': 'Tipping Point rule: any objective held by the same player for three consecutive rounds becomes a Fortified Point worth double VP until the game ends.',
    },
    # 40k Combat Patrol
    {
        'system_code': 'w40k10',
        'slug': '40k-combat-patrol-clash',
        'name': 'Patrol Clash',
        'format': 'combat_patrol',
        'summary': 'A fast-moving skirmish between light forces. Speed and cunning matter more than raw firepower.',
        'primary_objective': 'Score 3 VP at the end of each round for each objective you control. Score 2 VP if you control more than your opponent.',
        'secondary_objectives': [
            'Recon: Score 3 VP if a unit ends its Move action within the enemy deployment zone.',
            'Eliminate the Threat: Score 3 VP the first time you destroy an enemy unit of 3 or more models.',
            'Secure the Area: Score 2 VP each round you control the central objective.',
        ],
        'deployment_text': 'Short-edge deployment within 9" of the player\'s table edge. Three objectives: one central, one in each player\'s half at the midline.',
        'special_rules_text': 'Patrol Speed: All infantry units gain +1" Move for the duration of the battle. Combat Patrol datasheets apply.',
    },
]


def _do_seed(db, GameSystem, Battlepack):
    created = 0
    for data in BATTLEPACKS_DATA:
        existing = Battlepack.query.filter_by(slug=data['slug']).first()
        if existing:
            continue
        gs = GameSystem.query.filter_by(code=data['system_code']).first()
        if not gs:
            continue
        bp = Battlepack(
            system_id=gs.id,
            slug=data['slug'],
            name=data['name'],
            format=data['format'],
            summary=data['summary'],
            primary_objective=data['primary_objective'],
            secondary_objectives_json=data['secondary_objectives'],
            deployment_text=data['deployment_text'],
            special_rules_text=data['special_rules_text'],
        )
        db.session.add(bp)
        created += 1
    db.session.commit()
    return created


if __name__ == '__main__':
    from app import create_app
    from app.extensions import db
    from app.models.game import GameSystem
    from app.models.battlepack import Battlepack

    app = create_app('dev')
    with app.app_context():
        n = _do_seed(db, GameSystem, Battlepack)
        print(f'Seeded {n} battlepacks.')
