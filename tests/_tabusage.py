import ast

path = r'C:\Users\hachk\pilotage_b2b\app.py'
src = open(path, encoding='utf-8').read()
tree = ast.parse(src)

tabblocks = []
for node in ast.walk(tree):
    if isinstance(node, ast.With):
        for s in node.items:
            fe = s.context_expr
            if isinstance(fe, ast.Subscript) and isinstance(fe.value, ast.Name) and fe.value.id == 'tabs':
                tabblocks.append(node)

# find the slice index
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
            if isinstance(n, (ast.Assign, ast.AnnAssign)):
                tgt = n.target
                if isinstance(tgt, ast.Name):
                    lbs.add(tgt.id)
                elif isinstance(tgt, ast.Tuple):
                    for el in tgt.elts:
                        if isinstance(el, ast.Name):
                            lbs.add(el.id)
    return lbs

def block_usage(block):
    """Names loaded in block, with origin tab (whether bound in same block)."""
    loads = {}
    for stmt in block.body:
        for n in ast.walk(stmt):
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
                loads.setdefault(n.id, set()).add(type(n.ctx).__name__)
    return loads

# for each tab, compute:
#  - locals (bound in block)
#  - loads (read in block) with whether bound locally
for idx, block in tabblocks:
    lbs = block_locals(block)
    loads = block_usage(block)
    print(f'=== TAB {idx} ===')
    print('  locals:', sorted(lbs))
    print('  loads (all):', sorted(loads.keys()))
    cross = {k: v for k, v in loads.items() if k not in lbs}
    print('  external loads:', sorted(cross.keys()))
