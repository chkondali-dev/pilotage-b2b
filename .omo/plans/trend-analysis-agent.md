# Plan: Agent Sentry — Détection de Régression / Analyse de Tendances

## TL;DR

> **Quick Summary**: Build a trend analysis & regression detection agent for pilotage_b2b (SMG MG & BATAM).
> Monitors sales data per store and per client, detects drops > 10% YoY, surfaces alerts in Streamlit.
>
> **Deliverables**:
> - trend_analyzer.py — Core analysis engine (Pandas)
> - trend_alert_panel.py — Streamlit alert panel component
> - Integration into app.py — New Tab 7 alerts panel
> - GitHub Actions workflow — Daily trend scan
> - LLM narrative (Groq) — Analysis of top regressions
>
> **Estimated Effort**: Medium (5-7 days)
> **Parallel Execution**: YES — 3 waves

---

## Context

### Original Request
The user wants an AI agent that detects the slightest regression or potential regression in trends across all sales data, per store and per client, with alerts in the Streamlit dashboard. No conversational BI, no data pipeline.

### Interview Summary
**Key Decisions**:
- **Architecture**: Pure Python analysis engine in-Streamlit + GitHub Actions scheduled scans. ADK/LangGraph later.
- **LLM**: Groq (Llama 3 70B) free tier, already configured.
- **Regression threshold**: Drop > 10% vs same month N-1 (year-over-year).
- **Alert delivery**: Streamlit dashboard panel only.
- **Timeline**: 1 week for functional MVP.
- **Test strategy**: Tests after implementation.
- **Stack**: Streamlit Cloud, GitHub, Pandas, Plotly, Groq API.

---

## Work Objectives

### Core Objective
Build automated trend regression detection monitoring every store and every client across B2B sales data, identifying drops > 10% YoY and early regression signals, with dashboard alerts.

### Concrete Deliverables
- trend_analyzer.py — Reusable analysis module (importable by Streamlit and CLI)
- trend_alert_panel.py — Streamlit UI component
- app.py — New Tab 7 Trend Alerts
- .github/workflows/trend-scan.yml — Daily scan
- data/trend_alerts.json — Shared alert state
- LLM narrative for top 5 regressions

### Must Have
- Per-magasin trends: MoM, YoY, 3m rolling avg, consecutive declines
- Per-convention trends: same metrics
- Regression flags: drop > 10% YoY = RED, 5-10% = AMBER, stable = GREEN
- Inactivity detection: no sales > 60 days
- Streamlit alert panel with filtering by magasin/enseigne/convention
- GitHub Actions daily scan updating trend_alerts.json

### Must NOT Have (Guardrails)
- NO conversational chat interface
- NO data pipeline / validation agent
- NO email/Slack/Teams notifications
- NO ADK/LangGraph orchestration (pure Python MVP)
- NO mempalace integration
- NO changes to data loading or monthly_report.py

---

## Verification Strategy

> ZERO HUMAN INTERVENTION — All verification is agent-executed.

### Test Decision
- **Infrastructure exists**: NO
- **Automated tests**: Tests-after (pytest post-MVP)
- **QA**: Agent-executed scenarios per task, evidence to .omo/evidence/

---

## Execution Strategy

### Parallel Execution Waves

`
Wave 1 (Foundation — 4 parallel tasks):
  1. trend_analyzer.py — Core engine (deep)
  2. Regression rules (deep)
  3. Alert model + JSON serialization (quick)
  4. Streamlit panel component (visual-engineering)

Wave 2 (Integration — depends on W1):
  5. Integrate into app.py Tab 7 (deep)
  6. LLM narrative module with Groq (unspecified-high)
  7. pytest + tests (quick)
  8. GitHub Actions workflow (quick)

Wave 3 (Polish):
  9. End-to-end QA (unspecified-high)

FINAL (4 parallel reviews):
  F1. Plan compliance audit (oracle)
  F2. Code quality review (unspecified-high)
  F3. Real manual QA (unspecified-high)
  F4. Scope fidelity check (deep)
`

---


## TODOs

- [ ] 1. **trend_analyzer.py -- Core Trend Computation Engine**

  **What to do**:
  Create trend_analyzer.py as a standalone reusable Python module.
  Class TrendAnalyzer with methods:
  - compute_magasin_trends(): MoM, YoY, 3m/6m rolling avg, consecutive decline months per magasin
  - compute_convention_trends(): same for each convention
  - detect_regressions(): RED if YoY drop > 10%, AMBER if 5-10%, GREEN otherwise
  - detect_inactivity(): flag entries with no sales in 60 days
  - scan_all(): full scan, returns JSON-serializable dict

  1. Reuse _add_date_cols and _map_magasins patterns from app.py
  2. Handle partial months, edge cases, type safety
  3. Support both VC and EDC data

  **Must NOT do**: Modify app.py, add deps beyond pandas/numpy

  **Acceptance Criteria**:
  - Module imports successfully
  - compute_magasin_trends() returns DataFrame with expected columns
  - detect_regressions() correct RED/AMBER/GREEN flags
  - detect_inactivity() finds entries inactive > N days
  - scan_all() returns JSON-serializable dict

  **QA Scenarios**:
  Scenario: Module import
    Tool: Bash | Steps: python -c "from trend_analyzer import TrendAnalyzer; print("OK")"
    Expected: OK | Evidence: .omo/evidence/task-1-import.txt
  Scenario: Computation
    Tool: Bash | Steps: Create test DataFrame, call compute_convention_trends()
    Expected: Returns DataFrame | Evidence: .omo/evidence/task-1-compute.txt

---

- [ ] 2. **Regression Detection & Alert Rules Engine**

  **What to do**:
  Build 6 rules:
  1. YoY Drop > 10% = RED
  2. YoY Drop 5-10% = AMBER
  3. Consecutive decline >= 3 months = RED
  4. Rolling avg drop < 80% of 3m avg = AMBER
  5. Inactivity > 60 days = RED
  6. Volume drop > 30% YoY = AMBER
  Each rule: {entity, metric, severity, current, previous, threshold, message_fr}

  **Acceptance Criteria**:
  - All 6 rules implemented
  - Messages in French, handles division by zero

  **QA Scenarios**:
  Scenario: All rules fire
    Tool: Bash | Steps: Run with data triggering all 6 rules
    Expected: 6 rule types in output | Evidence: .omo/evidence/task-2-rules.txt

---

- [ ] 3. **Alert Data Model + JSON Serializer**

  **What to do**:
  Schema: trend_alerts.json with generated_at, summary, magasin_alerts, convention_alerts, inactivity
  Implement save_alerts(path, data), load_alerts(path), generate_summary(data)

  **Acceptance Criteria**:
  - Save/load roundtrip identical
  - Summary correctly counts RED/AMBER
  - Empty data = valid JSON

  **QA Scenarios**:
  Scenario: Roundtrip
    Tool: Bash | Steps: Create alert dict, save, load, compare
    Expected: Original == loaded | Evidence: .omo/evidence/task-3-roundtrip.txt

---

- [ ] 4. **Streamlit Alert Panel Component**

  **What to do**:
  Create trend_alert_panel.py with:
  1. Summary bar: RED count / AMBER count / magasins under watch
  2. Tab switcher: Par Magasin | Par Convention | Inactivite
  3. Filter bar: by enseigne, by severity
  4. Alert cards: name, severity badge, metrics, message FR, 6-month sparkline
  5. Expandable detail
  6. Inactivity table
  Function: render_alert_panel(alerts: dict) -> None

  **Acceptance Criteria**:
  - Component imports successfully
  - 3 tabs present, filters work, cards with sparklines render

  **QA Scenarios**:
  Scenario: Import
    Tool: Bash | Steps: python -c "from trend_alert_panel import render_alert_panel; print("OK")"
    Expected: OK | Evidence: .omo/evidence/task-4-import.txt

---

- [ ] 5. **Integrate Alert Panel into app.py (Tab 7)**

  **What to do**:
  Add a new Tab 7 "Alertes Tendances" to the Streamlit dashboard.
  1. Add import: from trend_alert_panel import render_alert_panel
  2. Add import: from trend_analyzer import TrendAnalyzer
  3. After data loading, run TrendAnalyzer.scan_all() to generate alerts
  4. Cache the alert results with @st.cache_data
  5. Add new tab in tab navigation
  6. In the new tab: call render_alert_panel(alerts)
  7. Add manual refresh button

  **Must NOT do**: Break existing tabs, modify data loading pipeline

  **Acceptance Criteria**:
  - streamlit run app.py loads without errors
  - Tab 7 "Alertes Tendances" visible
  - Alert panel renders with data
  - Refresh button works
  - Existing tabs unchanged

  **QA Scenarios**:
  Scenario: Syntax check
    Tool: Bash | Steps: python -c "import ast; ast.parse(open("app.py").read()); print("syntax OK")"
    Expected: syntax OK | Evidence: .omo/evidence/task-5-syntax.txt

---

- [ ] 6. **LLM Narrative Module -- Groq-Powered Regression Analysis**

  **What to do**:
  Create trend_narrative.py using Groq API (pattern from monthly_report.py):
  1. Top 5 regressions: 2-3 sentence explanation in French each
  2. Summary paragraph: overall trend assessment
  3. Recommendations: 2-3 actionable items

  Reuse call_llm() pattern: same Groq endpoint, model, temperature
  Function: generate_regression_analysis(alerts_summary: dict) -> dict
  Response format JSON: synthese, regressions: [{nom, analyse, recommandation}], priorites

  **Acceptance Criteria**:
  - Imports without LLM dependency
  - With LLM_API_KEY: returns structured analysis
  - Without LLM_API_KEY: graceful fallback
  - Output in French, actionable, data-grounded

  **QA Scenarios**:
  Scenario: Import test
    Tool: Bash | Steps: python -c "from trend_narrative import generate_regression_analysis; print("OK")"
    Expected: OK | Evidence: .omo/evidence/task-6-import.txt

---

- [ ] 7. **Install pytest + Write Post-MVP Tests**

  **What to do**:
  1. pip install pytest
  2. Create test_trend_analyzer.py with tests for:
     - test_compute_magasin_trends: output shape and columns
     - test_compute_convention_trends: same
     - test_detect_regressions_red: > 10% drop flagged RED
     - test_detect_regressions_amber: 5-10% drop flagged AMBER
     - test_detect_regressions_green: stable flagged GREEN
     - test_detect_inactivity: inactive entries detected
     - test_scan_all: returns valid JSON structure
     - test_empty_data: graceful handling of empty DataFrames
  3. Create test_trend_alert_panel.py for UI component

  **Acceptance Criteria**:
  - pytest --tb=short -q test_trend_analyzer.py passes
  - All edge cases covered

  **QA Scenarios**:
  Scenario: Tests pass
    Tool: Bash | Steps: pytest --tb=short -q test_trend_analyzer.py
    Expected: all pass | Evidence: .omo/evidence/task-7-tests.txt

---

- [ ] 8. **GitHub Actions Daily Trend Scan Workflow**

  **What to do**:
  Create .github/workflows/trend-scan.yml:
  1. Runs daily 06:00 UTC (cron: "0 6 * * *")
  2. Manual trigger (workflow_dispatch)
  3. Steps: checkout, setup Python 3.11, install deps, run trend_analyzer.py --mode scan, optionally run trend_narrative.py, commit results
  4. Add CLI entry points: --mode scan, --mode report
  5. Error handling: don't fail if LLM unavailable

  **Must NOT do**: Deploy to server, modify source code, expose secrets

  **QA Scenarios**:
  Scenario: CLI mode
    Tool: Bash | Steps: python trend_analyzer.py --mode scan --output test_alerts.json
    Expected: valid JSON | Evidence: .omo/evidence/task-8-cli.txt
  Scenario: YAML valid
    Tool: Bash | Steps: python -c "import yaml; yaml.safe_load(open(".github/workflows/trend-scan.yml")); print("valid")"
    Expected: valid | Evidence: .omo/evidence/task-8-yaml.txt
---

## Final Verification Wave

> 4 review agents run in PARALLEL. ALL must APPROVE. Present to user, wait for explicit "okay" before completing.

- [ ] F1. **Plan Compliance Audit** -- oracle
  For each "Must Have": verify implementation exists. For each "Must NOT Have": search for forbidden patterns. Check evidence files exist.
  Output: Must Have [X/X] | Must NOT Have [X/X] | Tasks [X/X] | VERDICT: APPROVE/REJECT

- [ ] F2. **Code Quality Review** -- unspecified-high
  Syntax check + linter on new files. Check for: bare except, unused imports, AI slop.
  Output: Syntax [PASS/FAIL] | Lint [PASS/FAIL] | Files [N clean/N issues] | VERDICT

- [ ] F3. **Real Manual QA** -- unspecified-high
  Execute EVERY QA scenario from EVERY task. Test cross-task integration. Edge cases. Save to .omo/evidence/final-qa/.
  Output: Scenarios [N/N pass] | Integration [N/N] | VERDICT

- [ ] F4. **Scope Fidelity Check** -- deep
  Read each task + actual diff. Verify 1:1. Check "Must NOT do" compliance.
  Output: Tasks [N/N compliant] | Contamination [CLEAN/N issues] | VERDICT

---

## Commit Strategy

- **Wave 1** (tasks 1-4): feat(trend): add core trend analysis engine with regression detection and alert panel
  Files: trend_analyzer.py, trend_alert_panel.py
- **Wave 2** (tasks 5-8): feat(dashboard): integrate trend alerts Tab 7, LLM narrative, CI workflow
  Files: app.py, trend_narrative.py, .github/workflows/trend-scan.yml, test_trend_analyzer.py
- **Wave 3**: chore(qa): end-to-end verification and polish

---

## Success Criteria

### Verification Commands
```bash
python -c "from trend_analyzer import TrendAnalyzer; print('analysis OK')"
python -c "from trend_alert_panel import render_alert_panel; print('panel OK')"
python trend_analyzer.py --mode scan --output test_alerts.json
pytest --tb=short -q test_trend_analyzer.py
streamlit run app.py
```

### Final Checklist
- [ ] All 6 Must Have items verified present
- [ ] All 7 Must NOT Have items verified absent
- [ ] trend_alerts.json generates valid output
- [ ] Alert panel renders in Tab 7
- [ ] All 6 rules implemented and tested
- [ ] Inactivity detection works
- [ ] LLM narrative generates French analysis
- [ ] GitHub Actions workflow valid
- [ ] All QA evidence files in .omo/evidence/
- [ ] User explicitly approved after F1-F4 review
