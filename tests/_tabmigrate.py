
TABS = {
    0: ("tab0_executive.py", 426, 673),
    1: ("tab1_tendances.py", 679, 987),
    2: ("tab2_conventions.py", 993, 1392),
    3: ("tab3_magasins.py", 1398, 1842),
    4: ("tab4_lens.py", 1848, 2485),
    5: ("tab5_conventions.py", 2491, 3068),
    6: ("tab6_crm.py", 3070, 3139),
    7: ("tab7_alertes.py", 3141, 3209),
    8: ("tab8_archive.py", 3214, 3295),
    9: ("tab9_conformite.py", 3300, 3446),
}

# Dependances externes par onglet (analyse AST : charges module non stockees
# localement, hors builtins/imports) — source de verite pour ctx et imports.
EXT0 = ["annee_sel", "ca_n", "ca_n1", "df_comp", "df_credit", "df_credit_part",
        "df_filt", "df_inactive", "df_vc", "df_vc_filt", "df_vc_scope", "ev_nn1",
        "mois_sel", "nb_actives", "nb_inact", "nb_total", "objectif_m",
        "risk_mat", "seuil_inactif"]
EXT1 = ["annee_sel", "ca_n", "ca_n1", "df_3m", "df_comp", "df_vc",
        "df_vc_filt", "df_vc_scope", "mois_sel"]
EXT2 = ["annee_sel", "conv_sel", "df_credit", "mois_sel", "nb_inact",
        "risk_mat", "type_vente_sel"]
EXT3 = ["annee_sel", "code_df", "df_credit", "df_credit_part", "df_cube_mag",
        "df_edc", "df_vc", "df_vc_filt", "mois_sel"]
EXT4 = ["LENS_LABELS", "_lens_meta", "mois_sel"]
EXT5 = ["REGISTRY_CSV_REL", "_registry_sha_now", "_sync_registre", "df_crm",
        "df_prospection"]
EXT6 = ["df_crm"]
EXT7 = ["_cached_scan_all", "annee_sel", "code_df", "df_conv", "df_edc",
        "df_vc", "df_vc_filt", "mois_sel"]
EXT8 = []
EXT9 = ["annee_sel", "df_credit_part", "df_vc"]

"""Migration Phase 2 : AST tab -> module render(c)."""


NB_TAB = 10

CTX_FIELDS = [
    "df_vc", "df_credit", "df_credit_part", "df_edc", "df_conv", "code_df",
    "df_cube_mag", "df_prospection", "df_crm",
    "df_vc_filt", "df_vc_scope", "df_filt",
    "annee_sel", "mois_sel", "conv_sel", "type_vente_sel", "seuil_inactif",
    "objectif_m",
    "df_comp", "risk_mat", "df_inactive", "df_3m", "ca_n", "ca_n1", "ev_nn1",
    "ca_n2", "ev_n1n2", "nb_actives", "nb_inact", "nb_total",
    "nb_declin_fort", "nb_inactif_cv", "nb_croissance",
    "vol", "conc", "lens_labels", "base_dir",
]

# Strategie generateur (_gen_tabs) :
#  - parse AST de app.py ; pour chaque With tabs[i] : copie profonde du corps,
#    renomme les Name externes (cf. RENAMES[i]) en attributs `c.<champ>`,
#    ajuste `__file__` -> c.base_dir, ecrit ui/tabs/<mod>.py avec imports.
#  - verifie : compile OK + aucun Name externe hors (c.*/imports/builtins/locaux).
RENAMES = {
    0: {"df_filt": "c.df_filt", "df_comp": "c.df_comp_tab0",
        "risk_mat": "c.risk_mat_tab0", "df_inactive": "c.df_inactive_tab0",
        "ca_n": "c.ca_n_tab0", "ca_n1": "c.ca_n1_tab0", "ev_nn1": "c.ev_nn1_tab0",
        "nb_actives": "c.nb_actives_tab0", "nb_inact": "c.nb_inact_tab0",
        "nb_total": "c.nb_total_tab0"},
    1: {"df_comp": "c.df_comp_tab1", "ca_n": "c.ca_n_tab1",
        "ca_n1": "c.ca_n1_tab1"},
    2: {"ca_total_n": "c.ca_total_n_tab2", "ca_total_n1": "c.ca_total_n1_tab2",
        "ev_total": "c.ev_total_tab2", "nb_convs": "c.nb_convs_tab2",
        "nb_risky": "c.nb_risky_tab2", "df_filt": "c.df_filt",
        "risk_mat": "c.risk_mat_tab2", "nb_inact": "c.nb_inact_tab2"},
    3: {},
    4: {"LENS_LABELS": "c.lens_labels"},
    5: {"df_filt": "c.df_filt"},
    6: {"df_crm": "c.df_crm"},
    7: {"df_vc": "c.df_vc_tab7", "ca_n": "c.ca_n_tab7",
        "ca_n1": "c.ca_n1_tab7"},
    8: {},
    9: {"df_vc": "c.df_vc_tab9", "df_credit_part": "c.df_credit_part_tab9"},
}

# _vol0/_conc0/mois_label : reconstruits localement dans tab0 et tab1
# (meme code qu'aujourd'hui, base sur df_vc_filt/annee_sel/mois_sel/MOIS).
# (Les autres champs ctx existent déjà via CTX_FIELDS à l'exception de
#  df_comp_tab0/risk_mat_tab0/df_inactive_tab0/ca_n_tab0/... ajoutés ci-dessous.)
CTX_FIELDS += [
    "df_comp_tab0", "risk_mat_tab0", "df_inactive_tab0",
    "ca_n_tab0", "ca_n1_tab0", "ev_nn1_tab0",
    "nb_actives_tab0", "nb_inact_tab0", "nb_total_tab0",
    "df_comp_tab1", "ca_n_tab1", "ca_n1_tab1",
    "df_filt", "ca_total_n_tab2", "ca_total_n1_tab2", "ev_total_tab2",
    "nb_convs_tab2", "nb_risky_tab2", "risk_mat_tab2", "nb_inact_tab2",
    "df_vc_tab7", "ca_n_tab7", "ca_n1_tab7",
    "df_vc_tab9", "df_credit_part_tab9",
]

# Imports par module (analyse AST : seuls les noms utilises, sans le superflu).
MOD_IMPORTS = {
    0: ["st", "pd", "C", "MOIS", "go", "section", "rank_card", "fmt_pct",
        "color_delta", "evol_pct", "volumes_panier", "concentration_portefeuille",
        "chart_line_compare", "chart_grouped_bar", "chart_bar",
        "chart_variation_bar", "chart_risk_table", "ventes_positives",
        "business_insights", "run_rate_fin_annee", "objectif_tracking",
        "chart_gauge", "bridge_volume_panier", "narratif_executif"],
    1: ["st", "pd", "np", "px", "go", "timedelta", "datetime", "C", "MOIS",
        "SEUILS", "section", "fmt_pct", "color_delta", "chart_line_compare",
        "chart_variation_bar", "chart_bar", "chart_gauge", "evol_pct",
        "bridge_volume_panier", "chart_bridge", "run_rate_fin_annee"],
    2: ["st", "pd", "np", "px", "C", "MOIS", "section", "fmt_pct", "color_delta",
        "evol_pct", "ca_sum_date_to_date", "chart_bar", "chart_variation_bar",
        "chart_risk_table", "cohortes_conventions", "badge",
        "conversion_conventions", "kpi_conversion_globale",
        "compare_years_date_to_date", "chart_grouped_bar", "chart_line_compare",
        "chart_pie", "truncate_n1_date_to_date"],
    3: ["st", "pd", "np", "px", "go", "C", "MOIS", "section", "fmt_pct",
        "color_delta", "evol_pct", "truncate_n1_date_to_date",
        "compare_years_date_to_date"],
    4: ["st", "pd", "np", "px", "go", "C", "MOIS", "SEUILS", "section",
        "kpi_card", "fmt_pct", "color_delta", "evol_pct", "chart_grouped_bar",
        "chart_line_compare", "chart_bar", "chart_variation_bar", "chart_pie",
        "compare_years_date_to_date", "truncate_n1_date_to_date"],
    5: ["st", "pd", "px", "BytesIO", "datetime", "os", "SEUILS", "JALONS_STATUTS",
        "PROSP_ETAPES", "STATUTS_CONVENTION", "enrich_prospection",
        "ajoute_crm", "conv", "push_csv_to_github", "file_sha"],
    6: ["st", "px"],
    7: ["st", "evol_pct", "render_alert_panel", "section"],
    8: ["st", "json", "Path", "MOIS", "fmt_pct", "color_delta", "logger"],
    9: ["st", "pd", "SEUILS", "section", "alertes_achats_repetes",
        "chart_stacked_bar"],
}

IMPORT_LINES = {
    "st": "import streamlit as st",
    "pd": "import pandas as pd",
    "np": "import numpy as np",
    "px": "import plotly.express as px",
    "go": "import plotly.graph_objects as go",
    "datetime": "from datetime import datetime",
    "timedelta": "from datetime import timedelta",
    "os": "import os",
    "json": "import json",
    "BytesIO": "from io import BytesIO",
    "Path": "from pathlib import Path",
    "logger": "import logging\nlogger = logging.getLogger(__name__)",
    "C": "from data.config import C",
    "MOIS": "from data.config import MOIS",
    "SEUILS": "from data.config import SEUILS",
    "STATUTS_CONVENTION": "from data.config import STATUTS_CONVENTION",
    "JALONS_STATUTS": "from data.config import JALONS_STATUTS",
    "PROSP_ETAPES": "from data.transforms import PROSP_ETAPES",
    "ajoute_crm": "from data.transforms import ajoute_crm",
    "enrich_prospection": "from data.transforms import enrich_prospection",
    "bridge_volume_panier": "from metrics.kpi import bridge_volume_panier",
    "business_insights": "from metrics.kpi import business_insights",
    "ca_sum_date_to_date": "from metrics.kpi import ca_sum_date_to_date",
    "cohortes_conventions": "from metrics.kpi import cohortes_conventions",
    "color_delta": "from metrics.kpi import color_delta",
    "compare_years_date_to_date": "from metrics.kpi import compare_years_date_to_date",
    "concentration_portefeuille": "from metrics.kpi import concentration_portefeuille",
    "conversion_conventions": "from metrics.kpi import conversion_conventions",
    "evol_pct": "from metrics.kpi import evol_pct",
    "fmt_pct": "from metrics.kpi import fmt_pct",
    "kpi_conversion_globale": "from metrics.kpi import kpi_conversion_globale",
    "narratif_executif": "from metrics.kpi import narratif_executif",
    "objectif_tracking": "from metrics.kpi import objectif_tracking",
    "run_rate_fin_annee": "from metrics.kpi import run_rate_fin_annee",
    "truncate_n1_date_to_date": "from metrics.kpi import truncate_n1_date_to_date",
    "ventes_positives": "from metrics.kpi import ventes_positives",
    "volumes_panier": "from metrics.kpi import volumes_panier",
    "alertes_achats_repetes": "from metrics.kpi import alertes_achats_repetes",
    "chart_bar": "from charts.factory import chart_bar",
    "chart_bridge": "from charts.factory import chart_bridge",
    "chart_gauge": "from charts.factory import chart_gauge",
    "chart_grouped_bar": "from charts.factory import chart_grouped_bar",
    "chart_line_compare": "from charts.factory import chart_line_compare",
    "chart_pie": "from charts.factory import chart_pie",
    "chart_risk_table": "from charts.factory import chart_risk_table",
    "chart_stacked_bar": "from charts.factory import chart_stacked_bar",
    "chart_variation_bar": "from charts.factory import chart_variation_bar",
    "section": "from ui.components import section",
    "badge": "from ui.components import badge",
    "rank_card": "from ui.components import rank_card",
    "kpi_card": "from ui.components import kpi_card",
    "conv": "import business.conventions as conv",
    "file_sha": "from utils.github import file_sha",
    "push_csv_to_github": "from utils.github import push_csv_to_github",
    "render_alert_panel": "from trend_alert_panel import render_alert_panel",
}

# --- generateur ---
import ast as _ast
import copy as _copy
import io as _io
import pathlib as _pathlib


def _rename(node, mapping):
    """Renomme les Name externes en attributs c.<champ> (token-exact via AST)."""
    for n in _ast.walk(node):
        if isinstance(n, _ast.Name) and n.id in mapping:
            field = mapping[n.id][2:]  # retire le prefixe "c."
            n2 = _ast.parse(mapping[n.id], mode="eval").body
            _ast.copy_location(n2, n)
            n.id, n.ctx = None, None  # neutralise avant remplacement
            return None
    return None


class _Renamer(_ast.NodeTransformer):
    def __init__(self, mapping):
        self.mapping = mapping

    def visit_Name(self, node):
        if node.id in self.mapping:
            new = _ast.parse(self.mapping[node.id], mode="eval").body
            return _ast.copy_location(new, node)
        return node


def _gen_tabs():
    root = _pathlib.Path(r"C:\Users\hachk\pilotage_b2b")
    src = _io.open(root / "app.py", encoding="utf-8").read()
    tree = _ast.parse(src)
    withs = [n for n in tree.body if isinstance(n, _ast.With) and any(
        isinstance(i.context_expr, _ast.Subscript)
        and isinstance(i.context_expr.value, _ast.Name)
        and i.context_expr.value.id == "tabs" for i in n.items)]
    assert len(withs) == NB_TAB, len(withs)
    for node in withs:
        idx = [i.context_expr.slice.value for i in node.items
               if isinstance(i.context_expr, _ast.Subscript)][0]
        mod, _, _ = TABS[idx]
        body = _copy.deepcopy(node.body)
        new_body = _Renamer(RENAMES[idx]).visit(_ast.Module(body=body, type_ignores=[]))
        _ast.fix_missing_locations(new_body)
        code = _ast.unparse(new_body)
        # __file__ (racine projet) -> base_dir du contexte
        code = code.replace("Path(__file__).parent", "Path(c.base_dir)")
        code = code.replace("os.path.dirname(__file__)", "c.base_dir")
        header = "\n".join(IMPORT_LINES[h] for h in MOD_IMPORTS[idx])
        text = header + "\n\n\ndef render(c):\n" + "\n".join(
            ("    " + ln if ln.strip() else "") for ln in code.splitlines()) + "\n"
        (root / "ui" / "tabs" / mod).write_text(text, encoding="utf-8")
        print("OK", mod)



if __name__ == "__main__":
    _gen_tabs()
