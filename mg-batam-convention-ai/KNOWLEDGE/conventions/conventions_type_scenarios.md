# Conventions type — 5 scénarios commerciaux SMG

> ⚠️ **SUPERSEDED** — Ce document (5 scénarios commerciaux, design 2026-06-10) est OBSOLÈTE
> pour la partie contractuelle. Référentiel canonique : **`reference/framework_conventions_smg.md`
> (FRAMEWORK_CONVENTIONS_SMG.md v2.0 — 7 scénarios 01-07, Groupe = 06).** Conservé pour
> l'historique produit (matrice de garanties et plan de rédaction 16 articles).

> Source : design spec validé `docs/superpowers/specs/2026-06-10-conventions-type-scenarios-design.md`
> Base : convention existante SMG / Amicale ETT (corrigée et améliorée)

## Matrice des garanties par scénario

| Scénario | Prél. salaire | Lettre de change | Reconnaiss. dette |
|----------|:---:|:---:|:---:|
| 1. Amicale | ✅ | ✅ | ✅ |
| 2. Mutuelle | ❌ | ✅ | ✅ |
| 3. Entr. publique | ✅ | ❌ | ✅ |
| 4. Entr. privée | ❌ | ✅ | ✅ |
| 5. Comptant | ❌ | ❌ | ❌ |

---

## Scénario 1 : Amicale / Association du personnel

| Élément | Valeur |
|---------|--------|
| Client type | Amicale du personnel, association de salariés |
| Produits | Tous (électroménager, meubles, high-tech, moto, meubles jardin) |
| Garantie | Prélèvement sur salaire + Lettre de change avalisée + Reconnaissance de dette légalisée |
| Intermédiaire | Amicale (signature + cachet) |
| Validation | Responsable RH + Président Amicale (ou mandataire) |
| Paiement | Virement global SMG avant le 10 du mois, état récapitulatif mensuel |
| Décès | Notif. 5j ouvrés, remb. 30j calendaires |
| Recouvrement | Recours cambiaire, injonction payer, action directe |

**Corrections historiques apportées au modèle :**
- Double article 15 corrigé (un seul article 15 : juridiction ; article 16 : élection de domicile)
- Seuil de 40% clarifié = taux d'endettement
- Aval personnel maintenu mais explicité (risque signalé)

## Scénario 2 : Mutuelle

| Élément | Valeur |
|---------|--------|
| Client type | Mutuelle, organisme de prévoyance |
| Produits | Tous |
| Garantie | Lettre de change avalisée + Reconnaissance de dette légalisée |
| Intermédiaire | Mutuelle (garantie morale / caution de l'organisme) |
| Validation | Responsable de la mutuelle + bénéficiaire |
| Paiement | Direct par l'adhérent (virement / chèque / espèce) |
| Recouvrement | Recours cambiaire, injonction payer |

**Particularités :**
- Pas de prélèvement sur salaire (pas de DRH, pas de lien contractuel employeur) → risque de non-paiement plus élevé
- Lettre de change avalisée par le dirigeant de la mutuelle (aval personnel)
- Possibilité d'ajouter une caution solidaire par un dirigeant

## Scénario 3 : Entreprise publique

| Élément | Valeur |
|---------|--------|
| Client type | Administration, établissement public, société d'État |
| Produits | Tous |
| Garantie | Prélèvement sur salaire + Reconnaissance de dette légalisée |
| Intermédiaire | Employeur public (convention directe avec l'entreprise) |
| Validation | DRH / Directeur financier de l'entreprise publique |
| Paiement | Virement global avant le 10 du mois, état récapitulatif mensuel |
| Recouvrement | Injonction payer, action directe |

**Particularités :**
- Pas de lettre de change (droit cambiaire moins adapté au secteur public)
- Reconnaissance de dette légalisée comme principal titre
- Prélèvement sur salaire garanti par la DRH de l'entreprise publique
- Clause de continuité du prélèvement même après mutation ou départ
- Validation parfois plus lourde (directeur général, voire ministre de tutelle pour les administrations)

## Scénario 4 : Entreprise privée

| Élément | Valeur |
|---------|--------|
| Client type | Société privée, PME, startup |
| Produits | Tous |
| Garantie | Lettre de change avalisée + Reconnaissance de dette légalisée |
| Intermédiaire | Employeur privé (caution morale et organisationnelle) |
| Validation | Dirigeant / DRH |
| Paiement | Virement global ou direct par l'employé |
| Recouvrement | Recours cambiaire, injonction payer |

**Particularités :**
- Pas de prélèvement sur salaire (l'entreprise privée peut refuser cette charge administrative)
- Lettre de change avalisée par le dirigeant (caution personnelle)
- Reconnaissance de dette légalisée
- Clause de non-opposition de l'employeur aux poursuites

## Scénario 5 : Achat comptant (tous clients)

| Élément | Valeur |
|---------|--------|
| Client type | Particulier, tout type |
| Produits | Tous |
| Garantie | Aucune (paiement intégral à la commande) |
| Intermédiaire | Aucun |
| Validation | Simple identification du client |
| Paiement | Comptant (espèce, carte bancaire, virement immédiat) |
| Recouvrement | Sans objet |

**Particularités :**
- Convention simplifiée (2-3 pages maximum)
- Pas de garantie, pas de crédit
- Clauses essentielles : identité du client, description du produit, prix, livraison, retour, garantie légale
- Pas d'annexes financières complexes

---

## Plan de rédaction commun (16 articles)

1. **Parties** (client)
2. **Durée** (fixe : 1 an, tacite reconduction)
3. **Objet** (produits concernés)
4. **Plafond et modalités de paiement** (variable selon garantie)
5. **Procédures de vente** (validation, documents obligatoires)
6. **Taux d'intérêt** (0,75%/mois pour les scénarios crédit)
7. **Modalités de versement** (variable)
8. **Décès / Cas de force majeure** (selon garantie)
9. **Suspension des ventes / Défaut**
10. **Recouvrement** (selon garantie)
11. **Résiliation**
12. **Confidentialité**
13. **Preuve électronique**
14. **Juridiction**
15. **Frais**
16. **Élection de domicile**

**Annexes :**
- Annexe 1 : Spécimen de signature et délégation (scénarios 1-4)
- Annexe 2 : Reconnaissance de dette légalisée (scénarios 1-4)
- Annexe 3 : Lettre de change (scénarios 1, 2, 4)
