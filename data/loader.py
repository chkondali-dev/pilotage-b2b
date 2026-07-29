"""
Chargement des données depuis GitHub avec cache Streamlit.
"""
import requests
import pandas as pd
from io import BytesIO
import streamlit as st
from data.config import GITHUB_RAW, FILES, CRM_URL


@st.cache_data(show_spinner=False, ttl=3600)
def _fetch(url: str) -> bytes:
    """HTTP fetch avec cache 1h — évite les re-téléchargements."""
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    """Nettoie les colonnes : supprime les sauts de ligne, strip."""
    df.columns = df.columns.str.replace("\n", " ").str.strip()
    for col in df.select_dtypes("object").columns:
        df[col] = df[col].astype(str).str.strip()
    return df


def _filter_conventions(df: pd.DataFrame) -> pd.DataFrame:
    """Exclut les entrées avec des noms individuels dans la colonne Convention."""
    from data.config import NOMS_INDIVIDUELS
    if df.empty or "Nom" not in df.columns:
        return df
    return df[~df["Nom"].str.upper().str.strip().isin(NOMS_INDIVIDUELS)].copy()


@st.cache_data(show_spinner=False, ttl=3600)
def load_all_data() -> dict:
    """Charge tous les fichiers Excel depuis GitHub, retourne un dict de DataFrames."""
    dfs: dict = {}
    for key, fname in FILES.items():
        try:
            raw = _fetch(GITHUB_RAW + fname)
            if key == "conventions_signees":
                dfs["conventions_signees"] = _clean(
                    pd.read_excel(BytesIO(raw), engine="openpyxl", sheet_name="Conventions signées")
                )
                dfs["conventions_en_cours"] = _clean(
                    pd.read_excel(BytesIO(raw), engine="openpyxl", sheet_name="convention en cours", skiprows=12)
                )
            else:
                dfs[key] = _clean(pd.read_excel(BytesIO(raw), engine="openpyxl"))
        except Exception as exc:
            st.sidebar.warning(f"⚠️ Fichier {key} : {exc}")
            dfs[key] = pd.DataFrame()
    return dfs


@st.cache_data(show_spinner=False, ttl=3600)
def load_crm() -> pd.DataFrame | None:
    """Charge CRM depuis GitHub avec le parser crm.py. Retourne None si indisponible."""
    try:
        raw = _fetch(CRM_URL)
        import crm as _crm
        return _crm.load_crm_data(source=BytesIO(raw))
    except Exception:
        return None
