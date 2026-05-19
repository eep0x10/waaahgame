import sys
import os
import re
import time
import logging
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)

UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
WIKI_UA = 'waaahgame/0.6 (educational; contact: yhextt@gmail.com) python-requests/2.31'

MIN_BYTES = 8 * 1024
MIN_W = 200
MIN_H = 200

AOS_API = 'https://ageofsigmar.fandom.com/api.php'
WH40K_API = 'https://warhammer40k.fandom.com/api.php'
WHFB_API = 'https://warhammerfantasy.fandom.com/api.php'

_SLUG_MAP = {
    # Skaven
    'skaven/night-runners': [(WHFB_API, 'Night_Runner'), (WHFB_API, 'Skaven')],
    'skaven/plague-monks': [(WHFB_API, 'Plague_Monk'), (WHFB_API, 'Skaven')],
    # Seraphon
    'seraphon/slann-starmaster': [(AOS_API, 'Slann_Starmaster'), (AOS_API, 'Seraphon')],
    'seraphon/skink-starpriest': [(AOS_API, 'Skink_Starpriest'), (AOS_API, 'Skink')],
    'seraphon/saurus-astrolith-bearer': [(AOS_API, 'Saurus_Astrolith_Bearer'), (AOS_API, 'Saurus_Guard')],
    'seraphon/aggradon-lancers': [(AOS_API, 'Seraphon'), (AOS_API, 'Aggradon_Lancers')],
    'seraphon/sunblood-pack': [(AOS_API, 'Sunblood'), (AOS_API, 'Saurus_Sunblood')],
    # 40K
    'tyranids/zoanthropes': [(WH40K_API, 'Zoanthrope')],
    'aeldari/dire-avengers': [(WH40K_API, 'Dire_Avengers')],
    'aeldari/howling-banshees': [(WH40K_API, 'Howling_Banshees')],
    'aeldari/striking-scorpions': [(WH40K_API, 'Striking_Scorpions')],
    'aeldari/fire-dragons': [(WH40K_API, 'Fire_Dragons')],
    'chaos-space-marines/legionaries': [(WH40K_API, 'Chaos_Space_Marines'), (WH40K_API, 'Legionaries')],
    # Cities of Sigmar
    'cities-of-sigmar/tahlia-vedra-lioness-of-the-parch': [(WHFB_API, 'Dark_Emissary'), (WHFB_API, 'Empire_Spearmen')],
    'cities-of-sigmar/freeguild-marshal': [(AOS_API, 'Freeguild_Marshal'), (WHFB_API, 'Empire_General')],
    'cities-of-sigmar/battlemage': [(WHFB_API, 'Dark_Emissary'), (WHFB_API, 'Mordheim')],
    'cities-of-sigmar/cogsmith': [(WHFB_API, 'Cogsmith'), (WHFB_API, 'Engineer')],
    'cities-of-sigmar/freeguild-cavaliers': [(WHFB_API, 'Empire_Swordsmen'), (WHFB_API, 'Empire_Knights')],
    'cities-of-sigmar/freeguild-steelhelms': [(WHFB_API, 'Empire_Spearmen'), (WHFB_API, 'Empire_Swordsmen')],
    'cities-of-sigmar/irondrakes': [(WHFB_API, 'Irondrakes')],
    'cities-of-sigmar/freeguild-crossbowmen': [(WHFB_API, 'Empire_Handgunners')],
    'cities-of-sigmar/fusil-major-on-ogor-warhulk': [(WHFB_API, 'Halfling'), (WHFB_API, 'Empire_Spearmen')],
    'cities-of-sigmar/helblaster-volley-gun': [(WHFB_API, 'Helblaster_Wagon'), (WHFB_API, 'Helblaster_Volley_Cannon')],
    'cities-of-sigmar/steam-tank-with-commander': [(WHFB_API, 'Steam_Tank')],
    # Daughters of Khaine
    'daughters-of-khaine/morathi-khaine': [(AOS_API, 'Morathi')],
    'daughters-of-khaine/slaughter-queen': [(AOS_API, 'Daughters_of_Khaine')],
    'daughters-of-khaine/hag-queen': [(AOS_API, 'Daughters_of_Khaine')],
    'daughters-of-khaine/witch-aelves': [(AOS_API, 'Witch_Aelves')],
    'daughters-of-khaine/sisters-of-slaughter': [(AOS_API, 'Sisters_of_Slaughter')],
    'daughters-of-khaine/blood-sisters': [(AOS_API, 'Melusai_Blood_Sisters')],
    'daughters-of-khaine/blood-stalkers': [(AOS_API, 'Melusai_Blood_Stalkers')],
    'daughters-of-khaine/khinerai-lifetakers': [(AOS_API, 'Khinerai_Lifetakers')],
    'daughters-of-khaine/doomfire-warlocks': [(AOS_API, 'Doomfire_Warlocks')],
    'daughters-of-khaine/bloodwrack-medusa': [(AOS_API, 'Daughters_of_Khaine')],
    # Kharadron Overlords
    'kharadron-overlords/brokk-grungsson-lord-magnate-of-barak-nar': [(AOS_API, 'Brokk_Grungsson')],
    'kharadron-overlords/aether-khemist': [(AOS_API, 'Aether-Khemist')],
    'kharadron-overlords/aetheric-navigator': [(AOS_API, 'Aetheric_Navigator')],
    'kharadron-overlords/arkanaut-admiral': [(AOS_API, 'Arkanaut_Admiral')],
    'kharadron-overlords/arkanaut-company': [(AOS_API, 'Kharadron_Overlords'), (AOS_API, 'Arkanaut_Company')],
    'kharadron-overlords/grundstok-gunhauler': [(AOS_API, 'Grundstok_Gunhauler')],
    'kharadron-overlords/arkanaut-ironclad': [(AOS_API, 'Arkanaut_Ironclad')],
    'kharadron-overlords/endrinmaster-with-dirigible-suit': [(AOS_API, 'Endrinmaster')],
    'kharadron-overlords/skywardens': [(AOS_API, 'Skywardens')],
    # Lumineth Realm-Lords (use High Elf WHFB pages as visual proxies)
    'lumineth-realm-lords/the-light-of-eltharion': [(WHFB_API, 'High_Elves'), (AOS_API, 'Eltharion')],
    'lumineth-realm-lords/alarith-stonemage': [(WHFB_API, 'High_Elf_Mage')],
    'lumineth-realm-lords/scinari-cathallar': [(WHFB_API, 'High_Elf_Mage')],
    'lumineth-realm-lords/vanari-lord-regent': [(WHFB_API, 'High_Elves')],
    'lumineth-realm-lords/vanari-auralan-wardens': [(WHFB_API, 'Lothern_Sea_Guard'), (WHFB_API, 'White_Lions')],
    'lumineth-realm-lords/vanari-auralan-sentinels': [(WHFB_API, 'Lothern_Sea_Guard')],
    'lumineth-realm-lords/vanari-dawnriders': [(WHFB_API, 'Dragon_Princes'), (WHFB_API, 'Silver_Helms')],
    'lumineth-realm-lords/alarith-stoneguard': [(WHFB_API, 'White_Lions')],
    'lumineth-realm-lords/alarith-spirit-of-the-mountain': [(WHFB_API, 'High_Elves')],
    'lumineth-realm-lords/hurakan-windchargers': [(WHFB_API, 'Silver_Helms'), (WHFB_API, 'Dragon_Princes')],
    # Maggotkin of Nurgle
    'maggotkin-of-nurgle/bloab-rotspawned': [(AOS_API, 'Bloab_Rotspawned')],
    'maggotkin-of-nurgle/great-unclean-one': [(WH40K_API, 'Great_Unclean_One'), (WHFB_API, 'Great_Unclean_One')],
    'maggotkin-of-nurgle/lord-of-plagues': [(WHFB_API, 'Nurgle'), (WH40K_API, 'Nurgle')],
    'maggotkin-of-nurgle/harbinger-of-decay': [(WHFB_API, 'Nurgle'), (WH40K_API, 'Nurgle')],
    'maggotkin-of-nurgle/putrid-blightkings': [(AOS_API, 'Putrid_Blightkings')],
    'maggotkin-of-nurgle/plaguebearers': [(WHFB_API, 'Plaguebearers'), (WH40K_API, 'Plaguebearer')],
    'maggotkin-of-nurgle/plague-drones': [(WH40K_API, 'Plague_Drone'), (WHFB_API, 'Plague_Drone_of_Nurgle')],
    'maggotkin-of-nurgle/beasts-of-nurgle': [(WH40K_API, 'Beast_of_Nurgle'), (WHFB_API, 'Beast_of_Nurgle')],
    'maggotkin-of-nurgle/rotigus': [(WH40K_API, 'Rotigus'), (AOS_API, 'Rotigus')],
    'maggotkin-of-nurgle/nurglings': [(WHFB_API, 'Nurglings'), (WH40K_API, 'Nurgling')],
    # Slaves to Darkness
    'slaves-to-darkness/archaon-the-everchosen': [(AOS_API, 'Archaon')],
    'slaves-to-darkness/chaos-lord-on-karkadrak': [(WHFB_API, 'Chaos_Lord'), (WH40K_API, 'Chaos_Lord')],
    'slaves-to-darkness/chaos-sorcerer-lord': [(WHFB_API, 'Chaos_Sorcerer'), (WH40K_API, 'Chaos_Sorcerer')],
    'slaves-to-darkness/darkoath-chieftain': [(WHFB_API, 'Chaos_Marauder'), (WHFB_API, 'Dark_Emissary')],
    'slaves-to-darkness/chaos-warriors': [(WHFB_API, 'Chaos_Warriors'), (AOS_API, 'Chaos_Warriors')],
    'slaves-to-darkness/chaos-knights': [(WHFB_API, 'Chaos_Knights')],
    'slaves-to-darkness/darkoath-marauders': [(WHFB_API, 'Chaos_Marauder'), (WHFB_API, 'Dark_Emissary')],
    'slaves-to-darkness/varanguard': [(AOS_API, 'Varanguard'), (WHFB_API, 'Chaos_Knights')],
    'slaves-to-darkness/chaos-chosen': [(WHFB_API, 'Chaos_Chosen'), (AOS_API, 'Slaves_to_Darkness')],
    # Disciples of Tzeentch
    'disciples-of-tzeentch/kairos-fateweaver': [(WHFB_API, 'Kairos_Fateweaver'), (WH40K_API, 'Kairos_Fateweaver')],
    'disciples-of-tzeentch/lord-of-change': [(WHFB_API, 'Lord_of_Change'), (WH40K_API, 'Lord_of_Change_(Tzeentch)'), (WH40K_API, 'Lord_of_Change')],
    'disciples-of-tzeentch/magister': [(WHFB_API, 'Magister'), (AOS_API, 'Disciples_of_Tzeentch')],
    'disciples-of-tzeentch/tzaangor-shaman': [(WHFB_API, 'Tzaangors'), (AOS_API, 'Tzaangors')],
    'disciples-of-tzeentch/pink-horrors-of-tzeentch': [(WHFB_API, 'Pink_Horror'), (AOS_API, 'Disciples_of_Tzeentch')],
    'disciples-of-tzeentch/blue-horrors-of-tzeentch': [(WHFB_API, 'Pink_Horror'), (AOS_API, 'Disciples_of_Tzeentch')],
    'disciples-of-tzeentch/tzaangors': [(WHFB_API, 'Tzaangors'), (AOS_API, 'Tzaangors')],
    'disciples-of-tzeentch/kairic-acolytes': [(AOS_API, 'Disciples_of_Tzeentch')],
    'disciples-of-tzeentch/flamers-of-tzeentch': [(WHFB_API, 'Flamers'), (WH40K_API, 'Flamer')],
    'disciples-of-tzeentch/screamers-of-tzeentch': [(WH40K_API, 'Screamer'), (WHFB_API, 'Screamer_of_Tzeentch')],
    # Soulblight Gravelords
    'soulblight-gravelords/mannfred-von-carstein-mortarch-of-night': [(WHFB_API, 'Mannfred_von_Carstein')],
    'soulblight-gravelords/vampire-lord': [(WHFB_API, 'Vampire_Lord')],
    'soulblight-gravelords/vampire-lord-on-zombie-dragon': [(WHFB_API, 'Zombie_Dragon'), (WHFB_API, 'Vampire_Lord')],
    'soulblight-gravelords/necromancer': [(WHFB_API, 'Necromancer')],
    'soulblight-gravelords/dire-wolves': [(WHFB_API, 'Dire_Wolves')],
    'soulblight-gravelords/blood-knights': [(WH40K_API, 'Blood_Knights'), (WHFB_API, 'Blood_Knights')],
    'soulblight-gravelords/zombie-dragon': [(WHFB_API, 'Zombie_Dragon')],
    'soulblight-gravelords/vargheists': [(WHFB_API, 'Vargheist')],
    # Ossiarch Bonereapers
    'ossiarch-bonereapers/nagash-supreme-lord-of-the-undead': [(WHFB_API, 'Nagash')],
    'ossiarch-bonereapers/mortisan-soulmason': [(WHFB_API, 'Liche_Priest'), (WHFB_API, 'Undead')],
    'ossiarch-bonereapers/mortisan-boneshaper': [(WHFB_API, 'Liche_Priest'), (WHFB_API, 'Undead')],
    'ossiarch-bonereapers/liege-kavalos': [(WHFB_API, 'Undead'), (WHFB_API, 'Skeleton')],
    'ossiarch-bonereapers/mortek-guard': [(WHFB_API, 'Skeleton'), (WHFB_API, 'Grave_Guard')],
    'ossiarch-bonereapers/kavalos-deathriders': [(WHFB_API, 'Undead'), (WHFB_API, 'Skeleton')],
    'ossiarch-bonereapers/necropolis-stalkers': [(WHFB_API, 'Ushabti'), (WHFB_API, 'Undead')],
    'ossiarch-bonereapers/immortis-guard': [(WHFB_API, 'Ushabti'), (WHFB_API, 'Undead')],
    'ossiarch-bonereapers/gothizzar-harvester': [(WHFB_API, 'Ushabti'), (WHFB_API, 'Undead')],
    'ossiarch-bonereapers/mortek-crawler': [(WHFB_API, 'Skeleton'), (WHFB_API, 'Undead')],
    # Orruk Warclans
    'orruk-warclans/gordrakk-the-fist-of-gork': [(AOS_API, 'Gordrakk')],
    'orruk-warclans/megaboss-on-maw-krusha': [(AOS_API, 'Megaboss_on_Maw-krusha'), (AOS_API, 'Maw-krusha')],
    'orruk-warclans/orruk-warchanter': [(AOS_API, 'Warchanter')],
    'orruk-warclans/orruk-weirdnob-shaman': [(AOS_API, 'Weirdnob_Shaman')],
    'orruk-warclans/orruk-ardboys': [(WHFB_API, 'Black_Orc'), (AOS_API, 'Ironjawz')],
    'orruk-warclans/orruk-brutes': [(AOS_API, 'Ironjawz'), (WHFB_API, 'Black_Orc')],
    'orruk-warclans/savage-orruk-morboys': [(WHFB_API, 'Savage_Orcs'), (AOS_API, 'Orruk_Warclans')],
    'orruk-warclans/kruleboyz-gutrippaz': [(AOS_API, 'Ironjawz'), (WHFB_API, 'Black_Orc')],
    'orruk-warclans/swampcalla-shaman-with-pot-grot': [(WHFB_API, 'Goblin_Big_Boss'), (WHFB_API, 'Goblin')],
    'orruk-warclans/orruk-gore-gruntas': [(WHFB_API, 'Orc_Boar_Boyz'), (AOS_API, 'Ironjawz')],
    # Gloomspite Gitz
    'gloomspite-gitz/skragrott-the-loonking': [(WHFB_API, 'Goblin_Big_Boss'), (WHFB_API, 'Goblin')],
    'gloomspite-gitz/loonboss': [(WHFB_API, 'Goblin_Big_Boss'), (WHFB_API, 'Goblin')],
    'gloomspite-gitz/fungoid-cave-shaman': [(WHFB_API, 'Goblin'), (WHFB_API, 'Night_Goblin_Fanatic')],
    'gloomspite-gitz/troggboss': [(WHFB_API, 'Troll'), (WHFB_API, 'Goblin')],
    'gloomspite-gitz/moonclan-grots': [(WHFB_API, 'Night_Goblin'), (AOS_API, 'Gloomspite_Gitz')],
    'gloomspite-gitz/squig-herd': [(WHFB_API, 'Squig_Herd'), (AOS_API, 'Gloomspite_Gitz')],
    'gloomspite-gitz/rockgut-troggoths': [(WHFB_API, 'Troll')],
    'gloomspite-gitz/fellwater-troggoths': [(WHFB_API, 'Troll')],
    'gloomspite-gitz/aleguzzler-gargant': [(AOS_API, 'Aleguzzler_Gargant')],
    'gloomspite-gitz/squig-hoppers': [(WHFB_API, 'Cave_Squig'), (WHFB_API, 'Night_Goblin_Fanatic')],
}

_FACTION_FALLBACK_PAGES = {
    'daughters-of-khaine': (AOS_API, 'Daughters_of_Khaine'),
    'kharadron-overlords': (AOS_API, 'Kharadron_Overlords'),
    'lumineth-realm-lords': (AOS_API, 'Lumineth_Realm-lords'),
    'maggotkin-of-nurgle': (AOS_API, 'Maggotkin_of_Nurgle'),
    'slaves-to-darkness': (AOS_API, 'Slaves_to_Darkness'),
    'disciples-of-tzeentch': (AOS_API, 'Disciples_of_Tzeentch'),
    'ossiarch-bonereapers': (AOS_API, 'Ossiarch_Bonereapers'),
    'orruk-warclans': (AOS_API, 'Orruk_Warclans'),
    'gloomspite-gitz': (AOS_API, 'Gloomspite_Gitz'),
    'seraphon': (AOS_API, 'Seraphon'),
    'cities-of-sigmar': (AOS_API, 'Cities_of_Sigmar'),
    'soulblight-gravelords': (AOS_API, 'Soulblight_Gravelords'),
}

_SEEN_FACTION_THUMBS = {}

# These units have unreliable/tiny thumbnails on their wiki pages;
# skip thumbnail and go straight to images-list.
_IMAGES_ONLY_SLUGS = {
    'tyranids/zoanthropes',
    'aeldari/dire-avengers',
    'aeldari/howling-banshees',
    'aeldari/striking-scorpions',
    'aeldari/fire-dragons',
    'disciples-of-tzeentch/lord-of-change',
    'cities-of-sigmar/freeguild-crossbowmen',
    'cities-of-sigmar/freeguild-cavaliers',
}


def _head_check_image(url, session):
    """HEAD-check a URL; return False if Content-Type is video/* (YouTube embeds)."""
    try:
        r = session.head(url, timeout=8, allow_redirects=True)
        ct = r.headers.get('Content-Type', '')
        if ct.startswith('video/'):
            return False
        return True
    except Exception:
        return True  # assume OK if head fails


def _get_fandom_thumbnail(api, slug, session):
    url = (api + '?action=query&titles=' + __import__('requests').utils.quote(slug)
           + '&prop=pageimages&piprop=thumbnail&pithumbsize=800&format=json')
    try:
        r = session.get(url, timeout=15)
        time.sleep(0.3)
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            if str(pid) == '-1':
                return None, 'missing'
            thumb = page.get('thumbnail', {})
            src = thumb.get('source', '')
            w = thumb.get('width', 0)
            h = thumb.get('height', 0)
            if src and w >= MIN_W and h >= MIN_H:
                # Extra check: reject YouTube video embeds
                if not _head_check_image(src, session):
                    return None, 'no_thumb'
                return src, 'thumb'
            if src:
                return None, 'thumb_small'
            return None, 'no_thumb'
    except Exception as exc:
        log.debug('Fandom API error %s/%s: %s', api, slug, exc)
    return None, 'error'


def _quick_size_ok(url, session):
    """Download URL and check it meets minimum size/dimension thresholds."""
    try:
        from PIL import Image
        r = session.get(url, timeout=20)
        if r.status_code != 200:
            return False
        ct = r.headers.get('Content-Type', '')
        if ct.startswith('video/'):
            return False
        raw = r.content
        if len(raw) < MIN_BYTES:
            return False
        img = Image.open(io.BytesIO(raw)).convert('RGB')
        return img.width >= MIN_W and img.height >= MIN_H
    except Exception:
        return False


def _get_fandom_images_and_resolve(api, slug, unit_name, session):
    url = (api + '?action=query&titles=' + __import__('requests').utils.quote(slug)
           + '&prop=images&imlimit=20&format=json')
    try:
        r = session.get(url, timeout=15)
        time.sleep(0.3)
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            if str(pid) == '-1':
                return None
            imgs = page.get('images', [])
            photo_imgs = [i['title'] for i in imgs
                          if any(i['title'].lower().endswith(e)
                                 for e in ['.jpg', '.jpeg', '.png', '.webp'])]
            unit_tokens = set(re.sub(r'[^a-z ]', ' ', unit_name.lower()).split())
            skip = {'logo', 'icon', 'banner', 'symbol', 'faction', 'map', 'flag', 'screenshot', 'background', 'artwork', 'teaser', 'interview', 'trailer', 'rune', 'wargear', 'shrine', 'total-warhammer', 'total warhammer'}
            scored = []
            for f in photo_imgs:
                fl = f.lower()
                if any(kw in fl for kw in skip):
                    continue
                # Split camelCase before lowercasing for token matching
                fl_split = re.sub(r'([a-z])([A-Z])', r'\1 \2', f).lower()
                ftokens = set(re.sub(r'[^a-z ]', ' ', fl_split).split())
                score = len(unit_tokens & ftokens)
                scored.append((score, f))
            # Sort by score desc, but always try all non-skip images (score >= 0)
            scored.sort(key=lambda x: -x[0])
            for score, file_title in scored[:5]:
                resolved = _resolve_fandom_image_file(api, file_title, session)
                if resolved and _quick_size_ok(resolved, session):
                    return resolved
    except Exception as exc:
        log.debug('Fandom images list error: %s', exc)
    return None


def _resolve_fandom_image_file(api, file_title, session):
    url = (api + '?action=query&titles=' + __import__('requests').utils.quote(file_title)
           + '&prop=imageinfo&iiprop=url&format=json')
    try:
        r = session.get(url, timeout=15)
        time.sleep(0.2)
        data = r.json()
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            for info in page.get('imageinfo', []):
                img_url = info.get('url', '')
                if img_url and img_url.startswith('http'):
                    return img_url
    except Exception as exc:
        log.debug('Fandom imageinfo error: %s', exc)
    return None


def _find_image(faction_slug, unit_slug, unit_name, session):
    unit_key = f'{faction_slug}/{unit_slug}'
    candidates = _SLUG_MAP.get(unit_key)
    if not candidates:
        api = AOS_API
        if faction_slug in ('tyranids', 'aeldari', 'chaos-space-marines', 'space-marines', 'necrons'):
            api = WH40K_API
        slug = unit_name.replace(' ', '_').replace(',', '').replace("'", '')
        candidates = [(api, slug)]

    images_only = unit_key in _IMAGES_ONLY_SLUGS

    for api, slug in candidates:
        if not images_only:
            img_url, status = _get_fandom_thumbnail(api, slug, session)
            if img_url:
                if img_url not in _SEEN_FACTION_THUMBS.values():
                    return img_url, f'thumb:{slug}'
                else:
                    log.debug('Duplicate faction thumb, skipping for %s', unit_key)
            if status not in ('no_thumb', 'thumb_small'):
                continue  # missing/error → try next candidate
        # no_thumb, thumb_small, or images_only mode → try images list
        resolved = _get_fandom_images_and_resolve(api, slug, unit_name, session)
        if resolved:
            return resolved, f'img:{slug}'

    return None, 'no_match'


def _download_and_save(img_url, dest_path, session):
    try:
        from PIL import Image
        resp = session.get(img_url, timeout=30, stream=True, headers={'User-Agent': UA})
        time.sleep(0.5)
        if resp.status_code != 200:
            return False, f'http_{resp.status_code}'
        ct = resp.headers.get('Content-Type', '')
        if not ct.startswith('image/') and not img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            return False, 'not_image'
        raw = resp.content
        if len(raw) < MIN_BYTES:
            return False, f'too_small_{len(raw)}'
        img = Image.open(io.BytesIO(raw)).convert('RGB')
        if img.width < MIN_W or img.height < MIN_H:
            return False, f'dims_{img.width}x{img.height}'
        max_side = 800
        if img.width > max_side or img.height > max_side:
            ratio = max_side / max(img.width, img.height)
            img = img.resize((int(img.width * ratio), int(img.height * ratio)), Image.LANCZOS)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.save(dest_path, 'JPEG', quality=85, optimize=True)
        return True, 'ok'
    except Exception as exc:
        return False, f'exception:{exc}'


def run():
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_run(db, Faction, Unit)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_run(db, Faction, Unit)


def _do_run(db, Faction, Unit):
    import requests as req

    session = req.Session()
    session.headers.update({'User-Agent': WIKI_UA})

    all_svg_units = Unit.query.join(Faction).filter(Unit.image_path.like('%.svg')).all()
    log.info('Total SVG units in DB: %d', len(all_svg_units))

    db_fixed = 0
    to_scrape = []

    for unit in all_svg_units:
        faction_slug = unit.faction.slug
        unit_slug = unit.slug
        jpg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.jpg')
        if os.path.exists(jpg_abs) and os.path.getsize(jpg_abs) >= MIN_BYTES:
            unit.image_path = f'img/units/{faction_slug}/{unit_slug}.jpg'
            db.session.commit()
            svg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.svg')
            if os.path.exists(svg_abs):
                os.remove(svg_abs)
            log.info('[DB_FIX] %s/%s', faction_slug, unit_slug)
            db_fixed += 1
        else:
            to_scrape.append(unit)

    log.info('DB-fixed: %d. Need scraping: %d', db_fixed, len(to_scrape))

    rescued = 0
    no_match = 0
    failed_dl = 0
    sample_urls = []

    for idx, unit in enumerate(to_scrape, 1):
        faction_slug = unit.faction.slug
        unit_slug = unit.slug
        jpg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.jpg')
        jpg_rel = f'img/units/{faction_slug}/{unit_slug}.jpg'
        svg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.svg')

        print(f'[{idx}/{len(to_scrape)}] {faction_slug}/{unit_slug}...', end=' ', flush=True)

        img_url, strategy = _find_image(faction_slug, unit_slug, unit.name, session)

        if not img_url:
            print('no_match')
            no_match += 1
            continue

        ok, reason = _download_and_save(img_url, jpg_abs, session)
        if ok:
            file_size = os.path.getsize(jpg_abs)
            print(f'OK ({file_size // 1024}KB) [{strategy}]')
            unit.image_path = jpg_rel
            db.session.commit()
            if os.path.exists(svg_abs):
                os.remove(svg_abs)
            rescued += 1
            if len(sample_urls) < 3:
                sample_urls.append(img_url)
        else:
            print(f'FAIL:{reason}')
            failed_dl += 1

    total = len(all_svg_units)
    remaining_svg = Unit.query.filter(Unit.image_path.like('%.svg')).count()

    print(f'\n=== Wave 6 Summary ===')
    print(f'Total SVG at start: {total}')
    print(f'DB-fixed (jpg existed): {db_fixed}')
    print(f'Scraped+rescued: {rescued}')
    print(f'No match: {no_match}')
    print(f'Failed download: {failed_dl}')
    print(f'Remaining SVG in DB: {remaining_svg}')
    if sample_urls:
        print(f'\nSample rescued image URLs:')
        for u in sample_urls:
            print(f'  {u}')

    return {
        'total_svg': total,
        'db_fixed': db_fixed,
        'rescued': rescued,
        'no_match': no_match,
        'failed_dl': failed_dl,
        'remaining_svg': remaining_svg,
        'sample_urls': sample_urls,
    }


if __name__ == '__main__':
    run()
