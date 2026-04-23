"""
Rapport Quotidien B2B - SMG
Envoi automatique par email
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
EMAIL_PASSWORD = "Azerty@4321!!!"

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/"

FILES = {
    "vc": quote("Factures ventes enregistrees VC (4).xlsx"),
    "vc_credit": quote("Factures ventes enregistrees VC credit conso.xlsx"),
    "conventions": quote("TDC CONVENTION 1.xlsm"),
    "code_magasin": quote("Code MAGASIN Business Central.xlsx"),
}

def load_excel(url):
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            return pd.read_excel(BytesIO(r.content))
    except:
        pass
    return None

def load_all_data():
    dfs = {}
    for name, filename in FILES.items():
        url = GITHUB_RAW + filename
        df = load_excel(url)
        if df is not None:
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

def generate_report(dfs):
    hier = (datetime.now() - timedelta(days=1)).strftime('%d/%m/%Y')
    today = datetime.now().strftime('%d/%m/%Y')
    
    ca_today = 0
    ca_yesterday = 0
    ca_month = 0
    
    if "vc" in dfs:
        df = dfs["vc"]
        date_col = None
        amount_col = None
        
        for col in df.columns:
            col_lower = col.lower() if isinstance(col, str) else ""
            if date_col is None and ("date" in col_lower or "jour" in col_lower):
                date_col = col
            if amount_col is None and ("montant" in col_lower or "ca" in col_lower):
                amount_col = col
        
        if date_col and amount_col:
            try:
                df[date_col] = pd.to_datetime(df[date_col], errors='coerce')
                df["Jour"] = df[date_col].dt.date
                
                today_date = datetime.now().date()
                yesterday_date = (datetime.now() - timedelta(days=1)).date()
                
                ca_today = df[df["Jour"] == today_date][amount_col].sum()
                ca_yesterday = df[df["Jour"] == yesterday_date][amount_col].sum()
                ca_month = df[df[date_col].dt.month == datetime.now().month][amount_col].sum()
            except:
                pass
    
    subject = f"Rapport B2B Quotidien - {hier}"
    
    html = f"""
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
            .container {{ max-width: 800px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; }}
            .header {{ background: #1E40AF; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
            .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 8px; }}
            .metric {{ display: inline-block; margin: 10px 20px; text-align: center; }}
            .metric-value {{ font-size: 28px; font-weight: bold; color: #1E40AF; }}
            .metric-label {{ font-size: 14px; color: #666; }}
            table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
            th {{ background: #1E40AF; color: white; padding: 12px; text-align: left; }}
            td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
            .positive {{ color: #059669; font-weight: bold; }}
            .negative {{ color: #DC2626; font-weight: bold; }}
            .footer {{ text-align: center; margin-top: 30px; color: #666; font-size: 12px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Rapport Quotidien B2B - SMG</h1>
                <p>Date: {hier}</p>
            </div>
            
            <div class="section">
                <h2>Indicateurs cles</h2>
                <div class="metric">
                    <div class="metric-value">{ca_today:,.0f} TND</div>
                    <div class="metric-label">CA Aujourd'hui</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{ca_yesterday:,.0f} TND</div>
                    <div class="metric-label">CA Hier</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{ca_month:,.0f} TND</div>
                    <div class="metric-label">CA Mois en cours</div>
                </div>
            </div>
            
            <div class="section">
                <h2>Alertes</h2>
                <p>Aucune alerte pour cette periode.</p>
            </div>
            
            <div class="footer">
                <p>Genere automatiquement le {datetime.now().strftime('%d/%m/%Y a %H:%M')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return subject, html

def main():
    print("=" * 60)
    print("GENERATION RAPPORT QUOTIDIEN B2B")
    print("=" * 60)
    
    print("\n1. Chargement des donnees...")
    dfs = load_all_data()
    print(f"   {len(dfs)} fichiers charges")
    
    print("\n2. Calcul des indicateurs...")
    # Calculs effectues dans generate_report
    
    print("\n3. Creation du rapport...")
    subject, html = generate_report(dfs)
    
    print("\n4. Envoi de l'email...")
    send_email(subject, html)
    
    print("\nTermine!")

if __name__ == "__main__":
    main()