# trend_alert_panel.py - Trend Analysis Alert Panel
import streamlit as st
import pandas as pd
import plotly.express as px
import json
from pathlib import Path


def load_alerts(path="data/trend_alerts.json"):
    p=Path(path)
    if not p.exists():
        return {"generated_at":"","summary":{"total_alerts":0,"red_alerts":0,"amber_alerts":0,"total_magasins_analyzed":0,"total_conventions_analyzed":0,"inactive_count":0},"magasin_alerts":[],"convention_alerts":[],"inactivity":[]}
    with open(p,"r",encoding="utf-8") as fh:
        return json.load(fh)


def _severity_badge(severity):
    if severity=="RED": return ":red_circle:"
    if severity=="AMBER": return ":large_orange_diamond:"
    return ":large_green_circle:"


def _severity_color(severity):
    return {"RED":"#DC2626","AMBER":"#D97706","GREEN":"#059669"}.get(severity,"#64748B")


def _format_k(x):
    if x>=1000000: return f"{x/1000000:.2f}M"
    if x>=1000: return f"{x/1000:.1f}k"
    return f"{x:,.0f}"

def render_alert_panel(alerts):
    if not alerts:
        st.info("Aucune donnee alerte. Lancez un scan d abord.")
        return
    summary=alerts.get("summary",{})
    gen_at=alerts.get("generated_at","")
    c1,c2,c3,c4,c5=st.columns(5)
    c1.metric("Alertes ROUGES",summary.get("red_alerts",0))
    c2.metric("Alertes AMBRE",summary.get("amber_alerts",0))
    c3.metric("Magasins analyses",summary.get("total_magasins_analyzed",0))
    c4.metric("Conventions analysees",summary.get("total_conventions_analyzed",0))
    c5.metric("Inactifs",summary.get("inactive_count",0))
    if gen_at:
        st.caption("Dernier scan: "+gen_at[:19].replace("T"," "))
    st.divider()
    cf1,cf2,_=st.columns([1,1,4])
    with cf1:
        sev_filter=st.selectbox("Severite",["Toutes","ROUGE","AMBRE"],key="sev_filter")
    with cf2:
        typ_filter=st.selectbox("Type",["Tous","Magasin","Convention"],key="typ_filter")
    all_alerts=[]
    for a in alerts.get("magasin_alerts",[]):
        a["_type"]="Magasin"
        a["_name"]=a.get("magasin","")
        all_alerts.append(a)
    for a in alerts.get("convention_alerts",[]):
        a["_type"]="Convention"
        a["_name"]=a.get("nom","")
        all_alerts.append(a)
    if sev_filter=="ROUGE":
        all_alerts=[a for a in all_alerts if a["severity"]=="RED"]
    elif sev_filter=="AMBRE":
        all_alerts=[a for a in all_alerts if a["severity"]=="AMBER"]
    if typ_filter=="Magasin":
        all_alerts=[a for a in all_alerts if a["_type"]=="Magasin"]
    elif typ_filter=="Convention":
        all_alerts=[a for a in all_alerts if a["_type"]=="Convention"]
    all_alerts.sort(key=lambda a: (0 if a["severity"]=="RED" else 1))
    if not all_alerts:
        st.success("Aucune alerte avec les filtres selectionnes.")
        return
    st.markdown("### Alertes ("+str(len(all_alerts))+")")
    for a in all_alerts:
        badge=_severity_badge(a["severity"])
        name=a["_name"]
        etype=a["_type"]
        enseigne=a.get("enseigne","MG")
        rules=a.get("rules_triggered",[])
        metrics=a.get("metrics",{})
        with st.container(border=True):
            cols=st.columns([1,3,2])
            with cols[0]:
                st.markdown("<h2 style=text-align:center;margin:0>"+badge+"</h2>",unsafe_allow_html=True)
            with cols[1]:
                st.markdown("**"+name+"**")
                st.caption(etype+" | "+enseigne)
            with cols[2]:
                if metrics:
                    val=metrics.get("yoy_change_pct",0)
                    st.metric("CA Mois",_format_k(metrics.get("ca_current_month",0)),"{:+.1f}%".format(val))
            for r in rules:
                st.markdown("**"+r["rule_id"]+"** "+r["message_fr"])
            with st.expander("Voir details"):
                if metrics:
                    md=metrics
                    cols2=st.columns(3)
                    cols2[0].metric("CA N",_format_k(md.get("ca_current_month",0)))
                    cols2[1].metric("CA N-1",_format_k(md.get("ca_same_month_last_year",0)))
                    cols2[2].metric("Var. N-1","{:+.1f}%".format(md.get("yoy_change_pct",0)))
                    cols3=st.columns(3)
                    cols3[0].metric("Var. M/M","{:+.1f}%".format(md.get("mom_change_pct",0)))
                    cols3[1].metric("Moy. 3 mois",_format_k(md.get("rolling_3m_avg",0)))
                    cols3[2].metric("Mois baisse",str(int(md.get("consecutive_decline_months",0))))
                    cols4=st.columns(2)
                    cols4[0].metric("Transactions",int(md.get("transaction_count_current",0)))
                    cols4[1].metric("Var. transactions","{:+.1f}%".format(md.get("transaction_count_yoy_change_pct",0)))
    inactivity=alerts.get("inactivity",[])
    if inactivity:
        st.divider()
        st.markdown("### Inactivites ("+str(len(inactivity))+")")
        inact_data=[]
        for i in inactivity[:20]:
            inact_data.append({"Entite":i.get("entity",""),"Enseigne":i.get("enseigne",""),"Jours sans vente":i.get("days_since_last_sale",0),"Derniere vente":i.get("last_sale_date","")})
        if inact_data:
            st.dataframe(pd.DataFrame(inact_data),use_container_width=True,hide_index=True)
    st.caption("Les alertes sont mises a jour quotidiennement via GitHub Actions. Rafraichissez pour mettre a jour.")
