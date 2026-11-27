"""Check: are any TabCtx field names used as a parameter anywhere in app.py?"""
import ast
import io

APP = r"C:/Users/hachk/pilotage_b2b/app.py"
CTX = r"C:/Users/hachk/pilotage_b2b/ui/tabs/context.py"

ctx_tree = ast.parse(io.open(CTX, encoding="utf-8").read())
FIELDS = set()
for n in ctx_tree.body:
    if isinstance(n, ast.ClassDef) and n.name == "TabCtx":
        for item in n.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                FIELDS.add(item.target.id)

tree = ast.parse(io.open(APP, encoding="utf-8").read())
params = set()
for n in ast.walk(tree):
    if isinstance(n, ast.arg):
        params.add(n.arg)

hits = sorted(FIELDS & params)
print("fields used as params:", hits)
