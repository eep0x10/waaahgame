"""
AoS 4e army validator.

validate_aos(army) -> ValidationResult   (legacy function — delegates to class)
"""
import collections

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


def _regiment_is_ror(au, army):
    """True if this ArmyUnit's regiment is a Regiment of Renown."""
    if au.regiment_id is None:
        return False
    reg = au.regiment
    return reg is not None and reg.is_ror


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

    # Points: RoR regiments use ror.points_cost (fixed), not sum of their units
    ror_regiment_ids = {r.id for r in regiments if r.is_ror}
    base_pts = (
        sum(au.points for au in all_aus if au.regiment_id not in ror_regiment_ids)
        + sum(r.ror.points_cost for r in regiments if r.is_ror and r.ror and r.ror.points_cost)
    )
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

    # Aux limit: PDF (3.6) diz "any number" — sem hard cap.
    # O ponto 0-1/0-2 é onde a sobretaxa começa; já calculada acima.
    # Emitir info apenas se exceder o limite soft para awareness.
    if n_aux > aux_max:
        issues.append(Issue(
            level="info",
            code="aux_count_surcharge",
            message=(
                f"{army.battlepack.capitalize()}: {n_aux} auxiliares "
                f"(acima de {aux_max}). Sobretaxa cumulativa aplicada — "
                f"sem limite máximo por regras (Core Rules 3.6)."
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
        # ── RoR regiment: skip all normal structural checks ──────────────
        if regiment.is_ror:
            ror = regiment.ror
            if ror:
                # Alliance check: ror.alliance must match army faction alliance OR be Mercenary
                faction = army.faction
                army_alliance = faction.grand_alliance if faction else None
                ror_alliance = ror.alliance or ''
                if ror_alliance.lower() != 'mercenary' and army_alliance and ror_alliance != army_alliance:
                    issues.append(Issue(
                        level="error",
                        code="ror_alliance_mismatch",
                        message=(
                            f'Regimento de Renome "{ror.name}" é da aliança {ror_alliance}; '
                            f"exército é {army_alliance}. Apenas RoR da mesma aliança ou "
                            f"Mercenário são permitidos."
                        ),
                        target=f"regiment:{regiment.id}",
                    ))
            continue

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

    # Bug 5 — UNIQUE units: no duplicates allowed (Core Rules 3.4)
    unique_counts = collections.Counter(
        au.unit_id for au in all_aus
        if _has_keyword(au.unit, "UNIQUE")
    )
    for uid, n in unique_counts.items():
        if n > 1:
            unit_name = next(au.unit.name for au in all_aus if au.unit_id == uid)
            issues.append(Issue(
                level="error",
                code="unique_duplicate",
                message=(
                    f"Unidade Única '{unit_name}' aparece {n}x; máximo 1 por exército."
                ),
            ))

    # Bug 6 — Legends units: warn (not block) per updates FAQ
    for au in all_aus:
        if getattr(au.unit, 'unit_category', None) == 'legends':
            issues.append(Issue(
                level="warning",
                code="legends_unit",
                message=(
                    f"'{au.unit.name}' é uma unidade Legends — restrita a jogo casual/"
                    f"matched-play não-oficial. Verifique se o evento aceita."
                ),
                target=f"army_unit:{au.id}",
            ))

    # ── Enhancements (rules 24-26, 30) ──────────────────────────────────
    import json as _json
    faction = army.faction
    try:
        _rules = _json.loads(faction.rules_json) if faction and faction.rules_json else {}
    except (ValueError, TypeError):
        _rules = {}

    _valid_traits    = {t['name'] for t in _rules.get('heroic_traits', []) if t.get('name')}
    _valid_artefacts = {a['name'] for a in _rules.get('artefacts', []) if a.get('name')}
    _valid_cmd       = {c['name'] for c in _rules.get('command_traits', []) if c.get('name')}
    # Fallback: command_traits → heroic_traits list when no dedicated table exists
    if not _valid_cmd:
        _valid_cmd = _valid_traits

    _used_traits    = []
    _used_artefacts = []

    for au in all_aus:
        is_ror = au.regiment_id is not None and _regiment_is_ror(au, army)
        is_aux = au.regiment_id is None

        # Auxiliaries and RoR members cannot have enhancements
        if au.heroic_trait or au.artefact or au.command_trait:
            if is_aux:
                issues.append(Issue(
                    level="error",
                    code="enhancement_on_aux",
                    message=f'Auxiliar "{au.unit.name}" não pode receber Aprimoramentos.',
                    target=f"army_unit:{au.id}",
                ))
            elif is_ror:
                issues.append(Issue(
                    level="error",
                    code="enhancement_on_ror",
                    message=f'"{au.unit.name}" pertence a Regimento de Renome; Aprimoramentos não permitidos.',
                    target=f"army_unit:{au.id}",
                ))

        if au.heroic_trait or au.artefact or au.command_trait:
            if not au.is_leader:
                issues.append(Issue(
                    level="error",
                    code="enhancement_on_non_leader",
                    message=f'"{au.unit.name}" não é líder de Regimento; não pode receber Aprimoramentos.',
                    target=f"army_unit:{au.id}",
                ))

        # heroic_trait uniqueness + validity
        if au.heroic_trait:
            if _valid_traits and au.heroic_trait not in _valid_traits:
                issues.append(Issue(
                    level="error",
                    code="invalid_heroic_trait",
                    message=f'Heroic Trait "{au.heroic_trait}" não pertence a esta facção.',
                    target=f"army_unit:{au.id}",
                ))
            if au.heroic_trait in _used_traits:
                issues.append(Issue(
                    level="error",
                    code="duplicate_heroic_trait",
                    message=f'Heroic Trait "{au.heroic_trait}" já está em uso neste exército.',
                    target=f"army_unit:{au.id}",
                ))
            else:
                _used_traits.append(au.heroic_trait)

        # artefact uniqueness + validity
        if au.artefact:
            if _valid_artefacts and au.artefact not in _valid_artefacts:
                issues.append(Issue(
                    level="error",
                    code="invalid_artefact",
                    message=f'Artefact "{au.artefact}" não pertence a esta facção.',
                    target=f"army_unit:{au.id}",
                ))
            if au.artefact in _used_artefacts:
                issues.append(Issue(
                    level="error",
                    code="duplicate_artefact",
                    message=f'Artefact "{au.artefact}" já está em uso neste exército.',
                    target=f"army_unit:{au.id}",
                ))
            else:
                _used_artefacts.append(au.artefact)

        # command_trait: General only
        if au.command_trait:
            if not au.is_general:
                issues.append(Issue(
                    level="error",
                    code="command_trait_non_general",
                    message=f'Command Trait só pode ser atribuído ao General.',
                    target=f"army_unit:{au.id}",
                ))
            elif _valid_cmd and au.command_trait not in _valid_cmd:
                issues.append(Issue(
                    level="error",
                    code="invalid_command_trait",
                    message=f'Command Trait "{au.command_trait}" não pertence a esta facção.',
                    target=f"army_unit:{au.id}",
                ))

    # CP underdog: bônus depende de comparação com oponente (runtime).
    # Sempre informar; não condicionar a n_aux == 0.
    aux_command_bonus = True  # sempre passa nota para o template

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
