"""Inventory of module-level definitions and which tabs use them.

Writes tests/_tb_inv.txt for reviewing, then is importable as a helper.
"""
import ast
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
OUT = r"C:/Users/hachk/pilotage_b2b/tests/_tb_inv.txt"


def iter_body(body):
    for n in body:
        yield n


tree = ast.parse(io.open(APP, encoding="utf-8").read())

top_withs = []
for n in tree.body:
    if isinstance(n, ast.With):
        items = [
            i.context_expr.slice.value
            for i in n.items
            if isinstance(i.context_expr, ast.Subscript)
        ]
        if items and items[0] is not None:
            top_withs.append((n.lineno, items[0], n.end_lineno))

# module-level defs/calls/classes (excluding the with blocks)
top_defs = []
for n in tree.body:
    if isinstance(n, ast.With):
        continue
    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        top_defs.append((n.lineno, n.end_lineno, n.name))
    elif isinstance(n, ast.Assign):
        # module-level constants (e.g. LENS_LABELS, REGISTRY_CSV_REL)
        for t in n.targets:
            if isinstance(t, ast.Name):
                top_defs.append((n.lineno, n.end_lineno, t.id + " = (module-level)"))
    elif isinstance(n, ast.AnnAssign):
        top_defs.append((n.lineno, n.end_lineno, n.target.id + " = (module-level)"))

with open(OUT, "w", encoding="utf-8") as f:
    for a, b, name in top_defs:
        f.write(f"{a:4} {b:4} {name}\n")
print("written", OUT)
print(f"{len(top_defs)} module-level defs")
print(f"{len(top_withs)} with blocks")
