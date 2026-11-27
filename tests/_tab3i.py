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

# tab3 block lines 1398-1842
for idx in (3,):
    blk = blocks[idx]
    loads = set()
    for stmt in blk.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                loads.add(n.id)
    print('TAB', idx, 'loads count', len(loads))
    for name in sorted(loads):
        if name == 'i':
            print('  i usages:', [n.lineno for n in ast.walk(blk) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == 'i'])
