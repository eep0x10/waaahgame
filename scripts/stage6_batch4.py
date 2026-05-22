#!/usr/bin/env python3
"""Stage 6 batch 4: final identified canonical duplicates."""
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

    c.execute('DELETE FROM units WHERE id=?', (old_id,))
    print(f'DELETE [{old_id}] {old_slug}  ->  [{new_id}] {new_slug}')


def delete_dup_canonical_has_img(old_slug, can_slug):
    c.execute('SELECT id FROM units WHERE slug=?', (old_slug,))
    row = c.fetchone()
    if not row:
        print(f'SKIP (not found): {old_slug}')
        return
    uid = row[0]
    refs = army_refs(uid)
    if refs > 0:
        print(f'SKIP {old_slug}: {refs} army refs')
        return
    c.execute('DELETE FROM units WHERE id=?', (uid,))
    print(f'DELETE [{uid}] {old_slug} (canonical {can_slug} already has image)')


print('=== Type A: transfer image, delete old ===')
transfer_and_delete('bullgor-warrior',         'bullgors')
transfer_and_delete('valkia',                  'valkia-the-bloody')
transfer_and_delete('dreadlord',               'dreadlord-on-black-dragon')
transfer_and_delete('freeguild-marshal',        'freeguild-marshal-on-griffon')
transfer_and_delete('steam-tank-with-commander','steam-tank-commander')
transfer_and_delete('frazzlegit-shaman',        'frazzlegit-shaman-on-war-wheela')
transfer_and_delete('scuttleboss',             'scuttleboss-on-gigantic-spider')
transfer_and_delete('shoota',                  'moonclan-shootas')
transfer_and_delete('squigboss',               'squigboss-with-gnasha-squig')
transfer_and_delete('stabba',                  'moonclan-stabbas')
transfer_and_delete('endrinmaster',            'endrinmaster-with-endrinharness')

print()
print('=== Type B: canonical already has image, delete old ===')
delete_dup_canonical_has_img('thunderers', 'grundstok-thunderers')
delete_dup_canonical_has_img('fusil-major', 'fusil-major-on-ogor-warhulk')

db.commit()
print('\nDone.')
db.close()
