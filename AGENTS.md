# Pilotage B2B — Knowledge Base

**Stack:** Python 3.14, Streamlit, Pandas, NumPy, Plotly, Requests
**Entry:** `app.py` (1684 lignes, architecture modulaire)

## Structure
```
pilotage_b2b/
├── app.py              # Bootstrap + 9 tabs Streamlit
├── data/               # Configuration, chargement, transformations
│   ├── config.py       # Constantes : GITHUB_RAW, FILES, palette C, MOIS
│   ├── loader.py       # _fetch, load_all_data, _clean
│   └── transforms.py   # _add_date_cols, _map_magasins, prepare_data
├── metrics/kpi.py      # 9 fonctions métier (CA, évolutions, risque, inactivité)
├── charts/factory.py   # 10 constructeurs Plotly (bar, line, gauge, waterfall…)
├── ui/components.py    # inject_css, hero, section, badge, rank_card
├── utils/github.py     # push_csv_to_github (Streamlit → GitHub API)
├── memory/             # Système mémoire local SQLite + embeddings
├── monthly_report.py   # Génération rapport mensuel IA
├── trend_analyzer.py   # Détection tendances + alertes
├── crm.py              # Module CRM (lecture TDC2.xlsx)
└── trend_alert_panel.py# Rendu UI des alertes
```

## Conventions
- **Palette sémantique** : `C["green"]` = croissance, `C["red"]` = déclin/alerte, `C["blue"]` = année N, `C["slate"]` = année N-1
- **Cache Streamlit** : `@st.cache_data` sur toutes les fonctions de chargement (TTL=3600) + préparations lourdes
- **Comparaisons date-à-date** : N-1 tronqué aux mêmes jours exacts que N — SOURCE UNIQUE `truncate_n1_date_to_date` dans `metrics/kpi.py` (utilisée par `compare_years_date_to_date`, `convention_risk_matrix` et `monthly_report.py`). Ne JAMAIS réimplémenter cette troncature ailleurs (dérive des chiffres garantie)
- **Noms individuels** : 4 entrées filtrées des vues Convention via `NOMS_INDIVIDUELS` dans `data/config.py`
- **Seuil d'inactivité** : 60j défaut, réglable via slider sidebar (15-180j)

## Antipatterns
- Ne PAS utiliser 30j comme seuil d'inactivité (faux positifs)
- Ne JAMAIS mettre de valeurs en dur pour les couleurs ou seuils (utiliser `C` dict)

## Commandes
```bash
streamlit run app.py                          # Lancer le dashboard
python monthly_report.py --month N --year Y   # Générer rapport mensuel
```

## Modules connexes
- `mempalace/` — Mémoire à long terme structurée
- `superpowers/` — Skills additionnels
- `full-stack-fastapi-template/` — Template API (projet séparé)
