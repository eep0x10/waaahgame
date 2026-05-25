"""
AoS 4th Edition DB reconciliation — April 2026 GW PDF as source of truth.
Adds missing units, deletes phantoms for disciples-of-tzeentch.
Run inside container: python /app/scripts/_fill_pdf_gaps.py
"""
import sqlite3
import datetime
import re

DB_PATH = "/app/instance/waaahgame.db"


def slug(name):
    s = name.lower()
    # handle apostrophes and special chars
    s = s.replace("'", "").replace("’", "").replace("‘", "")
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    return s


def now():
    return datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"


# (name, points_cost, model_count, unit_category, role)
# role: 'hero' | 'unit'  (informational only, not stored separately)
# unit_category: 'regular' | 'legends'

PDF_UNITS = {
    # ── Stormcast Eternals (id=5) ─────────────────────────────────────────
    5: {
        "add": [
            # Missing heroes (main)
            ("Ionus Cryptborn Warden of Lost Souls", 360, 1, "regular"),
            ("Knight-Judicator with Gryph-hounds", 130, 1, "regular"),
            ("Lord-Commander Bastian Carthalos", 190, 1, "regular"),
            ("Lorai Child of the Abyss", 0, 1, "regular"),
            # Missing units (main)
            ("Annihilators", 130, 3, "regular"),
            ("Liberators", 90, 5, "regular"),
            ("Neave's Companions", 0, 3, "regular"),
            ("Praetors", 120, 3, "regular"),
            ("Dracothian Guard Concussors", 210, 2, "regular"),
            ("Dracothian Guard Concussors", 120, 1, "regular"),
            ("Dracothian Guard Desolators", 170, 2, "regular"),
            ("Dracothian Guard Desolators", 100, 1, "regular"),
            ("Dracothian Guard Fulminators", 200, 2, "regular"),
            ("Dracothian Guard Fulminators", 100, 1, "regular"),
            ("Dracothian Guard Tempestors", 170, 2, "regular"),
            ("Dracothian Guard Tempestors", 90, 1, "regular"),
            ("Stormdrake Guard", 310, 2, "regular"),
            ("Stormdrake Guard", 160, 1, "regular"),
            # Missing heroes (legends)
            ("Astreia Solbright", 220, 1, "legends"),
            ("Aventis Firestrike Magister of Hammerhal", 310, 1, "legends"),
            ("Knight-Incantor", 140, 1, "legends"),
            ("Lord-Arcanum on Gryph-charger", 220, 1, "legends"),
            ("Lord-Castellant", 150, 1, "legends"),
            ("Lord-Exorcist", 150, 1, "legends"),
        ],
    },
    # ── Slaves to Darkness (id=16) ────────────────────────────────────────
    16: {
        "add": [
            # Missing heroes (main)
            ("Centaurion Marshal", 120, 1, "regular"),
            ("Darkoath Chieftain on Warsteed", 100, 1, "regular"),
            ("Eternus", 180, 1, "regular"),
            ("Gaunt Summoner", 160, 1, "regular"),
            ("Gaunt Summoner on Disc of Tzeentch", 190, 1, "regular"),
            # Missing units (main)
            ("Chaos Furies", 120, 6, "regular"),
            ("Darkoath Fellriders", 140, 5, "regular"),
            ("Darkoath Savagers", 90, 10, "regular"),
            ("Darkoath Wilderfiend", 130, 1, "regular"),
            ("Ogroid Theridons", 160, 3, "regular"),
            ("The Oathsworn Kin", 0, 3, "regular"),
            # Missing heroes/units (legends)
            ("Chaos Lord on Manticore", 260, 1, "legends"),
            ("Chaos Sorcerer Lord on Manticore", 280, 1, "legends"),
            ("Chaos Warshrine", 250, 1, "legends"),
            ("Corvus Cabal", 100, 9, "legends"),
            ("Cypher Lords", 100, 8, "legends"),
            ("Godsworn Hunt", 110, 6, "legends"),
            ("Horns of Hashut", 120, 10, "legends"),
            ("Iron Golem", 100, 8, "legends"),
            ("Khagra's Ravagers", 170, 4, "legends"),
            ("Scions of the Flame", 120, 8, "legends"),
            ("Soul Grinder", 330, 1, "legends"),
            ("Spire Tyrants", 110, 9, "legends"),
        ],
    },
    # ── Idoneth Deepkin (id=72) ───────────────────────────────────────────
    72: {
        "add": [
            ("Ikon of the Storm", 130, 1, "regular"),
            ("Ikon of the Sea", 120, 1, "regular"),
            ("Mathaela", 150, 1, "regular"),
            ("Cyreni's Razors", 120, 4, "legends"),
            ("Elathain's Soulraid", 80, 5, "legends"),
        ],
    },
    # ── Lumineth Realm-lords (id=14) ──────────────────────────────────────
    14: {
        "add": [
            ("Scinari Enlightener", 180, 1, "regular"),
            ("Vanari Lord Regent on Lightcourser", 150, 1, "regular"),
            ("Vanari Starshard Ballista", 120, 1, "regular"),
            ("Ydrilan Riverblades", 140, 10, "regular"),
            ("Myari's Purifiers", 130, 4, "legends"),
        ],
    },
    # ── Hedonites of Slaanesh (id=32) ─────────────────────────────────────
    32: {
        "add": [
            ("Bladebringer Herald on Exalted Chariot", 130, 1, "regular"),
            ("Lord of Hubris", 100, 1, "regular"),
            ("Hellflayer", 130, 1, "regular"),
            ("Bladebringer Herald on Hellflayer", 140, 1, "legends"),
            ("Bladebringer Herald on Seeker Chariot", 130, 1, "legends"),
            ("Viceleader Herald of Slaanesh", 140, 1, "legends"),
            ("Exalted Chariot", 120, 1, "legends"),
            ("The Dread Pageant", 110, 4, "legends"),
            ("The Thricefold Discord", 130, 3, "legends"),
        ],
    },
    # ── Ossiarch Bonereapers (id=19) ──────────────────────────────────────
    19: {
        "add": [
            ("Liege-Kavalos on War Chariot", 230, 1, "regular"),
            ("Kavalos War Chariot", 170, 1, "regular"),
            ("Mortis Reapers", 90, 5, "regular"),
            ("Mortek Triaxes", 140, 10, "regular"),
            ("Teratic Cohort", 90, 8, "regular"),
            ("Kainan's Reapers", 140, 6, "legends"),
            ("Thanatek's Tithe", 90, 5, "legends"),
        ],
    },
    # ── Skaven (id=1) ─────────────────────────────────────────────────────
    1: {
        "add": [
            ("Doom-Flayers", 100, 2, "regular"),
            ("Ratling Guns", 170, 3, "regular"),
            ("Warpfire Throwers", 130, 3, "regular"),
            ("Warpvolt Scourgers", 170, 3, "regular"),
            ("Plague Priest", 110, 1, "legends"),
            ("Gutter Runners", 110, 5, "legends"),
            ("Plague Censer Bearers", 160, 5, "legends"),
            ("Skabbik's Plaguepack", 100, 5, "legends"),
            ("Skittershank's Clawpack", 100, 5, "legends"),
            ("Spiteclaw's Swarm", 100, 5, "legends"),
            ("Zikkit's Tunnelpack", 110, 4, "legends"),
        ],
    },
    # ── Daughters of Khaine (id=12) ───────────────────────────────────────
    12: {
        "add": [
            ("Sisters of Slaughter with Bladed Bucklers", 120, 10, "regular"),
            ("Maleneth Witchblade", 0, 1, "legends"),
            ("Gryselle's Arenai", 70, 5, "legends"),
            ("The Knives of the Crone", 220, 4, "legends"),
            ("Morgwaeth's Blade-coven", 120, 5, "legends"),
            ("The Shadeborn", 80, 4, "legends"),
        ],
    },
    # ── Flesh-eater Courts (id=48) ────────────────────────────────────────
    48: {
        "add": [
            ("Crypt Flayers", 90, 2, "regular"),
            ("Crypt Horrors", 100, 2, "regular"),
            ("Morbheg Knights", 180, 3, "regular"),
            ("Royal Beastflayers", 110, 10, "regular"),
            ("Crypt Ghast Courtier", 0, 1, "legends"),
            ("The Grymwatch", 80, 7, "legends"),
            ("The Skinnerkin", 80, 5, "legends"),
        ],
    },
    # ── Gloomspite Gitz (id=21) ───────────────────────────────────────────
    21: {
        "add": [
            ("Snarlpack Cavalry", 110, 3, "regular"),
            ("Wolfgit Retinue", 70, 2, "regular"),
            ("Loonboss with Giant Cave Squig", 120, 1, "legends"),
            ("Mollog", 210, 1, "legends"),
            ("Scuttleboss on Gigantic Spider", 160, 1, "legends"),
            ("Borgit's Beastgrabbaz", 90, 5, "legends"),
            ("Grinkrak's Looncourt", 100, 7, "legends"),
            ("Rippa's Snarlfangs", 100, 3, "legends"),
            ("Zarbag's Gitz", 130, 9, "legends"),
        ],
    },
    # ── Soulblight Gravelords (id=18) ─────────────────────────────────────
    18: {
        "add": [
            ("Lauka Vai Mother of Nightmares", 220, 1, "regular"),
            ("Zondara's Gravebreakers", 120, 5, "legends"),
        ],
    },
    # ── Seraphon (id=2) ───────────────────────────────────────────────────
    2: {
        "add": [
            ("Sunblood Pack", 150, 3, "regular"),
            ("Terrawings", 70, 3, "regular"),
            ("The Jaws of Itzl", 120, 3, "legends"),
            ("The Starblood Stalkers", 110, 6, "legends"),
        ],
    },
    # ── Cities of Sigmar (id=11) ──────────────────────────────────────────
    11: {
        "add": [
            ("Toll's Companions", 0, 3, "regular"),
        ],
    },
    # ── Blades of Khorne (id=28) ──────────────────────────────────────────
    28: {
        "add": [
            ("Herald of Khorne on Blood Throne", 160, 1, "regular"),
        ],
    },
    # ── Maggotkin of Nurgle (id=15) ───────────────────────────────────────
    15: {
        "add": [
            ("Nurglings", 100, 3, "regular"),
        ],
    },
    # ── Sylvaneth (id=6) ──────────────────────────────────────────────────
    6: {
        "add": [
            ("The Twistweald", 100, 8, "regular"),
        ],
    },
    # ── Kruleboyz (id=76) ─────────────────────────────────────────────────
    76: {
        "add": [
            ("Kruleboyz Monsta-killaz", 120, 7, "regular"),
        ],
    },
}

# Disciples of Tzeentch phantoms to delete
TZEENTCH_FACTION_ID = 17
TZEENTCH_DELETE_IDS = [1741, 1742]


def main():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    ts = now()
    total_added = 0
    total_deleted = 0
    skipped = []
    added_log = []

    # ── 1. Backup note (actual file backup should be done outside) ─────────
    print("=== AoS DB Reconciliation ===")
    print(f"Timestamp: {ts}")
    print()

    # ── 2. DELETE Tzeentch phantoms ────────────────────────────────────────
    print("--- Deleting Tzeentch phantoms ---")
    for del_id in TZEENTCH_DELETE_IDS:
        cur.execute("SELECT id, name, points_cost FROM units WHERE id=?", (del_id,))
        row = cur.fetchone()
        if row:
            cur.execute("DELETE FROM units WHERE id=?", (del_id,))
            print(f"  DELETED id={row[0]} '{row[1]}' pts={row[2]}")
            total_deleted += 1
        else:
            print(f"  SKIP DELETE id={del_id} — not found")
    print()

    # ── 3. INSERT missing units per faction ────────────────────────────────
    for faction_id, data in PDF_UNITS.items():
        units_to_add = data.get("add", [])
        if not units_to_add:
            continue

        # Fetch existing names for this faction (lowercase for comparison)
        cur.execute(
            "SELECT lower(name) FROM units WHERE faction_id=?", (faction_id,)
        )
        existing = {r[0] for r in cur.fetchall()}

        # Also fetch faction slug for display
        cur.execute("SELECT slug FROM factions WHERE id=?", (faction_id,))
        frow = cur.fetchone()
        faction_slug = frow[0] if frow else str(faction_id)

        print(f"--- Faction: {faction_slug} (id={faction_id}) ---")
        faction_added = 0

        for entry in units_to_add:
            name, pts, count, category = entry
            name_lc = name.lower()

            if name_lc in existing:
                skipped.append((faction_id, faction_slug, name, "already exists"))
                print(f"  SKIP  '{name}' — already in DB")
                continue

            unit_slug = slug(name)
            # Ensure slug uniqueness within faction by appending suffix if needed
            base_slug = unit_slug
            suffix = 1
            cur.execute(
                "SELECT COUNT(*) FROM units WHERE faction_id=? AND slug=?",
                (faction_id, unit_slug),
            )
            while cur.fetchone()[0] > 0:
                suffix += 1
                unit_slug = f"{base_slug}-{suffix}"
                cur.execute(
                    "SELECT COUNT(*) FROM units WHERE faction_id=? AND slug=?",
                    (faction_id, unit_slug),
                )

            cur.execute(
                """INSERT INTO units
                   (faction_id, slug, name, points_cost, model_count,
                    stats_json, weapons_json, abilities_json, keywords_json,
                    companions_json, unit_category, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    faction_id,
                    unit_slug,
                    name,
                    pts,
                    count,
                    "{}",
                    "[]",
                    "[]",
                    "[]",
                    "[]",
                    category,
                    ts,
                    ts,
                ),
            )
            existing.add(name_lc)
            total_added += 1
            faction_added += 1
            added_log.append((faction_id, faction_slug, name, pts, count, category))
            print(f"  ADD   '{name}' pts={pts} count={count} cat={category}")

        print(f"  => Added {faction_added} units")
        print()

    con.commit()

    # ── 4. Final audit ─────────────────────────────────────────────────────
    print("=== FINAL AUDIT (per-faction unit counts) ===")
    cur.execute(
        """
        SELECT f.slug, f.id,
               SUM(CASE WHEN u.unit_category='regular' THEN 1 ELSE 0 END) AS main_count,
               SUM(CASE WHEN u.unit_category='legends' THEN 1 ELSE 0 END) AS legends_count,
               COUNT(*) AS total
        FROM factions f
        LEFT JOIN units u ON u.faction_id = f.id
        WHERE f.game_system_id = 1
        GROUP BY f.id
        ORDER BY f.slug
        """
    )
    rows = cur.fetchall()
    print(f"{'Faction':<45} {'ID':>5} {'Main':>6} {'Legends':>8} {'Total':>7}")
    print("-" * 75)
    for r in rows:
        print(f"{r[0]:<45} {r[1]:>5} {r[2]:>6} {r[3]:>8} {r[4]:>7}")
    print()

    # ── 5. Summary ─────────────────────────────────────────────────────────
    print("=== SUMMARY ===")
    print(f"Total ADDED:   {total_added}")
    print(f"Total DELETED: {total_deleted}")
    print(f"Total SKIPPED: {len(skipped)}")
    print()

    if skipped:
        print("--- Skipped (already in DB) ---")
        for s in skipped:
            print(f"  faction={s[1]} '{s[2]}' — {s[3]}")
        print()

    print("--- Suspicious cases to review manually ---")
    suspicious = [
        "SCE: DB has singular 'Annihilator'@180, 'Liberator'@90, 'Praetor'@120 — PDF uses plurals with different pts. Old entries, not deleted.",
        "SCE: DB 'Stormdrake Guard' may exist with different pts — check for duplicate after run.",
        "Skaven: DB 'Stormfiend'@150 vs PDF 'Stormfiends' 3/240 — name/pts mismatch, not deleted.",
        "Gloomspite: DB 'Troggboss' (standalone) not in PDF as standalone — possible phantom.",
        "StD: DB id=1738 'Archaon'@870 not in PDF (PDF has 810) — possible phantom, NOT deleted (outside +2 scope).",
        "Disciples: DB id=1739 'Magister'@90 and id=1740 'Tzaangor Shaman'@120 may be phantoms beyond the 2 deleted — verify.",
        "DoK: 'Sisters of Slaughter with Sacrificial Knives' (10/110) — check if already in DB under different name.",
        "Sylvaneth: PDF has 'Kurnoth Hunters with Greatbows' 3/240 and 'Kurnoth Hunters with Greatswords' 3/240 alongside 200pt variants — verify DB.",
    ]
    for s in suspicious:
        print(f"  [!] {s}")

    con.close()
    print()
    print("Done.")


if __name__ == "__main__":
    main()
