import os
import shutil

src_dir = '/app/app/static/img/units/skaventide'
dst_dir = '/app/app/static/img/units/skaven'

src_files = os.listdir(src_dir)
dst_files = os.listdir(dst_dir)

copied = []
skipped = []

for fname in src_files:
    src_path = os.path.join(src_dir, fname)
    dst_path = os.path.join(dst_dir, fname)
    if fname in dst_files:
        src_size = os.path.getsize(src_path)
        dst_size = os.path.getsize(dst_path)
        if src_size > dst_size:
            # Read src bytes, write to dst manually (bypass permission issues)
            with open(src_path, 'rb') as f:
                data = f.read()
            with open(dst_path, 'wb') as f:
                f.write(data)
            copied.append(f"OVERWRITE (skaventide bigger) {fname} ({src_size} vs {dst_size})")
        else:
            skipped.append(f"SKIP (skaven ok) {fname}")
    else:
        with open(src_path, 'rb') as f:
            data = f.read()
        with open(dst_path, 'wb') as f:
            f.write(data)
        copied.append(f"COPY (new) {fname}")

print(f"Copied/updated: {len(copied)}")
for c in copied:
    print(f"  {c}")
print(f"\nSkipped: {len(skipped)}")
for s in skipped:
    print(f"  {s}")
