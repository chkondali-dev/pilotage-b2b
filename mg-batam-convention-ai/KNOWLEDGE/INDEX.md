# KNOWLEDGE — Index documentaire

Base documentaire en LECTURE SEULE pour les agents. Toute mise à jour se fait
manuellement par l'expert métier (ou via workflow dédié).

## Conventions types

| Document | Emplacement | Statut |
|---|---|---|
| Contrat de cession sur salaire (modèle) | `conventions/contrat_cession_salaire.md` | ✅ prêt — référence principale |
| Contrat de cession sur salaire (.docx) | `docs/contrat_cession_salaire.docx` (repo racine) | ✅ prêt |
| 5 scénarios de conventions type + matrice garanties | `conventions/conventions_type_scenarios.md` | 🔁 SUPERSEDED — historique produit (design 2026-06-10), remplacé par le framework v2.0 |
| Convention modèle RTT | `conventions/convention_modele_rtt.md` | 🟡 placeholder — contenu à déposer |
| Conditions générales | `conventions/conditions_generales.md` | ⬜ à déposer |

## Procédures

| Document | Emplacement | Statut |
|---|---|---|
| Procédure de validation interne | `procedures/procedure_validation.md` | 🟡 coquille — à rédiger |
| Politique de risque | `procedures/politique_risque.md` | ✅ 9 sections (appétit par garantie, refus, protocole impayés H+72, référentiel juridique) — plafonds d'exposition et dérogations « à définir par l'expert métier » |

## Référence

| Document | Emplacement | Statut |
|---|---|---|
| **Framework conventions SMG v2.0 (7 scénarios)** | `reference/framework_conventions_smg.md` | ✅ **référence principale** — processus 9 étapes / 4 phases |
| FAQ conventions | `reference/faq_conventions.md` | ✅ complétée — 2 réponses à confirmer (tiers saisissable, MG vs BATAM) |
| Analyse mensuelle (prompt existant) | `prompts/analyse_convention.md` (repo racine) | ✅ prêt |

## Convention en cours de production

- Toute convention signée est déposée ici (`conventions/`) par l'expert métier.
- Les agents n'écrivent JAMAIS dans KNOWLEDGE/.
- Les sorties des agents vont dans `OUTPUTS/` (racine du projet convention-ai).
