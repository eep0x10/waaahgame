"""Apply manually-researched AoS 4 matched-play points to units the bulk
Wahapedia backfill could not resolve.

Idempotent: only updates rows where points_cost == 0 to avoid stomping on
later balance updates.

Sources (Wahapedia AoS4 warscrolls, Warhammer Community articles, Goonhammer):
  - Saurus Knight 100         -- wahapedia.ru (AoS3/AoS4 carryover, search-confirmed)
  - Saurus Eternity Warden 110-- wahapedia.ru/warhammer.com warscroll
  - Amethyst Knellmage 110    -- warhammer-community.com cities-of-sigmar rules new-units
  - Aqshian Pyrocaster 100    -- warhammer-community.com cities-of-sigmar rules new-units
  - Freeguild Gallant 130     -- warhammer-community.com cities-of-sigmar rules new-units
  - Freeguild Grenadier 140   -- warhammer-community.com cities-of-sigmar rules new-units
  - Mallus Forgepriest 130    -- COS Battle Profiles Apr 2026 PDF p.1
  - Cannonade Cogfort 530     -- COS Battle Profiles Apr 2026 PDF p.1
  - Conqueror Cogfort 440     -- COS Battle Profiles Apr 2026 PDF p.1
    (PDF URL: assets.warhammer-community.com/eng_13-05_aos_core_rules_
     cities_of_sigmar_battle_profiles-ezblw7onac-xjqbdov4pu.pdf)

Intentional-zero (no authoritative AoS4 matched-play points exists):
  - Avatar of Khaine          -- manifestation, summon-only, "Points: 0"
  - Riptooth                  -- Legends only (Magore's Fiends bundle)
  - Razordon, Salamander, Skink Handler -- retired from AoS4 Seraphon roster
  - Branchwraith              -- retired from AoS4 Sylvaneth roster
  - Blight Templar            -- not in AoS4 Maggotkin roster
  - Deathrunner, Packmaster   -- not individual units in AoS4 Skaven
  - Warpspark Weapon Battery  -- kit only; individual warscrolls (Ratling Gun
                                 170 / Warpfire Throwers 130 / Warpvolt
                                 Scourgers 170) exist as separate units
  - Freeguild General, White Lion Chariot
                              -- removed from AoS4 COS roster (Apr 2026
                                 battletome); old Warhammer Fantasy kits
                                 retired, not in official Battle Profiles PDF
                                 (confirmed Sprues & Brews 2026-05-16 review:
                                 "all old Warhammer Fantasy units removed")
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app import create_app
from app.extensions import db
from app.models.game import Unit, Faction


# (faction_slug, unit_name) -> (points, source_note)
UPDATES = {
    ("seraphon", "Saurus Knight"): (100, "wahapedia.ru aos seraphon"),
    ("seraphon", "Saurus Eternity Warden"): (110, "wahapedia.ru aos seraphon"),
    ("cities-of-sigmar", "Amethyst Knellmage"): (110, "warhammer-community.com cos new-units"),
    ("cities-of-sigmar", "Aqshian Pyrocaster"): (100, "warhammer-community.com cos new-units"),
    ("cities-of-sigmar", "Freeguild Gallant"): (130, "warhammer-community.com cos new-units"),
    ("cities-of-sigmar", "Freeguild Grenadier"): (140, "warhammer-community.com cos new-units"),
    # CITIES_BATTLETOME_2026 — sourced from official Apr 2026 Battle Profiles PDF
    ("cities-of-sigmar", "Mallus Forgepriest"): (130, "COS Battle Profiles Apr 2026 PDF p.1"),
    ("cities-of-sigmar", "Cannonade Cogfort"): (530, "COS Battle Profiles Apr 2026 PDF p.1"),
    ("cities-of-sigmar", "Conqueror Cogfort"): (440, "COS Battle Profiles Apr 2026 PDF p.1"),
}

# (faction_slug, unit_name) -> reason  (left at 0 deliberately)
INTENTIONAL_ZERO = {
    ("daughters-of-khaine", "Avatar of Khaine"): "manifestation/summon-only (Points: 0)",
    ("blades-of-khorne", "Riptooth"): "Legends only, part of Magore's Fiends 120pt bundle",
    ("seraphon", "Razordon"): "retired from AoS4 Seraphon roster",
    ("seraphon", "Salamander"): "retired from AoS4 Seraphon roster",
    ("seraphon", "Skink Handler"): "retired from AoS4 Seraphon roster",
    ("sylvaneth", "Branchwraith"): "retired from AoS4 Sylvaneth roster",
    ("maggotkin-of-nurgle", "Blight Templar"): "not in current AoS4 Maggotkin roster",
    ("skaventide", "Deathrunner"): "not individual unit in AoS4 Skaven",
    ("skaventide", "Packmaster"): "not individual unit in AoS4 Skaven",
    ("skaventide", "Warpspark Weapon Battery"): "kit only; individual ws: Ratling Gun 170, Warpfire 130, Warpvolt 170",
    ("cities-of-sigmar", "Freeguild General"): "removed from AoS4 COS Apr 2026 roster (old WHFB kit retired)",
    ("cities-of-sigmar", "White Lion Chariot"): "removed from AoS4 COS Apr 2026 roster (old WHFB kit retired)",
}


def main():
    app = create_app()
    app.app_context().push()

    updated = []
    skipped_already_set = []
    not_found = []

    for (slug, name), (pts, src) in UPDATES.items():
        fac = Faction.query.filter_by(slug=slug).first()
        if fac is None:
            not_found.append((slug, name, "faction missing"))
            continue
        unit = Unit.query.filter_by(faction_id=fac.id, name=name).first()
        if unit is None:
            not_found.append((slug, name, "unit missing"))
            continue
        if unit.points_cost and unit.points_cost != 0:
            skipped_already_set.append((slug, name, unit.points_cost))
            continue
        unit.points_cost = pts
        updated.append((slug, name, pts, src))

    db.session.commit()

    print("=== APPLIED UPDATES ===")
    for slug, name, pts, src in updated:
        print(f"  [+] {slug} | {name} -> {pts} pts ({src})")
    if not updated:
        print("  (none)")

    print("\n=== INTENTIONAL ZEROS (left at 0) ===")
    for (slug, name), reason in INTENTIONAL_ZERO.items():
        fac = Faction.query.filter_by(slug=slug).first()
        if not fac:
            print(f"  [?] {slug} | {name} - faction missing")
            continue
        unit = Unit.query.filter_by(faction_id=fac.id, name=name).first()
        if not unit:
            print(f"  [?] {slug} | {name} - unit missing in DB")
            continue
        print(f"  [0] {slug} | {name} - {reason}")

    if skipped_already_set:
        print("\n=== SKIPPED (already non-zero) ===")
        for slug, name, pts in skipped_already_set:
            print(f"  [=] {slug} | {name} already {pts}")

    if not_found:
        print("\n=== NOT FOUND ===")
        for slug, name, why in not_found:
            print(f"  [!] {slug} | {name} ({why})")

    zero_remaining = Unit.query.filter_by(points_cost=0).count()
    print(f"\nUnits with points_cost==0 after apply: {zero_remaining}")


if __name__ == "__main__":
    main()
