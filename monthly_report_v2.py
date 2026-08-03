# coding: utf-8
"""
Rapport Mensuel V2 — SMG Pilotage Conventions B2B
Comparaison date-à-date (N-1 tronqué au même nombre de jours que N)
Sans analyse IA — Chiffres seuls, fiables.
"""
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import argparse

from monthly_report import load_all_data, _add_date_cols, _map_magasins, MOIS_NOMS, MOIS_COURTS

SORTIE = Path.home() / "Downloads" / "rapport_mensuel"

# ── Utilitaires ──────────────────────────────────────────────────────────────

def format_k(v: float) -> str:
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.1f}k"
    return f"{v:.0f}"

def evol(n: float, n1: float) -> float:
    if n1 > 0:
        return round((n - n1) / n1 * 100, 1)
    return 100 if n > 0 else 0

def tronquer(df: pd.DataFrame, annee: int, mois: int) -> pd.DataFrame:
    """Tronque N-1 aux mêmes JOURS EXACTS que N (date-à-date)."""
    if df.empty or "Jour" not in df.columns:
        return df
    jours_n = df[(df["Annee"]==annee) & (df["Mois"]==mois)]["Jour"].unique()
    if len(jours_n) == 0:
        return df
    jours_n1 = df[(df["Annee"]==annee-1) & (df["Mois"]==mois)]["Jour"].unique()
    if len(jours_n1) == 0:
        return df
    # Garder dans N-1 uniquement les jours qui existent dans N
    jours_a_garder = set(jours_n)
    mask = (df["Annee"]==annee-1) & (df["Mois"]==mois) & (~df["Jour"].isin(jours_a_garder))
    return df[~mask]

def grouper_ca(df: pd.DataFrame, annee: int, mois: int, colonne: str = "Nom") -> pd.DataFrame:
    """CA par groupe (convention ou magasin) pour une période donnée."""
    d = df[(df["Annee"]==annee) & (df["Mois"]==mois)]
    if d.empty:
        return pd.DataFrame(columns=[colonne, "ca", "nb"])
    grp = d.groupby(colonne).agg(ca=("Montant TTC","sum"), nb=("Montant TTC","count")).reset_index()
    return grp

def fusionner(ca_n, ca_n1, colonne: str = "Nom") -> pd.DataFrame:
    """Fusionne deux groupby CA en un seul tableau comparatif."""
    cols = {colonne: colonne, "ca": "ca_n", "nb": "nb_n"}
    n  = ca_n.rename(columns=cols)
    n1 = ca_n1.rename(columns={colonne: colonne, "ca": "ca_n1", "nb": "nb_n1"})
    comp = n.merge(n1, on=colonne, how="outer").fillna(0)
    comp["evol"] = comp.apply(
        lambda r: round((r["ca_n"]-r["ca_n1"])/r["ca_n1"]*100, 1)
        if r["ca_n1"] > 0 else (100 if r["ca_n"] > 0 else 0), axis=1
    )
    return comp.sort_values("ca_n", ascending=False).reset_index(drop=True)

# ── HTML ─────────────────────────────────────────────────────────────────────

ARROW_UP = "&#9650;"   # ▲
ARROW_DOWN = "&#9660;" # ▼

def cell_evol(v: float) -> str:
    cls = "green" if v >= 0 else "red"
    arr = ARROW_UP if v >= 0 else ARROW_DOWN
    return f'<span class="{cls}">{arr} {abs(v):.1f}%</span>'

def tr(*cells, cls="") -> str:
    c = f' class="{cls}"' if cls else ""
    return f"<tr{c}>" + "".join(f"<td>{x}</td>" if not x.startswith("<td") else x for x in cells) + "</tr>"

def td(v, cls="") -> str:
    c = f' class="{cls}"' if cls else ""
    return f"<td{c}>{v}</td>"

def generer_html(data: dict) -> str:
    m, a = data["mois"], data["annee"]
    mn = MOIS_NOMS.get(m, str(m))
    mc = MOIS_COURTS.get(m, str(m))
    an1 = a - 1
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")

    # ── KPI rows ──
    kpi_def = [
        ("CA TTC Conventions", data["ca_conv"], data["ca_conv_n1"], data["var_conv"], " TND"),
        ("CA TTC EDC",         data["ca_edc"], data["ca_edc_n1"], data["var_edc"], " TND"),
        ("CA Total Combiné",   data["ca_total"], data["ca_total_n1"], data["var_total"], " TND"),
        ("Nombre de dossiers", data["nb_conv"], data["nb_conv_n1"], data["var_nb_conv"], ""),
        ("Panier moyen",       data["panier_conv"], data["panier_conv_n1"], data["var_panier"], " TND"),
    ]
    kpi_rows = ""
    for label, n, n1, v, unit in kpi_def:
        f_n  = format_k(n) if abs(n) >= 1000 else f"{n:.0f}"
        f_n1 = format_k(n1) if abs(n1) >= 1000 else f"{n1:.0f}"
        kpi_rows += f"<tr><td class='kpi-label'>{label}</td>{td(f_n+unit,'num')}{td(f_n1+unit,'num')}{td(cell_evol(v),'num')}</tr>"

    # Lignes actives / magasins (format différent)
    for label, curr, prev, diff_val in [
        ("Conventions actives", data["conv_actives"], data["conv_actives_n1"], data["diff_actives"]),
        ("Magasins contributeurs", data["mag_contributeurs"], data["mag_contributeurs_n1"], data["diff_magasins"]),
    ]:
        cls = "green" if diff_val >= 0 else "red"
        sign = "+" if diff_val >= 0 else ""
        kpi_rows += f"<tr><td class='kpi-label'>{label}</td>{td(int(curr),'num')}{td(int(prev),'num')}{td(f'<span class=\"{cls}\">{sign}{diff_val}</span>','num')}</tr>"

    # ── TOP / FLOP ──
    convs = data["conventions"]
    top5 = convs.head(5)
    flop5 = convs[convs["ca_n1"] > 0].tail(5).sort_values("evol")  # pires évolutions
    top_rows = flop_rows = ""
    for i, (_, r) in enumerate(top5.iterrows(), 1):
        top_rows += f"<tr><td class='rank'>#{i}</td><td>{r['Nom']}</td><td class='num'>{format_k(r['ca_n'])} TND</td></tr>"
    for _, r in flop5.iterrows():
        flop_rows += f"<tr><td>{r['Nom']}</td><td class='num'>{format_k(r['ca_n1'])} TND</td><td class='num'>{cell_evol(r['evol'])}</td></tr>"

    # ── Analyse par convention ──
    conv_rows = ""
    for _, r in convs.iterrows():
        conv_rows += f"<tr><td>{r['Nom']}</td>{td(format_k(r['ca_n'])+' TND','num')}{td(format_k(r['ca_n1'])+' TND','num')}{td(cell_evol(r['evol']),'num')}{td(int(r['nb_n']),'num')}</tr>"

    # ── Magasins ──
    mag_rows = ""
    for _, r in data["magasins"].head(15).iterrows():
        mag_rows += f"<tr><td>{r['Magasin']}</td>{td(format_k(r['ca_n'])+' TND','num')}{td(format_k(r['ca_n1'])+' TND','num')}{td(cell_evol(r['evol']),'num')}</tr>"

    # ── EDC ──
    # (déjà inclus dans les KPIs généraux)

    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Rapport Mensuel — {mn} {a}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; font-size:13px; color:#1E293B; background:#F1F5F9; line-height:1.5; }}
.container {{ max-width:960px; margin:0 auto; padding:20px; }}

/* Header */
.header {{ background:linear-gradient(135deg,#0B1E3F,#1A3460); border-radius:12px; padding:24px 28px; margin-bottom:20px; color:#FFF; }}
.header .badge {{ display:inline-block; background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2); color:#E2E8F0; font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; padding:4px 12px; border-radius:20px; margin-bottom:12px; }}
.header h1 {{ font-size:22px; font-weight:700; margin-bottom:4px; }}
.header .sub {{ font-size:12px; color:#94A3B8; }}
.header .tag {{ display:inline-block; font-size:10px; padding:2px 8px; border-radius:4px; background:rgba(22,163,74,0.2); color:#86EFAC; margin-left:8px; }}

/* Sections */
.section {{ background:#FFF; border-radius:8px; padding:20px 24px; margin-bottom:16px; box-shadow:0 1px 2px rgba(0,0,0,0.06); }}
.section-title {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:1.2px; color:#64748B; margin-bottom:14px; padding-bottom:8px; border-bottom:2px solid #E2E8F0; }}

/* Layout */
.row {{ display:flex; gap:16px; }}
.col {{ flex:1; }}
@media (max-width:700px) {{ .row {{ flex-direction:column; }} }}

/* Tables */
table {{ width:100%; border-collapse:collapse; font-size:13px; margin-bottom:4px; }}
th {{ text-align:left; font-size:10px; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.8px; padding:8px 6px; border-bottom:2px solid #E2E8F0; }}
td {{ padding:8px 6px; border-bottom:1px solid #F1F5F9; vertical-align:top; }}
.num {{ text-align:right; font-weight:600; font-variant-numeric:tabular-nums; font-family:'SF Mono','Cascadia Code','Consolas',monospace; font-size:12px; }}
.rank {{ color:#64748B; font-weight:700; font-size:12px; text-align:center; width:36px; }}

/* Colors */
.green {{ color:#059669; font-weight:600; }}
.red {{ color:#DC2626; font-weight:600; }}
.kpi-label {{ font-weight:600; color:#334155; }}

/* Striped tables */
tr:nth-child(even) {{ background:#F8FAFC; }}
thead tr {{ background:transparent; }}

/* Tooltip info */
.info {{ font-size:11px; color:#94A3B8; padding:4px 0 8px; }}

/* Footer */
.footer {{ text-align:center; font-size:11px; color:#94A3B8; padding:16px 0; }}
.footer strong {{ color:#64748B; }}

@media (prefers-color-scheme:dark) {{
body {{ background:#0F172A; color:#E2E8F0; }}
.section {{ background:#1E293B; }}
th {{ color:#64748B; border-color:#334155; }}
td {{ border-color:#334155; }}
tr:nth-child(even) {{ background:#1A2538; }}
.kpi-label {{ color:#94A3B8; }}
.rank {{ color:#64748B; }}
}}
</style>
</head>
<body>
<div class="container">

<!-- ═══ HEADER ═══ -->
<div class="header">
<div class="badge">Rapport Mensuel — Pilotage B2B</div>
<h1>MG &amp; BATAM — Conventions <span class="tag">Date-à-Date</span></h1>
<div class="sub">{mn} {a} &nbsp;|&nbsp; Généré le {now} &nbsp;|&nbsp; Comparaison N vs N-1 tronquée</div>
</div>

<!-- ═══ SECTION 1 : PERFORMANCE ═══ -->
<div class="section">
<div class="section-title">&#128202; Performance Globale — Synthèse</div>
<table>
<thead><tr><th>Indicateur</th><th class="num">{mc.upper()} {a}</th><th class="num">{mc.upper()} {an1}</th><th class="num">Variation</th></tr></thead>
<tbody>{kpi_rows}</tbody>
</table>
</div>

<!-- ═══ SECTION 2 : TOP / FLOP ═══ -->
<div class="section">
<div class="section-title">&#127942; Top 5 Conventions</div>
<table><thead><tr><th>#</th><th>Convention</th><th class="num">CA {mc.upper()} {a}</th></tr></thead>
<tbody>{top_rows}</tbody></table>
<div style="height:16px"></div>
<details>
<summary style="cursor:pointer;font-size:12px;font-weight:600;color:#64748B;">&#128200; Voir les conventions en baisse</summary>
<table style="margin-top:8px;"><thead><tr><th>Convention</th><th class="num">CA {mc.upper()} {an1}</th><th class="num">Évolution</th></tr></thead>
<tbody>{flop_rows}</tbody></table>
</details>
</div>

<!-- ═══ SECTION 3 : ANALYSE PAR CONVENTION ═══ -->
<div class="section">
<div class="section-title">&#128203; Analyse par Convention</div>
<div class="info">Toutes les conventions classées par CA {mc.upper()} {a} décroissant — N-1 tronqué au même nombre de jours que N</div>
<table>
<thead><tr><th>Convention</th><th class="num">CA {mc.upper()} {a}</th><th class="num">CA {mc.upper()} {an1}</th><th class="num">Évolution</th><th class="num">Dossiers</th></tr></thead>
<tbody>{conv_rows}</tbody>
</table>
</div>

<!-- ═══ SECTION 4 : MAGASINS ═══ -->
<div class="section">
<div class="section-title">&#127980; Analyse par Magasin (Top 15)</div>
<table>
<thead><tr><th>Magasin</th><th class="num">CA {mc.upper()} {a}</th><th class="num">CA {mc.upper()} {an1}</th><th class="num">Évolution</th></tr></thead>
<tbody>{mag_rows}</tbody>
</table>
</div>

<!-- ═══ SECTION 5 : EDC ═══ -->
<div class="section">
<div class="section-title">&#127891; Convention EDC — Éducation Nationale</div>
<table>
<thead><tr><th>Indicateur</th><th class="num">{mc.upper()} {a}</th><th class="num">{mc.upper()} {an1}</th><th class="num">Variation</th></tr></thead>
<tbody>
<tr><td class="kpi-label">CA EDC</td><td class="num">{format_k(data['ca_edc'])} TND</td><td class="num">{format_k(data['ca_edc_n1'])} TND</td><td class="num">{cell_evol(data['var_edc'])}</td></tr>
<tr><td class="kpi-label">Nombre de dossiers</td><td class="num">{int(data['nb_edc'])}</td><td class="num">{int(data['nb_edc_n1'])}</td><td class="num">{cell_evol(data['var_nb_edc'])}</td></tr>
<tr><td class="kpi-label">Panier moyen</td><td class="num">{data['panier_edc']:.0f} TND</td><td class="num">{data['panier_edc_n1']:.0f} TND</td><td class="num">{cell_evol(data['var_panier_edc'])}</td></tr>
</tbody>
</table>
</div>

<!-- ═══ FOOTER ═══ -->
<div class="footer">
<strong>SMG — Pilotage Grands Comptes</strong><br>
Rapport généré le {now}<br>
<em>Comparaison date-à-date : les données de N-1 sont tronquées au même nombre de jours que N pour une comparaison équitable.</em>
</div>

</div>
</body>
</html>"""
    return html

# ── Texte ────────────────────────────────────────────────────────────────────

def generer_texte(data: dict) -> str:
    m, a = data["mois"], data["annee"]
    mn = MOIS_NOMS.get(m, str(m))
    mc = MOIS_COURTS.get(m, str(m))
    an1 = a - 1
    now = datetime.now().strftime("%d/%m/%Y à %H:%M")

    convs = data["conventions"]
    top5 = convs.head(5)
    flop5 = convs[convs["ca_n1"] > 0].tail(5).sort_values("evol")

    lines = []
    lines.append(f"RAPPORT MENSUEL — {mn.upper()} {a}".center(70))
    lines.append("MG & BATAM — Pilotage Conventions B2B".center(70))
    lines.append("Comparaison date-à-date (N-1 tronqué au même nombre de jours que N)".center(70))
    lines.append("="*70)
    lines.append(f"Généré le {now}")
    lines.append("="*70)
    lines.append("")

    # KPIs
    lines.append("1. PERFORMANCE GLOBALE")
    lines.append("-"*70)
    for label, val in [
        (f"CA TTC Conventions", f"{format_k(data['ca_conv'])} TND ({data['var_conv']:+.1f}%)"),
        (f"CA TTC EDC", f"{format_k(data['ca_edc'])} TND ({data['var_edc']:+.1f}%)"),
        (f"CA Total Combiné", f"{format_k(data['ca_total'])} TND ({data['var_total']:+.1f}%)"),
        (f"Nbre de dossiers", f"{int(data['nb_conv'])} ({data['var_nb_conv']:+.1f}%)"),
        (f"Panier moyen", f"{data['panier_conv']:.0f} TND ({data['var_panier']:+.1f}%)"),
        (f"Conventions actives", f"{int(data['conv_actives'])} (N-1: {int(data['conv_actives_n1'])})"),
        (f"Magasins contributeurs", f"{int(data['mag_contributeurs'])} (N-1: {int(data['mag_contributeurs_n1'])})"),
    ]:
        lines.append(f"  {label:<35} {val}")
    lines.append("")

    # Top 5
    lines.append("2. TOP 5 CONVENTIONS")
    for i, (_, r) in enumerate(top5.iterrows(), 1):
        lines.append(f"  {i}. {r['Nom']:<35} {format_k(r['ca_n']):>8} TND ({r['evol']:+.1f}%)")
    lines.append("")

    # Analyse par convention (limitée aux 20 premières pour lisibilité)
    lines.append("3. ANALYSE PAR CONVENTION (Top 20)")
    lines.append("-"*100)
    lines.append(f"{'Convention':<35} {mc.upper()} {a:<12} {mc.upper()} {an1:<12} Évolution   Doss.")
    lines.append("-"*100)
    for _, r in convs.head(20).iterrows():
        ev = r["evol"]
        arrow = "+" if ev >= 0 else "-"
        lines.append(f"{r['Nom']:<35} {format_k(r['ca_n']):>8} TND  {format_k(r['ca_n1']):>8} TND  {arrow}{abs(ev):>7.1f}%  {int(r['nb_n']):>4}")
    lines.append("")

    # EDC
    lines.append("4. CONVENTION EDC — ÉDUCATION NATIONALE")
    lines.append(f"  CA EDC      : {format_k(data['ca_edc'])} TND ({data['var_edc']:+.1f}%)")
    lines.append(f"  Nb dossiers : {int(data['nb_edc'])} ({data['var_nb_edc']:+.1f}%)")
    lines.append(f"  Panier moyen: {data['panier_edc']:.0f} TND")
    lines.append("")
    lines.append("="*70)
    lines.append(f"SMG — Pilotage Grands Comptes | Généré le {now}")
    lines.append("Comparaison date-à-date : N-1 tronqué au même nombre de jours que N")

    return "\n".join(lines)

# ── Point d'entrée ──────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Rapport Mensuel V2 (sans IA)")
    parser.add_argument("--month", type=int)
    parser.add_argument("--year", type=int)
    parser.add_argument("--no-email", action="store_true")
    args = parser.parse_args()

    today = datetime.now()
    if args.month is None:
        mois = today.month - 1 or 12
        annee = today.year - (1 if today.month == 1 else 0)
    else:
        mois = args.month
        annee = args.year or today.year
    annee_n1 = annee - 1

    print(f"\n{'='*60}")
    print(f"  RAPPORT MENSUEL V2 — {MOIS_NOMS.get(mois,'?').upper()} {annee}")
    print(f"{'='*60}")

    print("\n  Chargement des données...")
    dfs = load_all_data()
    code_df = dfs.get("code_magasin", pd.DataFrame())
    df_vc = _map_magasins(_add_date_cols(dfs.get("vc", pd.DataFrame())), code_df)
    df_edc = _add_date_cols(dfs.get("vc_edc", pd.DataFrame()))

    if df_vc.empty and df_edc.empty:
        print("  ❌ Aucune donnée chargée.")
        return

    print("  Application de la troncature date-à-date...")
    df_vc_d2d = tronquer(df_vc, annee, mois)
    df_edc_d2d = tronquer(df_edc, annee, mois)

    # Calculs
    def _ca(df, a, m): return df[(df["Annee"]==a)&(df["Mois"]==m)]["Montant TTC"].sum()
    def _nb(df, a, m): return len(df[(df["Annee"]==a)&(df["Mois"]==m)])
    def _pm(df, a, m):
        s = df[(df["Annee"]==a)&(df["Mois"]==m)]["Montant TTC"]
        return s.mean() if len(s) > 0 else 0
    def _act(df, a, m):
        return df[(df["Annee"]==a)&(df["Mois"]==m)&(df["Montant TTC"]>0)]["Nom"].nunique()
    def _mag(df, a, m):
        return df[(df["Annee"]==a)&(df["Mois"]==m)&(df["Montant TTC"]>0)]["Magasin"].nunique()

    ca_conv  = _ca(df_vc_d2d, annee, mois)
    ca_conv1 = _ca(df_vc_d2d, annee_n1, mois)
    ca_edc   = _ca(df_edc_d2d, annee, mois)
    ca_edc1  = _ca(df_edc_d2d, annee_n1, mois)

    data = {
        "mois": mois, "annee": annee, "annee_n1": annee_n1,
        "mois_nom": MOIS_NOMS.get(mois, ""),
        "ca_conv": ca_conv, "ca_conv_n1": ca_conv1, "var_conv": evol(ca_conv, ca_conv1),
        "ca_edc": ca_edc, "ca_edc_n1": ca_edc1, "var_edc": evol(ca_edc, ca_edc1),
        "ca_total": ca_conv + ca_edc, "ca_total_n1": ca_conv1 + ca_edc1,
        "var_total": evol(ca_conv + ca_edc, ca_conv1 + ca_edc1),
        "nb_conv": _nb(df_vc_d2d, annee, mois), "nb_conv_n1": _nb(df_vc_d2d, annee_n1, mois),
        "var_nb_conv": evol(_nb(df_vc_d2d,annee,mois), _nb(df_vc_d2d,annee_n1,mois)),
        "panier_conv": _pm(df_vc_d2d, annee, mois), "panier_conv_n1": _pm(df_vc_d2d, annee_n1, mois),
        "var_panier": evol(_pm(df_vc_d2d,annee,mois), _pm(df_vc_d2d,annee_n1,mois)),
        "conv_actives": _act(df_vc_d2d, annee, mois), "conv_actives_n1": _act(df_vc_d2d, annee_n1, mois),
        "diff_actives": int(_act(df_vc_d2d,annee,mois) - _act(df_vc_d2d,annee_n1,mois)),
        "mag_contributeurs": _mag(df_vc_d2d, annee, mois), "mag_contributeurs_n1": _mag(df_vc_d2d, annee_n1, mois),
        "diff_magasins": int(_mag(df_vc_d2d,annee,mois) - _mag(df_vc_d2d,annee_n1,mois)),
        "nb_edc": _nb(df_edc_d2d, annee, mois), "nb_edc_n1": _nb(df_edc_d2d, annee_n1, mois),
        "var_nb_edc": evol(_nb(df_edc_d2d,annee,mois), _nb(df_edc_d2d,annee_n1,mois)),
        "panier_edc": _pm(df_edc_d2d, annee, mois), "panier_edc_n1": _pm(df_edc_d2d, annee_n1, mois),
        "var_panier_edc": evol(_pm(df_edc_d2d,annee,mois), _pm(df_edc_d2d,annee_n1,mois)),
    }

    # Conventions & Magasins
    ca_n  = grouper_ca(df_vc_d2d, annee, mois, "Nom")
    ca_n1 = grouper_ca(df_vc_d2d, annee_n1, mois, "Nom")
    data["conventions"] = fusionner(ca_n, ca_n1, "Nom")

    ca_m_n  = grouper_ca(df_vc_d2d, annee, mois, "Magasin")
    ca_m_n1 = grouper_ca(df_vc_d2d, annee_n1, mois, "Magasin")
    data["magasins"] = fusionner(ca_m_n, ca_m_n1, "Magasin")

    # Debug ONAS
    onas = data["conventions"][data["conventions"]["Nom"] == "O N A S"]
    if not onas.empty:
        r = onas.iloc[0]
        print(f"\n  ✅ ONAS : {r['ca_n']:.0f} TND vs {r['ca_n1']:.0f} TND → {r['evol']:+.1f}%")
    else:
        print("\n  ⚠️  ONAS non trouvé")

    # Debug Total CA
    print(f"  ✅ CA Total : {format_k(data['ca_total'])} TND vs {format_k(data['ca_total_n1'])} TND → {data['var_total']:+.1f}%")
    print(f"  ✅ Conventions actives : {data['conv_actives']} (N-1: {data['conv_actives_n1']})")
    print(f"  ✅ Magasins : {data['mag_contributeurs']} (N-1: {data['mag_contributeurs_n1']})")

    # Génération HTML
    print("\n  Génération du rapport HTML...")
    html = generer_html(data)
    SORTIE.mkdir(parents=True, exist_ok=True)
    fichier = SORTIE / f"rapport_v2_{annee}_{mois:02d}.html"
    fichier.write_text(html, encoding="utf-8")
    print(f"  ✅ {fichier}")

    # Texte
    texte = generer_texte(data)
    fichier_txt = SORTIE / f"rapport_v2_{annee}_{mois:02d}.txt"
    fichier_txt.write_text(texte, encoding="utf-8")
    print(f"  ✅ {fichier_txt}")

    print(f"\n{'='*60}")
    print(f"  TERMINÉ — {MOIS_NOMS.get(mois,'?').upper()} {annee}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()
