import ast

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

withblocks = []
for node in ast.walk(tree):
    if isinstance(node, ast.With):
        for s in node.items:
            if isinstance(s, ast.Call) and isinstance(s.func, ast.Attribute) and s.func.attr == 'tabs':
                withblocks.append(node)

print('with tabs(...) blocks:', len(withblocks))
for w in withblocks:
    print(w.lineno, 'n_stmts', len(w.body))

# Find names used inside each block
def names_in(node):
    ns = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            ns.add((n.id, n.ctx.__class__.__name__))
    return ns

for idx, w in enumerate(withblocks):
    ns = names_in(w)
    print('--- tab', idx, 'with-block line', w.lineno, '---')
    for nid, ctx in sorted(ns):
        print('   ', nid, ctx)
