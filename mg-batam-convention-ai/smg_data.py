"""
smg_data.py — Chargement autonome des données de facturation SMG pour convention-ai.

Réplique le strict nécessaire de data/loader + data/transforms du dashboard
(dont le projet est indépendant) : fetch GitHub raw + préparation des colonnes
Date/Année/Mois/Jour, mapping magasins, filtre des noms individuels.

Seuls les fichiers nécessaires aux KPIs de renouvellement sont chargés (vc, code_magasin).
"""

import requests
import pandas as pd
from io import BytesIO

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"

FILES = {
    "vc": "Factures%20ventes%20enregistr%C3%A9es%20VC%20(4).xlsx",
    "code_magasin": "Code%20MAGASIN%20Business%20Central.xlsx",
}

NOMS_INDIVIDUELS = {"AHMED ABIDI", "AMARA MISSAOUI", "BILEL BEN AMMAR", "MED KAIS SMAILI"}


def _fetch(url: str) -> bytes:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = df.columns.str.replace("\n", " ").str.strip()
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def _add_date_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Extrait Année / Mois / Jour depuis 'Date comptabilisation' (même logique que le dashboard)."""
    date_col = next(
        (c for c in df.columns if "date" in c.lower() and "comptabil" in c.lower()), None)
    if date_col is None:
        return df
    df = df.copy()
    df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["Année"] = df["Date"].dt.year.astype("Int64")
    df["Mois"] = df["Date"].dt.month.astype("Int64")
    df["Jour"] = df["Date"].dt.day.astype("Int64")
    return df


def _map_magasins(df: pd.DataFrame, code_df: pd.DataFrame) -> pd.DataFrame:
    """Mapping code Navision → nom magasin + enseigne (même logique que le dashboard)."""
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
    unite_col = list(code_df.columns)[2] if len(code_df.columns) > 2 else list(code_df.columns)[1]

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


def _filter_conventions(df: pd.DataFrame) -> pd.DataFrame:
    """Exclut les entrées avec des noms individuels dans la colonne Convention."""
    if df.empty or "Nom" not in df.columns:
        return df
    return df[~df["Nom"].str.upper().str.strip().isin(NOMS_INDIVIDUELS)].copy()


def load_vc() -> pd.DataFrame:
    """Charge les factures VC préparées (dates + magasins + filtre individus).

    Dégradation silencieuse : DataFrame vide si le réseau échoue.
    """
    try:
        raw_vc = _clean(pd.read_excel(BytesIO(_fetch(GITHUB_RAW + FILES["vc"])),
                                      engine="openpyxl"))
        raw_code = _clean(pd.read_excel(BytesIO(_fetch(GITHUB_RAW + FILES["code_magasin"])),
                                        engine="openpyxl"))
        return _filter_conventions(_map_magasins(_add_date_cols(raw_vc), raw_code))
    except Exception:
        return pd.DataFrame()
