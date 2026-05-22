#!/usr/bin/env python3
"""Stage 6 batch 3: orruk-warclans, seraphon, skaventide, soulblight, slaanesh merges."""
import sqlite3, os, shutil

db = sqlite3.connect('/app/instance/waaahgame.db')
c = db.cursor()
STATIC = '/app/app/static/img/units'


def army_refs(uid):
    c.execute('SELECT COUNT(*) FROM army_units WHERE unit_id=?', (uid,))
    return c.fetchone()[0]


def transfer_and_delete(old_slug, new_slug):
    c.execute('SELECT id, image_path, faction_id FROM units WHERE slug=?', (old_slug,))
    old = c.fetchone()
    if not old:
        print(f'SKIP (not found): {old_slug}')
        return
    old_id, old_img, old_fid = old

    c.execute('SELECT id, image_path, faction_id FROM units WHERE slug=?', (new_slug,))
    new = c.fetchone()
    if not new:
        print(f'SKIP (canonical not found): {new_slug}')
        return
    new_id, new_img, new_fid = new

    refs = army_refs(old_id)
    if refs > 0:
        print(f'SKIP {old_slug}: {refs} army refs')
        return

    if old_img and not new_img:
        c.execute('SELECT slug FROM factions WHERE id=?', (new_fid,))
        new_faction = c.fetchone()[0]
        ext = os.path.splitext(old_img)[1]
        new_img_path = f'units/{new_faction}/{new_slug}{ext}'
        old_parts = old_img.replace('\\', '/').split('/')
        src_path = os.path.join(STATIC, *old_parts[1:])
        dst_dir = os.path.join(STATIC, new_faction)
        dst_path = os.path.join(dst_dir, f'{new_slug}{ext}')

        os.makedirs(dst_dir, exist_ok=True)
        if os.path.exists(src_path):
            if not os.path.exists(dst_path):
                shutil.copy2(src_path, dst_path)
                print(f'  COPY: {src_path} -> {dst_path}')
            else:
                print(f'  SKIP COPY (exists): {dst_path}')
            c.execute('UPDATE units SET image_path=? WHERE id=?', (new_img_path, new_id))
            print(f'  SET image [{new_id}] {new_slug} = {new_img_path}')
        else:
            print(f'  WARN: src not found: {src_path}')
    elif old_img and new_img:
        print(f'  Both have images - no img transfer')

    c.execute('DELETE FROM units WHERE id=?', (old_id,))
    print(f'DELETE [{old_id}] {old_slug}  ->  [{new_id}] {new_slug}')


print('=== Orruk-warclans -> ironjawz/kruleboyz ===')
# ardboy and orruk-ardboys BOTH map to ardboyz
# Only one can transfer image; delete both and the second transfer just deletes
transfer_and_delete('ardboy', 'ardboyz')
transfer_and_delete('orruk-ardboys', 'ardboyz')  # ardboyz now has image, old_img copies skipped
transfer_and_delete('orruk-brutes', 'brutes')
transfer_and_delete('orruk-warchanter', 'warchanter')
transfer_and_delete('orruk-gore-gruntas', 'gore-gruntas')
transfer_and_delete('kruleboyz-gutrippaz', 'gutrippaz')
transfer_and_delete('brute-rager', 'brute-ragerz')
transfer_and_delete('tuskboss', 'tuskboss-on-maw-grunta')
transfer_and_delete('weirdbrute-wrekka', 'weirdbrute-wrekkaz')
# maw-grunta with apostrophe in slug
transfer_and_delete("maw-grunta-with-hakkin%27-krew", 'maw-grunta-with-hakkin-krew')

print()
print('=== Seraphon ===')
transfer_and_delete('skink-oracle', 'skink-oracle-on-troglodon')
transfer_and_delete('hunters-of-huanchi', 'hunters-of-huanchi-with-dartpipes')

print()
print('=== Skaventide ===')
transfer_and_delete('screaming-bell', 'grey-seer-on-screaming-bell')
transfer_and_delete('plague-furnace', 'plague-priest-on-plague-furnace')

print()
print('=== Flesh-Eater Courts ===')
transfer_and_delete('zombie-dragon', 'abhorrant-ghoul-king-on-royal-zombie-dragon')

print()
print('=== Soulblight ===')
transfer_and_delete('wight-lord', 'wight-lord-on-skeletal-steed')

print()
print('=== Slaanesh ===')
transfer_and_delete('infernal-enrapturess', 'infernal-enrapturess-herald-of-slaanesh')
transfer_and_delete('viceleader', 'viceleader-herald-of-slaanesh')

db.commit()
print('\nDone.')
db.close()
