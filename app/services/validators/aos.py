"""
AoS 4e army validator.

validate_aos(army) -> ValidationResult   (legacy function — delegates to class)
"""
from app.services.companions import is_companion_valid
from app.services.validators._types import Issue, PointsBreakdown, ValidationResult
from app.services.validators.base import BaseValidator
from app.services.validators.registry import register


@register
class AoSValidator(BaseValidator):
    code = "aos4"
    name = "Age of Sigmar"
    supports_groups = True
    supports_alliances = True
    group_label = "Regimento"
    group_label_plural = "Regimentos"
    auxiliary_label = "Auxiliar"
    color = "#b8935a"
    default_format = "vanguard"

    # Moved from app.models.army.BATTLEPACKS
    BATTLEPACKS = {
        "vanguard":   {"label": "Vanguard",   "pts": 1000, "regiments": (1, 2), "auxiliary": (0, 1)},
        "battlehost": {"label": "Battlehost", "pts": 2000, "regiments": (2, 4), "auxiliary": (0, 2)},
    }

    formats = {k: v["pts"] for k, v in BATTLEPACKS.items()}

    def validate(self, army) -> ValidationResult:
        return validate_aos(army)


def _has_keyword(unit, keyword):
    kws = unit.keywords_json or []
    return keyword.upper() in {k.upper() for k in kws}


def validate_aos(army) -> ValidationResult:
    """Standalone function kept for backward compat and direct import."""
    issues = []
    bp = AoSValidator.BATTLEPACKS.get(army.battlepack, AoSValidator.BATTLEPACKS["vanguard"])
    limit = army.points_limit

    regiments = army.regiments or []
    all_aus = army.army_units or []
    aux_units = [au for au in all_aus if au.regiment_id is None]
    regiment_aus = [au for au in all_aus if au.regiment_id is not None]  # noqa: F841

    aux_units_sorted = sorted(aux_units, key=lambda au: au.sort_order)
    n_aux = len(aux_units_sorted)

    aux_surcharge = 10 * n_aux * (n_aux - 1)

    base_pts = sum(au.points for au in all_aus)
    total_pts = base_pts + aux_surcharge
    over_by = max(0, total_pts - limit)

    pts = PointsBreakdown(
        base=base_pts,
        aux_surcharge=aux_surcharge,
        total=total_pts,
        limit=limit,
        over_by=over_by,
    )

    if over_by > 0:
        issues.append(Issue(
            level="error",
            code="pts_over_limit",
            message=f"Pontos acima do limite: {total_pts}/{limit} (+{over_by})",
        ))
    else:
        buffer = limit - total_pts
        issues.append(Issue(
            level="info",
            code="pts_ok",
            message=f"{total_pts}/{limit} pts — {buffer} pts de margem",
        ))

    if aux_surcharge > 0:
        issues.append(Issue(
            level="info",
            code="aux_surcharge",
            message=f"Sobretaxa auxiliar: +{aux_surcharge} pts ({n_aux} auxiliares)",
        ))

    reg_min, reg_max = bp["regiments"]
    aux_min, aux_max = bp["auxiliary"]

    n_reg = len(regiments)
    if not (reg_min <= n_reg <= reg_max):
        issues.append(Issue(
            level="error",
            code="regiment_count",
            message=(
                f"{army.battlepack.capitalize()} requer {reg_min}-{reg_max} "
                f"regimentos; encontrado {n_reg}"
            ),
        ))

    if not (aux_min <= n_aux <= aux_max):
        issues.append(Issue(
            level="error",
            code="aux_count",
            message=(
                f"{army.battlepack.capitalize()} permite {aux_min}-{aux_max} "
                f"auxiliares; encontrado {n_aux}"
            ),
        ))

    generals = [au for au in all_aus if au.is_general]
    if len(generals) == 0:
        issues.append(Issue(
            level="error",
            code="no_general",
            message="Nenhum general designado.",
        ))
    elif len(generals) > 1:
        issues.append(Issue(
            level="error",
            code="multiple_generals",
            message=f"{len(generals)} unidades marcadas como general; apenas 1 permitido.",
        ))
    else:
        gen = generals[0]
        if not _has_keyword(gen.unit, "HERO"):
            issues.append(Issue(
                level="error",
                code="general_not_hero",
                message=f'General "{gen.unit.name}" não é um Hero.',
                target=f"army_unit:{gen.id}",
            ))
        reg1_list = [r for r in regiments if r.position == 1]
        if reg1_list:
            reg1 = reg1_list[0]
            leader = reg1.leader
            if leader is None or leader.id != gen.id:
                issues.append(Issue(
                    level="error",
                    code="general_not_reg1_leader",
                    message="O general deve ser o líder do Regimento 1.",
                    target=f"army_unit:{gen.id}",
                ))
        else:
            issues.append(Issue(
                level="error",
                code="general_not_reg1_leader",
                message="Regimento 1 não encontrado; o general deve liderar o Regimento 1.",
            ))

    reinforced_unit_ids: set = set()
    for au in all_aus:
        if au.is_reinforced:
            if not au.unit.can_be_reinforced:
                issues.append(Issue(
                    level="error",
                    code="cannot_reinforce",
                    message=f'"{au.unit.name}" não pode ser reforçada.',
                    target=f"army_unit:{au.id}",
                ))
            else:
                if au.unit_id in reinforced_unit_ids:
                    issues.append(Issue(
                        level="error",
                        code="reinforcement_duplicate",
                        message=(
                            f'"{au.unit.name}" já está reforçada em outro local do exército.'
                        ),
                        target=f"army_unit:{au.id}",
                    ))
                reinforced_unit_ids.add(au.unit_id)

    for regiment in regiments:
        reg_aus = list(regiment.army_units)
        leaders = [au for au in reg_aus if au.is_leader]
        companions = [au for au in reg_aus if not au.is_leader]

        if len(leaders) == 0:
            issues.append(Issue(
                level="error",
                code="regiment_no_leader",
                message=f"Regimento {regiment.position} não possui líder.",
                target=f"regiment:{regiment.id}",
            ))
        elif len(leaders) > 1:
            issues.append(Issue(
                level="error",
                code="regiment_multiple_leaders",
                message=(
                    f"Regimento {regiment.position} tem {len(leaders)} líderes; "
                    f"apenas 1 permitido."
                ),
                target=f"regiment:{regiment.id}",
            ))
        else:
            leader_au = leaders[0]
            if not _has_keyword(leader_au.unit, "HERO"):
                issues.append(Issue(
                    level="error",
                    code="leader_not_hero",
                    message=(
                        f'Líder do Regimento {regiment.position} '
                        f'"{leader_au.unit.name}" não é um Hero.'
                    ),
                    target=f"army_unit:{leader_au.id}",
                ))

            if len(companions) > 3:
                issues.append(Issue(
                    level="error",
                    code="regiment_too_large",
                    message=(
                        f"Regimento {regiment.position} tem {len(companions)} "
                        f"companheiros; máximo 3."
                    ),
                    target=f"regiment:{regiment.id}",
                ))

            companion_units = [au.unit for au in companions]

            for comp_au in companions:
                if _has_keyword(comp_au.unit, "HERO"):
                    leader_specs = leader_au.unit.companions_json or []
                    hero_allowed = False
                    from app.services.companions import _matches_spec as _ms
                    for spec in leader_specs:
                        if _ms(comp_au.unit, spec):
                            hero_allowed = True
                            break
                    if not hero_allowed:
                        issues.append(Issue(
                            level="warning",
                            code="hero_as_companion_review",
                            message=(
                                f'"{comp_au.unit.name}" é um Hero no Regimento '
                                f"{regiment.position}; "
                                f"verifique elegibilidade como companheiro."
                            ),
                            target=f"army_unit:{comp_au.id}",
                        ))

                valid, reason = is_companion_valid(
                    comp_au.unit,
                    leader_au.unit,
                    companion_units,
                )
                if not valid:
                    issues.append(Issue(
                        level="error",
                        code="companion_invalid",
                        message=(
                            f"Regimento {regiment.position}: "
                            f'"{comp_au.unit.name}" é um companheiro inválido. '
                            f"{reason or ''}"
                        ),
                        target=f"army_unit:{comp_au.id}",
                    ))

    aux_command_bonus = n_aux == 0

    errors = [i for i in issues if i.level == "error"]
    is_legal = len(errors) == 0

    # Collect selected faction picks for display in the summary panel.
    # No enforcement yet — Phase 2 read-only display only.
    faction_picks = {}
    for attr, label in (
        ('sub_faction_id',        'Sub-facção'),
        ('formation_id',          'Formação'),
        ('spell_lore_id',         'Lore de Magia'),
        ('prayer_lore_id',        'Lore de Oração'),
        ('manifestation_lore_id', 'Lore de Manifestação'),
    ):
        val = getattr(army, attr, None)
        if val:
            faction_picks[label] = val

    return ValidationResult(
        is_legal=is_legal,
        points=pts,
        issues=issues,
        aux_command_bonus=aux_command_bonus,
        faction_picks=faction_picks,
    )
