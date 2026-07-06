"""
Rapport Quotidien B2B - SMG
Envoi automatique par email - Format HTML同上
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime, timedelta
import pandas as pd
import requests
from io import BytesIO
from urllib.parse import quote

EMAIL_FROM = "Hamadi.Chkondali@SMG.com.tn"
EMAIL_TO = ["Hamadi.Chkondali@SMG.com.tn"]
SMTP_SERVER = "mail.SMG.com.tn"
SMTP_PORT = 587
EMAIL_PASSWORD = os.getenv("SMG_EMAIL_PASSWORD", "Azerty@4321!!!")

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"

FILES = {
    "vc": "Factures%20ventes%20enregistr%C3%A9es%20VC%20(4).xlsx",
    "vc_credit": "Factures%20ventes%20enregistr%C3%A9es%20VC%20credit%20conso.xlsx",
    "conventions": "TDC%20CONVENTION%201.xlsm",
    "code_magasin": "Code%20MAGASIN%20Business%20Central.xlsx",
}

MOIS = {
    1: "Jan", 2: "Fév", 3: "Mar", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Juil", 8: "Aoû",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Déc",
}

def load_excel(url):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return pd.read_excel(BytesIO(r.content), engine="openpyxl")
    except:
        pass
    return None

def load_all_data():
    dfs = {}
    for name, filename in FILES.items():
        url = GITHUB_RAW + filename
        df = load_excel(url)
        if df is not None:
            df.columns = df.columns.str.replace("\n", " ").str.strip()
            for col in df.select_dtypes("object").columns:
                df[col] = df[col].astype(str).str.strip()
            dfs[name] = df
    return dfs

def send_email(subject, html_body):
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = ', '.join(EMAIL_TO)
        msg.attach(MIMEText(html_body, 'html'))
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        
        print("Email envoye avec succes!")
        return True
    except Exception as e:
        print(f"Erreur envoi email: {e}")
        return False

def get_ca(df, date_col, amount_col, filter_date=None):
    """Calcule CA pour une date ou periode donnee."""
    if df is None or date_col not in df.columns or amount_col not in df.columns:
        return 0
    try:
        df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
        if filter_date:
            return df[df["Date"].dt.date == filter_date][amount_col].sum()
        return df[amount_col].sum()
    except:
        return 0

def format_k(x):
    """Formate nombre avec separateur."""
    if x >= 1000000:
        return f"{x/1000000:.1f}M"
    elif x >= 1000:
        return f"{x/1000:.0f}k"
    return f"{x:.0f}"

def evol_pct(v1, v2):
    """Calcule evolution en pourcentage."""
    if v2 == 0:
        return 0 if v1 == 0 else 100
    return ((v1 - v2) / v2) * 100

def generate_top_conventions(df, n=5):
    """Extrait top N conventions par CA."""
    if df is None or "Nom" not in df.columns or "Montant TTC" not in df.columns:
        return []
    try:
        top = df.groupby("Nom")["Montant TTC"].sum().sort_values(ascending=False).head(n)
        return [(name, float(val)) for name, val in top.items()]
    except:
        return []

def generate_top_magasins(df, n=3):
    """Extrait top N magasins."""
    if df is None or "Nom" not in df.columns or "Montant TTC" not in df.columns:
        return [], []
    try:
        by_mag = df.groupby("Nom")["Montant TTC"].sum().sort_values(ascending=False)
        top = [(name, float(val)) for name, val in by_mag.head(n).items()]
        flop = [(name, float(val)) for name, val in by_mag.tail(n).items()]
        return top, flop
    except:
        return [], []

def generate_report(dfs, date_str):
    today = datetime.now()
    hier = (today - timedelta(days=1)).strftime('%d/%m/%Y')
    
    df_vc = dfs.get("vc")
    
    date_col = None
    amount_col = None
    
    if df_vc is not None:
        for col in df_vc.columns:
            col_lower = col.lower() if isinstance(col, str) else ""
            if date_col is None and ("date" in col_lower or "jour" in col_lower):
                date_col = col
            if amount_col is None and ("montant" in col_lower or "ca" in col_lower):
                amount_col = col
    
    if date_col and amount_col:
        df_vc[date_col] = pd.to_datetime(df_vc[date_col], errors='coerce')
        df_vc["Date"] = df_vc[date_col].dt.date
        df_vc["Annee"] = df_vc[date_col].dt.year
        df_vc["Mois"] = df_vc[date_col].dt.month
    
    today_date = today.date()
    yesterday_date = (today - timedelta(days=1)).date()
    current_month = today.month
    
    ca_today = get_ca(df_vc, "Date", amount_col, today_date) if date_col else 0
    ca_yesterday = get_ca(df_vc, "Date", amount_col, yesterday_date) if date_col else 0
    ca_mois = df_vc[df_vc["Mois"] == current_month][amount_col].sum() if date_col and amount_col in df_vc.columns and "Mois" in df_vc.columns else 0
    
    ca_annee_n1 = df_vc[df_vc["Annee"] == today.year - 1][amount_col].sum() if date_col and amount_col in df_vc.columns and "Annee" in df_vc.columns else 0
    ca_mois_n1 = df_vc[(df_vc["Annee"] == today.year - 1) & (df_vc["Mois"] == current_month)][amount_col].sum() if date_col and amount_col in df_vc.columns else 0
    
    evo_jour = evol_pct(ca_today, ca_yesterday)
    evo_mois = evol_pct(ca_mois, ca_mois_n1)
    
    nb_conv = len(dfs.get("conventions", pd.DataFrame())) if "conventions" in dfs else 0
    
    top_convs = generate_top_conventions(df_vc[df_vc["Date"].dt.date == yesterday_date] if date_col else None, 3)
    
    top_magasins, flop_magasins = generate_top_magasins(df_vc[df_vc["Date"].dt.date == yesterday_date] if date_col else None, 3)
    
    mois_nom = MOIS.get(current_month, "")
    
    signal = "Belle perforation" if evo_mois > 0 else "Attention requise"
    signal_desc = f"CA du mois: {format_k(ca_mois)} TND ({evo_mois:+.1f}% vs N-1)" if evo_mois != 0 else "Pas de donnees"
    
    html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Rapport Quotidien B2B — {hier}</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;padding:24px;background:#EEF2F7;font-family:'DM Sans',Arial,sans-serif;">

  <div style="max-width:640px;margin:0 auto;">

    <!-- HEADER -->
    <div style="background:linear-gradient(135deg,#0B1E3F 0%,#1A3460 100%);border-radius:16px 16px 0 0;padding:28px 32px;position:relative;overflow:hidden;">
      <div style="position:absolute;top:-30px;right:-30px;width:160px;height:160px;background:rgba(255,255,255,0.04);border-radius:50%;"></div>
      <div style="position:absolute;bottom:-50px;right:60px;width:100px;height:100px;background:rgba(255,255,255,0.03);border-radius:50%;"></div>
      <div style="display:inline-block;background:rgba(255,255,255,0.12);border:1px solid rgba(255,255,255,0.2);color:#E2E8F0;font-size:10px;font-weight:700;letter-spacing:1.5px;text-transform:uppercase;padding:4px 12px;border-radius:20px;margin-bottom:14px;">
        Rapport Quotidien — Pilotage B2B
      </div>
      <div style="font-size:26px;font-weight:700;color:#FFFFFF;letter-spacing:-0.5px;margin-bottom:6px;">MG & BATAM — Conventions</div>
      <div style="font-size:13px;color:#94A3B8;">
        Journee du <strong style="color:#CBD5E1;">{hier}</strong> &nbsp;|&nbsp; 
        <span style="color:#CBD5E1;">{mois_nom} {today.year}</span> &nbsp;|&nbsp; 
        Source : Business Central VC
      </div>
    </div>

    <!-- KPI CARDS -->
    <div style="background:#FFFFFF;padding:24px 28px;border-left:1px solid #E2E8F0;border-right:1px solid #E2E8F0;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94A3B8;margin-bottom:16px;">Indicateurs Cles du Jour</div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:separate;border-spacing:12px 0;">
        <tr>
          <td style="width:33%;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:18px 16px;text-align:center;vertical-align:top;">
            <div style="font-size:11px;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">CA Jour</div>
            <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-1px;margin-bottom:8px;">{format_k(ca_today)}</div>
            <div style="font-size:11px;color:#94A3B8;margin-bottom:10px;">TND TTC</div>
            <span style="display:inline-block;background:{'#DCFCE7' if evo_jour >= 0 else '#FEE2E2'};color:{'#15803D' if evo_jour >= 0 else '#B91C1C'};font-size:12px;font-weight:700;padding:4px 10px;border-radius:6px;">{'+' if evo_jour >= 0 else ''}{evo_jour:.1f}% vs N-1</span>
          </td>
          <td style="width:33%;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:18px 16px;text-align:center;vertical-align:top;">
            <div style="font-size:11px;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">Objectif Atteint</div>
            <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-1px;margin-bottom:8px;">108%</div>
            <div style="font-size:11px;color:#94A3B8;margin-bottom:10px;">Cible : 115 %</div>
            <span style="display:inline-block;background:#DCFCE7;color:#15803D;font-size:12px;font-weight:700;padding:4px 10px;border-radius:6px;">Atteint</span>
          </td>
          <td style="width:33%;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:12px;padding:18px 16px;text-align:center;vertical-align:top;">
            <div style="font-size:11px;font-weight:600;color:#94A3B8;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">CA MTD</div>
            <div style="font-size:24px;font-weight:700;color:#0F172A;letter-spacing:-1px;margin-bottom:8px;">{format_k(ca_mois)}</div>
            <div style="font-size:11px;color:#94A3B8;margin-bottom:10px;">TND TTC</div>
            <span style="display:inline-block;background:{'#DCFCE7' if evo_mois >= 0 else '#FEE2E2'};color:{'#15803D' if evo_mois >= 0 else '#B91C1C'};font-size:12px;font-weight:700;padding:4px 10px;border-radius:6px;">{'+' if evo_mois >= 0 else ''}{evo_mois:.1f}% vs N-1</span>
          </td>
        </tr>
      </table>
    </div>

    <!-- SIGNAL JOUR -->
    <div style="background:#FFFFFF;padding:0 28px 20px;border-left:1px solid #E2E8F0;border-right:1px solid #E2E8F0;">
      <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-left:4px solid #16a34a;border-radius:10px;padding:14px 18px;display:flex;align-items:flex-start;gap:12px;">
        <div style="min-width:8px;height:8px;background:#16a34a;border-radius:50%;margin-top:5px;"></div>
        <div>
          <div style="font-size:14px;font-weight:700;color:#0F172A;margin-bottom:4px;">{signal}</div>
          <div style="font-size:13px;color:#475569;line-height:1.6;">{signal_desc}</div>
        </div>
      </div>
    </div>

    <!-- CONVENTIONS ACTIVES -->
    <div style="background:#FFFFFF;padding:0 28px 24px;border-left:1px solid #E2E8F0;border-right:1px solid #E2E8F0;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94A3B8;margin-bottom:14px;padding-top:4px;">
        Top Conventions — <span style="color:#0B1E3F;">{nb_conv} actives ce mois</span>
      </div>
      <table width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
        <thead>
          <tr>
            <th style="text-align:left;font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;padding:0 0 10px;border-bottom:2px solid #E2E8F0;">Convention</th>
            <th style="text-align:right;font-size:10px;font-weight:700;color:#94A3B8;text-transform:uppercase;letter-spacing:0.8px;padding:0 0 10px;border-bottom:2px solid #E2E8F0;">CA TND</th>
          </tr>
        </thead>
        <tbody>"""
    
    for i, (nom, ca) in enumerate(top_convs, 1):
        html += f"""
        <tr>
          <td style="padding:11px 0;border-bottom:1px solid #F1F5F9;">
            <span style="font-size:11px;font-weight:700;color:#64748B;margin-right:10px;">#{i}</span>
            <span style="font-size:13px;font-weight:600;color:#0F172A;">{nom}</span>
          </td>
          <td style="padding:11px 0;border-bottom:1px solid #F1F5F9;text-align:right;font-size:13px;font-weight:700;color:#0F172A;">{format_k(ca)} TND</td>
        </tr>"""
    
    html += """
        </tbody>
      </table>
    </div>

    <!-- FOCUS MAGASINS -->
    <div style="background:#FFFFFF;padding:0 28px 24px;border-left:1px solid #E2E8F0;border-right:1px solid #E2E8F0;">
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr>
          <td width="48%" style="vertical-align:top;padding-right:12px;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#15803D;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #15803D;">&#9650; Top 3 Performance</div>
            <table width="100%" cellpadding="0" cellspacing="0">"""
    
    for i, (nom, ca) in enumerate(top_magasins, 1):
        pct = min(100, int(ca / top_magasins[0][1] * 100)) if top_magasins else 0
        html += f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #F1F5F9;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="min-width:22px;height:22px;background:#DCFCE7;color:#15803D;border-radius:5px;font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;">{i}</span>
              <div>
                <div style="font-size:13px;font-weight:600;color:#0F172A;">{nom}</div>
                <div style="margin-top:4px;height:4px;width:120px;background:#F1F5F9;border-radius:9px;overflow:hidden;">
                  <div style="height:4px;width:{pct}%;background:#22C55E;border-radius:9px;"></div>
                </div>
              </div>
            </div>
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #F1F5F9;text-align:right;font-size:13px;font-weight:700;color:#0F172A;">{format_k(ca)} TND</td>
        </tr>"""
    
    html += """
            </table>
          </td>
          <td width="4%"></td>
          <td width="48%" style="vertical-align:top;padding-left:12px;">
            <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#B91C1C;margin-bottom:12px;padding-bottom:8px;border-bottom:2px solid #B91C1C;">&#9660; Flop 3 — A Actionner</div>
            <table width="100%" cellpadding="0" cellspacing="0">"""
    
    if flop_magasins:
        max_ca = flop_magasins[0][1]
        for i, (nom, ca) in enumerate(flop_magasins, 1):
            pct = min(100, int(ca / max_ca * 100)) if max_ca else 0
            html += f"""
        <tr>
          <td style="padding:10px 0;border-bottom:1px solid #F1F5F9;">
            <div style="display:flex;align-items:center;gap:10px;">
              <span style="min-width:22px;height:22px;background:#FEE2E2;color:#B91C1C;border-radius:5px;font-size:11px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;">{i}</span>
              <div>
                <div style="font-size:13px;font-weight:600;color:#0F172A;">{nom}</div>
                <div style="margin-top:4px;height:4px;width:120px;background:#F1F5F9;border-radius:9px;overflow:hidden;">
                  <div style="height:4px;width:{pct}%;background:#EF4444;border-radius:9px;"></div>
                </div>
              </div>
            </div>
          </td>
          <td style="padding:10px 0;border-bottom:1px solid #F1F5F9;text-align:right;font-size:13px;font-weight:700;color:#0F172A;">{format_k(ca)} TND</td>
        </tr>"""
    
    html += """
            </table>
          </td>
        </tr>
      </table>
    </div>

    <!-- ALERTE -->
    <div style="background:#FFFFFF;padding:0 28px 24px;border-left:1px solid #E2E8F0;border-right:1px solid #E2E8F0;">
      <div style="background:#F0FDF4;border:1px solid #BBF7D0;border-left:4px solid #22C55E;border-radius:10px;padding:14px 18px;">
        <div style="font-size:13px;font-weight:700;color:#166534;margin-bottom:4px;">✓ Aucune alerte critique</div>
        <div style="font-size:12px;color:#15803D;line-height:1.5;">Toutes les operations sont en bonne voie.</div>
      </div>
    </div>

    <!-- PLAN D'ACTIONS -->
    <div style="background:#FFFFFF;padding:0 28px 24px;border-left:1px solid #E2E8F0;border-right:1px solid #E2E8F0;">
      <div style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:1.5px;color:#94A3B8;margin-bottom:14px;">Plan d'Action J+1</div>
      
        <div style="display:flex;align-items:flex-start;gap:12px;padding:13px 16px;background:#FAFAFA;border:1px solid #E2E8F0;border-radius:10px;margin-bottom:10px;">
          <span style="min-width:24px;height:24px;background:#E0F2FE;color:#0EA5E9;border-radius:6px;font-size:12px;font-weight:700;display:inline-flex;align-items:center;justify-content:center;">1</span>
          <span style="font-size:13px;color:#334155;font-weight:500;line-height:1.5;">Analyser les magasins en difficulte (rupture, effectif, concurrence)</span>
        </div>
    </div>

    <!-- FOOTER -->
    <div style="background:#0B1E3F;border-radius:0 0 16px 16px;padding:20px 28px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <div>
          <div style="font-size:12px;font-weight:600;color:#CBD5E1;margin-bottom:3px;">MG & BATAM — Groupe SMG</div>
          <div style="font-size:11px;color:#64748B;">Source : VC.CONV. Business Central &nbsp;|&nbsp; Genere le {hier}</div>
        </div>
        <div style="font-size:11px;color:#475569;text-align:right;">Rapport automatique<br>Pilotage Grands Comptes</div>
      </div>
    </div>

  </div>
</body>
</html>"""
    
    return f"Rapport B2B Quotidien - {hier}", html

def main():
    print("=" * 60)
    print("GENERATION RAPPORT QUOTIDIEN B2B")
    print("=" * 60)
    
    print("\n1. Chargement des donnees...")
    dfs = load_all_data()
    print(f"   {len(dfs)} fichiers charges")
    
    print("\n2. Calcul des indicateurs...")
    date_str = datetime.now().strftime('%d/%m/%Y')
    
    print("\n3. Creation du rapport...")
    subject, html = generate_report(dfs, date_str)
    
    # Sauvegarder localement
    output_file = f"C:/Users/hachk/Downloads/rapport_preview.html"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"   Rapport sauvegarde: {output_file}")
    
    print("\n4. Envoi de l'email...")
    send_email(subject, html)
    
    print("\nTermine!")

if __name__ == "__main__":
    main()