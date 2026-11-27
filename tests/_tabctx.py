import ast

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

for node in ast.walk(tree):
    if isinstance(node, ast.Name) and node.id == 'TabCtx':
        print('TabCtx Name line', node.lineno, type(node.ctx).__name__)
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'TabCtx':
        print('TabCtx call line', node.lineno)
    if isinstance(node, ast.Attribute) and node.attr == 'TabCtx':
        print('TabCtx attr line', node.lineno)
