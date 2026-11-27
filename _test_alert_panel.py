"""Validation du panneau Alertes Tendances (Lot 1 + 2) — harnais Streamlit simulé."""
import sys

sys.path.insert(0, r"C:\Users\hachk\pilotage_b2b")


class _Tee:
    """Écrit les résultats ET les tracebacks dans un fichier (redirection PS peu fiable)."""

    def __init__(self, path):
        self.f = open(path, "w", encoding="utf-8")

    def write(self, s):
        self.f.write(s)
        self.f.flush()

    def flush(self):
        self.f.flush()


sys.stdout = _Tee(r"C:\Users\hachk\pilotage_b2b\_t_results.txt")
sys.stderr = sys.stdout

import pandas as pd
import trend_alert_panel as tap


FAILS = []


def check(name, cond, extra=""):
    print(f"[{'PASS' if cond else 'FAIL'}] {name}" + (f" — {extra}" if extra else ""))
    if not cond:
        FAILS.append(name)


# ── Faux module streamlit : enregistre les appels, rejoue les contextes ──
class _Ctx:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _Col(_Ctx):
    def __init__(self, st_):
        self._st = st_

    def metric(self, label, value=None, **k):
        self._st.rec.setdefault("metric", []).append((label, value))

    def markdown(self, body, **k):
        self._st.rec.setdefault("markdown", []).append(body)

    def caption(self, body, **k):
        self._st.rec.setdefault("caption", []).append(body)


class FakeSt:
    def __init__(self, choices=None):
        self.choices = choices or {}
        self.rec = {}

    def container(self, **k):
        return _Ctx()

    def columns(self, spec, **k):
        n = spec if isinstance(spec, int) else len(spec)
        return [_Col(self) for _ in range(n)]

    def metric(self, label, value=None, **k):
        self.rec.setdefault("metric", []).append((label, value))

    def dataframe(self, data, **k):
        self.rec.setdefault("dataframe", []).append(data)

    def download_button(self, label, data=None, **k):
        self.rec.setdefault("download", []).append((label, data))

    def markdown(self, body, **k):
        self.rec.setdefault("markdown", []).append(body)

    def caption(self, body, **k):
        self.rec.setdefault("caption", []).append(body)

    def info(self, body, **k):
        self.rec.setdefault("info", []).append(body)

    def success(self, body, **k):
        self.rec.setdefault("success", []).append(body)

    def warning(self, body, **k):
        self.rec.setdefault("warning", []).append(body)

    def divider(self, **k):
        pass

    def plotly_chart(self, fig, **k):
        self.rec.setdefault("chart", []).append(fig)

    def selectbox(self, label, options, key=None, **k):
        self.rec.setdefault("selectbox", []).append((label, list(options)))
        if key in self.choices:
            return self.choices[key]
        return options[0] if options else None

    def dialog(self, title, **k):
        self.rec.setdefault("dialog", []).append(title)

        def _deco(fn):
            fn()
            return fn

        return _deco


# ── Données réelles ────────────────────────────────────────────
alerts = tap.load_alerts(r"C:\Users\hachk\pilotage_b2b\data\trend_alerts.json")
recs = tap._alert_frame(alerts)
tbl = tap._display_table(recs)
print(f"--- {len(recs)} alertes, enjeu total {sum(r['enjeu'] for r in recs):,.0f} TND ---\n")

# ── 1. Colonnes numériques (tri réel) ─────────────────────────
for col in ("CA mois (TND)", "CA N-1 (TND)", "Enjeu (TND)", "Var. YoY %", "Var. YTD %"):
    check(f"colonne « {col} » réellement numérique",
          pd.api.types.is_numeric_dtype(tbl[col]), str(tbl[col].dtype))
check("Gravité triable : P1 avant P2", sorted(tbl["Gravité"].unique())[0].startswith("P1"))
check("Motifs non tronqués (pas de « ... » final)",
      not tbl["Motifs"].astype(str).str.endswith("...").any())

# ── 2. Priorisation par enjeu ─────────────────────────────────
top = sorted(recs, key=lambda r: r["enjeu"], reverse=True)
check("tri enjeu décroissant stable",
      all(top[i]["enjeu"] >= top[i + 1]["enjeu"] for i in range(len(top) - 1)))
acts = tap._top_actions(recs)
check("Top 3 actions générées", len(acts) == 3)
check("Top 3 : 1re ligne = plus gros enjeu", top[0]["name"] in acts[0], acts[0][:100])
check("Top 3 : recommandation en français", "→" in acts[0])

# ── 3. Règles humanisées, messages complets ───────────────────
lbls = tap._rule_labels(top[0]["raw"]["rules_triggered"])
msgs = tap._rule_messages(top[0]["raw"]["rules_triggered"])
check("règle traduite (plus d'identifiant brut)", len(lbls) > 0 and all("DROP" not in l for l in lbls), str(lbls))
check("message métier complet conservé (> 70 car.)", len(msgs[0]) > 70, f"{len(msgs[0])} car.")

# ── 4. Garde de fraîcheur ─────────────────────────────────────
txt, stale = tap._scan_freshness(alerts.get("generated_at", ""))
check("fraîcheur lisible", "Scan du" in txt, f"{txt} | périmé={stale}")
txt2, stale2 = tap._scan_freshness("2020-01-01T06:00:00")
check("scan ancien signalé périmé", stale2 and "j)" in txt2, txt2)

# ── 5. Inactivités : sans plafond + impact CA N-1 ─────────────
df_syn = pd.DataFrame({
    "Nom": ["TUNIS AIR"] * 4,
    "Magasin": ["MG PROXI TABARKA", "MG PROXI TABARKA", "MG PROXI TABARKA", "MG PROXI TABARKA"],
    "Enseigne": ["BATAM"] * 4,
    "Année": [2026, 2025, 2026, 2025],
    "Mois": [9, 9, 8, 8],
    "Jour": [10, 10, 5, 5],
    "Montant TTC": [1000.0, 2000.0, 3000.0, 9000.0],
})
inact = tap._inactivity_table(alerts, df_syn, 2026)
check("inactivités : aucune troncature à 20",
      len(inact) == len(alerts.get("inactivity", [])), f"{len(inact)} lignes")
check("inactivités : impact CA N-1 calculé", "CA N-1 (TND)" in inact.columns
      and inact["CA N-1 (TND)"].notna().any())

# ── 6. Courbe N / N-1 du drill-down ───────────────────────────
piv = tap._monthly_pair(df_syn, "Nom", "TUNIS AIR", 2026)
check("courbe 12 mois construite", len(piv) == 12, f"{len(piv)} mois")
check("courbe porte N et N-1", {2026, 2025}.issubset(set(piv.columns)))
check("mapping mois FR présent", "Sep" in set(piv["Libellé"]))
fig = tap._curve_fig(piv, 2026, "titre test")
check("figure à 2 séries (N + N-1)", len(fig.data) == 2, f"{len(fig.data)} séries")
check("entité absente → courbe vide gérée",
      tap._monthly_pair(df_syn, "Nom", "ENTITE INEXISTANTE", 2026).empty)



# ── 7. Rendu complet — scénario par défaut ────────────────────
fake = FakeSt()
tap.st = fake
try:
    tap.render_alert_panel(alerts, df=df_syn, annee_n=2026)
    check("rendu complet sans exception", True)
except Exception as e:
    check("rendu complet sans exception", False, f"{type(e).__name__}: {e}")

check("4 tuiles de synthèse", len(fake.rec.get("metric", [])) >= 4,
      str([m[0] for m in fake.rec.get("metric", [])][:4]))
check("tuile « Enjeu identifié » en TND",
      any("Enjeu identifié" in m[0] and "TND" in str(m[1]) for m in fake.rec["metric"]))
check("bandeau Top 3 actions rendu", any("Top 3 actions" in m for m in fake.rec.get("markdown", [])))
check("tableau d'alertes rendu", len(fake.rec.get("dataframe", [])) >= 1)
check("exports CSV présents", len(fake.rec.get("download", [])) >= 1,
      str([l for l, _ in fake.rec.get("download", [])]))
_csv = [d for l, d in fake.rec.get("download", []) if "alertes filtr" in l]
check("CSV alertes : utf-8-sig + séparateur « ; »",
      bool(_csv) and _csv[0][:3] == b"\xef\xbb\xbf" and b";" in _csv[0])
check("CSV alertes : motifs non tronqués",
      bool(_csv) and "Baisse YoY" in _csv[0].decode("utf-8-sig"))
check("sélecteur de drill-down présent",
      any("Choisir une entité" in s[0] for s in fake.rec.get("selectbox", [])))
check("toutes les alertes affichées (défaut = Toutes)",
      fake.rec["dataframe"][0].data.shape[0] == len(recs),
      f"{fake.rec['dataframe'][0].data.shape[0]}/{len(recs)}")
check("DataFrame affiché garde les dtypes numériques (tri)",
      pd.api.types.is_numeric_dtype(fake.rec["dataframe"][0].data["Enjeu (TND)"]))

# ── 8. Scénario filtré (P1 + Conventions) ─────────────────────
print("\n--- Scénario filtré ---")
fake2 = FakeSt({"sev_filter": "P1 · Critique", "typ_filter": "Convention",
                "tri_filter": "Gravité puis enjeu"})
tap.st = fake2
tap.render_alert_panel(alerts, df=df_syn, annee_n=2026)
_d2 = fake2.rec["dataframe"][0].data
check("filtres P1 + Convention appliqués", _d2.shape[0] > 0, f"{_d2.shape[0]} lignes")
check("filtre : uniquement des Conventions", set(_d2["Type"]) == {"Convention"}, str(set(_d2["Type"])))
check("filtre : uniquement P1", _d2["Gravité"].str.startswith("P1").all())

# ── 9. Drill-down : ouverture du pop-up ───────────────────────
print("\n--- Drill-down ---")
fake3 = FakeSt()


def _sel(self, label, options, key=None, **k):
    self.rec.setdefault("selectbox", []).append((label, list(options)))
    if key == "alert_detail_choice":
        return options[1]
    if key in self.choices:
        return self.choices[key]
    return options[0]


FakeSt.selectbox = _sel
tap.st = fake3
try:
    tap.render_alert_panel(alerts, df=df_syn, annee_n=2026)
    check("drill-down exécuté sans exception", True)
    check("pop-up ouvert", len(fake3.rec.get("dialog", [])) == 1, str(fake3.rec.get("dialog", [])))
    check("pop-up : courbe N/N-1 affichée", len(fake3.rec.get("chart", [])) >= 1,
          f"{len(fake3.rec.get('chart', []))} figure(s)")
    check("pop-up : « Règles déclenchées » listées",
          any("Règles déclenchées" in m for m in fake3.rec.get("markdown", [])))
    check("pop-up : tuiles de détail en plus de la synthèse",
          len(fake3.rec.get("metric", [])) > 4, f"{len(fake3.rec.get('metric', []))} tuiles")
except Exception as e:
    check("drill-down exécuté sans exception", False, f"{type(e).__name__}: {e}")

# ── 10. Cas limites ───────────────────────────────────────────
print("\n--- Cas limites ---")
tap.st = FakeSt()
try:
    tap.render_alert_panel({"generated_at": "", "summary": {}, "magasin_alerts": [],
                            "convention_alerts": [], "inactivity": []}, df=None, annee_n=2026)
    check("JSON vide géré", True)
except Exception as e:
    check("JSON vide géré", False, f"{type(e).__name__}: {e}")
try:
    tap.render_alert_panel({"summary": {"red_alerts": 1, "amber_alerts": 0},
                            "magasin_alerts": [{"magasin": "X", "severity": "RED",
                                                "rules_triggered": [], "metrics": {}}],
                            "convention_alerts": [], "inactivity": []}, df=None, annee_n=2026)
    check("alerte minimale + df=None gérée", True)
except Exception as e:
    check("alerte minimale + df=None gérée", False, f"{type(e).__name__}: {e}")
tap.st = FakeSt({"sev_filter": "P2 · À surveiller", "typ_filter": "Magasin"})
try:
    tap.render_alert_panel(alerts, df=None, annee_n=2026)
    check("filtre sans résultat + df=None géré", True)
except Exception as e:
    check("filtre sans résultat + df=None géré", False, f"{type(e).__name__}: {e}")

print("\n" + ("TOUS LES TESTS PASSENT" if not FAILS else f"ECHECS ({len(FAILS)}) : {FAILS}"))
sys.exit(1 if FAILS else 0)
