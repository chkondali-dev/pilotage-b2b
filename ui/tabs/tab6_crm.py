import plotly.express as px
import streamlit as st


def render(ctx):
    if ctx.df_crm is not None and len(ctx.df_crm) > 0:
        ca_pot_total = ctx.df_crm['CA potentiel'].sum()
        ca_real_total = ctx.df_crm['CA realise'].sum()
        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric('Total prospects', len(ctx.df_crm))
        en_cours = len(ctx.df_crm[ctx.df_crm['Statut pipeline'] == 'En cours'])
        k2.metric('En cours', en_cours)
        cloture = len(ctx.df_crm[ctx.df_crm['Statut pipeline'] == 'Cloture'])
        k3.metric('Cloturees', cloture)
        k4.metric('CA potentiel', f'{ca_pot_total:,.0f}')
        k5.metric('CA realise', f'{ca_real_total:,.0f}', delta=f'{(ca_real_total / ca_pot_total * 100 if ca_pot_total > 0 else 0):.0f}% taux real.')
        col1, col2, col3 = st.columns(3)
        with col1:
            pipe = ctx.df_crm['Statut pipeline'].value_counts().reset_index()
            pipe.columns = ['Statut', 'Nb']
            fig_pipe = px.bar(pipe, x='Statut', y='Nb', color='Statut', title='Pipeline Commercial', text_auto=True, height=300)
            fig_pipe.update_layout(showlegend=False)
            st.plotly_chart(fig_pipe, use_container_width=True)
        with col2:
            prio = ctx.df_crm['Priorite relance'].value_counts().reset_index()
            prio.columns = ['Priorite', 'Nb']
            fig_prio = px.pie(prio, values='Nb', names='Priorite', title='Priorites Relance', height=300, hole=0.4)
            st.plotly_chart(fig_prio, use_container_width=True)
        with col3:
            sect = ctx.df_crm['Secteur'].value_counts().reset_index()
            sect.columns = ['Secteur', 'Nb']
            fig_sect = px.pie(sect, values='Nb', names='Secteur', title='Secteurs', height=300, hole=0.4, color_discrete_sequence=['#059669', '#1D4ED8', '#D97706'])
            st.plotly_chart(fig_sect, use_container_width=True)
        st.markdown("<div class='sec-hdr'>Prospects</div>", unsafe_allow_html=True)
        cols_show = ['Nom entreprise', 'Statut pipeline', 'Priorite relance', 'Secteur', 'CA potentiel', 'CA realise', 'Responsable commercial', 'Date derniere activite']
        cols_ok = [c for c in cols_show if c in ctx.df_crm.columns]
        df_disp = ctx.df_crm[cols_ok].head(20).reset_index(drop=True)
        ev = st.dataframe(df_disp, use_container_width=True, height=450, column_config={c: st.column_config.NumberColumn(format='%d') for c in ['CA potentiel', 'CA realise'] if c in df_disp.columns}, on_select='rerun', selection_mode='single-row')
        sel = ev.selection.rows if hasattr(ev, 'selection') else []
        if sel:
            idx = sel[0]
            client = ctx.df_crm.loc[df_disp.index[idx]]
            nm = str(client.get('Nom entreprise', ''))
            with st.container():
                st.markdown(f"<div style='background:#f0f2f6;padding:1.2rem 1.5rem;border-radius:12px;margin-top:0.5rem'><h3 style='margin:0 0 1rem 0'>{nm}</h3>", unsafe_allow_html=True)
                cx = st.columns(4)
                cx[0].markdown(f"**Contact**<br>{client.get('Contact', '')}", unsafe_allow_html=True)
                cx[1].markdown(f"**Telephone**<br>{client.get('Telephone', '')}", unsafe_allow_html=True)
                cx[2].markdown(f"**Secteur**<br>{client.get('Secteur', '')}", unsafe_allow_html=True)
                ca_p = client.get('CA potentiel', 0)
                ca_r = client.get('CA realise', 0)
                cx[3].markdown(f'**CA potentiel**<br>{ca_p:,.0f}  \n**CA realise**<br>{ca_r:,.0f}', unsafe_allow_html=True)
                cmt = str(client.get('Commentaire', ''))
                if cmt and cmt != 'nan' and cmt.strip():
                    st.markdown(f'**Commentaire :** {cmt}')
                st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info('CRM desactive. Verifiez TDC2.xlsx et crm.py')