"""
Wave 5 AoS seed: 10 new factions (Cities of Sigmar, Daughters of Khaine,
Kharadron Overlords, Lumineth Realm-Lords, Maggotkin of Nurgle,
Slaves to Darkness, Disciples of Tzeentch, Soulblight Gravelords,
Ossiarch Bonereapers, Orruk Warclans) + bonus Gloomspite Gitz.

Hardcoded-dict style (same pattern as seed_aos_expansion.py) — idempotent.
"""

import sys
import os
import re
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

WAHAPEDIA_BASE = 'https://wahapedia.ru/aos4/factions'


def _slug(name):
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


# ---------------------------------------------------------------------------
# Unit data
# (name, pts, role, can_be_general, can_be_reinforced, model_count, keywords, companions, stats)
# ---------------------------------------------------------------------------

CITIES_UNITS = [
    ('Tahlia Vedra, Lioness of the Parch', 260, 'Hero', True, False, 1,
     ['ORDER', 'CITIES_OF_SIGMAR', 'HUMAN', 'UNIQUE', 'HERO', 'CAVALRY'],
     [{'type': 'keyword', 'value': 'ANY_CITIES_OF_SIGMAR', 'max': None}],
     {'move': '10"', 'save': '3+', 'control': '2', 'health': '8'}),
    ('Freeguild Marshal', 100, 'Hero', True, False, 1,
     ['ORDER', 'CITIES_OF_SIGMAR', 'HUMAN', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_CITIES_OF_SIGMAR', 'max': None}],
     {'move': '5"', 'save': '4+', 'control': '2', 'health': '5'}),
    ('Battlemage', 90, 'Hero', True, False, 1,
     ['ORDER', 'CITIES_OF_SIGMAR', 'HUMAN', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_CITIES_OF_SIGMAR', 'max': None}],
     {'move': '5"', 'save': '6+', 'control': '2', 'health': '5'}),
    ('Cogsmith', 80, 'Hero', True, False, 1,
     ['ORDER', 'CITIES_OF_SIGMAR', 'DUARDIN', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_CITIES_OF_SIGMAR', 'max': None}],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '4'}),
    ('Freeguild Cavaliers', 180, 'Cavalry', False, True, 5,
     ['ORDER', 'CITIES_OF_SIGMAR', 'HUMAN', 'CAVALRY', 'BATTLELINE'],
     [],
     {'move': '10"', 'save': '4+', 'control': '1', 'health': '3'}),
    ('Freeguild Steelhelms', 110, 'Infantry', False, True, 10,
     ['ORDER', 'CITIES_OF_SIGMAR', 'HUMAN', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '5+', 'control': '1', 'health': '1'}),
    ('Irondrakes', 130, 'Infantry', False, True, 10,
     ['ORDER', 'CITIES_OF_SIGMAR', 'DUARDIN', 'INFANTRY'],
     [],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '1'}),
    ('Freeguild Crossbowmen', 110, 'Infantry', False, True, 10,
     ['ORDER', 'CITIES_OF_SIGMAR', 'HUMAN', 'INFANTRY'],
     [],
     {'move': '5"', 'save': '5+', 'control': '1', 'health': '1'}),
    ('Fusil-Major on Ogor Warhulk', 220, 'Hero', True, False, 1,
     ['ORDER', 'CITIES_OF_SIGMAR', 'OGOR', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_CITIES_OF_SIGMAR', 'max': None}],
     {'move': '6"', 'save': '4+', 'control': '2', 'health': '8'}),
    ('Helblaster Volley Gun', 130, None, False, False, 1,
     ['ORDER', 'CITIES_OF_SIGMAR', 'WAR_MACHINE'],
     [],
     {'move': '3"', 'save': '5+', 'control': '0', 'health': '8'}),
    ('Steam Tank with Commander', 230, 'Hero', True, False, 1,
     ['ORDER', 'CITIES_OF_SIGMAR', 'WAR_MACHINE', 'HERO', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_CITIES_OF_SIGMAR', 'max': None}],
     {'move': '8"', 'save': '3+', 'control': '5', 'health': '14'}),
]

DOK_UNITS = [
    ('Morathi-Khaine', 680, 'Hero', True, False, 1,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'UNIQUE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_DAUGHTERS_OF_KHAINE', 'max': None}],
     {'move': '6"', 'save': '4+', 'control': '5', 'health': '12'}),
    ('Slaughter Queen', 120, 'Hero', True, False, 1,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'HERO', 'PRIEST'],
     [{'type': 'keyword', 'value': 'ANY_DAUGHTERS_OF_KHAINE', 'max': None}],
     {'move': '6"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Hag Queen', 100, 'Hero', True, False, 1,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'HERO', 'PRIEST'],
     [{'type': 'keyword', 'value': 'ANY_DAUGHTERS_OF_KHAINE', 'max': None}],
     {'move': '6"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Witch Aelves', 110, 'Infantry', False, True, 10,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '6"', 'save': '6+', 'control': '1', 'health': '1'}),
    ('Sisters of Slaughter', 110, 'Infantry', False, True, 10,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '6"', 'save': '6+', 'control': '1', 'health': '1'}),
    ('Blood Sisters', 130, 'Infantry', False, True, 5,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'MELUSAI', 'INFANTRY'],
     [],
     {'move': '6"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Blood Stalkers', 130, 'Infantry', False, True, 5,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'MELUSAI', 'INFANTRY'],
     [],
     {'move': '6"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Khinerai Lifetakers', 110, 'Infantry', False, True, 5,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'KHINERAI', 'INFANTRY'],
     [],
     {'move': '14"', 'save': '6+', 'control': '1', 'health': '2'}),
    ('Doomfire Warlocks', 130, 'Cavalry', False, True, 5,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'WIZARD', 'CAVALRY'],
     [],
     {'move': '12"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Bloodwrack Medusa', 130, 'Hero', True, False, 1,
     ['ORDER', 'DAUGHTERS_OF_KHAINE', 'AELF', 'MELUSAI', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_DAUGHTERS_OF_KHAINE', 'max': None}],
     {'move': '6"', 'save': '5+', 'control': '2', 'health': '7'}),
]

KO_UNITS = [
    ('Brokk Grungsson, Lord-Magnate of Barak-Nar', 300, 'Hero', True, False, 1,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'UNIQUE', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_KHARADRON_OVERLORDS', 'max': None}],
     {'move': '12"', 'save': '3+', 'control': '3', 'health': '8'}),
    ('Aether-Khemist', 90, 'Hero', True, False, 1,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_KHARADRON_OVERLORDS', 'max': None}],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '5'}),
    ('Aetheric Navigator', 90, 'Hero', True, False, 1,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'HERO', 'PRIEST'],
     [{'type': 'keyword', 'value': 'ANY_KHARADRON_OVERLORDS', 'max': None}],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '5'}),
    ('Arkanaut Admiral', 120, 'Hero', True, False, 1,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_KHARADRON_OVERLORDS', 'max': None}],
     {'move': '4"', 'save': '4+', 'control': '2', 'health': '6'}),
    ('Arkanaut Company', 100, 'Infantry', False, True, 10,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '1'}),
    ('Thunderers', 110, 'Infantry', False, True, 5,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'INFANTRY'],
     [],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '2'}),
    ('Grundstok Gunhauler', 160, None, False, False, 1,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'WAR_MACHINE', 'SKYVESSEL'],
     [],
     {'move': '12"', 'save': '4+', 'control': '1', 'health': '8'}),
    ('Arkanaut Ironclad', 440, 'Hero', True, False, 1,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'HERO', 'SKYVESSEL', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_KHARADRON_OVERLORDS', 'max': None}],
     {'move': '12"', 'save': '3+', 'control': '5', 'health': '18'}),
    ('Endrinmaster with Dirigible Suit', 140, 'Hero', True, False, 1,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_KHARADRON_OVERLORDS', 'max': None}],
     {'move': '12"', 'save': '3+', 'control': '2', 'health': '7'}),
    ('Skywardens', 120, 'Infantry', False, True, 3,
     ['ORDER', 'KHARADRON_OVERLORDS', 'DUARDIN', 'SKYFARER', 'INFANTRY'],
     [],
     {'move': '12"', 'save': '4+', 'control': '1', 'health': '2'}),
]

LUMINETH_UNITS = [
    ('The Light of Eltharion', 320, 'Hero', True, False, 1,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'UNIQUE', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_LUMINETH_REALM_LORDS', 'max': None}],
     {'move': '6"', 'save': '3+', 'control': '3', 'health': '8'}),
    ('Alarith Stonemage', 120, 'Hero', True, False, 1,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'ALARITH', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_LUMINETH_REALM_LORDS', 'max': None}],
     {'move': '6"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Scinari Cathallar', 130, 'Hero', True, False, 1,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'SCINARI', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_LUMINETH_REALM_LORDS', 'max': None}],
     {'move': '6"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Vanari Lord Regent', 140, 'Hero', True, False, 1,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'VANARI', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_LUMINETH_REALM_LORDS', 'max': None}],
     {'move': '6"', 'save': '3+', 'control': '2', 'health': '6'}),
    ('Vanari Auralan Wardens', 140, 'Infantry', False, True, 10,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'VANARI', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '6"', 'save': '4+', 'control': '1', 'health': '1'}),
    ('Vanari Auralan Sentinels', 180, 'Infantry', False, True, 10,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'VANARI', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '6"', 'save': '5+', 'control': '1', 'health': '1'}),
    ('Vanari Dawnriders', 200, 'Cavalry', False, True, 5,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'VANARI', 'CAVALRY', 'BATTLELINE'],
     [],
     {'move': '12"', 'save': '4+', 'control': '1', 'health': '2'}),
    ('Alarith Stoneguard', 130, 'Infantry', False, True, 5,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'ALARITH', 'INFANTRY'],
     [],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '2'}),
    ('Alarith Spirit of the Mountain', 340, 'Hero', True, False, 1,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'ALARITH', 'HERO', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_LUMINETH_REALM_LORDS', 'max': None}],
     {'move': '8"', 'save': '3+', 'control': '5', 'health': '16'}),
    ('Hurakan Windchargers', 160, 'Cavalry', False, True, 5,
     ['ORDER', 'LUMINETH_REALM_LORDS', 'AELF', 'HURAKAN', 'CAVALRY'],
     [],
     {'move': '14"', 'save': '5+', 'control': '1', 'health': '2'}),
]

NURGLE_UNITS = [
    ('Bloab Rotspawned', 260, 'Hero', True, False, 1,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'MORTAL', 'UNIQUE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_MAGGOTKIN_OF_NURGLE', 'max': None}],
     {'move': '8"', 'save': '4+', 'control': '5', 'health': '14'}),
    ('Great Unclean One', 400, 'Hero', True, False, 1,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'DAEMON', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_MAGGOTKIN_OF_NURGLE', 'max': None}],
     {'move': '5"', 'save': '4+', 'control': '5', 'health': '18'}),
    ('Lord of Plagues', 110, 'Hero', True, False, 1,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'MORTAL', 'ROTBRINGERS', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_MAGGOTKIN_OF_NURGLE', 'max': None}],
     {'move': '4"', 'save': '3+', 'control': '2', 'health': '6'}),
    ('Harbinger of Decay', 140, 'Hero', True, False, 1,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'MORTAL', 'ROTBRINGERS', 'HERO', 'PRIEST'],
     [{'type': 'keyword', 'value': 'ANY_MAGGOTKIN_OF_NURGLE', 'max': None}],
     {'move': '5"', 'save': '3+', 'control': '2', 'health': '7'}),
    ('Putrid Blightkings', 200, 'Infantry', False, True, 5,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'MORTAL', 'ROTBRINGERS', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '4'}),
    ('Plaguebearers', 130, 'Infantry', False, True, 10,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'DAEMON', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Plague Drones', 200, 'Cavalry', False, True, 3,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'DAEMON', 'CAVALRY'],
     [],
     {'move': '8"', 'save': '5+', 'control': '1', 'health': '4'}),
    ('Beasts of Nurgle', 120, None, False, True, 1,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'DAEMON'],
     [],
     {'move': '5"', 'save': '5+', 'control': '3', 'health': '8'}),
    ('Rotigus', 360, 'Hero', True, False, 1,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'DAEMON', 'UNIQUE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_MAGGOTKIN_OF_NURGLE', 'max': None}],
     {'move': '5"', 'save': '4+', 'control': '5', 'health': '18'}),
    ('Nurglings', 75, None, False, True, 3,
     ['CHAOS', 'MAGGOTKIN_OF_NURGLE', 'DAEMON', 'SUMMONABLE'],
     [],
     {'move': '5"', 'save': '5+', 'control': '1', 'health': '3'}),
]

STD_UNITS = [
    ('Archaon the Everchosen', 870, 'Hero', True, False, 1,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'UNIQUE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_SLAVES_TO_DARKNESS', 'max': None}],
     {'move': '14"', 'save': '3+', 'control': '5', 'health': '20'}),
    ('Chaos Lord on Karkadrak', 220, 'Hero', True, False, 1,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_SLAVES_TO_DARKNESS', 'max': None}],
     {'move': '10"', 'save': '3+', 'control': '2', 'health': '10'}),
    ('Chaos Sorcerer Lord', 110, 'Hero', True, False, 1,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_SLAVES_TO_DARKNESS', 'max': None}],
     {'move': '5"', 'save': '4+', 'control': '2', 'health': '6'}),
    ('Darkoath Chieftain', 80, 'Hero', True, False, 1,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'DARKOATH', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_SLAVES_TO_DARKNESS', 'max': None}],
     {'move': '5"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Chaos Warriors', 130, 'Infantry', False, True, 10,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '4+', 'control': '1', 'health': '2'}),
    ('Chaos Knights', 170, 'Cavalry', False, True, 5,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'CAVALRY', 'BATTLELINE'],
     [],
     {'move': '10"', 'save': '4+', 'control': '1', 'health': '3'}),
    ('Darkoath Marauders', 100, 'Infantry', False, True, 10,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'DARKOATH', 'INFANTRY'],
     [],
     {'move': '6"', 'save': '6+', 'control': '1', 'health': '1'}),
    ('Varanguard', 330, 'Cavalry', False, False, 3,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'CAVALRY'],
     [],
     {'move': '10"', 'save': '3+', 'control': '2', 'health': '5'}),
    ('Chaos Chosen', 200, 'Infantry', False, True, 5,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'MORTAL', 'INFANTRY'],
     [],
     {'move': '5"', 'save': '4+', 'control': '2', 'health': '3'}),
    ('Be\'lakor, the Dark Master', 360, 'Hero', True, False, 1,
     ['CHAOS', 'SLAVES_TO_DARKNESS', 'DAEMON', 'UNIQUE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_SLAVES_TO_DARKNESS', 'max': None}],
     {'move': '12"', 'save': '4+', 'control': '5', 'health': '16'}),
]

TZEENTCH_UNITS = [
    ('Kairos Fateweaver', 430, 'Hero', True, False, 1,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'DAEMON', 'UNIQUE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_DISCIPLES_OF_TZEENTCH', 'max': None}],
     {'move': '12"', 'save': '5+', 'control': '5', 'health': '14'}),
    ('Lord of Change', 360, 'Hero', True, False, 1,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'DAEMON', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_DISCIPLES_OF_TZEENTCH', 'max': None}],
     {'move': '12"', 'save': '5+', 'control': '5', 'health': '14'}),
    ('Magister', 90, 'Hero', True, False, 1,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'MORTAL', 'ARCANITE', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_DISCIPLES_OF_TZEENTCH', 'max': None}],
     {'move': '5"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Tzaangor Shaman', 120, 'Hero', True, False, 1,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'MORTAL', 'ARCANITE', 'TZAANGOR', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_DISCIPLES_OF_TZEENTCH', 'max': None}],
     {'move': '6"', 'save': '5+', 'control': '2', 'health': '6'}),
    ('Pink Horrors of Tzeentch', 120, 'Infantry', False, True, 10,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'DAEMON', 'HORROR', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Blue Horrors of Tzeentch', 100, 'Infantry', False, True, 10,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'DAEMON', 'HORROR', 'INFANTRY'],
     [],
     {'move': '5"', 'save': '5+', 'control': '1', 'health': '1'}),
    ('Tzaangors', 120, 'Infantry', False, True, 10,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'MORTAL', 'ARCANITE', 'TZAANGOR', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '6"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Kairic Acolytes', 80, 'Infantry', False, True, 10,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'MORTAL', 'ARCANITE', 'INFANTRY'],
     [],
     {'move': '6"', 'save': '6+', 'control': '1', 'health': '1'}),
    ('Flamers of Tzeentch', 140, None, False, True, 3,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'DAEMON', 'FLAMER'],
     [],
     {'move': '9"', 'save': '5+', 'control': '1', 'health': '3'}),
    ('Screamers of Tzeentch', 120, 'Cavalry', False, True, 3,
     ['CHAOS', 'DISCIPLES_OF_TZEENTCH', 'DAEMON', 'CAVALRY'],
     [],
     {'move': '16"', 'save': '5+', 'control': '1', 'health': '3'}),
]

SOULBLIGHT_UNITS = [
    ('Mannfred von Carstein, Mortarch of Night', 380, 'Hero', True, False, 1,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'UNIQUE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_SOULBLIGHT_GRAVELORDS', 'max': None}],
     {'move': '12"', 'save': '3+', 'control': '5', 'health': '16'}),
    ('Vampire Lord', 120, 'Hero', True, False, 1,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_SOULBLIGHT_GRAVELORDS', 'max': None}],
     {'move': '6"', 'save': '3+', 'control': '2', 'health': '6'}),
    ('Vampire Lord on Zombie Dragon', 320, 'Hero', True, False, 1,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'HERO', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_SOULBLIGHT_GRAVELORDS', 'max': None}],
     {'move': '12"', 'save': '3+', 'control': '5', 'health': '14'}),
    ('Necromancer', 110, 'Hero', True, False, 1,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'DEATHMAGE', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_SOULBLIGHT_GRAVELORDS', 'max': None}],
     {'move': '5"', 'save': '6+', 'control': '2', 'health': '5'}),
    ('Skeleton Warriors', 110, 'Infantry', False, True, 10,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'DEADWALKER', 'SKELETON', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '6+', 'control': '1', 'health': '1'}),
    ('Dire Wolves', 100, 'Cavalry', False, True, 10,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'DEADWALKER', 'CAVALRY', 'BATTLELINE'],
     [],
     {'move': '10"', 'save': '6+', 'control': '1', 'health': '2'}),
    ('Black Knights', 150, 'Cavalry', False, True, 5,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'DEATHRATTLE', 'CAVALRY'],
     [],
     {'move': '10"', 'save': '4+', 'control': '1', 'health': '2'}),
    ('Blood Knights', 200, 'Cavalry', False, True, 5,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'CAVALRY'],
     [],
     {'move': '10"', 'save': '3+', 'control': '2', 'health': '3'}),
    ('Zombie Dragon', 170, 'Behemoth', False, False, 1,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'MONSTER'],
     [],
     {'move': '12"', 'save': '4+', 'control': '5', 'health': '12'}),
    ('Vargheists', 140, None, False, True, 3,
     ['DEATH', 'SOULBLIGHT_GRAVELORDS', 'VAMPIRE', 'INFANTRY'],
     [],
     {'move': '12"', 'save': '5+', 'control': '1', 'health': '4'}),
]

OBR_UNITS = [
    ('Nagash, Supreme Lord of the Undead', 895, 'Hero', True, False, 1,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'HERO', 'UNIQUE', 'WIZARD', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_OSSIARCH_BONEREAPERS', 'max': None}],
     {'move': '9"', 'save': '3+', 'control': '5', 'health': '20'}),
    ('Mortisan Soulmason', 100, 'Hero', True, False, 1,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'MORTISAN', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_OSSIARCH_BONEREAPERS', 'max': None}],
     {'move': '5"', 'save': '4+', 'control': '2', 'health': '5'}),
    ('Mortisan Boneshaper', 90, 'Hero', True, False, 1,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'MORTISAN', 'HERO', 'PRIEST'],
     [{'type': 'keyword', 'value': 'ANY_OSSIARCH_BONEREAPERS', 'max': None}],
     {'move': '5"', 'save': '4+', 'control': '2', 'health': '5'}),
    ('Liege-Kavalos', 190, 'Hero', True, False, 1,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_OSSIARCH_BONEREAPERS', 'max': None}],
     {'move': '10"', 'save': '3+', 'control': '2', 'health': '8'}),
    ('Mortek Guard', 120, 'Infantry', False, True, 10,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '2'}),
    ('Kavalos Deathriders', 170, 'Cavalry', False, True, 5,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'CAVALRY', 'BATTLELINE'],
     [],
     {'move': '10"', 'save': '3+', 'control': '1', 'health': '3'}),
    ('Necropolis Stalkers', 170, 'Infantry', False, True, 3,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'INFANTRY'],
     [],
     {'move': '6"', 'save': '3+', 'control': '1', 'health': '5'}),
    ('Immortis Guard', 190, 'Infantry', False, False, 3,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'INFANTRY'],
     [],
     {'move': '4"', 'save': '3+', 'control': '2', 'health': '5'}),
    ('Gothizzar Harvester', 180, 'Behemoth', False, False, 1,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'MONSTER'],
     [],
     {'move': '6"', 'save': '3+', 'control': '5', 'health': '12'}),
    ('Mortek Crawler', 200, None, False, False, 1,
     ['DEATH', 'OSSIARCH_BONEREAPERS', 'WAR_MACHINE'],
     [],
     {'move': '4"', 'save': '4+', 'control': '0', 'health': '12'}),
]

ORRUK_UNITS = [
    ('Gordrakk, the Fist of Gork', 490, 'Hero', True, False, 1,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'UNIQUE', 'HERO', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_ORRUK_WARCLANS', 'max': None}],
     {'move': '12"', 'save': '3+', 'control': '5', 'health': '18'}),
    ('Megaboss on Maw-krusha', 420, 'Hero', True, False, 1,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'HERO', 'MONSTER'],
     [{'type': 'keyword', 'value': 'ANY_ORRUK_WARCLANS', 'max': None}],
     {'move': '12"', 'save': '3+', 'control': '5', 'health': '16'}),
    ('Orruk Warchanter', 110, 'Hero', True, False, 1,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'HERO', 'PRIEST'],
     [{'type': 'keyword', 'value': 'ANY_ORRUK_WARCLANS', 'max': None}],
     {'move': '4"', 'save': '4+', 'control': '2', 'health': '6'}),
    ('Orruk Weirdnob Shaman', 90, 'Hero', True, False, 1,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_ORRUK_WARCLANS', 'max': None}],
     {'move': '5"', 'save': '6+', 'control': '2', 'health': '5'}),
    ('Orruk Ardboys', 120, 'Infantry', False, True, 10,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '4"', 'save': '4+', 'control': '1', 'health': '2'}),
    ('Orruk Brutes', 160, 'Infantry', False, True, 5,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '4"', 'save': '4+', 'control': '2', 'health': '3'}),
    ('Savage Orruk Morboys', 140, 'Infantry', False, True, 10,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'BONESPLITTERZ', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '6+', 'control': '1', 'health': '2'}),
    ('Kruleboyz Gutrippaz', 160, 'Infantry', False, True, 10,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'KRULEBOYZ', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Swampcalla Shaman with Pot-grot', 100, 'Hero', True, False, 1,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'KRULEBOYZ', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_ORRUK_WARCLANS', 'max': None}],
     {'move': '5"', 'save': '6+', 'control': '2', 'health': '5'}),
    ('Orruk Gore-gruntas', 220, 'Cavalry', False, True, 3,
     ['DESTRUCTION', 'ORRUK_WARCLANS', 'ORRUK', 'IRONJAWZ', 'CAVALRY'],
     [],
     {'move': '9"', 'save': '4+', 'control': '2', 'health': '5'}),
]

GLOOMSPITE_UNITS = [
    ('Skragrott, the Loonking', 220, 'Hero', True, False, 1,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'GROT', 'MOONCLAN', 'UNIQUE', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_GLOOMSPITE_GITZ', 'max': None}],
     {'move': '5"', 'save': '4+', 'control': '2', 'health': '7'}),
    ('Loonboss', 70, 'Hero', True, False, 1,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'GROT', 'MOONCLAN', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_GLOOMSPITE_GITZ', 'max': None}],
     {'move': '5"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Fungoid Cave-Shaman', 75, 'Hero', True, False, 1,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'GROT', 'MOONCLAN', 'HERO', 'WIZARD'],
     [{'type': 'keyword', 'value': 'ANY_GLOOMSPITE_GITZ', 'max': None}],
     {'move': '5"', 'save': '5+', 'control': '2', 'health': '5'}),
    ('Troggboss', 130, 'Hero', True, False, 1,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'TROGGOTH', 'HERO'],
     [{'type': 'keyword', 'value': 'ANY_GLOOMSPITE_GITZ', 'max': None}],
     {'move': '6"', 'save': '4+', 'control': '2', 'health': '8'}),
    ('Moonclan Grots', 80, 'Infantry', False, True, 20,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'GROT', 'MOONCLAN', 'INFANTRY', 'BATTLELINE'],
     [],
     {'move': '5"', 'save': '6+', 'control': '1', 'health': '1'}),
    ('Squig Herd', 110, None, False, True, 6,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'SQUIG', 'CAVALRY'],
     [],
     {'move': '2D6"', 'save': '5+', 'control': '1', 'health': '2'}),
    ('Rockgut Troggoths', 140, None, False, True, 3,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'TROGGOTH'],
     [],
     {'move': '6"', 'save': '4+', 'control': '2', 'health': '6'}),
    ('Fellwater Troggoths', 150, None, False, True, 3,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'TROGGOTH'],
     [],
     {'move': '6"', 'save': '5+', 'control': '2', 'health': '7'}),
    ('Aleguzzler Gargant', 170, 'Behemoth', False, False, 1,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'GARGANT', 'MONSTER'],
     [],
     {'move': '8"', 'save': '5+', 'control': '5', 'health': '12'}),
    ('Squig Hoppers', 100, 'Cavalry', False, True, 5,
     ['DESTRUCTION', 'GLOOMSPITE_GITZ', 'SQUIG', 'CAVALRY'],
     [],
     {'move': '2D6"', 'save': '5+', 'control': '1', 'health': '2'}),
]

# ---------------------------------------------------------------------------
# Blurbs
# ---------------------------------------------------------------------------

CITIES_BLURB = (
    "From the great free cities of the Mortal Realms — Hammerhal Aqsha, Anvilgard, Excelsis and more — "
    "the Cities of Sigmar field a truly diverse host of aelves, duardin and humans united under the "
    "banner of Sigmar. Disciplined gunlines, armoured cavalry, arcane battlemages and ironclad steam "
    "engines combine into a formidable combined-arms force defending order's greatest bastions."
)

DOK_BLURB = (
    "The Daughters of Khaine worship Morathi's dark aspect through war and bloodshed. Aelven warriors "
    "of supernal skill and frightening zeal, they fight in frenzied ecstasy — growing more powerful as "
    "blood is spilled. Slaughter Queens and Hag Queens lead hosts of Witch Aelves, Melusai shapeshifters "
    "and winged Khinerai, all driven by the prophetic will of the Shadow Queen herself."
)

KO_BLURB = (
    "The Kharadron Overlords are sky-duardin mercenaries who sail the aetheric winds in great armoured "
    "airships, trading and warring in equal measure. Bound by the Kharadron Code — a complex set of "
    "contracts, rights and obligations — they bring Aethercannons, bombs, and Skyfarer infantry to bear "
    "with the precision of seasoned sky-engineers."
)

LUMINETH_BLURB = (
    "The Lumineth Realm-Lords are aelven scholars and warriors of breathtaking precision, empowered by "
    "the magic of the Hyshian sun and the elemental spirits of mountain, wind, river and zenith. "
    "Vanari spear-regiments advance with geometric order while Alarith stoneguard and Hurakan windchargers "
    "shatter the enemy's flanks, all guided by the sublime intellect of the Scinari mage-caste."
)

NURGLE_BLURB = (
    "The Maggotkin of Nurgle are the favoured children of the Plague God, bloated with pestilent gifts "
    "and filled with a horrible, loving joy. Rotbringers and Plaguebearers advance in a tide of filth, "
    "spreading Nurgle's bountiful contagions across the Mortal Realms. The more they suffer, the more "
    "they laugh — for all things return to Grandfather Nurgle in the end."
)

STD_BLURB = (
    "The Slaves to Darkness are Chaos's mortal vanguard — warriors who have pledged their souls to the "
    "Dark Gods in exchange for martial power and the promise of ascension. Chaos Warriors in black iron, "
    "howling Darkoath marauders, and the dread Varanguard ride at the will of Archaon, the Everchosen, "
    "whose shadow falls across all the Mortal Realms."
)

TZEENTCH_BLURB = (
    "The Disciples of Tzeentch are agents of change, mutation and arcane scheming. The Changer of Ways "
    "delights in flux — his daemonic Horrors split and multiply, Tzaangor warbands twist reality with "
    "aetheric flame, and Arcanite cults manipulate mortal civilisations from within. Every plan within "
    "a plan ultimately serves the incomprehensible design of the Great Conspirator."
)

SOULBLIGHT_BLURB = (
    "The Soulblight Gravelords are undead dynasties of vampiric nobility commanding legions of the "
    "risen dead. Ancient vampires of terrible power lead Deathrattle skeleton warriors, shambling "
    "Deadwalker hordes and swift Dire Wolf packs, all answering ultimately to the will of Nagash "
    "even as they scheme for their own dominion over the Mortal Realms."
)

OBR_BLURB = (
    "The Ossiarch Bonereapers are Nagash's elite military force — constructed warriors built from "
    "harvested bones and imbued with the somatic essences of fallen warriors. Disciplined and merciless, "
    "Mortek Guard advance in lockstep formations while Liege-Kavalos cavalry thunder forward, and the "
    "great Gothizzar Harvesters harvest bones from the fallen to replenish their ranks."
)

ORRUK_BLURB = (
    "The Orruk Warclans bring together the savage might of three distinct orruk cultures. The heavily "
    "armoured Ironjawz crash into the enemy like a living avalanche, the cunning and cruel Kruleboyz "
    "stalk marshlands and ambush their prey, while the Bonesplitterz revel in the primal hunt. "
    "United or fractious, orruks fight for the sheer joy of battle."
)

GLOOMSPITE_BLURB = (
    "When the Bad Moon rises, the Gloomspite Gitz pour from tunnels and caves in an endless chittering "
    "tide. Moonclan Grots, Squig herds, Troggoth monstrosities and Spiderfang arachnid-riders all follow "
    "the prophetic lunacy of Skragrott, the Loonking. They are individually weak but numberless — "
    "a gibbering avalanche of teeth, spite, and very large mushrooms."
)

ALL_FACTIONS = [
    ('cities-of-sigmar',        'Cities of Sigmar',          'Order',       CITIES_BLURB,    CITIES_UNITS),
    ('daughters-of-khaine',     'Daughters of Khaine',        'Order',       DOK_BLURB,       DOK_UNITS),
    ('kharadron-overlords',     'Kharadron Overlords',        'Order',       KO_BLURB,        KO_UNITS),
    ('lumineth-realm-lords',    'Lumineth Realm-Lords',       'Order',       LUMINETH_BLURB,  LUMINETH_UNITS),
    ('maggotkin-of-nurgle',     'Maggotkin of Nurgle',        'Chaos',       NURGLE_BLURB,    NURGLE_UNITS),
    ('slaves-to-darkness',      'Slaves to Darkness',         'Chaos',       STD_BLURB,       STD_UNITS),
    ('disciples-of-tzeentch',   'Disciples of Tzeentch',      'Chaos',       TZEENTCH_BLURB,  TZEENTCH_UNITS),
    ('soulblight-gravelords',   'Soulblight Gravelords',      'Death',       SOULBLIGHT_BLURB, SOULBLIGHT_UNITS),
    ('ossiarch-bonereapers',    'Ossiarch Bonereapers',       'Death',       OBR_BLURB,       OBR_UNITS),
    ('orruk-warclans',          'Orruk Warclans',             'Destruction', ORRUK_BLURB,     ORRUK_UNITS),
    ('gloomspite-gitz',         'Gloomspite Gitz',            'Destruction', GLOOMSPITE_BLURB, GLOOMSPITE_UNITS),
]


def seed():
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import GameSystem, Faction, Unit
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
    gs = GameSystem.query.filter_by(code='aos4').first()
    if not gs:
        log.error('GameSystem aos4 not found — run seed_aos.py first')
        return {}

    def upsert_faction(code, name, alliance, blurb):
        f = Faction.query.filter_by(slug=code).first()
        if not f:
            f = Faction(game_system_id=gs.id, code=code, slug=code,
                        name=name, grand_alliance=alliance, blurb=blurb)
            db.session.add(f)
            db.session.flush()
            log.info('Created Faction %s', code)
        else:
            f.blurb = blurb
            log.info('Faction %s exists — updated blurb', code)
        return f

    def upsert_units(faction_obj, units_data):
        count = 0
        for row in units_data:
            name, pts, role, hero, reinforceable, model_count, keywords, companions, stats = row
            unit_slug = _slug(name)
            image_path = f'img/units/{faction_obj.slug}/{unit_slug}.jpg'
            waha_name = name.replace(' ', '-')
            wahapedia_url = f'{WAHAPEDIA_BASE}/{faction_obj.slug}/{waha_name}'

            u = Unit.query.filter_by(slug=unit_slug).first()
            if not u:
                u = Unit(
                    faction_id=faction_obj.id, slug=unit_slug, name=name,
                    points_cost=pts, unit_role=role, can_be_general=hero,
                    can_be_reinforced=reinforceable, model_count=model_count,
                    stats_json=stats, weapons_json=[], abilities_json=[],
                    keywords_json=keywords, companions_json=companions,
                    wahapedia_url=wahapedia_url, image_path=image_path,
                )
                db.session.add(u)
                log.info('[+] %s', name)
            else:
                u.points_cost = pts
                u.unit_role = role
                u.model_count = model_count
                u.stats_json = stats
                u.keywords_json = keywords
                u.companions_json = companions
                u.image_path = image_path
                log.info('[~] %s (updated)', name)
            count += 1
        db.session.commit()
        return count

    results = {}
    for slug, name, alliance, blurb, units in ALL_FACTIONS:
        f = upsert_faction(slug, name, alliance, blurb)
        n = upsert_units(f, units)
        results[slug] = n
        log.info('%s: %d units', slug, n)

    total = sum(results.values())
    log.info('Wave 5 done. Total units seeded: %d', total)
    return results


if __name__ == '__main__':
    seed()
