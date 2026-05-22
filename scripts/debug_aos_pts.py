import xml.etree.ElementTree as ET

def find_pts_anywhere(cat_path, max_units=5):
    tree = ET.parse(cat_path)
    root = tree.getroot()
    tag = root.tag
    ns = ''
    if '{' in tag:
        ns = tag.split('}')[0] + '}'

    print(f"\n=== {cat_path.split('/')[-1]} ===")
    # Find ALL cost elements with pts > 0
    pts_entries = []
    for cost in root.iter(f'{ns}cost'):
        if cost.get('name','').lower() in ('pts','points') and float(cost.get('value','0')) > 0:
            # Walk up to parent selectionEntry
            pts_entries.append(cost)

    print(f"  Found {len(pts_entries)} cost elements with pts > 0")
    for cost in pts_entries[:20]:
        print(f"    pts={cost.get('value')} typeId={cost.get('typeId')}")

    # Now look for the specific "pts" cost type on selectionEntry with any parent type
    print("\n  Searching selectionEntry by type with pts > 0:")
    for se in root.iter(f'{ns}selectionEntry'):
        name = se.get('name', '?')
        etype = se.get('type', '?')
        costs = se.find(f'{ns}costs')
        if costs is not None:
            for cost in costs:
                if cost.get('name','').lower() in ('pts','points','pt') and float(cost.get('value','0')) > 0:
                    print(f"    type={etype} '{name}' pts={cost.get('value')}")

    # Check for points in profileLinks or infoLinks
    print("\n  Looking for pts in entryLink costs:")
    for el in root.iter(f'{ns}entryLink'):
        el_name = el.get('name', '?')
        costs = el.find(f'{ns}costs')
        if costs is not None:
            for cost in costs:
                if cost.get('name','').lower() in ('pts','points','pt') and float(cost.get('value','0')) > 0:
                    print(f"    entryLink '{el_name}' pts={cost.get('value')}")

find_pts_anywhere('/app/scripts/cache/bsdata/aos/Skaven - Library.cat')
find_pts_anywhere('/app/scripts/cache/bsdata/aos/Stormcast Eternals - Library.cat')
