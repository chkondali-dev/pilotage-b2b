import ast
import json

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

# ---- find tab blocks ----
tabblocks = []
for node in ast.walk(tree):
    if isinstance(node, ast.With):
        for s in node.items:
            fe = s.context_expr
            if isinstance(fe, ast.Subscript) and isinstance(fe.value, ast.Name) and fe.value.id == 'tabs':
                if isinstance(fe.slice, ast.Index) and isinstance(fe.slice.value, ast.Num):
                    tabblocks.append((fe.slice.value.n, node))

tabblocks.sort()
print('tab blocks:', tabblocks)

def names_in(node, locals_set=None):
    ns = set()
    for n in ast.walk(node):
        if isinstance(n, ast.Name):
            ns.add(n.id)
    if locals_set is not None:
        ns -= locals_set
    return ns

def assigned_names(node):
    """Names bound (assigned) within a node (top-level of the node, not nested funcs)."""
    ns = set()
    for n in ast.walk(node):
        if isinstance(n, (ast.Assign, ast.AnnAssign)):
            if isinstance(n.target, ast.Name):
                ns.add(n.target.id)
            elif isinstance(n.target, ast.Tuple):
                for el in n.target.elts:
                    if isinstance(el, ast.Name):
                        ns.add(el.id)
    return ns

def block_locals(block):
    """Names bound anywhere in the block (top-level statements, excluding nested func defs)."""
    lbs = set()
    for stmt in block.body:
        lbs |= assigned_names(stmt)
    return lbs

def top_level_defs():
    """Top-level FunctionDef/AsyncFunctionDef/ClassDef outside tab blocks, with their line numbers."""
    res = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            res.append((node.name, node.lineno, type(node).__name__))
    return res

print('\nTOP-LEVEL DEFS:')
for name, ln, t in top_level_defs():
    print(' ', name, 'line', ln, t)

# module-level assignments (top-level, outside tab blocks)
mod_assigns = []
for node in tree.body:
    if isinstance(node, ast.Assign):
        for t in node.targets:
            if isinstance(t, ast.Name):
                mod_assigns.append((t.id, node.lineno))
    elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        mod_assigns.append((node.target.id, node.lineno))
mod_assigns.sort()
print('\nMODULE-LEVEL ASSIGNMENTS:')
for name, ln in mod_assigns:
    print(' ', name, 'line', ln)

# used by each tab?
used_by_tab = {}
for idx, block in tabblocks:
    lbs = block_locals(block)
    used = names_in(block)
    used_by_tab[idx] = {'external': sorted(used - lbs), 'locals': sorted(lbs & used),
                         'all_loads': sorted(used), 'assigned_all': sorted(lbs)}

for idx, info in sorted(used_by_tab.items()):
    print(f'\nTAB {idx}: external loads ({len(info["external"])}):', info['external'])
    print(f'  locals ({len(info["locals"])}):', info['locals'])
