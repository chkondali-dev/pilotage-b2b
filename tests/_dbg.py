import ast

PATH = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(PATH, encoding='utf-8').read()
tree = ast.parse(src)

tabblocks = []
for node in ast.walk(tree):
    if isinstance(node, ast.With):
        for s in node.items:
            fe = s.context_expr
            if isinstance(fe, ast.Subscript) and isinstance(fe.value, ast.Name) and fe.value.id == 'tabs':
                tabblocks.append(node)

def slice_index(fe):
    sl = fe.slice
    if isinstance(sl, ast.Index):
        sl = sl.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
        return sl.value
    return None

tabblocks.sort(key=lambda b: slice_index(b.items[0].context_expr))

def block_usage(block):
    loads = {}
    for stmt in block.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                loads[n.id] = loads.get(n.id, 0) + 1
    return loads

for idx, blk in enumerate(tabblocks):
    uses = block_usage(blk)
    if 'mois_hier' in uses or 'annee_hier' in uses or 'code_col_src' in uses:
        print('tab', idx, [k for k in uses if k in ('mois_hier','annee_hier','code_col_src','mois_label','_vol0','_conc0')])
