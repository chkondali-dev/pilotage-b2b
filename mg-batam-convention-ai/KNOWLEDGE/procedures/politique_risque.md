# Politique de risque — conventions B2B SMG

> Références : FRAMEWORK_CONVENTIONS_SMG.md v2.0 (juillet 2026) · Note d'orientation
> stratégique COMEX du 22 juin 2026 — seules les règles de risque sont reprises
> (la numérotation des scénarios reste celle du framework v2.0, 01 à 07).
> Source unique pour `llm/agents.py::analyse_risque` — toute évolution se fait ici.

## 1. Paramètres communs incompressibles

- Plafond standard : 300 à 3 000 TND
- Durée limite : 18 mois maximum
- Taux d'intérêt mensuel : 0,75 % fixe
- Règle d'or : **condition suspensive systématique** — aucune livraison n'est
  autorisée avant la parfaite régularisation des sûretés d'usage.

## 2. Appétit au risque par garantie (4 niveaux de sécurité)

| Niveau | Composition des sûretés | Sécurité | Scénarios |
|--------|--------------------------|----------|-----------|
| 1 | Cession sur salaire (Tribunal Cantonal) + caution solidaire de la structure | Maximale | 01, 02, 06 |
| 2 | Cession sur salaire seule (sans caution) | Forte | 03 |
| 3 | Traite avalisée + reconnaissance de dette + vérification 40 % | Modérée | 07 |
| 4 | Traite + reconnaissance de dette seule (sans vérification 40 %) | Modérée / stricte | 05 |

## 3. Grille de risque opérationnelle (appliquée par l'agent d'analyse)

> Source unique pour `llm/agents.py::analyse_risque` — toute évolution se fait ici.

- Cession sur salaire + bonne tendance → faible
- Niveau 1 (cession + caution solidaire) → faible
- Cession sur salaire seule (niveau 2) ou garantie solidaire seule ou tendance
  irrégulière → moyen
- Traite + reconnaissance de dette sans vérification 40 % (niveau 4) → élevé
- Baisse continue 2+ mois OU lettre de change seule → élevé
- Niveau 3 (traite avalisée + RD + vérification 40 %) → modéré

## 4. Critères de refus

- Profil **non solvable** (matrice d'orientation client) : éliminé en amont,
  avant l'étape de défense du dossier — aucun dossier non solvable n'entre en
  circuit.
- Garantie insuffisante au regard du niveau de sécurité requis pour le scénario
  (ex. : Amicale seule sans caution employeur — règle absolue du framework v2.0).
- Baisse continue 2+ mois ou historique d'impayés (grille opérationnelle §3).

## 5. Plafonds d'exposition par contrepartie et par segment (MG, BATAM, EDC)

> **À définir par l'expert métier.** Aucune valeur officielle disponible à ce
> jour. Bloc réservé — les plafonds d'exposition et la politique de concentration
> seront insérés ici dès qu'ils seront arrêtés.

## 6. Procédure de dérogation

> **À définir par l'expert métier.** Bloc réservé — règles de dérogation
> (autorité habilitée, conditions, traçabilité) à insérer ici dès qu'arrêtées.

## 7. Protocole impayés & recouvrement (réactivité H+72)

- **Régime Classique** : mise en demeure de 3 jours au salarié → si non
  régularisé, information de l'employeur et activation immédiate de la caution
  solidaire pour prélèvement à la source.
- **Régime PLUS** : mise en demeure de 3 jours → en l'absence de recours contre
  la structure, transmission instantanée au contentieux pour action cambiaire
  directe sur les traites et requête en injonction de payer (Art. 290+ CPCC).

## 8. Seuils d'alerte (liés au dashboard)

- Risque élevé : niveau 4 de sûretés, baisse continue 2+ mois, lettre de change
  seule (grille opérationnelle §3)
- Inactivité : 60 jours par défaut (réglable 15–180 j)
- Concentration : par contrepartie et par segment — liée au plafond
  d'exposition (§5)

## 9. Référentiel juridique (droit tunisien)

- Art. 142 du Code du Travail : plafonnement impératif de 40 % sur la quotité
  cessible du salaire
- Art. 434 à 436 du COC : force probante de la reconnaissance de dette
- Art. 253 et suivants du Code de Commerce : lettre de change, aval, protêt,
  action cambiaire
- Art. 290 et suivants du CPCC : procédure d'injonction de payer
