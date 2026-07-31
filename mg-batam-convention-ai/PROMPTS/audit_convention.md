# Prompt — Audit d'une convention

Utilisateur : `@juriste "Audite <chemin/vers/convention> et liste les risques"`

## Consigne

Audite la convention clause par clause. Pour chaque clause, applique le format suivant.

## Format de sortie

```markdown
# Audit — <Nom convention>
**Date :** <date> — **Document :** <chemin>

## Verdict global
🟢 / 🟠 / 🔴 — <une phrase>

## Constats

### 1. Clause <N°> — <intitulé>
- **Texte :** "<extrait exact>"
- **Constat :** 🔴 bloquant / 🟠 risqué / 🟡 à clarifier
- **Règle applicable :** <référence>
- **Impact :** <conséquence si litige/défaillance>
- **Recommandation :** <action concrète>

### 2. … (pour chaque clause ou point notable)

## Points positifs
- <clauses saines, garanties en place>

## Questions ouvertes
- <questions à poser à l'expert métier>
```

## Règles

- Toujours citer le texte exact de la clause avant de commenter.
- Classe 🔴 bloquant / 🟠 risqué / 🟡 à clarifier.
- Vérifie la cohérence numérique (montants, taux, échéancier).
- Vérifie que les garanties du préambule existent dans les articles.
