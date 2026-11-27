"""Inventory : per tab, stores, loads, externals, cross-tab leaks."""
import ast
import builtins
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
OUT = r"C:/Users/hachk/pilotage_b2b/tests/_leaks_out.txt"

tree = ast.parse(io.open(APP, encoding="utf-8").read())

withs = []
for n in tree.body:
    if isinstance(n, ast.With):
        e = n.items[0].context_expr
        if (isinstance(e, ast.Subscript) and isinstance(e.value, ast.Name)
                and e.value.id == "tabs"):
            withs.append((e.slice.value, n))
withs.sort(key=lambda x: x[0])

imports = set()
top_names = set()
for n in tree.body:
    if isinstance(n, ast.Import):
        imports |= {a.name.split(".")[0] for a in n.names}
    elif isinstance(n, ast.ImportFrom):
        imports |= {a.name for a in n.names}
    elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        top_names.add(n.name)
    elif isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name):
                top_names.add(t.id)
    elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
        top_names.add(n.target.id)

BUILTINS = set(dir(builtins))

info = {}
for idx, node in withs:
    mod = ast.Module(body=list(node.body), type_ignores=[])
    loads, stores = set(), set()
    for n in ast.walk(mod):
        if isinstance(n, ast.Name):
            if isinstance(n.ctx, ast.Load):
                loads.add(n.id)
            elif isinstance(n.ctx, ast.Store):
                stores.add(n.id)
        elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            stores.add(n.name)
        elif isinstance(n, ast.ExceptHandler) and n.name:
            stores.add(n.name)
    ext = sorted(loads - stores - BUILTINS)
    info[idx] = {"stores": stores, "loads": loads, "ext": ext}

leaks = []
for a in range(10):
    for b in range(10):
        if a == b:
            continue
        shared = (info[a]["stores"] & info[b]["loads"]) - info[b]["stores"]
        for name in sorted(shared):
            leaks.append((a, b, name))

with io.open(OUT, "w", encoding="utf-8") as f:
    for idx in range(10):
        f.write(f"TAB {idx} stores={len(info[idx]['stores'])} "
                f"loads={len(info[idx]['loads'])} ext={len(info[idx]['ext'])}\n")
        f.write("   ext: " + ", ".join(info[idx]["ext"]) + "\n")
    f.write("\nCROSS-TAB LEAKS (store in A, load in B, not store in B):\n")
    for a, b, name in leaks:
        f.write(f"  tab{a} -> tab{b} : {name}\n")

print("written", OUT)
print("leaks", len(leaks))

