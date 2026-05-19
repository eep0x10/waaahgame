"""
Shared dataclasses for all validators.
"""
from dataclasses import dataclass, field


@dataclass
class Issue:
    level: str
    code: str
    message: str
    target: str = None


@dataclass
class PointsBreakdown:
    base: int
    aux_surcharge: int
    total: int
    limit: int
    over_by: int


@dataclass
class ValidationResult:
    is_legal: bool
    points: PointsBreakdown
    issues: list = field(default_factory=list)
    aux_command_bonus: bool = False
