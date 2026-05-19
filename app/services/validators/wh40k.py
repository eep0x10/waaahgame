"""
Warhammer 40,000 10th edition army validator (simplified).

Formats and points caps:
  combat_patrol = 500
  incursion     = 1000
  strike_force  = 2000
  onslaught     = 3000

Rules enforced:
  - Exactly 1 unit with is_general (= Warlord). Must have CHARACTER keyword.
  - Total points <= cap.
  - Non-BATTLELINE units: max 3 copies of same slug.
  - BATTLELINE units: max 6 copies of same slug.
  - EPIC_HERO units: max 1 each, max 3 total.
  - No regiment/companion/auxiliary/surcharge semantics.
"""
from collections import Counter
from app.services.validators._types import Issue, PointsBreakdown, ValidationResult

FORMAT_CAPS = {
    'combat_patrol': 500,
    'incursion': 1000,
    'strike_force': 2000,
    'onslaught': 3000,
}


def _has_keyword(unit, keyword):
    kws = unit.keywords_json or []
    return keyword.upper() in {k.upper() for k in kws}


def validate_wh40k(army):
    issues = []

    # Determine points cap from battlepack (which holds the format slug for 40k armies)
    limit = army.points_limit
    cap = FORMAT_CAPS.get(army.battlepack, limit)

    all_aus = army.army_units or []
    base_pts = sum(au.points for au in all_aus)
    over_by = max(0, base_pts - cap)

    pts = PointsBreakdown(
        base=base_pts,
        aux_surcharge=0,
        total=base_pts,
        limit=cap,
        over_by=over_by,
    )

    # Points check
    if over_by > 0:
        issues.append(Issue(
            level='error',
            code='pts_over_limit',
            message=f'Points over limit: {base_pts}/{cap} (+{over_by})',
        ))
    else:
        buffer = cap - base_pts
        issues.append(Issue(
            level='info',
            code='pts_ok',
            message=f'{base_pts}/{cap} pts — {buffer} pts remaining',
        ))

    # Warlord (general) check
    generals = [au for au in all_aus if au.is_general]
    if len(generals) == 0:
        issues.append(Issue(
            level='error',
            code='no_general',
            message='No Warlord designated.',
        ))
    elif len(generals) > 1:
        issues.append(Issue(
            level='error',
            code='multiple_generals',
            message=f'{len(generals)} units marked as Warlord; only 1 allowed.',
        ))
    else:
        gen = generals[0]
        if not _has_keyword(gen.unit, 'CHARACTER'):
            issues.append(Issue(
                level='error',
                code='general_not_character',
                message=f'Warlord "{gen.unit.name}" does not have the CHARACTER keyword.',
                target=f'army_unit:{gen.id}',
            ))

    # Unit copy limits
    slug_counts = Counter(au.unit.slug for au in all_aus)
    # Track per-slug whether it's battleline
    slug_to_unit = {au.unit.slug: au.unit for au in all_aus}

    for slug, count in slug_counts.items():
        unit = slug_to_unit[slug]
        is_battleline = _has_keyword(unit, 'BATTLELINE')
        max_copies = 6 if is_battleline else 3
        if count > max_copies:
            issues.append(Issue(
                level='error',
                code='unit_max_copies',
                message=(
                    f'"{unit.name}" appears {count} times; '
                    f'max {"6 (BATTLELINE)" if is_battleline else "3"} copies allowed.'
                ),
            ))

    # EPIC_HERO: max 1 each, max 3 total
    epic_hero_aus = [au for au in all_aus if _has_keyword(au.unit, 'EPIC_HERO')]
    epic_hero_slugs = Counter(au.unit.slug for au in epic_hero_aus)
    for slug, count in epic_hero_slugs.items():
        if count > 1:
            unit_name = slug_to_unit[slug].name
            issues.append(Issue(
                level='error',
                code='epic_hero_duplicate',
                message=f'EPIC_HERO "{unit_name}" appears {count} times; max 1 allowed.',
            ))
    if len(epic_hero_aus) > 3:
        issues.append(Issue(
            level='error',
            code='epic_hero_limit',
            message=f'{len(epic_hero_aus)} EPIC_HERO units in army; max 3 allowed.',
        ))

    errors = [i for i in issues if i.level == 'error']
    is_legal = len(errors) == 0

    return ValidationResult(
        is_legal=is_legal,
        points=pts,
        issues=issues,
        aux_command_bonus=False,
    )
