import ast

APP = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(APP, encoding='utf-8').read()
tree = ast.parse(src)

tabblocks = []
for node in ast.walk(tree):
    if isinstance(node, ast.With):
        for s in node.items:
            fe = s.context_expr
            if isinstance(fe, ast.Subscript) and isinstance(fe.value, ast.Name) and fe.value.id == 'tabs':
                tabblocks.append(node)

def si(fe):
    sl = fe.slice
    if isinstance(sl, ast.Index): sl = sl.value
    if isinstance(sl, ast.Constant) and isinstance(sl.value, int): return sl.value
    return None

tabblocks.sort(key=lambda b: si(b.items[0].context_expr))

def block_locals(bl):
    lbs = set()
    for stmt in bl.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Assign):
                for t in n.targets:
                    if isinstance(t, ast.Name): lbs.add(t.id)
                    elif isinstance(t, ast.Tuple):
                        for e in t.elts:
                            if isinstance(e, ast.Name): lbs.add(e.id)
            elif isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
                lbs.add(n.target.id)
            elif isinstance(n, ast.For):
                for t in (n.target.elts if isinstance(n.target, ast.Tuple) else [n.target]):
                    if isinstance(t, ast.Name): lbs.add(t.id)
            elif isinstance(n, ast.AsyncFor):
                for t in (n.target.elts if isinstance(n.target, ast.Tuple) else [n.target]):
                    if isinstance(t, ast.Name): lbs.add(t.id)
    return lbs

def block_usage(bl):
    u = {}
    for stmt in bl.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                u[n.id] = u.get(n.id, 0) + 1
    return u

tabs = [{'locals': block_locals(b), 'usage': block_usage(b)} for b in tabblocks]

mod_defs = set(); mod_assigns = set()
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        mod_defs.add(node.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name): mod_assigns.add(t.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        mod_assigns.add(node.target.id)

allnames = set()
for t in tabs:
    allnames |= set(t['locals']) | set(t['usage'])
allnames |= mod_defs | mod_assigns
bind_tab = {n: set() for n in allnames}
load_tab = {n: set() for n in allnames}
for idx, t in enumerate(tabs):
    for n in t['locals']: bind_tab[n].add(idx)
    for n in t['usage']: load_tab[n].add(idx)

for name in ('ca_n', 'ca_n1', 'ev_nn1', 'df_filt', 'm', 'nom', 'c', 'ca', '_r'):
    print(name, 'bind', sorted(bind_tab[name]), 'load', sorted(load_tab[name]))
