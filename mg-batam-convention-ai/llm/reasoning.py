"""
reasoning.py — Compilation d'un audit brut en ReasoningDossier structuré.

Transforme la sortie markdown de agents.audit() (format PROMPTS/audit_convention.md)
en un dossier de faits sourcés + détection des trous de connaissance (anti-hallucination).

Flux : audit LLM → compile_dossier() → dossier (faits, contraintes, actions, manques)
      → render_json() pour archivage / injection des manques dans le prompt comex.

Chaque fait porte sa source (clause) et sa confiance (selon la sévérité du constat).
Les passes sont des fonctions pures, exécutées en séquence ; une passe qui échoue
est signalée dans passes_run sans casser le pipeline.
"""

import re
import unicodedata
from dataclasses import dataclass, field, asdict

# ── Types (port allégé du contrat ReasoningDossier, adapté au domaine contrat) ──

@dataclass
class Fact:
    text: str
    kind: str          # constat | regle | positif | question
    confidence: float  # 0.0 → 1.0
    source: str = ""   # clause d'origine

    def __post_init__(self):
        if not self.text.strip():
            raise ValueError("Fact.text ne doit pas être vide")


@dataclass
class Constraint:
    text: str
    severity: str      # info | warning | error


@dataclass
class Action:
    text: str
    priority: int      # 0 = plus haute
    source: str = ""


@dataclass
class DossierDelta:
    facts: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    objective: str | None = None

    def __bool__(self):
        return bool(self.facts or self.constraints or self.actions
                    or self.missing or self.objective)


@dataclass
class ReasoningDossier:
    objective: str
    facts: list = field(default_factory=list)
    constraints: list = field(default_factory=list)
    actions: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    source_context: str = ""
    passes_run: list = field(default_factory=list)

    def apply(self, delta: DossierDelta) -> "ReasoningDossier":
        self.facts.extend(delta.facts)
        self.constraints.extend(delta.constraints)
        self.actions.extend(delta.actions)
        self.missing.extend(delta.missing)
        if delta.objective:
            self.objective = delta.objective
        return self


# ── Patterns de trous de connaissance (anti-hallucination) ──
# Le texte est normalisé (accents → ASCII, minuscules) avant le matching,
# car les sorties LLM mélangent « à confirmer » / « a confirmer ».

def _sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s)
                   if not unicodedata.combining(c)).lower()


_PATTERNS_TROUS = [
    r"a confirmer", r"a verifier", r"a valider", r"non precise", r"non fourni",
    r"non communique", r"non mentionne", r"non disponible", r"non confirme",
    r"absent", r"introuvable", r"manquant", r"________", r"a completer",
    r"a definir", r"aucune information",
]


def _severite_emoji(texte: str) -> tuple[str, float]:
    """(severity, confidence) depuis un constat 🔴/🟠/🟡."""
    if "🔴" in texte:
        return "error", 0.9
    if "🟠" in texte:
        return "warning", 0.75
    if "🟡" in texte:
        return "info", 0.6
    return "info", 0.5


# ── Passes ─────────────────────────────────────────────────────────────────

def pass_extract_objective(text: str, dossier: ReasoningDossier) -> DossierDelta:
    m = re.search(r"^#\s*(Audit[^\n]*)", text, re.M)
    if m:
        return DossierDelta(objective=m.group(1).strip())
    premier = next((l.strip() for l in text.splitlines() if l.strip()), "")
    return DossierDelta(objective=premier[:120] or "Audit de convention")


def pass_extract_facts(text: str, dossier: ReasoningDossier) -> DossierDelta:
    """Parse les sections ## Constats / Points positifs / Questions ouvertes."""
    delta = DossierDelta()
    sections = re.split(r"^##\s+(.+?)\s*$", text, flags=re.M)  # titre, corps, titre, corps…
    for i in range(1, len(sections), 2):
        titre, corps = sections[i].strip().lower(), sections[i + 1]

        if titre.startswith("constat"):
            for bloc in re.split(r"(?=^###\s+)", corps, flags=re.M):
                bloc = bloc.strip()
                if not bloc.startswith("###"):
                    continue
                clause = bloc.splitlines()[0].lstrip("# ").strip()
                constat_m = re.search(r"\*\*?Constat\s*:\*\*\s*(.*)", bloc)
                constat = constat_m.group(1).strip() if constat_m else ""
                severity, conf = _severite_emoji(constat)
                delta.facts.append(Fact(text=constat or bloc, kind="constat",
                                        confidence=conf, source=clause))
                regle_m = re.search(r"\*\*?R[eè]gle applicable\s*:\*\*\s*(.*)", bloc)
                if regle_m and regle_m.group(1).strip():
                    delta.facts.append(Fact(text=regle_m.group(1).strip(),
                                            kind="regle", confidence=0.8, source=clause))
                rec_m = re.search(r"\*\*?Recommandation\s*:\*\*\s*(.*)", bloc)
                if rec_m and rec_m.group(1).strip():
                    delta.actions.append(Action(text=rec_m.group(1).strip(),
                                                priority=0 if severity == "error"
                                                else 1 if severity == "warning" else 2,
                                                source=clause))

        elif titre.startswith("verdict"):
            ligne = next((l.strip() for l in corps.splitlines()
                          if l.strip() and re.search(r"[🔴🟠🟡]", l)), "")
            if ligne:
                severity, _ = _severite_emoji(ligne)
                delta.constraints.append(Constraint(text=ligne, severity=severity))

        elif titre.startswith("point"):
            for ligne in corps.splitlines():
                ligne = ligne.strip().lstrip("- ").strip()
                if ligne:
                    delta.facts.append(Fact(text=ligne, kind="positif",
                                            confidence=0.8, source=""))

        elif titre.startswith("question"):
            for ligne in corps.splitlines():
                ligne = ligne.strip().lstrip("- ").strip()
                if ligne:
                    delta.facts.append(Fact(text=ligne, kind="question",
                                            confidence=0.5, source=""))
    return delta


def pass_detect_missing(text: str, dossier: ReasoningDossier) -> DossierDelta:
    """Repère les informations manquantes (à confirmer, absent, ________…) → warnings."""
    delta = DossierDelta()
    vus = set()
    for ligne in text.splitlines():
        l = ligne.strip()
        if not l:
            continue
        low = _sans_accents(l)
        if any(re.search(p, low) for p in _PATTERNS_TROUS):
            tronque = l[:200]
            if tronque not in vus:
                vus.add(tronque)
                delta.missing.append(tronque)
                delta.constraints.append(
                    Constraint(text=f"Information manquante : {tronque[:150]}",
                               severity="warning"))
    return delta


def pass_validate(text: str, dossier: ReasoningDossier) -> DossierDelta:
    """Intégrité : faits vides interdits, objectif non vide, manques listés."""
    delta = DossierDelta()
    if not dossier.objective.strip():
        delta.constraints.append(Constraint(text="Objectif non extrait de l'audit",
                                            severity="warning"))
    if dossier.facts and not any(f.kind == "constat" for f in dossier.facts):
        delta.constraints.append(
            Constraint(text="Aucun constat structuré détecté (format audit non conforme ?)",
                       severity="warning"))
    return delta


# ── Pipeline ────────────────────────────────────────────────────────────────

_PASSES = [
    ("extract.objective", pass_extract_objective),
    ("extract.facts", pass_extract_facts),
    ("detect.missing", pass_detect_missing),
    ("validate.dossier", pass_validate),
]


def compile_dossier(audit_text: str, objective: str = "") -> ReasoningDossier:
    """Compile un audit markdown en ReasoningDossier (passes séquentielles, non fatales)."""
    text = audit_text or ""
    dossier = ReasoningDossier(objective=objective, source_context=text[:2000])
    for nom, fn in _PASSES:
        try:
            delta = fn(text, dossier)
            if delta:
                dossier.apply(delta)
            dossier.passes_run.append(nom)
        except Exception:
            dossier.passes_run.append(f"{nom}(error)")
    return dossier


# ── Renderer ────────────────────────────────────────────────────────────────

def render_json(dossier: ReasoningDossier) -> dict:
    """Dossier → dict sérialisable (archivage OUTPUTS/, intégration comex)."""
    return {
        "objective": dossier.objective,
        "verdict": [c.text for c in dossier.constraints
                    if c.severity in ("error", "warning")][:1],
        "facts": [asdict(f) for f in dossier.facts],
        "constraints": [asdict(c) for c in dossier.constraints],
        "actions": [asdict(a) for a in dossier.actions],
        "missing": dossier.missing,
        "passes_run": dossier.passes_run,
    }


if __name__ == "__main__":
    # Self-check : la compilation d'un audit au format PROMPTS/audit_convention.md
    # doit produire faits, verdict, actions et détecter les informations manquantes.
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # console Windows + emojis
    _AUDIT = """# Audit - Convention Test
**Date :** 2026-07-31

## Verdict global
🔴 - Plusieurs clauses bloquantes.

## Constats

### 1. Clause 3 - Taux d'interet
- **Texte :** "Taux de 12% annuel"
- **Constat :** 🔴 bloquant - taux au-dessus du plafond legal, à confirmer par un juriste
- **Règle applicable :** Taux usure (seuil legal)
- **Impact :** Nullite de la clause
- **Recommandation :** Revoir le taux ou joindre la derogation

### 2. Clause 8 - Garantie
- **Texte :** "Cession sur salaire"
- **Constat :** 🟡 a clarifier - cession non confirmée par le Tribunal Cantonal
- **Règle applicable :** Notification Paierie Generale
- **Impact :** Opposabilite
- **Recommandation :** Verifier la notification

## Points positifs
- Duree conforme au plafond reglementaire

## Questions ouvertes
- Le tiers saisissable est-il respecte ?"""

    _d = compile_dossier(_AUDIT)
    assert "Audit - Convention Test" in _d.objective, "objective non extrait"
    assert sum(f.kind == "constat" for f in _d.facts) == 2, "2 constats attendus"
    assert sum(f.kind == "regle" for f in _d.facts) == 2, "2 regles attendues"
    assert any(a.priority == 0 for a in _d.actions), "action prioritaire attendue"
    assert any(c.severity == "error" for c in _d.constraints), "verdict 🔴 → constraint error"
    assert len(_d.missing) >= 1, "informations manquantes detectees"
    assert all(f.text.strip() for f in _d.facts), "aucun fait vide"
    assert "validate.dossier" in _d.passes_run, "toutes les passes executees"
    print(f"Self-check OK - {len(_d.facts)} faits, {len(_d.missing)} manques, "
          f"{len(_d.actions)} actions, verdict {render_json(_d)['verdict']}")
