import ast
import sys

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
t = ast.parse(src)

print('total lines:', src.count(chr(10)) + 1)
print('body items:', len(t.body))

for i, node in enumerate(t.body):
    if isinstance(node, ast.With):
        for s in node.items:
            if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute) and s.func.attr == 'tabs':
                print('WITH tabs call line', node.lineno, 'statements:', len(node.body))
