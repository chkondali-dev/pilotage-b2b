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

helpers = ['_cached_scan_all', '_cached_data_health', '_cached_precalcs', '_lens_meta', '_sync_registre', '_registry_sha_now', '_conv_options', 'LENS_LABELS']

for h in helpers:
    tabs_used = []
    for idx, blk in enumerate(blocks):
        uses = []
        for stmt in blk.body:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Name) and n.id == h and isinstance(n.ctx, ast.Load):
                    uses.append(stmt.lineno)
        if uses:
            tabs_used.append((idx, uses))
    print(h, '->', tabs_used)
