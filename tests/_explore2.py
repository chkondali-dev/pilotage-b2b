import ast
import json

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
t = ast.parse(src)

results = []

for i, node in enumerate(t.body):
    if isinstance(node, ast.With):
        for s in node.items:
            if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute) and s.func.attr == 'tabs':
                results.append({
                    'line': node.lineno,
                    'n_stmts': len(node.body),
                    'withexpr': ast.unparse(node.context_expr),
                })

print(json.dumps(results, indent=1))
