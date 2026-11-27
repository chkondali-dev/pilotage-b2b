"""Detect names read before first assignment inside each tabs[i] block.

In the original (module-level `with`) such a read pulls the module global.
After wrapping the body in `def render(c):` it would raise UnboundLocalError.
Writes tests/_readbefore_out.txt.
"""
import ast
import builtins
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
OUT = r"C:/Users/hachk/pilotage_b2b/tests/_readbefore_out.txt"

tree = ast.parse(io.open(APP, encoding="utf-8").read())

BUILTINS = set(dir(builtins))

lines = []
for n in tree.body:
    if not isinstance(n, ast.With):
        continue
    e = n.items[0].context_expr
    if not (isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name)
            and e.value.id == "tabs"):
        continue
    idx = e.slice.value
    events = []  # (lineno, col, kind, name)
    for x in ast.walk(n):
        if isinstance(x, ast.Name):
            if isinstance(x.ctx, ast.Load):
                events.append((x.lineno, x.col_offset, "L", x.id))
            elif isinstance(x.ctx, ast.Store):
                events.append((x.lineno, x.col_offset, "S", x.id))
        elif isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            events.append((x.lineno, x.col_offset, "S", x.name))
        elif isinstance(x, ast.ExceptHandler) and x.name:
            events.append((x.lineno, x.col_offset, "S", x.name))
    events.sort()
    first_load = {}
    first_store = {}
    for lineno, col, kind, name in events:
        if name in BUILTINS:
            continue
        if kind == "L" and name not in first_load:
            first_load[name] = (lineno, col)
        if kind == "S" and name not in first_store:
            first_store[name] = (lineno, col)
    risky = []
    for name, lp in first_load.items():
        sp = first_store.get(name)
        if sp is None:
            continue
        if lp < sp:
            risky.append((name, lp, sp))
    lines.append(f"TAB {idx}: read-before-write={len(risky)}")
    for name, lp, sp in risky:
        lines.append(f"   {name}: load@{lp[0]}:{lp[1]} store@{sp[0]}:{sp[1]}")
    lines.append("")

io.open(OUT, "w", encoding="utf-8").write("\n".join(lines))
print("written", OUT)
print("\n".join(lines))
