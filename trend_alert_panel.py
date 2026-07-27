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
    if severity=="RED": return "🔴"
    if severity=="AMBER": return "🟡"
    return "🟢"


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
    cf1,cf2,cf3,_=st.columns([1,1,1,4])
    with cf1:
        sev_filter=st.selectbox("Severite",["Toutes","ROUGE","AMBRE"],key="sev_filter")
    with cf2:
        typ_filter=st.selectbox("Type",["Tous","Magasin","Convention"],key="typ_filter")
    with cf3:
        limit_filter=st.selectbox("Afficher",[20,50,100,"Toutes"],index=0,key="limit_filter")
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
    rows=[]
    for a in all_alerts:
        r=a.get("rules_triggered",[])
        m=a.get("metrics",{})
        top_rule=r[0]["rule_id"] if r else ""
        top_msg=(r[0]["message_fr"][:70]+"...") if r and len(r[0].get("message_fr",""))>70 else (r[0].get("message_fr","") if r else "")
        yoy=m.get("yoy_change_pct",0)
        ytd_pct=m.get("ytd_change_pct",0)
        rows.append({"Severite":_severity_badge(a["severity"]),"Entite":a["_name"],"Type":a["_type"],"CA Mois":_format_k(m.get("ca_current_month",0)),"Var.":"{:+.1f}%".format(yoy),"Var. YTD":"{:+.1f}%".format(ytd_pct),"Regle":top_rule,"Detail":top_msg})
    limit_val=limit_filter
    display_rows=rows if limit_val=="Toutes" else rows[:int(limit_val)]
    df=pd.DataFrame(display_rows)
    styled=df.style.map(lambda v:"background-color:#FEF2F2;color:#7F1D1D" if "\U0001F534" in str(v) else "background-color:#FFFBEB;color:#78350F" if "\U0001F7E1" in str(v) else "")
    st.dataframe(styled,use_container_width=True,hide_index=True)
    st.caption(f"Affiche {len(display_rows)}/{len(rows)} alertes")
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
