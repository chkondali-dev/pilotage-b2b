"""Contexte figé passé à chaque onglet — Phase 2.

construit dans app.py (filtres, slices, _cached_precalcs) et passé tel quel
aux ui/tabs/<nom>.render(ctx). Immuable (frozen) : les onglets lisent, ne
mutent jamais (les copies sont faites dans les render).
"""
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class TabCtx:
    # DataFrames préparés (bruts)
    df_vc: Any
    df_credit: Any
    df_credit_part: Any
    df_edc: Any
    df_conv: Any
    code_df: Any
    df_cube_mag: Any
    df_prospection: Any
    df_crm: Any
    # Slices filtrés
    df_vc_filt: Any
    df_vc_scope: Any
    df_filt: Any
    # Filtres sidebar
    annee_sel: int
    mois_sel: list
    conv_sel: str
    type_vente_sel: str
    seuil_inactif: int
    objectif_m: float
    # Résultats de _cached_precalcs
    df_comp: Any
    risk_mat: Any
    df_inactive: Any
    df_3m: Any
    ca_n: float
    ca_n1: float
    ev_nn1: float
    ca_n2: float
    ev_n1n2: float
    nb_actives: int
    nb_inact: int
    nb_total: int
    nb_declin_fort: int
    nb_inactif_cv: int
    nb_croissance: int
    lens_labels: list
    # Base projet (remplace Path(__file__).parent dans les modules d'onglets)
    base_dir: str = ""
