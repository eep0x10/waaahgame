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
        'summary': 'Uma maré roedora de infantaria Skaven liderada por um astuto Warlock Engineer. Rápida, numerosa e imprevisível.',
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
        'summary': 'Guerreiros ancestrais nascidos das estrelas avançam sob o olhar frio de um Saurus Oldblood. Disciplinados, resistentes e letais.',
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
        'summary': 'Os guerreiros de Sigmar reforjados em raios celestiais. Um Lord-Celestant lidera uma força de ataque de Liberators e Prosecutors.',
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
        'summary': 'Espíritos da floresta dotados de forma e fúria. Uma Branchwych guia Dryads e Tree-Revenants pelos caminhos ocultos.',
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
        'summary': 'Uma horda uivante de espíritos vingadores liderada por um Knight of Shrouds. Atravessam paredes e golpeiam antes que você possa reagir.',
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
        'summary': 'Uma força urbana disciplinada com armas combinadas. Um Freeguild Marshal lidera Steelhelms e Cavaliers na defesa da ordem.',
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
        'summary': 'Uma horda aelven sedenta de sangue a serviço de Khaine. Uma Hag Queen leva as Witch Aelves ao frenesi.',
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
        'summary': 'Mercenários duardin dos céus descem das nuvens. Um Admiral comanda Arkanaut Companies e Thunderers.',
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
        'summary': 'Eruditos aelven marcham com precisão geométrica. Um Vanari Lord Regent comanda Wardens e Sentinels.',
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
        'summary': 'Praga e pestilência tornadas concretas. Um Lord of Plagues lidera Putrid Blightkings e Plaguebearers.',
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
        'summary': 'A vanguarda mortal do Caos avança sob estandartes sombrios. Um Chaos Sorcerer Lord lidera Warriors e Knights.',
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
        'summary': 'A realidade se desfaz diante do Mutador dos Caminhos. Um Magister lidera Pink Horrors e Tzaangors.',
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
        'summary': 'Nobreza vampírica comanda os mortos ressurgidos. Um Vampire Lord lidera Blood Knights e Skeleton Warriors.',
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
        'summary': 'As construções de osso de elite de Nagash avançam em formação perfeita. Um Liege-Kavalos lidera a Mortek Guard.',
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
        'summary': 'Os Ironjawz esmagam tudo em seu caminho. Um Orruk Warchanter leva Ardboys e Brutes ao frenesi.',
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
        'summary': 'Os Adeptus Astartes avançam em esquadrões disciplinados. Um Captain lidera Intercessors e Assault Intercessors para a linha de frente.',
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
        'summary': 'O Grande Devorador consome tudo em seu caminho. Um Hive Tyrant direciona ondas de Termagants e Hormagaunts para a frente.',
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
    created = updated = 0
    for data in TEMPLATES_DATA:
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

        existing_tmpl = ArmyTemplate.query.filter_by(slug=data['slug']).first()
        if existing_tmpl:
            existing_tmpl.name = data['name']
            existing_tmpl.format = data['format']
            existing_tmpl.points_target = data['points_target']
            existing_tmpl.summary = data['summary']
            existing_tmpl.units_json = units_seen
            existing_tmpl.regiments_layout_json = regiments_layout
            updated += 1
        else:
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
    return created, updated


if __name__ == '__main__':
    from app import create_app
    from app.extensions import db
    from app.models.game import GameSystem, Faction, Unit
    from app.models.army_template import ArmyTemplate

    app = create_app('dev')
    with app.app_context():
        n_created, n_updated = _do_seed(db, GameSystem, Faction, Unit, ArmyTemplate)
        print(f'Army templates: {n_created} criados, {n_updated} atualizados.')
