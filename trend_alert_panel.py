"""trend_alert_panel.py — Panneau « Alertes Tendances » (rendu uniquement).

Les règles métier vivent dans `trend_analyzer.py` et le JSON est régénéré
quotidiennement par GitHub Actions. Ce module ne fait que rendre le résultat :
lisible (colonnes numériques triables), priorisé par **enjeu TND**, et
**cliquable** (drill-down par entité avec courbe N / N-1).
"""
import json
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from data.config import C, MOIS


# ── Libellés humains des règles : fin des identifiants « YOY_DROP_10 » ──
RULE_LABELS = {
    "YOY_DROP_10": "Baisse YoY > 10 %",
    "YOY_DROP_5": "Baisse YoY > 5 %",
    "CONSECUTIVE_3": "3 mois consécutifs de baisse",
    "ROLLING_AVG_DROP": "CA sous 80 % de la moyenne 3 mois",
    "VOLUME_DROP": "Chute du volume de factures",
}

# Recommandation associée à la règle principale (bandeau « Top 3 actions »).
RULE_ACTIONS = {
    "YOY_DROP_10": "plan d'action commercial sous 7 jours",
    "YOY_DROP_5": "relance et suivi hebdomadaire",
    "CONSECUTIVE_3": "diagnostic complet (ruptures, assortiment, concurrence)",
    "ROLLING_AVG_DROP": "relance ciblée sur le trimestre",
    "VOLUME_DROP": "revue du mix produit et de la fréquence de commande",
}

# « P1 » / « P2 » en tête de libellé : le tri texte reste correct (P1 < P2).
SEV_LABEL = {"RED": "P1 · \U0001F534 Critique", "AMBER": "P2 · \U0001F7E1 À surveiller"}


def load_alerts(path="data/trend_alerts.json"):
    p = Path(path)
    if not p.exists():
        return {"generated_at": "", "summary": {"total_alerts": 0, "red_alerts": 0, "amber_alerts": 0, "total_magasins_analyzed": 0, "total_conventions_analyzed": 0, "inactive_count": 0}, "magasin_alerts": [], "convention_alerts": [], "inactivity": []}
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def _severity_badge(severity):
    if severity == "RED":
        return "\U0001F534"
    if severity == "AMBER":
        return "\U0001F7E1"
    return "\U0001F7E2"


def _severity_color(severity):
    return {"RED": "#DC2626", "AMBER": "#D97706", "GREEN": "#059669"}.get(severity, "#64748B")


def _format_k(x):
    if x >= 1000000:
        return f"{x/1000000:.2f}M"
    if x >= 1000:
        return f"{x/1000:.1f}k"
    return f"{x:,.0f}"


def _fmt_pct(v):
    """Variation NaN-safe pour le panneau : NaN/None → « — », jamais « +nan% »."""
    try:
        if v is None or pd.isna(v):
            return "—"
        return f"{float(v):+.1f}%"
    except (TypeError, ValueError):
        return "—"


def _fmt_tnd(v):
    """Montant en TND, séparateur d'espace (lecture française)."""
    try:
        return f"{float(v):,.0f}".replace(",", " ")
    except (TypeError, ValueError):
        return "—"


def _rule_labels(rules):
    """Libellés humains des règles déclenchées, sans troncature."""
    return [RULE_LABELS.get(r.get("rule_id", ""), r.get("rule_id", "")) for r in (rules or [])]


def _rule_messages(rules):
    """« Libellé humain — message métier complet » pour chaque règle."""
    out = []
    for r in (rules or []):
        lbl = RULE_LABELS.get(r.get("rule_id", ""), r.get("rule_id", ""))
        msg = str(r.get("message_fr", "")).strip()
        out.append(f"{lbl} — {msg}" if msg else lbl)
    return out


def _scan_freshness(generated_at):
    """Retourne (texte de fraîcheur, périmé ?) — garde-fou sur le scan JSON."""
    if not generated_at:
        return "Scan : date inconnue", True
    try:
        ts = datetime.fromisoformat(str(generated_at)[:19])
    except (TypeError, ValueError):
        return f"Scan : {str(generated_at)[:19]}", False
    age_h = (datetime.now() - ts).total_seconds() / 3600.0
    stamp = ts.strftime("%d/%m/%Y à %H:%M")
    if age_h < 1:
        txt = f"Scan du {stamp} (il y a moins d'une heure)"
    elif age_h < 48:
        txt = f"Scan du {stamp} (il y a {age_h:.0f} h)"
    else:
        txt = f"Scan du {stamp} (il y a {age_h/24:.0f} j)"
    return txt, age_h > 24

def _alert_frame(alerts):
    """
    Aplatit magasin_alerts + convention_alerts en une liste de dicts enrichis :
    montants numériques, enjeu TND (= CA N-1 − CA N, plancher à 0), libellés
    de règles humanisés. Aucun affichage ici — que de la donnée.
    """
    recs = []
    for a in (alerts or {}).get("magasin_alerts", []) or []:
        recs.append({"name": a.get("magasin", ""), "type": "Magasin", "col": "Magasin", "raw": a})
    for a in (alerts or {}).get("convention_alerts", []) or []:
        recs.append({"name": a.get("nom", ""), "type": "Convention", "col": "Nom", "raw": a})
    for r in recs:
        raw = r["raw"]
        m = raw.get("metrics", {}) or {}
        rules = raw.get("rules_triggered", []) or []
        ca = float(m.get("ca_current_month", 0.0) or 0.0)
        ca1 = float(m.get("ca_same_month_last_year", 0.0) or 0.0)
        r.update({
            "ca": ca,
            "ca1": ca1,
            "enjeu": max(ca1 - ca, 0.0),          # TND qui s'évaporent vs N-1
            "var": m.get("yoy_change_pct", np.nan),
            "ytd": m.get("ytd_change_pct", np.nan),
            "nb": len(rules),
            "labels": _rule_labels(rules),
            "messages": _rule_messages(rules),
            "top_rule": rules[0].get("rule_id", "") if rules else "",
            "mom": m.get("mom_change_pct", np.nan),
            "roll3": float(m.get("rolling_3m_avg", 0.0) or 0.0),
            "consec": int(m.get("consecutive_decline_months", 0) or 0),
            "tx": int(m.get("transaction_count_current", 0) or 0),
            "tx_var": m.get("transaction_count_yoy_change_pct", np.nan),
        })
    return recs


def _display_table(recs):
    """DataFrame d'affichage : numériques (tri réel) + gravité en clair."""
    rows = []
    for r in recs:
        sev = r["raw"].get("severity", "AMBER")
        rows.append({
            "Gravité": SEV_LABEL.get(sev, "P2 · \U0001F7E1 À surveiller"),
            "Entité": r["name"],
            "Type": r["type"],
            "Enseigne": r["raw"].get("enseigne", "MG"),
            "CA mois (TND)": r["ca"],
            "CA N-1 (TND)": r["ca1"],
            "Enjeu (TND)": r["enjeu"],
            "Var. YoY %": r["var"],
            "Var. YTD %": r["ytd"],
            "Nb règles": r["nb"],
            "Motifs": " + ".join(r["labels"]) if r["labels"] else "—",
        })
    return pd.DataFrame(rows)


def _sev_style(v):
    """Fond coloré sur la seule colonne Gravité (jamais toute la ligne)."""
    s = str(v)
    if s.startswith("P1"):
        return "background-color:#FEE2E2;color:#991B1B;font-weight:600"
    if s.startswith("P2"):
        return "background-color:#FEF3C7;color:#92400E;font-weight:600"
    return ""


def _monthly_pair(df, col, name, annee_n):
    """CA mensuel N vs N-1 d'une entité — courbe du drill-down."""
    if df is None or getattr(df, "empty", True) or col not in df.columns:
        return pd.DataFrame()
    sub = df[(df[col] == name) & (df["Année"].isin([annee_n, annee_n - 1]))]
    if sub.empty:
        return pd.DataFrame()
    g = sub.groupby(["Année", "Mois"])["Montant TTC"].sum().reset_index()
    piv = g.pivot(index="Mois", columns="Année", values="Montant TTC")
    piv = piv.reindex(range(1, 13))
    piv = piv.rename_axis("Mois").reset_index()
    piv["Libellé"] = piv["Mois"].map(MOIS)
    return piv


def _curve_fig(piv, annee_n, title):
    """Barres groupées N / N-1 par mois (N en couleur, N-1 estompé)."""
    fig = go.Figure()
    if annee_n - 1 in piv.columns:
        fig.add_bar(
            x=piv["Libellé"], y=piv[annee_n - 1], name=str(annee_n - 1),
            marker_color=C["slate"], opacity=0.55,
        )
    if annee_n in piv.columns:
        fig.add_bar(
            x=piv["Libellé"], y=piv[annee_n], name=str(annee_n),
            marker_color=C["blue"],
        )
    fig.update_layout(
        barmode="group", height=320, title=title,
        margin=dict(l=10, r=10, t=50, b=10),
        legend=dict(orientation="h", y=1.12, x=0),
        yaxis_title="CA mensuel (TND)",
    )
    return fig


def _recommandation(top_rule):
    return RULE_ACTIONS.get(top_rule, "analyse manuelle recommandée")


def _entity_dialog(r, annee_n, df):
    """Contenu du pop-up : métriques, courbe 12 mois N/N-1, règles complètes."""
    m1, m2, m3, m4 = st.columns(4)
    m1.metric(f"CA {annee_n}", _fmt_tnd(r["ca"]) + " TND", delta=_fmt_pct(r["var"]),
              delta_color="normal")
    m2.metric(f"CA {annee_n-1}", _fmt_tnd(r["ca1"]) + " TND")
    m3.metric("Enjeu vs N-1", _fmt_tnd(r["enjeu"]) + " TND")
    m4.metric("Mois de baisse", r["consec"])

    n1, n2, n3 = st.columns(3)
    n1.metric("Moyenne 3 mois", _fmt_tnd(r["roll3"]) + " TND")
    n2.metric("Factures", r["tx"], delta=_fmt_pct(r["tx_var"]))
    n3.metric("Var. MoM", _fmt_pct(r["mom"]))

    piv = _monthly_pair(df, r["col"], r["name"], annee_n)
    if not piv.empty:
        st.plotly_chart(
            _curve_fig(piv, annee_n, f"{r['name']} — CA mensuel {annee_n} vs {annee_n-1}"),
            use_container_width=True,
        )
    else:
        st.info("Courbe indisponible : entité absente du jeu de données chargé.")

    st.markdown("**Règles déclenchées**")
    for msg in (r["messages"] or ["Aucune règle détaillée"]):
        st.markdown(f"- {msg}")
    st.caption(f"Action recommandée : {_recommandation(r['top_rule'])}")


def _top_actions(recs, n=3):
    """Bandeau « Top 3 actions » : les plus gros enjeux TND, en français."""
    top = sorted(recs, key=lambda r: r["enjeu"], reverse=True)[:n]
    if not top or top[0]["enjeu"] <= 0:
        return []
    out = []
    for r in top:
        sev = r["raw"].get("severity", "AMBER")
        out.append(
            f"{_severity_badge(sev)} **{r['name']}** ({r['type']}) — "
            f"{_fmt_tnd(r['enjeu'])} TND d'enjeu · {_fmt_pct(r['var'])} YoY"
            + (f" · {r['consec']} mois de baisse" if r["consec"] >= 2 else "")
            + f" → {_recommandation(r['top_rule'])}"
        )
    return out


def _inactivity_table(alerts, df, annee_n):
    """
    Inactivités : plus de plafond à 20, tri par impact (CA N-1) quand le jeu
    de données est fourni, sinon par ancienneté du dernier achat.
    """
    inact = (alerts or {}).get("inactivity", []) or []
    if not inact:
        return pd.DataFrame()
    rows = []
    for i in inact:
        rows.append({
            "Entité": i.get("entity", ""),
            "Enseigne": i.get("enseigne", "MG"),
            "Jours sans vente": int(i.get("days_since_last_sale", 0) or 0),
            "Dernière vente": i.get("last_sale_date", ""),
        })
    tbl = pd.DataFrame(rows)
    ca_map = {}
    if df is not None and not getattr(df, "empty", True) and "Magasin" in df.columns:
        _prev = df[df["Année"] == annee_n - 1]
        if not _prev.empty:
            ca_map = _prev.groupby("Magasin")["Montant TTC"].sum().to_dict()
    tbl["CA N-1 (TND)"] = tbl["Entité"].map(ca_map)
    if tbl["CA N-1 (TND)"].notna().any():
        tbl = tbl.sort_values("CA N-1 (TND)", ascending=False).reset_index(drop=True)
    else:
        tbl = tbl.sort_values("Jours sans vente", ascending=False).reset_index(drop=True)
    return tbl


def render_alert_panel(alerts, df=None, annee_n=None, mois_sel=None):
    """
    Rend le panneau d'alertes.

    df      : jeu de données factures (df_vc) — active le drill-down et
              l'impact TND des inactivités. Optionnel.
    annee_n : année de référence pour la courbe N / N-1 (défaut : année en cours).
    """
    if not alerts:
        st.info("Aucune donnée alerte. Lancez un scan d'abord.")
        return

    summary = alerts.get("summary", {}) or {}
    gen_at = alerts.get("generated_at", "")
    annee_n = int(annee_n or datetime.now().year)
    recs = _alert_frame(alerts)

    # ── Synthèse : 4 indicateurs décisionnels (dont l'enjeu TND) ──
    enjeu_tot = sum(r["enjeu"] for r in recs)
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Alertes P1 (critiques)", summary.get("red_alerts", 0))
    k2.metric("Alertes P2 (à surveiller)", summary.get("amber_alerts", 0))
    k3.metric("Enjeu identifié", _fmt_tnd(enjeu_tot) + " TND",
              help="Somme des écarts vs N-1 sur les entités alertées (CA N-1 − CA N)")
    k4.metric("Inactifs", summary.get("inactive_count", 0))

    _fresh_txt, _stale = _scan_freshness(gen_at)
    if _stale:
        st.warning(f"⚠️ {_fresh_txt} — le scan quotidien semble interrompu, relancez le workflow.")
    else:
        st.caption(
            f"{_fresh_txt} · {summary.get('total_magasins_analyzed', 0)} magasins et "
            f"{summary.get('total_conventions_analyzed', 0)} conventions analysés"
        )
    st.divider()

    # ── Bandeau « Top 3 actions » : où agir en priorité, en TND ──
    _actions = _top_actions(recs)
    if _actions:
        with st.container(border=True):
            st.markdown("**\U0001F3AF Top 3 actions de la semaine** (par enjeu TND)")
            for line in _actions:
                st.markdown(line)

    # ── Filtres ──
    cf1, cf2, cf3, cf4 = st.columns([1, 1, 1, 1])
    with cf1:
        sev_filter = st.selectbox("Gravité", ["Toutes", "P1 · Critique", "P2 · À surveiller"],
                                  key="sev_filter")
    with cf2:
        typ_filter = st.selectbox("Type", ["Tous", "Magasin", "Convention"], key="typ_filter")
    with cf3:
        ens_filter = st.selectbox(
            "Enseigne", ["Toutes"] + sorted({r["raw"].get("enseigne", "MG") for r in recs}),
            key="ens_filter",
        )
    with cf4:
        tri_filter = st.selectbox(
            "Trier par", ["Enjeu TND", "Gravité puis enjeu", "Variation YoY", "Entité"],
            key="tri_filter",
        )

    sel = recs
    if sev_filter.startswith("P1"):
        sel = [r for r in sel if r["raw"].get("severity") == "RED"]
    elif sev_filter.startswith("P2"):
        sel = [r for r in sel if r["raw"].get("severity") == "AMBER"]
    if typ_filter != "Tous":
        sel = [r for r in sel if r["type"] == typ_filter]
    if ens_filter != "Toutes":
        sel = [r for r in sel if r["raw"].get("enseigne", "MG") == ens_filter]

    if tri_filter == "Enjeu TND":
        sel = sorted(sel, key=lambda r: r["enjeu"], reverse=True)
    elif tri_filter == "Gravité puis enjeu":
        sel = sorted(sel, key=lambda r: (0 if r["raw"].get("severity") == "RED" else 1,
                                         -r["enjeu"]))
    elif tri_filter == "Variation YoY":
        sel = sorted(sel, key=lambda r: float(np.nan_to_num(r["var"], nan=0.0)))
    else:
        sel = sorted(sel, key=lambda r: str(r["name"]).upper())

    if not sel:
        st.success("Aucune alerte avec les filtres sélectionnés.")
        return

    st.caption(
        f"{len(sel)} alerte(s) affichée(s) sur {len(recs)} · "
        f"enjeu cumulé {_fmt_tnd(sum(r['enjeu'] for r in sel))} TND"
    )
    tbl = _display_table(sel)
    styled = (
        tbl.style
        .map(_sev_style, subset=["Gravité"])
        .format(
            {"CA mois (TND)": "{:,.0f}", "CA N-1 (TND)": "{:,.0f}",
             "Enjeu (TND)": "{:,.0f}", "Var. YoY %": "{:+.1f}", "Var. YTD %": "{:+.1f}"},
            na_rep="—",
        )
    )
    st.dataframe(styled, use_container_width=True, hide_index=True,
                 height=min(560, 40 + 35 * len(sel)))

    # ── Export de la liste filtrée (traitement hors dashboard) ──
    _exp_cols = ["Gravité", "Entité", "Type", "Enseigne", "CA mois (TND)", "CA N-1 (TND)",
                 "Enjeu (TND)", "Var. YoY %", "Var. YTD %", "Nb règles", "Motifs"]
    _csv = tbl[_exp_cols].to_csv(index=False, sep=";").encode("utf-8-sig")
    st.download_button(
        "\U0001F4E5 Exporter les alertes filtrées (CSV)", data=_csv,
        file_name=f"alertes_tendances_{annee_n}.csv", mime="text/csv",
    )

    # ── Drill-down : choix d'une entité → courbe N/N-1 + règles complètes ──
    with st.container(border=True):
        st.markdown("**\U0001F50D Détail d'une entité**")
        _opts = {f"{r['type']} · {r['name']} ({_fmt_tnd(r['enjeu'])} TND)": r for r in sel}
        _choice = st.selectbox("Choisir une entité alertée", ["— Choisir —"] + list(_opts),
                               key="alert_detail_choice")
        if _choice != "— Choisir —":
            _r = _opts[_choice]

            @st.dialog(f"{_r['name']} — {_r['type']}")
            def _show():
                _entity_dialog(_r, annee_n, df)

            _show()

    # ── Inactivités : impact classé, sans plafond, exportable ──
    _inact_tbl = _inactivity_table(alerts, df, annee_n)
    if not _inact_tbl.empty:
        st.divider()
        st.markdown(f"### Inactivités ({len(_inact_tbl)})")
        st.caption("Entités sans vente récente, classées par impact (CA N-1) — "
                   "colonne « Jours sans vente » triable.")
        _inact_styled = _inact_tbl.style.format({"CA N-1 (TND)": "{:,.0f}"}, na_rep="—")
        st.dataframe(_inact_styled, use_container_width=True, hide_index=True,
                     height=min(460, 40 + 35 * len(_inact_tbl)))
        _csv_i = _inact_tbl.to_csv(index=False, sep=";").encode("utf-8-sig")
        st.download_button(
            "\U0001F4E5 Exporter les inactivités (CSV)", data=_csv_i,
            file_name=f"inactivites_{annee_n}.csv", mime="text/csv",
        )

    st.caption("Les alertes sont mises à jour quotidiennement via GitHub Actions.")

