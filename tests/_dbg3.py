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

def block_locals(block):
    lbs = set()
    for stmt in block.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Assign):
                for tgt in n.targets:
                    if isinstance(tgt, ast.Name):
                        lbs.add(tgt.id)
                    elif isinstance(tgt, ast.Tuple):
                        for el in tgt.elts:
                            if isinstance(el, ast.Name):
                                lbs.add(el.id)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                lbs.add(n.target.id)
            elif isinstance(n, ast.For):
                for t in (n.target.elts if isinstance(n.target, ast.Tuple) else [n.target]):
                    if isinstance(t, ast.Name):
                        lbs.add(t.id)
    return lbs

for idx, blk in enumerate(tabblocks):
    lbs = block_locals(blk)
    if 'i' in lbs or 'k1' in lbs or 'df_filt' in lbs or 'mois_label' in lbs:
        print('TAB', idx, 'has i:', 'i' in lbs, 'k1:', 'k1' in lbs, 'df_filt:', 'df_filt' in lbs, 'mois_label:', 'mois_label' in lbs)
    if idx in (0, 1, 5):
        print('TAB', idx, 'locals with i:', sorted(lbs))
