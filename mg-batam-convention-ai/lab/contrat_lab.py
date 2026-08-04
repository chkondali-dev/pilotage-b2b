"""
contrat_lab.py — Moteur du Contrat Lab (MG Convention Suite).

Wizard d'aide à la décision : réponses du prospect → scénario framework v2.0
(paramètres officiels, garanties, risque) → génération du dossier client
(data/dossiers/<slug>.md) → défense par le brain (llm/brain.py).

Source de vérité : KNOWLEDGE/reference/framework_conventions_smg.md (v2.0)
+ KNOWLEDGE/procedures/politique_risque.md (niveaux de sûretés §2, grille §3).

Le nombre de niveaux coïncide avec la politique de risque :
    niveau 1 = cession TC + caution → faible      (01-A, 02, 06)
    niveau 2 = cession seule          → moyen     (03)
    niveau 3 = traite avalisée + RD   → modéré    (07)
    niveau 4 = traite + RD sans 40 %  → élevé     (01-B, 04, 05)

Self-check : python -X utf8 -m lab.contrat_lab
"""
from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DOSSIERS_DIR = ROOT / "data" / "dossiers"
DOSSIERS_DIR.mkdir(parents=True, exist_ok=True)

# ── Scénarios du framework v2.0 (paramètres officiels) ────────────
SCENARIOS: dict[str, dict] = {
    "01": {
        "name": "Privé avec Amicale", "type": "Classique",
        "garantie": "Cession sur salaire TC + caution employeur",
        "plafond": "300 – 3 000 TND", "duree": "18 mois", "taux": "0,75%/mois",
        "rfa": "Uniquement sous-cas A + TC", "flow": "Employé → Employeur → Amicale → SMG",
        "niveau": 1, "risque": "faible",
        "clauses": ["Caution solidaire de l'employeur",
                    "Acte de cession sur salaire légalisé Tribunal Cantonal",
                    "Double signature : Président Amicale + DRH",
                    "Clause de révision du taux selon TMM",
                    "Suspension immédiate des ventes si impayé",
                    "Décès/départ : notification 5j, solde 30j"],
        "pieges": ["Signer avec l'Amicale sans caution société",
                   "Reconnaissance de dette simple sans légalisation",
                   "Absence de clause de révision du taux"],
    },
    "01b": {
        "name": "Privé avec Amicale B (employeur refuse la caution)", "type": "Classique",
        "garantie": "Traite de garantie obligatoire", "plafond": "300 – 3 000 TND",
        "duree": "18 mois", "taux": "0,75%/mois", "rfa": "Non",
        "flow": "Employé → Employeur → Amicale → SMG", "niveau": 4, "risque": "élevé",
        "clauses": ["Traite de garantie obligatoire (compense l'absence de caution)",
                    "Validation Dir. Service Clients obligatoire",
                    "Acte de cession sur salaire si l'employeur accepte le TC",
                    "Suspension immédiate des ventes si impayé"],
        "pieges": ["Sous-cas B sans traite = risque maximum",
                   "Oublier la validation DSC",
                   "Employeur non engagé = aucun recours"],
    },
    "02": {
        "name": "Privé sans Amicale", "type": "Classique",
        "garantie": "Cession sur salaire TC + caution employeur",
        "plafond": "300 – 3 000 TND", "duree": "18 mois", "taux": "0,75%/mois",
        "rfa": "Si levier (1 %, conditions)", "flow": "Employé → Employeur → SMG",
        "niveau": 1, "risque": "faible",
        "clauses": ["Caution solidaire de l'employeur",
                    "Acte de cession sur salaire légalisé TC",
                    "Signature unique DRH + spécimen + suppléant RH obligatoire",
                    "Suspension immédiate des ventes si impayé"],
        "pieges": ["Pas d'intermédiaire pour filtrer les demandes",
                   "Turn-over RH = risque de désorganisation"],
    },
    "02pme": {
        "name": "PME (< 20 employés)", "type": "Classique",
        "garantie": "Cession sur salaire TC + caution personnelle dirigeant",
        "plafond": "Fixé selon analyse", "duree": "18 mois", "taux": "0,75%/mois",
        "rfa": "Si levier (1 %, conditions)", "flow": "Employé → Dirigeant → SMG",
        "niveau": 1, "risque": "faible",
        "clauses": ["Caution personnelle solidaire du dirigeant",
                    "Acte de cession sur salaire légalisé TC",
                    "Convention simplifiée (10 articles)"],
        "pieges": ["Alourdir avec les clauses d'une convention 500 personnes",
                   "Accepter sans caution personnelle du dirigeant"],
    },
    "02inter": {
        "name": "Privé — International", "type": "Classique",
        "garantie": "Cession + traite (filiale tunisienne)",
        "plafond": "300 – 3 000 TND", "duree": "18 mois", "taux": "0,75%/mois",
        "rfa": "Si levier (1 %, conditions)", "flow": "Employé → Filiale Tunisie → SMG",
        "niveau": 1, "risque": "faible",
        "clauses": ["Élection de domicile en Tunisie",
                    "Droit tunisien exclusif",
                    "Caution : filiale tunisienne ou représentant légal",
                    "RIB sur banque tunisienne, tous montants en TND"],
        "pieges": ["Maison mère étrangère sans élection de domicile",
                   "Caution de la maison mère irrecevable sans domicile en Tunisie",
                   "Paiement en devise étrangère"],
    },
    "03": {
        "name": "Administration publique", "type": "Classique",
        "garantie": "Cession sur salaire TC seule (droit public)",
        "plafond": "300 – 3 000 TND", "duree": "12 mois", "taux": "0,75%/mois",
        "rfa": "Non écrite (possible en nature hors contrat)",
        "flow": "Agent → Administration RH → SMG", "niveau": 2, "risque": "moyen",
        "clauses": ["Tribunal Cantonal obligatoire (cession art. 142 CT)",
                    "Traite de garantie en renfort du TC (jamais en remplacement)",
                    "Délai de virement : 15e jour du mois",
                    "Résiliation 30 jours"],
        "pieges": ["Demander une caution solidaire (impossible en droit public)",
                   "Pénalités de retard (non applicables aux personnes publiques)"],
    },
    "04": {
        "name": "Amicale seule", "type": "Classique",
        "garantie": "Caution solidaire obligatoire + traite + RD",
        "plafond": "300 – 3 000 TND", "duree": "18 mois", "taux": "0,75%/mois",
        "rfa": "Si TC obtenu (1 %, conditions)", "flow": "Employé → Amicale → SMG",
        "niveau": 4, "risque": "élevé",
        "clauses": ["Caution solidaire de l'Amicale OBLIGATOIRE",
                    "Traite de garantie obligatoire",
                    "Reconnaissance de dette légalisée (municipalité)",
                    "Vérification du patrimoine et de la capacité financière",
                    "Changement de bureau : notification sous 15 jours"],
        "pieges": ["Signer sans caution ni traite",
                   "Accepter un bureau en fin de mandat",
                   "Ne pas vérifier la capacité financière de l'Amicale"],
    },
    "05": {
        "name": "Organismes (Ordre professionnel / Association)", "type": "PLUS",
        "garantie": "Traite individuelle + reconnaissance de dette légalisée",
        "plafond": "300 – 3 000 TND", "duree": "12 mois", "taux": "0,75%/mois",
        "rfa": "Jamais (Convention PLUS pure)", "flow": "Adhérent → Ordre/Association → SMG",
        "niveau": 4, "risque": "élevé",
        "clauses": ["Condition suspensive absolue : traite signée ET RD légalisée",
                    "Qualité débiteur : المنتسب (Ordre) / المنخرط (Association)",
                    "Recours cambiaire direct + injonction de payer",
                    "Vérification revenus sur 12 mois minimum"],
        "pieges": ["Livrer sans traite signée et RD légalisée",
                   "Prêter à un professionnel en début d'activité (< 2 ans)",
                   "S'appuyer sur la réputation de l'Ordre"],
    },
    "06": {
        "name": "Groupe multi-sociétés", "type": "Classique",
        "garantie": "Caution solidaire de la holding (jamais les filiales)",
        "plafond": "500 – 3 000 TND/filiale", "duree": "18 mois", "taux": "0,75%/mois",
        "rfa": "Progressive 0,5 % → 1 % → 1,5 %", "flow": "Employé → Filiale → Holding → SMG",
        "niveau": 1, "risque": "faible",
        "clauses": ["Caution solidaire de la holding pour toutes les filiales",
                    "Convention-cadre + annexe par filiale",
                    "Clause de non-cession obligatoire",
                    "Actualisation annuelle de la liste des filiales",
                    "Filiale cédée reste tenue des encours"],
        "pieges": ["Caution de la holding insuffisante",
                   "Filiale cédée sans clause de maintien des encours",
                   "Mélanger les conditions entre filiales"],
    },
    "07": {
        "name": "Mutuelle", "type": "PLUS",
        "garantie": "Engagement solidaire + traite de garantie globale + RD",
        "plafond": "300 – 3 000 TND", "duree": "18 mois", "taux": "0,75%/mois",
        "rfa": "Si levier de négociation (1 %, conditions)",
        "flow": "Adhérent → Mutuelle → SMG", "niveau": 3, "risque": "modéré",
        "clauses": ["Engagement solidaire de la mutuelle",
                    "Traite de garantie globale (+ RD légalisée)",
                    "Nantissement de parts sociales pour les sociétaires",
                    "Condition suspensive absolue avant livraison",
                    "Notification de toute modification des statuts"],
        "pieges": ["Mélanger employés et sociétaires dans les mêmes conditions",
                   "Accepter des engagements sans décision du CA"],
    },
}

# questions → clé de scénario (ordre du wizard HTML, aligné framework B2)
_MAPPING = {
    # type → (clé si amicale non pertinente, question suivante)
    "prive": "PRIVE",
    "admin": "03",
    "ordre": "05",
    "asso": "05",
    "groupe": "06",
    "mutuelle": "07",
}


def _qualifier(reponses: dict) -> dict | None:
    """Réponses du wizard → scénario framework (+ variante)."""
    t = reponses.get("type")
    if t == "admin":
        return SCENARIOS["03"]
    if t == "ordre" or t == "asso":
        return SCENARIOS["05"]
    if t == "groupe":
        return SCENARIOS["06"]
    if t == "mutuelle":
        return SCENARIOS["07"]
    # privé
    if t == "prive":
        amicale = reponses.get("amicale")
        if amicale == "oui-avec":
            return SCENARIOS["01"]
        if amicale == "oui-sans":
            return SCENARIOS["01b"]
        if amicale == "seule":
            return SCENARIOS["04"]
        # pas d'amicale → variante taille / international
        if reponses.get("international") == "oui":
            return SCENARIOS["02inter"]
        if reponses.get("taille") == "pme":
            return SCENARIOS["02pme"]
        return SCENARIOS["02"]
    return None


def generer_dossier(reponses: dict, client: str) -> tuple[Path, dict]:
    """Génère data/dossiers/<slug>.md au format des dossiers existants.

    Retourne (chemin, scénario). Le fichier est défendable tel quel par
    le brain (fait pivot niveau de sûreté via la section garanties).
    """
    sc = _qualifier(reponses)
    if sc is None:
        raise ValueError(f"Profil non qualifiable : {reponses}")

    slug = re.sub(r"[^a-z0-9]+", "_", client.strip().lower()).strip("_") or "client"
    path = DOSSIERS_DIR / f"{slug}.md"

    t = reponses.get("type")
    type_label = {
        "prive": "Société privée (SA/SARL)", "admin": "Administration publique",
        "ordre": "Ordre professionnel", "asso": "Association / ONG / Syndicat",
        "groupe": "Groupe multi-sociétés", "mutuelle": "Coopérative / Mutuelle",
    }.get(t, t)

    clauses = "\n".join(f"- {c}" for c in sc["clauses"])
    pieges = "\n".join(f"- {p}" for p in sc["pieges"])
    niveau = sc["niveau"]
    risque = sc["risque"]

    md = f"""# Dossier de convention — {client}

> **Contrat Lab** — généré le {datetime.now().strftime('%Y-%m-%d %H:%M')}.
> Étape 4 du process : défense du dossier (framework SMG v2.0).

## 1. Identification du client

| Élément | Valeur |
|---------|--------|
| Client | **{client}** |
| Profil | {type_label} |
| Scénario | **{sc['name']}** |
| Régime | **{sc['type']}** |

## 2. Paramètres contractuels (référence Framework C2 · C3)

| Paramètre | Valeur |
|-----------|--------|
| Plafond de crédit | {sc['plafond']} |
| Durée maximale | {sc['duree']} |
| Taux d'intérêt | {sc['taux']} |
| RFA | {sc['rfa']} |

## 3. Garanties du dossier (verrou risque)

1. Trame du scénario : {sc['garantie']}.
2. **Niveau {niveau} de sûretés** selon la politique de risque §2
   (niveau {niveau} → risque {risque}).
3. Circuit de paiement : {sc['flow']}.

Clauses obligatoires :
{clauses}

## 4. Maîtrise du risque (politique de risque §3)

- **Risque estimé : {risque}** ({sc['garantie'].split(' + ')[0]}{' + caution solidaire' if niveau == 1 else ''}).
- Seuil 40 % (art. 142 CT) vérifié lorsque le débiteur est salarié.
- Critère de refus du §4 contrôlé (profil solvable, pas d'impayés).

## 5. Pièges à éviter (matrice des formules)

{pieges}

## 6. Éléments à confirmer (avant validation juridique, étape 6)

- Identité précise des parties (dénomination, RNE, siège, représentant légal).
- Effectif estimé et pièces d'éligibilité selon le statut.
- Montant nominatif du premier crédit et échéancier individuel.
"""
    path.write_text(md, encoding="utf-8")
    return path, sc


def defendre(dossier: Path, mode: str = "dg") -> str:
    """Lance la défense brain sur le dossier généré (appel LLM long)."""
    from llm import brain  # import local : streamlit + llm mélangés sur demande

    slug = dossier.name
    demande = (
        f"Défends le dossier {slug} avant verrouillage. "
        "Justifie la viabilité, la couverture des garanties et le verrou du framework."
    )
    return brain.raisonner(demande, mode=mode) or "❌ Échec LLM"


if __name__ == "__main__":
    # Self-check : qualifier cas types + génération
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    cas = [
        ({"type": "prive", "amicale": "oui-avec"}, "01"),
        ({"type": "prive", "amicale": "oui-sans"}, "01b"),
        ({"type": "prive", "amicale": "non"}, "02"),
        ({"type": "prive", "amicale": "non", "taille": "pme"}, "02pme"),
        ({"type": "prive", "amicale": "non", "international": "oui"}, "02inter"),
        ({"type": "prive", "amicale": "seule"}, "04"),
        ({"type": "admin"}, "03"),
        ({"type": "ordre"}, "05"),
        ({"type": "groupe"}, "06"),
        ({"type": "mutuelle"}, "07"),
    ]
    for reps, attendu in cas:
        sc = _qualifier(reps)
        ok = sc is not None
        print(f"  {'OK ' if ok else 'KO '} {reps.get('type'):<8} → {sc['name'] if sc else '?'}  (attendu {attendu})")
        assert ok
    path, sc = generer_dossier({"type": "groupe", "amicale": "non"}, "Cliente Test")
    assert "niveau 1" in path.read_text(encoding="utf-8")
    assert "Groupe multi-sociétés" in path.read_text(encoding="utf-8")
    print(f"  génération OK → {path}")
    print("Self-check OK")