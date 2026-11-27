import ast

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

# find all Assign/AnnAssign targets containing 'vol' or 'conc'
for node in ast.walk(tree):
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name) and ('vol' in t.id or 'conc' in t.id):
                print('ASSIGN', t.id, 'line', node.lineno, 'value:', ast.unparse(node.value)[:100])
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and ('vol' in node.target.id or 'conc' in node.target.id):
        print('ANNSIGN', node.target.id, 'line', node.lineno, 'value:', ast.unparse(node.value)[:100])
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Tuple):
                for el in t.elts:
                    if isinstance(el, ast.Name) and ('vol' in el.id or 'conc' in el.id):
                        print('ASSIGN-tuple', el.id, 'line', node.lineno)
