# Workflow — Renouvellement d'une convention

**Déclencheur :** échéance approchante (≤ 60 jours) ou décision de l'expert métier

**Entrée :** convention existante + données de performance de la période écoulée (dashboard)

## Étapes

### 1. Bilan de performance — données du dashboard
- CA total et évolution N/N-1 sur la durée de la convention
- Régularité des paiements (impayés, retards)
- Concentration / part du CA total
- Statut de la garantie (cession toujours confirmée ?)

### 2. Revue documentaire — `@juriste`
Prompt : "Audite <convention existante>. Utilise PROMPTS/audit_convention.md. Signale tout point devenu caduc (réglementation, plafonds)."
Sortie : `OUTPUTS/rapports/audit_renouvellement_<convention>_<date>.md`

### 3. Contre-audit — `@contradicteur`
Prompt : "Relis l'audit + le bilan de performance. Cherche ce qui invalide la reconduction."
Sortie : `OUTPUTS/rapports/contre-audit_renouvellement_<convention>_<date>.md`

### 4. Stratégie — `@negociateur`
Prompt : "Prépare la renégociation. Utilise PROMPTS/preparation_negociation.md. Points de levier : <performance, volume>."
Sortie : `OUTPUTS/synthèses/negociation_renouvellement_<convention>_<date>.md`

### 5. Rédaction — `@redacteur`
Prompt : "Rédige la convention renouvelée avec les nouvelles conditions convenues."
Sortie : `OUTPUTS/contrats/renouvellement_<convention>_<date>.md`

### 6. Décision — `@comex`
Prompt : "Reconduire / renégocier / ne pas renouveler ? Utilise PROMPTS/synthese_comex.md."
Sortie : `OUTPUTS/synthèses/decision_renouvellement_<convention>_<date>.md`

## Règles

- Ne pas reconduire à l'identique sans comparer les conditions au marché.
- Risque `élevé` (baisse continue 2+ mois, lettre de change seule) → reconduction conditionnelle ou refus.
- La décision de non-renouvellement est communiquée avec un préavis respectant la clause de résiliation.
