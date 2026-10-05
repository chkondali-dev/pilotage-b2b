"""
Transformations et préparation des données.
"""
import re
import unicodedata
from datetime import datetime

import pandas as pd
import streamlit as st
from data.config import NOMS_INDIVIDUELS, JALONS, JALONS_SCENARIOS
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
    df[code_col_src] = df[code_col_src].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
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
    _ech_credit = next((c for c in df_credit.columns if c.startswith("Nbr_Mois_Ech")), None)
    if _ech_credit and _ech_credit != "Nbr_Mois_Echance":
        df_credit = df_credit.rename(columns={_ech_credit: "Nbr_Mois_Echance"})
    df_edc = _map_magasins(_add_date_cols(_raw.get("vc_edc", pd.DataFrame())), code_df)
    _ech_edc = next((c for c in df_edc.columns if c.startswith("Nbr_Mois_Ech")), None)
    if _ech_edc and _ech_edc != "Nbr_Mois_Echance":
        df_edc = df_edc.rename(columns={_ech_edc: "Nbr_Mois_Echance"})
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


# ══════════════════════════════════════════════════════════════
# Onglet « Conventions encours » — enrichissement prospection
# ══════════════════════════════════════════════════════════════

# Étapes du pipeline (colonnes du sheet Excel « convention en cours »).
PROSP_ETAPES = [
    ("Prise de contact", "date prise de contact"),
    ("Validation client", "date validation client"),
    ("Juridique", "date juridique"),
    ("Finance", "date fianance"),
    ("Signature", "date signature"),
]

# Entrées horodatées du journal COMMENTAIRE : [24/06/2025 08:52] texte…
_JOURNAL_RE = re.compile(
    r"\[(\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2})\](.*?)"
    r"(?=\[\d{1,2}/\d{1,2}/\d{4}\s+\d{1,2}:\d{2}\]|\Z)",
    re.S,
)


def _parse_journal(txt) -> tuple:
    """Dernière entrée horodatée d'un journal → (Timestamp, texte nettoyé)."""
    if not isinstance(txt, str) or not txt.strip():
        return pd.NaT, ""
    entries = []
    for m in _JOURNAL_RE.finditer(txt.replace("_x000D_", "\n")):
        try:
            d = datetime.strptime(m.group(1), "%d/%m/%Y %H:%M")
        except ValueError:
            continue
        body = " ".join(m.group(2).split()).strip(" -|")
        if body:
            entries.append((pd.Timestamp(d), body))
    if not entries:
        return pd.NaT, ""
    d, body = max(entries, key=lambda e: e[0])
    return d, body[:160]


# ── Scénarios, jalons et motifs de blocage ─────────────────────

# Motif pré-rempli selon l'étape où le prospect est bloqué (idée « calcul auto du motif »).
_MOTIF_ETAPES = {
    "Prise de contact": "Prise de contact non effectuée",
    "Validation client": "En attente de validation client",
    "Juridique": "Bloqué côté juridique",
    "Finance": "Bloqué côté financier",
    "Signature": "En attente de signature",
}


def _norm_txt(s) -> str:
    """Minuscules, sans accents, espaces réduits — clé de comparaison de noms."""
    nfkd = unicodedata.normalize("NFKD", str(s or ""))
    return " ".join(nfkd.encode("ascii", "ignore").decode().lower().split())


def scenario_prospect(nom: str) -> str:
    """Numéro de scénario (01/03/04/07) d'un prospect — heurique sur le nom.

    Utilisé pour appliquer les bons JALONS (data/config.py) aux prospects du
    pipeline qui n'ont pas de champ « scenario » dans le sheet Excel.
    """
    n = _norm_txt(nom)
    if "amicale" in n:
        return "04"
    if "mutuelle" in n:
        return "07"
    if any(k in n for k in ("ministere", "commune", "municipalite", "administration",
                            "prefecture", "gouvernorat", "direction regional")):
        return "03"
    return "01"


def _tokens_txt(s) -> set:
    """Tokens significatifs (≥3 lettres, hors mots vides) pour le match de noms."""
    stop = {"les", "des", "une", "societe", "sarl", "sas", "le", "la", "de", "du", "et", "el"}
    return {t for t in re.split(r"[^a-z0-9]+", _norm_txt(s)) if len(t) >= 3 and t not in stop}


def ajoute_crm(df: pd.DataFrame, df_crm: pd.DataFrame) -> pd.DataFrame:
    """Colle CA potentiel / CA réalisé du CRM sur les prospects du pipeline.

    Match : 1) égalité normalisée du nom  2) ≥ 2 tokens communs (≥3 lettres).
    Colonnes ajoutées « CA potentiel (CRM) » / « CA réalisé (CRM) » (NaN si pas de match).
    """
    if df is None or df.empty or "conventions en cours" not in df.columns:
        return df
    df = df.copy()
    df["CA potentiel (CRM)"] = float("nan")
    df["CA réalisé (CRM)"] = float("nan")
    if df_crm is None or df_crm.empty or "Nom entreprise" not in df_crm.columns:
        return df
    crm = df_crm.copy()
    crm["_tok"] = crm["Nom entreprise"].map(_tokens_txt)
    by_norm = {}
    tok_idx = []
    for i, row in crm.iterrows():
        nn = _norm_txt(row["Nom entreprise"])
        if nn and nn not in by_norm:
            by_norm[nn] = i
        tok_idx.append((row["_tok"], i))
    ca_p = "CA potentiel" if "CA potentiel" in crm.columns else None
    ca_r = "CA realise" if "CA realise" in crm.columns else None
    for idx, nom in df["conventions en cours"].items():
        hit = by_norm.get(_norm_txt(nom))
        if hit is None:
            nt = _tokens_txt(nom)
            if nt and tok_idx:
                best = max(tok_idx, key=lambda p: len(nt & p[0]))
                if len(nt & best[0]) >= 2:
                    hit = best[1]
        if hit is not None:
            if ca_p:
                df.at[idx, "CA potentiel (CRM)"] = crm.at[hit, ca_p]
            if ca_r:
                df.at[idx, "CA réalisé (CRM)"] = crm.at[hit, ca_r]
    return df


def enrich_prospection(df: pd.DataFrame, seuil_stalle: int = 30,
                       relance_jours: int = 14) -> pd.DataFrame:
    """Colonnes calculées de suivi pour l'onglet Conventions encours.

    Ajoute : Date début, Date fin, Durée (j), Étape atteinte/en cours,
    Jours étape, Scénario + Cible/Retard (jalons par scénario, data/config.py),
    Dernière activité, Dernier point, Sans mouvement (j), Relance suggérée,
    Situation (🟢/🟡/🔴) et Motif blocage (suggéré, pré-rempli selon l'étape).

    Seuil d'inactivité = SEUILS["prospection_stalle_jours"] ; délai entre deux
    relances = SEUILS["relance_jours"] (data/config.py).
    """
    if df is None or df.empty or "conventions en cours" not in df.columns:
        return pd.DataFrame()
    df = df.copy()
    nom = df["conventions en cours"]
    df = df[nom.notna() & (nom.astype(str).str.strip() != "")].reset_index(drop=True)

    date_cols = [c for _, c in PROSP_ETAPES if c in df.columns]
    for c in date_cols:
        df[c] = pd.to_datetime(df[c], errors="coerce")
    dates = df[date_cols] if date_cols else pd.DataFrame(index=df.index)
    today = pd.Timestamp.now().normalize()

    # Date début = première date d'étape atteinte ; Date fin = date de signature
    # (ou dernière date d'étape si clôturé sans date de signature renseignée).
    df["Date début"] = dates.min(axis=1) if date_cols else pd.Series(pd.NaT, index=df.index)
    if "date signature" in df.columns:
        df["Date fin"] = df["date signature"].copy()
    else:
        df["Date fin"] = pd.Series(pd.NaT, index=df.index)
    if "AVANCEMENT2" in df.columns and date_cols:
        clot = (df["AVANCEMENT2"].fillna("").str.strip().str.lower().eq("clôturé")
                & df["Date fin"].isna())
        df.loc[clot, "Date fin"] = dates.max(axis=1)[clot]

    df["Durée (j)"] = (df["Date fin"].fillna(today) - df["Date début"]).dt.days.where(
        df["Date début"].notna()
    )

    # Étapes franchies / étape en cours / jours depuis la dernière étape
    def _etapes(row):
        atteinte, en_cours = "—", None
        for nom_etape, col in PROSP_ETAPES:
            if col not in df.columns:      # colonne absente du sheet → étape inconnue
                continue
            if pd.isna(row.get(col)):
                if en_cours is None:
                    en_cours = nom_etape
            else:
                atteinte = nom_etape
        return pd.Series([atteinte, en_cours or "Terminé"])

    if date_cols:
        df[["Étape atteinte", "Étape en cours"]] = df.apply(_etapes, axis=1)
        df["Jours étape"] = (today - dates.max(axis=1)).dt.days.where(
            dates.notna().any(axis=1)
        )
    else:
        df["Étape atteinte"] = "—"
        df["Étape en cours"] = "—"
        df["Jours étape"] = pd.Series(pd.NA, index=df.index, dtype="Int64")

    # Jalons par scénario : cible de l'étape en cours + retard (jours au-delà)
    df["Scénario"] = df["conventions en cours"].map(
        lambda n: JALONS_SCENARIOS.get(scenario_prospect(n), JALONS_SCENARIOS["01"]))

    def _cible(row):
        etape = str(row.get("Étape en cours", "") or "")
        if etape in ("Terminé", "—", ""):
            return None
        return JALONS[scenario_prospect(row.get("conventions en cours", ""))].get(etape)

    df["Cible (j)"] = df.apply(_cible, axis=1)
    df["Retard (j)"] = [
        int(j) - int(c)
        if (pd.notna(j) and c is not None and not pd.isna(c) and int(j) > int(c))
        else None
        for j, c in zip(df["Jours étape"], df["Cible (j)"])
    ]

    # Dernière activité : journal horodaté (COMMENTAIRE > Commentaire fathi > Commentaires)
    journal_cols = [c for c in ("COMMENTAIRE", "Commentaire fathi", "Commentaires")
                    if c in df.columns]

    def _derniere_activite(row):
        fallback = ""
        for c in journal_cols:
            d, body = _parse_journal(row.get(c))
            if pd.notna(d):
                return pd.Series([d, body])
            if not fallback and isinstance(row.get(c), str) and row[c].strip():
                fallback = " ".join(row[c].split())[:160]
        return pd.Series([pd.NaT, fallback])

    if journal_cols:
        df[["Dernière activité", "Dernier point"]] = df.apply(_derniere_activite, axis=1)
    else:
        df["Dernière activité"] = pd.Series(pd.NaT, index=df.index)
        df["Dernier point"] = ""

    # Jours sans mouvement = depuis le max(journal, dates d'étape)
    _touches = date_cols + (["Dernière activité"] if journal_cols else [])
    if _touches:
        _last = df[_touches].max(axis=1)
        df["Sans mouvement (j)"] = (today - _last).dt.days
        # Relance suggérée = dernière activité + délai de relance (SEUILS)
        df["Relance suggérée"] = (_last + pd.Timedelta(days=relance_jours)).dt.normalize()
    else:
        df["Sans mouvement (j)"] = pd.Series(pd.NA, index=df.index, dtype="Int64")
        df["Relance suggérée"] = pd.Series(pd.NaT, index=df.index)

    def _situation(row) -> str:
        statut = str(row.get("AVANCEMENT2", "") or "").strip().lower()
        sm = row.get("Sans mouvement (j)")
        sm = int(sm) if pd.notna(sm) else None
        if statut == "clôturé":
            return "✅ Clôturé"
        if pd.notna(row.get("Date fin")):
            return "✅ Signé"          # signature datée mais AVANCEMENT2 non mis à jour
        if statut == "non démarré" and pd.isna(row.get("Date début")):
            return "⚪ Non démarré"
        if sm is None:
            return "🔵 À qualifier"
        if sm >= seuil_stalle:
            return f"🔴 Bloqué ({sm} j)"
        if sm >= seuil_stalle / 2:
            return f"🟡 À relancer ({sm} j)"
        return f"🟢 Actif ({sm} j)"

    def _motif(row) -> str:
        """Motif pré-rempli selon l'étape bloquée + dernier point du journal."""
        if not str(row.get("Situation", "")).startswith("🔴"):
            return ""
        base = _MOTIF_ETAPES.get(str(row.get("Étape en cours", "")), "Sans activité")
        point = str(row.get("Dernier point", "") or "").strip()
        if point:
            return f"{base} — {point}"[:160]
        return base

    df["Situation"] = df.apply(_situation, axis=1)
    df["Motif blocage (suggéré)"] = df.apply(_motif, axis=1)
    # Pas de relance suggérée sur les dossiers déjà clôturés
    if "Relance suggérée" in df.columns:
        df.loc[df["Situation"].str.startswith("✅"), "Relance suggérée"] = pd.NaT
    return df
