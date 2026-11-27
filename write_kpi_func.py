content = '''
def poids_convention_cube(df_cube_mag, df_vc, annee, mois=None):
    """Compute convention weight from Cube Magasin + VC data.

    Parameters
    ----------
    df_cube_mag : DataFrame
        Cube Magasin with columns: Date, Année, Mois, Jour, Magasin,
        Enseigne, CA Magasin (daily granularity).
    df_vc : DataFrame
        VC data with columns: Type de vente, Montant TTC, Date comptabilisation,
        Magasin, Enseigne.
    annee : int
        Year to filter.
    mois : int, list of ints, or None, optional
        Month(s) to filter.

    Returns
    -------
    dict
        Keys: poids_pct, ca_conv, ca_total, ca_comptant, nb_alertes, jours, periode, detail.
    """
    out = {
        "poids_pct": float("nan"),
        "ca_conv": 0.0,
        "ca_total": 0.0,
        "ca_comptant": 0.0,
        "nb_alertes": 0,
        "jours": 0,
        "periode": f"{annee}",
        "detail": pd.DataFrame(),
    }
    # Handle empty inputs
    if df_cube_mag is None or df_cube_mag.empty or df_vc is None or df_vc.empty:
        return out
    # Handle missing columns in cube
    cube_required = ["Date", "Année", "Mois", "Jour", "Magasin", "CA Magasin"]
    for col in cube_required:
        if col not in df_cube_mag.columns:
            return out
    # Handle missing columns in VC
    vc_required = ["Type de vente", "Montant TTC", "Date comptabilisation", "Magasin"]
    for col in vc_required:
        if col not in df_vc.columns:
            return out
    # Filter by year
    df_cube = df_cube_mag[df_cube_mag["Année"] == annee].copy()
    # Filter by month
    if mois is not None:
        if "Mois" in df_cube.columns:
            df_cube = df_cube[df_cube["Mois"].isin(mois)]
        if "Mois" in df_vc.columns:
            df_vc = df_vc[df_vc["Mois"].isin(mois)]
    # Filter convention (VC.CONV.)
    if "Type de vente" in df_vc.columns:
        df_vc = df_vc[df_vc["Type de vente"] == "VC.CONV."]
    # Normalize magasin names
    df_cube["Magasin_norm"] = df_cube["Magasin"].map(_norm_magasin)
    df_vc["Magasin_norm"] = df_vc["Magasin"].map(_norm_magasin)
    # CA_total per (magasin, jour) from Cube Magasin
    ca_total_daily = (
        df_cube.groupby(["Magasin_norm", "Jour"])["CA Magasin"]
        .sum()
        .reset_index()
    )
    ca_total_daily.columns = ["Magasin", "Jour", "CA_Total"]
    # CA_conv per (magasin, jour) from VC convention
    if not df_vc.empty and "Montant TTC" in df_vc.columns:
        df_vc["Jour"] = pd.to_datetime(df_vc["Date comptabilisation"], errors="coerce").dt.day
        df_vc["Magasin_norm"] = df_vc["Magasin"].map(_norm_magasin)
        ca_conv_daily = (
            df_vc.groupby(["Magasin_norm", "Jour"])["Montant TTC"]
            .sum()
            .reset_index()
        )
        ca_conv_daily.columns = ["Magasin", "Jour", "CA_Conv"]
    else:
        ca_conv_daily = pd.DataFrame(columns=["Magasin", "Jour", "CA_Conv"])
    # Merge
    if not ca_total_daily.empty and not ca_conv_daily.empty:
        daily_merge = ca_total_daily.merge(ca_conv_daily, on=["Magasin", "Jour"], how="outer").fillna(0)
    elif not ca_total_daily.empty:
        daily_merge = ca_total_daily.copy()
        daily_merge["CA_Conv"] = 0
    elif not ca_conv_daily.empty:
        daily_merge = ca_conv_daily.copy()
        daily_merge["CA_Total"] = 0
    else:
        daily_merge = pd.DataFrame(columns=["Magasin", "Jour", "CA_Total", "CA_Conv"])
    # Global values
    ca_total = float(daily_merge["CA_Total"].sum())
    ca_conv = float(daily_merge["CA_Conv"].sum())
    ca_comptant = float(ca_total - ca_conv)
    poids_pct = round(ca_conv / ca_total * 100, 1) if ca_total > 0 else float("nan")
    # Alerts: magasins where CA_conv > CA_total
    if not daily_merge.empty:
        mag_totals = daily_merge.groupby("Magasin").agg(
            CA_Total_mag=("CA_Total", "sum"),
            CA_Conv_mag=("CA_Conv", "sum"),
        )
        nb_alertes = int((mag_totals["CA_Conv_mag"] > mag_totals["CA_Total_mag"]).sum())
    else:
        nb_alertes = 0
    # Detail DataFrame
    if not daily_merge.empty:
        detail = daily_merge.groupby("Magasin").agg(
            CA_Total=("CA_Total", "sum"),
            CA_Conv=("CA_Conv", "sum"),
        ).reset_index()
        detail["CA_Comptant"] = detail["CA_Total"] - detail["CA_Conv"]
        detail["Poids %"] = np.where(detail["CA_Total"] > 0,
                                     detail["CA_Conv"] / detail["CA_Total"] * 100, np.nan)
        detail = detail.sort_values("CA_Total", ascending=False).reset_index(drop=True)
    else:
        detail = pd.DataFrame(columns=["Magasin", "CA_Total", "CA_Conv", "CA_Comptant", "Poids %"])
    out["ca_total"] = ca_total
    out["ca_conv"] = ca_conv
    out["ca_comptant"] = ca_comptant
    out["poids_pct"] = poids_pct
    out["nb_alertes"] = nb_alertes
    out["detail"] = detail
    return out
'''

path = r'C:/Users/hachk/pilotage_b2b/metrics/kpi.py'
with open(path, 'a', encoding='utf-8') as f:
    f.write(content)
print('Fonction ajoutee avec succes')
