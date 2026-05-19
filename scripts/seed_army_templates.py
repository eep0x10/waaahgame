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
        'faction_slug': 'cities-of-sigmar',
        'system_code': 'aos4',
        'slug': 'cities-vanguard-starter',
        'name': 'Cities of Sigmar Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'A disciplined combined-arms city force. A Freeguild Marshal leads Steelhelms and Cavaliers in defence of order.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'freeguild-marshal',
                'companions': ['freeguild-steelhelms', 'freeguild-steelhelms'],
            },
            {
                'position': 2,
                'leader_slug': 'battlemage',
                'companions': ['freeguild-cavaliers'],
            },
        ],
    },
    {
        'faction_slug': 'daughters-of-khaine',
        'system_code': 'aos4',
        'slug': 'dok-vanguard-starter',
        'name': 'Daughters of Khaine Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'A bloodthirsty aelven host in service to Khaine. A Hag Queen drives Witch Aelves into a frenzy.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'hag-queen',
                'companions': ['witch-aelves', 'witch-aelves'],
            },
            {
                'position': 2,
                'leader_slug': 'slaughter-queen',
                'companions': ['blood-sisters'],
            },
        ],
    },
    {
        'faction_slug': 'kharadron-overlords',
        'system_code': 'aos4',
        'slug': 'ko-vanguard-starter',
        'name': 'Kharadron Overlords Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Sky-duardin mercenaries descend from the clouds. An Admiral commands Arkanaut Companies and Thunderers.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'arkanaut-admiral',
                'companions': ['arkanaut-company', 'arkanaut-company'],
            },
            {
                'position': 2,
                'leader_slug': 'aether-khemist',
                'companions': ['thunderers'],
            },
        ],
    },
    {
        'faction_slug': 'lumineth-realm-lords',
        'system_code': 'aos4',
        'slug': 'lumineth-vanguard-starter',
        'name': 'Lumineth Realm-Lords Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Aelven scholars march with geometric precision. A Vanari Lord Regent commands Wardens and Sentinels.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'vanari-lord-regent',
                'companions': ['vanari-auralan-wardens', 'vanari-auralan-sentinels'],
            },
            {
                'position': 2,
                'leader_slug': 'alarith-stonemage',
                'companions': ['alarith-stoneguard'],
            },
        ],
    },
    {
        'faction_slug': 'maggotkin-of-nurgle',
        'system_code': 'aos4',
        'slug': 'nurgle-vanguard-starter',
        'name': 'Maggotkin of Nurgle Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Plague and pestilence made manifest. A Lord of Plagues leads Putrid Blightkings and Plaguebearers.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'lord-of-plagues',
                'companions': ['putrid-blightkings', 'plaguebearers'],
            },
            {
                'position': 2,
                'leader_slug': 'harbinger-of-decay',
                'companions': ['plaguebearers'],
            },
        ],
    },
    {
        'faction_slug': 'slaves-to-darkness',
        'system_code': 'aos4',
        'slug': 'std-vanguard-starter',
        'name': 'Slaves to Darkness Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': "Chaos's mortal vanguard advances under dark banners. A Chaos Sorcerer Lord leads Warriors and Knights.",
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'chaos-sorcerer-lord',
                'companions': ['chaos-warriors', 'chaos-warriors'],
            },
            {
                'position': 2,
                'leader_slug': 'darkoath-chieftain',
                'companions': ['chaos-knights'],
            },
        ],
    },
    {
        'faction_slug': 'disciples-of-tzeentch',
        'system_code': 'aos4',
        'slug': 'tzeentch-vanguard-starter',
        'name': 'Disciples of Tzeentch Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Reality unravels before the Changer of Ways. A Magister leads Pink Horrors and Tzaangors.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'magister',
                'companions': ['pink-horrors-of-tzeentch', 'tzaangors'],
            },
            {
                'position': 2,
                'leader_slug': 'tzaangor-shaman',
                'companions': ['kairic-acolytes'],
            },
        ],
    },
    {
        'faction_slug': 'soulblight-gravelords',
        'system_code': 'aos4',
        'slug': 'soulblight-vanguard-starter',
        'name': 'Soulblight Gravelords Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': 'Vampiric nobility commands the risen dead. A Vampire Lord leads Blood Knights and Skeleton Warriors.',
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'vampire-lord',
                'companions': ['blood-knights', 'skeleton-warriors'],
            },
            {
                'position': 2,
                'leader_slug': 'necromancer',
                'companions': ['dire-wolves'],
            },
        ],
    },
    {
        'faction_slug': 'ossiarch-bonereapers',
        'system_code': 'aos4',
        'slug': 'obr-vanguard-starter',
        'name': 'Ossiarch Bonereapers Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': "Nagash's elite bone constructs advance in perfect formation. A Liege-Kavalos leads Mortek Guard.",
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'liege-kavalos',
                'companions': ['mortek-guard', 'mortek-guard'],
            },
            {
                'position': 2,
                'leader_slug': 'mortisan-boneshaper',
                'companions': ['kavalos-deathriders'],
            },
        ],
    },
    {
        'faction_slug': 'orruk-warclans',
        'system_code': 'aos4',
        'slug': 'orruk-vanguard-starter',
        'name': 'Orruk Warclans Vanguard Starter',
        'format': 'vanguard',
        'points_target': 1000,
        'summary': "Ironjawz smash everything in their path. An Orruk Warchanter drives Ardboys and Brutes into a frenzy.",
        'regiments_layout': [
            {
                'position': 1,
                'leader_slug': 'orruk-warchanter',
                'companions': ['orruk-ardboys', 'orruk-brutes'],
            },
            {
                'position': 2,
                'leader_slug': 'orruk-weirdnob-shaman',
                'companions': ['kruleboyz-gutrippaz'],
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
