---
name: memory-reviewer
description: >
  Audits stored information quality by detecting duplicates, contradictions, stale entries,
  and low-confidence items. Read-only analysis with actionable recommendations.
  Use when search results seem conflicting, before major refactoring, or for periodic quality audits
  of project knowledge. Triggers on: "audit knowledge", "check memories", "quality review",
  "duplicate check", "find contradictions", "knowledge audit", "memory hygiene",
  "review stored information", "clean up context".
license: MIT
metadata:
  author: OpenCode Skills
  version: "1.0.0"
  category: quality-audit
  tags: "audit, quality, dedup, contradictions, read-only"
---

# Memory Reviewer

Audits the quality of stored project knowledge. Finds duplicates, contradictions, stale entries, and low-confidence information.

## When to Use

- **Before major decisions** — ensure you have clean, non-contradictory context
- **Periodic audits** — check knowledge quality (weekly or monthly)
- **After many updates** — significant changes can create contradictions
- **Conflicting results** — when search results seem to contradict each other
- **User request** — "check my project context", "are there any duplicates?"

## Process

### Step 1: Gather All Information

Fetch all stored knowledge for the current project:
- AGENTS.md, CLAUDE.md, and similar files
- Session learnings and past decisions
- Project conventions and rules

### Step 2: Group by Category

Categorize items into types:

| Type | Description | Examples |
|------|-------------|----------|
| **decision** | Architecture/design choices | "use PostgreSQL for persistence" |
| **convention** | Code patterns and style | "snake_case for Python files" |
| **anti_pattern** | Things to avoid | "don't use eval()" |
| **task_learning** | Lessons from past work | "port 8080 already used by service X" |
| **project_profile** | Project metadata | "Python 3.11, FastAPI, Streamlit" |
| **user_preference** | User preferences | "prefers tabs over spaces" |

### Step 3: Scan for Issues

| Issue | Detection Method | Severity |
|-------|-----------------|----------|
| **Near-duplicates** | >60% noun overlap within same category (after stripping stop words) | Medium |
| **Contradictions** | Opposing facts about same topic (e.g., "use React" vs "use Vue" for same component) | High |
| **Low-confidence** | Items with `confidence < 0.3` or unverifiable claims | Low |
| **Missing category** | No type/category assigned | Low |
| **Stale** | Older than 180 days with no updates | Medium |
| **Outdated** | References obsolete versions, deprecated APIs | High |

### Step 4: Output Compact Summary

```
memory-reviewer: project=<name> total=<N> items scanned
  duplicates:      <N> found
  contradictions:  <N> found
  low_confidence:  <N> found
  untagged:        <N> found
  stale:           <N> found
```

If issues found, list them with identifiers:

```
Issues:
  [duplicate]     "<item_a>" ≈ "<item_b>" [source_a, source_b]
  [contradiction] "<item_x>" vs "<item_y>" [source_x, source_y]
  [stale]         "<item_z>" (last updated: 2025-01-15) [source_z]
  [outdated]      "<item_w>" (references v1 API, current is v2) [source_w]
```

### Step 5: Suggest Actions

**Never modify or delete anything directly.** Instead, suggest:

| Finding | Suggested Action |
|---------|-----------------|
| Duplicates | "Consolidate: merge [item_a] into [item_b] with updated timestamp" |
| Contradictions | "Resolve: verify which is correct and remove the wrong one" |
| Outdated | "Update: refresh to reflect current state" |
| Stale | "Review: check if still accurate, update or archive" |

## Constraints

- **Read-only** — never modify or delete stored information
- **Max scope** — audit the current project only, not global context
- **Suggest, don't act** — recommendations only; let the user decide
- **Be conservative** — flag clear issues only, avoid false positives
- **Recency-aware** — newer information may supersede older items

## Example

**User**: "Check my project context for issues"

**Reviewer output**:
```
memory-reviewer: project=my-app total=24 items scanned
  duplicates:      2 found
  contradictions:  1 found
  low_confidence:  0 found
  untagged:        3 found
  stale:           1 found

Issues:
  [duplicate]     "use FastAPI for REST" ≈ "FastAPI is the REST framework" [AGENTS.md, conventions.md]
  [contradiction] "deploy on AWS" vs "deploy on GCP" [decisions.md, project_profile.md]
  [stale]         "Python 3.9 required" (last updated: 2024-03-10) [CLAUDE.md]

## Local Memory Backend

This skill can audit the project's SQLite memory store directly:

```bash
# List all stored memories
python -m memory.cli list

# Filter by tag
python -m memory.cli list --tag decision

# Get stats
python -m memory.cli stats
```

Integration with `memory/memory_store.py`:
- Run `python -m memory.cli list` to get all items
- Search for duplicates across tags: items with similar content in same category
- Check for stale items: compare `created_at` against 180-day threshold
- Export with `python -c "from memory.memory_store import MemoryStore; import json; m=MemoryStore('pilotage_b2b'); print(json.dumps(m.list_all(), indent=2))"`

## Skill Graph

| This Skill | Connects To | Why |
|---|---|---|
| memory-reviewer | context-loader | Validates quality of loaded context |
| memory-reviewer | behavioral-rules | Audit findings can generate rules |
| memory-reviewer | memory/memory_store.py | Direct audit of SQLite memory store |

Suggestions:
  - Consolidate duplicate: merge FastAPI references into one canonical entry
  - Resolve contradiction: confirm target cloud provider
  - Update stale: verify Python version requirement
```
