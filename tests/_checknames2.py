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

def bound_in(blk, name):
    for stmt in blk.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name) and t.id == name:
                        return True
                    if isinstance(t, ast.Tuple):
                        for el in t.elts:
                            if isinstance(el, ast.Name) and el.id == name:
                                return True
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.target.id == name:
                return True
            elif isinstance(n, ast.For):
                for t in (n.target.elts if isinstance(n.target, ast.Tuple) else [n.target]):
                    if isinstance(t, ast.Name) and t.id == name:
                        return True
            elif isinstance(n, ast.AsyncFor):
                for t in (n.target.elts if isinstance(n.target, ast.Tuple) else [n.target]):
                    if isinstance(t, ast.Name) and t.id == name:
                        return True
            elif isinstance(n, ast.NamedExpr) and isinstance(n.target, ast.Name) and n.target.id == name:
                return True
    return False

def loaded_in(blk, name):
    for stmt in blk.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load) and n.id == name:
                return True
    return False

for name in ('k1', 'k2', 'k3', 'k4', 'i', 'mois_label', 'df_filt', 'col_r1', 'col_r2', 'fig_cum', 'r', '_r', 'm', 'n', 'p', 'v', 'e', 'd', 't'):
    binds = set()
    loads = set()
    for idx, blk in enumerate(blocks):
        if bound_in(blk, name):
            binds.add(idx)
        if loaded_in(blk, name):
            loads.add(idx)
    print(name, 'bind', sorted(binds), 'load', sorted(loads))
