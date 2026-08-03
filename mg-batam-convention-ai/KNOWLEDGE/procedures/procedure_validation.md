# Procédure de validation interne — conventions B2B SMG

> Réf : `procedures/procedure_validation.md` — circuit d'approbation interne
> pour toute nouvelle convention ou renouvellement. Source : Framework SMG
> v2.0 partie A3 (processus 9 étapes) + organisation interne A2.
> Complète la politique de risque (`procedures/politique_risque.md`).

## 1. Qui valide quoi (niveaux d'approbation)

| Étape | Validation | Acteur | Délai cible |
|:-----:|-----------|--------|:-----------:|
| 1–3 | Qualification, sélection du template, rédaction | Responsable Convention | 1–2 sem. |
| 4 | **Défense du dossier** (verrou risque) — argumentation du dossier | Responsable Convention → Directeur Service Clients | 1–3 jours |
| 5 | **Décision finale et arbitrage** (verrouillage risque) — validation ou rejet | Directeur Service Clients + Directeur Finance & Contentieux | 1–2 jours |
| 6 | Conformité légale — lecture, correction | Juriste | 1–3 jours |
| 7 | Signature | Directeur Général | 1–2 jours |
| 8 | Signature client et enregistrement (frais à la charge du client, art. 19) | Client + SMG | 1–2 sem. |
| 9 | Suivi client et KPI | Responsable Convention | Continu |

**Règle impérative :** les étapes 4 et 5 (verrouillage risque) précèdent la
validation juridique (étape 6) — seuls les dossiers solides arrivent au
juridique.

## 2. Seuils de décision

- **Verrouillage risque (étapes 4–5)** : le Directeur Service Clients juge la
  maîtrise du risque ; le Directeur Finance & Contentieux arbitre. Décision
  binaire : validation ou rejet.
- **Amicale B (scénario 01)** : validation DSC **obligatoire** (framework C2).
- **Dérogations** : plafonds d'exposition et procédure de dérogation encore
  non arrêtés par l'expert métier (politique de risque §5–6) — aucun dossier
  en dérogation ne peut être validé sans règle écrite.
- **Refus obligatoires** (politique de risque §4) : profil non solvable,
  garantie insuffisante au regard du scénario, baisse continue 2+ mois ou
  historique d'impayés.

## 3. Documents requis pour la validation

- Dossier client complété (identification, effectif estimé, pièces
  d'éligibilité) ;
- Paramètres contractuels alignés sur le scénario (plafonds, durée, taux) ;
- Garanties conformes au régime (cession + caution, ou traite + RD légalisée) ;
- Preuve du circuit de paiement accepté par la structure ;
- Résultat de la défense (étape 4) : synthèse exécutive + journal du
  raisonnement de l'agent d'analyse ;
- Checklist production complétée (framework D1) pour l'étape 6.

## 4. Archivage des conventions validées

- **KNOWLEDGE/ (lecture seule)** : conventions signées déposées dans
  `conventions/` par l'expert métier — les agents n'écrivent JAMAIS dans
  KNOWLEDGE/ ;
- **OUTPUTS/** : journaux de raisonnement, rapports et sorties des agents ;
- **data/dossiers/** : dossiers clients en cours de traitement (créés et
  indexés par le brain pour la défense).

## 5. Cas particuliers

- **Renouvellement** : tacite reconduction à 1 an, préavis 3 mois par LRAR.
  Le renouvellement est l'occasion de revoir plafonds, taux et RFA (framework B8).
- **Groupe multi-sociétés (06)** : caution portée par la holding, jamais par
  les filiales ; clause de non-cession obligatoire.
- **Administration (03)** : caution interdite (droit public) ; TC obligatoire.
- **Convention PLUS (05, 07)** : condition suspensive absolue — traite signée
  ET RD légalisée avant toute livraison.
