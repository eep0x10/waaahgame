#!/usr/bin/env python3
"""Stage 6: Merge idoneth old-slugs to canonical, clean up tzeentch, delete no-image stubs."""
import sqlite3, os, shutil

db = sqlite3.connect('/app/instance/waaahgame.db')
c = db.cursor()
STATIC = '/app/app/static/img/units'


def army_refs(uid):
    c.execute('SELECT COUNT(*) FROM army_units WHERE unit_id=?', (uid,))
    return c.fetchone()[0]


def transfer_and_delete(old_slug, new_slug):
    """Transfer image from old slug to new slug row, delete old row."""
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
        # Get canonical faction slug
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
    print(f'DELETE [{old_id}] {old_slug} -> [{new_id}] {new_slug}')


def delete_stub(slug, reason):
    """Delete a no-image, no-army-ref stub."""
    c.execute('SELECT id, image_path FROM units WHERE slug=?', (slug,))
    row = c.fetchone()
    if not row:
        print(f'SKIP (not found): {slug}')
        return
    uid, img = row
    refs = army_refs(uid)
    if refs > 0:
        print(f'SKIP {slug}: {refs} army refs')
        return
    if img:
        print(f'SKIP {slug}: has image {img}, not a stub')
        return
    c.execute('DELETE FROM units WHERE id=?', (uid,))
    print(f'DELETE STUB [{uid}] {slug} ({reason})')


print('=== Idoneth merges ===')
transfer_and_delete('akhelian-guard', 'akhelian-morrsarr-guard')
transfer_and_delete('soulrender', 'isharann-soulrender')
transfer_and_delete('soulscryrer', 'isharann-soulscryer')   # note typo in old slug
transfer_and_delete('tidecaster', 'isharann-tidecaster')
transfer_and_delete('eidolon-of-mathlann', 'eidolon-of-mathlann-aspect-of-the-sea')
transfer_and_delete('ikon', 'ikon-of-the-sea')

print()
print('=== Tzeentch merges ===')
# burning-chariot (no img) -> burning-chariot-of-tzeentch (has img). Just delete stub.
delete_stub('burning-chariot', 'dup of burning-chariot-of-tzeentch which has image')
# herald-of-tzeentch (has img) -> changecaster-herald-of-tzeentch (no img)
transfer_and_delete('herald-of-tzeentch', 'changecaster-herald-of-tzeentch')
# blue-horrors-of-tzeentch (img) + brimstone-horrors-of-tzeentch (img) -> blue-horrors-and-brimstone-horrors (no img)
# Use blue-horrors image for the combined unit; delete both old
transfer_and_delete('blue-horrors-of-tzeentch', 'blue-horrors-and-brimstone-horrors')
# brimstone is now just a duplicate of the combined canonical - delete
c.execute('SELECT id FROM units WHERE slug=?', ('brimstone-horrors-of-tzeentch',))
row = c.fetchone()
if row:
    refs = army_refs(row[0])
    if refs == 0:
        c.execute('DELETE FROM units WHERE id=?', (row[0],))
        print(f'DELETE [{row[0]}] brimstone-horrors-of-tzeentch (combined into blue-horrors-and-brimstone-horrors)')

print()
print('=== Delete no-image stubs ===')
# These are pre-canonical placeholders: no image, no army refs, canonical entry exists separately
stubs = [
    ('disc-of-tzeentch', 'not in canonical, old placeholder'),
    ('herald-of-nurgle', 'canonical has specific herald variants instead'),
    ('ethereal-steed', 'not in canonical'),
    ('beastrider', 'canonical has stonehorn-beastriders/thundertusk-beastriders'),
    ('grot-scuttling', 'not in canonical'),
    ('chaos-lord-aos', 'workaround slug, canonical chaos-lord is 40K-only in DB'),
    ('karkadrak', 'canonical has chaos-lord-on-karkadrak instead'),
    ('tzeentch-sorcerer-lord', 'not in canonical, old placeholder'),
]
for slug, reason in stubs:
    delete_stub(slug, reason)

db.commit()
print('\nDone.')
db.close()
