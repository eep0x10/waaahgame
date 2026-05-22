import xml.etree.ElementTree as ET

def dump_entry_full(cat_path, search_name):
    tree = ET.parse(cat_path)
    root = tree.getroot()
    tag = root.tag
    ns = ''
    if '{' in tag:
        ns = tag.split('}')[0] + '}'

    def elem_to_str(elem, depth=0, max_depth=5):
        if depth > max_depth:
            return '  '*depth + '...\n'
        s = '  '*depth + f'<{elem.tag.split("}")[-1]} {dict(elem.attrib)}>\n'
        for child in elem:
            s += elem_to_str(child, depth+1, max_depth)
        return s

    for se in root.iter(f'{ns}selectionEntry'):
        if search_name.lower() in se.get('name','').lower() and se.get('type') == 'unit':
            print(f"\n=== ENTRY: {se.get('name')} ===")
            # Print structure limited
            print(elem_to_str(se, max_depth=4))
            break

print("=== Skaven Library: Stormfiends ===")
dump_entry_full('/app/scripts/cache/bsdata/aos/Skaven - Library.cat', 'Stormfiend')

print("\n=== 40K Daemons Library: Bloodletters ===")
dump_entry_full('/app/scripts/cache/bsdata/40k/Chaos - Chaos Daemons Library.cat', 'Bloodletters')
