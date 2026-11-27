"""
Smoke-test du lot « P0 complet + veille 7j + CA à risque ».
Valide : sémantique NaN sans base N-1, troncature unique, helpers,
matrice de risque, conventions inactives + CA N-1, charts NaN-safe.
"""
import sys
import math

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # console Windows cp1252
sys.path.insert(0, r"C:\Users\hachk\pilotage_b2b")

import pandas as pd

from metrics.kpi import (
    evol_pct, fmt_pct, color_delta,
    compare_years_date_to_date, ca_sum_date_to_date,
    convention_risk_matrix, inactive_conventions,
    truncate_n1_date_to_date,
    nb_factures, panier_moyen, bridge_volume_panier,
    run_rate_fin_annee, data_health,
    objectif_tracking, cohortes_conventions, narratif_executif,
    ventes_positives, concentration_portefeuille, volumes_panier, business_insights,
)
from charts.factory import chart_variation_bar, chart_risk_table, chart_bridge
from trend_alert_panel import _fmt_pct
from data.config import SEUILS

FAILS = []


def check(name, cond, extra=""):
    status = "PASS" if cond else "FAIL"
    if not cond:
        FAILS.append(name)
    print(f"[{status}] {name}" + (f" — {extra}" if extra else ""))


# ── 1. Helpers « sans base N-1 » ────────────────────────────────
check("evol_pct sans base → NaN", math.isnan(evol_pct(100, 0)))
check("evol_pct normal = +50%", evol_pct(150, 100) == 50.0)
check("fmt_pct(NaN) → « — »", fmt_pct(float("nan")) == "—")
check("fmt_pct(+50) → « +50.0% »", fmt_pct(50.0) == "+50.0%")
check("color_delta(NaN) → off", color_delta(float("nan")) == "off")
check("color_delta(+5) → normal", color_delta(5.0) == "normal")
check("color_delta(-5) → inverse", color_delta(-5.0) == "inverse")

# ── 2. Données synthétiques ────────────────────────────────────
rows = []
for d in (1, 2, 3):  # N = 2026, 3 jours de factures
    rows.append({"Date": pd.Timestamp(2026, 9, d), "Année": 2026, "Mois": 9, "Jour": d,
                 "Nom": "ConvA", "Montant TTC": 100.0})
for d, m in ((1, 100.0), (2, 100.0), (3, 100.0), (10, 500.0), (20, 500.0)):
    rows.append({"Date": pd.Timestamp(2025, 9, d), "Année": 2025, "Mois": 9, "Jour": d,
                 "Nom": "ConvA", "Montant TTC": m})
rows.append({"Date": pd.Timestamp(2026, 9, 4), "Année": 2026, "Mois": 9, "Jour": 4,
             "Nom": "ConvB", "Montant TTC": 42.0})  # nouvelle : zéro base N-1
df = pd.DataFrame(rows)

# ── 3. compare_years_date_to_date (source des KPI df_comp) ─────
comp = compare_years_date_to_date(df, 2026, 2025, [9])
check("d2d CA N-1 tronqué aux jours N (300)", comp["CA N-1"].iloc[0] == 300.0,
      f"obtenu {comp['CA N-1'].iloc[0]}")
check("d2d CA N = 342", comp["CA N"].iloc[0] == 342.0, f"obtenu {comp['CA N'].iloc[0]}")
expected_evo = round((342 - 300) / 300 * 100, 1)
check("d2d Variation % = +14.0", comp["Variation %"].iloc[0] == expected_evo,
      f"obtenu {comp['Variation %'].iloc[0]}")

# ── 4. ca_sum_date_to_date sans base → NaN (plus de faux +100%) ─
conv_b = df[df["Nom"] == "ConvB"]
ca_n, ca_n1, evo = ca_sum_date_to_date(conv_b, 2026, 2025, [9])
check("ca_sum sans base → NaN", math.isnan(evo), f"ca_n={ca_n}, ca_n1={ca_n1}")
check("fmt_pct(evo dashboard) → « — »", fmt_pct(evo) == "—")

# ── 5. Troncature unique ───────────────────────────────────────
trunc = truncate_n1_date_to_date(df, 2026, 2025, [9])
n1 = trunc[trunc["Année"] == 2025]
check("truncate : jours 10/20 de N-1 supprimés", sorted(n1["Jour"].tolist()) == [1, 2, 3],
      f"obtenu {sorted(n1['Jour'].tolist())}")
check("truncate : total N-1 = 300", n1["Montant TTC"].sum() == 300.0)

# ── 6. Matrice de risque ───────────────────────────────────────
rm = convention_risk_matrix(df, 2026)
row_b = rm[rm["Nom"] == "ConvB"].iloc[0]
check("risque : ConvB = Nouveau", "Nouveau" in row_b["Statut"], row_b["Statut"])
check("risque : ConvB Évolution % = NaN", pd.isna(row_b["Évolution %"]))
row_a = rm[rm["Nom"] == "ConvA"].iloc[0]
check("risque : ConvA statut stable/croissance",
      row_a["Statut"] in ("🟢 Croissance", "🟡 Déclin", "🔴 Déclin fort", "🟢 Nouveau"),
      row_a["Statut"])

# ── 7. Inactives + CA à risque ─────────────────────────────────
today = pd.Timestamp.today().normalize()
inac_df = pd.DataFrame({
    "Nom": ["Inact", "Inact", "Live", "Live"],
    "Date": [today - pd.Timedelta(days=100), today - pd.Timedelta(days=90),
             today - pd.Timedelta(days=1), today],
    "Année": [2025, 2025, 2026, 2026],
    "Montant TTC": [100.0, 50.0, 200.0, 300.0],
})
out = inactive_conventions(inac_df, 60, annee_n=2026)
check("inactives : 1 convention (Inact)", len(out) == 1 and out.iloc[0]["Convention"] == "Inact")
check("inactives : CA N-1 à risque = 150",
      len(out) == 1 and abs(float(out.iloc[0]["CA N-1"]) - 150.0) < 1e-9,
      f"obtenu {out['CA N-1'].tolist() if len(out) else 'empty'}")
out_legacy = inactive_conventions(inac_df, 60)
check("inactives : sans annee_n, pas de colonne CA N-1",
      "CA N-1" not in out_legacy.columns)

# ── 8. Charts NaN-safe ─────────────────────────────────────────
cdf = pd.DataFrame({"Nom": ["A", "B", "C"], "Évolution %": [10.0, float("nan"), -5.0]})
fig = chart_variation_bar(cdf, "Nom", "Évolution %", "T")
check("variation_bar : figure construite", fig is not None and len(fig.data) == 1)
check("variation_bar : label NaN → « — »", "—" in list(fig.data[0].text),
      str(list(fig.data[0].text)))
figt = chart_risk_table(rm, 2026, "T")
evo_cells = list(figt.data[0].cells.values[3])
check("risk_table : cellule NaN → « — »", "—" in evo_cells, str(evo_cells))

# ── 9. Fenêtre veille 7j : gestion 29 février ──────────────────
d = (pd.Timestamp(pd.Timestamp(2024, 2, 29).date()) - pd.DateOffset(years=1)).date()
check("DateOffset(years=1) gère le 29/02 → 28/02/2023", d.isoformat() == "2023-02-28",
      d.isoformat())

# ══════════════════════════════════════════════════════════════
# LOT P1 — SEUILS, bridge, run-rate, santé, chart_bridge
# ══════════════════════════════════════════════════════════════

# ── 10. SEUILS centralisés ───────────────────────────────────
check("SEUILS inactivite_jours = 60", SEUILS["inactivite_jours"] == 60)
check("SEUILS declin_fort_pct = -20", SEUILS["declin_fort_pct"] == -20)
check("SEUILS alerte_veille_pct = -20", SEUILS["alerte_veille_pct"] == -20)
_dflt = inactive_conventions(df)  # défaut = SEUILS
check("inactive_conventions() défaut = SEUILS (60j)", True)  # ne plante pas sans seuil
check("evol_pct(NaN, 100) → NaN", math.isnan(evol_pct(float("nan"), 100)))
check("evol_pct(100, NaN) → NaN", math.isnan(evol_pct(100, float("nan"))))
check("evol_pct(None, 100) → NaN", math.isnan(evol_pct(None, 100)))

# ── 11. Bridge volume × panier ───────────────────────────────
# Données : N = 4 factures / 342 (3×100 + 42) ; N-1 tronquée = 3×100 (300).
check("nb_factures N = 4", nb_factures(df, 2026, [9]) == 4, str(nb_factures(df, 2026, [9])))
check("nb_factures N-1 tronquée = 3", nb_factures(
    truncate_n1_date_to_date(df, 2026, 2025, [9]), 2025, [9]) == 3)
check("panier_moyen N = 85.5", panier_moyen(df, 2026, [9]) == 85.5,
      str(panier_moyen(df, 2026, [9])))
check("panier_moyen vide → NaN", math.isnan(panier_moyen(df.iloc[0:0], 2026)))
br = bridge_volume_panier(df, 2026, [9])
_beff = br.set_index("Étape")["Effet (TND)"]
_bval = br.set_index("Étape")["Valeur"]
_tot_bridge = _beff["+ Volume"] + _beff["+ Panier"] + _beff["+ Mix"]
check("bridge : vol+panier+mix = ΔCA exact",
      abs(_tot_bridge - _beff["= CA N"]) < 1.5,
      f"effets={_tot_bridge} vs Δ={_beff['= CA N']}")
check("bridge : effet volume = (4-3)×100 = +100", _beff["+ Volume"] == 100.0,
      str(_beff["+ Volume"]))
check("bridge : effet panier = 3×(85.5-100) ≈ -44 (arrondi TND)", _beff["+ Panier"] == -44.0,
      str(_beff["+ Panier"]))
check("bridge : effet mix = 1×(-14.5) ≈ -14 (arrondi TND)", _beff["+ Mix"] == -14.0,
      str(_beff["+ Mix"]))
check("bridge : niveaux Valeur = [300, 100, -43.5→-44, -14.5→-14, 342]",
      _bval["CA N-1"] == 300.0 and _bval["= CA N"] == 342.0
      and _bval["+ Volume"] == 100.0,
      str(_bval.tolist()))
br_nobase = bridge_volume_panier(df[df["Année"] == 2026], 2026, [9])  # pas de N-1
_bnb = br_nobase.set_index("Étape")["Effet (TND)"]
_bnbv = br_nobase.set_index("Étape")["Valeur"]
check("bridge sans base : effets NaN", math.isnan(_bnb["+ Volume"]) and math.isnan(_bnb["+ Panier"]))
check("bridge sans base : niveaux NaN", math.isnan(_bnbv["CA N-1"]) and math.isnan(_bnbv["+ Volume"]))

# ── 12. Run-rate fin d'année ─────────────────────────────────
rr = run_rate_fin_annee(df, 2026, today=pd.Timestamp(2026, 9, 24))
check("run-rate : jours écoulés = 247 (04/09/2026, dernier jour facturé)",
      rr["Jours écoulés"] == 247, str(rr["Jours écoulés"]))
check("run-rate : projection = 342/247×365",
      rr["Projection"] == round(342 / 247 * 365, 0), str(rr["Projection"]))
rr_past = run_rate_fin_annee(df, 2025, today=pd.Timestamp(2026, 9, 24))
check("run-rate année passée = CA réel", rr_past["Projection"] == rr_past["CA YTD"])
rr_fut = run_rate_fin_annee(df, 2027, today=pd.Timestamp(2026, 9, 24))
check("run-rate année future → NaN", math.isnan(rr_fut["Projection"]))

# ── 13. Santé des données ────────────────────────────────────
h = data_health(df, today=pd.Timestamp(2026, 9, 24))
check("health : lignes = 9", h["Lignes"] == 9, str(h["Lignes"]))
check("health : dernière facture = 2026-09-04", h["Dernière facture"] == "2026-09-04",
      str(h["Dernière facture"]))
check("health : retard = 20 j", h["Retard (j)"] == 20, str(h["Retard (j)"]))
h_dup = data_health(pd.concat([df, df.iloc[[0]]], ignore_index=True),
                    today=pd.Timestamp(2026, 9, 24))
check("health : doublon → ⚠️", h_dup["Statut"] == "⚠️" and h_dup["Doublons exacts"] == 1)
h_neg = data_health(df.assign(**{"Montant TTC": -5.0}), today=pd.Timestamp(2026, 9, 24))
check("health : montants ≤ 0 → ⚠️", h_neg["Statut"] == "⚠️")
check("health : vide → ⚠️", data_health(df.iloc[0:0])["Statut"] == "⚠️")

# ── 14. chart_bridge ─────────────────────────────────────────
figb = chart_bridge(br, "Étape", "Valeur", "Bridge test", h=300)
check("chart_bridge : 5 mesures (absolute/relative×3/total)",
      list(figb.data[0].measure) == ["absolute", "relative", "relative", "relative", "total"],
      str(list(figb.data[0].measure)))
check("chart_bridge : labels = étapes pont",
      list(figb.data[0].x) == ["CA N-1", "+ Volume", "+ Panier", "+ Mix", "= CA N"],
      str(list(figb.data[0].x)))
figb2 = chart_bridge(br_nobase, "Étape", "Valeur", "Bridge vide", h=300)
check("chart_bridge sans base : figure vide (message)",
      len(figb2.data) == 0 and "Aucune donnée" in str(figb2.layout.annotations[0].text))

# ── 15. Panneau alertes : variations NaN-safe ────────────────
check("alert_panel : NaN → « — »", _fmt_pct(float("nan")) == "—")
check("alert_panel : None → « — »", _fmt_pct(None) == "—")
check("alert_panel : +12.3 → « +12.3% »", _fmt_pct(12.345) == "+12.3%")

# ══════════════════════════════════════════════════════════════
# LOT P2 — objectifs, cohortes, narratif exécutif
# ══════════════════════════════════════════════════════════════

# ── 16. Objectifs / % atteinte ───────────────────────────────
ob = objectif_tracking(200.0, 1000.0, 73, 365)
check("objectif : atteinte 20%", ob["Atteinte %"] == 20.0, str(ob["Atteinte %"]))
check("objectif : cible prorata 200 (= pile)", ob["Cible prorata"] == 200.0,
      str(ob["Cible prorata"]))
check("objectif : avance/retard 0", ob["Avance/retard"] == 0.0)
ob0 = objectif_tracking(200.0, 0.0, 73, 365)
check("objectif 0 → NaN (—)", math.isnan(ob0["Atteinte %"]))
ob_none = objectif_tracking(200.0, None, 73, 365)
check("objectif None → NaN (—)", math.isnan(ob_none["Atteinte %"]))

# ── 17. Cohortes ─────────────────────────────────────────────
coh_rows = [
    # Fidèle : CA 2024, 2025 (tronqué j1-3 : 300) et 2026 (300)
    {"Date": pd.Timestamp(2024, 5, 1), "Année": 2024, "Mois": 5, "Jour": 1,
     "Nom": "Fidele", "Montant TTC": 500.0},
    {"Date": pd.Timestamp(2025, 9, 1), "Année": 2025, "Mois": 9, "Jour": 1,
     "Nom": "Fidele", "Montant TTC": 300.0},
    {"Date": pd.Timestamp(2026, 9, 1), "Année": 2026, "Mois": 9, "Jour": 1,
     "Nom": "Fidele", "Montant TTC": 300.0},
    # Nouvelle : 1re facture en 2026
    {"Date": pd.Timestamp(2026, 9, 2), "Année": 2026, "Mois": 9, "Jour": 2,
     "Nom": "New", "Montant TTC": 42.0},
    # Perdue : CA 2025 (j1 : 100) mais rien en 2026
    {"Date": pd.Timestamp(2025, 9, 1), "Année": 2025, "Mois": 9, "Jour": 1,
     "Nom": "Lost", "Montant TTC": 100.0},
]
cdf = pd.DataFrame(coh_rows)
coh = cohortes_conventions(cdf, 2026, history_years=2, mois_sel=[9])
_cmap = coh.set_index("Cohorte")["Conventions"].to_dict()
check("cohorte Fidèle = 1", _cmap.get("✅ Fidèles") == 1, str(_cmap))
check("cohorte Nouvelle = 1", _cmap.get("🆕 Nouvelles") == 1, str(_cmap))
check("cohorte Perdue = 1", _cmap.get("❌ Perdues") == 1, str(_cmap))
check("cohorte Perdue : Variation % = -100 (base N-1 existante)",
      coh.set_index("Cohorte").loc["❌ Perdues", "Variation %"] == -100.0,
      str(coh.set_index("Cohorte").loc["❌ Perdues", "Variation %"]))
check("cohorte : poids N = 100%",
      abs(coh["Poids % N"].sum() - 100.0) < 0.2, str(coh["Poids % N"].tolist()))
check("cohorte : vide → colonnes", list(cohortes_conventions(
    cdf.iloc[0:0], 2026).columns) == ["Cohorte", "Conventions", "CA N", "CA N-1",
                                      "Variation %", "Poids % N"])

# ── 18. Narratif exécutif ────────────────────────────────────
narr = narratif_executif({
    "annee": 2026, "ca_n": 342.0, "ca_n1": 300.0, "evo_pct": 14.0,
    "objectif": 1000.0, "atteinte_pct": 34.2, "avance_retard": -50.0,
    "bridge": {"+ Volume": 100.0, "+ Panier": -44.0, "+ Mix": -14.0},
    "top_hausse": {"nom": "Fidele", "delta": 120.0},
    "flop": {"nom": "Lost", "evo": -100.0},
    "run_rate": 505.0, "ca_risque": 150.0, "nb_inact": 1,
})
check("narratif : 6 bullets", len(narr) == 6, str(len(narr)))
check("narratif : CA cité", any("342" in t for _, t in narr))
check("narratif : objectif cité", any("34.2" in t for _, t in narr))
check("narratif : moteur dominant = Volume", any("Volume" in t for _, t in narr))
narr_noobj = narratif_executif({"annee": 2026, "ca_n": 342.0, "evo_pct": float("nan"),
                                "objectif": 0.0})
check("narratif sans objectif → consigne sidebar",
      any("sidebar" in t for _, t in narr_noobj))
check("narratif evo NaN → « — »", any("—" in t for _, t in narr_noobj))

# ══════════════════════════════════════════════════════════════
# REVUE GLOBALE — concentration, volumes, insights
# ══════════════════════════════════════════════════════════════

# ── 19. Ventes positives (hors avoirs) ───────────────────────
_av = pd.DataFrame([
    {"Nom": "A", "Année": 2026, "Mois": 9, "Montant TTC": 100.0},
    {"Nom": "A", "Année": 2026, "Mois": 9, "Montant TTC": -20.0},
    {"Nom": "B", "Année": 2026, "Mois": 9, "Montant TTC": 0.0},
])
check("ventes_positives : 1 ligne sur 3", len(ventes_positives(_av)) == 1)
check("ventes_positives : vide → vide", ventes_positives(_av.iloc[0:0]).empty)
_avn = pd.DataFrame([
    {"Nom": "A", "Année": 2026, "Mois": 9, "Montant TTC": 100.0},
    {"Nom": "A", "Année": 2026, "Mois": 9, "Montant TTC": -20.0},
])
_voln = volumes_panier(_avn, 2026, [9])
check("volumes : avoir exclu du comptage (Nb=1, panier=100)",
      _voln["Nb N"] == 1 and _voln["Panier N"] == 100.0,
      str((_voln["Nb N"], _voln["Panier N"])))

# ── 20. Concentration ────────────────────────────────────────
conc = concentration_portefeuille(df, 2026, [9])
check("concentration : Top3 % = 100 (2 conventions)",
      conc["Top3 %"] == 100.0, str(conc["Top3 %"]))
check("concentration : HHI cohérent",
      conc["HHI"] == int(((300 / 342) ** 2 + (42 / 342) ** 2) * 10000),
      str(conc["HHI"]))
check("concentration : courbe cumulée termine à 100",
      abs(conc["courbe"]["Cumul %"].iloc[-1] - 100.0) < 0.15,
      str(conc["courbe"]["Cumul %"].tolist()))
check("concentration : vide → NaN", math.isnan(concentration_portefeuille(
    df.iloc[0:0], 2026)["Top3 %"]))

# ── 21. Volumes & panier ─────────────────────────────────────
vol = volumes_panier(df, 2026, [9])
check("volumes : Nb N = 4", vol["Nb N"] == 4, str(vol["Nb N"]))
check("volumes : Nb N-1 = 3", vol["Nb N-1"] == 3, str(vol["Nb N-1"]))
check("volumes : Evo Nb = +33.3%", vol["Evo Nb %"] == 33.3, str(vol["Evo Nb %"]))
check("volumes : Panier N = 86 (342/4, arrondi TND)", vol["Panier N"] == 86.0,
      str(vol["Panier N"]))
check("volumes : sans base → NaN",
      math.isnan(volumes_panier(df[df["Année"] == 2026], 2026)["Evo Nb %"]))

# ── 22. Insights ─────────────────────────────────────────────
ins = business_insights(df, 2026, rm, [9])
check("insights : liste non vide", len(ins) > 0, str(ins))
check("insights : max 5", len(ins) <= 5)
check("insights : tuples (ico, txt)", all(isinstance(x, tuple) and len(x) == 2 for x in ins))
check("insights : vide → []", business_insights(df.iloc[0:0], 2026, pd.DataFrame()) == [])
ins_big = business_insights(df, 2026, pd.concat([rm] * 10, ignore_index=True), [9])
check("insights : toujours max 5", len(ins_big) <= 5)

# ── Bilan ──────────────────────────────────────────────────────
print()
if FAILS:
    print(f"ÉCHEC — {len(FAILS)} test(s) : {FAILS}")
    sys.exit(1)
print("TOUS LES TESTS PASSENT")
