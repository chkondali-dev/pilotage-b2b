"""
scenarios.py — Brique métier : matrice des 7 scénarios SMG (framework v2.0).

Source : KNOWLEDGE/reference/framework_conventions_smg.md (FRAMEWORK_CONVENTIONS_SMG.md
v2.0, juillet 2026). Cette brique porte la partie CALCULABLE du framework :
arbre de sélection (B2), paramètres contractuels (C2), gate de production (D).
La rédaction du texte reste confiée au LLM piloté par le workflow.

Usage :
    python -m business.scenarios            # self-check
"""

import re
import sys
import unicodedata

# ── Matrice des 7 scénarios (framework v2.0, C2) ─────────────────

SCENARIOS: dict[str, dict] = {
    "01": {
        "titre": "Privé avec Amicale",
        "regime": "Classique",
        "garantie": "Cession sur salaire + caution employeur",
        "plafond": (300, 3000),
        "duree_mois": 18,
        "taux": 0.75,
        "circuit": "Employé → Employeur → Amicale → SMG",
        "rfa": "Ristourne de Fin d'Année (RFA) : possible (A + TC), progressive 0,5 % → 1 % → 1,5 %",
        "seuil_40": True,
        "condition_suspensive": False,
        "recouvrement": "Recours cambiaire · injonction de payer · action directe",
        "signataires": ("Directeur Général SMG", "Président de l'Amicale",
                        "DRH (validation employeur)", "DSC (sous-cas B)"),
        "qualites": "المستفيد / المنخرط",
    },
    "02": {
        "titre": "Privé sans Amicale",
        "regime": "Classique",
        "garantie": "Cession sur salaire + caution employeur",
        "plafond": (300, 3000),
        "duree_mois": 18,
        "taux": 0.75,
        "circuit": "Employé → Employeur → SMG",
        "rfa": "Ristourne de Fin d'Année (RFA) : possible (TC), progressive 0,5 % → 1 % → 1,5 %",
        "seuil_40": True,
        "condition_suspensive": False,
        "recouvrement": "Recours cambiaire · injonction de payer · action directe",
        "signataires": ("Directeur Général SMG", "DRH / Dirigeant employeur"),
        "qualites": "المستفيد / المنخرط",
    },
    "03": {
        "titre": "Administration publique",
        "regime": "Classique",
        "garantie": "Cession sur salaire (sans caution — droit public)",
        "plafond": (300, 3000),
        "duree_mois": 12,
        "taux": 0.75,
        "circuit": "Employé → Administration → SMG",
        "rfa": "Ristourne de Fin d'Année (RFA) : NON écrite (interdit)",
        "seuil_40": True,
        "condition_suspensive": False,
        "recouvrement": "Injonction de payer · action directe",
        "signataires": ("Directeur Général SMG", "DRH / Directeur financier de l'administration"),
        "qualites": "المستفيد / المنخرط",
    },
    "04": {
        "titre": "Amicale seule (sans employeur)",
        "regime": "Classique",
        "garantie": "Caution employeur OBLIGATOIRE + reconnaissance de dette",
        "plafond": (300, 3000),
        "duree_mois": 18,
        "taux": 0.75,
        "circuit": "Employé → Amicale → SMG",
        "rfa": "Ristourne de Fin d'Année (RFA) : possible si TC",
        "seuil_40": True,
        "condition_suspensive": False,
        "recouvrement": "Injonction de payer · action directe",
        "signataires": ("Directeur Général SMG", "Président de l'Amicale"),
        "qualites": "المستفيد / المنخرط",
        "regle_absolue": "Jamais de convention Amicale seule sans caution employeur (règle absolue).",
    },
    "05": {
        "titre": "Organismes (Ordres professionnels / Associations)",
        "regime": "PLUS",
        "garantie": "Traite individuelle + reconnaissance de dette",
        "plafond": (300, 3000),
        "duree_mois": 12,
        "taux": 0.75,
        "circuit": "Adhérent → Ordre / Association → SMG",
        "rfa": "Ristourne de Fin d'Année (RFA) : JAMAIS",
        "seuil_40": False,
        "condition_suspensive": True,
        "recouvrement": "Recours cambiaire (traite) · injonction de payer",
        "signataires": ("Directeur Général SMG", "Président de l'Ordre / de l'Association"),
        "qualites": "المنخرط",
    },
    "06": {
        "titre": "Groupe multi-sociétés",
        "regime": "Classique",
        "garantie": "Cession sur salaire + caution solidaire de la holding",
        "plafond": (500, 3000),
        "duree_mois": 18,
        "taux": 0.75,
        "circuit": "Employé → Filiale → Holding → SMG",
        "rfa": "Ristourne de Fin d'Année (RFA) : progressive 0,5 % → 1 % → 1,5 %",
        "seuil_40": True,
        "condition_suspensive": False,
        "recouvrement": "Recours cambiaire · injonction de payer · action directe",
        "signataires": ("Directeur Général SMG", "Représentant de la holding"),
        "qualites": "المستفيد / المنخرط",
        "regle_absolue": "Convention-cadre + avenants par filiale · clause de non-cession obligatoire.",
    },
    "07": {
        "titre": "Mutuelle",
        "regime": "PLUS",
        "garantie": "Engagement solidaire de la mutuelle + traite + reconnaissance de dette",
        "plafond": (300, 3000),
        "duree_mois": 18,
        "taux": 0.75,
        "circuit": "Adhérent → Mutuelle → SMG",
        "rfa": "Ristourne de Fin d'Année (RFA) : possible si levier",
        "seuil_40": False,
        "condition_suspensive": True,
        "recouvrement": "Recours cambiaire · injonction de payer",
        "signataires": ("Directeur Général SMG", "Dirigeant de la mutuelle"),
        "qualites": "المنخرط",
    },
}

# Terminologie impérative (framework v2.0, A) — « cession sur salaire »,
# « Ristourne de Fin d'Année (RFA) » ; jamais les termes ci-dessous.
TERMES_INTERDITS = (
    "cession de créance", "cession de creance", "dailly",
    "réserve de fonds d'avances", "reserve de fonds d'avances",
)

_PATTERNS = {
    "administration": re.compile(r"administr|ministere|etat|publique|tutelle|fonctionnaire"),
    "mutuelle": re.compile(r"mutuelle|prevoyance"),
    "organisme": re.compile(r"ordre (des|de|du)|organisme professionnel|association professionnelle|chambre"),
    "groupe": re.compile(r"groupe|holding|filiale"),
    "amicale": re.compile(r"amicale|association du personnel|personnel cnam|comite d.entreprise"),
    "type_morale": re.compile(r"personne morale|societe anonyme|sarl|entreprise|organisme|mutuelle|association"),
    "employeur_garant": re.compile(r"garantit|garantie employeur|caution de l.employeur|prend en charge|signe la caution"),
    "employeur_refuse": re.compile(r"refuse|sans garantie|ne garantit pas|sans caution|refuse de"),
}


def _sans_accents(t: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFD", t)
                   if unicodedata.category(ch) != "Mn")


def extraire_profil(contexte: str) -> dict:
    """Qualification du client depuis le contexte libre (déterministe, sans LLM)."""
    c = _sans_accents(contexte.lower())
    profil = {
        "type": "morale" if _PATTERNS["type_morale"].search(c) else "physique",
        "administration": bool(_PATTERNS["administration"].search(c)),
        "mutuelle": bool(_PATTERNS["mutuelle"].search(c)),
        "organisme": bool(_PATTERNS["organisme"].search(c)),
        "groupe": bool(_PATTERNS["groupe"].search(c)),
        "amicale": bool(_PATTERNS["amicale"].search(c)),
        "employeur_garant": None,
    }
    if _PATTERNS["employeur_refuse"].search(c):
        profil["employeur_garant"] = False
    elif _PATTERNS["employeur_garant"].search(c):
        profil["employeur_garant"] = True
    if profil["type"] == "physique" and profil["administration"]:
        profil["employeur_garant"] = True  # l'administration prélève toujours (scénario 03)
    profil["indetermine"] = (
        (profil["type"] == "physique" and profil["amicale"]
         and profil["employeur_garant"] is None)
        or (profil["type"] == "morale" and not any(
            (profil["mutuelle"], profil["organisme"], profil["groupe"], profil["amicale"])))
    )
    return profil


def choisir_scenario(profil: dict) -> str | None:
    """Arbre de sélection B2 du framework v2.0 → numéro de scénario (None si hors matrice)."""
    if profil.get("type") == "physique":
        if profil.get("administration"):
            return "03"
        if profil.get("amicale"):
            return "01" if profil.get("employeur_garant") else "04"
        return "02"
    if profil.get("mutuelle"):
        return "07"
    if profil.get("organisme"):
        return "05"
    if profil.get("groupe"):
        return "06"
    if profil.get("amicale"):
        return "04"
    return None


def parametres_scenario(num: str) -> dict:
    """Paramètres contractuels du scénario (framework v2.0, C2)."""
    return SCENARIOS[num]


# ── Gate de production (checklist D1) — déterministe ──────────────

def verifier_production(texte: str, num: str) -> list[dict]:
    """Checklist de production D1 : écarts bloquants (erreur) et points à confirmer (warning).

    Chaque check : {"check", "ok", "severity" ("erreur"|"warning"), "detail"}.
    """
    s = SCENARIOS[num]
    t = _sans_accents(texte.lower())
    checks: list[dict] = []

    def add(nom: str, ok: bool, detail: str, severity: str = "erreur"):
        checks.append({"check": nom, "ok": ok, "severity": severity, "detail": detail})

    # 1. Terminologie impérative (A) — zéro terme interdit (cession de créance, RFA fautive…)
    interdit = [x for x in TERMES_INTERDITS if _sans_accents(x.lower()) in t]
    add("Terminologie", not interdit,
        f"Termes interdits détectés : {', '.join(interdit)}" if interdit
        else "Aucun terme interdit — 'cession sur salaire' / 'Ristourne de Fin d'Année' cohérents")

    # 2. Garantie principale actée dans le texte
    if "cession sur salaire" in s["garantie"]:
        add("Garantie principale", "cession sur salaire" in t,
            "la convention doit acter la cession sur salaire")
    if "caution" in s["garantie"] and s["regime"] == "Classique":
        add("Caution", "caution" in t, f"caution prévue par le scénario {num}")

    # 3. Condition suspensive (régime PLUS : traite + reconnaissance de dette)
    if s["condition_suspensive"]:
        ok = ("traite" in t or "lettre de change" in t) and "reconnaissance de dette" in t
        add("Condition suspensive (PLUS)", ok,
            "traite + reconnaissance de dette requis" if not ok
            else "traite + reconnaissance de dette présents")

    # 4. Seuil 40 % (taux d'endettement) — non applicable aux régimes PLUS 05/07
    if s["seuil_40"]:
        add("Seuil 40 % (endettement)", "40" in t,
            "taux d'endettement 40 % à mentionner", severity="warning")

    # 5. Plafond / taux / durée (valeurs du scénario)
    add("Plafond", str(s["plafond"][1]) in t,
        f"plafond {s['plafond'][0]}–{s['plafond'][1]} TND", severity="warning")
    add("Taux", "0,75" in t or "0.75" in t, "taux 0,75 %/mois", severity="warning")
    add("Durée", f"{s['duree_mois']} mois" in t,
        f"durée {s['duree_mois']} mois", severity="warning")

    # 6. Règles absolues (04 : caution obligatoire · 06 : convention-cadre + non-cession)
    if num == "04":
        add("Règle absolue (04)", "caution" in t,
            "jamais de convention Amicale seule sans caution employeur")
    if num == "06":
        add("Clause non-cession", "non-cession" in t or "ne peut ceder" in t
            or "ne peut céder" in texte.lower(),
            "clause de non-cession obligatoire pour le groupe", severity="warning")

    # 7. Signature du Directeur Général
    add("Signature DG", "directeur general" in t,
        "signature du Directeur Général requise", severity="warning")

    return checks


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Arbre de sélection : chaque profil → scénario attendu
    for profil, attendu in [
        ({"type": "physique", "administration": True}, "03"),
        ({"type": "physique", "amicale": True, "employeur_garant": True}, "01"),
        ({"type": "physique", "amicale": True, "employeur_garant": False}, "04"),
        ({"type": "physique", "amicale": False, "employeur_garant": False}, "02"),
        ({"type": "morale", "mutuelle": True}, "07"),
        ({"type": "morale", "organisme": True}, "05"),
        ({"type": "morale", "groupe": True}, "06"),
        ({"type": "morale"}, None),
    ]:
        r = choisir_scenario(profil)
        print(f"  {profil} → {r}")
        assert r == attendu, f"{profil} → {r} (attendu {attendu})"

    # Qualification depuis un contexte libre
    p = extraire_profil("Employé du Ministère de l'Intérieur, administration publique, fonctionnaire")
    assert p["type"] == "physique" and p["administration"] and p["employeur_garant"] is True, p
    p = extraire_profil("Mutuelle de prévoyance des avocats, adhérents à financer")
    assert p["type"] == "morale" and p["mutuelle"], p
    p = extraire_profil("Salarié d'une société privée, amicale du personnel existante")
    assert p["indetermine"] is True and p["amicale"], p

    # Gate de production : texte conforme → aucun erreur ; texte fautif → erreur
    bon = ("Convention de cession sur salaire entre SMG et l'Amicale du personnel. "
           "Caution employeur signée par la DRH. Ristourne de Fin d'Année (RFA) prévue. "
           "Plafond de 3000 TND, durée 18 mois, taux 0,75 % par mois, "
           "taux d'endettement ne dépassant pas 40 %, "
           "signée par le Directeur Général et le Président de l'Amicale.")
    err = [c for c in verifier_production(bon, "01")
           if c["severity"] == "erreur" and not c["ok"]]
    for c in err:
        print("  ❌ inattendu :", c)
    assert not err, "gate a rejeté un texte conforme"
    mauvais = "Convention de cession de créance… Réserve de Fonds d'Avances à hauteur de…"
    assert any(not c["ok"] for c in verifier_production(mauvais, "01")
               if c["severity"] == "erreur"), "termes interdits non détectés"
    print("Self-check OK")
