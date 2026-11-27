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

# every occurrence of helper names in the whole file
for h in ('_cached_data_health', '_cached_scan_all', '_cached_precalcs', '_lens_meta',
          '_sync_registre', '_registry_sha_now', '_conv_options', 'LENS_LABELS',
          'render_alert_panel', '_sync_registre'):
    print('===', h)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == h:
            print('  line', node.lineno, type(node.ctx).__name__)
