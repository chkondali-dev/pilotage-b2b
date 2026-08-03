---
name: context-loader
description: >
  Pre-fetches relevant context before starting work on a task. Runs parallel searches
  across different angles (architecture decisions, conventions, anti-patterns, broad context),
  deduplicates results, and injects only the most relevant information.
  Supports auto-injection from local SQLite memory store with Ollama embeddings.
  Use when beginning a new task, switching context, or when project history, past decisions,
  or coding conventions need to be loaded. Triggers on: "load context", "what do we know about",
  "context for this task", "before we start", "relevant context", "past decisions",
  "history on this", "what's the background", "project conventions", "session start",
  "load memory".
license: MIT
metadata:
  author: OpenCode Skills
  version: "1.0.0"
  category: context-management
  tags: "context, search, dedup, parallel-queries, memory, embeddings, auto-inject"
---

# Context Loader

Pre-fetches relevant context from past work, decisions, and patterns before starting a task.

## When to Use

- **Session start** — Load context automatically when beginning work
- **Task switch** — User switches to a different feature or module
- **Complex task** — Multi-step task that needs historical context
- **Explicit request** — User asks "what do we know about X?" or "context for X"
- **Error troubleshooting** — Before debugging, load known anti-patterns

## Process

### Step 0: Auto-Inject Local Memory

Before any search, query the local SQLite memory store for relevant past context:

```bash
python memory/session_start.py "<current task description>"
```

This automatically:
- Loads project state summary from `~/.opencode_memory/pilotage_b2b.sqlite`
- Searches for semantically similar past decisions via Ollama embeddings
- Returns only items with similarity > 0.15 (silent if nothing relevant)

**No Ollama?** Falls back to keyword search automatically.

### Step 1: Extract Topics

From the current message/task, identify:
- **File paths** — files mentioned or related to the task
- **Module names** — feature areas, packages, components
- **Error patterns** — error messages, stack traces, bug symptoms
- **Technology keywords** — frameworks, libraries, patterns

### Step 2: Run Parallel Searches (2-4 queries)

Launch searches simultaneously with different angles:

| Query Angle | Focus | Purpose |
|-------------|-------|---------|
| **Feature/module** | Architecture decisions | Past design choices, why things are built this way |
| **File paths** | Conventions | Coding patterns, naming, structure |
| **Error keywords** | Anti-patterns | Known pitfalls, past bugs, solutions |
| **Broad context** | Catch-all | Any related information |

Search across available knowledge sources:
- AGENTS.md or CLAUDE.md files in the project
- Past session learnings (if accessible)
- Git history for relevant commits
- Project documentation

### Step 3: Deduplicate

Merge results from all parallel searches. Remove duplicates by content similarity:
- >60% overlap → consider duplicate, keep the most recent or most detailed
- Same source referenced multiple times → keep once

### Step 4: Output Compact Context Block

If relevant context was found (max 10 items):

```
context-loader: loaded <N> items for "<task summary>"
  - [decision] <content> [source]
  - [convention] <content> [source]
  - [anti_pattern] <content> [source]
```

**If zero results: output nothing.** Don't announce empty context — silence means "nothing relevant found."

## Constraints

- **Read-only** — never modify or delete existing content
- **Max 10 items** returned (most relevant only)
- **Silent on empty** — only surface findings if relevant context exists
- **Skip duplicates** — don't repeat what's already visible in current context
- **Recency matters** — prefer newer information when there's overlap

## Output Format

Compact, scannable, actionable:

```
context-loader: loaded 4 items for "adding user authentication"
  - [decision] Use JWT with refresh tokens (2026-03-15)
  - [convention] Service layer pattern: service/ → controller/ → route/
  - [anti_pattern] Don't store passwords in plaintext — use bcrypt
  - [broad] Auth module at src/auth/ with middleware pattern
```

## Example

**User**: "Let's add rate limiting to the API"

**Context loader**:
1. Extract topics: `rate limiting`, `API`, `middleware`
2. Parallel searches:
   - Feature: "rate limit architecture decisions"
   - Conventions: "API middleware patterns"
   - Anti-patterns: "rate limit issues"
 3. Deduplicate results
 4. Output:

```
context-loader: loaded 3 items for "adding rate limiting"
  - [decision] Use token bucket algorithm for API rate limiting
  - [convention] Middleware in src/middleware/ with Express-style next()
  - [anti_pattern] Don't use IP-based rate limiting behind reverse proxy
```

## Local Memory Backend

This skill integrates with the project's `memory/` module (SQLite + optional Ollama embeddings):

```python
from memory.injector import inject_context
context = inject_context("rate limiting API")
# Returns: <prior_context> items matching the query
```

- **Without Ollama**: keyword search (fuzzy match on stored content)
- **With Ollama**: semantic search via `all-minilm` embeddings — captures meaning, not just keywords
- **Storage**: `~/.opencode_memory/<namespace>.sqlite`
- **Auto-inject**: via `.opencode/hooks/memory-inject.sh`

### Manual Usage

```bash
# Store a decision
python -m memory.cli remember "Ne pas utiliser ORM" --tags decision,architecture

# Search context
python -m memory.cli inject "rate limiting"
```

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| context-loader | memory-reviewer | Verify loaded context quality |
| context-loader | feature-dev-workflow | Phase 2 exploration feeds context-loader |
| context-loader | memory/memory_store.py | Local SQLite + embeddings backend |
