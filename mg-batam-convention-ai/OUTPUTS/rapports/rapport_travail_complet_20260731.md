# Rapport complet du travail effectué — convention-ai (SMG / MG-BATAM)

**Date :** 2026-07-31 · **Projet :** `mg-batam-convention-ai` · **Stack :** Python 3.14, Streamlit (dashboard voisin), Pandas, SQLite, Ollama, Groq API

---

## 1. Contexte et objectifs de la session

Le projet `convention-ai` assiste l'expert métier SMG dans le cycle de vie des conventions B2B (MG / BATAM) : audit juridique, contre-audit, analyse de risque, négociation, décision comex, rédaction, suivi.

Trois missions ont été menées dans cette session :

| # | Mission | Livrable |
|---|---|---|
| 1 | **Autonomiser** convention-ai (zéro dépendance au dashboard `pilotage_b2b`) | `smg_data.py`, `llm/store.py`, registre local, refonte des imports |
| 2 | **Ajouter une capacité de raisonnement structuré** (faits sourcés, trous de connaissance) | `llm/reasoning.py` (ReasoningDossier) + intégration workflows |
| 3 | **Revue critique complète du système** avec une nouvelle capacité de raisonnement (llama-3.3-70b-versatile via Groq), puis corrections validées | Rapport de revue + 3 corrections (dont 1 bug P0 prouvé) |

---

## 2. Schéma complet du système (état final)

```
                            ┌─────────────────────────────────────────────┐
                            │             EXPERT MÉTIER (CLI)             │
                            │   python main.py <commande> [arguments]     │
                            └──────────────────┬──────────────────────────┘
                                               │
                                               ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                              main.py  (CLI, 13 commandes)                     │
│  audit · risque · comparer · negocier · comex · question · indexer · register │
│  workflow {revue_complete | nouvelle | renouvellement}                        │
└───────┬───────────────┬──────────────────┬─────────────────┬─────────────────┘
        │               │                  │                 │
        ▼               ▼                  ▼                 ▼
┌──────────────┐ ┌──────────────┐ ┌───────────────┐ ┌────────────────────────┐
│  workflows   │ │  llm/agents  │ │  llm/rag      │ │  workflows.register    │
│  3 workflows │ │  5 personas  │ │  (RAG léger)  │ │  ───────────────────── │
│  orchestrés  │ │  (AGENTS/*)  │ │               │ │  data/                │
└──────┬───────┘ └──────┬───────┘ └──────┬────────┘ │  conventions_signees.csv│
       │                │                │          │  (registre de suivi)   │
       │                ▼                │          └────────────────────────┘
       │        ┌──────────────┐         │
       │        │ llm/client   │         │
       │        │  chat()      │         │
       │        │  provider()  │         │
       │        └──┬───────┬───┘         │
       │           │       │             │
       │    ┌──────▼──┐ ┌──▼──────────┐  │
       │    │ OLLAMA  │ │ GROQ API    │  │
       │    │ qwen2.5 │ │ llama-3.3-  │  │
       │    │ :7b     │ │ 70b-versatile│ │
       │    └─────────┘ └─────────────┘  │
       │                                │
       ▼                                ▼
┌──────────────────┐        ┌───────────────────────────┐
│ llm/store (SQLite│        │ smg_data.py (loader auto) │
│ + embeddings)    │        │  GITHUB_RAW (pilotage-b2b │
│ data/convention_ │        │  GitHub) → VC + Code      │
│ ai.sqlite        │        │  magasin → KPIs CA N/N-1  │
└──────────────────┘        └───────────────────────────┘
```

### 2.1 Les modules (rôle + responsabilité)

| Module | Rôle | Point clé |
|---|---|---|
| `main.py` | CLI — point d'entrée unique | 13 commandes, `sys.stdout.reconfigure` (console Windows + emojis) |
| `workflows.py` | Orchestration des 3 procédures du dossier | Chaque étape écrit dans `OUTPUTS/` ; injecte les trous détectés dans le prompt comex |
| `llm/agents.py` | Les 5 personas SMG (juriste, contradicteur, négociateur, comex, rédacteur) | Prompts système chargés depuis `AGENTS/*.md` (source unique) |
| `llm/client.py` | Client LLM unifié, routage **Ollama > Groq selon le modèle** | `provider(model)` vérifie que le modèle est installé dans Ollama avant de choisir (fix P0) |
| `llm/config.py` | Configuration centralisée | `MODELS` par rôle, endpoints, `KNOWLEDGE_DIR`… |
| `llm/reasoning.py` | **ReasoningDossier** — compilation d'un audit en faits/actions/trous | 4 passes pures, normalisation accents, anti-hallucination |
| `llm/rag.py` + `llm/store.py` | Mémoire RAG autonome (SQLite + embeddings all-minilm) | Dégradation silencieuse → recherche mots-clés si Ollama down |
| `smg_data.py` | Chargement autonome des données de facturation (ex-dashboard) | `_fetch` GitHub → `_clean` → dates → magasins → filtre individus |
| `data/conventions_signees.csv` | Registre de suivi local (semi-colon) | create/update idempotent, `nb_modifications` |

### 2.2 Les modèles LLM par rôle (`llm/config.py`)

| Rôle | Modèle | Endpoint |
|---|---|---|
| `analyse` (audit, risque, comparaison) | `qwen2.5:7b` | Ollama local |
| `negociation` | `qwen2.5:7b` | Ollama local |
| `comex` (décision) | `qwen2.5:7b` | Ollama local |
| `redaction` (rédaction juridique) | `llama-3.3-70b-versatile` | Groq API (qualité française) |

Chaque modèle est surchargeable par variable d'env (`CAI_ANALYSE_MODEL`, `CAI_REDACTION_MODEL`…). Température 0.3 (factuel), max_tokens 4096.

---

## 3. Traitement des données — flux détaillé

### 3.1 Données de facturation (KPIs de renouvellement)

```
GitHub raw (pilotage-b2b/2025/)
  ├─ Factures ventes VC (4).xlsx
  └─ Code MAGASIN Business Central.xlsx
        │
        ▼  smg_data.py
  _fetch() → _clean() (colonnes nettoyées)
  → _add_date_cols()  (Date comptabilisation → Date / Année / Mois / Jour)
  → _map_magasins()   (code Navision → nom magasin + enseigne MG/BATAM)
  → _filter_conventions()  (exclut 4 noms individuels : AHMED ABIDI, AMARA MISSAOUI,
                             BILEL BEN AMMAR, MED KAIS SMAILI)
        │
        ▼  workflows._kpis_vente(client)
  Matching par tokens (≥3 lettres, ≥2 tokens communs) sur la colonne Nom
  → CA année N, CA année N-1, évolution % (ex : "CA facturé 2025: 406,314 TND |
     CA 2024: 481,300 TND | Évolution: -15.6%")
        │
        ▼  Dégradation silencieuse
  Réseau KO → DataFrame vide → KPI absent du bilan (le workflow continue)
```

### 3.2 Documents de convention (workflow revue complète)

```
Convention (md/docx)
  │
  ▼  [1/4] agents.audit()        → rapport markdown (clauses, constats 🔴🟠🟡, règles,
  │                                 impacts, recommandations, questions)
  ▼  _dossier_audit()            → ReasoningDossier JSON (faits sourcés + trous)
  ▼  [2/4] agents.contre_audit() → faille hunting (probabilité, impact, scénario)
  ▼  [3/4] agents.preparer_negociation()  (si renégociation)
  ▼  [4/4] agents.synthese_comex(dossier + POINTS À CONFIRMER détectés automatiquement)
  │                                 → décision ✅/✏️/❌/⏳
  ▼
OUTPUTS/rapports/ + OUTPUTS/syntheses/  (horodatés YYYYMMDD)
```

### 3.3 Mémoire RAG (KNOWLEDGE/ → SQLite + embeddings)

```
KNOWLEDGE/**/*.md (lecture seule pour les agents)
  │
  ▼  python main.py indexer → llm/rag.indexer()
  _chunks(text, 1500) → découpage par paragraphes
  → MemoryStore.remember(chunk, tags, source)   [idempotent par hash SHA-256]
  → embedding all-minilm:latest via Ollama (384 dims, BLOB binaire)
        │
        ▼  question / audit --rag
  MemoryStore.recall(query) → cosinus sim (80%) + score usage (20%)
  → top-4 chunks → enrichir_prompt() → contexte KNOWLEDGE injecté
        │
        ▼  Dégradation silencieuse
  Ollama down → recherche par mots-clés (comptage de termes)
```

### 3.4 Registre de suivi (`data/conventions_signees.csv`)

```
register_convention(code, client, scenario, garantie, statut, date_signature, notes)
  → existe ? update (nb_modifications +1) : insert (date_debut_prospection = aujourd'hui)
  → écriture complète CSV delimiter=";"   [ponytail: sans verrou — SQLite si écritures concurrentes]
  → retourne "created" | "updated"
```

### 3.5 ReasoningDossier — le raisonnement structuré (`llm/reasoning.py`)

```
Audit markdown brut (sortie LLM)
  │
  ▼  compile_dossier() — 4 passes séquentielles, non fatales (une passe en erreur
  │  est marquée dans passes_run sans casser le pipeline)
  │
  ├─ pass_extract_objective  → titre "# Audit …" ou première ligne
  ├─ pass_extract_facts      → sections ## Constats / Points positifs / Questions ouvertes
  │     • chaque constat 🔴/🟠/🟡 → Fact(kind=constat, confidence 0.9/0.75/0.6, source=clause)
  │     • "Règle applicable" → Fact(kind=regle, conf 0.8)
  │     • "Recommandation" → Action(priority 0/1/2 selon sévérité)
  │     • Verdict global → Constraint(severity error/warning/info)
  ├─ pass_detect_missing     → texte normalisé (accents → ASCII, minuscules, car les
  │     sorties LLM mélangent « à confirmer » / « a confirmer »)
  │     → patterns : à confirmer, à vérifier, absent, manquant, ________, …
  │     → liste missing + Constraint(warning) par trou
  └─ pass_validate           → intégrité : objectif non vide, ≥1 constat structuré
        │
        ▼  render_json() → archive JSON dans OUTPUTS/rapports/*_dossier_YYYYMMDD.json
        │
        ▼  INTÉGRATION COMEX (anti-hallucination)
  dossier.missing → section "--- POINTS À CONFIRMER (détection automatique) ---"
  injectée dans le dossier soumis à synthese_comex : le comex sait ce qui
  n'est PAS confirmé avant de trancher.
```

---

## 4. Le raisonnement — décisions et justifications

### 4.1 Pourquoi l'autonomisation (mission 1)

- **Constat** : convention-ai dépendait du repo racine `pilotage_b2b` (imports `sys.path` vers le parent, loader/transforms du dashboard, registre CSV distant, mémoire du dashboard).
- **Décision** : copier le **strict nécessaire** dans le projet (`smg_data.py`, `llm/store.py`, `data/conventions_signees.csv`) et supprimer tous les couplages (plus aucun `sys.path.insert` vers le parent).
- **Pourquoi ce périmètre** : les KPIs de renouvellement (CA N/N-1) ne nécessitent que 2 fichiers (VC + code magasin) et 4 transformations. Répliquer plus aurait créé de la dette.

### 4.2 Pourquoi un ReasoningDossier plutôt qu'un port complet (mission 2)

- Trois options ont été évaluées : **A)** audit structuré (faits + trous) — ROI maximal, ~6 fichiers ; **B)** évaluateur de pertinence — utile mais secondaire ; **C)** port complet du pipeline de raisonnement du dashboard — refonte lourde, non justifiée.
- **Choix : A.** Le besoin réel : éviter que le comex prenne une décision sur un audit qui contient des trous (« à confirmer », « non fourni », « ________ »). La détection de trous + injection dans le prompt comex est la mesure anti-hallucination la plus rentable.

### 4.3 Pourquoi la revue via llama-3.3-70b-versatile (mission 3)

- Demande explicite : revue complète avec une « très nouvelle capacité de raisonnement », **en utilisant llama**.
- **Contrainte découverte** : llama-3.3-70b-versatile n'est pas installé localement — il est servi par **l'API Groq** (Groq = hébergeur, llama = modèle). Le rôle `redaction` y était déjà mappé.
- **Contournement nécessaire** : le client unifié `provider()` privilégiait Ollama dès qu'il tournait → la revue a utilisé un script temporaire appelant Groq directement, en 4 passes ≤ 21k chars chacune (limite payload 413 de Groq) avec persistance incrémentale + retry sur 429.

### 4.4 Résultats de la revue — honnêteté sur la qualité

La sortie llama (rapport brut : `revue_systeme_20260731.md`) contenait :
- **Vrai (confirmé)** : gestion des exceptions de connexion LLM (→ bug P0 réel), statuts INDEX non alignés, coquilles KNOWLEDGE.
- **Bruit rejeté** : numéros de ligne hallucinés (`workflows.py:150/200/250` inexistants), « utiliser une base de données », « sécuriser les clés API » (déjà en env vars), trous connus re-signalés malgré la consigne.
- **Verdict documenté** : llama vaut confirmation partielle, pas verdict d'expert.

### 4.5 Les corrections appliquées (validées par l'expert métier)

| # | Sévérité | Correction | Raisonnement |
|---|---|---|---|
| 1 | **P0** | `llm/client.py` : `_ollama_has_model(model)` — ne choisit `ollama` que si le modèle demandé y est installé, sinon `groq` | Prouvé en exécution : le rôle rédaction (llama via Groq) partait vers `localhost:11434` → 404 tant qu'Ollama tournait. Rôle inutilisable. |
| 2 | **P2** | `KNOWLEDGE/INDEX.md` : statuts alignés sur la réalité (placeholder vs coquille vs prêt) | `convention_modele_rtt.md` existait mais était marqué « à déposer » ; procédures marquées « à rédiger » alors que les coquilles existent. |
| 3 | **P2** | Grille de risque SMG déplacée d'`agents.py` (valeur en dur) vers `KNOWLEDGE/procedures/politique_risque.md`, lue via `_grille_risque()` | Convention du projet : pas de valeurs en dur ; KNOWLEDGE = source unique (lecture seule pour les agents). |

### 4.6 Ce qui a été refusé de toucher

- Fallback embeddings → mots-clés dans `store.py` : déjà géré, **ne pas toucher**.
- Écriture CSV sans verrou : choix assumé (usage monocanal) — passer en SQLite **si** des écritures concurrentes apparaissent.
- La politique de risque complète (appétit, plafonds, dérogations) : reste **à rédiger par l'expert métier** (trou connu, pas un bug).

---

## 5. Vérifications effectuées (chaque livrable prouvé)

| Livrable | Preuve |
|---|---|
| Autonomie (imports) | `grep` sur tout le projet : **zéro** référence à `pilotage_b2b` |
| `smg_data.load_vc` | Test réel : `_kpis_vente("Amicale Personnel CNAM")` → CA N=406 314 / N-1=481 300 / **-15,6 %** |
| Registre CSV | Test réel : création + mise à jour (`created` / `updated`) |
| Indexeur RAG | Test réel : **14 chunks** indexés depuis KNOWLEDGE/ |
| `llm/reasoning` | Self-check `python -m llm.reasoning` : 6 faits, 2 manques, 2 actions, verdict 🔴 — **vert** |
| `_dossier_audit` | Test JSON réel : objectif, faits sourcés, missing, passes_run |
| **Fix P0 (provider)** | Exécution réelle : `provider('qwen2.5:7b') → ollama` · `provider('llama-3.3-70b-versatile') → groq` · `chat(role='redaction')` → `[LLM] llama-3.3-70b-versatile via groq...` → réponse **OK** |
| Grille de risque | `py_compile` OK sur `client.py` + `agents.py` ; grep : plus aucun résidu de grille en dur |
| Scripts temporaires | `revue_tmp.py` supprimé après usage (cleanup) |

---

## 6. État final et suites possibles

**État :** système entièrement autonome, avec raisonnement structuré anti-hallucination, revu de bout en bout et corrigé (P0 + 2×P2). Tous les checks passent.

**Suites possibles (non demandées, non engagées) :**
1. Passer le registre CSV en SQLite si écritures concurrentes (ponytail-comment déjà en place).
2. Rédiger les procédures réelles (validation interne, politique de risque complète) dans KNOWLEDGE.
3. Option B évaluée en mission 2 (évaluateur de pertinence des retours RAG).
4. Déposer `convention_modele_rtt.md` et `conditions_generales.md` réels.

---

## 7. Phase suivante — architecture cible `brain` v2 (validée en discussion, NON implémentée)

Retour expert reçu après la mission 4 (couche `brain`). Quatre briques proposées, discutées,
arbitrées, **documentées ici pour implémentation ultérieure — aucun code écrit à ce stade.**

### 7.1 Pipeline cible

```
Utilisateur
    │
    ▼
Intent Planner (déterministe, existant)
    │
    ▼
Context Builder (existant)
    │
    ▼
Brain Query (mémoire SQLite + Ollama optionnel, existant)
    │
    ▼
ReasoningDossier  ← NOUVEAU : structurer_pack() déterministe
    │   objectif · faits sourcés · contraintes · manques · actions
    ▼
DeepSeek (raisonnement, citant [F3], [F7]…)
    │
    ▼
Decision Renderer  ← NOUVEAU : --mode expert | dg | technique | commercial | audit
```

### 7.2 Les 4 briques (décisions d'arbitrage)

| Brique | Décision retenue | Ce qui est refusé et pourquoi |
|---|---|---|
| **ReasoningDossier dans le pipeline** | `structurer_pack()` **déterministe**, réutilisant les dataclasses `Fact/Constraint/Action` et les patterns de trous de `llm/reasoning.py` ; faits = chunks (source+score) + registre + KPIs ; manques = patterns + données absentes selon l'intention | Réutiliser `compile_dossier()` tel quel : il est spécialisé au format d'audit markdown, inadapté aux chunks KNOWLEDGE |
| **Coverage Engine** (ex-« Confidence Engine ») | Deux objets séparés et complémentaires — **jamais un chiffre unique** : le comptage mélangerait qualité des données et qualité du raisonnement (10 docs dont 9 contradictoires = score élevé, confiance réelle faible). Voir contrats 7.2.1 et 7.2.2 | Un pourcentage mécanique unique (nb preuves → %) : faux air de rigueur |
| **Evidence Graph** | **Liste chaînée de références** : DeepSeek cite `[F3]`, le rendu résout `[F3] → source (chemin fichier) → document`. Les sources existent déjà (chunk = chemin KNOWLEDGE, fait = clause) | Un vrai graphe (nœuds/arêtes stockés) : sur-ingénierie pour un besoin de traçabilité linéaire |
| **Decision Renderer** | Paramètre `--mode` changeant le prompt final ; le raisonnement (dossier) reste identique, **une seule génération** | Deux appels LLM (raisonnement puis reformatage) : coût doublé sans valeur ajoutée |

#### 7.2.1 Contrat `ContextCoverage` (calculé par le système — objectif, mesurable)

```
coverage:
  required_sources: 4        # définies par intention (mapping déterministe, cf. 7.5)
  available_sources: 3
  required_kpis: 5
  available_kpis: 5
  memory_chunks: 8
  average_relevance: 0.82
  missing:
    - Politique risque
    - Historique BATAM
```

Ce que le système **possède**, ce qui **manque**, ce qui est **exploitable**. Il ne mesure
pas la vérité : il mesure l'état du contexte. C'est le contrat de la Phase B.

#### 7.2.2 Contrat `ModelAssessment` (produit par DeepSeek — déclaration subjective)

```
assessment:
  confidence: 72             # auto-évaluation 0-100, déclarée par le modèle
  rationale:
    - politique_risque absente
    - registre présent
    - KPIs présents
    - mémoire pertinente
  unanswered:
    - plafond BATAM
```

Ce n'est pas le système qui affirme être sûr : c'est le modèle qui déclare son propre
niveau de confiance, avec ses justifications et ce qu'il ne peut pas répondre.

### 7.3 Orchestration Ollama (point « Stopping »)

- Vérifié : le pipeline est **strictement séquentiel** (Python synchrone : brain_query termine avant l'appel de génération) — pas de collision de générations.
- À ajouter au prochain passage : journalisation début/fin/durée/modèle dans `llm/client.chat` (3 lignes) pour diagnostiquer les blocages apparents.
- Le « blocage » suspecté est très probablement le temps de raisonnement de `deepseek-r1:7b` sur CPU — ressemble à un stop, n'en est pas un.

### 7.4 Roadmap validée (phases A → D)

| Phase | Contenu | Sortie |
|---|---|---|
| **A** | Context Builder → **ReasoningDossier** (`structurer_pack()` déterministe) | Dossier sourcé (faits, contraintes, manques) |
| **B** | Dossier → **Evidence Renderer** → sources → **Coverage Report** | `ContextCoverage` (objectif) |
| **C** | `Coverage Report` + **DeepSeek Assessment** → réponse | `ContextCoverage` + `ModelAssessment` + réponse structurée |
| **D** | **Logs de raisonnement** — pas seulement techniques : Intent · Sources utilisées · Sources ignorées · Contraintes · Inconnues · Temps · Tokens · Réponse | Journal JSON archivé (`OUTPUTS/rapports/*_raisonnement_YYYYMMDD.json`) — dans 6 mois, ces journaux expliqueront pourquoi une réponse était bonne ou mauvaise |

### 7.5 Principe d'architecture (règle gravée, issue de l'arbitrage)

> **Aucun composant architectural ne doit être introduit avant que son contrat métier soit clairement défini.**

Autrement dit : pas de « Decision Engine » parce que le nom est séduisant — seulement
lorsqu'on sait exactement quelles décisions il doit prendre. Application immédiate : le
`required_sources` du ContextCoverage exige un **mapping intention → sources requises**
(ex : renouvellement requiert registre + KPIs + politique de risque + contrat ; question
requiert mémoire + FAQ) — ce mapping est le contrat métier de la Phase A, à définir avec
l'expert avant d'écrire le code.

---

*Rapport généré depuis le suivi de session — fichiers de référence : `main.py`, `workflows.py`, `llm/` (`config`, `client`, `agents`, `reasoning`, `rag`, `store`, `brain`), `smg_data.py`, `KNOWLEDGE/INDEX.md`, `OUTPUTS/rapports/revue_systeme_20260731.md`.*
