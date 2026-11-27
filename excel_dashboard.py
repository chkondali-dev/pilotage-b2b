"""
Générateur de Dashboard Excel — Pilotage B2B (SMG / MG & BATAM)

Produit un classeur Excel formaté et prêt à l'emploi à partir des mêmes
fichiers sources que le dashboard Streamlit (GitHub / data/).

Onglets :
  1. Tableau de bord   — KPI dirigeants (CA, Δ vs N-1, panier, factures,
                         inactivité, risque, run-rate) + indicateurs visuels
  2. CA Mensuel        — CA N vs N-1 mois par mois + graphique barres
  3. Magasins          — CA par magasin / enseigne + part de portefeuille
  4. Risque            — Matrice de risque des conventions (CA N vs N-1)
  5. Inactivité        — Conventions sans facture depuis X jours
  6. Données           — Extrait des lignes sources utilisées

Conventions du projet respectées :
  • Palette sémantique C (green/red/blue/slate/amber) — data/config.py
  • Seuil d'inactivité 60j (SEUILS) — jamais 30j en dur
  • Comparaison date-à-date : N-1 borné au dernier jour écoulé de N
    (truncate_n1_date_to_date) — source unique, pas de réimplémentation
  • 4 noms individuels filtrés des vues Convention (NOMS_INDIVIDUELS)
  • Libellés français, devise TND

Dépendances : pandas, numpy, openpyxl, requests (déjà présents dans le projet).

Usage :
    python excel_dashboard.py                 # année détectée = max des données
    python excel_dashboard.py --annee 2025    # année forcée
    python excel_dashboard.py --sortie mon_dashboard.xlsx
"""

from __future__ import annotations

import argparse
import io
import re
import sys
import unicodedata
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote

import numpy as np
import pandas as pd
import requests
from openpyxl import Workbook
from openpyxl.chart import BarChart, LineChart, Reference
from openpyxl.chart.label import DataLabelList
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.table import Table, TableStyleInfo

from data.config import (
    C, MOIS, SEUILS, NOMS_INDIVIDUELS, TYPES_CONVENTION,
    FILES, GITHUB_RAW, LIBELLE_HORS_CONVENTION,
)


def _argb(hexstr: str) -> str:
    """Convertit '#RRGGBB' -> 'FFRRGGBB' (aRGB exigé par openpyxl)."""
    h = str(hexstr).lstrip("#")
    return ("FF" + h) if len(h) == 6 else h


CC = {k: _argb(v) for k, v in C.items()}

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTES DE MISE EN PAGE EXCEL
# ═══════════════════════════════════════════════════════════════════════════════

FILL_INK = PatternFill("solid", fgColor=CC["ink"])
FILL_BLUE = PatternFill("solid", fgColor=CC["blue"])
FILL_SLATE = PatternFill("solid", fgColor=CC["slate"])
FILL_GREEN = PatternFill("solid", fgColor=CC["green"])
FILL_RED = PatternFill("solid", fgColor=CC["red"])
FILL_AMBER = PatternFill("solid", fgColor=CC["amber"])
FILL_SURFACE = PatternFill("solid", fgColor=CC["surface"])
FILL_BORDER_LIGHT = PatternFill("solid", fgColor=CC["border"])
FILL_MUTED = PatternFill("solid", fgColor=CC["surface"])

FONT_WHITE_BOLD = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
FONT_INK_BOLD = Font(name="Calibri", size=11, bold=True, color=CC["ink"])
FONT_INK = Font(name="Calibri", size=11, color=CC["ink"])
FONT_MUTED = Font(name="Calibri", size=10, color=CC["muted"])
FONT_TITLE = Font(name="Calibri", size=16, bold=True, color=CC["ink"])
FONT_SUB = Font(name="Calibri", size=10, italic=True, color=CC["muted"])
FONT_KPI_VAL = Font(name="Calibri", size=20, bold=True, color=CC["blue"])
FONT_KPI_LBL = Font(name="Calibri", size=9, bold=True, color=CC["muted"])

THIN = Side(style="thin", color=CC["border"])
BORDER_ALL = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)

ALIGN_C = Alignment(horizontal="center", vertical="center", wrap_text=True)
ALIGN_L = Alignment(horizontal="left", vertical="center", wrap_text=True)
ALIGN_R = Alignment(horizontal="right", vertical="center")

NUM_TND = '# ##0 "TND"'
NUM_PCT = '0.0"%"'
NUM_INT = '# ##0'


def _fetch(url: str) -> bytes:
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    return r.content


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df.columns = df.columns.str.replace("\n", " ").str.replace("\r", " ").str.strip()
    df.columns = [re.sub(r"\s+", " ", c) for c in df.columns]
    for col in df.select_dtypes(include=["object", "string"]).columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": "", "None": ""})
    return df


def _filter_conventions(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "Nom" not in df.columns:
        return df
    return df[~df["Nom"].str.upper().str.strip().isin(NOMS_INDIVIDUELS)].copy()



def load_all_data(local_folder: Path | None = None) -> dict:
    dfs: dict = {}
    for key, fname in FILES.items():
        try:
            if local_folder is not None:
                path = local_folder / fname
                if not path.exists():
                    alt = local_folder / unquote(fname)
                    if alt.exists():
                        path = alt
                if not path.exists():
                    raise FileNotFoundError(f"{fname} (ni encodé, ni décodé) dans {local_folder}")
                if key == "conventions_signees":
                    dfs["conventions_signees"] = _clean(
                        pd.read_excel(path, engine="openpyxl", sheet_name="Conventions signées")
                    )
                    dfs["conventions_en_cours"] = _clean(
                        pd.read_excel(path, engine="openpyxl", sheet_name="convention en cours", skiprows=12)
                    )
                else:
                    dfs[key] = _clean(pd.read_excel(path, engine="openpyxl"))
            else:
                raw = _fetch(GITHUB_RAW + fname)
                if key == "conventions_signees":
                    dfs["conventions_signees"] = _clean(
                        pd.read_excel(io.BytesIO(raw), engine="openpyxl", sheet_name="Conventions signées")
                    )
                    dfs["conventions_en_cours"] = _clean(
                        pd.read_excel(io.BytesIO(raw), engine="openpyxl", sheet_name="convention en cours", skiprows=12)
                    )
                else:
                    dfs[key] = _clean(pd.read_excel(io.BytesIO(raw), engine="openpyxl"))
        except Exception as exc:
            print(f"[warn] Fichier {key} introuvable : {exc}")
            dfs[key] = pd.DataFrame()
    return dfs


def _add_date_cols(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    date_col = next((c for c in df.columns if "date" in c.lower() and "comptabil" in c.lower()), None)
    if date_col is None:
        date_col = next((c for c in df.columns if "date" in c.lower()), None)
    if date_col is None:
        return df
    df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["Année"] = df["Date"].dt.year.astype("Int64")
    df["Mois"] = df["Date"].dt.month.astype("Int64")
    df["Jour"] = df["Date"].dt.day.astype("Int64")
    return df


def _map_magasins(df: pd.DataFrame, code_df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["Enseigne"] = "MG"
    df["Magasin"] = "Inconnu"
    if code_df is None or code_df.empty:
        return df
    code_df = code_df.copy()
    code_df.columns = code_df.columns.str.strip()
    code_col_src = next((c for c in df.columns if c.lower() == "unite code"), None)
    if not code_col_src:
        return df
    code_col = list(code_df.columns)[0]
    unite_col = list(code_df.columns)[2] if len(code_df.columns) > 2 else list(code_df.columns)[-1]

    def get_ense(unit):
        s = str(unit).upper()
        return "BATAM" if ("BATAM" in s or "BTM" in s) else "MG"

    code_df["Enseigne"] = code_df[unite_col].apply(get_ense)
    code_df[code_col] = code_df[code_col].astype(str).str.strip()
    mapping_nom = code_df.set_index(code_col)[unite_col].to_dict()
    mapping_ense = code_df.set_index(code_col)["Enseigne"].to_dict()
    df[code_col_src] = df[code_col_src].astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
    df["Magasin"] = df[code_col_src].map(mapping_nom).fillna(df[code_col_src])
    df["Enseigne"] = df[code_col_src].map(mapping_ense).fillna("MG")
    return df


def prepare_data(dfs: dict) -> dict:
    df_vc = dfs.get("vc", pd.DataFrame()).copy()
    df_credit = dfs.get("vc_credit", pd.DataFrame()).copy()
    df_edc = dfs.get("vc_edc", pd.DataFrame()).copy()
    code_df = dfs.get("code_magasin", pd.DataFrame()).copy()

    frames = [f for f in (df_vc, df_credit, df_edc) if not f.empty]
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
    df = _clean(df)
    df = _add_date_cols(df)
    df = _map_magasins(df, code_df)

    if "Montant TTC" in df.columns:
        df["Montant TTC"] = pd.to_numeric(df["Montant TTC"], errors="coerce").fillna(0.0)

    df_conv = pd.DataFrame()
    if not df.empty and "Type de vente" in df.columns:
        df_conv = df[df["Type de vente"].isin(TYPES_CONVENTION)].copy()
    df_conv = _filter_conventions(df_conv)

    df_pos = df[df["Montant TTC"] > 0].copy() if not df.empty and "Montant TTC" in df.columns else df

    return {
        "vc": df,
        "vc_pos": df_pos,
        "convention": df_conv,
        "conventions_en_cours": dfs.get("conventions_en_cours", pd.DataFrame()),
        "conventions_signees": dfs.get("conventions_signees", pd.DataFrame()),
        "credit": df_credit,
        "edc": df_edc,
        "code_magasin": code_df,
    }


# ══════════════════════════════════════════════════════════════════════════════
# MÉTRIQUES (même logique que metrics/kpi.py — troncature date-à-date définie
# une seule fois ici, source unique du générateur Excel)
# ══════════════════════════════════════════════════════════════════════════════

def truncate_n1_date_to_date(df: pd.DataFrame, annee_n: int, annee_n1: int,
                             mois_sel: list = None) -> pd.DataFrame:
    if df.empty or "Jour" not in df.columns or "Année" not in df.columns:
        return df
    out = df.copy()
    if mois_sel is not None and len(mois_sel) > 0:
        mois_list = list(mois_sel)
    else:
        mois_list = sorted(df[df["Année"] == annee_n]["Mois"].dropna().unique())
    for mois in mois_list:
        jours_n = df[(df["Année"] == annee_n) & (df["Mois"] == mois)]["Jour"].dropna()
        if jours_n.empty:
            continue
        max_jour = int(jours_n.max())
        mask_n1 = (out["Année"] == annee_n1) & (out["Mois"] == mois) & (out["Jour"] > max_jour)
        out = out[~mask_n1]
    return out


def ca_sum(df: pd.DataFrame, annee: int, mois=None) -> float:
    d = df[df["Année"] == annee] if "Année" in df.columns else df
    if mois and isinstance(mois, list) and len(mois) > 0:
        d = d[d["Mois"].isin(mois)]
    elif mois and isinstance(mois, int):
        d = d[d["Mois"] == mois]
    return float(d["Montant TTC"].sum()) if "Montant TTC" in d.columns else 0.0


def evol_pct(n: float, n1: float) -> float:
    try:
        if n is None or n1 is None:
            return float("nan")
        if float(n1) > 0 and pd.notna(n) and pd.notna(n1):
            return round((float(n) - float(n1)) / float(n1) * 100, 1)
    except (TypeError, ValueError):
        pass
    return float("nan")


def compare_years_date_to_date(df: pd.DataFrame, annee_n: int, annee_n1: int,
                               mois_sel: list = None) -> pd.DataFrame:
    cols = ["Mois", "CA N", "CA N-1", "Variation %", "Mois Nom", "Jours comparés"]
    if df.empty or "Montant TTC" not in df.columns:
        return pd.DataFrame(columns=cols)
    df_filtered = df.copy()
    if mois_sel is not None and len(mois_sel) > 0:
        df_filtered = df_filtered[df_filtered["Mois"].isin(mois_sel)]
    df_n = df_filtered[df_filtered["Année"] == annee_n].copy()
    if "Mois" not in df_n.columns or "Jour" not in df_n.columns or df_n.empty:
        n = df_filtered[df_filtered["Année"] == annee_n].groupby("Mois")["Montant TTC"].sum().reset_index()
        n1 = df_filtered[df_filtered["Année"] == annee_n1].groupby("Mois")["Montant TTC"].sum().reset_index()
        comp = n.merge(n1, on="Mois", how="outer").sort_values("Mois").fillna(0)
        comp.columns = ["Mois", "CA N", "CA N-1"]
        comp["Variation %"] = np.where(
            comp["CA N-1"] > 0,
            (comp["CA N"] - comp["CA N-1"]) / comp["CA N-1"] * 100, np.nan,
        ).round(1)
        comp["Mois Nom"] = comp["Mois"].map(MOIS)
        comp["Jours comparés"] = ""
        return comp[cols]
    df_n1 = truncate_n1_date_to_date(df_filtered, annee_n, annee_n1, mois_sel)
    df_n1 = df_n1[df_n1["Année"] == annee_n1]
    jours_par_mois = df_n.groupby("Mois")["Jour"].apply(max).to_dict()
    rows = []
    for mois in sorted(jours_par_mois.keys()):
        max_jour = int(jours_par_mois[mois])
        ca_n = df_n[df_n["Mois"] == mois]["Montant TTC"].sum()
        ca_n1 = df_n1[df_n1["Mois"] == mois]["Montant TTC"].sum()
        var_pct = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else float("nan")
        rows.append({
            "Mois": mois, "CA N": ca_n, "CA N-1": ca_n1,
            "Variation %": round(var_pct, 1),
            "Mois Nom": MOIS.get(mois, str(mois)), "Jours comparés": max_jour,
        })
    return pd.DataFrame(rows, columns=cols)


def nb_factures(df: pd.DataFrame, annee: int, mois_sel: list = None) -> int:
    if df.empty or "Année" not in df.columns:
        return 0
    d = df[df["Année"] == annee]
    if mois_sel:
        d = d[d["Mois"].isin(mois_sel)]
    return int(len(d))


def panier_moyen(df: pd.DataFrame, annee: int, mois_sel: list = None) -> float:
    n = nb_factures(df, annee, mois_sel)
    if n == 0:
        return float("nan")
    d = df[df["Année"] == annee] if "Année" in df.columns else df
    if mois_sel:
        d = d[d["Mois"].isin(mois_sel)]
    if "Montant TTC" not in d.columns:
        return float("nan")
    return float(d["Montant TTC"].sum() / n)


def inactive_conventions(df_vc: pd.DataFrame, threshold_days: int = None,
                         annee_n: int = None) -> pd.DataFrame:
    if threshold_days is None:
        threshold_days = SEUILS["inactivite_jours"]
    if df_vc.empty or "Nom" not in df_vc.columns or "Date" not in df_vc.columns:
        return pd.DataFrame()
    today = pd.Timestamp.today().normalize()
    last = df_vc.groupby("Nom")["Date"].max().reset_index()
    last.columns = ["Convention", "Dernière Facture"]
    last["Jours inactifs"] = (today - last["Dernière Facture"]).dt.days
    out = last[last["Jours inactifs"] > threshold_days].sort_values(
        "Jours inactifs", ascending=False
    ).reset_index(drop=True)
    if not out.empty and annee_n is not None and "Année" in df_vc.columns and "Montant TTC" in df_vc.columns:
        ca_n1 = (df_vc[df_vc["Année"] == annee_n - 1]
                 .groupby("Nom")["Montant TTC"].sum().rename("CA N-1"))
        out = out.merge(ca_n1, left_on="Convention", right_index=True, how="left")
        out["CA N-1"] = out["CA N-1"].fillna(0.0)
    return out


def convention_risk_matrix(df: pd.DataFrame, annee_n: int, annee_n1: int,
                           mois_sel: list = None, declin_fort_pct: int = None) -> pd.DataFrame:
    if declin_fort_pct is None:
        declin_fort_pct = SEUILS["declin_fort_pct"]
    cols = ["Convention", "CA N", "CA N-1", "Variation %", "Statut", "Niveau risque"]
    if df.empty or "Nom" not in df.columns or "Montant TTC" not in df.columns:
        return pd.DataFrame(columns=cols)
    d = df[df["Année"].isin([annee_n, annee_n1])] if "Année" in df.columns else df
    if mois_sel:
        d = d[d["Mois"].isin(mois_sel)]
    if d.empty:
        return pd.DataFrame(columns=cols)
    ca_n = d[d["Année"] == annee_n].groupby("Nom")["Montant TTC"].sum() if "Année" in d.columns else pd.Series(dtype=float)
    ca_n1 = d[d["Année"] == annee_n1].groupby("Nom")["Montant TTC"].sum() if "Année" in d.columns else pd.Series(dtype=float)
    noms = sorted(set(ca_n.index) | set(ca_n1.index))
    rows = []
    for nom in noms:
        v_n = float(ca_n.get(nom, 0.0))
        v_n1 = float(ca_n1.get(nom, 0.0))
        evo = evol_pct(v_n, v_n1)
        if v_n == 0 and v_n1 > 0:
            statut, niveau = "🔴 Perdue", "Critique"
        elif v_n > 0 and v_n1 == 0:
            statut, niveau = "🟢 Nouvelle", "Opportunité"
        elif evo is not None and pd.notna(evo) and evo <= declin_fort_pct:
            statut, niveau = "🔴 Déclin fort", "Critique"
        elif evo is not None and pd.notna(evo) and evo < 0:
            statut, niveau = "🟡 En baisse", "Surveillance"
        else:
            statut, niveau = "🟢 Stable/Croissance", "Maîtrisé"
        rows.append({
            "Convention": nom, "CA N": v_n, "CA N-1": v_n1,
            "Variation %": round(evo, 1) if pd.notna(evo) else float("nan"),
            "Statut": statut, "Niveau risque": niveau,
        })
    out = pd.DataFrame(rows, columns=cols)
    return out.sort_values("CA N", ascending=False).reset_index(drop=True)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS DE MISE EN PAGE EXCEL
# ══════════════════════════════════════════════════════════════════════════════

def _title_block(ws, title: str, subtitle: str, start_row: int = 1) -> int:
    """Écrit un bandeau titre et retourne la prochaine ligne libre."""
    ws.merge_cells(start_row=start_row, start_column=1, end_row=start_row, end_column=8)
    c = ws.cell(row=start_row, column=1, value=title)
    c.font = FONT_TITLE
    c.fill = FILL_BLUE
    c.alignment = ALIGN_L
    for col in range(1, 9):
        ws.cell(row=start_row, column=col).fill = FILL_BLUE
        ws.cell(row=start_row, column=col).font = Font(name="Calibri", size=16, bold=True, color="FFFFFF")
    ws.row_dimensions[start_row].height = 30

    r = start_row + 1
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    c = ws.cell(row=r, column=1, value=subtitle)
    c.font = FONT_SUB
    c.alignment = ALIGN_L
    return r + 2  # ligne de début du contenu


def _style_header_row(ws, row: int, ncols: int, fill=FILL_INK) -> None:
    for col in range(1, ncols + 1):
        cell = ws.cell(row=row, column=col)
        cell.font = FONT_WHITE_BOLD
        cell.fill = fill
        cell.alignment = ALIGN_C
        cell.border = BORDER_ALL


def _write_dataframe(ws, df: pd.DataFrame, start_row: int,
                     num_fmts: dict = None, header_fill=FILL_INK) -> int:
    """Écrit un DataFrame avec mise en forme tableau. Retourne la ligne après le dernier écrit."""
    num_fmts = num_fmts or {}
    ncols = len(df.columns)
    for j, col_name in enumerate(df.columns, start=1):
        ws.cell(row=start_row, column=j, value=col_name)
    _style_header_row(ws, start_row, ncols, header_fill)
    r = start_row + 1
    for _, row in df.iterrows():
        for j, val in enumerate(row, start=1):
            cell = ws.cell(row=r, column=j, value=val)
            cell.font = FONT_INK
            cell.border = BORDER_ALL
            cell.alignment = ALIGN_L if j == 1 else ALIGN_R
            col_name = df.columns[j - 1]
            if col_name in num_fmts:
                cell.number_format = num_fmts[col_name]
                cell.alignment = ALIGN_R
            if isinstance(val, float) and pd.isna(val):
                cell.value = "—"
                cell.font = FONT_MUTED
                cell.alignment = ALIGN_C
        r += 1
    # largeurs de colonnes auto (bornées)
    for j, col_name in enumerate(df.columns, start=1):
        max_len = max([len(str(col_name))] + [len(str(v)) for v in df[col_name].head(40).tolist()] + [0])
        ws.column_dimensions[get_column_letter(j)].width = min(max(max_len + 2, 10), 42)
    return r


def _kpi_card(ws, row: int, col: int, label: str, value, delta: str = None,
              val_color: str = CC["blue"], delta_color: str = None) -> None:
    """Carte KPI sur 2 lignes x 3 colonnes fusionnées."""
    # bloc valeur
    ws.merge_cells(start_row=row, start_column=col, end_row=row, end_column=col + 2)
    vc = ws.cell(row=row, column=col, value=value)
    vc.font = Font(name="Calibri", size=22, bold=True, color=val_color)
    vc.alignment = ALIGN_C
    ws.merge_cells(start_row=row + 1, start_column=col, end_row=row + 1, end_column=col + 2)
    lc = ws.cell(row=row + 1, column=col, value=label)
    lc.font = FONT_KPI_LBL
    lc.alignment = ALIGN_C
    # bordure autour du bloc 2x3
    for rr in (row, row + 1):
        for cc in range(col, col + 3):
            cell = ws.cell(row=rr, column=cc)
            cell.border = BORDER_ALL
            cell.fill = FILL_SURFACE
    # delta sous le label (ligne row+2, même largeur)
    if delta is not None:
        ws.merge_cells(start_row=row + 2, start_column=col, end_row=row + 2, end_column=col + 2)
        dc = ws.cell(row=row + 2, column=col, value=delta)
        dc.font = Font(name="Calibri", size=10, bold=True, color=delta_color or CC["muted"])
        dc.alignment = ALIGN_C
        for cc in range(col, col + 3):
            ws.cell(row=row + 2, column=cc).border = BORDER_ALL
            ws.cell(row=row + 2, column=cc).fill = FILL_SURFACE


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 1 — TABLEAU DE BORD (exécutif)
# ══════════════════════════════════════════════════════════════════════════════

def build_executif(ws, data: dict, annee: int, annee_n1: int) -> None:
    df = data["vc"]
    df_pos = data["vc_pos"]
    title = "TABLEAU DE BORD — PILOTAGE B2B"
    sub = f"SMG & BATAM  |  Année sélectionnée : {annee} (comparaison {annee_n1} → {annee})  |  Devise : TND"
    r = _title_block(ws, title, sub, start_row=1)

    # ── KPI dirigeants ──
    ca_n = ca_sum(df_pos, annee)
    ca_n1 = ca_sum(df_pos, annee_n1)
    evo_ca = evol_pct(ca_n, ca_n1)
    nb_n = nb_factures(df_pos, annee)
    nb_n1 = nb_factures(df_pos, annee_n1)
    evo_nb = evol_pct(nb_n, nb_n1)
    panier_n = panier_moyen(df_pos, annee)
    panier_n1 = panier_moyen(df_pos, annee_n1)
    evo_panier = evol_pct(panier_n, panier_n1)

    inact = inactive_conventions(df_pos, annee_n=annee)
    nb_inact = len(inact)
    ca_risque = float(inact["CA N-1"].sum()) if not inact.empty and "CA N-1" in inact.columns else 0.0

    risk = convention_risk_matrix(df_pos, annee, annee_n1)
    nb_critique = int((risk["Niveau risque"] == "Critique").sum()) if not risk.empty else 0

    cards = [
        (f"{ca_n:,.0f}".replace(",", " "), f"CA {annee}", f"vs {annee_n1}: {fmt(evo_ca)}", CC["blue"], None),
        (f"{ca_n1:,.0f}".replace(",", " "), f"CA {annee_n1}", "Référence N-1", CC["slate"], None),
        (fmt(evo_ca), "Évolution CA", "+" if (evo_ca is not None and pd.notna(evo_ca) and evo_ca >= 0) else "—",
         CC["green"] if (evo_ca is not None and pd.notna(evo_ca) and evo_ca >= 0) else CC["red"],
         CC["green"] if (evo_ca is not None and pd.notna(evo_ca) and evo_ca >= 0) else CC["red"]),
        (f"{nb_n:,}".replace(",", " "), "Factures", f"Δ {fmt(evo_nb)}", CC["blue"], None),
        (f"{panier_n:,.0f}".replace(",", " ") if pd.notna(panier_n) else "—", "Panier moyen", f"Δ {fmt(evo_panier)}",
         CC["blue"], None),
        (f"{nb_inact}", "Inactives (>60j)", f"{ca_risque:,.0f}".replace(",", " ") + " TND CA N-1 à relancer",
         CC["red"] if nb_inact else CC["green"], CC["red"] if nb_inact else CC["green"]),
    ]
    # 6 cartes sur 2 rangées x 3 colonnes
    start_col = 1
    for idx, (val, lbl, delta, vcol, dcol) in enumerate(cards):
        row_k = r + (idx // 3) * 3
        col_k = start_col + (idx % 3) * 3
        _kpi_card(ws, row_k, col_k, lbl, val, delta, vcol, dcol)

    r = r + 2 * 3 + 2  # après les 2 rangées de cartes

    # ── Résumé risque ──
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=8)
    c = ws.cell(row=r, column=1, value=f"📊 Portefeuille : {len(risk)} convention(s)  |  ⚠️  {nb_critique} à risque critique")
    c.font = FONT_INK_BOLD
    c.fill = FILL_SURFACE
    c.alignment = ALIGN_L
    for cc in range(1, 9):
        ws.cell(row=r, column=cc).fill = FILL_SURFACE
        ws.cell(row=r, column=cc).border = BORDER_ALL
    r += 2

    # Top 5 baisses (extrait risque)
    if not risk.empty:
        baisse = risk[risk["Variation %"].notna() & (risk["Variation %"] < 0)].head(5)
        if not baisse.empty:
            ws.cell(row=r, column=1, value="🔴 Vigilance — plus fortes baisses de CA").font = FONT_INK_BOLD
            r += 1
            end = _write_dataframe(ws, baisse[["Convention", "CA N", "CA N-1", "Variation %", "Statut"]],
                                   r, num_fmts={"CA N": NUM_TND, "CA N-1": NUM_TND, "Variation %": NUM_PCT},
                                   header_fill=FILL_RED)
            r = end + 2

    ws.sheet_view.showGridLines = False


def fmt(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return "—"
    return f"{v:+.1f}%"


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 2 — CA MENSUEL (N vs N-1) + GRAPHIQUE
# ══════════════════════════════════════════════════════════════════════════════

def build_ca_mensuel(ws, comp: pd.DataFrame, annee_n: int, annee_n1: int) -> None:
    title = f"CA MENSUEL — {annee_n} vs {annee_n1} (date à date)"
    sub = "Comparaison mois par mois, N-1 tronquée au dernier jour écoulé de N (aucun jour creux ne retire du CA N-1)."
    r = _title_block(ws, title, sub, start_row=1)

    if comp.empty:
        ws.cell(row=r, column=1, value="Aucune donnée disponible.").font = FONT_MUTED
        ws.sheet_view.showGridLines = False
        return

    end = _write_dataframe(ws, comp, r,
                           num_fmts={"CA N": NUM_TND, "CA N-1": NUM_TND, "Variation %": NUM_PCT},
                           header_fill=FILL_BLUE)
    last_data_row = end - 1

    # Graphique barres groupées N vs N-1
    chart = BarChart()
    chart.type = "col"
    chart.grouping = "clustered"
    chart.title = f"CA {annee_n} vs {annee_n1} par mois (TND)"
    chart.y_axis.title = "CA (TND)"
    chart.x_axis.title = "Mois"
    chart.height = 9
    chart.width = 24
    chart.style = 10
    data = Reference(ws, min_col=2, max_col=3, min_row=r, max_row=last_data_row)
    cats = Reference(ws, min_col=5, min_row=r + 1, max_row=last_data_row)  # col E = Mois Nom
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    ws.add_chart(chart, f"A{end + 2}")

    # Coloration des séries : N-1 slate, N blue
    try:
        ser_n1 = chart.series[0]
        ser_n = chart.series[1]
        ser_n1.graphicalProperties.solidFill = CC["slate"]
        ser_n.graphicalProperties.solidFill = CC["blue"]
    except Exception:
        pass

    ws.sheet_view.showGridLines = False


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 3 — MAGASINS (CA par magasin / enseigne)
# ══════════════════════════════════════════════════════════════════════════════

def build_magasins(ws, data: dict, annee: int) -> None:
    df = data["vc_pos"]
    title = f"CA PAR MAGASIN / ENSEIGNE — {annee}"
    sub = "Ventes positives (hors avoirs), scope année sélectionnée."
    r = _title_block(ws, title, sub, start_row=1)

    if df.empty or "Magasin" not in df.columns:
        ws.cell(row=r, column=1, value="Aucune donnée magasin disponible.").font = FONT_MUTED
        ws.sheet_view.showGridLines = False
        return

    g = (df.groupby(["Enseigne", "Magasin"])["Montant TTC"]
         .sum().reset_index()
         .sort_values("Montant TTC", ascending=False))
    g["Part %"] = (g["Montant TTC"] / g["Montant TTC"].sum() * 100).round(1)
    g.columns = ["Enseigne", "Magasin", "CA (TND)", "Part du CA %"]

    end = _write_dataframe(ws, g, r,
                           num_fmts={"CA (TND)": NUM_TND, "Part du CA %": NUM_PCT},
                           header_fill=FILL_SLATE)

    # Graphique barres horizontales par enseigne (somme)
    ense = (df.groupby("Enseigne")["Montant TTC"].sum()
            .reset_index().sort_values("Montant TTC", ascending=False))
    chart = BarChart()
    chart.type = "bar"
    chart.grouping = "clustered"
    chart.title = f"CA par enseigne — {annee} (TND)"
    chart.height = 8
    chart.width = 16
    chart.style = 11
    start_ense = end + 2
    for j, col_name in enumerate(ense.columns, start=1):
        ws.cell(row=start_ense, column=j, value=col_name)
    _style_header_row(ws, start_ense, len(ense.columns), FILL_INK)
    rr = start_ense + 1
    for _, row in ense.iterrows():
        for j, val in enumerate(row, start=1):
            cell = ws.cell(row=rr, column=j, value=val)
            cell.font = FONT_INK
            cell.border = BORDER_ALL
            cell.alignment = ALIGN_L if j == 1 else ALIGN_R
            if j == 2:
                cell.number_format = NUM_TND
        rr += 1
    last_ense = rr - 1
    data = Reference(ws, min_col=2, min_row=start_ense, max_row=last_ense)
    cats = Reference(ws, min_col=1, min_row=start_ense + 1, max_row=last_ense)
    chart.add_data(data, titles_from_data=True)
    chart.set_categories(cats)
    try:
        chart.series[0].graphicalProperties.solidFill = CC["blue"]
    except Exception:
        pass
    ws.add_chart(chart, f"A{rr + 2}")

    ws.sheet_view.showGridLines = False


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 4 — RISQUE (matrice des conventions)
# ══════════════════════════════════════════════════════════════════════════════

def _niveau_fill(niveau: str):
    return {
        "Critique": FILL_RED,
        "Surveillance": FILL_AMBER,
        "Maîtrisé": FILL_GREEN,
        "Opportunité": FILL_BLUE,
    }.get(niveau, FILL_SURFACE)


def build_risque(ws, risk: pd.DataFrame) -> None:
    title = "MATRICE DE RISQUE — CONVENTIONS (N vs N-1)"
    sub = "Statut et niveau de risque calculés sur l'évolution du CA. Seuil déclin fort = -20 % (SEUILS)."
    r = _title_block(ws, title, sub, start_row=1)

    if risk.empty:
        ws.cell(row=r, column=1, value="Aucune donnée de risque disponible.").font = FONT_MUTED
        ws.sheet_view.showGridLines = False
        return

    end = _write_dataframe(ws, risk, r,
                           num_fmts={"CA N": NUM_TND, "CA N-1": NUM_TND, "Variation %": NUM_PCT},
                           header_fill=FILL_INK)

    # Mise en forme conditionnelle sur la colonne "Niveau risque"
    col_niveau = None
    for j, name in enumerate(risk.columns, start=1):
        if name == "Niveau risque":
            col_niveau = j
            break
    if col_niveau:
        for rr in range(r + 1, end):
            cell = ws.cell(row=rr, column=col_niveau)
            fill = _niveau_fill(str(cell.value))
            cell.fill = fill
            cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            cell.alignment = ALIGN_C

    ws.sheet_view.showGridLines = False


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 5 — INACTIVITÉ (conventions sans facture depuis > 60 j)
# ══════════════════════════════════════════════════════════════════════════════

def build_inactivite(ws, inact: pd.DataFrame, seuil: int = 60) -> None:
    title = f"CONVENTIONS INACTIVES (>{seuil} j sans facture)"
    sub = "Dernière facture et CA N-1 associé — priorité de relance commerciale."
    r = _title_block(ws, title, sub, start_row=1)

    if inact.empty:
        ws.cell(row=r, column=1, value="Aucune convention inactive détectée.").font = FONT_GREEN
        ws.sheet_view.showGridLines = False
        return

    cols_disp = ["Convention", "Dernière Facture", "Jours inactifs"]
    if "CA N-1" in inact.columns:
        cols_disp.append("CA N-1")
    df = inact[cols_disp].copy()

    end = _write_dataframe(ws, df, r,
                           num_fmts={"Jours inactifs": NUM_INT, "CA N-1": NUM_TND},
                           header_fill=FILL_AMBER)

    # Coloration des jours inactifs : >90 rouge, >60 amber
    col_ji = None
    for j, name in enumerate(df.columns, start=1):
        if name == "Jours inactifs":
            col_ji = j
            break
    if col_ji:
        for rr in range(r + 1, end):
            cell = ws.cell(row=rr, column=col_ji)
            try:
                v = int(cell.value)
            except (TypeError, ValueError):
                v = 0
            if v > 90:
                cell.fill = FILL_RED
                cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            elif v > seuil:
                cell.fill = FILL_AMBER
                cell.font = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
            cell.alignment = ALIGN_C

    ws.sheet_view.showGridLines = False


# ══════════════════════════════════════════════════════════════════════════════
# ONGLET 6 — DONNÉES (extrait source)
# ══════════════════════════════════════════════════════════════════════════════

def build_donnees(ws, df: pd.DataFrame, max_lignes: int = 5000) -> None:
    title = "DONNÉES SOURCE (extrait)"
    sub = "Lignes utilisées pour le calcul des KPI (premières 5 000)."
    r = _title_block(ws, title, sub, start_row=1)

    if df.empty:
        ws.cell(row=r, column=1, value="Aucune donnée source.").font = FONT_MUTED
        ws.sheet_view.showGridLines = False
        return

    show = df.head(max_lignes).copy()
    # colonnes utiles en premier si présentes
    preferred = ["Date", "Année", "Mois", "Jour", "Nom", "Magasin", "Enseigne",
                 "Type de vente", "Montant TTC", "Unite code"]
    cols = [c for c in preferred if c in show.columns] + [c for c in show.columns
                                                          if c not in preferred]
    show = show[cols]
    end = _write_dataframe(ws, show, r, header_fill=FILL_MUTED)
    ws.sheet_view.showGridLines = False


# ══════════════════════════════════════════════════════════════════════════════
# ASSEMBLAGE DU CLASSEUR
# ══════════════════════════════════════════════════════════════════════════════

def build_workbook(data: dict, annee: int, sortie: str = "Dashboard_Pilotage_B2B.xlsx") -> str:
    annee_n1 = annee - 1
    df_pos = data["vc_pos"]
    df_conv = data["convention"]

    wb = Workbook()

    # Onglet 1 : Tableau de bord
    ws1 = wb.active
    ws1.title = "Tableau de bord"
    build_executif(ws1, data, annee, annee_n1)

    # Onglet 2 : CA Mensuel
    ws2 = wb.create_sheet("CA Mensuel")
    comp = compare_years_date_to_date(df_pos, annee, annee_n1)
    build_ca_mensuel(ws2, comp, annee, annee_n1)

    # Onglet 3 : Magasins
    ws3 = wb.create_sheet("Magasins")
    build_magasins(ws3, data, annee)

    # Onglet 4 : Risque
    ws4 = wb.create_sheet("Risque")
    risk = convention_risk_matrix(df_conv, annee, annee_n1)
    build_risque(ws4, risk)

    # Onglet 5 : Inactivité
    ws5 = wb.create_sheet("Inactivité")
    inact = inactive_conventions(df_pos, annee_n=annee)
    build_inactivite(ws5, inact, SEUILS["inactivite_jours"])

    # Onglet 6 : Données
    ws6 = wb.create_sheet("Données")
    build_donnees(ws6, df_pos)

    wb.save(sortie)
    return sortie


# ══════════════════════════════════════════════════════════════════════════════
# POINT D'ENTRÉE
# ══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Génère un dashboard Excel Pilotage B2B.")
    parser.add_argument("--annee", type=int, default=None,
                        help="Année à afficher (défaut = année max présente dans les données).")
    parser.add_argument("--sortie", type=str, default="Dashboard_Pilotage_B2B.xlsx",
                        help="Chemin du fichier Excel de sortie.")
    parser.add_argument("--local", type=str, default=None,
                        help="Dossier contenant les fichiers Excel sources (au lieu de GitHub).")
    args = parser.parse_args()

    local_folder = Path(args.local) if args.local else None
    print("[*] Chargement des données…")
    dfs = load_all_data(local_folder)
    data = prepare_data(dfs)

    df_pos = data["vc_pos"]
    annees = sorted({int(a) for a in df_pos["Année"].dropna().unique()}) if "Année" in df_pos.columns and not df_pos.empty else []
    if not annees:
        print("[!] Aucune année détectée dans les données.")
        return
    annee = args.annee if args.annee in annees else annees[-1]
    print(f"[*] Année retenue : {annee}")

    sortie = build_workbook(data, annee, args.sortie)
    print(f"[OK] Dashboard Excel genere : {sortie}")


if __name__ == "__main__":
    main()

