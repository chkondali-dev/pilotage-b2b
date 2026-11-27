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

for h in ('ev_n1n2', 'ev_nn1', 'ca_n2', 'nb_inactif_cv', 'nb_croissance', 'nb_declin_fort', 'nb_total', 'nb_inact', 'nb_actives', 'ca_n', 'ca_n1', 'df_comp', 'risk_mat', 'df_inactive', 'df_3m', 'df_vc_filt', 'df_vc_scope', 'df_filt', 'df_vc', 'df_credit', 'df_edc', 'df_conv', 'code_df', 'df_credit_part', 'df_cube_mag', 'df_prospection', 'df_crm', 'annee_sel', 'mois_sel', 'conv_sel', 'type_vente_sel', 'seuil_inactif', 'objectif_m', 'vol', 'conc', 'lens_labels', 'df_comp', 'risk_mat', 'df_inactive', 'df_3m', 'ca_n', 'ca_n1', 'ev_nn1', 'ca_n2', 'nb_actives', 'nb_inact', 'nb_total', 'seuil_inactif', 'objectif_m', 'df_comp', 'risk_mat', 'df_vc_filt', 'df_vc_scope', 'df_filt', 'df_vc', 'df_credit', 'df_edc', 'df_conv', 'code_df', 'df_credit_part', 'df_cube_mag', 'df_prospection', 'df_crm', 'annee_sel', 'mois_sel', 'conv_sel', 'type_vente_sel', 'seuil_inactif', 'objectif_m'):
    tabs_used = []
    for idx, blk in enumerate(blocks):
        uses = []
        for stmt in blk.body:
            for n in ast.walk(stmt):
                if isinstance(n, ast.Name) and n.id == h and isinstance(n.ctx, ast.Load):
                    uses.append(stmt.lineno)
        if uses:
            tabs_used.append((idx, uses))
    if tabs_used:
        print(h, '->', tabs_used)
