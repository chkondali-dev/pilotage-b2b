"""
types.py — Types fondamentaux du compilateur de dossier.

Contrat stable defini dans .opencode/ARCHITECTURE.md (section 5).
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class IntentKind(str, Enum):
    EXPLORE  = "explore"
    DEBUG    = "debug"
    REFACTOR = "refactor"
    ARCH     = "arch"
    REPORT   = "report"
    GENERAL  = "general"


class FactKind(str, Enum):
    STATEMENT = "statement"
    ARTIFACT  = "artifact"
    SIGNAL    = "signal"
    METRIC    = "metric"


@dataclass
class Fact:
    """Un fait verifie, tracable jusqu'a sa source.

    v3 — Trois dimensions de qualite :
      importance : valeur intrinseque du fait (0.0-1.0)
      utility    : utilite pour la question courante (0.0-1.0)
      confidence : fiabilite de la source (0.0-1.0)
    """
    text: str
    kind: FactKind = FactKind.STATEMENT
    confidence: float = 1.0
    source: Optional[str] = None
    symbol: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    # v3 — Optimizer
    importance: float = 0.5      # valeur intrinseque
    utility: float = 0.5         # utilite pour la question
    category: str = ""            # critical | important | context | secondary
    tags: list[str] = field(default_factory=list)  # ["security", "auth", ...]

    def __post_init__(self):
        if not self.text:
            raise ValueError("Fact.text ne peut pas etre vide")


@dataclass
class Constraint:
    """Une limite explicite a respecter."""
    text: str
    severity: str = "info"        # info | warning | error
    source: Optional[str] = None

    def __post_init__(self):
        assert self.severity in ("info", "warning", "error"), \
            f"severite invalide: {self.severity}"


@dataclass
class Action:
    """Une etape a suivre, avec priorite et dependances."""
    text: str
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)


@dataclass
class Hypothesis:
    """Une piste a explorer (debug, analyse)."""
    text: str
    confidence: float = 0.5
    triggered_by: Optional[str] = None


# ── DossierDelta ───────────────────────────────────────

@dataclass
class DossierDelta:
    """Diff applique au dossier par une passe de compilation."""
    facts: list[Fact] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)
    options: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)
    metrics: dict = field(default_factory=dict)
    recommendations: list[dict] = field(default_factory=list)
    objective: Optional[str] = None
    artifacts: list[str] = field(default_factory=list)

    def __bool__(self):
        return bool(
            self.facts or self.constraints or self.actions
            or self.hypotheses or self.signals or self.options
            or self.risks or self.metrics or self.recommendations
            or self.objective or self.artifacts
        )


# ── ReasoningDossier (IR) ──────────────────────────────

@dataclass
class ReasoningDossier:
    """Representation intermediaire du raisonnement.

    Accumule les DossierDelta via apply().
    Ne contient PAS de render() — les renderers sont separes.
    """
    intent: IntentKind = IntentKind.GENERAL
    objective: str = ""

    facts: list[Fact] = field(default_factory=list)
    constraints: list[Constraint] = field(default_factory=list)
    actions: list[Action] = field(default_factory=list)

    hypotheses: list[Hypothesis] = field(default_factory=list)
    signals: list[str] = field(default_factory=list)

    options: list[str] = field(default_factory=list)
    risks: list[str] = field(default_factory=list)

    metrics: dict = field(default_factory=dict)
    recommendations: list[dict] = field(default_factory=list)

    source_context: str = ""
    passes_run: list[str] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)

    def apply(self, delta: DossierDelta) -> "ReasoningDossier":
        if delta.objective is not None:
            self.objective = delta.objective
        self.facts.extend(delta.facts)
        self.constraints.extend(delta.constraints)
        self.actions.extend(delta.actions)
        self.hypotheses.extend(delta.hypotheses)
        self.signals.extend(delta.signals)
        self.options.extend(delta.options)
        self.risks.extend(delta.risks)
        self.metrics.update(delta.metrics)
        self.recommendations.extend(delta.recommendations)
        self.artifacts.extend(delta.artifacts)
        self.source_context = self.source_context or ""
        return self

    def __post_init__(self):
        self.source_context = self.source_context or ""

    def __bool__(self):
        return bool(self.objective)


# ── Passes ──────────────────────────────────────────────

# (query, plan, context_pack, intent, dossier_courant) -> DossierDelta
PassFn = Callable[..., DossierDelta]


@dataclass
class PassDef:
    """Definition d'une passe de compilation."""
    name: str
    description: str
    fn: PassFn
    requires: list[str] = field(default_factory=list)
    priority: int = 50


# ── Helpers partages ───────────────────────────────────

# ponytail: global lock, per-account locks if throughput matters
_PASSES: list[PassDef] = []


def register_pass(name: str, description: str,
                  requires: Optional[list[str]] = None,
                  priority: int = 50):
    """Decorator pour enregistrer une passe de compilation."""
    fn_requires = requires or []
    def decorator(fn):
        _PASSES.append(PassDef(
            name=name, description=description,
            fn=fn, requires=fn_requires,
            priority=priority,
        ))
        return fn
    return decorator


def get_all_passes() -> list[PassDef]:
    """Retourne toutes les passes enregistrees."""
    return list(_PASSES)


def clear_passes():
    """Reinitialise le registre (utile pour les tests)."""
    _PASSES.clear()
