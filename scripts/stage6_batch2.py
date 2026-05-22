#!/usr/bin/env python3
"""Stage 6 batch 2: merge more old-slug vs canonical-slug duplicates."""
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
        print(f'  Both have images, no transfer needed')

    c.execute('DELETE FROM units WHERE id=?', (old_id,))
    print(f'DELETE [{old_id}] {old_slug}  ->  [{new_id}] {new_slug}')


def delete_if_canonical_has_img(old_slug, can_slug, reason=''):
    """Canonical already has image; just delete old duplicate."""
    c.execute('SELECT id, image_path FROM units WHERE slug=?', (old_slug,))
    old = c.fetchone()
    if not old:
        print(f'SKIP (not found): {old_slug}')
        return
    old_id, old_img = old
    refs = army_refs(old_id)
    if refs > 0:
        print(f'SKIP {old_slug}: {refs} army refs')
        return
    c.execute('DELETE FROM units WHERE id=?', (old_id,))
    print(f'DELETE [{old_id}] {old_slug} (canonical {can_slug} already has image) {reason}')


print('=== Nurgle: generic heralds -> specific heralds ===')
transfer_and_delete('poxbringer', 'poxbringer-herald-of-nurgle')
transfer_and_delete('sloppity-bilepiper', 'sloppity-bilepiper-herald-of-nurgle')
transfer_and_delete('spoilpox-scrivener', 'spoilpox-scrivener-herald-of-nurgle')

print()
print('=== Slaanesh: bladebringer -> specific ===')
transfer_and_delete('bladebringer', 'bladebringer-herald-on-seeker-chariot')

print()
print('=== Ogor: generic -> specific ===')
transfer_and_delete('stonehorn', 'stonehorn-beastriders')
transfer_and_delete('thundertusk', 'thundertusk-beastriders')
transfer_and_delete('glutton', 'ogor-gluttons')
transfer_and_delete('frostlord', 'frostlord-on-stonehorn')
transfer_and_delete('huskard', 'huskard-on-stonehorn')

print()
print('=== Stormcast: generic -> specific ===')
transfer_and_delete('desolator', 'dracothian-guard-desolators')
transfer_and_delete('fulminator', 'dracothian-guard-fulminators')
transfer_and_delete('tempestor', 'dracothian-guard-tempestors')

print()
print('=== Seraphon: generic -> specific ===')
transfer_and_delete('bastiladon', 'bastiladon-with-solar-engine')
delete_if_canonical_has_img('skink-skirmisher', 'skinks', '(skinks already has image)')

print()
print('=== Fyreslayer: generic -> specific ===')
transfer_and_delete('fyreslayer-doomseeker', 'doomseeker')

print()
print('=== Nighthaunt: legion-black-coach dup ===')
delete_if_canonical_has_img('legion-black-coach', 'black-coach', '(black-coach has image)')

print()
print('=== Tzeentch arcanites: generic -> specific ===')
transfer_and_delete('curseling', 'curseling-eye-of-tzeentch')
transfer_and_delete('gaunt-summoner-of-tzeentch', 'gaunt-summoner-on-disc-of-tzeentch')

db.commit()
print('\nDone.')
db.close()
