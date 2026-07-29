"""
Moteur KPI — logique métier centralisée (CA, évolutions, risque, inactivité).
"""
import pandas as pd
import numpy as np
from data.config import MOIS


def ca_sum(df: pd.DataFrame, annee: int, mois=None) -> float:
    """Somme du Montant TTC filtré par année (et optionnellement mois)."""
    d = df[df["Année"] == annee]
    if mois and isinstance(mois, list) and len(mois) > 0:
        d = d[d["Mois"].isin(mois)]
    elif mois and isinstance(mois, int):
        d = d[d["Mois"] == mois]
    return float(d["Montant TTC"].sum()) if "Montant TTC" in d.columns else 0.0


def evol_pct(n: float, n1: float) -> float:
    """Évolution en % entre deux valeurs."""
    return round((n - n1) / n1 * 100, 1) if n1 > 0 else 0.0


def ca_par_mois(df: pd.DataFrame, annee: int) -> pd.DataFrame:
    """CA mensuel pour une année donnée."""
    return (
        df[df["Année"] == annee]
        .groupby("Mois")["Montant TTC"].sum()
        .reset_index()
    )


def compare_years(df: pd.DataFrame, annee_n: int, annee_n1: int) -> pd.DataFrame:
    """Comparaison mensuelle N vs N-1."""
    if df.empty or "Montant TTC" not in df.columns:
        return pd.DataFrame(columns=["Mois", "CA N", "CA N-1", "Variation %", "Mois Nom"])
    n = ca_par_mois(df, annee_n).rename(columns={"Montant TTC": "CA N"})
    n1 = ca_par_mois(df, annee_n1).rename(columns={"Montant TTC": "CA N-1"})
    comp = n.merge(n1, on="Mois", how="outer").sort_values("Mois").fillna(0)
    comp["Variation %"] = (
        (comp["CA N"] - comp["CA N-1"]) / comp["CA N-1"].replace(0, 1) * 100
    ).round(1)
    comp["Mois Nom"] = comp["Mois"].map(MOIS)
    return comp


def compare_years_date_to_date(
    df: pd.DataFrame, annee_n: int, annee_n1: int, mois_sel: list = None
) -> pd.DataFrame:
    """Comparaison N vs N-1 DATE À DATE (mêmes JOURS EXACTS)."""
    if df.empty or "Montant TTC" not in df.columns:
        return pd.DataFrame(
            columns=["Mois", "CA N", "CA N-1", "Variation %", "Mois Nom", "Jours comparés"]
        )
    df_filtered = df.copy()
    if mois_sel is not None and len(mois_sel) > 0:
        df_filtered = df_filtered[df_filtered["Mois"].isin(mois_sel)]
    df_n = df_filtered[df_filtered["Année"] == annee_n].copy()
    df_n1 = df_filtered[df_filtered["Année"] == annee_n1].copy()
    if "Mois" not in df_n.columns or "Jour" not in df_n.columns or df_n.empty:
        return compare_years(df_filtered, annee_n, annee_n1)
    jours_par_mois = df_n.groupby("Mois")["Jour"].apply(set).to_dict()
    result_rows = []
    for mois in sorted(jours_par_mois.keys()):
        jours_n = jours_par_mois[mois]
        ca_n = df_n[df_n["Mois"] == mois]["Montant TTC"].sum()
        ca_n1 = df_n1[(df_n1["Mois"] == mois) & (df_n1["Jour"].isin(jours_n))]["Montant TTC"].sum()
        var_pct = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else (100 if ca_n > 0 else 0)
        result_rows.append({
            "Mois": mois,
            "CA N": ca_n,
            "CA N-1": ca_n1,
            "Variation %": round(var_pct, 1),
            "Mois Nom": MOIS.get(mois, str(mois)),
            "Jours comparés": len(jours_n),
        })
    return pd.DataFrame(result_rows)


def ca_sum_date_to_date(
    df: pd.DataFrame, annee_n: int, annee_n1: int, mois_sel: list = None
) -> tuple:
    """Calcul CA total date à date pour les deux années. Retourne (CA N, CA N-1, Évolution %)."""
    comp = compare_years_date_to_date(df, annee_n, annee_n1, mois_sel)
    if comp.empty:
        return 0, 0, 0
    ca_n = comp["CA N"].sum()
    ca_n1 = comp["CA N-1"].sum()
    evo = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else (100 if ca_n > 0 else 0)
    return ca_n, ca_n1, round(evo, 1)


def get_rolling_3m(df: pd.DataFrame) -> pd.DataFrame:
    """CA des 3 derniers mois glissants."""
    now = pd.Timestamp.now()
    periods = [(now - pd.DateOffset(months=i)) for i in range(2, -1, -1)]
    masks = [(df["Année"] == p.year) & (df["Mois"] == p.month) for p in periods]
    combined = masks[0] | masks[1] | masks[2]
    d = (
        df[combined]
        .groupby(["Année", "Mois"])["Montant TTC"].sum()
        .reset_index()
    )
    d["Periode"] = d["Mois"].map(MOIS) + " " + d["Année"].astype(str)
    return d.sort_values(["Année", "Mois"])


def convention_risk_matrix(df_vc: pd.DataFrame, annee_n: int, annee_n1: int = None) -> pd.DataFrame:
    """Matrice risque / opportunité par convention."""
    if annee_n1 is None:
        annee_n1 = annee_n - 1
    if df_vc.empty or "Nom" not in df_vc.columns:
        return pd.DataFrame()
    df = df_vc.copy()
    if "Jour" in df.columns:
        df_n = df[df["Année"] == annee_n]
        if not df_n.empty:
            jours_par_mois = df_n.groupby("Mois")["Jour"].apply(set).to_dict()
            for mois, jours_n in jours_par_mois.items():
                mask = (df["Année"] == annee_n1) & (df["Mois"] == mois) & (~df["Jour"].isin(jours_n))
                df = df[~mask]
    ca_n = df[df["Année"] == annee_n].groupby("Nom")["Montant TTC"].sum().rename("CA N")
    ca_n1 = df[df["Année"] == annee_n1].groupby("Nom")["Montant TTC"].sum().rename("CA N-1")
    mat = pd.concat([ca_n, ca_n1], axis=1).fillna(0).reset_index()
    mat["Évolution %"] = (
        (mat["CA N"] - mat["CA N-1"]) / mat["CA N-1"].replace(0, 1) * 100
    ).round(1)
    conditions = [
        (mat["CA N"] == 0) & (mat["CA N-1"] == 0),
        mat["CA N"] == 0,
        mat["CA N-1"] == 0,
        mat["Évolution %"] <= -20,
        mat["Évolution %"] < 0,
    ]
    choices = [
        "⚫ Aucun historique",
        "🔴 Inactif",
        "🟢 Nouveau",
        "🔴 Déclin fort",
        "🟡 Déclin",
    ]
    mat["Statut"] = np.select(conditions, choices, default="🟢 Croissance")
    return mat.sort_values("CA N", ascending=False)


def inactive_conventions(df_vc: pd.DataFrame, threshold_days: int = 60) -> pd.DataFrame:
    """Détecte les conventions sans facture depuis N jours."""
    if df_vc.empty or "Nom" not in df_vc.columns or "Date" not in df_vc.columns:
        return pd.DataFrame()
    today = pd.Timestamp.today().normalize()
    last = df_vc.groupby("Nom")["Date"].max().reset_index()
    last.columns = ["Convention", "Dernière Facture"]
    last["Jours inactifs"] = (today - last["Dernière Facture"]).dt.days
    return (
        last[last["Jours inactifs"] > threshold_days]
        .sort_values("Jours inactifs", ascending=False)
        .reset_index(drop=True)
    )
