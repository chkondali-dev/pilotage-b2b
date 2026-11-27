"""
Phase 2 generator: ui/tabs/<tabN>.py
- parses app.py (C:\Users\hachk\pilotage_b2b\app.py)
- classifies every Load name inside each with tabs[i]: block
- writes ui/tabs/tab0.py..tab9.py with render(c: TabCtx) -> None
- inlines module-level helpers, adds TabCtx fields, recomputes cross-tab locals
- py_compile checks + prints needed TabCtx fields per tab
"""
import ast, py_compile, sys, re

APP = r'C:\Users\hachk\pilotage_b2b\app.py'
OUTDIR = r'C:\Users\hachk\pilotage_b2b\ui\tabs'
sys.stdout.reconfigure(encoding='utf-8')
TABS = 10

src = open(APP, encoding='utf-8').read()
tree = ast.parse(src)

# ---- locate the 10 tab blocks ----
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
assert len(tabblocks) == TABS

# ---- block locals (bound) / usage (loaded) ----
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

# ---- module-level defs/assigns/imports ----
mod_defs = set(); mod_assigns = set(); mod_imports = []
for node in tree.body:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        mod_defs.add(node.name)
    elif isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name): mod_assigns.add(t.id)
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        mod_assigns.add(node.target.id)
    elif isinstance(node, ast.Import):
        for a in node.names: mod_imports.append((a.name, a.asname or a.name))
    elif isinstance(node, ast.ImportFrom):
        mod_imports.append((node.module or '', [a.asname or a.name for a in node.names]))

# ---- cross-tab binding map ----
allnames = set()
for t in tabs:
    allnames |= set(t['locals']) | set(t['usage'])
allnames |= mod_defs | mod_assigns
for mod, names in mod_imports:
    for n in names: allnames.add(n)
bind_tab = {n: set() for n in allnames}
load_tab = {n: set() for n in allnames}
for idx, t in enumerate(tabs):
    for n in t['locals']: bind_tab[n].add(idx)
    for n in t['usage']: load_tab[n].add(idx)

# ---- recompute expression for a cross-tab local ----
def replace_module_names(seg):
    names = sorted(mod_assigns | mod_defs, key=len, reverse=True)
    r = seg
    for n in names:
        r = re.sub(r'(?<![A-Za-z0-9_])' + re.escape(n) + r'(?![A-Za-z0-9_])', r'c.' + n, r)
    return r

def recompute_expr(name, blk):
    for stmt in blk.body:
        if isinstance(stmt, ast.Assign): targets = stmt.targets
        elif isinstance(stmt, ast.AnnAssign): targets = [stmt.target]
        else: continue
        for t in targets:
            if isinstance(t, ast.Name) and t.id == name:
                seg = ast.get_source_segment(src, stmt.value)
                return replace_module_names(seg)
    return None

def is_top_level_assign(name, tidx):
    for stmt in tabblocks[tidx].body:
        if isinstance(stmt, ast.Assign):
            for t in stmt.targets:
                if isinstance(t, ast.Name) and t.id == name: return True
                if isinstance(t, ast.Tuple):
                    for e in t.elts:
                        if isinstance(e, ast.Name) and e.id == name: return True
        elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name) and stmt.target.id == name:
            return True
    return False

# ---- per-tab classification ----
TABINFO = {}
for idx, t in enumerate(tabs):
    locs = set(); cross = {}; mods = set(); ctx = set()
    for name in sorted(t['usage']):
        b = bind_tab[name]; l = load_tab[name]
        if idx in b and idx in l:
            locs.add(name); continue
        if idx in l:
            if name in mod_assigns:
                ctx.add(name)
            elif name in mod_defs:
                mods.add(name)
            elif name in mod_imports and name in mod_imports:
                mods.add(name)
            elif b and is_top_level_assign(name, idx):
                cross[name] = recompute_expr(name, tabblocks[idx])
            else:
                mods.add(name)
    TABINFO[idx] = {'locs': locs, 'cross': cross, 'mods': mods, 'ctx': ctx}
