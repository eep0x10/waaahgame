import sqlite3, json, os, shutil

conn = sqlite3.connect('/app/instance/waaahgame.db')
c = conn.cursor()

BASE_IMG = '/app/app/static/img/'

c.execute("SELECT slug, id FROM factions WHERE game_system_id=1")
faction_map = {r[0]: r[1] for r in c.fetchall()}

conflicts = [
    (337, 'acolyte-globadier', 'acolyte-globadiers', 1128, 'skaven'),
    (639, 'aetherwing', 'aetherwings', 1237, None),
    (611, 'aggradon-lancer', 'aggradon-lancers', 713, None),
    (640, 'annihilator', 'annihilators', 1224, None),
    (389, 'barrow-knight', 'barrow-knights', 1186, None),
    (240, 'bestigor', 'bestigors', 761, None),
    (607, 'black-ark-corsair', 'black-ark-corsairs', 816, None),
    (411, 'bladegheist-revenant', 'bladegheist-revenants', 1058, None),
    (526, 'bleaksword', 'bleakswords', 838, None),
    (286, 'blissbarb-archer', 'blissbarb-archers', 968, 'hedonites-of-slaanesh'),
    (287, 'blissbarb-seeker', 'blissbarb-seekers', 949, 'hedonites-of-slaanesh'),
    (437, 'blood-knight', 'blood-knights', 1189, None),
    (533, 'blood-sister', 'blood-sisters', 844, None),
    (534, 'blood-stalker', 'blood-stalkers', 848, None),
    (478, 'brute', 'brutes', 992, 'ironjawz'),
    (641, 'castigator', 'castigators', 1218, None),
    (241, 'centigor', 'centigors', 764, None),
    (413, 'chainghast', 'chainghasts', 1066, None),
    (414, 'chainrasp', 'chainrasps', 1056, None),
    (376, 'chaos-knight', 'chaos-knights', 1158, None),
    (308, 'chaos-warhound', 'chaos-warhounds', 765, 'beasts-of-chaos'),
    (377, 'chaos-warrior', 'chaos-warriors', 1155, None),
    (369, 'clanrat', 'clanrats', 704, 'skaven'),
    (398, 'crypt-flayer', 'crypt-flayers', 891, None),
    (400, 'crypt-ghoul', 'crypt-ghouls', 894, None),
    (403, 'crypt-horror', 'crypt-horrors', 900, None),
    (638, 'dark-rider', 'dark-riders', 840, None),
    (527, 'darkshard', 'darkshards', 815, None),
    (385, 'deadwalker-zombie', 'deadwalker-zombies', 1179, None),
    (203, 'deathrattle-skeleton', 'deathrattle-skeletons', 1164, None),
    (335, 'doom-flayer', 'doom-flayers', 1123, 'skaven'),
    (536, 'doomfire-warlock', 'doomfire-warlocks', 852, None),
    (362, 'dragon-ogor', 'dragon-ogors', 756, None),
    (604, 'drakespawn-knight', 'drakespawn-knights', 829, None),
    (416, 'dreadblade-harrow', 'dreadblade-harrows', 1061, None),
    (417, 'dreadscythe-harridan', 'dreadscythe-harridans', 1049, None),
    (528, 'dreadspear', 'dreadspears', 808, None),
    (686, 'dryad', 'dryads', 1251, None),
    (596, 'endrinrigger', 'endrinriggers', 1001, None),
    (646, 'evocator', 'evocators', 1230, None),
    (529, 'executioner', 'executioners', 832, None),
    (440, 'fell-bat', 'fell-bats', 1178, None),
    (518, 'fellwater-troggoth', 'fellwater-troggoths', 943, None),
    (543, 'flagellant', 'flagellants', 824, None),
    (551, 'freeguild-cavalier', 'freeguild-cavaliers', 826, None),
    (554, 'freeguild-fusilier', 'freeguild-fusiliers', 839, None),
    (558, 'freeguild-steelhelm', 'freeguild-steelhelms', 835, None),
    (445, 'frost-sabre', 'frost-sabres', 1075, None),
    (418, 'glaivewraith-stalker', 'glaivewraith-stalkers', 1054, None),
    (469, 'gnoblar', 'gnoblars', 1078, None),
    (242, 'gor', 'gors', 760, None),
    (480, 'gore-grunta', 'gore-gruntas', 994, 'ironjawz'),
    (419, 'grimghast-reaper', 'grimghast-reapers', 1060, None),
    (597, 'grundstok-thunderer', 'grundstok-thunderers', 1005, None),
    (648, 'gryph-hound', 'gryph-hounds', 1226, None),
    (282, 'gutter-runner', 'gutter-runners', 706, 'skaven'),
    (545, 'hammerer', 'hammerers', 810, None),
    (420, 'hexwraith', 'hexwraiths', 1053, None),
    (449, 'icefall-yhetee', 'icefall-yhetees', 1070, None),
    (546, 'ironbreaker', 'ironbreakers', 827, None),
    (547, 'irondrake', 'irondrakes', 828, None),
    (472, 'irongut', 'ironguts', 1076, None),
    (367, 'kairic-acolyte', 'kairic-acolytes', 870, None),
    (428, 'kavalos-deathrider', 'kavalos-deathriders', 1099, None),
    (539, 'khinerai-heartrender', 'khinerai-heartrenders', 853, None),
    (540, 'khinerai-lifetaker', 'khinerai-lifetakers', 846, None),
    (473, 'leadbelcher', 'leadbelchers', 1086, None),
    (660, 'liberator', 'liberators', 1243, None),
    (548, 'longbeard', 'longbeards', 819, None),
    (492, 'loonsmasha-fanatic', 'loonsmasha-fanatics', 929, None),
    (488, 'maneater', 'maneaters', 1073, None),
    (481, 'maw-grunta-gouger', 'maw-grunta-gougers', 998, 'ironjawz'),
    (406, 'morbheg-knight', 'morbheg-knights', 902, None),
    (387, 'morghast-harbinger', 'morghast-harbingers', 1100, 'ossiarch-bonereapers'),
    (430, 'mortis-reaper', 'mortis-reapers', 1093, None),
    (291, 'myrmidesh-painbringer', 'myrmidesh-painbringers', 958, 'hedonites-of-slaanesh'),
    (423, 'myrmourn-banshee', 'myrmourn-banshees', 1068, None),
    (586, 'namarti-reaver', 'namarti-reavers', 984, None),
    (585, 'namarti-thrall', 'namarti-thralls', 978, None),
    (433, 'necropolis-stalker', 'necropolis-stalkers', 1090, None),
    (283, 'night-runner', 'night-runners', 705, 'skaven'),
    (261, 'nurgling', 'nurglings', 1040, None),
    (322, 'pestigor', 'pestigors', 1029, None),
    (330, 'plague-censer-bearer', 'plague-censer-bearers', 708, 'skaven'),
    (332, 'plague-monk', 'plague-monks', 707, 'skaven'),
    (669, 'praetor', 'praetors', 1199, None),
    (670, 'prosecutor', 'prosecutors', 1246, None),
    (671, 'protector', 'protectors', 1222, None),
    (324, 'pusgoyle-blightlord', 'pusgoyle-blightlords', 1035, None),
    (325, 'putrid-blightking', 'putrid-blightkings', 1047, None),
    (424, 'pyregheist', 'pyregheists', 1057, None),
    (617, 'raptadon-charger', 'raptadon-chargers', 1115, None),
    (618, 'raptadon-hunter', 'raptadon-hunters', 1108, None),
    (316, 'rat-ogor', 'rat-ogors', 709, 'skaven'),
    (673, 'reclusian', 'reclusians', 1221, None),
    (674, 'retributor', 'retributors', 1207, None),
    (621, 'ripperdactyl-rider', 'ripperdactyl-riders', 1114, None),
    (519, 'rockgut-troggoth', 'rockgut-troggoths', 930, None),
    (328, 'rotsword', 'rotswords', 1027, None),
    (628, 'saurus-warrior', 'saurus-warriors', 712, None),
    (454, 'savage-big-stabba', 'savage-big-stabbas', 804, 'bonesplitterz'),
    (455, 'savage-boarboy', 'savage-boarboys', 806, 'bonesplitterz'),
    (456, 'savage-boarboy-maniak', 'savage-boarboy-maniaks', 803, 'bonesplitterz'),
    (457, 'savage-orruk', 'savage-orruks', 802, 'bonesplitterz'),
    (458, 'savage-orruk-arrowboy', 'savage-orruk-arrowboys', 800, 'bonesplitterz'),
    (459, 'savage-orruk-morboy', 'savage-orruk-morboys', 801, 'bonesplitterz'),
    (675, 'sequitor', 'sequitors', 1229, None),
    (29, 'skink', 'skinks', 714, None),
    (599, 'skywarden', 'skywardens', 1002, None),
    (293, 'slaangor-fiendblood', 'slaangor-fiendbloods', 951, 'hedonites-of-slaanesh'),
    (294, 'slickblade-seeker', 'slickblade-seekers', 970, 'hedonites-of-slaanesh'),
    (329, 'sloven-knight', 'sloven-knights', 1039, None),
    (508, 'snarlfang-rider', 'snarlfang-riders', 939, None),
    (499, 'sneaky-snuffler', 'sneaky-snufflers', 917, None),
    (514, 'spider-rider', 'spider-riders', 940, None),
    (426, 'spirit-host', 'spirit-hosts', 1048, None),
    (690, 'spite-revenant', 'spite-revenants', 1258, None),
    (501, 'sporesplatta-fanatic', 'sporesplatta-fanatics', 942, None),
    (503, 'squig-hopper', 'squig-hoppers', 922, None),
    (318, 'stormfiend', 'stormfiends', 710, 'skaven'),
    (677, 'stormstrike-pallador', 'stormstrike-palladors', 1247, None),
    (510, 'sunsteala-wheela', 'sunsteala-wheelas', 944, None),
    (295, 'symbaresh-twinsoul', 'symbaresh-twinsouls', 964, 'hedonites-of-slaanesh'),
    (635, 'terradon-rider', 'terradon-riders', 1105, None),
    (691, 'tree-revenant', 'tree-revenants', 1255, None),
    (244, 'tuskgor-chariot', 'tuskgor-chariots', 758, None),
    (245, 'tzaangor', 'tzaangors', 878, None),
    (247, 'tzaangor-skyfire', 'tzaangor-skyfires', 869, 'disciples-of-tzeentch'),
    (248, 'ungor', 'ungors', 753, None),
    (249, 'ungor-raider', 'ungor-raiders', 754, None),
    (679, 'vanguard-hunter', 'vanguard-hunters', 1209, None),
    (682, 'vanquisher', 'vanquishers', 1231, None),
    (441, 'vargheist', 'vargheists', 1161, None),
    (683, 'vigilor', 'vigilors', 1242, None),
    (684, 'vindictor', 'vindictors', 1214, None),
    (600, 'vongrim-salvager', 'vongrim-salvagers', 1007, None),
    (574, 'vulkyn-flameseeker', 'vulkyn-flameseekers', 904, None),
    (343, 'warplock-jezzail', 'warplock-jezzails', 711, 'skaven'),
    (561, 'wildercorps-hunter', 'wildercorps-hunters', 831, None),
]

print(f"Processing {len(conflicts)} conflicts")

renamed = 0
errors = []

for sing_id, sing_slug, plur_slug, plur_id, new_faction in conflicts:
    c.execute("SELECT COUNT(*) FROM army_units WHERE unit_id=?", (sing_id,))
    sing_refs = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM army_units WHERE unit_id=?", (plur_id,))
    plur_refs = c.fetchone()[0]

    c.execute("SELECT id, slug, name, faction_id, image_path FROM units WHERE id=?", (sing_id,))
    sing_row = c.fetchone()
    c.execute("SELECT id, slug, name, faction_id, image_path FROM units WHERE id=?", (plur_id,))
    plur_row = c.fetchone()

    if not sing_row:
        errors.append(f"Missing sing_id={sing_id} {sing_slug}")
        continue
    if not plur_row:
        errors.append(f"Missing plur_id={plur_id} {plur_slug}")
        continue

    sing_has_img = sing_row[4] is not None
    plur_has_img = plur_row[4] is not None

    if plur_has_img and not sing_has_img:
        keep_id = plur_id
        keep_slug = plur_slug
        del_id = sing_id
        keep_img = plur_row[4]
        old_faction_id = plur_row[3]
    else:
        keep_id = sing_id
        keep_slug = plur_slug
        del_id = plur_id
        keep_img = sing_row[4]
        old_faction_id = sing_row[3]

        if keep_img:
            basename = os.path.basename(keep_img)
            ext = os.path.splitext(basename)[1]
            dir_part = os.path.dirname(keep_img)
            new_img_path = dir_part + '/' + plur_slug + ext
            old_file = BASE_IMG + keep_img
            new_file = BASE_IMG + new_img_path
            if os.path.exists(old_file) and keep_img != new_img_path:
                os.makedirs(os.path.dirname(new_file), exist_ok=True)
                shutil.copy2(old_file, new_file)
                keep_img = new_img_path
            elif not os.path.exists(old_file):
                keep_img = None

    if new_faction:
        target_faction_id = faction_map.get(new_faction, old_faction_id)
    else:
        target_faction_id = old_faction_id

    if plur_refs > 0 and del_id == plur_id:
        c.execute("UPDATE army_units SET unit_id=? WHERE unit_id=?", (keep_id, del_id))
    if sing_refs > 0 and del_id == sing_id:
        c.execute("UPDATE army_units SET unit_id=? WHERE unit_id=?", (keep_id, del_id))

    # Must delete duplicate BEFORE renaming to avoid UNIQUE constraint violation
    c.execute("DELETE FROM units WHERE id=?", (del_id,))
    c.execute("UPDATE units SET slug=?, faction_id=?, image_path=? WHERE id=?",
              (keep_slug, target_faction_id, keep_img, keep_id))

    renamed += 1

conn.commit()

print(f"Renamed/merged: {renamed}")
if errors:
    print(f"Errors: {errors}")

c.execute("""SELECT COUNT(*) FROM units u
JOIN factions f ON u.faction_id=f.id
JOIN game_systems gs ON f.game_system_id=gs.id
WHERE gs.code='aos4'""")
print(f"Post-rename AoS count: {c.fetchone()[0]}")
c.execute("SELECT COUNT(*) FROM units")
print(f"Post-rename total: {c.fetchone()[0]}")
