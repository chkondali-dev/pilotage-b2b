# Workflow — Revue complète d'une convention existante

**Déclencheur :** renouvellement, incident, revue périodique, ou demande de l'expert métier

**Entrée :** chemin du document de convention (KNOWLEDGE/conventions/ ou autre)

## Étapes

### 1. Audit juridique — `@juriste`
Prompt : "Audite <chemin>. Utilise PROMPTS/audit_convention.md."
Sortie : `OUTPUTS/rapports/audit_<convention>_<date>.md`

### 2. Contre-audit — `@contradicteur`
Prompt : "Relis OUTPUTS/rapports/audit_<convention>_<date>.md et le document source. Cherche les failles et angles morts."
Sortie : `OUTPUTS/rapports/contre-audit_<convention>_<date>.md`

### 3. Stratégie de négociation — `@negociateur` (si renégociation prévue)
Prompt : "Prépare la négociation de <convention>. Utilise PROMPTS/preparation_negociation.md. Données : <KPIs du dashboard>."
Sortie : `OUTPUTS/synthèses/negociation_<convention>_<date>.md`

### 4. Rédaction des amendements — `@redacteur`
Prompt : "Rédige les amendements issus de l'audit + contre-audit. Utilise PROMPTS/comparaison_versions.md si deux versions."
Sortie : `OUTPUTS/contrats/amendement_<convention>_<date>.md`

### 5. Décision — `@comex`
Prompt : "Synthétise et tranche. Utilise PROMPTS/synthese_comex.md."
Sortie : `OUTPUTS/synthèses/decision_<convention>_<date>.md` + réponse directe

## Règles

- Étapes 1-2 obligatoires ; 3-4 selon le besoin ; 5 toujours en dernier.
- Chaque étape attend la sortie de la précédente.
- Si une étape révèle un 🔴 bloquant : arrêter et alerter l'expert métier immédiatement.
