"""Report free (non-module) names for selected top-level defs in app.py."""
import ast
import builtins
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
targets = {"_lens_meta", "_registry_sha_now", "_sync_registre", "_cached_scan_all"}

tree = ast.parse(io.open(APP, encoding="utf-8").read())

imports = set()
for n in tree.body:
    if isinstance(n, ast.Import):
        imports |= {(a.asname or a.name.split(".")[0]) for a in n.names}
    elif isinstance(n, ast.ImportFrom):
        imports |= {(a.asname or a.name) for a in n.names}
    elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        imports.add(n.name)
    elif isinstance(n, ast.Assign):
        for t in n.targets:
            if isinstance(t, ast.Name):
                imports.add(t.id)

BUILTINS = set(dir(builtins))

out = []
for n in tree.body:
    if isinstance(n, ast.FunctionDef) and n.name in targets:
        loads, stores = set(), set()
        for x in ast.walk(n):
            if isinstance(x, ast.Name):
                if isinstance(x.ctx, ast.Load):
                    loads.add(x.id)
                elif isinstance(x.ctx, ast.Store):
                    stores.add(x.id)
            elif isinstance(x, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                stores.add(x.name)
            elif isinstance(x, ast.ExceptHandler) and x.name:
                stores.add(x.name)
            elif isinstance(x, ast.arg):
                stores.add(x.arg)
        free = sorted(loads - stores - BUILTINS - imports)
        out.append(f"{n.name}: free={free}")

print("\n".join(out))
