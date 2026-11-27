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
    for stmt in blk.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == 'df_filt':
                        print('tab', idx, 'df_filt store at line', stmt.lineno)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == 'df_filt':
                print('tab', idx, 'df_filt annassign at line', stmt.lineno)
