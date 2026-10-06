"""
Audit Phase 0 — constats 0.1 a 0.4 figes en tests (chiffres sur fixtures).

0.1  suite.py -> pages/dashboard.py est un wrapper vers app.py (source unique).
0.2  Double comptage : EDC inclus dans CREDIT PARTICULIER ; le Global ne double
     pas, mais l'expander « Consolidation multi-sources » oui.
0.3  _cached_precalcs : _df_conv_ref exclu du hachage (prefixe _).
0.4  « Dynamique du portefeuille » ignore Type de vente et Mois.
"""
from pathlib import Path

import pandas as pd

from baseline_lib import ROOT_DIR, slice_type_vente

APP = ROOT_DIR / "app.py"
SUITE = ROOT_DIR / "suite.py"
PAGE_DASH = ROOT_DIR / "pages" / "dashboard.py"


# ── 0.1 — pages/dashboard.py : wrapper, pas une copie ────────────

def test_01_dashboard_page_is_wrapper():
    content = PAGE_DASH.read_text(encoding="utf-8")
    assert "runpy.run_path" in content and "app.py" in content, (
        "pages/dashboard.py n'est plus un wrapper vers app.py — "
        "divergence de source unique a arbitrer"
    )
    # Une copie divergente ferait des milliers de lignes, pas ~15.
    assert len(content.splitlines()) < 50


def test_01_suite_links_to_pages_dashboard():
    assert "pages/dashboard.py" in SUITE.read_text(encoding="utf-8")


# ── 0.2 — double comptage chiffré ───────────────────────────────

def test_02_flux_disjoint_except_edc_in_credit_part(prepared):
    """Les 4 flux sont disjoints par N° de facture SAUF edc ⊂ credit_particulier."""
    df_vc, df_credit, df_edc, _conv, _code, df_credit_part, *_ = prepared

    def nums(df):
        return set(df["N°"].astype(str))

    nv, nc = nums(df_vc), nums(df_credit)
    np_, ne = nums(df_credit_part), nums(df_edc)

    assert len(nv & nc) == 0
    assert len(nv & np_) == 0
    assert len(nc & np_) == 0
    assert len(ne & nv) == 0
    assert len(ne & nc) == 0
    # Les 531 factures EDC existent aussi dans CREDIT PARTICULIER.
    assert ne == ne & np_
    assert len(ne) == 531


def test_02_edc_amount_shared_with_credit_part(prepared):
    """Montant commun EDC / credit_particulier : 1 109 135,54 TND."""
    _vc, _credit, df_edc, *_rest = prepared
    df_credit_part = prepared[5]

    inter = set(df_edc["N°"].astype(str)) & set(df_credit_part["N°"].astype(str))
    montant = float(
        df_edc[df_edc["N°"].astype(str).isin(inter)]["Montant TTC"].sum()
    )
    assert abs(montant - 1_109_135.54) <= 0.5


def test_02_global_counts_edc_once_but_consolidation_doubles(prepared):
    """Global (vc+credit+part) = EDC 1x ; l'expander Consolidation (+edc) = 2x."""
    df_vc, df_credit, df_edc, _conv, _code, df_credit_part, *_ = prepared
    ne = set(df_edc["N°"].astype(str))

    global_ = pd.concat([df_vc, df_credit, df_credit_part], ignore_index=True)
    in_global = global_[global_["N°"].astype(str).isin(ne)]
    assert len(in_global) == 531, "EDC doive etre comptee 1x dans le Global"

    # Reproduction du concat de l'expander (app.py ~1624).
    consol = pd.concat([df_vc, df_credit, df_credit_part, df_edc], ignore_index=True)
    mask = consol["N°"].astype(str).isin(ne)
    assert int(mask.sum()) == 1062, "les 531 EDC sont doublees dans la consolidation"
    montant = float(consol[mask]["Montant TTC"].sum())
    assert abs(montant - 2_218_271.07) <= 1.0


# ── 0.3 — _df_conv_ref exclu du hachage ─────────────────────────

def test_03_precacls_excludes_df_conv_from_hash():
    src = APP.read_text(encoding="utf-8")
    assert "def _cached_precalcs(df, annee, seuil, mois_tuple, _df_conv_ref)" in src
    assert "nb_t  = len(_df_conv_ref)" in src, (
        "nb_total n'est plus calcule depuis _df_conv_ref — revoir l'audit 0.3"
    )
    # Le parametre prefiche _ est ignore par st.cache_data : nb_total peut
    # devenir perime (scenario documente dans AUDIT_PHASE0.md).
    assert "_df_conv_ref".startswith("_")


def test_03_df_conv_line_count_frozen(prepared):
    """Valeur actuelle de nb_total sur le snapshot : 93 conventions signees."""
    df_conv = prepared[3]
    assert len(df_conv) == 93


# ── 0.4 — Dynamique du portefeuille ignore les filtres ──────────

def test_04_dynamique_ignores_type_vente(prepared):
    """Périmètre de la Dynamique (toujours vc+credit+part) vs KPI voisin."""
    df_vc, df_credit, _edc, _conv, _code, df_credit_part, *_ = prepared
    all3 = pd.concat([df_vc, df_credit, df_credit_part], ignore_index=True)

    cases = [
        # (type, annee, kpi_actives, dynamique_actives)
        ("Convention", 2026, 78, 4060),
        ("Convention", 2025, 77, 5001),
        ("Credit conso", 2026, 6, 4060),
        ("Credit conso", 2025, 4, 5001),
        ("Credit particulier", 2026, 3976, 4060),
        ("Credit particulier", 2025, 4921, 5001),
        ("Global", 2026, 4060, 4060),
        ("Global", 2025, 5001, 5001),
    ]
    for type_sel, annee, exp_kpi, exp_dyn in cases:
        d = slice_type_vente(type_sel, df_vc, df_credit, df_credit_part)
        kpi = d[d["Année"] == annee]["Nom"].dropna().nunique()
        dyn = all3[all3["Année"] == annee]["Nom"].dropna().nunique()
        assert (kpi, dyn) == (exp_kpi, exp_dyn), (
            f"{type_sel}/{annee}: attendu KPI={exp_kpi} Dynamique={exp_dyn}, "
            f"obtenu KPI={kpi} Dynamique={dyn}"
        )


def test_04_dynamique_ignores_mois(prepared):
    """Même avec Global, la Dynamique ignore le filtre Mois des KPI voisins."""
    df_vc, df_credit, _edc, _conv, _code, df_credit_part, *_ = prepared
    all3 = pd.concat([df_vc, df_credit, df_credit_part], ignore_index=True)
    g = slice_type_vente("Global", df_vc, df_credit, df_credit_part)

    dyn = all3[all3["Année"] == 2026]["Nom"].dropna().nunique()
    kpi_jan_mars = g[(g["Année"] == 2026) & (g["Mois"].isin([1, 2, 3]))][
        "Nom"
    ].dropna().nunique()
    kpi_sept = g[(g["Année"] == 2026) & (g["Mois"] == 9)]["Nom"].dropna().nunique()

    assert dyn == 4060
    assert kpi_jan_mars == 1610          # KPI voisin filtre : écart 2450
    assert kpi_sept == 314               # KPI voisin filtre : écart 3746
