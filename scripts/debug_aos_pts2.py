import xml.etree.ElementTree as ET
import os

def check_file_for_pts(cat_path):
    try:
        tree = ET.parse(cat_path)
        root = tree.getroot()
    except:
        return []

    tag = root.tag
    ns = ''
    if '{' in tag:
        ns = tag.split('}')[0] + '}'

    results = []
    for se in root.iter(f'{ns}selectionEntry'):
        name = se.get('name', '')
        etype = se.get('type', '')
        if etype not in ('unit', 'model', 'upgrade'):
            continue
        direct_costs = se.find(f'{ns}costs')
        if direct_costs is not None:
            for cost in direct_costs:
                cname = cost.get('name','').lower()
                cval = float(cost.get('value','0'))
                if 'pt' in cname and cval > 0:
                    results.append((name, etype, cval))
    return results

# Check ALL AoS cat files
print("=== Scanning ALL AoS .cat files for pts > 0 on unit/model entries ===")
aos_dir = '/app/scripts/cache/bsdata/aos'
for fname in sorted(os.listdir(aos_dir)):
    if not fname.endswith('.cat') and not fname.endswith('.gst'):
        continue
    path = os.path.join(aos_dir, fname)
    results = check_file_for_pts(path)
    if results:
        print(f"\n  {fname}: {len(results)} entries with pts>0")
        for name, etype, pts in results[:5]:
            print(f"    [{etype}] '{name}' pts={pts}")

print("\n=== Also checking main .gst file ===")
gst_path = '/app/scripts/cache/bsdata/aos/Age of Sigmar 4.0.gst'
try:
    tree = ET.parse(gst_path)
    root = tree.getroot()
    tag = root.tag
    ns = ''
    if '{' in tag:
        ns = tag.split('}')[0] + '}'
    # Look at cost types defined
    for ct in root.iter(f'{ns}costType'):
        print(f"  costType: id={ct.get('id')} name={ct.get('name')}")
    # Look at shared selection entries
    for se in root.iter(f'{ns}sharedSelectionEntry'):
        name = se.get('name','')
        costs_el = se.find(f'.//{ns}costs')
        if costs_el is not None:
            for c in costs_el:
                if 'pt' in c.get('name','').lower() and float(c.get('value','0')) > 0:
                    print(f"  sharedSE '{name}' pts={c.get('value')}")
except Exception as e:
    print(f"  Error: {e}")
