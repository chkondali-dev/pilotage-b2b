"""
Transformations et préparation des données.
"""
import pandas as pd
import streamlit as st
from data.config import NOMS_INDIVIDUELS
from data.loader import _filter_conventions


def _add_date_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Extrait Année / Mois / Jour depuis 'Date comptabilisation'."""
    date_col = next(
        (c for c in df.columns if "date" in c.lower() and "comptabil" in c.lower()), None
    )
    if date_col is None:
        return df
    df = df.copy()
    df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["Année"] = df["Date"].dt.year.astype("Int64")
    df["Mois"] = df["Date"].dt.month.astype("Int64")
    df["Jour"] = df["Date"].dt.day.astype("Int64")
    return df


def _map_magasins(df: pd.DataFrame, code_df: pd.DataFrame) -> pd.DataFrame:
    """Mapping code Navision → nom magasin + enseigne."""
    if len(df) == 0:
        return df
    df = df.copy()
    df["Enseigne"] = "MG"
    df["Magasin"] = "Inconnu"
    if code_df.empty:
        return df
    code_df = code_df.copy()
    code_df.columns = code_df.columns.str.strip()
    code_col_src = next((c for c in df.columns if c.lower() == "unite code"), None)
    if not code_col_src:
        return df
    code_col = list(code_df.columns)[0]
    unite_col = list(code_df.columns)[2]

    def get_ense(unit):
        s = str(unit).upper()
        return "BATAM" if "BATAM" in s or "BTM" in s else "MG"

    code_df["Enseigne"] = code_df[unite_col].apply(get_ense)
    code_df[code_col] = code_df[code_col].astype(str).str.strip()
    mapping_nom = code_df.set_index(code_col)[unite_col].to_dict()
    mapping_ense = code_df.set_index(code_col)["Enseigne"].to_dict()
    df[code_col_src] = df[code_col_src].astype(str).str.strip()
    df["Magasin"] = df[code_col_src].map(mapping_nom).fillna(df[code_col_src])
    df["Enseigne"] = df[code_col_src].map(mapping_ense).fillna("MG")
    return df


def load_cube_magasin(df_raw: pd.DataFrame, code_df: pd.DataFrame = None) -> pd.DataFrame:
    """Parse CUBE MAGASIN — extract BC code, map to Unite name, melt to long format."""
    if code_df is None:
        code_df = pd.DataFrame()
    if df_raw.empty:
        return pd.DataFrame()
    df_raw = df_raw.copy()
    df_raw.columns = df_raw.columns.str.strip()
    header_row = None
    for i, val in enumerate(df_raw.iloc[:, 0]):
        if pd.notna(val) and ("étiquettes" in str(val) or "lignes" in str(val).lower()):
            header_row = i
            break
    if header_row is None:
        return pd.DataFrame()
    headers = df_raw.iloc[header_row].tolist()
    data = df_raw.iloc[header_row + 1:].copy()
    data.columns = headers
    data = data.rename(columns={headers[0]: "Date"})
    data = data[data["Date"].notna()].copy()
    bc_to_unite = {}
    if not code_df.empty:
        code_df = code_df.copy()
        bc_col = next(
            (c for c in code_df.columns if "business" in c.lower() or "central" in c.lower()), None
        )
        unite_col = next(
            (
                c
                for c in code_df.columns
                if c not in [bc_col, code_df.columns[0], "enseigne"] and "code" not in c.lower()
            ),
            None,
        )
        if bc_col and unite_col:
            code_df[bc_col] = pd.to_numeric(code_df[bc_col], errors="coerce")
            bc_to_unite = code_df.dropna(subset=[bc_col]).set_index(bc_col)[unite_col].to_dict()

    def map_store_name(store_name):
        s = str(store_name).strip()
        parts = s.split(" - ")
        if len(parts) >= 1:
            try:
                bc_code = float(parts[0])
                if bc_code in bc_to_unite:
                    return bc_to_unite[bc_code].strip()
            except ValueError:
                pass
        if " - " in s:
            return s.split(" - ", 1)[1].strip()
        return s

    store_cols = [c for c in data.columns if c != "Date" and pd.notna(c)]
    data_long = data.melt(
        id_vars=["Date"], value_vars=store_cols, var_name="StoreRaw", value_name="CA Magasin"
    )
    data_long["Magasin"] = data_long["StoreRaw"].apply(map_store_name)
    data_long["Date"] = pd.to_datetime(data_long["Date"], errors="coerce")
    data_long["Année"] = data_long["Date"].dt.year
    data_long["Mois"] = data_long["Date"].dt.month
    data_long = data_long.dropna(subset=["Date", "CA Magasin"])
    data_long["CA Magasin"] = pd.to_numeric(data_long["CA Magasin"], errors="coerce").fillna(0)
    return data_long[["Date", "Magasin", "CA Magasin", "Année", "Mois"]]


def _compute_ca_realise(df_crm: pd.DataFrame, df_vc: pd.DataFrame) -> pd.DataFrame:
    """Match chaque prospect CRM au CA facturé dans VC par convention name."""
    if df_crm.empty or df_vc.empty:
        return df_crm
    df_crm = df_crm.copy()
    vc_ca = (
        df_vc.groupby("Nom")["Montant TTC"]
        .sum()
        .reset_index()
        .rename(columns={"Nom": "Nom entreprise", "Montant TTC": "CA realise"})
    )
    df_crm["Nom entreprise key"] = (
        df_crm["Nom entreprise"].fillna("").str.strip().str.lower()
    )
    vc_ca["Nom entreprise key"] = (
        vc_ca["Nom entreprise"].fillna("").str.strip().str.lower()
    )
    ca_map = vc_ca.set_index("Nom entreprise key")["CA realise"].to_dict()
    df_crm["CA realise"] = (
        df_crm["Nom entreprise key"].map(ca_map).fillna(0).round(2)
    )
    df_crm = df_crm.drop(columns=["Nom entreprise key"])
    return df_crm


@st.cache_data(show_spinner=False)
def prepare_data(_raw: dict) -> tuple:
    """
    Point d'entrée unique pour tout le processing.
    Retourne (df_vc, df_credit, df_edc, df_conv, code_df, df_credit_part, df_cube_mag, df_prospection).
    """
    code_df = _raw.get("code_magasin", pd.DataFrame())
    df_vc = _filter_conventions(
        _map_magasins(_add_date_cols(_raw.get("vc", pd.DataFrame())), code_df)
    )
    df_credit = _filter_conventions(
        _map_magasins(_add_date_cols(_raw.get("vc_credit", pd.DataFrame())), code_df)
    )
    df_edc = _map_magasins(_add_date_cols(_raw.get("vc_edc", pd.DataFrame())), code_df)
    if "Nbr_Mois_Échance" in df_edc.columns:
        df_edc = df_edc.rename(columns={"Nbr_Mois_Échance": "Nbr_Mois_Echance"})
    df_conv = _raw.get("conventions_signees", pd.DataFrame())
    df_prospection = _raw.get("conventions_en_cours", pd.DataFrame())
    df_credit_part = _map_magasins(
        _add_date_cols(_raw.get("credit_particulier", pd.DataFrame())), code_df
    )
    df_cube_mag = load_cube_magasin(_raw.get("cube_magasin", pd.DataFrame()), code_df)

    # CRM — chargé séparément via GitHub, parsé par crm.py
    from data.loader import load_crm
    df_crm = load_crm()
    if df_crm is not None:
        df_crm = _compute_ca_realise(df_crm, df_vc)
    return df_vc, df_credit, df_edc, df_conv, code_df, df_credit_part, df_cube_mag, df_prospection, df_crm
