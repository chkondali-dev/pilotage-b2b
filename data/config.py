"""
Configuration centralisée — constantes, palette, fichiers.
"""

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"
GITHUB_RAW_IMAGES = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/"
LOGO_MG_URL = GITHUB_RAW_IMAGES + "logo-1653837429.jpg"
LOGO_BATAM_URL = GITHUB_RAW_IMAGES + "logo.svg"
CRM_URL = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/TDC2.xlsx"

FILES = {
    "vc": "Factures%20ventes%20enregistr%C3%A9es%20VC%20(4).xlsx",
    "vc_credit": "Factures%20ventes%20enregistr%C3%A9es%20VC%20credit%20conso.xlsx",
    "vc_edc": "Factures%20ventes%20enregistr%C3%A9es%20VC%20CONVENTION%20EDC.xlsx",
    "credit_particulier": "CREDIT%20PARTICULIER.xlsx",
    "conventions_signees": "TDC%20CONVENTION%201.xlsm",
    "code_magasin": "Code%20MAGASIN%20Business%20Central.xlsx",
    "cube_magasin": "CUBE%20MAGASIN.xlsx",
}

C = {
    "green": "#059669",
    "red": "#DC2626",
    "blue": "#1D4ED8",
    "slate": "#94A3B8",
    "amber": "#D97706",
    "purple": "#6D28D9",
    "ink": "#0F172A",
    "muted": "#64748B",
    "border": "#E2E8F0",
    "surface": "#F8FAFC",
}

MOIS = {
    1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Juil", 8: "Aoû",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc",
}

NOMS_INDIVIDUELS = {"AHMED ABIDI", "AMARA MISSAOUI", "BILEL BEN AMMAR", "MED KAIS SMAILI"}

# Types de vente constituant une convention (identification "Hors convention").
# SOURCE UNIQUE de la règle : un achat est "en convention" ssi son type de vente
# est VC.CONV. ; tout le reste (VC.PARTIC., VC.CONSO., CLT-IMPAYE…) = hors convention.
TYPES_CONVENTION = {"VC.CONV."}

LIBELLE_HORS_CONVENTION = "Hors convention"

# Seuils métier centralisés — SOURCE UNIQUE (P1).
# Toute nouvelle règle de pilotage doit y déclarer son seuil ici.
SEUILS = {
    "inactivite_jours": 60,   # défaut slider + inactive_conventions()
    "declin_fort_pct": -20,   # « Déclin fort » (matrice risque, établissements)
    "alerte_veille_pct": -20,  # alerte rouge veille 7j glissants vs N-1
    "cohorte_fidele_ans": 2,  # fidélité cohorte : CA sur les N dernières années
    "objectif_defaut_m": 14.0,  # CA annuel cible par défaut (M TND), éditable (sidebar)
    "hausse_sig_pct": 20,     # insight : hausse significative vs N-1 (%, base exigée)
    "baisse_sig_pct": -20,    # insight : baisse significative vs N-1 (%, base exigée)
    "concentration_top3_pct": 50,  # insight : top 3 > X % du CA → risque concentration
    "panier_bas_ratio": 0.8,  # insight : panier période < 80 % du panier annuel
    "ca_tnd_min": 1000,       # insight : ignore les variations sur CA < 1 000 TND (bruit)
    "prospection_stalle_jours": 30,  # onglet Conventions encours : prospect sans activité → bloqué
    "relance_jours": 14,      # délai entre 2 relances (prochaine relance auto pipeline)
    "achats_annee_alerte": 3,  # conformité 40% : ≥ 3 achats/crédit par adhérent dans l'année → 🔴 Alerte
    "achats_annee_risque": 2,  # conformité 40% : = 2 achats dans l'année → 🟡 À risque (surveillance)
}

# Jalons types — délai max (jours) par étape du pipeline, par scénario.
# Clé = numéro du scénario ("01", "03"…) ; "defaut" si inconnu.
# Source unique des seuils de pilotage : adapter ICI, jamais en dur dans app.py.
JALONS = {
    "01": {"Prise de contact": 7,  "Validation client": 21, "Juridique": 30, "Finance": 15, "Signature": 15},
    "03": {"Prise de contact": 15, "Validation client": 30, "Juridique": 45, "Finance": 30, "Signature": 30},
    "04": {"Prise de contact": 7,  "Validation client": 21, "Juridique": 30, "Finance": 20, "Signature": 20},
    "07": {"Prise de contact": 15, "Validation client": 30, "Juridique": 45, "Finance": 30, "Signature": 30},
    "defaut": {"Prise de contact": 10, "Validation client": 25, "Juridique": 35,
               "Finance": 20, "Signature": 20},
}

JALONS_SCENARIOS = {   # libellés des scénarios (affichage)
    "01": "01-Prive avec Amicale", "03": "03-Administration",
    "04": "04-Amicale seule", "07": "07-Mutuelle",
}

# Jalons du registre : jours max dans un statut OUVERT avant alerte "en retard".
JALONS_STATUTS = {
    "Prospection": 30, "Negociation": 30, "En cours": 45, "Finalisation": 30,
}


def jalons_scenario(scenario: str) -> dict:
    """Jalons d'un scénario « 07-Mutuelle », « 01 - Privé… » → dict étape→jours."""
    import re as _re
    m = _re.match(r"\s*(\d+)", str(scenario or ""))
    return JALONS.get(m.group(1) if m else "", JALONS["defaut"])
