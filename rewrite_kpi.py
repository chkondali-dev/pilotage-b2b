#!/usr/bin/env python3
import re

filepath = r'C:\Users\hachk\pilotage_b2b\ui\tabs\tab0_executive.py'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Debug: check if old content exists
if "k2.metric(f'Factures'" in content:
    print("OLD: Found Factures metric - will replace")
    old_marker = "k2.metric(f'Factures {ctx.annee_sel}',"
    new_section = '''    # --- Section 1: Les 4 KPIs strategiques (sans Factures en double) ---
    _vol0 = volumes_panier(ctx.df_vc_filt, ctx.annee_sel, ctx.mois_sel)
    _conc0 = concentration_portefeuille(ctx.df_vc_filt, ctx.annee_sel, ctx.mois_sel)

    k1, k2, k3, k4 = st.columns(4)

    # KPI 1: CA N
    k1.metric(f'CA {ctx.annee_sel}', f'{ctx.ca_n:,.0f} TND', f'{fmt_pct(ctx.ev_nn1)} vs {ctx.annee_sel - 1}', delta_color=color_delta(ctx.ev_nn1))

    # KPI 2: Panier moyen (Factures declincee vers tab1_tendances)
    k3.metric('Panier moyen', f'{_vol0["Panier N"]:,.0f} TND' if pd.notna(_vol0["Panier N"]) else '—', f'{fmt_pct(_vol0["Evo panier %"])} vs N-1' if pd.notna(_vol0["Evo panier %"]) else '—', delta_color=color_delta(_vol0["Evo panier %"]))

    # KPI 3: Conventions actives
    with k2:
        st.metric('Conventions actives', f'{ctx.nb_actives}')
        st.caption(f'{_conc0["Top3 %"]:.1f}% top 3' if pd.notna(_conc0["Top3 %"]) else f'/ {ctx.nb_total} total')

    # KPI 4: Concentration Top 3
    with k4:
        st.metric('Concentration Top 3', f'{_conc0["Top3 %"]:.1f}%' if pd.notna(_conc0["Top3 %"]) else '—', help='Part du CA détenue par les 3 plus gros clients')

    # --- Section 2: Resume Financier ---'''

    # Replace the old section starting from the marker
    if old_marker in content:
        content = content.replace(old_marker, new_section)
        print("Replaced KPI section")
    else:
        print("Could not find old marker exactly")
else:
    print("NEW: No Factures metric found - checking structure")
    
# Write back if changes made
if "old_marker" in dir() and old_marker in content:
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    print("File updated successfully")
elif "old_marker" in dir():
    print("No changes made - marker not found")