"""Refactor app.py (Phase 2) : retire les 10 blocs ``with tabs[i]:`` et les
remplace par un selecteur + dispatch vers ui/tabs/<mod>.render(TabCtx).

Anchors found with AST (no hardcoded line numbers):
  * last top-level import  -> insert the ui.tabs imports after it
  * ``tabs = st.tabs([...])`` assign -> start of the replaced region
  * last ``with tabs[9]:``          -> end of the replaced region

Line endings of app.py (CRLF) are preserved.
"""
import ast
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
CONTEXT = r"C:/Users/hachk/pilotage_b2b/ui/tabs/context.py"
EOL = "\r\n"

TAB_MODULES = [
    "tab0_executive",
    "tab1_tendances",
    "tab2_conventions",
    "tab3_magasins",
    "tab4_lens",
    "tab5_conventions",
    "tab6_crm",
    "tab7_alertes",
    "tab8_archive",
    "tab9_conformite",
]

# TabCtx fields whose python expression differs from the field name itself.
SPECIAL = {
    "lens_labels": "LENS_LABELS",
    "base_dir": "str(Path(__file__).parent)",
}

src = io.open(APP, encoding="utf-8", newline="").read()
tree = ast.parse(src)
lines = src.splitlines(keepends=True)

# ------------------------------------------------------------------ anchors
last_import = 0
tabs_assign_node = None
last_with = 0
for node in tree.body:
    if isinstance(node, (ast.Import, ast.ImportFrom)):
        last_import = max(last_import, node.end_lineno)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and t.id == "tabs":
                tabs_assign_node = node
    elif isinstance(node, ast.With):
        e = node.items[0].context_expr
        if (isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name)
                and e.value.id == "tabs"):
            last_with = max(last_with, node.end_lineno)

assert tabs_assign_node is not None, "tabs = st.tabs(...) not found"
tabs_start = tabs_assign_node.lineno
assert last_with > tabs_start, (last_with, tabs_start)

# original labels, read back from the st.tabs([...]) literal
labels = [
    e.value for e in tabs_assign_node.value.args[0].elts
]
assert len(labels) == 10, len(labels)

# ------------------------------------------------------------------ context
ctx_tree = ast.parse(io.open(CONTEXT, encoding="utf-8", newline="").read())
FIELDS = []
for n in ctx_tree.body:
    if isinstance(n, ast.ClassDef) and n.name == "TabCtx":
        for item in n.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                FIELDS.append(item.target.id)

# ------------------------------------------------------------------ blocks
import_lines = [
    "",
    "from ui.tabs.context import TabCtx",
]
for i, mod in enumerate(TAB_MODULES):
    import_lines.append("from ui.tabs.%s import render as _render_tab%d" % (mod, i))
import_lines += [
    "",
    "import re",
    "import unicodedata",
    "",
]

dispatch = []
dispatch.append("# " + "=" * 63)
dispatch.append("# SECTION 8 - NAVIGATION (onglets extraits vers ui/tabs/)")
dispatch.append("# " + "=" * 63)
dispatch.append("# Chaque onglet est un module ui/tabs/<nom>.py exposant")
dispatch.append("# render(ctx: TabCtx). Seul l'onglet selectionne est rendu")
dispatch.append("# (rendu paresseux, Phase 2 : moins de calcul par rerun).")
dispatch.append("_TAB_ITEMS = [")
for i, lbl in enumerate(labels):
    dispatch.append("    (%r, _render_tab%d)," % (lbl, i))
dispatch.append("]")
dispatch.append("_TAB_LABELS = [lbl for lbl, _ in _TAB_ITEMS]")
dispatch.append("")
dispatch.append("")
dispatch.append("def _norm_label(value):")
dispatch.append('    """Libelle d\'onglet normalise : sans emoji, sans accent."""')
dispatch.append("    text = unicodedata.normalize('NFKD', str(value))")
dispatch.append("    text = ''.join(ch for ch in text if not unicodedata.combining(ch))")
dispatch.append("    return re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()")
dispatch.append("")
dispatch.append("")
dispatch.append("_TAB_INDEX = {_norm_label(lbl): i for i, (lbl, _) in enumerate(_TAB_ITEMS)}")
dispatch.append("")
dispatch.append("_tab_sel = st.segmented_control(")
dispatch.append("    'Navigation',")
dispatch.append("    _TAB_LABELS,")
dispatch.append("    default=_TAB_LABELS[0],")
dispatch.append("    label_visibility='collapsed',")
dispatch.append(")")
dispatch.append("_tab_idx = _TAB_INDEX.get(_norm_label(_tab_sel), 0) if _tab_sel else 0")
dispatch.append("")
dispatch.append("_tab_ctx = TabCtx(")
for f in FIELDS:
    dispatch.append("    %s=%s," % (f, SPECIAL.get(f, f)))
dispatch.append(")")
dispatch.append("_TAB_ITEMS[_tab_idx][1](_tab_ctx)")
dispatch.append("")

dispatch_lines = [ln + EOL for ln in dispatch]
import_block_lines = [ln + EOL for ln in import_lines]

new_lines = (
    lines[:last_import]
    + import_block_lines
    + lines[last_import:tabs_start - 1]
    + dispatch_lines
    + lines[last_with:]
)

out = "".join(new_lines)
io.open(APP, "w", encoding="utf-8", newline="").write(out)

print("last_import   :", last_import)
print("tabs_start    :", tabs_start)
print("last_with     :", last_with)
print("labels        :", len(labels))
print("fields        :", len(FIELDS))
print("old lines     :", len(lines))
print("new lines     :", len(new_lines))
