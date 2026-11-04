#!/usr/bin/env python3
import sys

filepath = r'C:/Users/hachk/pilotage_b2b/ui/tabs/tab0_executive.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the full KPI section - replace lines 37-42
old_section = """    k1.metric(f'CA {ctx.annee_sel}', f'{ctx.ca_n:,.0f} TND', f'{fmt_pct(ctx.ev_nn1)} vs {ctx.annee_sel - 1}', delta_color=color_delta(ctx.ev_nn1))\n    # KPI 2: Concentration Top 3% - Factures redirigé vers tab1_tendances\n    k2.metric('Conventions actives', f'{ctx.nb_actives}')\n    st.caption(f'{_conc0[\"Top3 %\"]:.1f}% top 3' if pd.notna(_conc0[\"Top3 %\"]) else f'/ {ctx.nb_total} total')\n    k3.metric('Panier moyen', f\"{_vol0['Panier N']:,.0f} TND\" if pd.notna(_vol0['Panier N']) else '—', f\"{fmt_pct(_vol0['Evo panier %'])} vs N-1\" if pd.notna(_vol0['Evo panier %']) else '—', delta_color=color_delta(_vol0['Evo panier %']))\n    with k4:\n        st.metric('Conventions actives', f'{ctx.nb_actives}')\n        st.caption(f\"{_conc0['Top3 %']:.1f}% top 3\" if pd.notna(_conc0['Top3 %']) else f'/ {ctx.nb_total} total')"""

new_section = """    k1.metric(f'CA {ctx.annee_sel}', f'{ctx.ca_n:,.0f} TND', f'{fmt_pct(ctx.ev_nn1)} vs {ctx.annee_sel - 1}', delta_color=color_delta(ctx.ev_nn1))\n    # KPI 2: Conventions actives\n    with k2:\n        st.metric('Conventions actives', f'{ctx.nb_actives}')\n        st.caption(f'{_conc0[\"Top3 %\"]:.1f}% top 3' if pd.notna(_conc0[\"Top3 %\"]) else f'/ {ctx.nb_total} total')\n    # KPI 3: Panier moyen\n    k3.metric('Panier moyen', f\"{_vol0['Panier N']:,.0f} TND\" if pd.notna(_vol0['Panier N']) else '—', f\"{fmt_pct(_vol0['Evo panier %'])} vs N-1\" if pd.notna(_vol0['Evo panier %']) else '—', delta_color=color_delta(_vol0['Evo panier %']))\n    # KPI 4: Concentration Top 3\n    with k4:\n        st.metric('Concentration Top 3', f'{_conc0[\"Top3 %\"]:.1f}%' if pd.notna(_conc0[\"Top3 %\"]) else '—', help='Part du CA détenue par les 3 plus gros clients')"""

if old_section in content:
    content = content.replace(old_section, new_section)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print('SUCCESS: KPI section fully fixed')
else:
    print('FAILED: old_section not found')
    print('Looking for k1.metric...')
    if 'k1.metric' in content:
        idx = content.find('k1.metric')
        print('Found k1.metric, context:', repr(content[idx:idx+200]))
    # Show what's actually on line 38
    lines = content.split('\n')
    if len(lines) > 37:
        print('Line 38:', repr(lines[37]))