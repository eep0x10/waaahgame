import re

# Check if PitchedBattleProfile exists in any cached HTML
import os

cache_dir = '/app/scripts/_cache/wahapedia_pts'
found_pbp = 0
total_files = 0

for faction in os.listdir(cache_dir):
    faction_dir = os.path.join(cache_dir, faction)
    if not os.path.isdir(faction_dir):
        continue
    for fname in os.listdir(faction_dir):
        if not fname.endswith('.html'):
            continue
        path = os.path.join(faction_dir, fname)
        total_files += 1
        try:
            with open(path, 'rb') as f:
                content = f.read()
            text = content.decode('utf-8', errors='replace')
            if 'PitchedBattleProfile' in text:
                found_pbp += 1
                # Extract and show
                m = re.search(r'PitchedBattleProfile.*?Points\s*:\s*(\d+)', text, re.DOTALL)
                if m:
                    print(f"  {faction}/{fname}: pts={m.group(1)}")
        except:
            pass

print(f"\nTotal HTML files: {total_files}")
print(f"Files with PitchedBattleProfile: {found_pbp}")

# Check size of a few files to see if they have real content
print("\n=== File sizes (sample) ===")
for faction in list(os.listdir(cache_dir))[:3]:
    faction_dir = os.path.join(cache_dir, faction)
    if not os.path.isdir(faction_dir):
        continue
    for fname in list(os.listdir(faction_dir))[:3]:
        if not fname.endswith('.html'):
            continue
        path = os.path.join(faction_dir, fname)
        size = os.path.getsize(path)
        print(f"  {faction}/{fname}: {size} bytes")
