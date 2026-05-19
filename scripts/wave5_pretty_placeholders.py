"""
Generate/replace SVG placeholders for all units still missing a real image.
400x400px, parchment background, decorative gold border, faction sigil.
"""

import sys
import os
import re
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)

ALLIANCE_COLORS = {
    'Order':       ('#1a3a5c', '#d4af37', '#f4e8d5'),
    'Chaos':       ('#3d0000', '#c0392b', '#f4e8d5'),
    'Death':       ('#1a1a2e', '#7f8c8d', '#f4e8d5'),
    'Destruction': ('#1a2d00', '#27ae60', '#f4e8d5'),
}

FACTION_SIGILS = {
    'skaven':               '☠',
    'seraphon':             '★',
    'stormcast-eternals':   '⚡',
    'sylvaneth':            '☘',
    'nighthaunt':           '☠',
    'cities-of-sigmar':     '⛰',
    'daughters-of-khaine':  '⚔',
    'kharadron-overlords':  '⚓',
    'lumineth-realm-lords': '☀',
    'maggotkin-of-nurgle':  '☣',
    'slaves-to-darkness':   '♦',
    'disciples-of-tzeentch':'❤',
    'soulblight-gravelords':'⬤',
    'ossiarch-bonereapers': '☠',
    'orruk-warclans':       '⚔',
    'gloomspite-gitz':      '☽',
    'space-marines':        '☸',
    'tyranids':             '✦',
    'necrons':              '⚧',
    'aeldari':              '✶',
    'chaos-space-marines':  '♦',
}


def _wrap_text(text, max_chars=22):
    words = text.split()
    lines = []
    current = ''
    for w in words:
        if len(current) + len(w) + 1 <= max_chars:
            current = (current + ' ' + w).strip()
        else:
            if current:
                lines.append(current)
            current = w
    if current:
        lines.append(current)
    return lines[:3]


def _make_pretty_svg(unit_name, faction_name, faction_slug, alliance):
    border_color, accent_color, bg_color = ALLIANCE_COLORS.get(alliance, ALLIANCE_COLORS['Order'])
    sigil = FACTION_SIGILS.get(faction_slug, '★')

    name_lines = _wrap_text(unit_name, 20)
    name_y_start = 230 if len(name_lines) > 1 else 245

    name_svgs = []
    for i, line in enumerate(name_lines):
        y = name_y_start + i * 24
        name_svgs.append(
            f'  <text x="200" y="{y}" font-family="Garamond,\'Times New Roman\',serif" '
            f'font-size="16" fill="{border_color}" text-anchor="middle" font-weight="bold">'
            f'{line}</text>'
        )
    name_block = '\n'.join(name_svgs)

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="400" height="400" viewBox="0 0 400 400">
  <!-- Background -->
  <rect width="400" height="400" fill="{bg_color}"/>
  <!-- Outer gold border -->
  <rect x="6" y="6" width="388" height="388" fill="none" stroke="{accent_color}" stroke-width="3"/>
  <!-- Inner gold border -->
  <rect x="14" y="14" width="372" height="372" fill="none" stroke="{accent_color}" stroke-width="1.5" stroke-dasharray="6,3"/>
  <!-- Corner ornaments -->
  <circle cx="20" cy="20" r="4" fill="{accent_color}"/>
  <circle cx="380" cy="20" r="4" fill="{accent_color}"/>
  <circle cx="20" cy="380" r="4" fill="{accent_color}"/>
  <circle cx="380" cy="380" r="4" fill="{accent_color}"/>
  <!-- Faction sigil -->
  <text x="200" y="130" font-family="serif" font-size="64" fill="{accent_color}" text-anchor="middle" opacity="0.55">{sigil}</text>
  <!-- Faction name -->
  <text x="200" y="175" font-family="Garamond,\'Times New Roman\',serif" font-size="13" fill="{border_color}" text-anchor="middle" letter-spacing="2">{faction_name.upper()}</text>
  <!-- Divider -->
  <line x1="60" y1="187" x2="340" y2="187" stroke="{accent_color}" stroke-width="1"/>
  <!-- Unit name -->
{name_block}
  <!-- Bottom label -->
  <text x="200" y="360" font-family="Garamond,\'Times New Roman\',serif" font-size="11" fill="{border_color}" text-anchor="middle" opacity="0.6" letter-spacing="1">NO ART AVAILABLE</text>
  <!-- Bottom divider -->
  <line x1="60" y1="345" x2="340" y2="345" stroke="{accent_color}" stroke-width="1" opacity="0.5"/>
</svg>'''
    return svg


def run():
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_run(db, Faction, Unit)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_run(db, Faction, Unit)


def _do_run(db, Faction, Unit):
    all_units = Unit.query.join(Faction).all()
    generated = 0

    for unit in all_units:
        faction = unit.faction
        faction_slug = faction.slug
        unit_slug = unit.slug

        jpg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.jpg')
        if os.path.exists(jpg_abs):
            continue

        svg_rel = f'img/units/{faction_slug}/{unit_slug}.svg'
        svg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.svg')

        alliance = faction.grand_alliance or 'Order'
        svg_content = _make_pretty_svg(unit.name, faction.name, faction_slug, alliance)

        os.makedirs(os.path.dirname(svg_abs), exist_ok=True)
        with open(svg_abs, 'w', encoding='utf-8') as fh:
            fh.write(svg_content)

        unit.image_path = svg_rel
        generated += 1
        log.info('[SVG] %s -> %s', unit.name, svg_rel)

    db.session.commit()
    log.info('Pretty placeholders generated: %d', generated)
    return generated


if __name__ == '__main__':
    n = run()
    print(f'\nGenerated {n} pretty SVG placeholders.')
