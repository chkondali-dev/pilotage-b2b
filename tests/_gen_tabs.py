"""Final Phase-2 generator.

Turns each ``with tabs[i]:`` block of app.py into ``ui/tabs/<mod>.py`` exposing
``render(ctx: TabCtx) -> None``.

Design (validated by the AST/symtable analysis in tests/):
  * ``ctx`` is the parameter name (NOT ``c``) because several tabs already use
    a comprehension variable named ``c``.
  * Every TabCtx field referenced in a tab is rewritten ``name -> ctx.name``.
    Exception: names rebound at render level in that tab (tab5 ``df_filt``,
    tab7 ``ca_n``/``ca_n1``) are seeded at the top of render with
    ``name = ctx.name`` and stay locals - this reproduces the original
    module-global-then-overwrite semantics on every control-flow path.
  * Module-level helpers used by a tab are inlined: cached ones at module
    scope (keeps @st.cache_data identity), the rest nested inside render so
    their ``ctx``-free references resolve.
  * ``Path(__file__).parent`` -> ``Path(ctx.base_dir)`` and
    ``os.path.dirname(__file__)`` -> ``ctx.base_dir``.
  * Import headers are derived from symtable on the assembled module.
"""
import ast
import builtins
import io
import symtable

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
TABS_DIR = r"C:/Users/hachk/pilotage_b2b/ui/tabs"
CONTEXT = r"C:/Users/hachk/pilotage_b2b/ui/tabs/context.py"

CTX_PARAM = "ctx"

TAB_MODULES = {
    0: "tab0_executive",
    1: "tab1_tendances",
    2: "tab2_conventions",
    3: "tab3_magasins",
    4: "tab4_lens",
    5: "tab5_conventions",
    6: "tab6_crm",
    7: "tab7_alertes",
    8: "tab8_archive",
    9: "tab9_conformite",
}

# TabCtx fields REBOUND at render level inside a given tab -> seeded as locals.
PREPEND = {
    5: ["df_filt"],
    7: ["ca_n", "ca_n1"],
}

# Cross-tab locals (bound inside tab0, read inside another tab). Recomputed in
# the consumer from the same context data => same values, no shared global.
SEED_EXPR = {
    1: [
        "_vol0 = volumes_panier(df_vc_filt, annee_sel, mois_sel)",
        'mois_label = ", ".join([MOIS.get(m, str(m)) for m in mois_sel]) '
        'if mois_sel else f"{annee_sel}"',
    ],
}

# Non-field names that map onto a TabCtx field.
FIELD_ALIAS = {
    "LENS_LABELS": "lens_labels",
}

BUILTINS = set(dir(builtins))

IMPORT_LINES = {
    "st": "import streamlit as st",
    "pd": "import pandas as pd",
    "np": "import numpy as np",
    "px": "import plotly.express as px",
    "go": "import plotly.graph_objects as go",
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "os": "import os",
    "json": "import json",
    "BytesIO": "from io import BytesIO",
    "Path": "from pathlib import Path",
    "logging": "import logging",
    "C": "from data.config import C",
    "MOIS": "from data.config import MOIS",
    "SEUILS": "from data.config import SEUILS",
    "STATUTS_CONVENTION": "from data.config import STATUTS_CONVENTION",
    "JALONS_STATUTS": "from data.config import JALONS_STATUTS",
    "PROSP_ETAPES": "from data.transforms import PROSP_ETAPES",
    "ajoute_crm": "from data.transforms import ajoute_crm",
    "enrich_prospection": "from data.transforms import enrich_prospection",
    "bridge_volume_panier": "from metrics.kpi import bridge_volume_panier",
    "business_insights": "from metrics.kpi import business_insights",
    "ca_sum_date_to_date": "from metrics.kpi import ca_sum_date_to_date",
    "cohortes_conventions": "from metrics.kpi import cohortes_conventions",
    "color_delta": "from metrics.kpi import color_delta",
    "compare_years_date_to_date": "from metrics.kpi import compare_years_date_to_date",
    "concentration_portefeuille": "from metrics.kpi import concentration_portefeuille",
    "conversion_conventions": "from metrics.kpi import conversion_conventions",
    "evol_pct": "from metrics.kpi import evol_pct",
    "fmt_pct": "from metrics.kpi import fmt_pct",
    "kpi_conversion_globale": "from metrics.kpi import kpi_conversion_globale",
    "narratif_executif": "from metrics.kpi import narratif_executif",
    "objectif_tracking": "from metrics.kpi import objectif_tracking",
    "run_rate_fin_annee": "from metrics.kpi import run_rate_fin_annee",
    "truncate_n1_date_to_date": "from metrics.kpi import truncate_n1_date_to_date",
    "ventes_positives": "from metrics.kpi import ventes_positives",
    "volumes_panier": "from metrics.kpi import volumes_panier",
    "alertes_achats_repetes": "from metrics.kpi import alertes_achats_repetes",
    "chart_bar": "from charts.factory import chart_bar",
    "chart_bridge": "from charts.factory import chart_bridge",
    "chart_gauge": "from charts.factory import chart_gauge",
    "chart_grouped_bar": "from charts.factory import chart_grouped_bar",
    "chart_line_compare": "from charts.factory import chart_line_compare",
    "chart_pie": "from charts.factory import chart_pie",
    "chart_risk_table": "from charts.factory import chart_risk_table",
    "chart_stacked_bar": "from charts.factory import chart_stacked_bar",
    "chart_variation_bar": "from charts.factory import chart_variation_bar",
    "section": "from ui.components import section",
    "badge": "from ui.components import badge",
    "rank_card": "from ui.components import rank_card",
    "kpi_card": "from ui.components import kpi_card",
    "conv": "import business.conventions as conv",
    "file_sha": "from utils.github import file_sha",
    "push_csv_to_github": "from utils.github import push_csv_to_github",
    "render_alert_panel": "from trend_alert_panel import render_alert_panel",
}


MODULE_LEVEL_DEFS = {"_cached_scan_all"}


# ----------------------------------------------------------------- parsing
src = io.open(APP, encoding="utf-8").read()
tree = ast.parse(src)

ctx_tree = ast.parse(io.open(CONTEXT, encoding="utf-8").read())
FIELDS = []
for _n in ctx_tree.body:
    if isinstance(_n, ast.ClassDef) and _n.name == "TabCtx":
        for _item in _n.body:
            if isinstance(_item, ast.AnnAssign) and isinstance(_item.target, ast.Name):
                FIELDS.append(_item.target.id)
FIELD_SET = set(FIELDS)

withs = {}
for _n in tree.body:
    if isinstance(_n, ast.With):
        _e = _n.items[0].context_expr
        if (isinstance(_e, ast.Subscript) and isinstance(_e.value, ast.Name)
                and _e.value.id == "tabs"):
            withs[_e.slice.value] = _n
assert sorted(withs) == list(range(10)), sorted(withs)

top_defs = {}
top_assigns = {}
imports = set()
for _n in tree.body:
    if isinstance(_n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        top_defs[_n.name] = _n
    elif isinstance(_n, ast.Assign):
        for _t in _n.targets:
            if isinstance(_t, ast.Name):
                top_assigns[_t.id] = _n
    elif isinstance(_n, ast.AnnAssign) and isinstance(_n.target, ast.Name):
        top_assigns[_n.target.id] = _n
    elif isinstance(_n, ast.Import):
        imports |= {(a.asname or a.name.split(".")[0]) for a in _n.names}
    elif isinstance(_n, ast.ImportFrom):
        imports |= {(a.asname or a.name) for a in _n.names}


def unparse(node):
    return ast.unparse(node)


class Fresh(ast.NodeTransformer):
    """Deep-copies and lets us rewrite Names safely."""

    def visit(self, node):
        return super().visit(node)



# ----------------------------------------------------------------- helpers
def loads_of(stmts):
    out = set()
    for s in stmts:
        for n in ast.walk(s):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                out.add(n.id)
    return out


def rename_stmts(stmts, rename_map):
    mod = ast.Module(body=list(stmts), type_ignores=[])

    class R(ast.NodeTransformer):
        def visit_Name(self, node):
            if isinstance(node.ctx, ast.Load) and node.id in rename_map:
                new = ast.parse(rename_map[node.id], mode="eval").body
                return ast.copy_location(new, node)
            return node

    out = R().visit(mod)
    ast.fix_missing_locations(out)
    return out.body


def fix_file(text):
    text = text.replace("Path(__file__).parent", "Path(%s.base_dir)" % CTX_PARAM)
    text = text.replace("os.path.dirname(__file__)", "%s.base_dir" % CTX_PARAM)
    return text


def needed_imports(module_src):
    table = symtable.symtable(module_src, "<m>", "exec")
    module_defined = {
        s.get_name() for s in table.get_symbols()
        if s.is_assigned() or s.is_imported() or s.is_parameter()
    }
    needed = set()

    def walk(t, depth):
        for s in t.get_symbols():
            if not s.is_referenced():
                continue
            if s.is_parameter():
                continue
            if s.is_assigned() or s.is_imported():
                continue
            if depth == 0:
                needed.add(s.get_name())
            elif not s.is_free():
                needed.add(s.get_name())
        for c in t.get_children():
            walk(c, depth + 1)

    walk(table, 0)
    needed -= BUILTINS
    needed -= module_defined
    return needed


def indent(text, pad="    "):
    return "\n".join((pad + ln) if ln.strip() else "" for ln in text.splitlines())



# ----------------------------------------------------------------- build
import copy
import os
import py_compile

REPORT = {}
ERRORS = []

for idx in sorted(withs):
    body = copy.deepcopy(withs[idx].body)
    seeds = list(PREPEND.get(idx, []))
    seed_nodes = [
        ast.parse("%s = %s.%s" % (n, CTX_PARAM, n)).body[0] for n in seeds
    ]
    for _expr in SEED_EXPR.get(idx, []):
        seed_nodes.append(ast.parse(_expr).body[0])

    used_defs = [n for n in top_defs if n in loads_of(body)]
    used_assigns = [n for n in top_assigns if n in loads_of(body)]

    module_def_names = [n for n in used_defs if n in MODULE_LEVEL_DEFS]
    nest_def_names = [n for n in used_defs if n not in MODULE_LEVEL_DEFS]
    const_names = [
        n for n in used_assigns
        if n not in FIELD_SET and n not in FIELD_ALIAS
    ]

    module_defs = copy.deepcopy([top_defs[n] for n in module_def_names])
    nested_defs = copy.deepcopy([top_defs[n] for n in nest_def_names])
    module_consts = copy.deepcopy([top_assigns[n] for n in const_names])

    all_loads = (
        loads_of(body) | loads_of(nested_defs) | loads_of(module_defs)
        | loads_of(seed_nodes)
    )

    rename_map = {}
    for f in FIELDS:
        if f in all_loads and f not in seeds:
            rename_map[f] = "%s.%s" % (CTX_PARAM, f)
    for alias, field in FIELD_ALIAS.items():
        if alias in all_loads:
            rename_map[alias] = "%s.%s" % (CTX_PARAM, field)

    # safety: no inlined def may bind a TabCtx field locally
    for d in nested_defs + module_defs:
        bound = {a.arg for a in ast.walk(d) if isinstance(a, ast.arg)}
        clash = bound & FIELD_SET
        if clash:
            ERRORS.append("tab%d: inlined def %s binds fields %s"
                          % (idx, getattr(d, "name", "?"), sorted(clash)))

    # module-level defs must not need ctx (ctx is not in scope there)
    for d in module_defs:
        dloads = loads_of([d])
        clash = dloads & FIELD_SET
        if clash:
            ERRORS.append("tab%d: module-level def %s references fields %s"
                          % (idx, d.name, sorted(clash)))

    body = rename_stmts(body, rename_map)
    nested_defs = rename_stmts(nested_defs, rename_map)
    module_defs = rename_stmts(module_defs, rename_map)
    seed_nodes = rename_stmts(seed_nodes, rename_map)

    render_body = seed_nodes + nested_defs + body
    render_text = ast.unparse(ast.Module(body=render_body, type_ignores=[]))
    render_fn = "def render(%s):\n%s" % (CTX_PARAM, indent(render_text))

    top_nodes = module_consts + module_defs
    if top_nodes:
        top_text = ast.unparse(ast.Module(body=top_nodes, type_ignores=[]))
        core = top_text + "\n\n\n" + render_fn
    else:
        core = render_fn

    core = fix_file(core)

    needs = needed_imports(core)
    missing = sorted(n for n in needs if n not in IMPORT_LINES)
    if missing:
        ERRORS.append("tab%d: no import mapping for %s" % (idx, missing))
    import_text = "\n".join(
        IMPORT_LINES[n] for n in sorted(needs) if n in IMPORT_LINES
    )
    final = (import_text + "\n\n\n" + core) if import_text else core

    path = os.path.join(TABS_DIR, TAB_MODULES[idx] + ".py")
    io.open(path, "w", encoding="utf-8", newline="\r\n").write(final)
    REPORT[idx] = {
        "path": path,
        "needs": sorted(needs),
        "seeds": seeds,
        "consts": const_names,
        "module_defs": module_def_names,
        "nested_defs": nest_def_names,
        "rename": sorted(rename_map),
    }

# ----------------------------------------------------------------- verify
for idx in sorted(REPORT):
    p = REPORT[idx]["path"]
    try:
        py_compile.compile(p, doraise=True)
        REPORT[idx]["compile"] = "OK"
    except Exception as exc:
        REPORT[idx]["compile"] = "FAIL: %s" % exc
        ERRORS.append("tab%d compile: %s" % (idx, exc))

print("=== TabCtx fields (%d) ===" % len(FIELDS))
print(", ".join(FIELDS))
for idx in sorted(REPORT):
    r = REPORT[idx]
    print("\nTAB %d -> %s" % (idx, os.path.basename(r["path"])))
    print("  compile   : %s" % r["compile"])
    print("  seeds     : %s" % r["seeds"])
    print("  consts    : %s" % r["consts"])
    print("  mod_defs  : %s" % r["module_defs"])
    print("  nest_defs : %s" % r["nested_defs"])
    print("  imports   : %s" % r["needs"])

print("\n=== union of TabCtx fields required ===")
union = set()
for idx in REPORT:
    for n in REPORT[idx]["rename"]:
        if n in FIELD_SET:
            union.add(n)
print(", ".join(sorted(union)))

if ERRORS:
    print("\n=== ERRORS ===")
    for e in ERRORS:
        print(" -", e)
    raise SystemExit(1)
print("\nALL OK")
