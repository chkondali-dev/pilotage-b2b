# REVUE SYSTÈME convention-ai — llama-3.3-70b-versatile (Groq)

Généré le 2026-07-31T13:45

---


## PASS 1a — Workflows et données

## Verdict global
Le système présente des risques importants liés à la gestion des données et aux workflows. Les trois risques les plus graves sont :
1. La gestion des données dans `workflows.py` et `smg_data.py` peut entraîner des erreurs de synchronisation et des pertes de données.
2. Les workflows dans `workflows.py` ne sont pas robustes et peuvent échouer en cas de données manquantes ou incorrectes.
3. La dépendance à l'égard de GitHub pour charger les données peut entraîner des problèmes de disponibilité et de sécurité.

## Findings P0 (correction urgente)
- workflows.py:33 | Problème de gestion des données | Scénario de déclenchement : erreur de lecture ou d'écriture du fichier `conventions_signees.csv` | Correction minimale : utiliser un verrou pour éviter les écritures concurrentes.
- smg_data.py:23 | Erreur de chargement des données | Scénario de déclenchement : échec de la requête GitHub | Correction minimale : implémenter une rétente pour les requêtes échouées.
- workflows.py:101 | Erreur de workflow | Scénario de déclenchement : données manquantes ou incorrectes | Correction minimale : ajouter des vérifications de données pour éviter les erreurs de workflow.

## Findings P1 (important)
- workflows.py:50 | Amélioration de la gestion des données | Scénario de déclenchement : besoin de mise à jour des données | Correction minimale : utiliser une base de données pour stocker les données au lieu d'un fichier CSV.
- smg_data.py:50 | Amélioration de la robustesse | Scénario de déclenchement : erreur de chargement des données | Correction minimale : ajouter des vérifications de données pour éviter les erreurs de chargement.
- workflows.py:150 | Amélioration de la sécurité | Scénario de déclenchement : besoin de sécurité accrue | Correction minimale : utiliser des mécanismes de sécurité pour protéger les données sensibles.

## Findings P2 (amélioration)
- workflows.py:200 | Amélioration de la performance | Scénario de déclenchement : besoin de performance accrue | Correction minimale : optimiser les requêtes et les traitements de données pour améliorer la performance.
- smg_data.py:100 | Amélioration de la flexibilité | Scénario de déclenchement : besoin de flexibilité accrue | Correction minimale : utiliser des mécanismes de configuration pour permettre une flexibilité accrue.
- workflows.py:250 | Amélioration de la documentation | Scénario de déclenchement : besoin de documentation accrue | Correction minimale : ajouter des commentaires et des documentation pour améliorer la compréhension du code.

## OK / ne pas toucher
- Les parties du code qui ne présentent pas de risques importants ou de problèmes de performance, telles que les fonctions de calcul et les traitements de données simples.


## PASS 1b1 — Client, agents et personas

## Verdict global
Le système est globalement sain, mais présente quelques risques et failles qui nécessitent une correction urgente. Les trois risques les plus graves sont liés à la gestion des exceptions, à la validation des données et à la sécurité des informations sensibles.

## Findings P0 (correction urgente)
- llm/client.py:33 | Problème de gestion d'exceptions | Scénario de déclenchement : erreur de connexion à Ollama ou Groq | Correction minimale : ajouter un try-except pour gérer les exceptions de connexion
- llm/agents.py:120 | Problème de validation des données | Scénario de déclenchement : données invalides ou manquantes | Correction minimale : ajouter des vérifications de données pour garantir leur validité
- llm/config.py:20 | Problème de sécurité | Scénario de déclenchement : accès non autorisé aux clés API | Correction minimale : sécuriser les clés API en utilisant des variables d'environnement ou un système de gestion de secrets

## Findings P1 (important)
- llm/rag.py:50 | Problème de performances | Scénario de déclenchement : grande quantité de données à indexer | Correction minimale : optimiser l'algorithme d'indexation pour améliorer les performances
- AGENTS/juriste.md:30 | Problème de cohérence | Scénario de déclenchement : incohérence dans les règles métier | Correction minimale : réviser les règles métier pour garantir leur cohérence
- llm/store.py:10 | Problème de gestion des données | Scénario de déclenchement : données non sauvegardées | Correction minimale : ajouter une fonction de sauvegarde des données pour garantir leur intégrité

## Findings P2 (amélioration)
- llm/agents.py:100 | Amélioration de la logique de décision | Scénario de déclenchement : décision non optimale | Correction minimale : réviser la logique de décision pour l'améliorer
- llm/client.py:20 | Amélioration de la gestion des erreurs | Scénario de déclenchement : erreur non gérée | Correction minimale : ajouter des messages d'erreur pour améliorer la gestion des erreurs
- AGENTS/comex.md:20 | Amélioration de la documentation | Scénario de déclenchement : documentation incomplète | Correction minimale : compléter la documentation pour améliorer la compréhension du système

## OK / ne pas toucher
- llm/agents.py:50 | La fonction `audit` est correcte et ne nécessite pas de modification
- llm/config.py:30 | Les constantes de configuration sont correctes et ne nécessitent pas de modification
- AGENTS/redacteur.md:10 | La documentation du rédacteur est complète et ne nécessite pas de modification


## PASS 1b2 — Store et raisonnement

## Verdict global
Le système est globalement sain, mais présente quelques risques importants liés à la gestion des embeddings et à la détection des trous de connaissance. Les trois risques les plus graves sont :
- La gestion des embeddings dans `llm/store.py` qui peut causer des problèmes de performances et de fiabilité si Ollama est indisponible.
- La détection des trous de connaissance dans `llm/reasoning.py` qui peut ne pas être suffisamment robuste pour détecter tous les cas de manques d'information.
- La gestion des erreurs dans `llm/reasoning.py` qui peut ne pas être suffisamment robuste pour gérer les cas d'erreur lors de la compilation d'un audit.

## Findings P0 (correction urgente)
- llm/store.py:30 | Problème de gestion des embeddings | Scénario de déclenchement : Ollama indisponible | Correction minimale : Ajouter une gestion d'erreur plus robuste pour les cas où Ollama est indisponible.
- llm/reasoning.py:150 | Problème de détection des trous de connaissance | Scénario de déclenchement : Manque d'information dans l'audit | Correction minimale : Améliorer la détection des trous de connaissance en utilisant des techniques de traitement de langage naturel plus avancées.
- llm/reasoning.py:200 | Problème de gestion des erreurs | Scénario de déclenchement : Erreur lors de la compilation d'un audit | Correction minimale : Ajouter une gestion d'erreur plus robuste pour les cas d'erreur lors de la compilation d'un audit.

## Findings P1 (important)
- llm/store.py:50 | Problème de performances | Scénario de déclenchement : Grande quantité de données à stocker | Correction minimale : Optimiser la base de données pour améliorer les performances.
- llm/reasoning.py:100 | Problème de robustesse | Scénario de déclenchement : Données non conformes | Correction minimale : Améliorer la robustesse de la compilation d'un audit en utilisant des techniques de validation de données plus avancées.

## Findings P2 (amélioration)
- llm/store.py:20 | Amélioration de la gestion des embeddings | Scénario de déclenchement : Utilisation de différents modèles d'embeddings | Correction minimale : Ajouter la possibilité d'utiliser différents modèles d'embeddings.
- llm/reasoning.py:250 | Amélioration de la détection des trous de connaissance | Scénario de déclenchement : Utilisation de techniques de traitement de langage naturel plus avancées | Correction minimale : Améliorer la détection des trous de connaissance en utilisant des techniques de traitement de langage naturel plus avancées.

## OK / ne pas toucher
- llm/store.py:10 | La gestion des données est correcte.
- llm/reasoning.py:50 | La compilation d'un audit est correcte.


## PASS 2 — Docs métier

## Verdict global
Le système de gestion des conventions B2B présente des risques importants liés à la cohérence métier et à la fiabilité des workflows. Les trois risques les plus graves sont la non-conformité des documents de référence, les incohérences dans la matrice de garanties et les manques dans les workflows qui pourraient entraîner des erreurs de traitement.

## Findings P0 (correction urgente)
- Fichier : `KNOWLEDGE/INDEX.md` : ligne 10 | problème : Statut de certains documents non à jour | scénario de déclenchement : Mise à jour manuelle nécessaire pour refléter les changements dans les documents de référence | correction minimale : Mettre à jour les statuts des documents pour refléter leur état actuel.
- Fichier : `KNOWLEDGE/procedures/procedure_validation.md` : ligne 5 | problème : Procédure de validation interne non rédigée | scénario de déclenchement : Nécessité d'une procédure claire pour la validation des conventions | correction minimale : Rédiger la procédure de validation interne pour garantir une approbation cohérente des conventions.
- Fichier : `KNOWLEDGE/reference/faq_conventions.md` : ligne 20 | problème : Réponses à confirmer dans la FAQ | scénario de déclenchement : Besoin de clarifier les réponses pour éviter les ambiguïtés | correction minimale : Valider les réponses à confirmer pour fournir des informations précises aux agents.

## Findings P1 (important)
- Fichier : `KNOWLEDGE/conventions/conventions_type_scenarios.md` : ligne 15 | problème : Matrice de garanties incomplète | scénario de déclenchement : Nécessité d'une matrice complète pour évaluer les risques | correction minimale : Compléter la matrice de garanties pour refléter tous les scénarios possibles.
- Fichier : `PROMPTS/audit_convention.md` : ligne 10 | problème : Format de sortie non standardisé | scénario de déclenchement : Besoin d'un format standard pour faciliter l'analyse | correction minimale : Standardiser le format de sortie pour les audits de conventions.
- Fichier : `PROMPTS/analyse_risque.md` : ligne 20 | problème : Grille de risque non appliquée de manière cohérente | scénario de déclenchement : Nécessité d'une évaluation de risque cohérente | correction minimale : Appliquer la grille de risque de manière cohérente pour évaluer les risques associés aux conventions.

## Findings P2 (amélioration)
- Fichier : `KNOWLEDGE/conventions/convention_modele_rtt.md` : ligne 5 | problème : Modèle de convention RTT non déposé | scénario de déclenchement : Besoin d'un modèle pour les conventions RTT | correction minimale : Déposer le modèle de convention RTT pour compléter les documents de référence.
- Fichier : `PROMPTS/comparaison_versions.md` : ligne 15 | problème : Format de comparaison des versions non standardisé | scénario de déclenchement : Besoin d'un format standard pour comparer les versions | correction minimale : Standardiser le format de comparaison des versions pour faciliter l'analyse.
- Fichier : `PROMPTS/synthese_comex.md` : ligne 10 | problème : Format de synthèse non standardisé | scénario de déclenchement : Besoin d'un format standard pour la synthèse | correction minimale : Standardiser le format de synthèse pour les décisions Comex.

## OK / ne pas toucher
- Fichier : `KNOWLEDGE/conventions/contrat_cession_salaire.md` : Le contrat de cession sur salaire semble complet et à jour.
- Fichier : `PROMPTS/preparation_negociation.md` : Le format de préparation de négociation semble clair et utile.

---

# Corrections appliquées (2026-07-31)

Suite à la revue, trois corrections validées par l'expert métier :

## P0 — `llm/client.py` : routage Ollama masquait Groq
- **Cause** : `provider()` choisissait `ollama` dès qu'Ollama tournait, sans vérifier que le modèle demandé y était installé → le rôle `redaction` (`llama-3.3-70b-versatile`, servi par Groq) partait vers `localhost:11434` → 404.
- **Fix** : `_ollama_has_model(model)` interroge `/api/tags` et ne retient `ollama` que si le modèle y est installé ; sinon `groq` si clé API.
- **Preuves** : `provider('qwen2.5:7b') → ollama` · `provider('llama-3.3-70b-versatile') → groq` · appel réel `chat(role='redaction')` → `[LLM] llama-3.3-70b-versatile via groq...` → réponse OK.

## P2 — `KNOWLEDGE/INDEX.md` : statuts alignés sur la réalité
- `convention_modele_rtt.md` : « ⬜ à déposer » → « 🟡 placeholder — contenu à déposer » (le fichier existe, vide).
- `procedure_validation.md` / `politique_risque.md` : « ⬜ à rédiger » → « 🟡 coquille — à rédiger / grille incluse, à compléter ».

## P2 — Grille de risque déplacée dans `KNOWLEDGE/procedures/politique_risque.md`
- La grille SMG était en dur dans le prompt d'`agents.py::analyse_risque` (contraire à la convention du projet : pas de valeurs en dur).
- **Fix** : grille déplacée dans `politique_risque.md` (source unique), lue via `_grille_risque()` dans `agents.py`.
- **Preuve** : `py_compile` OK ; plus aucun résidu de grille dans `agents.py`.

## Bruit de la revue rejeté
- Numéros de ligne hallucinés (`workflows.py:150/200/250` inexistants), « utiliser une base de données », « sécuriser les clés API » (déjà en env vars), « optimiser les requêtes » sans scénario, trous connus re-signalés (FAQ tiers saisissable, MG/BATAM, procédures) — non suivis.
