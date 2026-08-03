# Rapport de travail — 03 août 2026

> Projet mg-batam-convention-ai · Défense des dossiers de convention + durcissement pipeline brain.
> Complète le rapport du 31/07 (rapport_travail_complet_20260731.md).

## 1. Dossier MEDITECH (scénario 01 Amicale) — défendable

- `data/dossiers/meditech.md` créé : identification, paramètres framework
  (plafond 300–3 000 TND, 18 mois, 0,75 %/mois), **garanties niveau 1**
  (cession sur salaire + caution solidaire MEDITECH), maîtrise du risque,
  éléments à confirmer.
- `KNOWLEDGE/conventions/convention_modele_rtt.md` : placeholder → **modèle
  type 16 articles + annexes** (comble F1 : modèle RTT absent).
- `KNOWLEDGE/INDEX.md` : statut du modèle → ✅ prêt.

## 2. Correctifs pipeline brain (root causes, pas de symptômes)

| Problème | Correctif |
|----------|-----------|
| Recall mémoire : dossier client jamais dans le top_k (3/4 chunks = politique_risque + FAQ) | `brain_query` : top_k=8 + **diversification ≤ 2 chunks/source** ([brain.py](llm/brain.py)) |
| Dossier MEDITECH absent de la mémoire (indexeur limité à KNOWLEDGE/) | `indexer` scanne aussi `data/dossiers/` (tag `dossier`) + `purge_source` pour nettoyer les chunks périmés ([rag.py](llm/rag.py), [store.py](llm/store.py)) |
| JSON invalide de deepseek-r1:7b (`"analyse"` en tableau non quoté) | `_reparer_analyse` : quote les lignes — testé sur le JSON réellement raté du 14:28 |
| F7 disait « niveau 2 » alors que le dossier dit niveau 1 | Fait pivot déterministe dans `structurer_pack` : `niveau\s+(\d)` → risque selon politique §2/§3 (confiance 0.9) |

## 3. Résultats de défense (journaux dans OUTPUTS/rapports/)

| Fichier | Verdict | Faits | Notes |
|---------|:-------:|:-----:|-------|
| raisonnement_defense_20260803_140807.json | 🟢 | 8 | 1er succès post-recall |
| raisonnement_defense_20260803_142808.json | ⚠️ | — | JSON raté (déclencheur du réparateur) |
| raisonnement_defense_20260803_143725.json | 🟢 | 9 | `_reparer_analyse` validé sur cas réel |
| raisonnement_defense_20260803_150622.json | 🟢 | 10 | **MEDITECH final** — F4 « risque faible (niveau 1) », confiance 85 %, 1 appel LLM |
| raisonnement_defense_20260803_152318.json | 🟢 | 10 | **Groupe (scénario 06)** — dossier `data/dossiers/groupe.md`, confiance 95 % |

## 4. Dossier Groupe multi-sociétés (scénario 06)

`data/dossiers/groupe.md` : convention-cadre + annexes par filiale, caution
solidaire **holding** (jamais filiales — règle framework C2), plafond
500–3 000 TND, RFA progressive, clause de non-cession. Défendu 🟢 95 %.

## 5. Connaissances déposées (trous INDEX comblés)

- `KNOWLEDGE/conventions/conditions_generales.md` : ⬜ → ✅ 10 sections
  (régimes, paramètres, garanties, circuits de paiement, défaut, renouvellement,
  juridiction) — alignée framework v2.0 + politique de risque.
- `KNOWLEDGE/procedures/procedure_validation.md` : 🟡 coquille → ✅ circuit
  9 étapes, niveaux d'approbation, seuils de décision, archivage.
- Réindexation : **57 chunks** (3 dossiers clients inclus), 2 résidus de
  l'ancienne coquille purgés.

## 6. État roadmap brain v2 (audit du 03/08)

Phases A→D **toutes implémentées** dans `llm/brain.py` :
Intent Planner → Context Builder → `structurer_pack` (A) → `coverage` (B) →
DeepSeek + ModelAssessment (C) → Decision Renderer 5 modes + journal (D).
Aucun écart restant sans nouvelle spécification métier.

## 7. Points ouverts (hors périmètre de ce chantier)

- Valeur réglementaire du tiers saisissable et taux d'usure (FAQ ⚠️ à confirmer).
- Plafonds d'exposition §5 et dérogations §6 de la politique de risque (blocs
  réservés expert métier).
- Différences commerciales MG vs BATAM (FAQ ⬜).
- KPIs de défense : `required_kpis=0/0` — l'intention defense n'exige pas de
  KPI ; enrichissement possible si la décision DSC le demande.

## 8. Commits

- `c3ae898` — dossier MEDITECH défendable (verdict 🟢) + correctifs pipeline.
- (commit final) — dossier Groupe scénario 06, conditions générales,
  procédure de validation, rapport.
