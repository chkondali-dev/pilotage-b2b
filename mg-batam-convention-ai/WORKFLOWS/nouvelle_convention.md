# Workflow — Nouvelle convention

**Déclencheur :** demande d'un nouveau partenaire (amicale, ministère, entreprise)

**Entrée :** besoins exprimés par l'expert métier (contrepartie, volume estimé, type de garantie)

## Étapes

### 1. Cadrage — Expert métier (avec l'assistant)
- Identifier la contrepartie et son profil de risque
- Définir : volume estimé, type de garantie (cession sur salaire / solidaire / lettre de change), durée
- Vérifier les données historiques si le partenaire est déjà client (dashboard)

### 2. Ébauche — `@redacteur`
Prompt : "Rédige une convention de crédit B2B pour <contrepartie>. Contexte : <besoins>. Champ à compléter pour tout chiffre manquant. Structure standard."
Sortie : `OUTPUTS/contrats/convention_<contrepartie>_<date>.md`

### 3. Vérification conformité — `@juriste`
Prompt : "Vérifie la conformité de OUTPUTS/contrats/convention_<contrepartie>_<date>.md. Clauses obligatoires, garantie, plafond tiers saisissable."
Sortie : `OUTPUTS/rapports/verification_<contrepartie>_<date>.md`

### 4. Stress-test — `@contradicteur`
Prompt : "Cherche les failles dans <contrat> et <verification>. Scénarios de défaillance."
Sortie : `OUTPUTS/rapports/contre-audit_<contrepartie>_<date>.md`

### 5. Corrections — `@redacteur`
Prompt : "Intègre les corrections issues des étapes 3-4 dans le contrat."
Sortie : version finale `OUTPUTS/contrats/convention_<contrepartie>_<date>_v2.md`

### 6. Validation — `@comex`
Prompt : "Décision go/no-go. Utilise PROMPTS/synthese_comex.md."
Sortie : `OUTPUTS/synthèses/decision_<contrepartie>_<date>.md`

## Règles

- Ne jamais sauter l'étape 4 (stress-test) pour gagner du temps — c'est elle qui attrape les erreurs.
- Aucun chiffre inventé : tout champ non fourni reste `________` jusqu'à l'expert métier.
- Après signature, le document original va dans KNOWLEDGE/conventions/ (par l'expert métier, pas par les agents).
