"""
Moteur KPI — logique métier centralisée (CA, évolutions, risque, inactivité).
"""
import pandas as pd
import numpy as np
import re as _re
import unicodedata as _ud
from pathlib import Path as _Path
from data.config import MOIS, SEUILS

EFFECTIFS_PATH = _Path(__file__).resolve().parent.parent / "data" / "effectifs_conventions.csv"


def ca_sum(df: pd.DataFrame, annee: int, mois=None) -> float:
    """Somme du Montant TTC filtré par année (et optionnellement mois)."""
    d = df[df["Année"] == annee]
    if mois and isinstance(mois, list) and len(mois) > 0:
        d = d[d["Mois"].isin(mois)]
    elif mois and isinstance(mois, int):
        d = d[d["Mois"] == mois]
    return float(d["Montant TTC"].sum()) if "Montant TTC" in d.columns else 0.0


def evol_pct(n: float, n1: float) -> float:
    """Évolution en % — np.nan si pas de base N-1 (afficher « — », jamais +0/+100 % fictif)."""
    try:
        if n is None or n1 is None:
            return float("nan")
        if float(n1) > 0 and pd.notna(n) and pd.notna(n1):
            return round((float(n) - float(n1)) / float(n1) * 100, 1)
    except (TypeError, ValueError):
        pass
    return float("nan")


def fmt_pct(v, na: str = "—") -> str:
    """Formatage sûr d'une évolution : NaN/None → `na` (jamais « +nan% »)."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return na
    return f"{v:+.1f}%"


def color_delta(v) -> str:
    """Couleur delta Streamlit : « off » sans base (NaN/None), sinon normal/inverse."""
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "off"
    return "normal" if v >= 0 else "inverse"


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
    comp["Variation %"] = np.where(
        comp["CA N-1"] > 0,
        (comp["CA N"] - comp["CA N-1"]) / comp["CA N-1"] * 100,
        np.nan,  # sans base N-1 → « — » plutôt que faux 0/+100 %
    ).round(1)
    comp["Mois Nom"] = comp["Mois"].map(MOIS)
    return comp


def truncate_n1_date_to_date(
    df: pd.DataFrame, annee_n: int, annee_n1: int, mois_sel: list = None
) -> pd.DataFrame:
    """
    SOURCE UNIQUE de troncature date-à-date : borne N-1 au dernier jour
    ÉCOULÉ de N (jour max atteint par mois). Tous les jours 1..max de N-1
    sont conservés, y compris ceux où N n'a pas de transaction (CA nul) —
    une journée sans facture ne doit PAS retirer le CA de N-1 (faussait les
    totaux en fin de mois). Si mois_sel est fourni, ne tronque que ces mois.
    Les autres lignes (autres mois/années) sont conservées (tendances 3m).
    """
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
    if "Mois" not in df_n.columns or "Jour" not in df_n.columns or df_n.empty:
        return compare_years(df_filtered, annee_n, annee_n1)
    df_n1 = truncate_n1_date_to_date(df_filtered, annee_n, annee_n1, mois_sel)
    df_n1 = df_n1[df_n1["Année"] == annee_n1]
    jours_par_mois = df_n.groupby("Mois")["Jour"].apply(max).to_dict()
    result_rows = []
    for mois in sorted(jours_par_mois.keys()):
        max_jour = int(jours_par_mois[mois])
        ca_n = df_n[df_n["Mois"] == mois]["Montant TTC"].sum()
        ca_n1 = df_n1[df_n1["Mois"] == mois]["Montant TTC"].sum()
        var_pct = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else float("nan")  # sans base → « — »
        result_rows.append({
            "Mois": mois,
            "CA N": ca_n,
            "CA N-1": ca_n1,
            "Variation %": round(var_pct, 1),
            "Mois Nom": MOIS.get(mois, str(mois)),
            "Jours comparés": max_jour,
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
    evo = ((ca_n - ca_n1) / ca_n1 * 100) if ca_n1 > 0 else float("nan")  # sans base → « — »
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
    df = truncate_n1_date_to_date(df_vc, annee_n, annee_n1)
    ca_n = df[df["Année"] == annee_n].groupby("Nom")["Montant TTC"].sum().rename("CA N")
    ca_n1 = df[df["Année"] == annee_n1].groupby("Nom")["Montant TTC"].sum().rename("CA N-1")
    mat = pd.concat([ca_n, ca_n1], axis=1).fillna(0).reset_index()
    mat["Évolution %"] = np.where(
        mat["CA N-1"] > 0,
        (mat["CA N"] - mat["CA N-1"]) / mat["CA N-1"] * 100,
        np.nan,  # sans base N-1 (ex. « Nouveau ») → « — »
    ).round(1)
    conditions = [
        (mat["CA N"] == 0) & (mat["CA N-1"] == 0),
        mat["CA N"] == 0,
        mat["CA N-1"] == 0,
        mat["Évolution %"] <= SEUILS["declin_fort_pct"],
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


def inactive_conventions(
    df_vc: pd.DataFrame, threshold_days: int = None, annee_n: int = None
) -> pd.DataFrame:
    """
    Détecte les conventions sans facture depuis N jours.
    Défaut = SEUILS["inactivite_jours"] (source unique).
    Si annee_n est fourni, ajoute la colonne « CA N-1 » (année annee_n - 1)
    pour chiffrer le CA à risque lié à l'inactivité.
    """
    if threshold_days is None:
        threshold_days = SEUILS["inactivite_jours"]
    if df_vc.empty or "Nom" not in df_vc.columns or "Date" not in df_vc.columns:
        return pd.DataFrame()
    today = pd.Timestamp.today().normalize()
    last = df_vc.groupby("Nom")["Date"].max().reset_index()
    last.columns = ["Convention", "Dernière Facture"]
    last["Jours inactifs"] = (today - last["Dernière Facture"]).dt.days
    out = (
        last[last["Jours inactifs"] > threshold_days]
        .sort_values("Jours inactifs", ascending=False)
        .reset_index(drop=True)
    )
    if (
        not out.empty
        and annee_n is not None
        and "Année" in df_vc.columns
        and "Montant TTC" in df_vc.columns
    ):
        ca_n1 = (
            df_vc[df_vc["Année"] == annee_n - 1]
            .groupby("Nom")["Montant TTC"].sum()
            .rename("CA N-1")
        )
        out = out.merge(ca_n1, left_on="Convention", right_index=True, how="left")
        out["CA N-1"] = out["CA N-1"].fillna(0.0)
    return out

# ══════════════════════════════════════════════════════════════
# LOT P1 — bridge volume×panier
# ══════════════════════════════════════════════════════════════

def _scope_d2d(df: pd.DataFrame, annee_n: int, mois_sel: list = None) -> tuple:
    """Scope N (mois filtrés) + N-1 tronquée date-à-date. Retourne (df_n, df_n1)."""
    if df.empty or "Année" not in df.columns:
        return df.iloc[0:0].copy(), df.iloc[0:0].copy()
    df_n = df[df["Année"] == annee_n].copy()
    if mois_sel:
        df_n = df_n[df_n["Mois"].isin(mois_sel)]
    df_n1 = truncate_n1_date_to_date(df, annee_n, annee_n - 1, mois_sel)
    df_n1 = df_n1[df_n1["Année"] == annee_n - 1]
    return df_n, df_n1


def nb_factures(df: pd.DataFrame, annee: int, mois_sel: list = None) -> int:
    """Nombre de factures (lignes) sur l'année (et mois optionnels)."""
    if df.empty or "Année" not in df.columns:
        return 0
    d = df[df["Année"] == annee]
    if mois_sel:
        d = d[d["Mois"].isin(mois_sel)]
    return int(len(d))


def panier_moyen(df: pd.DataFrame, annee: int, mois_sel: list = None) -> float:
    """Panier moyen = CA / nb factures. NaN si aucune facture (pas de base)."""
    n = nb_factures(df, annee, mois_sel)
    if n == 0:
        return float("nan")
    d = df[df["Année"] == annee]
    if mois_sel:
        d = d[d["Mois"].isin(mois_sel)]
    if "Montant TTC" not in d.columns:
        return float("nan")
    return float(d["Montant TTC"].sum() / n)


def bridge_volume_panier(
    df: pd.DataFrame, annee_n: int, mois_sel: list = None
) -> pd.DataFrame:
    """
    Pont de variation CA : ΔCA = effet volume + effet panier + interaction.
      effet volume = (n − n0) × p0      (plus/moins de factures)
      effet panier = n0 × (p − p0)      (panier moyen)
      effet mix    = (n − n0) × (p − p0) (interaction, résiduel exact)
    N-1 tronquée date-à-date (mêmes jours que N). Effets NaN sans base N-1.
    """
    df_n, df_n1 = _scope_d2d(df, annee_n, mois_sel)
    ca_n = float(df_n["Montant TTC"].sum()) if "Montant TTC" in df_n.columns else 0.0
    ca_n1 = float(df_n1["Montant TTC"].sum()) if "Montant TTC" in df_n1.columns else 0.0
    n = int(len(df_n))
    n0 = int(len(df_n1))
    nan = float("nan")
    base_ok = n0 > 0 and ca_n1 > 0
    if not base_ok:
        p0 = p1 = v = p = mix = nan
    else:
        p0 = ca_n1 / n0
        p1 = ca_n / n if n > 0 else 0.0
        v = (n - n0) * p0
        p = n0 * (p1 - p0)
        mix = (n - n0) * (p1 - p0)
    r = lambda x: round(x, 0) if pd.notna(x) else nan
    # « Effet (TND) » = écarts (métriques/tableaux) ; « Valeur » = niveaux du pont
    # [CA N-1, +v, +p, +mix, CA N] tracés par chart_bridge (NaN si pas de base).
    return pd.DataFrame([
        {"Étape": "CA N-1", "Nb factures": n0, "Panier moyen": r(p0 if base_ok else nan),
         "Effet (TND)": nan, "Valeur": round(ca_n1, 0) if base_ok else nan},
        {"Étape": "+ Volume", "Nb factures": (n - n0) if base_ok else nan,
         "Panier moyen": r(p0 if base_ok else nan), "Effet (TND)": r(v), "Valeur": r(v)},
        {"Étape": "+ Panier", "Nb factures": n0 if base_ok else nan,
         "Panier moyen": r((p1 - p0) if base_ok else nan), "Effet (TND)": r(p), "Valeur": r(p)},
        {"Étape": "+ Mix", "Nb factures": nan, "Panier moyen": nan,
         "Effet (TND)": r(mix), "Valeur": r(mix)},
        {"Étape": "= CA N", "Nb factures": n, "Panier moyen": r(p1 if n > 0 else nan),
         "Effet (TND)": round(ca_n - ca_n1, 0),
         "Valeur": round(ca_n, 0) if base_ok else nan},
    ])
    return out

# ── Run-rate fin d'année ─────────────────────────────────────

def run_rate_fin_annee(df: pd.DataFrame, annee: int, today=None) -> dict:
    """
    Projection fin d'année : CA YTD / jours écoulés × jours de l'année.
    Jours écoulés = jour calendaire de la dernière facture de l'année
    (années passées : année complète → projection = CA réel).
    """
    today = today or pd.Timestamp.today().normalize()
    out = {"CA YTD": 0.0, "Jours écoulés": 0, "Jours année": 365,
           "Projection": float("nan")}
    if df.empty or "Année" not in df.columns or "Montant TTC" not in df.columns:
        return out
    d = df[df["Année"] == annee]
    if d.empty:
        return out
    out["CA YTD"] = float(d["Montant TTC"].sum())
    bissextile = (annee % 4 == 0 and annee % 100 != 0) or (annee % 400 == 0)
    out["Jours année"] = 366 if bissextile else 365
    if annee < today.year:
        out["Jours écoulés"] = out["Jours année"]
    elif annee == today.year and "Date" in d.columns:
        last = d["Date"].max()
        out["Jours écoulés"] = int(min(last.dayofyear, out["Jours année"])) if pd.notna(last) else 0
    else:
        return out  # année future : pas de base
    if out["Jours écoulés"] > 0:
        out["Projection"] = round(out["CA YTD"] / out["Jours écoulés"] * out["Jours année"], 0)
    return out


# ── Santé des données ────────────────────────────────────────

def data_health(df: pd.DataFrame, recent_days: int = 90, today=None) -> dict:
    """
    Santé des données (panneau sidebar) : retard d'alimentation, doublons,
    montants non positifs, NaN critiques, jours sans facture (fenêtre récente).
    """
    today = today or pd.Timestamp.today().normalize()
    out = {
        "Lignes": 0, "Dernière facture": None, "Retard (j)": None,
        "Doublons exacts": 0, "Montants ≤ 0": 0, "NaN Date": 0, "NaN Montant": 0,
        "Jours sans facture (90j)": 0, "Statut": "✅",
    }
    if df.empty:
        out["Statut"] = "⚠️"
        return out
    out["Lignes"] = int(len(df))
    out["Doublons exacts"] = int(df.duplicated().sum())
    if "Montant TTC" in df.columns:
        out["Montants ≤ 0"] = int((df["Montant TTC"] <= 0).sum())
        out["NaN Montant"] = int(df["Montant TTC"].isna().sum())
    if "Date" in df.columns:
        dd = pd.to_datetime(df["Date"], errors="coerce")
        out["NaN Date"] = int(dd.isna().sum())
        last = dd.max()
        if pd.notna(last):
            out["Dernière facture"] = last.date().isoformat()
            out["Retard (j)"] = int((today - last.normalize()).days)
            start = today - pd.Timedelta(days=recent_days)
            rec = dd[(dd >= start) & (dd <= today)].dt.normalize().dropna().unique()
            out["Jours sans facture (90j)"] = int(max((today - start).days + 1, 1) - len(rec))
    issues = (
        out["Doublons exacts"] > 0 or out["Montants ≤ 0"] > 0
        or out["NaN Date"] > 0 or out["NaN Montant"] > 0
        or (out["Retard (j)"] is not None and out["Retard (j)"] > SEUILS["inactivite_jours"])
    )
    out["Statut"] = "⚠️" if issues else "✅"
    return out

# ══════════════════════════════════════════════════════════════
# LOT P2 — objectifs, cohortes, narratif exécutif (déterministe)
# ══════════════════════════════════════════════════════════════

def objectif_tracking(ca_ytd: float, objectif_annuel: float, jours_ecoules: int,
                      jours_annee: int = 365) -> dict:
    """
    Suivi d'objectif annuel : % atteinte, cible prorata, avance/retard.
    NaN si objectif ≤ 0 (pas de cible définie → « — »).
    """
    out = {"Objectif": float(objectif_annuel or 0.0), "CA YTD": float(ca_ytd or 0.0),
           "Atteinte %": float("nan"), "Cible prorata": float("nan"),
           "Avance/retard": float("nan")}
    if objectif_annuel is None or objectif_annuel <= 0:
        return out
    out["Atteinte %"] = round(ca_ytd / objectif_annuel * 100, 1)
    if jours_ecoules and jours_ecoules > 0 and jours_annee > 0:
        out["Cible prorata"] = round(objectif_annuel * jours_ecoules / jours_annee, 0)
        out["Avance/retard"] = round(ca_ytd - out["Cible prorata"], 0)
    return out


def cohortes_conventions(df: pd.DataFrame, annee_n: int, history_years: int = None,
                         mois_sel: list = None) -> pd.DataFrame:
    """
    Cohortes par ancienneté (1re année facturée sur TOUT l'historique) :
    Nouvelles (1re facture = N), Fidèles (CA chaque année sur la fenêtre),
    Revenantes (CA en N après ≥1 an de trou), Perdues (CA récent, rien en N).
    N-1 tronquée date-à-date sur le scope filtré (cohérence dashboard).
    Colonnes : Cohorte, Conventions, CA N, CA N-1, Variation %, Poids % N.
    """
    cols = ["Cohorte", "Conventions", "CA N", "CA N-1", "Variation %", "Poids % N"]
    if df.empty or "Nom" not in df.columns or "Année" not in df.columns:
        return pd.DataFrame(columns=cols)
    window = history_years or SEUILS["cohorte_fidele_ans"]
    df_n, df_n1 = _scope_d2d(df, annee_n, mois_sel)
    if df_n.empty and df_n1.empty:
        return pd.DataFrame(columns=cols)
    first = df.groupby("Nom")["Année"].min().to_dict()
    years_avail = sorted(df["Année"].dropna().unique().tolist())
    ca_n = df_n.groupby("Nom")["Montant TTC"].sum().to_dict() if not df_n.empty else {}
    ca_n1 = df_n1.groupby("Nom")["Montant TTC"].sum().to_dict() if not df_n1.empty else {}
    noms = set(ca_n) | set(ca_n1)
    rows = []
    for nom in noms:
        v_n = float(ca_n.get(nom, 0.0))
        v_n1 = float(ca_n1.get(nom, 0.0))
        if first.get(nom) == annee_n:
            coh = "🆕 Nouvelles"
        elif v_n > 0 and v_n1 > 0:
            hist = [y for y in years_avail if annee_n - window <= y <= annee_n]
            had = {y for y in hist if float(df[(df["Nom"] == nom) & (df["Année"] == y)][
                "Montant TTC"].sum()) > 0}
            coh = "✅ Fidèles" if len(had) >= min(window + 1, len(hist)) else "🔄 Revenantes"
        elif v_n > 0:
            coh = "🔄 Revenantes"
        else:
            coh = "❌ Perdues"
        rows.append({"Nom": nom, "Cohorte": coh, "CA N": v_n, "CA N-1": v_n1})
    g = pd.DataFrame(rows)
    agg = g.groupby("Cohorte").agg(
        Conventions=("Nom", "nunique"), **{"CA N": ("CA N", "sum"), "CA N-1": ("CA N-1", "sum")}
    ).reset_index()
    agg["Variation %"] = np.where(
        agg["CA N-1"] > 0, (agg["CA N"] - agg["CA N-1"]) / agg["CA N-1"] * 100, np.nan,
    ).round(1)
    tot_n = agg["CA N"].sum()
    agg["Poids % N"] = (agg["CA N"] / tot_n * 100).round(1) if tot_n > 0 else 0.0
    order = ["✅ Fidèles", "🆕 Nouvelles", "🔄 Revenantes", "❌ Perdues"]
    agg["__o"] = agg["Cohorte"].apply(lambda c: order.index(c) if c in order else 9)
    agg = agg.sort_values("__o").drop(columns="__o").reset_index(drop=True)
    # Liste détaillée par convention (pour le drill-down cliquable du dashboard).
    agg.attrs["detail"] = g[["Nom", "Cohorte", "CA N", "CA N-1"]].copy()
    return agg


def _norm_nom(s) -> str:
    """Normalise un nom de convention : lower, sans accents, espaces/ponct uniformises."""
    if s is None or (isinstance(s, float) and pd.isna(s)):
        return ""
    s = str(s).strip()
    s = _ud.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    s = s.lower().replace("'", " ").replace('"', " ").replace("*", " ")
    s = _re.sub(r"[^a-z0-9 ]+", " ", s)
    s = _re.sub(r"\s+", " ", s).strip()
    return s


def load_effectifs() -> pd.DataFrame:
    """Charge le référentiel effectifs (col societe/effectif). NaN/0 conservés (exclus du ratio)."""
    cols = ["Nom", "Effectif"]
    if not EFFECTIFS_PATH.exists():
        return pd.DataFrame(columns=cols)
    try:
        eff = pd.read_csv(EFFECTIFS_PATH, sep=";", encoding="utf-8")
    except Exception:
        return pd.DataFrame(columns=cols)
    eff.columns = [str(c).strip().lower() for c in eff.columns]
    col_nom = next((c for c in eff.columns if "soc" in c or "nom" in c or "conv" in c), eff.columns[0])
    col_eff = next((c for c in eff.columns if "eff" in c), eff.columns[-1])
    out = pd.DataFrame({"Nom": eff[col_nom].astype(str).str.strip(),
                        "Effectif": pd.to_numeric(eff[col_eff], errors="coerce")})
    out["key"] = out["Nom"].map(_norm_nom)
    return out


def conversion_conventions(df: pd.DataFrame, annee_n: int, mois_sel: list = None) -> pd.DataFrame:
    """
    Taux de conversion client par convention.
    Nb acheteurs = nb distinct de clients ayant acheté (col 'N° Client'/'Nom Client'
    si présentes, sinon nb de factures). Effectif = référentiel data/effectifs_conventions.csv.
    Taux % = Nb acheteurs / Effectif (NaN si effectif manquant ou ≤ 0).
    Scope : année N (et mois filtrés). Colonnes : Nom, Effectif, Nb acheteurs, Nb factures, Taux %.
    """
    cols = ["Nom", "Effectif", "Nb acheteurs", "Nb factures", "Taux %"]
    if df is None or df.empty or "Nom" not in df.columns:
        return pd.DataFrame(columns=cols)
    d = df[df["Année"] == annee_n].copy() if "Année" in df.columns else df.copy()
    if mois_sel:
        d = d[d["Mois"].isin(mois_sel)]
    if d.empty:
        return pd.DataFrame(columns=cols)
    client_col = None
    cands = [c for c in d.columns if "client" in c.lower()]
    # Priorite : 'N° Client' exact de l'acheteur (exclure 'facture' = compte convention,
    # exclure 'nom client' texte libre) puis N° compte bancaire, puis fallback
    for c in cands:
        cl = c.lower()
        if "factur" in cl or "nom client" in cl or "groupe" in cl:
            continue
        if "n°" in cl or "no " in cl or cl.strip() in ("n client", "n° client",
             "no client", "code client", "n° client", "n client"):
            client_col = c
            break
    if client_col is None:
        for c in cands:
            cl = c.lower()
            if "factur" in cl or "groupe" in cl:
                continue
            client_col = c
            break
    grp = d.groupby("Nom")
    nb_fact = grp.size().rename("Nb factures")
    if client_col is not None:
        nb_ach = grp[client_col].nunique(dropna=True).rename("Nb acheteurs")
    else:
        nb_ach = grp.size().rename("Nb acheteurs")
    conv = pd.concat([nb_ach, nb_fact], axis=1).reset_index()
    eff = load_effectifs()
    if not eff.empty:
        eff_map = eff.drop_duplicates("key").set_index("key")["Effectif"].to_dict()
        eff_nom = eff.drop_duplicates("key").set_index("key")["Nom"].to_dict()
        conv["key"] = conv["Nom"].map(_norm_nom)
        conv["Effectif"] = conv["key"].map(eff_map)
        # libellé référentiel si dispo (optionnel, garde Nom facturé)
        conv = conv.drop(columns=["key"])
    else:
        conv["Effectif"] = float("nan")
    conv["Taux %"] = (conv["Nb acheteurs"] / conv["Effectif"] * 100).round(1)
    conv.loc[~(conv["Effectif"] > 0), "Taux %"] = float("nan")
    return conv.sort_values("Taux %", ascending=False, na_position="last").reset_index(drop=True)


def kpi_conversion_globale(conv_df: pd.DataFrame) -> dict:
    """Ratio global = Σ acheteurs / Σ effectifs (effectifs > 0 uniquement)."""
    out = {"Nb acheteurs": 0, "Effectif total": 0, "Taux global %": float("nan"),
           "Nb conventions suivies": 0, "Nb sans effectif": 0}
    if conv_df is None or conv_df.empty:
        return out
    ok = conv_df[conv_df["Effectif"] > 0].copy()
    out["Nb conventions suivies"] = int(len(ok))
    out["Nb sans effectif"] = int(len(conv_df) - len(ok))
    out["Nb acheteurs"] = int(ok["Nb acheteurs"].sum())
    out["Effectif total"] = int(ok["Effectif"].sum())
    if out["Effectif total"] > 0:
        out["Taux global %"] = round(out["Nb acheteurs"] / out["Effectif total"] * 100, 2)
    return out


def narratif_executif(ctx: dict) -> list:
    """5 bullets exécutifs déterministes (FR) à partir d'un contexte chiffré.
    Chaque bullet : (icône, texte). NaN-safe : mention « — » si pas de base.
    Clés attendues : annee, ca_n, ca_n1, evo_pct, objectif, atteinte_pct,
    avance_retard, bridge (dict étape→effet), top_hausse (nom, delta),
    flop (nom, evo), ca_risque, nb_inact, run_rate, ca_n1_annuel.
    """
    b = []
    an, evo = ctx.get("annee"), ctx.get("evo_pct")
    b.append(("📊", f"CA {an} à {ctx.get('ca_n', 0):,.0f} TND, "
              f"{fmt_pct(evo)} vs {an - 1 if an else 'N-1'}."
              if an else f"CA à {ctx.get('ca_n', 0):,.0f} TND."))
    att, av = ctx.get("atteinte_pct"), ctx.get("avance_retard")
    if ctx.get("objectif") and ctx["objectif"] > 0 and pd.notna(att):
        sens = "d'avance" if (av or 0) >= 0 else "de retard"
        b.append(("🎯", f"Objectif {ctx['objectif']:,.0f} TND : {att:.1f} % atteint "
                  f"({abs(av or 0):,.0f} TND {sens} sur le prorata)."))
    else:
        b.append(("🎯", "Objectif annuel non défini — renseignez-le dans la sidebar."))
    br = ctx.get("bridge") or {}
    if pd.notna(br.get("+ Volume")):
        moteur = max([("+ Volume", br["+ Volume"]), ("+ Panier", br["+ Panier"]),
                      ("+ Mix", br.get("+ Mix", 0))], key=lambda kv: abs(kv[1]))
        b.append(("⚙️", f"Moteur dominant : {moteur[0].replace('+ ', '')} "
                  f"({moteur[1]:+,.0f} TND)."))
    th = ctx.get("top_hausse") or {}
    fl = ctx.get("flop") or {}
    if th.get("nom"):
        b.append(("📈", f"Top hausse : {th['nom']} ({th.get('delta', 0):+,.0f} TND vs N-1)."))
    if fl.get("nom"):
        b.append(("📉", f"Vigilance : {fl['nom']} ({fmt_pct(fl.get('evo'))} vs N-1)."))
    else:
        b.append(("📉", "Aucune baisse significative détectée sur la période."))
    rr, risiko, ni = ctx.get("run_rate"), ctx.get("ca_risque", 0), ctx.get("nb_inact", 0)
    tail = (f"Run-rate fin d'année : {rr:,.0f} TND. " if pd.notna(rr) else "")
    tail += (f"{ni} convention(s) inactive(s) = {risiko:,.0f} TND de CA N-1 à relancer."
             if ni and risiko > 0 else "Portefeuille actif stable.")
    b.append(("🔭", tail))
    return b[:6]

# ══════════════════════════════════════════════════════════════
# REVUE GLOBALE — concentration, volumes, insights (déterministes)
# ══════════════════════════════════════════════════════════════

def ventes_positives(df: pd.DataFrame) -> pd.DataFrame:
    """Lignes de vente réelles : Montant TTC strictement positif (hors avoirs)."""
    if df.empty or "Montant TTC" not in df.columns:
        return df.iloc[0:0].copy() if not df.empty else df
    return df[df["Montant TTC"] > 0].copy()


def concentration_portefeuille(df: pd.DataFrame, annee: int,
                               mois_sel: list = None) -> dict:
    """
    Concentration du portefeuille (ventes positives, scope N mois filtrés) :
    parts Top 1/3/5, HHI (0-10000, seuils standards 1500/2500), courbe cumulée.
    HHI NaN si CA total ≤ 0.
    """
    out = {"Top1 %": float("nan"), "Top3 %": float("nan"), "Top5 %": float("nan"),
           "HHI": float("nan"), "Niveau": "—", "CA total": 0.0, "Nb": 0, "courbe": pd.DataFrame()}
    if df.empty or "Nom" not in df.columns or "Montant TTC" not in df.columns:
        return out
    d = ventes_positives(df[df["Année"] == annee] if "Année" in df.columns else df)
    if mois_sel and "Mois" in d.columns:
        d = d[d["Mois"].isin(mois_sel)]
    if d.empty:
        return out
    g = d.groupby("Nom")["Montant TTC"].sum().sort_values(ascending=False)
    total = float(g.sum())
    out["CA total"], out["Nb"] = total, int(len(g))
    if total <= 0:
        return out
    parts = (g / total * 100)
    out["Top1 %"] = round(float(parts.iloc[:1].sum()), 1)
    out["Top3 %"] = round(float(parts.iloc[:3].sum()), 1)
    out["Top5 %"] = round(float(parts.iloc[:5].sum()), 1)
    hhi = float(((g / total) ** 2).sum() * 10000)
    out["HHI"] = int(hhi)
    out["Niveau"] = "Faible" if hhi < 1500 else ("Modérée" if hhi < 2500 else "Élevée")
    c = pd.DataFrame({"Nom": g.index, "CA": g.values})
    c["Cumul %"] = (c["CA"].cumsum() / total * 100).round(1)
    out["courbe"] = c.head(20).reset_index(drop=True)
    return out


def volumes_panier(df: pd.DataFrame, annee_n: int, mois_sel: list = None) -> dict:
    """
    Volumes & panier (ventes positives) N vs N-1 d2d : nb factures, paniers,
    évolutions NaN-safe. Base unique avec bridge_volume_panier via _scope_d2d.
    """
    out = {"Nb N": 0, "Nb N-1": 0, "Evo Nb %": float("nan"),
           "Panier N": float("nan"), "Panier N-1": float("nan"), "Evo panier %": float("nan")}
    df_n, df_n1 = _scope_d2d(ventes_positives(df), annee_n, mois_sel)
    out["Nb N"], out["Nb N-1"] = int(len(df_n)), int(len(df_n1))
    out["Evo Nb %"] = evol_pct(out["Nb N"], out["Nb N-1"])
    if out["Nb N"] > 0:
        out["Panier N"] = round(float(df_n["Montant TTC"].sum()) / out["Nb N"], 0)
    if out["Nb N-1"] > 0:
        out["Panier N-1"] = round(float(df_n1["Montant TTC"].sum()) / out["Nb N-1"], 0)
    out["Evo panier %"] = evol_pct(out["Panier N"], out["Panier N-1"])
    return out


def business_insights(df: pd.DataFrame, annee_n: int, risk_mat: pd.DataFrame,
                      mois_sel: list = None, max_items: int = 5) -> list:
    """
    Insights déterministes (max 5, triés par impact TND décroissant).
    Chaque item : (icône, texte). Règles à seuils SEUILS, base N-1 exigée,
    CA plancher anti-bruit. Ne devine jamais : que du mesuré.
    """
    ins = []
    ca_min = SEUILS["ca_tnd_min"]

    def _push(impact, ico, txt):
        ins.append({"impact": abs(float(impact or 0.0)), "ico": ico, "txt": txt})

    if risk_mat is not None and not risk_mat.empty and "CA N" in risk_mat.columns:
        rm = risk_mat.copy()
        rm["Δ CA (TND)"] = rm["CA N"] - rm["CA N-1"]
        base = rm[(rm["CA N-1"] >= ca_min) | (rm["CA N"] >= ca_min)]
        up = base[(base["Évolution %"] >= SEUILS["hausse_sig_pct"])]
        if not up.empty:
            r = up.nlargest(1, "Δ CA (TND)").iloc[0]
            _push(r["Δ CA (TND)"], "📈",
                  f"**{r['Nom']}** en forte hausse : {fmt_pct(r['Évolution %'])} "
                  f"(+{r['Δ CA (TND)']:,.0f} TND vs N-1).")
        down = base[(base["Évolution %"] <= SEUILS["baisse_sig_pct"])]
        if not down.empty:
            r = down.nsmallest(1, "Δ CA (TND)").iloc[0]
            _push(r["Δ CA (TND)"], "📉",
                  f"**{r['Nom']}** en fort repli : {fmt_pct(r['Évolution %'])} "
                  f"({r['Δ CA (TND)']:,.0f} TND vs N-1) — à accompagner.")
        new = rm[(rm["CA N-1"] == 0) & (rm["CA N"] >= ca_min)]
        if not new.empty:
            r = new.nlargest(1, "CA N").iloc[0]
            _push(r["CA N"], "🆕",
                  f"**{r['Nom']}** : nouveau contributeur ({r['CA N']:,.0f} TND).")
        lost = rm[(rm["CA N"] == 0) & (rm["CA N-1"] >= ca_min)]
        if not lost.empty:
            r = lost.nlargest(1, "CA N-1").iloc[0]
            _push(r["CA N-1"], "🚪",
                  f"**{r['Nom']}** : plus aucune facture en {annee_n} "
                  f"({r['CA N-1']:,.0f} TND en N-1) — vérifier.")
    conc = concentration_portefeuille(df, annee_n, mois_sel)
    if pd.notna(conc["Top3 %"]) and conc["Top3 %"] >= SEUILS["concentration_top3_pct"]:
        _push(conc["CA total"] * conc["Top3 %"] / 100, "⚖️",
              f"Concentration élevée : le top 3 pèse **{conc['Top3 %']:.1f} %** du CA "
              f"(HHI {conc['HHI']}) — dépendance à surveiller.")
    vol = volumes_panier(df, annee_n, mois_sel)
    if pd.notna(vol["Evo Nb %"]) and abs(vol["Evo Nb %"]) >= SEUILS["hausse_sig_pct"]:
        sens = "hausse" if vol["Evo Nb %"] > 0 else "baisse"
        _push(0, "🧾",
              f"Volume en {sens} marquée : {fmt_pct(vol['Evo Nb %'])} factures vs N-1 "
              f"({vol['Nb N']} vs {vol['Nb N-1']}).")
    ins.sort(key=lambda x: -x["impact"])
    return [(x["ico"], x["txt"]) for x in ins[:max_items]]
