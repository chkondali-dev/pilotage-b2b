from data.config import MOIS
from pathlib import Path
from metrics.kpi import color_delta
from metrics.kpi import fmt_pct
import json
import logging
import streamlit as st


logger = logging.getLogger(__name__)


def render(ctx):
    st.markdown('### 📂 Archive des Rapports Mensuels')
    archive_path = Path(ctx.base_dir) / '.cache_monthly' / 'report_archive.json'
    if not archive_path.exists():
        st.info("Aucun rapport archive pour l'instant. Utilisez `python monthly_report.py` pour generer un rapport.")
    else:
        try:
            archive = json.loads(archive_path.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, ValueError):
            archive = []
        if not archive:
            st.info('Archive vide.')
        else:
            periodes = sorted(set(((e['annee'], e['mois']) for e in archive)), reverse=True)
            col1, col2 = st.columns([1, 3])
            with col1:
                selected = st.selectbox('Periode', options=[f'{MOIS.get(m, m)} {a}' for a, m in periodes], index=0)
            with col2:
                st.markdown(f'**{len(archive)} rapport(s)** archive(s)')
            selected_entries = [e for e in archive if f"{MOIS.get(e['mois'], e['mois'])} {e['annee']}" == selected]
            for entry in reversed(selected_entries):
                filename = entry.get('filename', '?')
                ts = entry.get('timestamp', '')[:16].replace('T', ' ')
                kpi = entry.get('kpi', {})
                exec_summary = entry.get('exec_summary')
                with st.container(border=True):
                    cols = st.columns([3, 1, 1])
                    with cols[0]:
                        st.markdown(f'**{filename}**  \nGenere le {ts}')
                    with cols[1]:
                        st.metric('CA Total', f"{kpi.get('ca_total', 0):,.0f}")
                    with cols[2]:
                        var = kpi.get('var_total', 0)
                        st.metric('Variation', fmt_pct(var), delta_color=color_delta(var))
                    if exec_summary and exec_summary.get('tendance_globale'):
                        tg = exec_summary['tendance_globale']
                        st.markdown(f"**Tendance :** {tg.get('texte', '')}  \nDirection: {tg.get('direction', '?').upper()} — Intensite: {tg.get('intensite', '?')}")
                        points = exec_summary.get('points_cles', [])
                        if points:
                            for p in points:
                                st.markdown(f'- {p}')
                    report_dir = Path.home() / 'Downloads' / 'rapport_mensuel'
                    html_file = report_dir / filename
                    if html_file.exists():
                        with open(html_file, 'r', encoding='utf-8') as fh:
                            html_content = fh.read()
                        st.download_button(label='📥 Telecharger le rapport HTML', data=html_content, file_name=filename, mime='text/html', key=f'dl_{filename}')
                    else:
                        st.caption(f'Fichier non trouve: {html_file.name}')
                    try:
                        _rel = html_file.relative_to(Path(ctx.base_dir))
                        st.markdown(f'[Ouvrir le rapport](./{_rel})')
                    except ValueError:
                        logger.debug('Rapport hors arborescence — lien relatif non affiché')