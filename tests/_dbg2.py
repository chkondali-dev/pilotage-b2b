import ast

PATH = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(PATH, encoding='utf-8').read()
t = ast.parse(src)
blocks = []
for n in ast.walk(t):
    if isinstance(n, ast.With):
        for s in n.items:
            fe = s.context_expr
            if isinstance(fe, ast.Subscript) and isinstance(fe.value, ast.Name) and fe.value.id == 'tabs':
                blocks.append(n)
def si(fe):
    sl = fe.slice
    if isinstance(sl, ast.Index):
        sl = sl.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, int):
        return sl.value
    return -1
blocks.sort(key=lambda n: si(n.items[0].context_expr))
blk = blocks[1]
loads = set()
for n in ast.walk(blk):
    if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
        loads.add(n.id)
print('tab1 block lineno', blk.lineno, 'end', blk.end_lineno)
print('annee_hier in loads:', 'annee_hier' in loads)
print('mois_hier in loads:', 'mois_hier' in loads)
print('code_col_src in loads:', 'code_col_src' in loads)
print('mois_label in loads:', 'mois_label' in loads)
print('sorted loads count', len(loads))
