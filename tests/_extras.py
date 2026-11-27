"""Compute external (non-local) Name IDs used by each tabs[i] block."""
import ast
import builtins
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"

src = io.open(APP, encoding="utf-8").read()
tree = ast.parse(src)

imports = set()
for n in tree.body:
    if isinstance(n, ast.Import):
        imports |= {a.name.split(".")[0] for a in n.names}
    elif isinstance(n, ast.ImportFrom):
        imports |= {a.name for a in n.names}
    elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        imports.add(n.name)

builtins = set(dir(builtins))

withs = [
    n
    for n in tree.body
    if isinstance(n, ast.With) and any(
        isinstance(i.context_expr, ast.Subscript)
        and isinstance(i.context_expr.value, ast.Name)
        and i.context_expr.value.id == "tabs"
        for i in n.items
    )
]
assert len(withs) == 10

for node in withs:
    idx = [
        i.context_expr.slice.value
        for i in node.items
        if isinstance(i.context_expr, ast.Subscript)
    ][0]
    loads = set()
    stores = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                loads.add(n.id)
            elif isinstance(n.ctx, ast.Store):
                stores.add(n.id)
    external = sorted(loads - stores - builtins - imports)
    print(f"TAB {idx}: {len(external)} externals")
    print("  ", ", ".join(external))
    print()
