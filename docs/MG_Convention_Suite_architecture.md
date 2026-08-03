# MG Convention Suite — Architecture produit

> Statut : proposition v1, à valider. Auteur : Sisyphus, août 2026.
> Principe : le workspace est une **règle d'import**, pas un déménagement de dossiers.

## 1. Vision

Une plateforme, deux surfaces, un cerveau.

- **Dashboard** — observe. KPIs, tableaux, alertes, tendances, rapports. N'écrit rien dans les données métier.
- **Contract Lab** — décide. Créer une convention, simuler, évaluer le risque, produire un dossier de décision.
- Les deux consomment le même `business/` (métier) et le même `core/` (LLM, mémoire, raisonnement).

## 2. État des lieux vérifié (août 2026)

| Brique | Dashboard (`pilotage_b2b/`) | Contract Lab (`mg-batam-convention-ai/`) | Risque |
|---|---|---|---|
| Registre conventions | `data/conventions_signees.csv` + racine + xlsm GitHub (`TDC CONVENTION 1.xlsm`) — **lit ET écrit** (`app.py:1582,1690,1705,1742`) | `data/conventions_signees.csv` (3ᵉ copie) + `workflows.register_convention` | **Divergence en cours** — 3 CSV identiques aujourd'hui, divergents dans 6 mois |
| Modèle de contrat | `docs/contrat_cession_salaire.md` | `KNOWLEDGE/conventions/contrat_cession_salaire.md` | Doublon de référence |
| Mémoire/embeddings | `memory/` (intent_planner, context_builder, dossier_builder, memory_store, relations…) | `llm/store.py` (MemoryStore, interface propre remember/recall) | Deux moteurs, deux schémas SQLite |
| Raisonnement | `trend_analyzer.py` + `monthly_report.py` (prompts narratifs ad hoc) | `llm/brain.py` (pipeline A→D : intent → dossier → coverage → assessment → renderer + journal) | Le dashboard va recopier brain dès qu'on lui demandera des alertes expliquées |
| Client LLM | none | `llm/client.py` (chat avec meta : modèle, durée, tokens, logging) | Référence à réutiliser |

## 3. Structure cible (logique)

```
pilotage_b2b/                    ← le workspace (racine actuelle)
├── apps/                        ← découpage logique ; physique inchangé
│   ├── dashboard/               = app.py + metrics/ charts/ ui/ utils/ (actuel)
│   └── contract-lab/            = mg-batam-convention-ai/ (actuel)
├── core/                        ← ce qui existe déjà, propre : llm/ du contract lab
│   ├── llm/                     client.py (chat+meta), config.py
│   ├── memory/                  llm/store.py (candidat canonique)
│   └── reasoning/               llm/brain.py + reasoning.py (pipeline A→D)
├── business/                    ← LA création : logique métier pure, sans écran ni prompt
│   ├── conventions.py           load_convention(code), register_convention(...), history(code)
│   ├── risques.py               (à extraire des prompts : _grille_risque)
│   ├── kpis.py                  (existant côté dashboard : metrics/kpi.py)
│   ├── renouvellement.py        (seuil 60j etc.)
│   └── reporting.py             (monthly_report — plus tard)
├── data/
│   ├── conventions_signees.csv  ← UN SEUL registre (ex-3 copies : data/, racine, mg-batam/data/)
│   ├── sqlite/                  brain.db · registre.db · logs.db · cache.db (séparés par domaine)
│   ├── exports/  cache/
├── docs/  tests/
```

## 4. Contrats de modules

- `business.conventions.load_convention(code) -> dict | None` — lit le registre unique.
- `business.conventions.register_convention(code, client, ...) -> dict` — écrit dans le registre unique (seul point d'écriture métier autorisé).
- `core.memory.MemoryStore(namespace).remember/recall` — interface existante de `llm/store.py`.
- `core.reasoning.raisonner(demande, mode) -> str` — pipeline brain existant, consommable par les deux apps.
- `core.llm.chat(prompt, role, system, meta=False) -> str | (str, meta)` — client existant.

## 5. Règles de commit (la loi du workspace)

1. Toute nouvelle brique va dans `core/` ou `business/`, jamais dans une app.
2. Une app n'importe que des briques partagées — jamais du code copié d'une autre app.
3. Aucun prompt ne contient de calcul métier (Business Core). Les règles métier vivent en Python, les prompts les citent.
4. Aucun écran n'écrit dans les données métier — sauf via `business.conventions.register_convention()`.
5. Le dashboard observe ; les écritures système (mémoire, logs, cache, exports, push GitHub) restent autorisées.
6. Les deux apps n'importent JAMAIS directement les fichiers internes de l'autre.

## 6. Décisions différées (YAGNI — on attend une vraie demande)

- `apps/admin/`, `auth/` — pas d'utilisateurs aujourd'hui.
- `business/simulations.py` — pas encore de contrat métier.
- Hub UI (`st.navigation`) — Streamlit le fait nativement ; on l'active quand une surface Contract Lab UI existe.
- Fusion physique des dossiers (`apps/`) — l'import est la frontière ; déplacer ne paie que si le partage est prouvé.
- Pivot CSV → SQLite pour le registre — seulement quand le contrat le demande (concurrence, historique volumineux).

## 7. Roadmap de migration

| Étape | Contenu | Bénéfice | Risque |
|---|---|---|---|
| **1. Registre unique** | Créer `business/conventions.py` à la racine ; 3 CSV → 1 ; brancher `app.py` (lecture+écriture), `loader`, `transforms`, `trend_analyzer`, `workflows.py` (contract lab) dessus | Tue la divergence la plus dangereuse | Faible (CSV conservé, mêmes champs) |
| **2. Mémoire unique** | `core/memory` absorbe `llm/store.py` ; `memory/` du dashboard devient un import | Un seul schéma d'embeddings | Moyen (schémas à concilier) |
| **3. Raisonnement brique** | `core/reasoning` = pipeline brain ; `trend_analyzer`/`monthly_report` consomment au lieu de recopier | Le dashboard hérite de A→D sans réécrire | Moyen |
| **4. Hub UI** | `st.navigation` + surface Contract Lab si demandé | Une seule plateforme perçue | Faible |

Étape 1 = prochaine exécution (B). Les étapes 2-4 se font chacune sur un go explicite.
