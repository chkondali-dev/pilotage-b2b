"""
corpus.py — Jeu de test structuré pour le ReasoningEvaluator.

Chaque question a :
  - id unique
  - category (EXPLORE|DEBUG|REFACTOR|ARCH|REPORT|GENERAL)
  - question text
  - expected_keywords : termes qui DEVRAIENT apparaître dans une bonne réponse
  - expected_files : fichiers qui devraient être référencés
  - difficulty : 1-5
"""

from dataclasses import dataclass, field
from typing import Optional

CORPUS_VERSION = "1.0.0"


@dataclass
class EvalQuestion:
    id: str
    category: str          # EXPLORE | DEBUG | REFACTOR | ARCH | REPORT | GENERAL
    question: str
    expected_keywords: list[str] = field(default_factory=list)
    expected_files: list[str] = field(default_factory=list)
    difficulty: int = 1    # 1-5
    note: str = ""


def _explore_questions() -> list[EvalQuestion]:
    return [
        EvalQuestion(
            id="EXP-001", category="EXPLORE",
            question="comment fonctionne index_file dans code_indexer ?",
            expected_keywords=["index_file", "code_indexer", "tree-sitter", "AST", "parcourir"],
            expected_files=["code_indexer.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-002", category="EXPLORE",
            question="où est gérée la palette de couleurs dans le dashboard ?",
            expected_keywords=["C", "config", "couleur", "palette", "data/config"],
            expected_files=["data/config.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-003", category="EXPLORE",
            question="qu'est-ce que MemoryStore.recall retourne ?",
            expected_keywords=["recall", "embedding", "vector", "keyword", "list", "dict"],
            expected_files=["memory/memory_store.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-004", category="EXPLORE",
            question="montre la structure du pipeline compile_dossier",
            expected_keywords=["compile_dossier", "passe", "extract", "infer", "validate",
                               "ReasoningDossier", "DossierDelta"],
            expected_files=["dossier_builder.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="EXP-005", category="EXPLORE",
            question="trouve les fichiers qui utilisent Plotly dans le projet",
            expected_keywords=["Plotly", "chart", "factory", "graphique"],
            expected_files=["charts/factory.py", "app.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-006", category="EXPLORE",
            question="comment le ContextBuilder construit le Context Pack ?",
            expected_keywords=["ContextBuilder", "build", "plan", "RetrievalPlan",
                               "Context Pack"],
            expected_files=["context_builder.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-007", category="EXPLORE",
            question="où sont définis les IntentKind ?",
            expected_keywords=["IntentKind", "EXPLORE", "DEBUG", "REFACTOR", "ARCH",
                               "REPORT", "GENERAL", "Enum"],
            expected_files=["dossier_builder.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-008", category="EXPLORE",
            question="décris le rôle de RelationsStore",
            expected_keywords=["RelationsStore", "call", "import", "inherit",
                               "graphe", "relation"],
            expected_files=["relations.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-009", category="EXPLORE",
            question="quel est le chemin de la base SQLite mémoire ?",
            expected_keywords=[".opencode_memory", "sqlite", "namespace", "MEMORY_DIR",
                               "Path.home"],
            expected_files=["memory_store.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-010", category="EXPLORE",
            question="comment le IntentPlanner détecte l'intention d'une requête ?",
            expected_keywords=["IntentPlanner", "plan", "RetrievalPlan", "pattern",
                               "symbole", "confidence"],
            expected_files=["intent_planner.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="EXP-011", category="EXPLORE",
            question="quels champs contient la structure Fact ?",
            expected_keywords=["Fact", "text", "kind", "confidence", "source",
                               "symbol", "file", "line"],
            expected_files=["dossier_builder.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-012", category="EXPLORE",
            question="où est le point d'entrée du dashboard Streamlit ?",
            expected_keywords=["app.py", "streamlit", "run", "bootstrap"],
            expected_files=["app.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-013", category="EXPLORE",
            question="comment les données sont chargées dans le dashboard ?",
            expected_keywords=["loader", "load_all_data", "_fetch", "GitHub",
                               "cache", "st.cache_data"],
            expected_files=["data/loader.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-014", category="EXPLORE",
            question="qu'est-ce que le RendererPrompt affiche ?",
            expected_keywords=["RendererPrompt", "render", "INTENT", "OBJECTIF",
                               "FAITS", "HYPOTHESES"],
            expected_files=["dossier_builder.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-015", category="EXPLORE",
            question="explique le mécanisme d'injection de contexte en début de session",
            expected_keywords=["inject_context", "injector", "session_start",
                               "memory", "contexte"],
            expected_files=["injector.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="EXP-016", category="EXPLORE",
            question="comment les métriques KPI sont calculées dans le dashboard ?",
            expected_keywords=["kpi", "CA", "évolution", "date", "compare_years",
                               "metrics"],
            expected_files=["metrics/kpi.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-017", category="EXPLORE",
            question="qu'est-ce que DossierDelta contient ?",
            expected_keywords=["DossierDelta", "facts", "constraints", "actions",
                               "hypotheses", "signals"],
            expected_files=["dossier_builder.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-018", category="EXPLORE",
            question="dans quel fichier les composants UI sont-ils définis ?",
            expected_keywords=["ui/components", "inject_css", "hero", "section",
                               "badge"],
            expected_files=["ui/components.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-019", category="EXPLORE",
            question="trouve le module qui gère les alertes de tendances",
            expected_keywords=["trend_alert_panel", "alerte", "tendance", "UI"],
            expected_files=["trend_alert_panel.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="EXP-020", category="EXPLORE",
            question="à quoi sert le module monthly_report.py ?",
            expected_keywords=["monthly_report", "rapport", "mensuel", "IA",
                               "génération"],
            expected_files=["monthly_report.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="EXP-021", category="EXPLORE",
            question="comment la fonction _compute_embedding gère-t-elle l'indisponibilité d'Ollama ?",
            expected_keywords=["_compute_embedding", "Ollama", "ping", "cache",
                               "fallback", "None", "ConnectionRefused"],
            expected_files=["memory/memory_store.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="EXP-022", category="EXPLORE",
            question="quelles commandes CLI sont disponibles dans memory/cli.py ?",
            expected_keywords=["cli", "brain", "context", "search", "add", "list",
                               "index"],
            expected_files=["cli.py"],
            difficulty=1,
        ),
    ]


def _debug_questions() -> list[EvalQuestion]:
    return [
        EvalQuestion(
            id="DBG-001", category="DEBUG",
            question="le calcul d'évolution N vs N-1 semble faux, qu'est-ce qui peut causer une différence ?",
            expected_keywords=["compare_years", "date_to_date", "tronqué", "jours",
                               "N-1", "période"],
            expected_files=["metrics/kpi.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="DBG-002", category="DEBUG",
            question="pourquoi un appel à recall retourne 0 résultats alors que la mémoire contient des entrées ?",
            expected_keywords=["recall", "embedding", "min_score", "vector",
                               "Ollama", "fallback", "keyword"],
            expected_files=["memory/memory_store.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="DBG-003", category="DEBUG",
            question="le dashboard ne charge pas, que vérifier ?",
            expected_keywords=["streamlit", "cache", "TTL", "loader", "_fetch",
                               "GitHub", "URL", "réseau"],
            expected_files=["data/loader.py", "data/config.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="DBG-004", category="DEBUG",
            question="un test échoue à cause d'une importation circulaire dans memory/, comment la résoudre ?",
            expected_keywords=["import", "circulaire", "cycle", "dépendance",
                               "dossier_builder", "context_builder"],
            difficulty=4,
        ),
        EvalQuestion(
            id="DBG-005", category="DEBUG",
            question="pourquoi _extract_symbol retourne None pour 'comment fonctionne la fonction login' ?",
            expected_keywords=["_extract_symbol", "token", "CamelCase", "snake_case",
                               "dossier_builder", "symbole"],
            expected_files=["dossier_builder.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="DBG-006", category="DEBUG",
            question="la fonction compile_dossier lève ValueError, quelles sont les causes possibles ?",
            expected_keywords=["compile_dossier", "ValueError", "validate",
                               "objective", "dossier", "vide"],
            expected_files=["dossier_builder.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="DBG-007", category="DEBUG",
            question="l'identité visuelle du dashboard ne correspond plus aux couleurs attendues, que vérifier ?",
            expected_keywords=["C", "config", "couleur", "palette", "hex",
                               "data/config"],
            expected_files=["data/config.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="DBG-008", category="DEBUG",
            question="une question de type DEBUG n'est pas détectée correctement, quel pattern vérifier ?",
            expected_keywords=["detect_intent", "_is_debug_query", "keywords",
                               "DEBUG", "intent"],
            expected_files=["dossier_builder.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="DBG-009", category="DEBUG",
            question="le tri topologique des passes ignore certaines passes, pourquoi ?",
            expected_keywords=["_resolve_pass_order", "dépendance", "requires",
                               "passe", "tri", "exécuté"],
            expected_files=["dossier_builder.py"],
            difficulty=4,
        ),
        EvalQuestion(
            id="DBG-010", category="DEBUG",
            question="la fonction push_csv_to_github échoue silencieusement, quelles vérifications faire ?",
            expected_keywords=["push_csv_to_github", "GitHub", "API", "token",
                               "erreur", "exception", "silencieux"],
            expected_files=["utils/github.py"],
            difficulty=3,
        ),
    ]


def _refactor_questions() -> list[EvalQuestion]:
    return [
        EvalQuestion(
            id="REF-001", category="REFACTOR",
            question="comment simplifier le passage des paramètres entre IntentPlanner et ContextBuilder ?",
            expected_keywords=["RetrievalPlan", "plan", "interface", "contrat",
                               "dataclass"],
            difficulty=3,
        ),
        EvalQuestion(
            id="REF-002", category="REFACTOR",
            question="l'injecteur charge trop d'entrées mémoire en début de session, que faire ?",
            expected_keywords=["injector", "top_k", "min_score", "limite",
                               "pertinence", "seuil"],
            expected_files=["injector.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="REF-003", category="REFACTOR",
            question="la fonction _parse_context_pack est longue, comment la découper ?",
            expected_keywords=["_parse_context_pack", "section", "parse", "ligne",
                               "fact", "helper"],
            expected_files=["dossier_builder.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="REF-004", category="REFACTOR",
            question="comment réduire la duplication entre RendererPrompt et RendererJSON ?",
            expected_keywords=["Renderer", "render", "itération", "helper",
                               "dossier", "sections"],
            expected_files=["dossier_builder.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="REF-005", category="REFACTOR",
            question="les mots-clés de détection d'intent sont dispersés, comment les centraliser ?",
            expected_keywords=["detect_intent", "keywords", "config", "constante",
                               "frozenset"],
            expected_files=["dossier_builder.py"],
            difficulty=2,
        ),
    ]


def _arch_questions() -> list[EvalQuestion]:
    return [
        EvalQuestion(
            id="ARC-001", category="ARCH",
            question="décris l'architecture globale du pipeline de raisonnement",
            expected_keywords=["IntentPlanner", "ContextBuilder", "compile_dossier",
                               "ReasoningDossier", "passe", "Renderer"],
            difficulty=3,
        ),
        EvalQuestion(
            id="ARC-002", category="ARCH",
            question="quels modules dépendent de SQLite dans le projet ?",
            expected_keywords=["memory_store", "SQLite", "base", "persistance"],
            expected_files=["memory/memory_store.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="ARC-003", category="ARCH",
            question="quel est le flux de données entre les 3 couches principales du Project Brain ?",
            expected_keywords=["MemoryStore", "RelationsStore", "CodeIndexer",
                               "injecter", "contexte"],
            difficulty=3,
        ),
        EvalQuestion(
            id="ARC-004", category="ARCH",
            question="comment les passes de compilation communiquent-elles entre elles ?",
            expected_keywords=["DossierDelta", "dossier", "apply", "ReasoningDossier",
                               "fusion", "séquentiel"],
            expected_files=["dossier_builder.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="ARC-005", category="ARCH",
            question="pourquoi le dossier ne contient-il pas de méthode render ?",
            expected_keywords=["Renderer", "séparation", "préoccupation",
                               "IR", "pure", "render"],
            expected_files=["dossier_builder.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="ARC-006", category="ARCH",
            question="quel est le rôle de chaque répertoire sous la racine du projet ?",
            expected_keywords=["data", "metrics", "charts", "ui", "utils", "memory",
                               "rôle", "responsabilité"],
            difficulty=1,
        ),
        EvalQuestion(
            id="ARC-007", category="ARCH",
            question="comment les nouveaux jeux de données sont-ils ajoutés au dashboard ?",
            expected_keywords=["FILES", "config", "loader", "GitHub", "transforms",
                               "onglet"],
            expected_files=["data/config.py", "data/loader.py"],
            difficulty=3,
        ),
        EvalQuestion(
            id="ARC-008", category="ARCH",
            question="décris le cycle de vie d'une session OpenCode avec le Project Brain",
            expected_keywords=["session_start", "inject", "contexte", "query",
                               "pipeline", "capture", "memory"],
            expected_files=["session_start.py", "injector.py"],
            difficulty=4,
        ),
    ]


def _report_questions() -> list[EvalQuestion]:
    return [
        EvalQuestion(
            id="RPT-001", category="REPORT",
            question="quel est le CA du mois dernier ?",
            expected_keywords=["CA", "chiffre", "affaires", "mois", "metrics/kpi"],
            difficulty=2,
        ),
        EvalQuestion(
            id="RPT-002", category="REPORT",
            question="quels sont les 3 meilleurs magasins par chiffre d'affaires ?",
            expected_keywords=["top", "magasin", "CA", "classement"],
            difficulty=2,
        ),
        EvalQuestion(
            id="RPT-003", category="REPORT",
            question="combien de questions y a-t-il dans le corpus de test ?",
            expected_keywords=["corpus", "question", "évaluation", "charge"],
            difficulty=1,
        ),
        EvalQuestion(
            id="RPT-004", category="REPORT",
            question="quelles sont les catégories de questions disponibles dans le corpus ?",
            expected_keywords=["EXPLORE", "DEBUG", "REFACTOR", "ARCH", "REPORT"],
            difficulty=1,
        ),
        EvalQuestion(
            id="RPT-005", category="REPORT",
            question="quels sont les seuils d'inactivité configurés dans le dashboard ?",
            expected_keywords=["60", "jours", "inactivité", "slider", "15", "180"],
            expected_files=["app.py", "AGENTS.md"],
            difficulty=1,
        ),
    ]


def _general_questions() -> list[EvalQuestion]:
    return [
        EvalQuestion(
            id="GEN-001", category="GENERAL",
            question="qu'est-ce que ce projet fait ?",
            expected_keywords=["pilotage", "B2B", "dashboard", "vente", "Streamlit"],
            difficulty=1,
        ),
        EvalQuestion(
            id="GEN-002", category="GENERAL",
            question="quel est le langage principal utilisé ?",
            expected_keywords=["Python", "3.12", "3.14"],
            difficulty=1,
        ),
        EvalQuestion(
            id="GEN-003", category="GENERAL",
            question="liste les dépendances principales du projet",
            expected_keywords=["Streamlit", "Pandas", "Plotly", "NumPy", "SQLite"],
            difficulty=1,
        ),
        EvalQuestion(
            id="GEN-004", category="GENERAL",
            question="donne la liste des 9 onglets du dashboard",
            expected_keywords=["onglet", "tab", "dashboard", "vue"],
            expected_files=["app.py"],
            difficulty=2,
        ),
        EvalQuestion(
            id="GEN-005", category="GENERAL",
            question="comment lancer le dashboard en local ?",
            expected_keywords=["streamlit", "run", "app.py", "terminal"],
            expected_files=["app.py"],
            difficulty=1,
        ),
        EvalQuestion(
            id="GEN-006", category="GENERAL",
            question="qu'est-ce que le ReasoningEvaluator mesure ?",
            expected_keywords=["exactitude", "pertinence", "token", "temps",
                               "fichiers", "score"],
            difficulty=2,
        ),
    ]


def load_corpus(category: str = "", sample: int = 0) -> list[EvalQuestion]:
    """Charge le corpus, filtré par catégorie et/ou limité."""
    all_q: list[EvalQuestion] = []
    all_q.extend(_explore_questions())
    all_q.extend(_debug_questions())
    all_q.extend(_refactor_questions())
    all_q.extend(_arch_questions())
    all_q.extend(_report_questions())
    all_q.extend(_general_questions())

    if category:
        all_q = [q for q in all_q if q.category.upper() == category.upper()]

    if sample and sample < len(all_q):
        # Prendre un échantillon équilibré si possible
        if category == "" and sample >= 6:
            # Au moins 1 par catégorie
            import random
            random.seed(42)
            cats = list(set(q.category for q in all_q))
            per_cat = max(1, sample // len(cats))
            sampled = []
            for c in cats:
                pool = [q for q in all_q if q.category == c]
                random.shuffle(pool)
                sampled.extend(pool[:per_cat])
            # Compléter si besoin
            remaining = [q for q in all_q if q not in sampled]
            random.shuffle(remaining)
            sampled.extend(remaining[:sample - len(sampled)])
            all_q = sampled
        else:
            import random
            random.seed(42)
            random.shuffle(all_q)
            all_q = all_q[:sample]

    return all_q


def list_categories() -> list[str]:
    """Liste les catégories disponibles dans le corpus."""
    return ["EXPLORE", "DEBUG", "REFACTOR", "ARCH", "REPORT", "GENERAL"]
