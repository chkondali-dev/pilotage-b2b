from io import BytesIO
from data.config import JALONS_STATUTS
from data.transforms import PROSP_ETAPES
from pathlib import Path
from data.config import SEUILS
from data.config import STATUTS_CONVENTION
from data.transforms import ajoute_crm
import business.conventions as conv
from datetime import datetime
from data.transforms import enrich_prospection
from utils.github import file_sha
import os
import pandas as pd
from utils.github import push_csv_to_github
import plotly.express as px
import streamlit as st


REGISTRY_CSV_REL = 'data/conventions_signees.csv'


def render(ctx):
    df_filt = ctx.df_filt

    def _registry_sha_now():
        """sha blob du registre local APRÈS une synchro réussie (nouvelle base)."""
        return file_sha(Path(ctx.base_dir) / REGISTRY_CSV_REL)

    def _sync_registre(commit_msg: str, msg_ok: str) -> bool:
        """Pousse le registre sur GitHub et affiche le statut RÉEL (Phase 1.2).

        « synchronisé » affiché uniquement si le push réussit ; sinon st.error avec
        la cause. La modification reste locale et l'intention est conservée dans
        st.session_state["sync_pending"] pour retenter (bouton en haut de l'onglet
        Conventions encours).
        """
        res = push_csv_to_github(REGISTRY_CSV_REL, commit_msg, base_sha=st.session_state.get('registry_base_sha'))
        if res['ok']:
            st.session_state.pop('sync_pending', None)
            st.session_state['registry_base_sha'] = _registry_sha_now()
            st.success(msg_ok)
            return True
        st.session_state['sync_pending'] = {'commit_msg': commit_msg, 'status': res['status'], 'detail': res['detail']}
        st.error(f"GitHub non synchronisé ({res['status']}) : {res['detail']}")
        st.caption("Modifications conservées localement dans data/conventions_signees.csv — « Réessayer la synchronisation » en haut de l'onglet Conventions encours.")
        return False
    st.markdown('Conventions encours')
    st.caption('Suivi des projets de convention — de la prospection a la finalisation.')
    _pend = st.session_state.get('sync_pending')
    if _pend:
        st.error(f"GitHub non synchronisé ({_pend['status']}) : {_pend['detail']} — modifications conservées localement.")
        if st.button('Réessayer la synchronisation', key='retry_sync'):
            _res = push_csv_to_github(REGISTRY_CSV_REL, _pend['commit_msg'], base_sha=st.session_state.get('registry_base_sha'))
            if _res['ok']:
                st.session_state.pop('sync_pending', None)
                st.session_state['registry_base_sha'] = _registry_sha_now()
                st.success('Synchronisé sur GitHub.')
                st.rerun()
            else:
                st.session_state['sync_pending'] = {**_pend, 'status': _res['status'], 'detail': _res['detail']}
                st.error(f"Échec à nouveau ({_res['status']}) : {_res['detail']}")
    MOTIFS_BLOCAGE = ['(aucun)', 'Attente décision / confirmation client', 'Bloqué côté juridique', 'Bloqué côté financier', 'En attente de signature', 'Prix / remise à renégocier', 'Concurrent engagé', 'Contact injoignable', 'Dossier incomplet', 'Reporté / pause', 'Refusé / non retenu']
    STATUTS_CLOS = {'Signe', 'Finalise', 'Refuse', 'Archive'}
    COLORS_STATUTS = {'Prospection': '#F59E0B', 'Negociation': '#F97316', 'En cours': '#3B82F6', 'Finalisation': '#8B5CF6', 'Signe': '#10B981', 'Finalise': '#059669', 'Refuse': '#DC2626'}
    if not ctx.df_prospection.empty:
        st.markdown('### Pipeline Prospection')
        st.caption(f'{len(ctx.df_prospection)} prospects suivis dans le pipeline')
        dfp = enrich_prospection(ctx.df_prospection, SEUILS['prospection_stalle_jours'], SEUILS['relance_jours'])
        if dfp.empty:
            dfp = ctx.df_prospection.copy()
            dfp['Situation'] = dfp.get('AVANCEMENT2', pd.Series('', index=dfp.index)).fillna('')
            dfp['Durée (j)'] = pd.NA
            dfp['Dernière activité'] = pd.NaT
            dfp['Motif blocage (suggéré)'] = ''
        dfp = ajoute_crm(dfp, ctx.df_crm)
        non_dem = len(dfp[dfp['AVANCEMENT2'] == 'Non démarré'])
        en_cours = len(dfp[dfp['AVANCEMENT2'] == 'En cours'])
        cloture = len(dfp[dfp['AVANCEMENT2'] == 'Clôturé'])
        nb_bloq = int(dfp['Situation'].str.startswith('🔴').sum())
        nb_rel = int(dfp['Situation'].str.startswith('🟡').sum())
        _ouvr = dfp[~dfp['Situation'].str.startswith(('✅', '⚪'))]
        _dm_ouvr = _ouvr['Durée (j)'].dropna().mean()
        _last_act = dfp['Dernière activité'].max()
        pc1, pc2, pc3, pc4 = st.columns(4)
        pc1.metric('Total prospects', len(dfp))
        pc2.metric('Non démarré', non_dem)
        pc3.metric('En cours', en_cours)
        pc4.metric('Clôturé', cloture)
        pd1, pd2, pd3, pd4 = st.columns(4)
        pd1.metric(f"🔴 Bloqués ≥ {SEUILS['prospection_stalle_jours']} j", nb_bloq)
        pd2.metric('🟡 À relancer', nb_rel)
        pd3.metric('Durée moy. ouverts', f'{_dm_ouvr:.0f} j' if pd.notna(_dm_ouvr) else '—')
        pd4.metric('Dernière activité', _last_act.strftime('%d/%m/%Y') if pd.notna(_last_act) else '—')
        today_pip = pd.Timestamp.now().normalize()
        nb_retard = int(dfp['Retard (j)'].notna().sum()) if 'Retard (j)' in dfp.columns else 0
        ca_pot_ouvr = _ouvr['CA potentiel (CRM)'].fillna(0).sum() if 'CA potentiel (CRM)' in _ouvr.columns else 0
        _rel7 = 0
        if 'Relance suggérée' in dfp.columns:
            _rel7 = int((dfp['Relance suggérée'].notna() & (dfp['Relance suggérée'] <= today_pip + pd.Timedelta(days=7))).sum())
        _taux_sig = dfp['Étape atteinte'].eq('Signature').mean() * 100 if 'Étape atteinte' in dfp.columns else float('nan')
        pe1, pe2, pe3, pe4 = st.columns(4)
        pe1.metric('⏰ Retard de jalon', nb_retard)
        pe2.metric('🎯 CA potentiel ouverts', f'{ca_pot_ouvr:,.0f} TND' if ca_pot_ouvr else '—')
        pe3.metric('📅 Relances ≤ 7 j', _rel7)
        pe4.metric('🔄 Taux transformation', f'{_taux_sig:.0f} %' if pd.notna(_taux_sig) else '—')
        c_a, c_b = st.columns(2)
        with c_a:
            df_pipe = pd.DataFrame({'Étape': ['Non démarré', 'En cours', 'Clôturé'], 'Prospects': [non_dem, en_cours, cloture]})
            fig_bar = px.bar(df_pipe, y='Étape', x='Prospects', orientation='h', title='Répartition du pipeline', color='Étape', color_discrete_map={'Non démarré': '#94A3B8', 'En cours': '#1D4ED8', 'Clôturé': '#059669'}, text='Prospects')
            fig_bar.update_traces(textposition='outside')
            fig_bar.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), showlegend=False, xaxis_visible=False, yaxis_title=None)
            st.plotly_chart(fig_bar, use_container_width=True, key='chart_pipe_statuts')
        with c_b:
            _fun, _prev, _prev_n = ([], None, len(dfp))
            for _nom_e, _col_e in PROSP_ETAPES:
                if _col_e not in dfp.columns:
                    continue
                _n = int(dfp[_col_e].notna().sum())
                _delai = '—'
                if _prev is not None:
                    _d = (dfp[_col_e] - dfp[_prev]).dt.days.dropna()
                    _delai = f'{_d.mean():.0f}' if len(_d) else '—'
                _fun.append({'Étape': _nom_e, 'Atteints': _n, '% pipeline': f'{_n * 100 / len(dfp):.0f}%', '% vs préc.': f'{_n * 100 / _prev_n:.0f}%' if _prev_n else '—', 'Délai (j)': _delai})
                _prev, _prev_n = (_col_e, max(_n, 1))
            df_fun = pd.DataFrame(_fun)
            fig_fun = px.bar(df_fun, y='Étape', x='Atteints', orientation='h', title='Funnel — étapes du dossier', text='Atteints', category_orders={'Étape': list(df_fun['Étape'])[::-1]})
            fig_fun.update_traces(textposition='outside')
            fig_fun.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), showlegend=False, xaxis_visible=False, yaxis_title=None)
            st.plotly_chart(fig_fun, use_container_width=True, key='chart_funnel_prosp')
            st.caption("Conversion vs l'étape précédente + délai moyen entre étapes :")
            st.dataframe(df_fun, use_container_width=True, hide_index=True)
        _g = dfp[dfp['Date début'].notna() & ~dfp['Situation'].str.startswith('✅')].copy() if 'Date début' in dfp.columns else pd.DataFrame()
        if not _g.empty:
            _fin_g = _g['Date fin'].fillna(today_pip)
            _g['Fin Gantt'] = _fin_g.where(_fin_g >= _g['Date début'], _g['Date début'] + pd.Timedelta(days=1))
            _g['Client'] = _g['conventions en cours'].astype(str).str.slice(0, 45)
            _g = _g.sort_values('Date début')
            fig_g = px.timeline(_g, x_start='Date début', x_end='Fin Gantt', y='Client', color='Étape en cours', title="Dossiers ouverts — de la première étape à aujourd'hui")
            fig_g.update_layout(height=max(320, 24 * len(_g) + 90), margin=dict(l=10, r=10, t=30, b=10), yaxis={'autorange': 'reversed'})
            st.plotly_chart(fig_g, use_container_width=True, key='gantt_prosp')
        if nb_bloq or nb_retard:
            st.warning(f"🔴 **{nb_bloq} prospect(s)** sans activité depuis ≥ {SEUILS['prospection_stalle_jours']} jours — à relancer en priorité (motif pré-rempli selon l'étape, dernier point du journal dans le tableau)." + (f' ⏰ **{nb_retard}** ont dépassé le jalon de leur étape (colonne « Retard (j) »).' if nb_retard else ''))
        st.markdown('#### Détails prospects')
        fp1, fp2, fp3 = st.columns([1, 1, 2])
        with fp1:
            f_stat = st.selectbox('Statut', ['Tous', 'Non démarré', 'En cours', 'Clôturé'], key='pip_statut')
        with fp2:
            f_bloq = st.checkbox('🔴 Bloqués seulement', key='pip_bloq')
        with fp3:
            f_q = st.text_input('Rechercher un prospect', '', key='pip_q')
        m_p = pd.Series(True, index=dfp.index)
        if f_stat != 'Tous':
            m_p &= dfp['AVANCEMENT2'].fillna('').str.strip() == f_stat
        if f_bloq and 'Situation' in dfp.columns:
            m_p &= dfp['Situation'].str.startswith('🔴')
        if f_q.strip() and 'conventions en cours' in dfp.columns:
            m_p &= dfp['conventions en cours'].fillna('').str.lower().str.contains(f_q.strip().lower(), regex=False)
        cols_pip = ['conventions en cours', 'Situation', 'AVANCEMENT2', 'Scénario', 'RANKING', 'contacts', 'EMAIL', 'Date début', 'Date fin', 'Durée (j)', 'Étape atteinte', 'Étape en cours', 'Jours étape', 'Cible (j)', 'Retard (j)', 'Dernière activité', 'Sans mouvement (j)', 'Relance suggérée', 'CA potentiel (CRM)', 'CA réalisé (CRM)', 'Motif blocage (suggéré)', 'Dernier point', 'Commentaires']
        cols_exist = [c for c in cols_pip if c in dfp.columns]
        st.caption(f"{int(m_p.sum())} prospect(s) affiché(s) — « Motif blocage » est pré-rempli selon l'étape bloquée (+ dernier point du journal) : recopiez-le dans le registre ci-dessous pour le suivi éditable.")
        st.dataframe(dfp[m_p][cols_exist], use_container_width=True, hide_index=True, height=420)
        _exp_pip = dfp[m_p][cols_exist].copy()
        _stamp = datetime.now().strftime('%Y%m%d')
        _x1, _x2 = st.columns(2)
        with _x1:
            st.download_button('📤 Export CSV — vue affichée', _exp_pip.to_csv(sep=';', index=False, encoding='utf-8-sig'), file_name=f'relance_pipeline_{_stamp}.csv', mime='text/csv', key='dl_pip_csv')
        with _x2:
            _buf = BytesIO()
            with pd.ExcelWriter(_buf, engine='openpyxl') as _w:
                _exp_pip.to_excel(_w, sheet_name='Pipeline', index=False)
            st.download_button('📤 Export Excel — vue affichée', _buf.getvalue(), file_name=f'relance_pipeline_{_stamp}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_pip_xls')
        st.divider()
    data_dir = os.path.join(ctx.base_dir, 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    csv_path = os.path.join(data_dir, 'conventions_signees.csv')
    if not os.path.exists(csv_path):
        st.info('Fichier data/conventions_signees.csv introuvable.')
    else:
        if 'registry_base_sha' not in st.session_state:
            st.session_state['registry_base_sha'] = file_sha(csv_path)
        df_sig = pd.read_csv(csv_path, sep=';')
        for _c in ('date_fin', 'motif_blocage', 'prochaine_relance', 'historique'):
            if _c not in df_sig.columns:
                df_sig[_c] = ''
            df_sig[_c] = df_sig[_c].fillna('')
        if df_sig.empty or 'code' not in df_sig.columns:
            st.info('CSV vide ou mal formatte.')
        else:
            cf1, cf2, cf3, cf4 = st.columns([1, 1, 1, 1])
            with cf1:
                sf = st.selectbox('Filtrer par statut', ['Tous', 'Prospection', 'Negociation', 'En cours', 'Finalisation', 'Signe', 'Finalise', 'Refuse', 'Archive'])
            with cf2:
                q = st.text_input('Rechercher un client', '')
            with cf3:
                only_bloq = st.checkbox('🔴 Bloqués uniquement')
            with cf4:
                only_relance = st.checkbox('📩 Relance due')
            today = pd.Timestamp.now()
            mask = pd.Series(True, index=df_sig.index)
            if sf != 'Tous':
                mask &= df_sig['statut'].fillna('').str.strip() == sf
            if q.strip():
                mask &= df_sig['client'].fillna('').str.lower().str.contains(q.strip().lower())
            if only_bloq:
                mask &= (df_sig['motif_blocage'].fillna('').str.strip() != '') & ~df_sig['statut'].fillna('').str.strip().isin(STATUTS_CLOS)
            if only_relance:
                _pr = pd.to_datetime(df_sig['prochaine_relance'], errors='coerce')
                mask &= _pr.notna() & (_pr <= today) & ~df_sig['statut'].fillna('').str.strip().isin(STATUTS_CLOS)
            df_filt = df_sig[mask].copy()
            rows_data = []
            tot_j = 0
            stats = {}
            for _, r in df_filt.iterrows():
                d = pd.NaT
                f = pd.NaT
                if pd.notna(r.get('date_debut_prospection', '')):
                    d = pd.Timestamp(r['date_debut_prospection'])
                _fin = r.get('date_fin', '')
                if pd.notna(_fin) and str(_fin).strip():
                    f = pd.to_datetime(_fin, errors='coerce')
                elif pd.notna(r.get('date_signature', '')):
                    f = pd.Timestamp(r['date_signature'])
                dur = (f - d).days if pd.notna(f) and pd.notna(d) else (today - d).days if pd.notna(d) else 0
                tot_j += dur
                s = str(r.get('statut', '')).strip()
                stats[s] = stats.get(s, 0) + 1
                _pr = r.get('prochaine_relance', '')
                _pr = str(_pr) if pd.notna(_pr) and str(_pr).strip() else ''
                _js = conv.jours_dans_statut(r, today.date())
                _cib_s = JALONS_STATUTS.get(s)
                _ret_s = _js - _cib_s if _js is not None and _cib_s and (_js > _cib_s) and (s not in STATUTS_CLOS) else None
                rows_data.append({'Client': r['client'], 'Statut': s, 'Debut': str(d.date()) if pd.notna(d) else '-', 'Fin': str(f.date()) if pd.notna(f) else '-', 'Delai (j)': dur, 'Modifs': int(r.get('nb_modifications', 0)), 'Motif blocage': str(r.get('motif_blocage', '') or '').strip(), 'Relance': _pr, 'J statut': _js, 'Retard statut': _ret_s, 'Notes': str(r.get('notes', ''))})
            if len(rows_data) > 0:
                dm = round(tot_j / len(rows_data), 1)
                ss = ' | '.join([f'{s}: {c}' for s, c in sorted(stats.items())])
                nb_bloq_reg = int(sum((1 for r in rows_data if r['Motif blocage'] and r['Statut'] not in STATUTS_CLOS)))
                c1, c2, c3, c4 = st.columns(4)
                c1.metric('Projets', len(rows_data))
                c2.metric('Delai moyen', f'{dm} jrs')
                c3.metric('🔴 Bloqués', nb_bloq_reg)
                c4.caption(ss)
                _dues = sum((1 for r in rows_data if r['Relance'] and r['Statut'] not in STATUTS_CLOS and (r['Relance'] <= today.date().isoformat())))
                _ret_s_nb = sum((1 for r in rows_data if r['Retard statut'] is not None))
                _proch = min([r['Relance'] for r in rows_data if r['Relance'] and r['Statut'] not in STATUTS_CLOS], default='')
                k1, k2, k3, k4 = st.columns(4)
                k1.metric('📩 Relances dues', _dues)
                k2.metric('⏰ Retard de jalon', _ret_s_nb)
                k3.metric('📅 Prochaine relance', _proch or '—')
                k4.caption('jalons statuts (jours max) : ' + ' · '.join((f'{k_} {v_}' for k_, v_ in JALONS_STATUTS.items())))
                _ouverts = [r for r in rows_data if r['Statut'] not in STATUTS_CLOS]
                if _ouverts:
                    _top = sorted(_ouverts, key=lambda r: r['Delai (j)'], reverse=True)[:5]
                    st.markdown('#### ⏳ Relances prioritaires')

                    def _ligne_relance(r):
                        bits = []
                        if r['Motif blocage']:
                            bits.append(f"🔴 {r['Motif blocage']}")
                        if r['Retard statut'] is not None:
                            bits.append(f"⏰ +{r['Retard statut']} j de jalon")
                        if r['Relance']:
                            bits.append(f"📩 avant le {r['Relance']}")
                        return f"- **{r['Client']}** — {r['Statut']} depuis **{r['Delai (j)']} j**" + ('' if not bits else ' — ' + ' · '.join(bits))
                    st.markdown('\n'.join((_ligne_relance(r) for r in _top)))
                _sans_fin = [r for r in rows_data if r['Statut'] in {'Signe', 'Finalise', 'Refuse'} and r['Fin'] == '-']
                if _sans_fin:
                    st.info(f'📅 {len(_sans_fin)} projet(s) clôturé(s) sans date de fin — complétez la colonne « Fin » puis sauvegardez.')
            st.markdown('#### Edition')
            df_edit = df_filt.copy()
            df_edit['_idx'] = df_filt.index
            df_edit['Client'] = df_edit['client']
            df_edit['Statut'] = df_edit['statut']
            df_edit['Debut'] = df_edit['date_debut_prospection'].fillna('-')
            df_edit['Fin'] = [d.date() if pd.notna(d) else None for d in pd.to_datetime(df_edit['date_fin'], errors='coerce')]
            df_edit['Delai (j)'] = 0
            df_edit['Modifs'] = df_edit['nb_modifications'].fillna(0).astype(int)
            df_edit['Motif blocage'] = df_edit['motif_blocage'].fillna('')
            df_edit['Relance'] = [d.date() if pd.notna(d) else None for d in pd.to_datetime(df_edit['prochaine_relance'], errors='coerce')]
            df_edit['Archiver'] = False
            df_edit['Notes'] = df_edit['notes']
            for i in df_edit.index:
                r = df_edit.loc[i]
                d = pd.NaT
                f = pd.NaT
                if pd.notna(r.get('date_debut_prospection', '')):
                    d = pd.Timestamp(r['date_debut_prospection'])
                _fin = r.get('date_fin', '')
                if pd.notna(_fin) and str(_fin).strip():
                    f = pd.to_datetime(_fin, errors='coerce')
                elif pd.notna(r.get('date_signature', '')):
                    f = pd.Timestamp(r['date_signature'])
                dur = (f - d).days if pd.notna(f) and pd.notna(d) else (today - d).days if pd.notna(d) else 0
                df_edit.at[i, 'Delai (j)'] = dur
            edited = st.data_editor(df_edit[['Client', 'Statut', 'Debut', 'Fin', 'Delai (j)', 'Modifs', 'Motif blocage', 'Relance', 'Notes', 'Archiver', '_idx']], column_config={'Client': st.column_config.TextColumn('Client', disabled=True), 'Statut': st.column_config.SelectboxColumn('Statut', options=STATUTS_CONVENTION, help='Liste fermée (data/config.py STATUTS_CONVENTION) : ' + ', '.join(STATUTS_CONVENTION)), 'Debut': st.column_config.TextColumn('Debut', disabled=True), 'Fin': st.column_config.DateColumn('Fin', format='DD/MM/YYYY', help='Date de fin de prospection (signature ou clôture) — stockée en AAAA-MM-JJ'), 'Delai (j)': st.column_config.NumberColumn('Delai (j)', disabled=True), 'Modifs': st.column_config.NumberColumn('Modifs', disabled=True), 'Motif blocage': st.column_config.TextColumn('Motif blocage', width='large', help='Pourquoi le dossier est bloqué — requis pour le filtre 🔴 Bloqués uniquement'), 'Relance': st.column_config.DateColumn('Relance', format='DD/MM/YYYY', help='Prochaine relance programmée — filtre 📩 Relance due'), 'Notes': st.column_config.TextColumn('Notes', width='large'), 'Archiver': st.column_config.CheckboxColumn('Archiver'), '_idx': st.column_config.NumberColumn('_idx', disabled=True, width='small')}, use_container_width=True, hide_index=True, key='editor_conv')
            if edited is not None and '_idx' in edited.columns:
                ca, cb = st.columns([1, 3])
                with ca:
                    if st.button('Sauvegarder les modifications'):
                        modifs = 0
                        for _, row in edited.iterrows():
                            oidx = int(row['_idx'])
                            if oidx in df_sig.index:
                                code = str(df_sig.at[oidx, 'code']).strip()
                                _vf = row.get('Fin')
                                _date_fin = str(_vf) if _vf is not None and pd.notna(_vf) else ''
                                _vr = row.get('Relance')
                                _relance = str(_vr) if _vr is not None and pd.notna(_vr) else ''
                                if conv.update_convention(code, statut=str(row.get('Statut', '')).strip(), notes=str(row.get('Notes', '')), date_fin=_date_fin, motif_blocage=str(row.get('Motif blocage', '') or '').strip(), prochaine_relance=_relance):
                                    modifs += 1
                        if modifs:
                            if _sync_registre('update(data): modifications conventions [auto]', 'Modifications sauvegardees et synchronisees sur GitHub !'):
                                st.rerun()
                        else:
                            st.info('Aucune modification.')
                with cb:
                    to_arch = [int(r['_idx']) for _, r in edited.iterrows() if r.get('Archiver', False)]
                    if to_arch:
                        st.warning(f'{len(to_arch)} projet(s) a archiver')
                        if st.button("Confirmer l'archivage"):
                            for idx in to_arch:
                                if idx in df_sig.index:
                                    conv.update_convention(str(df_sig.at[idx, 'code']).strip(), statut='Archive')
                            if _sync_registre('update(data): archivage convention [auto]', f'{len(to_arch)} projet(s) archive(s) et synchronise(s) sur GitHub !'):
                                st.rerun()
            if stats:
                st.markdown('#### Repartition par statut')
                df_chart = pd.DataFrame({'Statut': list(stats.keys()), 'Nombre': list(stats.values())})
                colors = COLORS_STATUTS
                fig = px.bar(df_chart, x='Statut', y='Nombre', color='Statut', color_discrete_map=colors, text='Nombre', height=280)
                fig.update_traces(textposition='outside')
                fig.update_layout(margin=dict(l=10, r=10, t=10, b=10))
                st.plotly_chart(fig, use_container_width=True, key='chart_statut')
            _gop = df_filt[~df_filt['statut'].fillna('').str.strip().isin(STATUTS_CLOS)].copy()
            if not _gop.empty:
                _gop['Début'] = pd.to_datetime(_gop['date_debut_prospection'], errors='coerce')
                _f_g = pd.to_datetime(_gop['date_fin'], errors='coerce')
                _f_g = _f_g.fillna(pd.to_datetime(_gop['date_signature'], errors='coerce')).fillna(today)
                _gop['Fin'] = _f_g.where(_f_g >= _gop['Début'], _gop['Début'] + pd.Timedelta(days=1))
                _gop['Client'] = _gop['client'].astype(str).str.slice(0, 45)
                _gop = _gop.dropna(subset=['Début']).sort_values('Début')
                if not _gop.empty:
                    fig_gg = px.timeline(_gop, x_start='Début', x_end='Fin', y='Client', color='statut', color_discrete_map=COLORS_STATUTS, title="Projets ouverts — du lancement à aujourd'hui")
                    fig_gg.update_layout(height=max(300, 26 * len(_gop) + 90), margin=dict(l=10, r=10, t=30, b=10), yaxis={'autorange': 'reversed'})
                    st.plotly_chart(fig_gg, use_container_width=True, key='gantt_reg')
            st.markdown('#### 📜 Historique des statuts')
            _rows_h = []
            for _, r_ in df_filt.iterrows():
                _ent = conv.parse_historique(r_.get('historique', ''))
                for _i, (_d, _a, _n) in enumerate(_ent):
                    _nxt = _ent[_i + 1][0] if _i + 1 < len(_ent) else None
                    _rows_h.append({'Client': r_['client'], 'De': _a, 'Vers': _n, 'Date': _d, 'Durée (j)': (_nxt - _d).days if _nxt else (today.date() - _d).days})
            if _rows_h:
                df_h = pd.DataFrame(_rows_h).sort_values('Date', ascending=False)
                h1, h2 = st.columns([3, 2])
                with h1:
                    st.dataframe(df_h, use_container_width=True, hide_index=True, height=300)
                with h2:
                    _agg = df_h.groupby(['De', 'Vers'])['Durée (j)'].agg(Nb='count', Moy='mean').reset_index()
                    _agg['Transition'] = _agg['De'] + ' → ' + _agg['Vers']
                    _agg['Moy'] = _agg['Moy'].round(0).astype(int)
                    st.dataframe(_agg[['Transition', 'Nb', 'Moy']].rename(columns={'Moy': 'Durée moy (j)'}), use_container_width=True, hide_index=True)
            else:
                st.caption("Aucun changement de statut enregistré — l'historique se remplit automatiquement à chaque sauvegarde de statut.")
            if rows_data:
                st.markdown('#### 📤 Export — liste de relance')
                _stamp_r = datetime.now().strftime('%Y%m%d')
                _exp_reg = pd.DataFrame(rows_data)[['Client', 'Statut', 'Debut', 'Fin', 'Delai (j)', 'Motif blocage', 'Relance', 'J statut', 'Retard statut', 'Modifs', 'Notes']]
                _xr1, _xr2 = st.columns(2)
                with _xr1:
                    st.download_button('📤 Export CSV — liste de relance', _exp_reg.to_csv(sep=';', index=False, encoding='utf-8-sig'), file_name=f'relance_registre_{_stamp_r}.csv', mime='text/csv', key='dl_reg_csv')
                with _xr2:
                    _buf2 = BytesIO()
                    with pd.ExcelWriter(_buf2, engine='openpyxl') as _w2:
                        _exp_reg.to_excel(_w2, sheet_name='Relance', index=False)
                    st.download_button('📤 Export Excel — liste de relance', _buf2.getvalue(), file_name=f'relance_registre_{_stamp_r}.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', key='dl_reg_xls')
            st.markdown('#### Ajouter un projet')
            with st.expander('Nouvelle convention'):
                with st.form('conv_form'):
                    x1, x2 = st.columns(2)
                    with x1:
                        nc = st.text_input('Client')
                        ns = st.selectbox('Statut', ['Prospection', 'Negociation', 'En cours', 'Finalisation', 'Signe', 'Finalise', 'Refuse'])
                    with x2:
                        nd = st.date_input('Debut prospection', value=today)
                        nv = st.text_input('Scenario', '01-Prive avec Amicale')
                    x3, x4 = st.columns(2)
                    with x3:
                        nf = st.text_input('Date fin (AAAA-MM-JJ, vide si ouvert)', '')
                    with x4:
                        nm = st.selectbox('Motif blocage', MOTIFS_BLOCAGE)
                    x5, x6 = st.columns(2)
                    with x5:
                        nr = st.text_input('Prochaine relance (AAAA-MM-JJ, vide)', '')
                    with x6:
                        nt = st.text_input('Notes (optionnel)', '')
                    _dates_ok = True
                    for _val, _lbl in ((nf, 'Date fin'), (nr, 'Prochaine relance')):
                        if _val.strip():
                            try:
                                datetime.strptime(_val.strip(), '%Y-%m-%d')
                            except ValueError:
                                st.error(f'{_lbl} attendue au format AAAA-MM-JJ.')
                                _dates_ok = False
                    if _dates_ok and st.form_submit_button('Ajouter'):
                        new_code = nc.upper().replace(' ', '_')[:20] if nc else 'NOUVEAU'
                        conv.register_convention(new_code, nc, scenario=nv, garantie='', statut=ns, date_debut_prospection=str(nd), date_fin=nf.strip(), motif_blocage='' if nm == '(aucun)' else nm, prochaine_relance=nr.strip(), notes=nt)
                        if _sync_registre('update(data): nouvelle convention [auto]', f'Ajoute : {nc}'):
                            st.rerun()