# OpenCode — Architecture Contract

> **Status:** Contract — do not modify without explicit approval.
> This document defines the stable interfaces of OpenCode's reasoning system.
> Every component below has a single responsibility, a defined contract, and
> no knowledge of anything outside its scope.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [Project Brain](#2-project-brain)
3. [Retrieval Planner](#3-retrieval-planner)
4. [Brain Query](#4-brain-query)
5. [ReasoningDossier](#5-reasoningdossier)
6. [Compilation Passes](#6-compilation-passes)
7. [Renderers](#7-renderers)
8. [Pipeline](#8-pipeline)
9. [Appendix: Current Implementation](#9-appendix-current-implementation)

---

## 1. System Overview

OpenCode's reasoning system transforms a user query into a structured,
verifiable reasoning artifact through a sequential pipeline:

```
User Query
    │
    ▼
┌────────────────────────────────────────────────────────────┐
│  RETRIEVAL PLANNER        IntentPlanner                    │
│  "Vague question → plan de retrieval structuré"            │
└────────────────────┬───────────────────────────────────────┘
                     │ RetrievalPlan (steps, confidence)
                     ▼
┌────────────────────────────────────────────────────────────┐
│  BRAIN QUERY              ContextBuilder                   │
│  "Plan → Context Pack structuré (brut, sections)"          │
└────────────────────┬───────────────────────────────────────┘
                     │ Context Pack (plain text)
                     ▼
┌────────────────────────────────────────────────────────────┐
│  COMPILATION PIPELINE    compile_dossier()                 │
│                                                           │
│  Pass 1 — Normalizer    (extract.objective)               │
│  Pass 2 — Extraction    (extract.facts, .constraints,     │
│                           .artifacts, .actions)            │
│  Pass 3 — Inference     (infer.hypotheses, .signals)      │
│  Pass 4 — Validator     (validate.dossier)                │
│  Pass 5 — Optimizer     (future)                          │
└────────────────────┬───────────────────────────────────────┘
                     │ DossierDelta (each pass)
                     ▼
┌────────────────────────────────────────────────────────────┐
│  REASONINGDOSSIER        ReasoningDossier                  │
│  "IR — accumulateur de faits, contraintes, actions"        │
└────────────────────┬───────────────────────────────────────┘
                     │
                     ▼
┌────────────────────────────────────────────────────────────┐
│  RENDERERS               RendererPrompt / RendererJSON     │
│  "Dossier → str (prompt) ou dict (JSON)"                   │
└────────────────────────────────────────────────────────────┘
                     │
                     ▼
                LLM Prompt / API Call
```

**Design principles:**
- Each stage is a **pure transformation** — same input → same output.
- The ReasoningDossier is the **Intermediate Representation (IR)**.
- Compilation passes are **pluggable, ordered, and independently testable**.
- Renderers are **separated from the model** — the dossier has no render method.

---

## 2. Project Brain

### Role

Project Brain is the persistent knowledge layer. It stores two kinds of data
in a single SQLite database per namespace:

| Store | Purpose | Backend |
|-------|---------|---------|
| `MemoryStore` | Semantic memory (decisions, conventions, patterns) | SQLite + optional Ollama embeddings (384d) |
| `RelationsStore` | Structural relationships (calls, imports, inheritance) | SQLite |

### Contract: MemoryStore

```python
class MemoryStore:
    def __init__(self, namespace: str = "default")

    # Write
    def remember(self, content: str, tags: list[str] | None = None,
                 source: str = "", no_embed: bool = False) -> int
    def forget(self, memory_id: int) -> bool

    # Read
    def recall(self, query: str, top_k: int = 10,
               min_score: float = 0.0) -> list[dict]
    def list_all(self, tag_filter: str | None = None,
                 limit: int = 50) -> list[dict]

    # Utility
    def stats(self) -> dict
```

**Rules:**
- `remember` is idempotent — duplicate content updates `updated_at` + `access_count`.
- `recall` uses embedding vector search when Ollama is available; falls back to keyword search.
- Tags classify entries: `code:class`, `code:function`, `code:import`, `code:constant`, `code:module`, `session_end`, `brain:index`, `brain:git`, `project_meta`.

### Contract: RelationsStore

```python
class RelationsStore:
    def __init__(self, namespace: str = "default")

    # Write
    def add_call(self, source_file: str, source_function: str,
                 callee: str, line_number: int = 0)
    def add_import(self, source_file: str, module: str,
                   name: str, alias: str = "")
    def add_inherit(self, source_file: str, class_name: str,
                    base_class: str)
    def clear_file(self, file_path: str)

    # Read
    def find_callers(self, symbol: str, top_k: int = 20) -> list[dict]
    def find_callees(self, symbol: str, top_k: int = 20) -> list[dict]
    def find_imports(self, file_path: str) -> list[dict]
    def find_importers(self, module: str) -> list[str]
    def find_inheritors(self, class_name: str) -> list[dict]
    def get_called_by(self, symbol: str) -> list[tuple[str, str, int]]
    def get_calls(self, symbol: str) -> list[tuple[str, int, str]]
    def get_imports(self, module_name: str) -> list[tuple[str, str, str]]
    def module_deps(self, file_path: str) -> dict
    def symbol_deps(self, symbol: str) -> dict
    def stats(self) -> dict
```

### Data Flow

The **Code Indexer** (`code_indexer.py`) uses Tree-sitter to scan `.py` files and:
1. Extracts symbols (classes, functions, constants, imports) → stores in MemoryStore.
2. Extracts relationships → stores in RelationsStore (15 relation types supported):
   - `calls` — function A calls function B
   - `imports` — file imports module/symbol
   - `inherits` — class extends base class
   - `overrides` — method in subclass shadows parent method (potential heuristic)
   - `raises` — function raises an exception
   - `catches` — except clause catches an exception type
   - `decorator` — function/class decorated with @symbol
   - `route` — @app.get("/path") style route decorator
   - `test` — test_X function tests symbol X (convention-based)
   - `uses_type` — type annotation on parameter or return type
   - `implements` — class extends Protocol/ABC

The **Impact Analyzer** (`impact_analyzer.py`) traverses RelationsStore with BFS to
measure change impact:
- `forward_impact(symbol, depth=N)` — everything that depends on a symbol
- `backward_impact(symbol, depth=N)` — everything a symbol depends on
- `full_impact(symbol, depth=N)` — combined report
- `summarize(symbol)` — single-page role description

The **Injector** (`injector.py`) queries MemoryStore at session start to inject
relevant past context into the prompt.

---

## 3. Retrieval Planner

### Role

Translates a vague user question into a structured retrieval plan.
Each step in the plan is a concrete operation executable by the Context Builder.

### Implementation: IntentPlanner

```python
class IntentPlanner:
    def __init__(self, rules: list | None = None)
    def plan(self, query: str) -> RetrievalPlan
    def plan_debug(self, query: str) -> str
```

### Output: RetrievalPlan

```python
@dataclass
class RetrievalStep:
    tool: str       # find | calls | deps | module | query | symbol
    args: list[str] # arguments for the tool
    label: str      # human-readable description

@dataclass
class RetrievalPlan:
    query: str
    steps: list[RetrievalStep]
    confidence: float  # 0.0 → 1.0
```

### Rules

1. **Pattern matching** — rules map question patterns to tool sequences:
   - `"how does X work?"` → `[symbol, calls]`
   - `"where is X?"` → `[find]`
   - `"explain architecture"` → `[module, deps, calls]`
   - `"what calls X?"` → `[calls]`
   - fallback → `[query]` (semantic search)

2. **Symbol extraction** — heuristics to extract the target symbol:
   - File path (contains `/`)
   - Module path (contains `.`)
   - CamelCase word
   - snake_case word
   - Last non-stop-word token

3. **Confidence** — `0.9` for matched rules, `0.0` for fallback/no match.

4. **Boundary** — the planner does NOT execute any tool. It only produces a plan.

---

## 4. Brain Query

### Role

Executes a `RetrievalPlan` and assembles a **Context Pack** — a structured
plain-text document ready for consumption by the compilation pipeline.

### Implementation: ContextBuilder

```python
class ContextBuilder:
    def __init__(self, namespace: str = "default")
    def build(self, plan: RetrievalPlan) -> str
    def build_from_query(self, query: str) -> str  # shorthand: planner + builder
```

### Output: Context Pack

Format (plain text):

```
.-- Context Pack --------------------------------------------------
Query: <original query>
Steps: <tool descriptions>

  == <section label> ==
  <tool output>

  == <section label> ==
  <tool output>
'-----------------------------------------------------------------
```

### Available Tools

| Tool | Function | Description |
|------|----------|-------------|
| `symbol` | `_tool_symbol(symbol)` | Find class/function definition in MemoryStore |
| `find` | `_tool_find(query)` | Keyword search over all memories |
| `calls` | `_tool_calls(symbol)` | Call graph: who calls this symbol, what it calls |
| `deps` | `_tool_deps(module)` | Imports and importers of a module |
| `module` | `_tool_module(symbol)` | All indexed content for a module |
| `query` | `_tool_query(text)` | Semantic recall from MemoryStore |

### Rules

1. Each tool is a **pure function** of `(self, args) → str`.
2. The Context Pack is **plain text** — no structured data. This is by design:
   the Context Pack is the raw material that the compilation passes parse.
3. Empty sections are omitted.
4. The builder does NOT interpret the results — it collects and formats.

---

## 5. ReasoningDossier

### Role

The **Intermediate Representation (IR)** of OpenCode's reasoning.
A dossier accumulates facts, constraints, hypotheses, signals, actions, and
recommendations through sequential application of `DossierDelta`s.

**Key property:** The dossier has NO render method. Rendering is handled by
separate Renderer components. This is a deliberate architectural choice to
keep the IR pure and the output format flexible.

### Implementation: ReasoningDossier

```python
@dataclass
class ReasoningDossier:
    # Identity
    intent: IntentKind         # EXPLORE | DEBUG | REFACTOR | ARCH | REPORT | GENERAL
    objective: str

    # Core
    facts: list[Fact]          # verified statements, traceable to source
    constraints: list[Constraint]  # limits to respect (info/warning/error)
    actions: list[Action]      # steps with priority + dependencies

    # Investigation
    hypotheses: list[Hypothesis]  # debug/deep-dive leads
    signals: list[str]            # weak signals, suspicious patterns

    # Decision
    options: list[str]         # alternative approaches
    risks: list[str]           # known risks

    # Business
    metrics: dict              # KPIs, numerical results
    recommendations: list[dict]

    # Traceability
    source_context: str        # the original Context Pack
    passes_run: list[str]      # names of executed passes
    artifacts: list[str]       # files/modules referenced

    def apply(self, delta: DossierDelta) -> ReasoningDossier
```

### Supporting Types

```python
@dataclass
class Fact:
    text: str
    kind: FactKind       # STATEMENT | ARTIFACT | SIGNAL | METRIC
    confidence: float    # 0.0 → 1.0
    source: str | None   # "Context Pack :: calls('login')"
    symbol: str | None
    file: str | None
    line: int | None

@dataclass
class Constraint:
    text: str
    severity: str        # info | warning | error
    source: str | None

@dataclass
class Action:
    text: str
    priority: int        # 0 = highest
    depends_on: list[str]

@dataclass
class Hypothesis:
    text: str
    confidence: float    # 0.0 → 1.0
    triggered_by: str | None

@dataclass
class DossierDelta:
    facts: list[Fact]
    constraints: list[Constraint]
    actions: list[Action]
    hypotheses: list[Hypothesis]
    signals: list[str]
    options: list[str]
    risks: list[str]
    metrics: dict
    recommendations: list[dict]
    objective: str | None    # None = no override
    artifacts: list[str]
```

### Rules

1. `Fact.text` must never be empty — raises `ValueError` in `__post_init__`.
2. `Constraint.severity` is validated — only `info`, `warning`, `error`.
3. `apply()` merges deltas sequentially: lists are extended, dicts updated,
   objective is overridden if non-None.
4. Empty `DossierDelta.__bool__()` returns `False` — pipeline skips empty deltas.
5. The dossier is **mutable** by design — it accumulates state through the pipeline.

---

## 6. Compilation Passes

### Role

Compilation passes transform raw input (`query`, `plan`, `context_pack`)
into structured data inside the `ReasoningDossier`. Each pass is a pure
function `(query, plan, context_pack, intent, dossier) → DossierDelta`.

### Fact Quality Dimensions (v3)

Every `Fact` now carries three orthogonal quality dimensions set by `classify.facts`:

| Dimension | Range | Meaning |
|-----------|-------|---------|
| `importance` | 0.0–1.0 | Intrinsic value of the fact (security > metric > artifact) |
| `utility` | 0.0–1.0 | Relevance to the current user query |
| `confidence` | 0.0–1.0 | Reliability of the source (from extraction) |

Combined into a `category`:

| Score | Category | Behavior |
|-------|----------|----------|
| ≥ 0.75 | `critical` | Always preserved, highest budget priority |
| 0.55–0.74 | `important` | Preserved unless budget exceeded |
| 0.35–0.54 | `context` | Truncated first if budget tight |
| < 0.35 | `secondary` | Removed by `prune.facts` |

Each fact also receives semantic `tags` (e.g. `auth`, `security`, `call_chain`, `dependency`).

### Reasoning Optimizer Pipeline

New optimizer passes run between extraction and inference, in this exact order:

```
extract.facts (20)
    │
    ▼
classify.facts (43)     # tag each fact: importance, utility, category
    │
    ▼
chain.dedup (46)         # merge call chains: login→auth→jwt
    │
    ▼
prune.facts (47)         # remove noise, duplicates, low-utility
    │
    ▼
prioritize (48)          # token budget allocator
    │
    ▼
detect.missing (49)      # what don't we know?
    │
    ▼
infer.* / validate.*     # inference & validation
```

### Registry

Passes are registered globally via the `@register_pass` decorator:

```python
@dataclass
class PassDef:
    name: str
    description: str
    fn: PassFn                              # Callable[..., DossierDelta]
    requires: list[str]                     # dependencies by name
    priority: int                           # execution order (lower = earlier)

PassFn = Callable[[str, RetrievalPlan | None, str, IntentKind, ReasoningDossier], DossierDelta]
```

### Pass Catalog

| Priority | Name | Requires | Responsibility |
|----------|------|----------|----------------|
| 10 | `extract.objective` | — | Clean and normalize the user's objective from the query |
| 20 | `extract.facts` | `extract.objective` | Parse Context Pack into typed Facts with metadata |
| 30 | `extract.constraints` | `extract.facts` | Infer constraints from context: stack, files, tests |
| 35 | `extract.artifacts` | `extract.facts` | List files/modules referenced as artifacts |
| 40 | `extract.actions` | `extract.facts` | Convert retrieval plan into readable action items |
| 43 | `classify.facts` | `extract.facts` | Classify each fact: importance, utility, category, tags |
| 46 | `chain.dedup` | `classify.facts` | Merge call chains into sequences, reduce fact count |
| 47 | `prune.facts` | `chain.dedup` | Remove noise, duplicates, low-utility facts |
| 48 | `prioritize` | `prune.facts` | Token budget allocation by category, truncation |
| 49 | `detect.missing` | `classify.facts` | Identify knowledge gaps, reduce hasty conclusions |
| 50 | `optimize.sources` | `extract.facts` | Code path optimization, redundant imports, perf hints |
| 60 | `infer.hypotheses` | `extract.facts` | Generate debug hypotheses (only if intent=DEBUG) |
| 65 | `infer.signals` | `extract.facts` | Detect weak signals (timeout, incomplete code, deprecated API) |
| 80 | `validate.dossier` | `extract.objective`, `extract.facts` | Validate dossier integrity, raise on fatal errors |

### Intent Detection

```python
def detect_intent(query: str, plan=None, facts: list[Fact] | None = None) -> IntentKind
```

Rules (evaluated in order):
1. DEBUG keywords (`bug`, `error`, `fail`, `broken`, `crash`, …) → `DEBUG`
2. REFACTOR keywords (`refactor`, `amelior`, `simplif`, …) → `REFACTOR`
3. ARCH keywords (`architecture`, `design pattern`, `structure`, …) → `ARCH`
4. EXPLORE starters (`comment`, `how`, `what`, `where`, `explique`, …) → `EXPLORE`
5. Fallback → `GENERAL`

### Rules

1. Passes are **independent** — a pass must not call another pass.
2. Passes communicate exclusively through the `ReasoningDossier`.
3. Dependencies are resolved via topological sort (`_resolve_pass_order`).
4. A pass that raises `ValueError` halts the pipeline (fatal).
5. Any other exception from a pass is non-fatal — a warning constraint is added,
   and the pipeline continues.
6. New passes can be added by `@register_pass` — no other code changes needed.

---

## 7. Renderers

### Role

Transform a `ReasoningDossier` into an output format.
Renderers are **separate** from the dossier — the dossier has no `render()` method.

### Contract: RendererPrompt

```python
class RendererPrompt:
    def render(self, dossier: ReasoningDossier) -> str
```

Produces a structured text prompt:

```
=======================================================
INTENT  EXPLORE

OBJECTIF
  <objective>

FAITS
  <fact 1> [file.py]
  <fact 2>

CONTRAINTES
  [i] <info constraint>
  [!] <warning>

HYPOTHESES
  • <hypothesis> (70%)

SIGNAUX
  ~ <signal>

ACTIONS
  1. <action>

...
=======================================================
```

**Rules:**
- Sections with empty content are omitted entirely.
- Facts with a file reference append `[file.py]` as a tag.
- Constraint severity is mapped: `info` → `[i]`, `warning` → `[!]`, `error` → `[X]`.
- Hypothesis confidence is shown as percentage if different from default (50%).

### Contract: RendererJSON

```python
class RendererJSON:
    def render(self, dossier: ReasoningDossier) -> dict
```

Produces a JSON-serializable dict:

```json
{
  "intent": "explore",
  "objective": "Comprendre index_file",
  "facts": [
    {"text": "...", "kind": "artifact", "confidence": 1.0,
     "symbol": "index_file", "file": "code_indexer.py", "line": null}
  ],
  "constraints": [{"text": "Stack Python 3.14", "severity": "info"}],
  "hypotheses": [{"text": "...", "confidence": 0.7}],
  "signals": ["~ Gestion d'exceptions..."],
  "actions": [{"text": "Analyser...", "priority": 0}],
  "options": [],
  "risks": [],
  "metrics": {},
  "recommendations": [],
  "artifacts": ["code_indexer.py"]
}
```

### Rules

1. A renderer must not modify the dossier (read-only access).
2. A renderer must not raise — if rendering fails, it returns an empty string/`{}`.
3. A renderer must handle an empty dossier gracefully.
4. New renderers can be added without modifying existing code.

---

## 8. Pipeline

### Entry Points

```python
# Full pipeline (brain path)
def compile_dossier(
    query: str = "",
    plan: RetrievalPlan | None = None,
    context_pack: str = "",
    intent: IntentKind | None = None,
) -> ReasoningDossier

# Legacy facade (DossierBuilder)
class DossierBuilder:
    def build(self, query: str, plan=None, context_pack: str = "") -> ReasoningDossier
    def build_report(self, objective: str = "", facts=None,
                     constraints=None, actions=None) -> ReasoningDossier
```

### Execution

1. `detect_intent(query, plan)` determines the `IntentKind` (if not provided).
2. `ReasoningDossier(intent, source_context=context_pack)` is created.
3. Passes are resolved in topological order via `_resolve_pass_order()`.
4. Each pass executes: `delta = pass.fn(query, plan, context_pack, intent, dossier)`.
5. If delta is non-empty: `dossier.apply(delta)`.
6. Pass name is appended to `dossier.passes_run`.
7. Fatal errors (`ValueError`) propagate up; non-fatal exceptions add a warning
   constraint and continue.
8. The completed dossier is returned.

### Full CLI Flow

```bash
python -m memory.cli brain context "comment fonctionne index_file ?"
```

This executes:
1. `IntentPlanner.plan(query)` → `RetrievalPlan`
2. `ContextBuilder.build(plan)` → `Context Pack`
3. `compile_dossier(query, plan, context_pack)` → `ReasoningDossier`
4. `RendererPrompt.render(dossier)` → output

---

## 9. Appendix: Current Implementation

### Module Map

```
memory/
├── __init__.py              # Exports: MemoryStore, inject_context, ...
├── AGENTS.md                # Knowledge-base entry for this module
├── memory_store.py          # Project Brain — MemoryStore (SQLite + embeddings)
├── relations.py             # Project Brain — RelationsStore (call graph)
├── code_indexer.py          # Project Brain — Code Indexer (Tree-sitter v3)
├── impact_analyzer.py       # Project Brain — Impact Analyzer (BFS)
├── intent_planner.py        # Retrieval Planner — IntentPlanner
├── context_builder.py       # Brain Query — ContextBuilder
├── dossier_builder.py       # [Compat] Re-exports memory.compiler
├── injector.py              # Session injection hook
├── session_start.py         # Session entry point
├── cli.py                   # CLI frontend for all brain commands
├── evaluator/               # Benchmark — ReasoningEvaluator
│   ├── __init__.py          #   Public API
│   ├── corpus.py            #   53 questions typees
│   ├── metrics.py           #   Scoring: exactitude, pertinence, temps, fichiers
│   ├── runner.py            #   Orchestrateur dry-run / pipeline reel
│   └── report.py            #   Scoreboard par categorie + global
├── compiler/                # Reasoning Compiler (modulaire)
│   ├── __init__.py          #   Public API (re-exporte tout)
│   ├── types.py             #   Core types: Fact, Constraint, Action, ...
│   ├── detect.py            #   Intent detection + helpers
│   ├── pipeline.py          #   resolve_pass_order + compile_dossier
│   ├── renderers.py         #   RendererPrompt / RendererJSON
│   └── passes/              #   8 passes, 1 fichier par passe
│       ├── __init__.py      #   Autodiscover
│       ├── extract_objective.py
│       ├── extract_facts.py
│       ├── extract_constraints.py
│       ├── extract_artifacts.py
│       ├── extract_actions.py
│       ├── classify_facts.py
│       ├── chain_dedup.py
│       ├── prune_facts.py
│       ├── prioritize.py
│       ├── detect_missing.py
│       ├── optimize_sources.py
│       ├── infer_hypotheses.py
│       ├── infer_signals.py
│       └── validate.py
```

### Dependencies

- **Python 3.12+**
- **SQLite3** (stdlib) — persistent storage
- **Tree-sitter** — AST parsing for code indexing
- **tree-sitter-python** — Python grammar
- **NumPy** — vector operations for cosine similarity
- **Ollama** (optional) — embedding generation

### Key Files Outside `memory/`

| File | Purpose |
|------|---------|
| `.opencode/hooks/memory-inject.sh` | Session start hook — injects memory context |
| `.opencode/AGENTS.md` | Project-level knowledge base |
| `opencode.json` | OpenCode configuration (model, provider, plugins) |
| `superpowers/` | Plugin system extending OpenCode capabilities |

### Pass Catalog (Complete)

| Priority | Name | Requires | Responsibility |
|----------|------|----------|----------------|
| 10 | `extract.objective` | — | Clean and normalize the user's objective from the query |
| 20 | `extract.facts` | `extract.objective` | Parse Context Pack into typed Facts with metadata |
| 30 | `extract.constraints` | `extract.facts` | Infer constraints from context: stack, files, tests |
| 35 | `extract.artifacts` | `extract.facts` | List files/modules referenced as artifacts |
| 40 | `extract.actions` | `extract.facts` | Convert retrieval plan into readable action items |
| 43 | `classify.facts` | `extract.facts` | Classify each fact: importance, utility, category, tags |
| 46 | `chain.dedup` | `classify.facts` | Merge call chains into sequences, reduce fact count |
| 47 | `prune.facts` | `chain.dedup` | Remove noise, duplicates, low-utility facts |
| 48 | `prioritize` | `prune.facts` | Token budget allocation by category, truncation |
| 49 | `detect.missing` | `classify.facts` | Identify knowledge gaps, reduce hasty conclusions |
| 50 | `optimize.sources` | `extract.facts` | Code path optimization, redundant imports, perf hints |
| 60 | `infer.hypotheses` | `extract.facts` | Generate debug hypotheses (only if intent=DEBUG) |
| 65 | `infer.signals` | `extract.facts` | Detect weak signals (timeout, incomplete code, deprecated API) |
| 80 | `validate.dossier` | `extract.objective`, `extract.facts` | Validate dossier integrity, raise on fatal errors |

### Future Passes (Reserved)

| Priority | Name | Status |
|----------|------|--------|
| 70 | `infer.impact` | Implemented as `ImpactAnalyzer` (standalone, not yet a compiler pass) |
| 85 | `assemble.summary` | Not implemented — executive summary |

---

*This document is the architecture contract. No component interface described
here may be modified without explicit approval. Additions (new passes, new
renderers, new tools) are always welcome — modifications to existing contracts
require review.*
