import ast

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

blocks = []
for node in ast.walk(tree):
    if isinstance(node, ast.With):
        for s in node.items:
            fe = s.context_expr
            if isinstance(fe, ast.Subscript) and isinstance(fe.value, ast.Name) and fe.value.id == 'tabs':
                blocks.append(node)

def si(fe):
    sl = fe.slice
    if isinstance(sl, ast.Index):
        sl = sl.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
        return sl.value
    return None

blocks.sort(key=lambda b: si(b.items[0].context_expr))

for idx, blk in enumerate(blocks):
    if idx in (0, 1, 2, 3, 4, 5):
        print('TAB', idx, 'lineno', blk.lineno, 'end', blk.end_lineno, 'body stmts', len(blk.body))
        for j, stmt in enumerate(blk.body[:3]):
            print('   stmt', j, stmt.lineno, type(stmt).__name__)
