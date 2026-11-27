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
    if isinstance(sl, ast.Index): sl = sl.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, int): return sl.value
    return None

blocks.sort(key=lambda b: si(b.items[0].context_expr))

for idx in (0, 4, 8):
    blk = blocks[idx]
    uses = []
    for stmt in blk.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == 'm':
                uses.append(stmt.lineno)
    print('TAB', idx, 'uses of m:', uses)
