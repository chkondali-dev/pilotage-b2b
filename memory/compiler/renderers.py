"""
renderers.py — Renderers separes du modele (dossier).

RendererPrompt  → str (format prompt LLM)
RendererJSON    → dict (format JSON structure)
render_to_*     → fonctions libres (API fonctionnelle)
"""

from .types import ReasoningDossier


class RendererPrompt:
    """Rend le dossier au format prompt pour LLM."""

    def render(self, dossier: ReasoningDossier) -> str:
        parts = []
        sep = "=" * 55
        parts.append(sep)
        parts.append(f"INTENT  {dossier.intent.value.upper()}")
        parts.append("")
        parts.append("OBJECTIF")
        parts.append(f"  {dossier.objective}")
        parts.append("")

        if dossier.facts:
            parts.append("FAITS")
            for f in dossier.facts:
                file_tag = f" [{f.file}]" if f.file and f.file not in f.text else ""
                meta = ""
                if f.category:
                    badge = {"critical": "[!]", "important": "[*]", "context": "[i]", "secondary": "[ ]"}
                    meta += f" {badge.get(f.category, '[?]')}"
                if f.tags:
                    meta += f" ({','.join(f.tags[:3])})"
                parts.append(f"  {f.text}{file_tag}{meta}")
            parts.append("")

        if dossier.constraints:
            parts.append("CONTRAINTES")
            for c in dossier.constraints:
                badge = {"info": "i", "warning": "!", "error": "X"}.get(c.severity, "i")
                parts.append(f"  [{badge}] {c.text}")
            parts.append("")

        if dossier.hypotheses:
            parts.append("HYPOTHESES")
            for h in dossier.hypotheses:
                pct = f" ({h.confidence:.0%})" if h.confidence != 0.5 else ""
                parts.append(f"  * {h.text}{pct}")
            parts.append("")

        if dossier.signals:
            parts.append("SIGNAUX")
            for s in dossier.signals:
                parts.append(f"  ~ {s}")
            parts.append("")

        if dossier.actions:
            parts.append("ACTIONS")
            for i, a in enumerate(dossier.actions, 1):
                parts.append(f"  {i}. {a.text}")
            parts.append("")

        if dossier.options:
            parts.append("OPTIONS")
            for o in dossier.options:
                parts.append(f"  * {o}")
            parts.append("")

        if dossier.risks:
            parts.append("RISQUES")
            for r in dossier.risks:
                parts.append(f"  * {r}")
            parts.append("")

        if dossier.metrics:
            parts.append("METRIQUES")
            for k, v in dossier.metrics.items():
                parts.append(f"  * {k}: {v}")
            parts.append("")

        if dossier.recommendations:
            parts.append("RECOMMANDATIONS")
            for i, r in enumerate(dossier.recommendations, 1):
                label = r.get("action", r.get("texte", str(r)))[:120]
                parts.append(f"  {i}. {label}")
            parts.append("")

        if dossier.artifacts:
            parts.append("ARTEFACTS")
            for a in dossier.artifacts:
                parts.append(f"  * {a}")
            parts.append("")

        parts.append(sep)
        return "\n".join(parts)


class RendererJSON:
    """Rend le dossier en JSON structure."""

    def render(self, dossier: ReasoningDossier) -> dict:
        return {
            "intent": dossier.intent.value,
            "objective": dossier.objective,
            "facts": [
                {"text": f.text, "kind": f.kind.value, "confidence": f.confidence,
                 "symbol": f.symbol, "file": f.file, "line": f.line}
                for f in dossier.facts
            ],
            "constraints": [
                {"text": c.text, "severity": c.severity} for c in dossier.constraints
            ],
            "hypotheses": [
                {"text": h.text, "confidence": h.confidence} for h in dossier.hypotheses
            ],
            "signals": dossier.signals,
            "actions": [{"text": a.text, "priority": a.priority} for a in dossier.actions],
            "options": dossier.options,
            "risks": dossier.risks,
            "metrics": dossier.metrics,
            "recommendations": dossier.recommendations,
            "artifacts": dossier.artifacts,
        }


# ── API fonctionnelle ──────────────────────────────────

def render_to_prompt(dossier: ReasoningDossier) -> str:
    """Fonction libre : dossier -> prompt."""
    return RendererPrompt().render(dossier)


def render_to_dict(dossier: ReasoningDossier) -> dict:
    """Fonction libre : dossier -> dict JSON."""
    return RendererJSON().render(dossier)
