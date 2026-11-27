import ast

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

withblocks = []
for node in ast.walk(tree):
    if isinstance(node, ast.With):
        for s in node.items:
            fe = s.context_expr
            if isinstance(fe, ast.Subscript):
                withblocks.append(node)

print('with tabs[...] blocks:', len(withblocks))
for w in withblocks:
    print(w.lineno, 'n_stmts', len(w.body))
