import ast, json

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
NT = len(tabblocks)

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
            elif isinstance(n, ast.AsyncFor):
                for t in (n.target.elts if isinstance(n.target, ast.Tuple) else [n.target]):
                    if isinstance(t, ast.Name):
                        lbs.add(t.id)
            elif isinstance(n, ast.NamedExpr) and isinstance(n.target, ast.Name):
                lbs.add(n.target.id)
    return lbs

def block_usage(block):
    loads = {}
    for stmt in block.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                loads[n.id] = loads.get(n.id, 0) + 1
    return loads

tabs = []
for idx, blk in enumerate(tabblocks):
    lbs = block_locals(blk)
    uses = block_usage(blk)
    tabs.append({'locals': lbs, 'uses': uses})

# module-level defs & assigns
mod_defs = set()
mod_assigns = set()
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        mod_defs.add(node.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                mod_assigns.add(t.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        mod_assigns.add(node.target.id)

# imports
mod_imports = []
for node in tree.body:
    if isinstance(node, ast.Import):
        for a in node.names:
            mod_imports.append((a.name, a.asname or a.name))
    elif isinstance(node, ast.ImportFrom):
        mod_imports.append((node.module or '', [a.asname or a.name for a in node.names]))

allnames = set()
for t in tabs:
    allnames |= set(t['uses'])
for n in mod_defs | mod_assigns:
    allnames.add(n)
for mod, names in mod_imports:
    for n in names:
        allnames.add(n)

bind = {n: set() for n in allnames}
load = {n: set() for n in allnames}
for idx, t in enumerate(tabs):
    for n in t['locals']:
        bind[n].add(idx)
    for n in t['uses']:
        load[n].add(idx)

def classify(name):
    b, l = bind[name], load[name]
    # tab-local: bound only in same tab as loaded
    same = b & l
    if same:
        for b_ in same:
            if b == l == {b_}:
                return 'TAB_LOCAL', b_
    if b or l:
        # cross-tab: bound in a different tab than loaded
        if b & l:
            # if all binds are in same tabs as loads but not equal
            if not (b == l):
                return 'CROSS_TAB', None
        elif b and not l:
            return 'STORE_ONLY', None
        elif l and not b:
            return 'SOMEWHERE', None
    for n in mod_defs:
        if n == name:
            return 'DEF', None
    for n in mod_assigns:
        if n == name:
            return 'ASSIGN', None
    for mod, names in mod_imports:
        if name in names:
            return 'IMPORT', mod
    return 'UNKNOWN', None

out = {}
for idx in range(NT):
    loc, cross, modnames, ctxnames = set(), [], set(), set()
    for name in tabs[idx]['uses']:
        kind, note = classify(name)
        if kind == 'TAB_LOCAL':
            loc.add(name)
        elif kind == 'CROSS_TAB':
            cross.append(name)
        elif kind in ('IMPORT', 'DEF', 'ASSIGN'):
            modnames.add(name)
        else:
            modnames.add(name)
    out[idx] = {
        'locals': sorted(loc),
        'cross': cross,
        'imports': sorted(modnames),
        'tab_ctx': sorted(ctxnames),
    }

with open(r'C:\Users\hachk\pilotage_b2b\tests\_classify3_out.json', 'w', encoding='utf-8') as f:
    json.dump(out, f, indent=1, ensure_ascii=False)

print(json.dumps(out, indent=1))
