import re
import os

def extract_pts_from_html(path):
    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        html = f.read()
    # Look for PitchedBattleProfile or Points patterns
    # Pattern 1: class="PitchedBattleProfile"
    pbp = re.findall(r'class="PitchedBattleProfile"[^>]*>.*?</[^>]+>', html, re.DOTALL)
    if pbp:
        return f"PBP: {pbp[0][:200]}"
    # Pattern 2: pts directly
    pts = re.findall(r'(\d+)\s*pts', html, re.IGNORECASE)
    if pts:
        return f"pts values found: {pts[:5]}"
    # Pattern 3: Points
    p2 = re.findall(r'Points[:\s]+(\d+)', html, re.IGNORECASE)
    if p2:
        return f"Points: {p2[:5]}"
    # Just show a chunk around "pts" or "points"
    idx = html.lower().find('pts')
    if idx > 0:
        return f"near 'pts': ...{html[max(0,idx-100):idx+200]}..."
    return "No pts found"

# Check a few
print("=== Vindictors ===")
print(extract_pts_from_html('/app/scripts/_cache/wahapedia_pts/stormcast-eternals/Vindictors.html'))

print("\n=== Liberators ===")
print(extract_pts_from_html('/app/scripts/_cache/wahapedia_pts/stormcast-eternals/Liberators.html'))

print("\n=== Valkia ===")
print(extract_pts_from_html('/app/scripts/_cache/wahapedia_pts/blades-of-khorne/Valkia-The-Bloody.html'))
