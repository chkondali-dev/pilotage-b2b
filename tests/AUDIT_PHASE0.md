# Phase 0 — Audit et baseline

Snapshot figé : `tests/fixtures/` (7 fichiers de `2025/`, servis par GitHub raw).
Date de référence des tests : **2026-10-05**. Commande : `python -m pytest tests/`
(équivalent de `pytest tests/` — le raccourci `pytest` n'est pas dans le PATH de ce shell).

## Architecture réelle (15 lignes)

1. `suite.py` — portail Streamlit : 2 cartes → `pages/dashboard.py` et `pages/contrat_lab.py`.
2. `pages/dashboard.py` — wrapper de 15 lignes (`runpy.run_path("app.py")`), source unique = `app.py`.
3. `app.py` (3 377 lignes, CRLF) — dashboard : sidebar filtres (Année/Mois/Type/Convention/Seuil),
   chargement, pré-calculs `st.cache_data`, **10 onglets `st.tabs`** (tout est exécuté à chaque rerun).
4. `data/loader.py` — téléchargement GitHub raw (`FILES` de `data/config.py`), cache 1 h, `_filter_conventions`.
5. `data/transforms.py` — `prepare_data()` retourne 9 DataFrames (vc, credit, edc, conv, code, credit_part,
   cube, prospection, crm) ; `enrich_prospection()` pour le pipeline ; `ajoute_crm()`.
6. `data/config.py` — `SEUILS`, `MOIS`, `JALONS`/`JALONS_STATUTS`, `FILES`, `TYPES_CONVENTION` ✔ conforme.
7. `metrics/kpi.py` (934 lignes) — date-à-date (`ca_sum_date_to_date`, `truncate_n1_date_to_date`),
   matrice risque, inactivité (`inactive_conventions`), volumes/panier, pont, cohortes, conformité 40 %.
8. `charts/factory.py` — wrappers Plotly ; `ui/components.py` — CSS + `hero/section/badge/rank_card/kpi_card`.
9. `business/conventions.py` — registre unique `data/conventions_signees.csv` (écriture + historique statuts).
10. `utils/github.py` — `push_csv_to_github()` via API (retour bool, écrit sur `main`, commit « [auto] »).
11. `trend_analyzer.py` + `trend_alert_panel.py` — scan de tendances (onglet 7), JSON d'état dans `data/`.
12. `monthly_report.py` (1 475 lignes, + `monthly_report_v2.py`) — rapport IA en sous-processus Python
    (CLI `--api-key`, argparse l.1451), écrit `~/Downloads/rapport_mensuel`.
13. `crm.py` — parsing CRM (`TDC2.xlsx`), consommé par `prepare_data` (onglet 6).
14. Données brutes versionnées : `2025/*.xlsx` (VC, conso, EDC, particulier, TDC, codes, cube).
15. Divergences vs contexte : **aucune structurelle** ; le contexte est confirmé, voir ci-dessous les
    réserves sur les points 0.1-0.4. `pytest` n'est pas sur le PATH → `python -m pytest tests/`.

## 0.1 — `suite.py` → `pages/dashboard.py` : wrapper, pas copie divergente

`pages/dashboard.py` = 15 lignes : `runpy.run_path(str(ROOT / "app.py"))`. Ce n'est **ni une copie ni
une divergence** : source unique = `app.py`. Seule singularité : le docstring de `suite.py` dit
« Dashboard → app.py » alors que `st.page_link` pointe `pages/dashboard.py` (qui exécute app.py).
**Proposition (non appliquée)** : garder le wrapper comme seule porte d'entrée (état actuel),
corriger éventuellement le docstring de `suite.py` en Phase 1 si vous le souhaitez.

## 0.2 — Double comptage « Global » (chiffré sur snapshot)

Flux et chevauchement par **N° de facture** (après pipeline complet `prepare_data`) :

| paire | N° en commun |
|---|---|
| vc ∩ credit conso | 0 |
| vc ∩ credit particulier | 0 |
| credit conso ∩ credit particulier | 0 |
| vc ∩ EDC | 0 |
| credit conso ∩ EDC | 0 |
| **EDC ∩ credit particulier** | **531 / 531** |

- **Les 531 factures EDC (1 109 135,54 TND) sont un sous-ensemble exact de `CREDIT PARTICULIER.xlsx`**
  (mêmes N°, même date, même montant, même client). `Type vente à crédit` = `VC.PARTIC.` dans les deux.
- **Le filtre « Global » ne double PAS** (vc + credit + credit_part, EDC non concaténé) : EDC comptée 1×.
- **Double comptage réel ailleurs** : l'expander « Consolidation multi-sources » (app.py ~l.1624) concat
  vc + credit + part + **edc** → 45 018 lignes dont **1 062 lignes = 2 × 531**, soit
  **+1 109 135,54 TND comptés deux fois** dans cet écran.
- Mutuelles : extraits de `df_credit` par filtre nom (`_lens_meta`), jamais re-concaténés → pas de double.
- Clients (N° Client) partagés entre flux : 47 (vc/conso), 92 (vc/part), 506 (conso/part) → clients
  réellement multi-flux, cumul cohérent en Global (pas un doublon de facture).
- Impact : **aucun sur les KPI** ; écart chiffré **uniquement dans l'expander Consolidation** du tab
  Magasins. Correctif proposé (Phase 3, arbitrage requis) : retirer `vc_edc` de `sources` OU retirer
  les N° EDC de `credit_particulier` dans cet écran.

## 0.3 — `_cached_precalcs` : `_df_conv_ref` exclu du hachage

`def _cached_precalcs(df, annee, seuil, mois_tuple, _df_conv_ref)` (app.py l.328) : le préfixe `_`
exclut `_df_conv_ref` du hash `st.cache_data`. `nb_total = len(_df_conv_ref)` (l.338) peut donc
**devenir périmé**. Scénario : mise à jour du classeur `TDC CONVENTION 1.xlsm` sur GitHub (ajout ou
suppression d'une convention) → `load_all_data` (TTL 1 h) finit par livrer le nouveau `df_conv`,
mais `_cached_precalcs` n'est **pas recalculé** : aucune entrée hachée (df, année, seuil, mois) n'a
changé. `nb_total` reste affiché à l'ancienne valeur (fallback « / N total » du KPI « Conventions
actives », l.408 — visible uniquement quand `Top3 %` est NaN) jusqu'au prochain changement de filtre
ou au clic « 🔄 Actualiser » (`st.cache_data.clear()`), voire jusqu'au redéploiement sur Streamlit
Cloud. Valeur actuelle figée : **93 conventions signées**.

## 0.4 — « Dynamique du portefeuille » ignore Type de vente et Mois (confirmé, chiffré)

La section (app.py l.553-601) reconstruit `_all = concat(vc, credit, credit_part)` puis filtre
**seulement** `Année ∈ [annee_sel-1, annee_sel]` — elle ignore `type_vente_sel` **et** `mois_sel`,
contrairement aux KPI voisins « Indicateurs clés » (k1-k4, l.386-409, calculés sur `df_vc_filt`).
Écarts « Conventions actives » affiché vs section Dynamique (mêmes données) :

| filtre Type de vente (année 2026) | KPI voisin | Dynamique | écart |
|---|---|---|---|
| Convention | 78 | 4 060 | **+3 982** |
| Credit conso | 6 | 4 060 | **+4 054** |
| Credit particulier | 3 976 | 4 060 | +84 |
| Global (mois vides) | 4 060 | 4 060 | 0 |

Filtre Mois ignoré (type Global, année 2026) : mois jan-avr → KPI 1 610 vs Dynamique 4 060
(**+2 450**) ; mois sept. → KPI 314 vs 4 060 (**+3 746**). La Dynamique affiche en plus
« Moy. actives/mois » (468,6 en 2026) et « Nouvelles YTD », calculés sur le périmètre 3 flux.
Correctif proposé (Phase 3, arbitrage requis) : construire `_all` depuis `df_vc_filt` sur l'année
sélectionnée seulement, ou annoter explicitement la section « périmètre tous flux, hors filtres ».

## 0.5 — Livrables

- `tests/fixtures/` — snapshot des 7 fichiers de données (~14,7 Mo).
- `tests/baseline.json` — CA N, CA N-1, nb factures, panier moyen, conventions actives, CA à risque
  × 4 types de vente × 2025/2026 (seuil 60 j, mois vide, convention « Tous », date 2026-10-05).
- `tests/baseline_lib.py` + `tests/conftest.py` — environnement hors-ligne (aucun réseau,
  aucun `push_csv_to_github`), horloge figée.
- `tests/make_baseline.py` — régénération (uniquement après validation d'un changement de chiffres).
- `tests/test_baseline.py` — non-régression ; `tests/test_audit_phase0.py` — constats 0.1-0.4 figés.
