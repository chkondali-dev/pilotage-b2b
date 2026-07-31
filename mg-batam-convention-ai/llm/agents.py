"""
Agents — les 5 personas SMG exécutés via LLM local.
Les définitions complètes vivent dans AGENTS/*.md (source unique, chargée ici).
Équivalent de metrics/kpi.py dans le dashboard : la logique métier, centralisée.
"""
from pathlib import Path
from llm import client, config

_ROLE_FILE = {
    "juriste": "juriste.md",
    "negociateur": "negociateur.md",
    "contradicteur": "contradicteur.md",
    "comex": "comex.md",
    "redacteur": "redacteur.md",
}


def _system_prompt(role: str) -> str:
    """Charge AGENTS/<role>.md comme prompt système."""
    return (config.AGENTS_DIR / _ROLE_FILE[role]).read_text(encoding="utf-8")


def audit(document: str, chemin: str = "") -> str | None:
    """Audit clause par clause. Retourne le rapport markdown."""
    prompt = f"""Audite la convention suivante clause par clause, au format de PROMPTS/audit_convention.md.

Document : {chemin or "(fourni ci-dessous)"}

{document}

Rappel du format attendu :
- Verdict global (🟢/🟠/🔴)
- Constats par clause : texte exact, constat (🔴 bloquant / 🟠 risqué / 🟡 à clarifier), règle applicable, impact, recommandation
- Points positifs
- Questions ouvertes

Sois factuel. Cite toujours le texte exact de la clause avant de commenter."""
    return client.chat(prompt, role="analyse", system=_system_prompt("juriste"))


def contre_audit(rapport: str, document: str = "") -> str | None:
    """Relit un audit et cherche les failles. Retourne le contre-audit."""
    prompt = f"""Relis cet audit et le document source. Cherche les failles, angles morts et hypothèses non vérifiées.

Document source :
{document or "(non fourni — base-toi sur l'audit)"}

Audit à critiquer :
{rapport}

Format attendu :
- Liste priorisée des failles : 🔴 bloquant / 🟠 risqué / 🟡 mineur
- Pour chacune : probabilité, impact chiffré si possible, scénario de déclenchement
- Questions que l'expert métier n'a pas encore posées

Ne valide jamais un document sans avoir trouvé au moins un point d'amélioration."""
    return client.chat(prompt, role="analyse", system=_system_prompt("contradicteur"))


def analyse_risque(document: str, chemin: str = "") -> str | None:
    """Analyse le risque selon la grille SMG. Retourne le rapport."""
    prompt = f"""Analyse le risque de cette convention selon la grille SMG, au format de PROMPTS/analyse_risque.md.

Document : {chemin or "(fourni ci-dessous)"}

{document}

Grille de risque SMG :
- Cession sur salaire + bonne tendance → faible
- Garantie solidaire seule ou tendance irrégulière → moyen
- Baisse continue 2+ mois OU lettre de change seule → élevé

Points à vérifier en priorité :
- Cession confirmée par le Tribunal Cantonal ?
- Notification à la Paierie Générale ?
- Respect du tiers saisissable ?
- Cohérence des montants (taux, échéancier, plafond)

Format attendu : profil de garantie, exposition, risque global (🟢/🟠/🔴), recommandation (reconduire/renégocier/surveiller/relancer urgent/suspendre)."""
    return client.chat(prompt, role="analyse", system=_system_prompt("juriste"))


def comparer(version_a: str, version_b: str) -> str | None:
    """Compare deux versions d'un document. Retourne la table de différences."""
    prompt = f"""Compare ces deux versions d'un même document, au format de PROMPTS/comparaison_versions.md.

VERSION A :
{version_a}

VERSION B :
{version_b}

Format attendu :
- Table des différences : clause | version A | version B | impact (🔴/🟠/🟡) | recommandation
- Extrait exact pour chaque différence
- Résumé : combien de clauses modifiées, à l'avantage ou au désavantage de SMG
- Points d'attention : clauses nouvelles, supprimées, changements de montants/taux/durée"""
    return client.chat(prompt, role="analyse", system=_system_prompt("redacteur"))


def preparer_negociation(contexte: str, document: str = "") -> str | None:
    """Prépare la stratégie de négociation. Retourne la fiche."""
    prompt = f"""Prépare la stratégie de négociation complète, au format de PROMPTS/preparation_negociation.md.

Contexte fourni par l'expert métier :
{contexte}

{document}

Format attendu :
- Enjeux (CA annuel, historique)
- Positions intouchables / négociables / cadeaux
- BATNA
- Seuil de rupture chiffré
- 3-5 contre-offres anticipées avec réponse type
- Questions à poser en réunion

Règles : jamais de concession sur une position intouchable sans validation comex. Donnant-donnant."""
    return client.chat(prompt, role="negociation", system=_system_prompt("negociateur"))


def synthese_comex(dossier: str) -> str | None:
    """Tranche une décision à partir des avis des agents. Retourne la décision."""
    prompt = f"""Produis la synthèse exécutive et la décision finale, au format de PROMPTS/synthese_comex.md.

Dossier complet (avis des agents, contexte) :
{dossier}

Format attendu :
- Situation en une phrase
- Tableau des avis des agents (position + justification)
- Décision : ✅ valider / ✏️ modifier / ❌ rejeter / ⏳ différer, avec justification 2-3 lignes
- Conditions éventuelles
- Prochaine échéance

Règles : la décision se base sur garantie confirmée, historique, tendance, exposition. Tranche en citant les positions divergentes."""
    return client.chat(prompt, role="comex", system=_system_prompt("comex"))


def rediger(prompt_user: str) -> str | None:
    """Rédaction juridique — passe par Groq si dispo (qualité), sinon local."""
    prompt = f"""{prompt_user}

Structure attendue : Préambule → Objet → Définitions → Articles (obligations, garanties, durée, résiliation, litiges) → Signatures.
Règles : jamais de chiffre inventé (champ ________ si inconnu). Mentionner le mécanisme de cession sur salaire (Tribunal Cantonal, Paierie Générale) quand il s'applique."""
    return client.chat(prompt, role="redaction", system=_system_prompt("redacteur"))
