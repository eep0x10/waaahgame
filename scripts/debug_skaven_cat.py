import xml.etree.ElementTree as ET
import os

def dump_cat_info(cat_path):
    print(f"\n=== {os.path.basename(cat_path)} ===")
    try:
        tree = ET.parse(cat_path)
        root = tree.getroot()
    except Exception as e:
        print(f"  Parse error: {e}")
        return

    tag = root.tag
    ns = ''
    if '{' in tag:
        ns = tag.split('}')[0] + '}'
    print(f"  root tag: {tag}, ns: '{ns}'")

    # Count selection entries
    all_se = list(root.iter(f'{ns}selectionEntry'))
    print(f"  selectionEntry count: {len(all_se)}")

    # Show first 10 entry names
    for se in all_se[:10]:
        name = se.get('name', '???')
        etype = se.get('type', '?')
        # check costs
        costs_el = se.find(f'.//{ns}costs')
        cost_val = None
        if costs_el is not None:
            for c in costs_el:
                if c.get('name','').lower() in ('pts','points','pt'):
                    cost_val = c.get('value')
                    break
        print(f"    {name} (type={etype}) pts={cost_val}")

    # Also look at entryLinks
    all_el = list(root.iter(f'{ns}entryLink'))
    print(f"  entryLink count: {len(all_el)}")

# Check main cat files
dump_cat_info('/app/scripts/cache/bsdata/aos/Skaven.cat')
dump_cat_info('/app/scripts/cache/bsdata/aos/Stormcast Eternals.cat')
dump_cat_info('/app/scripts/cache/bsdata/40k/Chaos - Chaos Daemons.cat')
