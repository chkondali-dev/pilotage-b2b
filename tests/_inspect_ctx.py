"""Inspect the frozen TabCtx contract."""
import ast
import io
from pathlib import Path

PATH = Path(r"C:/Users/hachk/pilotage_b2b/ui/tabs/context.py")

tree = ast.parse(PATH.read_text(encoding="utf-8"))
print("dataclass:", any(isinstance(n, ast.ClassDef) and n.name == "TabCtx" for n in tree.body))
for n in tree.body:
    if isinstance(n, ast.ClassDef) and n.name == "TabCtx":
        print("frozen:", any(
            isinstance(b, ast.Assign)
            and any(isinstance(t, ast.Attribute) and t.attr == "frozen" for t in [b.value])
            for b in n.body
        ))
        print("fields:", len(n.body))
        for item in n.body:
            if isinstance(item, ast.AnnAssign):
                print("  ", item.target.id, "->", item.annotation.id)
