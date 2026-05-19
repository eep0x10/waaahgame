"""Seed starter army templates. Idempotent."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEMPLATES_DATA = [
    {
        'faction_slug': 'skaven',
        'system_code': 'aos4',
        'slug': 'skaven-vanguard-starter',
        'name': 'Skaven Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'A gnawing tide of Skaven infantry led by a cunning Warlock Engineer. Fast, numerous, and unpredictable.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'warlock-engineer',
                'companions': ['clanrats', 'clanrats'],
            },
            {
                'position': 2,
                'leader_slug': 'plague-priest',
                'companions': ['plague-monks'],
            },
        ],
    },
    {
        'faction_slug': 'seraphon',
        'system_code': 'aos4',
        'slug': 'seraphon-vanguard-starter',
        'name': 'Seraphon Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Ancient starborn warriors advance under the cold gaze of a Saurus Oldblood. Disciplined, resilient, and deadly.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'saurus-oldblood',
                'companions': ['saurus-warriors', 'saurus-warriors'],
            },
            {
                'position': 2,
                'leader_slug': 'skink-starpriest',
                'companions': ['skinks'],
            },
        ],
    },
    {
        'faction_slug': 'stormcast-eternals',
        'system_code': 'aos4',
        'slug': 'stormcast-vanguard-starter',
        'name': 'Stormcast Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Sigmar\'s warriors reforged in celestial lightning. A Lord-Celestant leads a strike force of Liberators and Prosecutors.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'lord-celestant',
                'companions': ['liberators', 'liberators'],
            },
            {
                'position': 2,
                'leader_slug': 'knight-incantor',
                'companions': ['prosecutors'],
            },
        ],
    },
    {
        'faction_slug': 'sylvaneth',
        'system_code': 'aos4',
        'slug': 'sylvaneth-vanguard-starter',
        'name': 'Sylvaneth Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Spirits of the forest given form and fury. A Branchwych guides Dryads and Tree-Revenants through the hidden paths.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'branchwych',
                'companions': ['dryads', 'dryads'],
            },
            {
                'position': 2,
                'leader_slug': 'treelord-ancient',
                'companions': ['tree-revenants'],
            },
        ],
    },
    {
        'faction_slug': 'nighthaunt',
        'system_code': 'aos4',
        'slug': 'nighthaunt-vanguard-starter',
        'name': 'Nighthaunt Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'A shrieking host of vengeful spirits led by a Knight of Shrouds. They fade through walls and strike before you can react.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'knight-of-shrouds',
                'companions': ['chainrasp-horde', 'chainrasp-horde'],
            },
            {
                'position': 2,
                'leader_slug': 'dreadblade-harrow',
                'companions': ['grimghast-reapers'],
            },
        ],
    },
    {
        'faction_slug': 'space-marines',
        'system_code': 'w40k10',
        'slug': 'space-marines-incursion-starter',
        'name': 'Space Marines Incursion Starter',
        'format': 'incursion',
        'points_target': 1000,
        'summary': 'The Adeptus Astartes advance in disciplined squads. A Captain leads Intercessors and Assault Intercessors into the line.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'captain',
                'companions': ['intercessors', 'intercessors'],
            },
            {
                'position': 2,
                'leader_slug': 'lieutenant',
                'companions': ['assault-intercessors', 'hellblasters'],
            },
        ],
    },
    {
        'faction_slug': 'tyranids',
        'system_code': 'w40k10',
        'slug': 'tyranids-incursion-starter',
        'name': 'Tyranids Incursion Starter',
        'format': 'incursion',
        'points_target': 1000,
        'summary': 'The Great Devourer consumes all in its path. A Hive Tyrant directs waves of Termagants and Hormagaunts forward.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'hive-tyrant',
                'companions': ['termagants', 'termagants'],
            },
            {
                'position': 2,
                'leader_slug': 'tyranid-prime',
                'companions': ['hormagaunts', 'genestealers'],
            },
        ],
    },
]


def _do_seed(db, GameSystem, Faction, Unit, ArmyTemplate):
    created = 0
    for data in TEMPLATES_DATA:
        if ArmyTemplate.query.filter_by(slug=data['slug']).first():
            continue

        gs = GameSystem.query.filter_by(code=data['system_code']).first()
        faction = Faction.query.filter_by(slug=data['faction_slug']).first()
        if not gs or not faction:
            continue

        units_seen = []
        regiments_layout = []
        for reg in data['regiments_layout']:
            reg_entry = {'position': reg['position'], 'leader_slug': None, 'companion_slugs': []}
            leader = Unit.query.filter_by(slug=reg['leader_slug'], faction_id=faction.id).first()
            if leader:
                reg_entry['leader_slug'] = leader.slug
                units_seen.append({'slug': leader.slug, 'count': 1})
            for comp_slug in reg.get('companions', []):
                comp = Unit.query.filter_by(slug=comp_slug, faction_id=faction.id).first()
                if comp:
                    reg_entry['companion_slugs'].append(comp.slug)
                    existing = next((u for u in units_seen if u['slug'] == comp.slug), None)
                    if existing:
                        existing['count'] += 1
                    else:
                        units_seen.append({'slug': comp.slug, 'count': 1})
            regiments_layout.append(reg_entry)

        tmpl = ArmyTemplate(
            system_id=gs.id,
            faction_id=faction.id,
            slug=data['slug'],
            name=data['name'],
            format=data['format'],
            points_target=data['points_target'],
            units_json=units_seen,
            regiments_layout_json=regiments_layout,
            summary=data['summary'],
        )
        db.session.add(tmpl)
        created += 1

    db.session.commit()
    return created


if __name__ == '__main__':
    from app import create_app
    from app.extensions import db
    from app.models.game import GameSystem, Faction, Unit
    from app.models.army_template import ArmyTemplate

    app = create_app('dev')
    with app.app_context():
        n = _do_seed(db, GameSystem, Faction, Unit, ArmyTemplate)
        print(f'Seeded {n} army templates.')
