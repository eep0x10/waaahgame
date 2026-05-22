"""
remap_subfactions.py — Remapeia units de subfactions para suas factions canônicas no AoS4.

Lógica:
  Para cada unit no DB (AoS4), consulta manifest pelo slug, pega a lista factions[],
  itera de TRÁS pra frente e usa o primeiro slug que corresponder a uma Faction existente
  no DB (game_system='aos4'). Se nenhum bate, mantém como está.

Idempotente: segunda execução não muda nada.

Após o remap, deleta Factions AoS4 que ficaram vazias (0 units) E não têm blurb
E não estão na lista de 18 factions originais protegidas.
"""

import sys
import os
import json
import re

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

MANIFEST_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'cache', 'lexicanum_manifest.json',
)

# Factions originais (pré-seed) que NUNCA devem ser deletadas mesmo se vazias
PROTECTED_SLUGS = {
    'skaven',
    'seraphon',
    'stormcast-eternals',
    'sylvaneth',
    'nighthaunt',
    'cities-of-sigmar',
    'daughters-of-khaine',
    'kharadron-overlords',
    'lumineth-realm-lords',
    'maggotkin-of-nurgle',
    'slaves-to-darkness',
    'soulblight-gravelords',
    'fyreslayers',
    'idoneth-deepkin',
    'ossiarch-bonereapers',
    'disciples-of-tzeentch',
    'gloomspite-gitz',
    'orruk-warclans',
}


def slugify(name: str) -> str:
    """Lowercase, substitui não-alfanuméricos por hifens, remove hifens das bordas."""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')


def main():
    from app import create_app
    from app.extensions import db
    from app.models.game import GameSystem, Faction, Unit

    app = create_app()
    with app.app_context():
        _run(db, GameSystem, Faction, Unit)


def _run(db, GameSystem, Faction, Unit):
    # ------------------------------------------------------------------
    # Carregar manifest
    # ------------------------------------------------------------------
    if not os.path.exists(MANIFEST_PATH):
        print(f'ERROR: manifest não encontrado: {MANIFEST_PATH}')
        sys.exit(1)

    with open(MANIFEST_PATH, 'r', encoding='utf-8') as fh:
        manifest = json.load(fh)

    manifest_units: dict = manifest.get('units', {})  # slug -> {factions: [...], ...}

    # ------------------------------------------------------------------
    # Resolve GameSystem
    # ------------------------------------------------------------------
    gs = GameSystem.query.filter_by(code='aos4').first()
    if gs is None:
        print('ERROR: GameSystem aos4 não encontrado no DB.')
        sys.exit(1)

    print(f'GameSystem: {gs.code} (id={gs.id})')

    # ------------------------------------------------------------------
    # Indexar todas as Factions AoS4 por slug
    # ------------------------------------------------------------------
    all_aos4_factions: dict[str, Faction] = {
        f.slug: f for f in Faction.query.filter_by(game_system_id=gs.id).all()
    }
    print(f'Factions AoS4 no DB: {len(all_aos4_factions)}')

    # ------------------------------------------------------------------
    # Carregar todas as Units AoS4 do DB
    # ------------------------------------------------------------------
    all_units: list[Unit] = (
        Unit.query
        .join(Faction)
        .filter(Faction.game_system_id == gs.id)
        .all()
    )
    print(f'Units AoS4 no DB: {len(all_units)}')
    print()

    # ------------------------------------------------------------------
    # FASE 1: Remap faction_id
    # ------------------------------------------------------------------
    moved = 0
    not_in_manifest = 0
    no_match = 0
    already_correct = 0

    # Tabela de movimentações: (from_slug, to_slug) -> count
    move_table: dict[tuple, int] = {}

    for unit in all_units:
        udata = manifest_units.get(unit.slug)
        if udata is None:
            not_in_manifest += 1
            continue

        factions_list = udata.get('factions') or []
        if not factions_list:
            no_match += 1
            continue

        # Iterar de TRÁS pra frente (último = mais canônico)
        target_faction = None
        for fname in reversed(factions_list):
            fslug = slugify(fname)
            candidate = all_aos4_factions.get(fslug)
            if candidate is not None:
                target_faction = candidate
                break

        if target_faction is None:
            no_match += 1
            continue

        if unit.faction_id == target_faction.id:
            already_correct += 1
            continue

        # Registrar movimentação
        from_slug = unit.faction.slug if unit.faction else '(unknown)'
        key = (from_slug, target_faction.slug)
        move_table[key] = move_table.get(key, 0) + 1

        unit.faction_id = target_faction.id
        moved += 1

    # Commit remap
    db.session.flush()

    print('=' * 60)
    print('  FASE 1 — Remap faction_id')
    print('=' * 60)
    print(f'  Units movidas          : {moved}')
    print(f'  Units já corretas      : {already_correct}')
    print(f'  Units sem match no DB  : {no_match}')
    print(f'  Units não no manifest  : {not_in_manifest}')
    print()

    if move_table:
        print('  Movimentações (from → to):')
        for (frm, to), cnt in sorted(move_table.items(), key=lambda x: -x[1]):
            print(f'    {frm:40s} → {to:40s}  [{cnt} units]')
    else:
        print('  Nenhuma movimentação necessária (idempotente).')
    print()

    # ------------------------------------------------------------------
    # FASE 2: Deletar factions vazias não-protegidas sem blurb
    # ------------------------------------------------------------------
    # Recarregar factions após o flush para contar units atualizado
    factions_to_delete = []
    factions_kept = []

    for fslug, faction in all_aos4_factions.items():
        # Usar len() na relação — SQLAlchemy rastreia dirty state
        unit_count = len(faction.units)

        if unit_count > 0:
            continue  # tem units, mantém

        if fslug in PROTECTED_SLUGS:
            factions_kept.append((fslug, 'protected'))
            continue

        if faction.blurb is not None:
            factions_kept.append((fslug, 'has blurb'))
            continue

        # Candidata a deletar
        factions_to_delete.append(faction)

    print('=' * 60)
    print('  FASE 2 — Deletar factions vazias não-protegidas')
    print('=' * 60)
    print(f'  Factions a deletar: {len(factions_to_delete)}')

    if factions_to_delete:
        print()
        print('  Lista:')
        for f in sorted(factions_to_delete, key=lambda x: x.slug):
            print(f'    DELETE faction: {f.slug!r}  (id={f.id}, name={f.name!r})')

    if factions_kept:
        print()
        print(f'  Factions vazias mantidas ({len(factions_kept)}):')
        for fslug, reason in sorted(factions_kept):
            print(f'    KEEP {fslug!r}  [{reason}]')

    print()

    for faction in factions_to_delete:
        db.session.delete(faction)

    # Commit tudo (remap + deletes)
    db.session.commit()
    print('  Commit OK.')
    print()

    # ------------------------------------------------------------------
    # FASE 3: Verificação pós-commit — factions canônicas alvo
    # ------------------------------------------------------------------
    TARGET_CANONICAL = [
        'beasts-of-chaos',
        'tzeentch-arcanites',
        'blades-of-khorne',
        'hedonites-of-slaanesh',
        'skaventide',
        'everchosen',
        'deathlords',
        'aleguzzler-gargants',
        'ogor-mawtribes',
    ]

    print('=' * 60)
    print('  FASE 3 — Status das factions canônicas alvo')
    print('=' * 60)

    for slug in TARGET_CANONICAL:
        faction = Faction.query.filter_by(slug=slug).first()
        if faction is None:
            print(f'  {slug:45s} : DELETADA (estava vazia e não era protegida)')
        else:
            count = Unit.query.filter_by(faction_id=faction.id).count()
            status = f'{count} units'
            print(f'  {slug:45s} : {status}')

    print()

    # Sumário geral AoS4
    total_factions_now = Faction.query.filter_by(game_system_id=gs.id).count()
    total_units_now = (
        Unit.query.join(Faction).filter(Faction.game_system_id == gs.id).count()
    )

    print('=' * 60)
    print('  SUMÁRIO FINAL')
    print('=' * 60)
    print(f'  Total factions AoS4 agora : {total_factions_now}')
    print(f'  Total units AoS4 agora    : {total_units_now}')
    print(f'  Units reassigned          : {moved}')
    print(f'  Factions deletadas        : {len(factions_to_delete)}')
    print('=' * 60)


if __name__ == '__main__':
    main()
