import xml.etree.ElementTree as ET
import os

def dump_units_with_pts(cat_path, show_count=20):
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

    all_se = list(root.iter(f'{ns}selectionEntry'))
    unit_type = []
    for se in all_se:
        etype = se.get('type', '')
        if etype == 'unit':
            name = se.get('name', '???')
            # Find direct costs
            cost_val = None
            costs_el = se.find(f'{ns}costs')
            if costs_el is None:
                # Try nested
                costs_el = se.find(f'.//{ns}costs')
            if costs_el is not None:
                for c in costs_el:
                    if c.get('name','').lower() in ('pts','points','pt'):
                        cost_val = c.get('value')
                        break
            unit_type.append((name, cost_val))

    print(f"  unit entries: {len(unit_type)}")
    for name, pts in unit_type[:show_count]:
        print(f"    '{name}' pts={pts}")

    # Also show entryLinks targeting this
    all_el = list(root.iter(f'{ns}entryLink'))
    print(f"  entryLink count: {len(all_el)}")
    for el in all_el[:10]:
        name = el.get('name', el.get('id','?'))
        print(f"    entryLink name={name}")

dump_units_with_pts('/app/scripts/cache/bsdata/aos/Skaven - Library.cat')
dump_units_with_pts('/app/scripts/cache/bsdata/aos/Stormcast Eternals - Library.cat', 15)
dump_units_with_pts('/app/scripts/cache/bsdata/40k/Chaos - Chaos Daemons Library.cat')
