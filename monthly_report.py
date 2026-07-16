# coding: utf-8
"""
Rapport Mensuel B2B - SMG (MG & BATAM)
Generation automatique du rapport mensuel conventions + EDC
avec analyse IA par convention, commentaires et recommandations.

Usage:
    python monthly_report.py                     # Mois precedent, sauvegarde + email
    python monthly_report.py --month 6 --year 2026  # Mois specifique
    python monthly_report.py --no-email           # Sauvegarde locale seulement
    python monthly_report.py --no-ai              # Rapport sans analyse IA

API IA gratuite (Groq - Llama 3) :
    1. Cree un compte gratuit sur https://console.groq.com (sans CB)
    2. Genere une cle API (commence par gsk_)
    3. Configure-la :
       set LLM_API_KEY=gsk_votre-cle-groq    (dans CMD)
       Ou dans variables d'environnement Windows

Sortie :
    - Rapport HTML sauvegarde localement
    - Copie dans le presse-papiers (Windows)
    - Email envoye via SMTP SMG (optionnel)
"""

import os
import re
import json
import sys
import smtplib
import argparse
import subprocess
import warnings
from datetime import datetime, timedelta
from io import BytesIO
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import pandas as pd
import requests

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ─── Configuration ─────────────────────────────────────────────

EMAIL_FROM = "Hamadi.Chkondali@SMG.com.tn"
EMAIL_TO = ["Hamadi.Chkondali@SMG.com.tn"]
SMTP_SERVER = "mail.SMG.com.tn"
SMTP_PORT = 587
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
# Par defaut : Groq (API gratuite, sans CB, modele Llama 3 70B)
# Alternatives payantes : mettre LLM_MODEL=gpt-4o-mini et LLM_ENDPOINT=https://api.openai.com/v1/chat/completions
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
LLM_ENDPOINT = os.getenv("LLM_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")

GITHUB_RAW = "https://raw.githubusercontent.com/chkondali-dev/pilotage-b2b/main/2025/"

FILES = {
    "vc":                "Factures%20ventes%20enregistr%C3%A9es%20VC%20(4).xlsx",
    "vc_credit":         "Factures%20ventes%20enregistr%C3%A9es%20VC%20credit%20conso.xlsx",
    "vc_edc":            "Factures%20ventes%20enregistr%C3%A9es%20VC%20CONVENTION%20EDC.xlsx",
    "conventions":       "TDC%20CONVENTION%201.xlsm",
    "code_magasin":      "Code%20MAGASIN%20Business%20Central.xlsx",
    "cube_magasin":      "CUBE%20MAGASIN.xlsx",
}

MOIS_NOMS = {
    1: "Janvier", 2: "Fevrier", 3: "Mars", 4: "Avril",
    5: "Mai", 6: "Juin", 7: "Juillet", 8: "Aout",
    9: "Septembre", 10: "Octobre", 11: "Novembre", 12: "Decembre",
}

MOIS_COURTS = {
    1: "Jan", 2: "Fev", 3: "Mar", 4: "Avr",
    5: "Mai", 6: "Juin", 7: "Juil", 8: "Aou",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec",
}

SORTIE = Path.home() / "Downloads" / "rapport_mensuel"
CACHE_DIR = Path(__file__).parent / ".cache_monthly"
PROMPT_FILE = Path(__file__).parent / "prompts" / "analyse_convention.md"


# ─── Data Loading ──────────────────────────────────────────────

def load_excel(url: str) -> pd.DataFrame | None:
    """Charge un fichier Excel depuis une URL."""
    try:
        r = requests.get(url, timeout=30)
        if r.status_code == 200:
            df = pd.read_excel(BytesIO(r.content), engine="openpyxl")
            df.columns = df.columns.str.replace("\n", " ").str.strip()
            for col in df.select_dtypes("str").columns:
                df[col] = df[col].astype(str).str.strip()
            return df
    except Exception as e:
        print(f"  ⚠️  Erreur chargement {url}: {e}")
    return None


def load_all_data() -> dict:
    """Charge tous les fichiers depuis GitHub."""
    print("  Chargement des donnees...")
    dfs = {}
    for name, filename in FILES.items():
        url = GITHUB_RAW + filename
        df = load_excel(url)
        if df is not None:
            dfs[name] = df
            print(f"    ✓ {name}: {len(df)} lignes")
        else:
            dfs[name] = pd.DataFrame()
            print(f"    ✗ {name}: non trouve")
    return dfs


# ─── Data Processing ───────────────────────────────────────────

def _add_date_cols(df: pd.DataFrame) -> pd.DataFrame:
    """Ajoute colonnes Annee/Mois/Jour depuis la colonne date."""
    if df.empty:
        return df
    date_col = next(
        (c for c in df.columns if "date" in c.lower() and "comptabil" in c.lower()),
        None
    )
    if date_col is None:
        date_col = next(
            (c for c in df.columns if "date" in c.lower()),
            None
        )
    if date_col is None:
        return df
    df = df.copy()
    df["Date"] = pd.to_datetime(df[date_col], errors="coerce")
    df["Annee"] = df["Date"].dt.year.astype("Int64")
    df["Mois"] = df["Date"].dt.month.astype("Int64")
    df["Jour"] = df["Date"].dt.day.astype("Int64")
    return df


def _map_magasins(df: pd.DataFrame, code_df: pd.DataFrame) -> pd.DataFrame:
    """Mapping code magasin → nom + enseigne."""
    if df.empty or code_df.empty:
        return df
    df = df.copy()
    df["Enseigne"] = "MG"
    df["Magasin"] = "Inconnu"
    code_col_src = next((c for c in df.columns if c.lower() == "unite code"), None)
    if not code_col_src:
        return df
    code_col = list(code_df.columns)[0]
    unite_col = list(code_df.columns)[2] if len(code_df.columns) > 2 else list(code_df.columns)[1]
    def get_ense(unit: str) -> str:
        s = str(unit).upper()
        return "BATAM" if ("BATAM" in s or "BTM" in s) else "MG"
    code_df = code_df.copy()
    code_df.columns = code_df.columns.str.strip()
    code_df["Enseigne"] = code_df[unite_col].apply(get_ense)
    code_df[code_col] = code_df[code_col].astype(str).str.strip()
    mapping_nom = code_df.set_index(code_col)[unite_col].to_dict()
    mapping_ense = code_df.set_index(code_col)["Enseigne"].to_dict()
    df[code_col_src] = df[code_col_src].astype(str).str.strip()
    df["Magasin"] = df[code_col_src].map(mapping_nom).fillna(df[code_col_src])
    df["Enseigne"] = df[code_col_src].map(mapping_ense).fillna("MG")
    return df


def format_k(x: float) -> str:
    """Formate un nombre en K/M."""
    if x >= 1_000_000:
        return f"{x/1_000_000:.2f}M"
    elif x >= 1_000:
        return f"{x/1_000:.1f}k"
    elif x >= 0:
        return f"{x:,.0f}"
    return "0"


def evol_pct(n: float, n1: float) -> float:
    """Pourcentage d'evolution."""
    if n1 == 0:
        return 100.0 if n > 0 else 0.0
    return round((n - n1) / n1 * 100, 2)


# ─── KPI Engine ────────────────────────────────────────────────

def ca_periode(df: pd.DataFrame, annee: int, mois: int) -> float:
    """CA pour un mois donne."""
    if df.empty or "Montant TTC" not in df.columns:
        return 0.0
    d = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
    return float(d["Montant TTC"].sum())


def nb_dossiers(df: pd.DataFrame, annee: int, mois: int) -> int:
    """Nombre de factures/dossiers pour un mois."""
    if df.empty:
        return 0
    return int(len(df[(df["Annee"] == annee) & (df["Mois"] == mois)]))


def panier_moyen(df: pd.DataFrame, annee: int, mois: int) -> float:
    """Panier moyen pour un mois."""
    d = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
    if len(d) == 0 or "Montant TTC" not in d.columns:
        return 0.0
    return float(d["Montant TTC"].mean())


def top_conventions(df: pd.DataFrame, annee: int, mois: int, n: int = 5) -> list:
    """Top N conventions par CA."""
    if df.empty or "Nom" not in df.columns or "Montant TTC" not in df.columns:
        return []
    d = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
    top = d.groupby("Nom")["Montant TTC"].sum().sort_values(ascending=False).head(n)
    return list(top.items())


def flop_conventions(df: pd.DataFrame, annee: int, mois: int, annee_n1: int, mois_n1: int, n: int = 5) -> list:
    """Conventions avec la plus forte baisse d'activite.
    Retourne une liste de tuples (nom, evolution_pct)."""
    if df.empty or "Nom" not in df.columns:
        return []
    d_n = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
    d_n1 = df[(df["Annee"] == annee_n1) & (df["Mois"] == mois_n1)]
    ca_n = d_n.groupby("Nom")["Montant TTC"].sum()
    ca_n1 = d_n1.groupby("Nom")["Montant TTC"].sum()
    comp = pd.DataFrame({"ca_n": ca_n, "ca_n1": ca_n1}).fillna(0)
    comp = comp[comp["ca_n1"] > 0].copy()
    comp["evol"] = round((comp["ca_n"] - comp["ca_n1"]) / comp["ca_n1"] * 100, 1)
    comp = comp.sort_values("evol").head(n)
    return list(comp["evol"].items())  # (nom, evol_pct)


def conventions_actives(df: pd.DataFrame, annee: int, mois: int) -> int:
    """Nombre de conventions avec activite dans le mois."""
    if df.empty or "Nom" not in df.columns:
        return 0
    return int(df[(df["Annee"] == annee) & (df["Mois"] == mois)]["Nom"].nunique())


def magasins_contributeurs(df: pd.DataFrame, annee: int, mois: int) -> int:
    """Nombre de magasins avec activite dans le mois."""
    if df.empty:
        return 0
    d = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
    if "Magasin" in d.columns:
        return int(d["Magasin"].nunique())
    if "Nom" in d.columns:
        return int(d["Nom"].nunique())
    return 0


def analyse_par_convention(df: pd.DataFrame, annee: int, mois: int, annee_n1: int) -> list[dict]:
    """Analyse detaillee par convention pour le mois."""
    if df.empty or "Nom" not in df.columns:
        return []
    d_n = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
    d_n1 = df[(df["Annee"] == annee_n1) & (df["Mois"] == mois)]
    ca_n = d_n.groupby("Nom")["Montant TTC"].sum()
    ca_n1 = d_n1.groupby("Nom")["Montant TTC"].sum()
    nb_n = d_n.groupby("Nom").size()
    comp = pd.DataFrame({
        "ca_n": ca_n, "ca_n1": ca_n1, "nb_n": nb_n
    }).fillna(0).reset_index()
    comp["evol"] = comp.apply(
        lambda r: round((r["ca_n"] - r["ca_n1"]) / r["ca_n1"] * 100, 1)
        if r["ca_n1"] > 0 else (100 if r["ca_n"] > 0 else 0), axis=1
    )
    comp = comp.sort_values("ca_n", ascending=False)
    result = []
    for _, r in comp.iterrows():
        signal = "green" if r["evol"] >= 5 else ("amber" if r["evol"] >= -5 else "red")
        result.append({
            "nom": r["Nom"],
            "ca_mois": round(r["ca_n"], 2),
            "ca_mois_n1": round(r["ca_n1"], 2),
            "evolution_pct": r["evol"],
            "nb_dossiers": int(r["nb_n"]),
            "signal": signal,
        })
    return result


def _normalize_ia_response(raw: dict) -> dict:
    """Normalise la reponse IA (l'IA peut utiliser differents noms de champs)."""
    normalized = {}

    # synthese_globale : peut etre un string ou un dict
    sg = raw.get("synthese_globale") or raw.get("synthese") or raw.get("resume") or ""
    if isinstance(sg, dict):
        # Si c'est un dict, on le convertit en phrase
        parts = []
        for k, v in sg.items():
            if isinstance(v, (int, float)):
                parts.append(f"{k}: {v:,.0f}")
            else:
                parts.append(f"{k}: {v}")
        normalized["synthese_globale"] = ". ".join(parts) + "."
    else:
        normalized["synthese_globale"] = str(sg) if sg else ""

    # conventions : plusieurs noms possibles
    convs = (
        raw.get("conventions") or
        raw.get("donnees_par_convention") or
        raw.get("analyse_par_convention") or
        raw.get("conventions_data") or
        []
    )
    normalized["conventions"] = []
    for c in convs if isinstance(convs, list) else []:
        if not isinstance(c, dict):
            continue
        norm_c = {
            "nom": c.get("nom") or c.get("Nom") or c.get("Convention") or c.get("convention") or "",
            "ca_mois": c.get("ca_mois") or c.get("CA_N") or c.get("ca_n") or c.get("ca_mois_N") or 0,
            "ca_mois_n1": c.get("ca_mois_n1") or c.get("CA_N_1") or c.get("CA_N-1") or c.get("ca_n1") or 0,
            "evolution_pct": c.get("evolution_pct") or c.get("Evolution") or c.get("evolution") or c.get("evol") or 0,
            "signal": c.get("signal") or c.get("Signal") or "amber",
            "risque": c.get("risque") or c.get("Risque") or "moyen",
            "tendance": c.get("tendance") or c.get("Tendance") or "stable",
            "commentaire": c.get("commentaire") or c.get("Commentaire") or c.get("analyse") or c.get("Analyse") or "",
            "recommandation": c.get("recommandation") or c.get("Recommandation") or c.get("recommendation") or "surveiller",
            "action": c.get("action") or c.get("Action") or "",
        }
        # S'assurer que les valeurs numeriques sont bien des nombres
        for num_field in ["ca_mois", "ca_mois_n1", "evolution_pct"]:
            try:
                norm_c[num_field] = float(norm_c[num_field] or 0)
            except (ValueError, TypeError):
                norm_c[num_field] = 0
        normalized["conventions"].append(norm_c)

    # priorites
    normalized["priorites"] = (
        raw.get("priorites") or
        raw.get("priorites") or
        raw.get("priorites_action") or
        raw.get("plan_action") or
        raw.get("recommandations") or
        []
    )
    if isinstance(normalized["priorites"], str):
        normalized["priorites"] = [normalized["priorites"]]
    if not isinstance(normalized["priorites"], list):
        normalized["priorites"] = []

    # conclusion
    conclusion = (
        raw.get("conclusion") or
        raw.get("Conclusion") or
        raw.get("resume_executif") or
        ""
    )
    normalized["conclusion"] = str(conclusion) if conclusion else ""

    return normalized


def analyse_par_magasin(df: pd.DataFrame, annee: int, mois: int, annee_n1: int) -> list[dict]:
    """Analyse detaillee par magasin."""
    if df.empty or "Magasin" not in df.columns:
        return []
    d_n = df[(df["Annee"] == annee) & (df["Mois"] == mois)]
    d_n1 = df[(df["Annee"] == annee_n1) & (df["Mois"] == mois)]
    ca_n = d_n.groupby("Magasin")["Montant TTC"].sum()
    ca_n1 = d_n1.groupby("Magasin")["Montant TTC"].sum()
    comp = pd.DataFrame({"ca_n": ca_n, "ca_n1": ca_n1}).fillna(0).reset_index()
    comp["evol"] = comp.apply(
        lambda r: round((r["ca_n"] - r["ca_n1"]) / r["ca_n1"] * 100, 1)
        if r["ca_n1"] > 0 else (100 if r["ca_n"] > 0 else 0), axis=1
    )
    comp = comp.sort_values("ca_n", ascending=False)
    result = []
    for _, r in comp.iterrows():
        result.append({
            "magasin": r["Magasin"],
            "ca_mois": round(r["ca_n"], 2),
            "ca_mois_n1": round(r["ca_n1"], 2),
            "evolution_pct": r["evol"],
        })
    return result


# ─── LLM Integration ───────────────────────────────────────────

def call_llm(prompt: str, api_key: str | None = None) -> str | None:
    """Appelle l'API LLM avec le prompt structure."""
    key = api_key or LLM_API_KEY or os.getenv("LLM_API_KEY", "")
    if not key:
        print("  ⚠️  Pas de cle API LLM configuree (LLM_API_KEY)")
        return None
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": LLM_MODEL,
        "messages": [
            {"role": "system", "content": "Tu es un analyste commercial senior. Reponds en JSON uniquement."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.3,
        "max_tokens": 8000,
        "response_format": {"type": "json_object"},
    }
    try:
        print(f"  Appel LLM ({LLM_MODEL}) via {LLM_ENDPOINT.split('/')[2]}...")
        r = requests.post(LLM_ENDPOINT, headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        resp = r.json()
        content = resp["choices"][0]["message"]["content"]
        # Nettoyer le JSON (parer les cas ou le LLM met du markdown)
        content = re.sub(r"^```(?:json)?\s*", "", content.strip())
        content = re.sub(r"\s*```$", "", content)
        return content
    except Exception as e:
        print(f"  ⚠️  Erreur API LLM: {e}")
        try:
            debug_file = SORTIE / f"ia_raw_response_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            debug_file.write_text(str(r.text[:5000] if 'r' in dir() else 'N/A'), encoding='utf-8')
            print(f"      Reponse brute sauvegardee: {debug_file}")
        except:
            pass
        return None


def _calc_trend_3m(df: pd.DataFrame, nom: str, annee: int, mois: int) -> list:
    """Calcule le CA des 3 derniers mois pour une convention."""
    trend = []
    for i in range(2, -1, -1):
        m = mois - i
        y = annee
        while m < 1:
            m += 12
            y -= 1
        ca = ca_periode(df[df["Nom"] == nom], y, m)
        trend.append(round(ca, 0))
    return trend


def _calc_consecutive_declines(df: pd.DataFrame, nom: str, annee: int, mois: int) -> int:
    """Calcule le nombre de mois consecutifs de baisse (vs N-1)."""
    count = 0
    for i in range(6):  # Regarder jusqu'a 6 mois en arriere
        m = mois - i
        y = annee
        while m < 1:
            m += 12
            y -= 1
        ca_n = ca_periode(df[df["Nom"] == nom], y, m)
        ca_n1 = ca_periode(df[df["Nom"] == nom], y - 1, m)
        if ca_n1 > 0 and ca_n < ca_n1:
            count += 1
        else:
            break
    return count


def _detect_inactive(df: pd.DataFrame) -> dict:
    """Detecte les conventions sans aucune vente depuis N jours."""
    if df.empty or "Nom" not in df.columns or "Date" not in df.columns:
        return {}
    today = pd.Timestamp.today().normalize()
    last = df.groupby("Nom")["Date"].max().reset_index()
    last.columns = ["Nom", "DerniereVente"]
    last["Jours"] = (today - last["DerniereVente"]).dt.days
    inactive = {}
    for _, r in last.iterrows():
        if r["Jours"] > 30:
            inactive[r["Nom"]] = int(r["Jours"])
    return inactive


def build_llm_prompt(data: dict) -> str:
    """Construit le prompt compact pour l'analyse IA approfondie (20+ conventions)."""
    df_vc_full = data.get("_df_vc", pd.DataFrame())

    # Donnees des conventions (top 25 max) - format compact
    conv_lines = ""
    for c in data["conventions"][:25]:
        nom = c["nom"]
        t = _calc_trend_3m(df_vc_full, nom, data["annee"], data["mois"])
        d = _calc_consecutive_declines(df_vc_full, nom, data["annee"], data["mois"])
        t_str = f" T3M:{','.join(format_k(v) for v in t)}" if t else ""
        d_str = f" B{d}mois" if d > 0 else ""
        conv_lines += f"  {nom}: CA={format_k(c['ca_mois'])},N-1={format_k(c['ca_mois_n1'])},evol={c['evolution_pct']:+.1f}%,dos={c['nb_dossiers']}{t_str}{d_str}\n"

    top_lines = "\n".join(f"  {i}. {t[0]}:{format_k(t[1])}TND" for i, t in enumerate(data["top_convs"], 1))
    flop_lines = "\n".join(f"  {i}. {f[0]}:{f[1]:+.1f}%" for i, f in enumerate(data["flop_convs"], 1))
    mag_lines = "\n".join(f"  {m['magasin']}:{format_k(m['ca_mois'])}TND({m['evolution_pct']:+.1f}%)" for m in data["magasins"][:15])

    prompt = f"""Tu es un analyste commercial senior chez SMG Tunisie. Analyse les ventes B2B du credit du mois. Sois CHIFFRE, CONCRET, INTERDIS-TOI les phrases "probablement due a", "bonne gestion", "concurrence accrue".

MOIS: {data['mois_nom']} {data['annee']}
CA Total: {format_k(data['ca_total'])}TND ({data['var_total']:+.1f}%)
Conventions: {format_k(data['ca_conv'])}TND ({data['var_conv']:+.1f}%) | EDC: {format_k(data['ca_edc'])}TND ({data['var_edc']:+.1f}%)
Actives: {data['conv_actives']} convs | {data['mag_contributeurs']} magasins

TOP: {top_lines}
FLOP: {flop_lines}

CONVENTIONS:
{conv_lines}

MAGASINS:
{mag_lines}

GENERE un JSON avec TOUTES les 25 conventions listees dans CONVENTIONS:
{{
  "synthese_globale": "3-5 phrases. Resume le mois, chiffres cles, causes externes vs internes",
  "conventions": [
    {{
      "nom": "COFAT TUNIS",
      "ca_mois": 204600,
      "ca_mois_n1": 168000,
      "evolution_pct": 21.8,
      "signal": "green",
      "commentaire": "ex: Passe de 168k a 204k (+21.8%). Tendance 3 mois: 92k, 116k, 204k. Croissance soutenue. Explique POURQUOI avec les chiffres.",
      "recommandation": "reconduire|surveiller|renegocier|relancer|suspendre",
      "action": "action CONCRETE verifiable"
    }}
    ... REPETE pour CHACUNE des 25 conventions listees ci-dessus
  ],
  "priorites": ["3-5 actions classees par urgence avec impact potentiel"],
  "conclusion": "2-4 phrases. Message cle pour la direction."
}}
CRITIQUE: "ca_mois" doit contenir la VALEUR REELLE de la convention, pas 0 et pas le total."
"""
    return prompt


# ─── Rapport HTML ──────────────────────────────────────────────

def generer_html(data: dict, analyse_ia: dict | None = None) -> str:
    """Genere le rapport HTML complet, copiable comme texte."""
    m = data["mois"]
    a = data["annee"]
    mois_nom = MOIS_NOMS.get(m, str(m))
    mois_court = MOIS_COURTS.get(m, str(m))

    jours_data = datetime.now().strftime("%d/%m/%Y")

    # ── Preparer donnees ──
    ca_conv_s = format_k(data["ca_conv"])
    ca_conv_n1_s = format_k(data["ca_conv_n1"])
    ca_edc_s = format_k(data["ca_edc"])
    ca_edc_n1_s = format_k(data["ca_edc_n1"])
    ca_total_s = format_k(data["ca_total"])
    ca_total_n1_s = format_k(data["ca_total_n1"])

    def evol_html(v: float) -> str:
        cls = "green" if v >= 0 else "red"
        arrow = "▲" if v >= 0 else "▼"
        v_str = f"{abs(v):.1f}"
        return f'<span class="{cls}">{arrow} {v_str}%</span>'

    evol_conv_h = evol_html(data["var_conv"])
    evol_edc_h = evol_html(data["var_edc"])
    evol_total_h = evol_html(data["var_total"])
    evol_nb_h = evol_html(data["var_nb_conv"])
    evol_nb_edc_h = evol_html(data["var_nb_edc"])
    evol_panier_h = evol_html(data["var_panier"])
    evol_panier_edc_h = evol_html(data["var_panier_edc"])

    # ── Commentaire IA ──
    ia_synthese = ""
    ia_conventions_html = ""
    ia_priorites_html = ""
    ia_conclusion_html = ""

    if analyse_ia:
        ia_synthese = f"""
        <div class="ia-box">
            <div class="ia-label">[IA] Analyse IA</div>
            <p class="ia-text">{analyse_ia.get("synthese_globale", "")}</p>
        </div>"""

        ia_conventions_html = f"""
        <h3 style="font-size:13px;font-weight:700;margin:16px 0 8px;color:#0F172A;">Conventions</h3>
        <table>
        <tr><th>Convention</th><th style="text-align:right">CA {mois_court} {a}</th><th style="text-align:right">CA {mois_court} {a-1}</th><th style="text-align:right">Evol</th></tr>"""

        for c in data["conventions"]:
            ca_f = format_k(c["ca_mois"])
            ca_n1_f = format_k(c["ca_mois_n1"])
            ev = c["evolution_pct"]
            arrow = "▲" if ev >= 0 else "▼"
            cls = "green" if ev >= 0 else "red"
            ev_str = f"{abs(ev):.1f}"
            ia_conventions_html += f"""
        <tr>
            <td>{c['nom']}</td>
            <td class="num">{ca_f} TND</td>
            <td class="num">{ca_n1_f} TND</td>
            <td class="num {cls}">{arrow} {ev_str}%</td>
        </tr>"""
        ia_conventions_html += "</table>"

        # Commentaires IA condenses pour les conventions en baisse
        alertes = [c for c in analyse_ia.get("conventions", []) if c.get("signal") == "red" and c.get("commentaire")]
        if alertes:
            ia_conventions_html += """
        <div class="ia-box" style="background:#FEF2F2;border-color:#FECACA;border-left-color:#DC2626;margin-top:12px;">
            <div class="ia-label" style="color:#991B1B;">Alertes IA - Conventions en baisse</div>"""
            for c in alertes[:5]:
                ia_conventions_html += f"""
            <p style="font-size:12px;margin:4px 0;color:#1E293B;"><strong>{c['nom']}:</strong> {c.get('commentaire','')[:150]}</p>"""
            ia_conventions_html += """
        </div>"""

        priorites = analyse_ia.get("priorites", [])
        if priorites:
            items = "".join(f'<li>{p}</li>' for p in priorites)
            ia_priorites_html = f"""
            <div class="ia-box priorities">
                <div class="ia-label">[target] Priorites action</div>
                <ol class="priority-list">{items}</ol>
            </div>"""

        conclusion = analyse_ia.get("conclusion", "")
        if conclusion:
            ia_conclusion_html = f"""
            <div class="ia-box conclusion">
                <div class="ia-label">[pin] Conclusion</div>
                <p class="ia-text">{conclusion}</p>
            </div>"""

    # ── Conventions lines ──
    conv_rows = ""
    for c in data["conventions"]:
        ca_f = format_k(c["ca_mois"])
        ca_n1_f = format_k(c["ca_mois_n1"])
        ev = c["evolution_pct"]
        arrow = "▲" if ev >= 0 else "▼"
        cls = "green" if ev >= 0 else "red"
        ev_str = f"{abs(ev):.1f}"
        conv_rows += f"""
        <tr>
            <td>{c['nom']}</td>
            <td class="num">{ca_f} TND</td>
            <td class="num">{ca_n1_f} TND</td>
            <td class="num {cls}">{arrow} {ev_str}%</td>
            <td class="num">{c['nb_dossiers']}</td>
        </tr>"""

    # ── Magasins lines ──
    mag_rows = ""
    for m in data["magasins"][:15]:
        ca_f = format_k(m["ca_mois"])
        ca_n1_f = format_k(m["ca_mois_n1"])
        ev = m["evolution_pct"]
        arrow = "▲" if ev >= 0 else "▼"
        cls = "green" if ev >= 0 else "red"
        ev_str = f"{abs(ev):.1f}"
        mag_rows += f"""
        <tr>
            <td>{m['magasin']}</td>
            <td class="num">{ca_f} TND</td>
            <td class="num">{ca_n1_f} TND</td>
            <td class="num {cls}">{arrow} {ev_str}%</td>
        </tr>"""

    # ── Top / Flop ──
    top_rows = ""
    for i, (nom, ca) in enumerate(data["top_convs"], 1):
        top_rows += f"""
        <tr>
            <td class="rank">#{i}</td>
            <td>{nom}</td>
            <td class="num">{format_k(ca)} TND</td>
        </tr>"""

    flop_rows = ""
    for i, f in enumerate(data["flop_convs"], 1):
        f_pct = f"{f[1]:+.1f}"
        flop_rows += f"""
        <tr>
            <td class="rank">#{i}</td>
            <td>{f[0]}</td>
            <td class="num red">{f_pct}%</td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rapport Mensuel B2B - {mois_nom} {a}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background:#EEF2F7; font-family:system-ui,-apple-system,'Segoe UI',Roboto,sans-serif; padding:24px; color:#0F172A; }}
.container {{ max-width:720px; margin:0 auto; }}

/* Header */
.header {{ background:linear-gradient(135deg,#0B1E3F,#1A3460); border-radius:16px 16px 0 0; padding:28px 32px; position:relative; overflow:hidden; }}
.header .badge {{ display:inline-block; background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.2); color:#E2E8F0; font-size:10px; font-weight:700; letter-spacing:1.5px; text-transform:uppercase; padding:4px 12px; border-radius:20px; margin-bottom:14px; }}
.header h1 {{ font-size:24px; font-weight:700; color:#FFFFFF; margin-bottom:4px; }}
.header .sub {{ font-size:13px; color:#94A3B8; }}

/* Sections */
.section {{ background:#FFFFFF; padding:24px 28px; border-left:1px solid #E2E8F0; border-right:1px solid #E2E8F0; }}
.section-title {{ font-size:10px; font-weight:700; text-transform:uppercase; letter-spacing:1.5px; color:#94A3B8; margin-bottom:16px; padding-bottom:8px; border-bottom:2px solid #E2E8F0; }}

/* Tables */
table {{ width:100%; border-collapse:collapse; font-size:13px; }}
th {{ text-align:left; font-size:10px; font-weight:700; color:#94A3B8; text-transform:uppercase; letter-spacing:0.8px; padding:8px 6px; border-bottom:2px solid #E2E8F0; }}
td {{ padding:10px 6px; border-bottom:1px solid #F1F5F9; }}
td.num {{ text-align:right; font-weight:600; font-variant-numeric:tabular-nums; }}
.rank {{ color:#64748B; font-weight:700; font-size:11px; width:32px; }}

/* Colors */
.green {{ color:#059669; }}
.red {{ color:#DC2626; }}
.amber {{ color:#D97706; }}

/* IA Box */
.ia-box {{ background:#F0FDF4; border:1px solid #BBF7D0; border-left:4px solid #16A34A; border-radius:10px; padding:16px 20px; margin-bottom:16px; }}
.ia-box.priorities {{ background:#FFFBEB; border-color:#FDE68A; border-left-color:#D97706; }}
.ia-box.conclusion {{ background:#EFF6FF; border-color:#BFDBFE; border-left-color:#2563EB; }}
.ia-label {{ font-size:11px; font-weight:700; text-transform:uppercase; letter-spacing:1px; color:#64748B; margin-bottom:8px; }}
.ia-text {{ font-size:13px; line-height:1.7; color:#1E293B; }}

/* Convention Cards */
.conv-card {{ border:1px solid #E2E8F0; border-radius:10px; padding:14px 16px; margin-bottom:10px; border-left:4px solid #94A3B8; }}
.conv-green {{ border-left-color:#059669; background:#F0FDF4; }}
.conv-amber {{ border-left-color:#D97706; background:#FFFBEB; }}
.conv-red {{ border-left-color:#DC2626; background:#FEF2F2; }}
.conv-header {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:6px; }}
.conv-name {{ font-size:14px; font-weight:700; color:#0F172A; }}
.conv-reco {{ font-size:11px; font-weight:700; padding:3px 8px; border-radius:5px; background:#E2E8F0; }}
.conv-green .conv-reco {{ background:#DCFCE7; color:#15803D; }}
.conv-amber .conv-reco {{ background:#FEF3C7; color:#92400E; }}
.conv-red .conv-reco {{ background:#FEE2E2; color:#991B1B; }}
.conv-kpis {{ display:flex; gap:16px; margin-bottom:8px; font-size:12px; color:#64748B; }}
.kpi strong {{ color:#0F172A; }}
.kpi.evol {{ font-weight:700; }}
.conv-comment {{ font-size:13px; line-height:1.6; color:#334155; margin-bottom:4px; }}
.conv-action {{ font-size:12px; color:#1D4ED8; margin-top:4px; padding-top:8px; border-top:1px solid #E2E8F0; }}

/* Priorities */
.priority-list {{ margin:8px 0 0 20px; }}
.priority-list li {{ font-size:13px; line-height:1.7; color:#334155; margin-bottom:4px; }}

/* Footer */
.footer {{ background:#0B1E3F; border-radius:0 0 16px 16px; padding:20px 28px; display:flex; justify-content:space-between; align-items:center; }}
.footer-left {{ font-size:12px; color:#CBD5E1; }}
.footer-right {{ font-size:11px; color:#475569; text-align:right; }}

/* Sync */
@media (prefers-color-scheme:dark) {{
    body {{ background:#0F172A; color:#E2E8F0; }}
    .section {{ background:#1E293B; border-color:#334155; }}
    table, td {{ border-color:#334155; }}
    th {{ color:#64748B; }}
    .conv-card {{ background:#1E293B; border-color:#334155; }}
    .ia-text {{ color:#CBD5E1; }}
    .ia-box {{ background:#1A3A2A; border-color:#2D5A3A; }}
    .ia-box.priorities {{ background:#3A2A1A; border-color:#5A4A2D; }}
    .ia-box.conclusion {{ background:#1A2A3A; border-color:#2D4A5A; }}
    .conv-name {{ color:#E2E8F0; }}
    .conv-card.conv-green {{ background:#0F2A1A; }}
    .conv-card.conv-amber {{ background:#2A1F0F; }}
    .conv-card.conv-red {{ background:#2A0F0F; }}
}}
</style>
</head>
<body>
<div class="container">

    <!-- HEADER -->
    <div class="header">
        <div class="badge">Rapport Mensuel - Pilotage B2B</div>
        <h1>MG & BATAM - Conventions</h1>
        <div class="sub">
            {mois_nom} {a} &nbsp;|&nbsp; 
            Genere le {jours_data} &nbsp;|&nbsp;
            Source : Business Central VC
        </div>
    </div>

    <!-- SYNTHÈSE IA -->
    {ia_synthese}

    <!-- 1. PERFORMANCE GLOBALE -->
    <div class="section">
        <div class="section-title">[chart] Performance Globale - Synthese</div>
        <table>
            <thead>
                <tr>
                    <th>Indicateur</th>
                    <th class="num">{mois_court} {a}</th>
                    <th class="num">{mois_court} {a-1}</th>
                    <th class="num">Variation</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>CA TTC conventions</td>
                    <td class="num">{ca_conv_s} TND</td>
                    <td class="num">{ca_conv_n1_s} TND</td>
                    <td class="num">{evol_conv_h}</td>
                </tr>
                <tr>
                    <td>CA TTC EDC</td>
                    <td class="num">{ca_edc_s} TND</td>
                    <td class="num">{ca_edc_n1_s} TND</td>
                    <td class="num">{evol_edc_h}</td>
                </tr>
                <tr style="font-weight:700; background:#F8FAFC;">
                    <td>CA TOTAL COMBINÉ</td>
                    <td class="num">{ca_total_s} TND</td>
                    <td class="num">{ca_total_n1_s} TND</td>
                    <td class="num">{evol_total_h}</td>
                </tr>
                <tr>
                    <td>Nombre de dossiers conventions</td>
                    <td class="num">{data['nb_conv']}</td>
                    <td class="num">{data['nb_conv_n1']}</td>
                    <td class="num">{evol_nb_h}</td>
                </tr>
                <tr>
                    <td>Nombre de dossiers EDC</td>
                    <td class="num">{data['nb_edc']}</td>
                    <td class="num">{data['nb_edc_n1']}</td>
                    <td class="num">{evol_nb_edc_h}</td>
                </tr>
                <tr>
                    <td>Panier moyen conventions</td>
                    <td class="num">{data['panier_conv']:.0f} TND</td>
                    <td class="num">{data['panier_conv_n1']:.0f} TND</td>
                    <td class="num">{evol_panier_h}</td>
                </tr>
                <tr>
                    <td>Panier moyen EDC</td>
                    <td class="num">{data['panier_edc']:.0f} TND</td>
                    <td class="num">{data['panier_edc_n1']:.0f} TND</td>
                    <td class="num">{evol_panier_edc_h}</td>
                </tr>
                <tr>
                    <td>Conventions actives</td>
                    <td class="num">{data['conv_actives']}</td>
                    <td class="num">{data['conv_actives_n1']}</td>
                    <td class="num">{data['var_actives']}</td>
                </tr>
                <tr>
                    <td>Magasins contributeurs</td>
                    <td class="num">{data['mag_contributeurs']}</td>
                    <td class="num">{data['mag_contributeurs_n1']}</td>
                    <td class="num">{data['var_magasins']}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- TOP / FLOP -->
    <div class="section">
        <table width="100%"><tr>
        <td width="48%" style="vertical-align:top;">
            <div class="section-title" style="border-bottom-color:#059669;">▲ Top 5 Conventions</div>
            <table>
                <thead>
                    <tr><th>#</th><th>Convention</th><th class="num">CA</th></tr>
                </thead>
                <tbody>{top_rows}</tbody>
            </table>
        </td>
        <td width="4%"></td>
        <td width="48%" style="vertical-align:top;">
            <div class="section-title" style="border-bottom-color:#DC2626;">▼ Flop 5 - Baisse</div>
            <table>
                <thead>
                    <tr><th>#</th><th>Convention</th><th class="num">Évolution</th></tr>
                </thead>
                <tbody>{flop_rows}</tbody>
            </table>
        </td>
        </tr></table>
    </div>

    <!-- 2. ANALYSE PAR CONVENTION (IA) -->
    <div class="section">
        <div class="section-title">[hospital] Analyse par Convention - Diagnostic IA</div>
        {ia_conventions_html if ia_conventions_html else '<p style="color:#94A3B8;font-size:13px;">Analyse IA non disponible (cle API non configuree).</p>'}
    </div>

    <!-- 3. ANALYSE PAR MAGASIN -->
    <div class="section">
        <div class="section-title">[shop] Analyse par Magasin</div>
        <table>
            <thead>
                <tr>
                    <th>Magasin</th>
                    <th class="num">{mois_court} {a}</th>
                    <th class="num">{mois_court} {a-1}</th>
                    <th class="num">Évolution</th>
                </tr>
            </thead>
            <tbody>{mag_rows}</tbody>
        </table>
    </div>

    <!-- 4. EDC -->
    <div class="section">
        <div class="section-title">[books] Convention EDC - Éducation Nationale</div>
        <table>
            <thead>
                <tr>
                    <th>Indicateur</th>
                    <th class="num">{mois_court} {a}</th>
                    <th class="num">{mois_court} {a-1}</th>
                    <th class="num">Variation</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td>CA TTC EDC</td>
                    <td class="num">{ca_edc_s} TND</td>
                    <td class="num">{ca_edc_n1_s} TND</td>
                    <td class="num">{evol_edc_h}</td>
                </tr>
                <tr>
                    <td>Nombre de dossiers</td>
                    <td class="num">{data['nb_edc']}</td>
                    <td class="num">{data['nb_edc_n1']}</td>
                    <td class="num">{evol_nb_edc_h}</td>
                </tr>
                <tr>
                    <td>Panier moyen</td>
                    <td class="num">{data['panier_edc']:.0f} TND</td>
                    <td class="num">{data['panier_edc_n1']:.0f} TND</td>
                    <td class="num">{evol_panier_edc_h}</td>
                </tr>
            </tbody>
        </table>
    </div>

    <!-- 5. PRIORITÉS IA -->
    {ia_priorites_html}

    <!-- 6. CONCLUSION IA -->
    {ia_conclusion_html}

    <!-- TEXT COPY VERSION (hidden but selectable) -->
    <div class="section" style="border-bottom:1px solid #E2E8F0;border-radius:0;">
        <div class="section-title">[clip] Version Texte (copier/coller)</div>
        <pre style="font-size:11px;line-height:1.6;color:#334155;white-space:pre-wrap;font-family:monospace;background:#F8FAFC;padding:16px;border-radius:8px;border:1px solid #E2E8F0;">
{generer_texte(data, analyse_ia)}
        </pre>
    </div>

    <!-- FOOTER -->
    <div class="footer">
        <div class="footer-left">
            <div style="font-weight:600;margin-bottom:3px;">MG & BATAM - Groupe SMG</div>
            <div style="font-size:11px;color:#64748B;">Source : VC.CONV. Business Central</div>
        </div>
        <div class="footer-right">
            Rapport automatique<br>
            Pilotage Grands Comptes
        </div>
    </div>

</div>
</body>
</html>"""


# ─── Version texte copiable ────────────────────────────────────

def generer_texte(data: dict, analyse_ia: dict | None = None) -> str:
    """Genere la version texte brut copiable."""
    m = data["mois"]
    a = data["annee"]
    mois_nom = MOIS_NOMS.get(m, str(m)).upper()

    lignes = []
    lignes.append(f"RAPPORT MENSUEL - {mois_nom} {a}".center(70))
    lignes.append(f"MG & BATAM - Pilotage Conventions B2B".center(70))
    lignes.append("=" * 70)
    lignes.append("")

    # Texte IA
    if analyse_ia:
        sg = analyse_ia.get("synthese_globale")
        lignes.append(str(sg) if sg else "")
        lignes.append("")

    # Synthese
    lignes.append("1. PERFORMANCE GLOBALE - SYNTHÈSE")
    lignes.append("-" * 70)
    lignes.append(f"{'Indicateur':<40} {mois_nom} {a:<12} {mois_nom} {a-1:<12} Variation")
    lignes.append("-" * 70)
    lignes.append(f"{'CA TTC conventions':<40} {format_k(data['ca_conv']):>8} TND  {format_k(data['ca_conv_n1']):>8} TND  {data['var_conv']:>+.1f}%")
    lignes.append(f"{'CA TTC EDC':<40} {format_k(data['ca_edc']):>8} TND  {format_k(data['ca_edc_n1']):>8} TND  {data['var_edc']:>+.1f}%")
    lignes.append(f"{'CA TOTAL COMBINÉ':<40} {format_k(data['ca_total']):>8} TND  {format_k(data['ca_total_n1']):>8} TND  {data['var_total']:>+.1f}%")
    lignes.append(f"{'Nombre de dossiers':<40} {data['nb_conv']:>8}     {data['nb_conv_n1']:>8}     {data['var_nb_conv']:>+.1f}%")
    lignes.append(f"{'Panier moyen':<40} {data['panier_conv']:>8.0f} TND  {data['panier_conv_n1']:>8.0f} TND  {data['var_panier']:>+.1f}%")
    lignes.append(f"{'Conventions actives':<40} {data['conv_actives']:>8}     {data['conv_actives_n1']:>8}     {data['var_actives']}")
    lignes.append(f"{'Magasins contributeurs':<40} {data['mag_contributeurs']:>8}     {data['mag_contributeurs_n1']:>8}     {data['var_magasins']}")
    lignes.append("")

    # Top/Flop
    lignes.append("▶ TOP 5 CONVENTIONS")
    for i, (nom, ca) in enumerate(data["top_convs"], 1):
        lignes.append(f"  {i}. {nom:<35} {format_k(ca):>8} TND")
    lignes.append("")

    lignes.append("▶ FLOP 5 - BAISSES")
    for i, f in enumerate(data["flop_convs"], 1):
        lignes.append(f"  {i}. {f[0]:<35} {f[1]:>+.1f}%")
    lignes.append("")

    # Analyse par convention (tableau compact)
    lignes.append("2. ANALYSE PAR CONVENTION")
    lignes.append("-" * 70)
    lignes.append(f"{'Convention':<35} {mois_nom} {a:<12} {mois_nom} {a-1:<12} Evol")
    lignes.append("-" * 70)
    for c in data["conventions"]:
        ev = c["evolution_pct"]
        arrow = "+" if ev >= 0 else "-"
        lignes.append(f"{c['nom']:<35} {format_k(c['ca_mois']):>8} TND  {format_k(c['ca_mois_n1']):>8} TND  {arrow}{abs(ev):>7.1f}%")
    lignes.append("")

    # Commentaires IA condenses (conventions signalees uniquement)
    if analyse_ia and analyse_ia.get("conventions"):
        alertes = [c for c in analyse_ia["conventions"] if c.get("signal") == "red" and c.get("commentaire")]
        if alertes:
            lignes.append("  [!] ALERTES IA - Conventions en baisse")
            for c in alertes[:5]:
                com = c["commentaire"][:120]
                lignes.append(f"      {c['nom']}: {com}")
            lignes.append("")

    # Magasins
    lignes.append("3. ANALYSE PAR MAGASIN (Top 15)")
    lignes.append("-" * 70)
    lignes.append(f"{'Magasin':<30} {mois_nom} {a:<12} {mois_nom} {a-1:<12} Évolution")
    lignes.append("-" * 70)
    for m in data["magasins"][:15]:
        lignes.append(f"{m['magasin']:<30} {format_k(m['ca_mois']):>8} TND  {format_k(m['ca_mois_n1']):>8} TND  {m['evolution_pct']:>+.1f}%")
    lignes.append("")

    # EDC
    lignes.append("4. CONVENTION EDC - ÉDUCATION NATIONALE")
    lignes.append("-" * 70)
    lignes.append(f"  CA EDC          : {format_k(data['ca_edc']):>8} TND ({data['var_edc']:>+.1f}% vs N-1)")
    lignes.append(f"  Nb dossiers     : {data['nb_edc']:>8} ({data['var_nb_edc']:>+.1f}% vs N-1)")
    lignes.append(f"  Panier moyen    : {data['panier_edc']:>8.0f} TND")
    lignes.append("")

    # Priorites IA
    if analyse_ia and analyse_ia.get("priorites"):
        lignes.append("5. PRIORITÉS D'ACTION")
        lignes.append("-" * 70)
        for p in analyse_ia["priorites"]:
            lignes.append(f"  {p}")
        lignes.append("")

    # Conclusion IA
    if analyse_ia and analyse_ia.get("conclusion"):
        lignes.append("6. CONCLUSION")
        lignes.append("-" * 70)
        lignes.append(f"  {analyse_ia['conclusion']}")
        lignes.append("")

    # Footer
    lignes.append("=" * 70)
    lignes.append(f"Genere le {datetime.now().strftime('%d/%m/%Y a %H:%M')}")
    lignes.append("Pilotage Grands Comptes - SMG")
    lignes.append("")

    return "\n".join(lignes)


# ─── Email ─────────────────────────────────────────────────────

def send_email(subject: str, html_body: str, text_body: str | None = None):
    """Envoie l'email via SMTP SMG."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = EMAIL_FROM
        msg['To'] = ', '.join(EMAIL_TO)
        msg.attach(MIMEText(text_body or "Voir piece jointe HTML", 'plain'))
        msg.attach(MIMEText(html_body, 'html'))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())

        print("  ✓ Email envoye avec succes!")
        return True
    except Exception as e:
        print(f"  ⚠️  Erreur envoi email: {e}")
        return False


# ─── Presse-papiers Windows ────────────────────────────────────

def copy_to_clipboard(text: str):
    """Copie le texte dans le presse-papiers Windows."""
    try:
        escaped = text.replace("'", "''")
        ps_cmd = f"Set-Clipboard -Value '{escaped}'"
        subprocess.run(
            ["powershell", "-command", ps_cmd],
            check=True, capture_output=True, timeout=5
        )
        print("  ✓ Copie dans le presse-papiers !")
        return True
    except Exception as e:
        print(f"  ⚠️  Impossible de copier dans le presse-papiers: {e}")
        return False


# ─── Main ──────────────────────────────────────────────────────

def _truncate_n1_date_to_date(df: pd.DataFrame, annee: int, mois: int) -> pd.DataFrame:
    """
    Tronque N-1 au meme nombre de jours que N pour une comparaison equitable.
    Ex: si Juillet 2026 a des donnees jusqu'au jour 7, on ne garde que les 7 premiers jours de Juillet 2025.
    """
    if df.empty or "Jour" not in df.columns or "Annee" not in df.columns:
        return df
    max_jour_n = df[(df["Annee"] == annee) & (df["Mois"] == mois)]["Jour"].max()
    if pd.isna(max_jour_n):
        return df
    # Ne pas tronquer si N a plus de jours que N-1 (cas normal en fin de mois)
    df_n1 = df[df["Annee"] == annee - 1]
    max_jour_n1 = df_n1[df_n1["Mois"] == mois]["Jour"].max()
    if pd.isna(max_jour_n1) or max_jour_n >= max_jour_n1:
        return df
    # Tronquer N-1 au meme nombre de jours que N
    mask_n1 = (df["Annee"] == annee - 1) & (df["Mois"] == mois) & (df["Jour"] > max_jour_n)
    return df[~mask_n1]


def analyse(annee: int, mois: int, with_ai: bool = True, with_email: bool = True, api_key: str | None = None):
    """Point d'entree principal."""
    mois_nom = MOIS_NOMS.get(mois, str(mois))
    annee_n1 = annee - 1

    print(f"\n{'='*60}")
    print(f"  RAPPORT MENSUEL - {mois_nom.upper()} {annee}")
    print(f"{'='*60}\n")

    SORTIE.mkdir(parents=True, exist_ok=True)

    # 1. Chargement donnees
    dfs = load_all_data()
    code_df = dfs.get("code_magasin", pd.DataFrame())
    df_vc = _map_magasins(_add_date_cols(dfs.get("vc", pd.DataFrame())), code_df)
    df_edc = _add_date_cols(dfs.get("vc_edc", pd.DataFrame()))

    if df_vc.empty and df_edc.empty:
        print("  ❌ Aucune donnee chargee. Abandon.")
        return

    # ── Troncature date-à-date : si N a 7 jours, N-1 n'est compare que sur 7 jours ──
    df_vc_d2d = _truncate_n1_date_to_date(df_vc, annee, mois)
    df_edc_d2d = _truncate_n1_date_to_date(df_edc, annee, mois)

    # 2. Calcul KPIs
    print("\n  Calcul des indicateurs...")
    data = {
        "mois": mois,
        "annee": annee,
        "annee_n1": annee_n1,
        "mois_nom": mois_nom,
    }

    # Conventions (date-à-date)
    data["ca_conv"] = ca_periode(df_vc_d2d, annee, mois)
    data["ca_conv_n1"] = ca_periode(df_vc_d2d, annee_n1, mois)
    data["var_conv"] = evol_pct(data["ca_conv"], data["ca_conv_n1"])
    data["nb_conv"] = nb_dossiers(df_vc_d2d, annee, mois)
    data["nb_conv_n1"] = nb_dossiers(df_vc_d2d, annee_n1, mois)
    data["var_nb_conv"] = evol_pct(data["nb_conv"], data["nb_conv_n1"])
    data["panier_conv"] = panier_moyen(df_vc_d2d, annee, mois)
    data["panier_conv_n1"] = panier_moyen(df_vc_d2d, annee_n1, mois)
    data["var_panier"] = evol_pct(data["panier_conv"], data["panier_conv_n1"])

    # EDC (date-à-date)
    data["ca_edc"] = ca_periode(df_edc_d2d, annee, mois)
    data["ca_edc_n1"] = ca_periode(df_edc_d2d, annee_n1, mois)
    data["var_edc"] = evol_pct(data["ca_edc"], data["ca_edc_n1"])
    data["nb_edc"] = nb_dossiers(df_edc_d2d, annee, mois)
    data["nb_edc_n1"] = nb_dossiers(df_edc_d2d, annee_n1, mois)
    data["var_nb_edc"] = evol_pct(data["nb_edc"], data["nb_edc_n1"])
    data["panier_edc"] = panier_moyen(df_edc_d2d, annee, mois)
    data["panier_edc_n1"] = panier_moyen(df_edc_d2d, annee_n1, mois)
    data["var_panier_edc"] = evol_pct(data["panier_edc"], data["panier_edc_n1"])

    # Total
    data["ca_total"] = data["ca_conv"] + data["ca_edc"]
    data["ca_total_n1"] = data["ca_conv_n1"] + data["ca_edc_n1"]
    data["var_total"] = evol_pct(data["ca_total"], data["ca_total_n1"])

    # Metriques derivees (date-à-date aussi)
    data["conv_actives"] = conventions_actives(df_vc_d2d, annee, mois)
    data["conv_actives_n1"] = conventions_actives(df_vc_d2d, annee_n1, mois)
    data["var_actives"] = f"{data['conv_actives'] - data['conv_actives_n1']:+}"
    data["mag_contributeurs"] = magasins_contributeurs(df_vc_d2d, annee, mois)
    data["mag_contributeurs_n1"] = magasins_contributeurs(df_vc_d2d, annee_n1, mois)
    data["var_magasins"] = f"{data['mag_contributeurs'] - data['mag_contributeurs_n1']:+}"

    data["top_convs"] = top_conventions(df_vc_d2d, annee, mois, 5)
    data["flop_convs"] = flop_conventions(df_vc_d2d, annee, mois, annee_n1, mois, 5)
    data["conventions"] = analyse_par_convention(df_vc_d2d, annee, mois, annee_n1)
    data["magasins"] = analyse_par_magasin(df_vc_d2d, annee, mois, annee_n1)

    # Print KPIs
    print(f"  CA Conventions   : {format_k(data['ca_conv']):>8} TND ({data['var_conv']:>+.1f}%)")
    print(f"  CA EDC           : {format_k(data['ca_edc']):>8} TND ({data['var_edc']:>+.1f}%)")
    print(f"  CA Total         : {format_k(data['ca_total']):>8} TND ({data['var_total']:>+.1f}%)")
    print(f"  Conventions      : {data['conv_actives']} actives / {data['mag_contributeurs']} magasins")
    print(f"  Top 1            : {data['top_convs'][0][0] if data['top_convs'] else 'N/A'} ({format_k(data['top_convs'][0][1])} TND)")

    # 3. Analyse IA
    analyse_ia = None
    if with_ai:
        print("\n  Analyse IA...")
        data["_df_vc"] = df_vc_d2d  # DataFrame tronqué date-à-date pour les tendances
        prompt = build_llm_prompt(data)
        print(f"      Prompt: {len(prompt)} chars")
        response = call_llm(prompt, api_key=api_key)
        if response:
            try:
                raw = json.loads(response)
                # Normaliser les noms de champs (l'IA peut varier)
                analyse_ia = _normalize_ia_response(raw)
                nb_conv_ia = len(analyse_ia.get("conventions") or [])
                print(f"  ✓ Analyse IA recue: {nb_conv_ia} conventions analysees")
                if nb_conv_ia == 0:
                    dbg = SORTIE / f"ia_debug_{annee}_{mois}.json"
                    dbg.write_text(json.dumps(raw, indent=2, ensure_ascii=False), encoding='utf-8')
                    print(f"      Reponse sauvegardee: {dbg}")
            except json.JSONDecodeError as e:
                print(f"  ⚠️  Reponse IA invalide (JSON): {e}")
                # Sauvegarder la reponse brute pour debogage
                debug_file = SORTIE / f"ia_response_{annee}_{mois}.txt"
                debug_file.write_text(response)
                print(f"      Reponse brute sauvegardee: {debug_file}")
        else:
            print("  ⚠️  Analyse IA non disponible (pas de cle API)")

    # 4. Generation rapport
    print("\n  Generation du rapport...")
    html = generer_html(data, analyse_ia)
    texte = generer_texte(data, analyse_ia)

    # 5. Sauvegarde
    fichier = SORTIE / f"rapport_mensuel_{annee}_{mois:02d}.html"
    fichier.write_text(html, encoding="utf-8")
    print(f"  ✓ Rapport sauvegarde: {fichier}")

    fichier_txt = SORTIE / f"rapport_mensuel_{annee}_{mois:02d}.txt"
    fichier_txt.write_text(texte, encoding="utf-8")
    print(f"  ✓ Version texte: {fichier_txt}")

    # 6. Presse-papiers
    print("\n  Copie dans le presse-papiers...")
    copy_to_clipboard(texte)

    # 7. Email
    if with_email:
        print("\n  Envoi email...")
        subject = f"Rapport Mensuel Pilotage Conventions - {mois_nom} {annee}"
        send_email(subject, html, texte)
    else:
        print("\n  ⏭️  Envoi email desactive (--no-email)")

    print(f"\n{'='*60}")
    print(f"  TERMINÉ - Rapport {mois_nom} {annee}")
    print(f"  Fichier: {fichier}")
    print(f"  Texte copie dans le presse-papiers ✅")
    print(f"{'='*60}\n")

    return html, texte, analyse_ia


def main():
    parser = argparse.ArgumentParser(
        description="Rapport Mensuel B2B - SMG (MG & BATAM)"
    )
    parser.add_argument("--month", type=int, default=None,
                        help="Mois (1-12, defaut: mois precedent)")
    parser.add_argument("--year", type=int, default=None,
                        help="Annee (defaut: annee courante)")
    parser.add_argument("--no-email", action="store_true",
                        help="Desactiver l'envoi email")
    parser.add_argument("--no-ai", action="store_true",
                        help="Desactiver l'analyse IA")
    parser.add_argument("--api-key", type=str, default=None,
                        help="Cle API LLM (alternative a LLM_API_KEY env)")
    args = parser.parse_args()

    # Mois par defaut : mois precedent
    today = datetime.now()
    if args.month is None:
        mois = today.month - 1
        annee = today.year
        if mois == 0:
            mois = 12
            annee -= 1
    else:
        mois = args.month
        annee = args.year if args.year else today.year

    if mois < 1 or mois > 12:
        print("❌ Mois invalide (1-12)")
        sys.exit(1)

    analyse(annee, mois, with_ai=not args.no_ai, with_email=not args.no_email, api_key=args.api_key)


if __name__ == "__main__":
    main()
