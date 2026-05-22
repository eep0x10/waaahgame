import xml.etree.ElementTree as ET
import os

def sample_unit_points(cat_path, search_names, label=""):
    print(f"\n=== {label}: {os.path.basename(cat_path)} ===")
    try:
        tree = ET.parse(cat_path)
        root = tree.getroot()
    except Exception as e:
        print(f"  Parse error: {e}")
        return

    # Handle namespace
    ns = ''
    tag = root.tag
    if '{' in tag:
        ns = tag.split('}')[0] + '}'

    def find_costs(elem):
        costs = []
        for costs_el in elem.findall(f'.//{ns}costs'):
            for cost in costs_el.findall(f'{ns}cost'):
                name = cost.get('name', '')
                val = cost.get('value', '0')
                if name.lower() in ('pts', 'points', 'pt'):
                    costs.append(float(val))
        return costs

    # Try to find selectionEntry elements that match search names
    found = []
    for se in root.iter(f'{ns}selectionEntry'):
        entry_name = se.get('name', '')
        for sname in search_names:
            if sname.lower() in entry_name.lower():
                costs = find_costs(se)
                found.append((entry_name, costs, se.get('type', '?')))
                # Also show raw XML of first <costs> element
                costs_el = se.find(f'.//{ns}costs')
                if costs_el is not None:
                    children = list(costs_el)
                    for child in children[:3]:
                        print(f"  RAW: {child.tag} attrs={child.attrib}")

    if found:
        for name, costs, etype in found:
            print(f"  Entry: '{name}' type={etype} pts={costs}")
    else:
        print(f"  Not found: {search_names}")

# AoS samples
aos_base = '/app/scripts/cache/bsdata/aos'
sample_unit_points(
    os.path.join(aos_base, 'Skaven.cat'),
    ['Stormvermin', 'Grey Seer', 'Clawlord'],
    'AoS Skaven'
)
sample_unit_points(
    os.path.join(aos_base, 'Stormcast Eternals.cat'),
    ['Vindictors', 'Liberators'],
    'AoS Stormcast'
)
sample_unit_points(
    os.path.join(aos_base, 'Blades of Khorne.cat'),
    ['Bloodthirster'],
    'AoS BoK'
)

# 40K samples
k40_base = '/app/scripts/cache/bsdata/40k'
sample_unit_points(
    os.path.join(k40_base, 'Chaos - Chaos Daemons.cat'),
    ['Bloodletters', 'Bloodcrushers', 'Pink Horrors'],
    '40K Daemons'
)
sample_unit_points(
    os.path.join(k40_base, 'Imperium - Adeptus Custodes.cat'),
    ['Custodian Guard'],
    '40K Custodes'
)
