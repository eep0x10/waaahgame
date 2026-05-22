"""
Pass 2: Add remaining missing AoS units that were skipped in pass 1 due to slug collisions
with units in sibling factions (e.g., tzeentch-arcanites, orruk-warclans, monsters-of-chaos).
These units need faction-prefixed slugs to avoid the globally-unique slug constraint.
"""
import sys
sys.path.insert(0, '/app')

from app import create_app
from app.extensions import db
from app.models.game import Faction, Unit

app = create_app()

UNITS_PASS2 = [
    # DISCIPLES OF TZEENTCH (fid=17) - slug collisions with tzeentch-arcanites (fid=24)
    dict(faction_id=17, slug='disciples-fatemaster', name='Fatemaster', points_cost=150, model_count=1,
         keywords=['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'ARCANITE', 'INFANTRY', 'WIZARD (1)'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=17, slug='disciples-magister', name='Magister', points_cost=140, model_count=1,
         keywords=['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'WIZARD (1)', 'ARCANITE', 'INFANTRY'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=17, slug='disciples-tzaangor-enlightened', name='Tzaangor Enlightened', points_cost=200, model_count=3,
         keywords=['CHAOS', 'DISCIPLES OF TZEENTCH', 'ARCANITE', 'INFANTRY', 'CHAMPION', 'WARFLOCK'],
         unit_role=None, can_be_general=False),
    dict(faction_id=17, slug='disciples-tzaangor-shaman', name='Tzaangor Shaman', points_cost=130, model_count=1,
         keywords=['HERO', 'CHAOS', 'DISCIPLES OF TZEENTCH', 'CAVALRY', 'FLY', 'WIZARD (1)', 'ARCANITE', 'WARFLOCK'],
         unit_role='Hero', can_be_general=True),

    # HEDONITES OF SLAANESH (fid=32) - slug collisions with slaanesh-sybarites (fid=36)
    dict(faction_id=32, slug='hedonites-lord-of-hubris', name='Lord of Hubris', points_cost=100, model_count=1,
         keywords=['CHAOS', 'HEDONITES OF SLAANESH', 'SYBARITE', 'HERO', 'INFANTRY', 'WARD (5+)'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=32, slug='hedonites-lord-of-pain', name='Lord of Pain', points_cost=110, model_count=1,
         keywords=['CHAOS', 'HEDONITES OF SLAANESH', 'SYBARITE', 'HERO', 'INFANTRY', 'WARD (5+)'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=32, slug='hedonites-shardspeaker-of-slaanesh', name='Shardspeaker of Slaanesh', points_cost=120, model_count=1,
         keywords=['CHAOS', 'HEDONITES OF SLAANESH', 'SYBARITE', 'HERO', 'WIZARD (1)', 'INFANTRY', 'WARD (6+)'],
         unit_role='Hero', can_be_general=True),

    # IRONJAWZ (fid=75) - slug collisions with orruk-warclans (fid=20)
    dict(faction_id=75, slug='ironjawz-ardboy-big-boss', name='Ardboy Big Boss', points_cost=100, model_count=1,
         keywords=['HERO', 'DESTRUCTION', 'IRONJAWZ', 'INFANTRY'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=75, slug='ironjawz-gordrakk-the-fist-of-gork', name='Gordrakk, the Fist of Gork', points_cost=340, model_count=1,
         keywords=['HERO', 'UNIQUE', 'MONSTER', 'WARMASTER', 'DESTRUCTION', 'IRONJAWZ', 'MAW-KRUSHA', 'FLY'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=75, slug='ironjawz-megaboss', name='Megaboss', points_cost=140, model_count=1,
         keywords=['HERO', 'DESTRUCTION', 'INFANTRY', 'IRONJAWZ'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=75, slug='ironjawz-megaboss-on-maw-krusha', name='Megaboss on Maw-krusha', points_cost=330, model_count=1,
         keywords=['HERO', 'MONSTER', 'DESTRUCTION', 'IRONJAWZ', 'MAW-KRUSHA', 'FLY'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=75, slug='ironjawz-warchanter', name='Warchanter', points_cost=110, model_count=1,
         keywords=['HERO', 'DESTRUCTION', 'INFANTRY', 'IRONJAWZ', 'PRIEST (1)'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=75, slug='ironjawz-weirdnob-shaman', name='Weirdnob Shaman', points_cost=110, model_count=1,
         keywords=['HERO', 'DESTRUCTION', 'INFANTRY', 'IRONJAWZ', 'WIZARD (1)'],
         unit_role='Hero', can_be_general=True),

    # KRULEBOYZ (fid=76) - slug collision with orruk-warclans (fid=20)
    dict(faction_id=76, slug='kruleboyz-swampcalla-shaman-with-pot-grot', name='Swampcalla Shaman with Pot-grot', points_cost=120, model_count=1,
         keywords=['HERO', 'DESTRUCTION', 'KRULEBOYZ', 'INFANTRY', 'WIZARD (1)'],
         unit_role='Hero', can_be_general=True),

    # MAGGOTKIN OF NURGLE (fid=15) - slug collision with existing 'Pusgoyle Blightlord' mc=1
    dict(faction_id=15, slug='maggotkin-pusgoyle-blightlords', name='Pusgoyle Blightlords', points_cost=110, model_count=1,
         keywords=['CHAOS', 'MAGGOTKIN OF NURGLE', 'ROTBRINGERS', 'CAVALRY', 'FLY', 'WARD (6+)'],
         unit_role=None, can_be_general=False),

    # SLAVES TO DARKNESS (fid=16) - various slug collisions
    dict(faction_id=16, slug='slaves-archaon-the-everchosen', name='Archaon, the Everchosen', points_cost=810, model_count=1,
         keywords=['HERO', 'MONSTER', 'UNIQUE', 'WARMASTER', 'CHAOS', 'SLAVES TO DARKNESS', 'DAEMON',
                   'WARRIORS OF CHAOS', 'WARD (5+)', 'FLY', 'WIZARD (2)'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=16, slug='slaves-chaos-lord', name='Chaos Lord', points_cost=100, model_count=1,
         keywords=['HERO', 'CHAOS', 'SLAVES TO DARKNESS', 'MORTAL', 'INFANTRY', 'WARRIORS OF CHAOS'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=16, slug='slaves-gaunt-summoner', name='Gaunt Summoner', points_cost=160, model_count=1,
         keywords=['HERO', 'CHAOS', 'SLAVES TO DARKNESS', 'MORTAL', 'INFANTRY', 'WIZARD (2)'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=16, slug='slaves-gaunt-summoner-on-disc', name='Gaunt Summoner on Disc of Tzeentch', points_cost=190, model_count=1,
         keywords=['HERO', 'CHAOS', 'SLAVES TO DARKNESS', 'MORTAL', 'CAVALRY', 'FLY', 'WIZARD (2)'],
         unit_role='Hero', can_be_general=True),
    dict(faction_id=16, slug='slaves-mutalith-vortex-beast', name='Mutalith Vortex Beast', points_cost=160, model_count=1,
         keywords=['SLAVES TO DARKNESS', 'CHAOS', 'MONSTER', 'DAEMON'],
         unit_role=None, can_be_general=False),
    dict(faction_id=16, slug='slaves-slaughterbrute', name='Slaughterbrute', points_cost=200, model_count=1,
         keywords=['SLAVES TO DARKNESS', 'CHAOS', 'MONSTER', 'DAEMON'],
         unit_role=None, can_be_general=False),

    # SOULBLIGHT GRAVELORDS (fid=18)
    dict(faction_id=18, slug='soulblight-fell-bats', name='Fell Bats', points_cost=80, model_count=3,
         keywords=['DEATH', 'SOULBLIGHT GRAVELORDS', 'DEADWALKERS', 'BEAST', 'FLY', 'WARD (6+)'],
         unit_role=None, can_be_general=False),
    dict(faction_id=18, slug='deadwalker-zombies', name='Deadwalker Zombies', points_cost=130, model_count=10,
         keywords=['DEATH', 'SOULBLIGHT GRAVELORDS', 'DEADWALKERS', 'INFANTRY', 'CHAMPION', 'WARD (6+)'],
         unit_role=None, can_be_general=False),
    dict(faction_id=18, slug='soulblight-revenant-draconith', name='Revenant Draconith', points_cost=190, model_count=1,
         keywords=['DEATH', 'SOULBLIGHT GRAVELORDS', 'MONSTER', 'FLY', 'WARD (6+)'],
         unit_role=None, can_be_general=False),

    # SERAPHON (fid=2) - slug collisions with existing singular entries
    dict(faction_id=2, slug='seraphon-ripperdactyl-riders', name='Ripperdactyl Riders', points_cost=70, model_count=2,
         keywords=['ORDER', 'SERAPHON', 'SKINK', 'CAVALRY', 'CHAMPION', 'FLY'],
         unit_role=None, can_be_general=False),
    dict(faction_id=2, slug='seraphon-terradon-riders', name='Terradon Riders', points_cost=70, model_count=2,
         keywords=['ORDER', 'SERAPHON', 'SKINK', 'CAVALRY', 'CHAMPION', 'FLY'],
         unit_role=None, can_be_general=False),
]


def main():
    with app.app_context():
        inserted = 0
        skipped = 0
        errors = []
        faction_count = {}

        for d in UNITS_PASS2:
            fid = d['faction_id']
            name = d['name']
            slug = d['slug']

            # Idempotency check
            if Unit.query.filter_by(slug=slug).first() or Unit.query.filter_by(faction_id=fid, name=name).first():
                skipped += 1
                continue

            try:
                u = Unit(
                    faction_id=fid,
                    slug=slug,
                    name=name,
                    points_cost=d['points_cost'],
                    model_count=d.get('model_count', 1),
                    base_size_mm=None,
                    unit_role=d.get('unit_role'),
                    can_be_general=d.get('can_be_general', False),
                    can_be_reinforced=False,
                    stats_json={},
                    weapons_json=[],
                    abilities_json=[],
                    keywords_json=d.get('keywords', []),
                    companions_json=[],
                    unit_category='regular',
                )
                db.session.add(u)
                db.session.flush()
                inserted += 1
                f = Faction.query.get(fid)
                fname = f.code if f else str(fid)
                faction_count[fname] = faction_count.get(fname, 0) + 1
            except Exception as e:
                db.session.rollback()
                errors.append(f"{name} (fid={fid}): {e}")

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"COMMIT FAILED: {e}")
            return

        print("\n=== add_missing_aos_units_pass2.py ===")
        print(f"Inserted:  {inserted}")
        print(f"Skipped (already present): {skipped}")
        print(f"Errors:    {len(errors)}")
        for err in errors:
            print(f"  - {err}")
        print("\nInserted by faction:")
        for fname, count in sorted(faction_count.items(), key=lambda x: -x[1]):
            print(f"  {fname}: {count}")

        # Post-insert AoS totals
        total_regular = Unit.query.join(Faction).filter(
            Faction.game_system_id == 1,
            Unit.unit_category == 'regular'
        ).count()
        total_all = Unit.query.join(Faction).filter(Faction.game_system_id == 1).count()
        print(f"\nPost-insert AoS regular units: {total_regular}")
        print(f"Post-insert AoS total (all categories): {total_all}")


if __name__ == '__main__':
    main()
