"""Per-tab scope analysis via symtable : exact external names for render(c).

Builds ``def render(c): <tab body>`` for each tabs[i] block, then asks
symtable which names ``render`` references without binding them locally.
Writes tests/_scopes_out.txt.
"""
import ast
import builtins
import io
import symtable

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
OUT = r"C:/Users/hachk/pilotage_b2b/tests/_scopes_out.txt"

src = io.open(APP, encoding="utf-8").read()
tree = ast.parse(src)

withs = {}
for n in tree.body:
    if isinstance(n, ast.With):
        e = n.items[0].context_expr
        if (isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name)
                and e.value.id == "tabs"):
            withs[e.slice.value] = n

imports = set()
top_defs = set()
top_assigns = set()
for n in tree.body:
    if isinstance(n, ast.Import):
        imports |= {(a.asname or a.name.split(".")[0]) for a in n.names}
    elif isinstance(n, ast.ImportFrom):
        imports |= {(a.asname or a.name) for a in n.names}
    elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        top_defs.add(n.name)
    elif isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name):
                top_assigns.add(t.id)
    elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
        top_assigns.add(n.target.id)

BUILTINS = set(dir(builtins))

lines = []
report = {}
for idx in sorted(withs):
    body_src = ast.unparse(ast.Module(body=withs[idx].body, type_ignores=[]))
    wrapped = "def render(c):\n" + "\n".join(
        ("    " + ln if ln.strip() else "") for ln in body_src.splitlines())
    table = symtable.symtable(wrapped, f"<tab{idx}>", "exec")
    render_tbl = next(t for t in table.get_children() if t.get_name() == "render")
    ext = set()
    local = set()
    for sym in render_tbl.get_symbols():
        if sym.is_parameter() or sym.is_assigned() or sym.is_imported():
            local.add(sym.get_name())
        else:
            ext.add(sym.get_name())
    ext -= BUILTINS
    report[idx] = {
        "ext": sorted(ext),
        "imports": sorted(ext & imports),
        "top_defs": sorted(ext & top_defs),
        "top_assigns": sorted(ext & top_assigns),
        "unknown": sorted(ext - imports - top_defs - top_assigns),
    }
    lines.append(f"TAB {idx}")
    lines.append(f"  imports     : {', '.join(report[idx]['imports'])}")
    lines.append(f"  top_defs    : {', '.join(report[idx]['top_defs'])}")
    lines.append(f"  top_assigns : {', '.join(report[idx]['top_assigns'])}")
    lines.append(f"  unknown     : {', '.join(report[idx]['unknown'])}")
    lines.append("")

io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("written", OUT)
for idx in sorted(report):
    u = report[idx]["unknown"]
    print(f"tab{idx}: unknown={len(u)} {u}")
