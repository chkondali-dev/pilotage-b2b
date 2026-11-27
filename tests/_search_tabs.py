import ast
import re

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()

# find all assignments of tabs
tree = ast.parse(src)
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and 'tabs' in t.id.lower():
                print('ASSIGN', t.id, 'line', node.lineno, 'value', ast.unparse(node.value)[:120])
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and 'tabs' in node.target.id.lower():
        print('ANNSIGN', node.target.id, 'line', node.lineno, 'value', ast.unparse(node.value)[:120])

# find all Name uses of tabs
names = set()
for node in ast.walk(tree):
    if isinstance(node, ast.Name) and node.id == 'tabs':
        names.add(node.lineno)
print('tabs Name uses:', sorted(names))
