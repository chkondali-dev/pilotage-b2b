# KNOWLEDGE — Index documentaire

Base documentaire en LECTURE SEULE pour les agents. Toute mise à jour se fait
manuellement par l'expert métier (ou via workflow dédié).

## Conventions types

| Document | Emplacement | Statut |
|---|---|---|
| Contrat de cession sur salaire (modèle) | `conventions/contrat_cession_salaire.md` | ✅ prêt — référence principale |
| Contrat de cession sur salaire (.docx) | `docs/contrat_cession_salaire.docx` (repo racine) | ✅ prêt |
| 5 scénarios de conventions type + matrice garanties | `conventions/conventions_type_scenarios.md` | ✅ prêt (design validé 2026-06-10) |
| Convention modèle RTT | `conventions/convention_modele_rtt.md` | ⬜ à déposer |
| Conditions générales | `conventions/conditions_generales.md` | ⬜ à déposer |

## Procédures

| Document | Emplacement | Statut |
|---|---|---|
| Procédure de validation interne | `procedures/procedure_validation.md` | ⬜ à rédiger |
| Politique de risque | `procedures/politique_risque.md` | ⬜ à rédiger |

## Référence

| Document | Emplacement | Statut |
|---|---|---|
| FAQ conventions | `reference/faq_conventions.md` | ✅ complétée — 2 réponses à confirmer (tiers saisissable, MG vs BATAM) |
| Analyse mensuelle (prompt existant) | `prompts/analyse_convention.md` (repo racine) | ✅ prêt |

## Convention en cours de production

- Toute convention signée est déposée ici (`conventions/`) par l'expert métier.
- Les agents n'écrivent JAMAIS dans KNOWLEDGE/.
- Les sorties des agents vont dans `OUTPUTS/` (racine du projet convention-ai).
