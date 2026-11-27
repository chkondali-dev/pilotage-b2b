import ast

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

for node in ast.walk(tree):
    if isinstance(node, ast.Name) and node.id in ('annee_hier', 'mois_hier', 'code_col_src', 'SEUILS', 'dict'):
        print(node.id, type(node.ctx).__name__, 'line', node.lineno)
