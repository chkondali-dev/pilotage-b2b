"""
Composants UI réutilisables — CSS, badges, cartes de classement.
"""
import streamlit as st
from data.config import C


def inject_css():
    """Injecte le CSS global du dashboard."""
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=Figtree:wght@400;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif; }}
    .stApp {{
        background:
            radial-gradient(ellipse at 0% 0%, rgba(29,78,216,0.08) 0%, transparent 40%),
            radial-gradient(ellipse at 100% 0%, rgba(5,150,105,0.08) 0%, transparent 40%),
            linear-gradient(180deg, #f0f4ff 0%, #f7fafc 55%, #eef7f5 100%);
    }}
    .block-container {{ padding: 1rem 2rem 3rem; max-width: 1400px; }}
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0a0f1e 0%, #0f2040 60%, #0d2e28 100%);
        border-right: 1px solid rgba(255,255,255,0.05);
    }}
    [data-testid="stSidebar"] * {{ color: #e2e8f0 !important; }}
    [data-testid="stSidebar"] label {{ color: #94a3b8 !important; font-size: 0.78rem !important; font-weight: 700 !important; text-transform: uppercase; letter-spacing: 0.05em; }}
    [data-testid="stSidebar"] .stButton>button {{
        background: linear-gradient(135deg, #14b8a6 0%, #0f766e 100%);
        border: none; border-radius: 10px; font-weight: 700;
        color: white !important; width: 100%; margin-top: 8px;
        padding: 0.5rem; transition: opacity .2s;
    }}
    [data-testid="stSidebar"] .stButton>button:hover {{ opacity: 0.88; }}
    [data-testid="stMetric"] {{
        background: rgba(255,255,255,0.92);
        border: 1px solid {C["border"]};
        border-radius: 16px;
        padding: 0.9rem 1.1rem;
        box-shadow: 0 2px 12px rgba(15,23,42,0.06);
        transition: box-shadow .2s;
    }}
    [data-testid="stMetric"]:hover {{ box-shadow: 0 6px 24px rgba(15,23,42,0.10); }}
    [data-testid="metric-container"] > div:first-child {{
        font-size: 0.72rem; font-weight: 700; color: {C["muted"]};
        text-transform: uppercase; letter-spacing: 0.07em;
    }}
    [data-testid="metric-container"] > div:nth-child(2) {{
        font-size: 1.6rem; font-weight: 800; color: {C["ink"]}; line-height: 1.1;
    }}
    div[data-testid="stPlotlyChart"] {{
        background: rgba(255,255,255,0.88);
        border: 1px solid {C["border"]};
        border-radius: 18px;
        padding: 0.3rem;
        box-shadow: 0 2px 14px rgba(15,23,42,0.05);
        transition: box-shadow .2s;
    }}
    div[data-testid="stPlotlyChart"]:hover {{ box-shadow: 0 8px 28px rgba(15,23,42,0.09); }}
    [data-testid="stExpander"] summary {{
        background: rgba(248,250,252,0.85);
        border-radius: 10px;
        border: 1px solid {C["border"]};
        padding: 0.5rem 1rem;
        font-weight: 600; font-size: 0.88rem; color: {C["ink"]};
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] {{
        background: rgba(255,255,255,0.10);
        border-radius: 12px;
        padding: 2px;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] summary {{
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.08);
        color: #f1f5f9 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] {{
        background: #f8fafc;
        border-radius: 0 0 10px 10px;
        padding: 8px 12px 4px;
        margin-top: -2px;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] * {{
        color: #1e293b !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] label {{
        color: #475569 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] [data-testid="stExpanderDetails"] .stCaption {{
        color: #64748b !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] div[data-baseweb="select"] > div {{
        background: white !important;
        border: 1px solid #cbd5e1 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stExpander"] div[data-baseweb="select"] * {{
        color: #1e293b !important;
    }}
    [data-testid="stTabs"] button[role="tab"] {{
        border-radius: 11px; padding: 0.45rem 0.9rem;
        font-weight: 600; font-size: 0.88rem;
        background: rgba(255,255,255,0.6);
        border: 1px solid rgba(148,163,184,0.18);
        margin-right: 4px; transition: all .15s;
    }}
    [data-testid="stTabs"] button[aria-selected="true"] {{
        background: linear-gradient(135deg, rgba(29,78,216,0.11) 0%, rgba(5,150,105,0.12) 100%);
        border-color: rgba(29,78,216,0.26);
        color: {C["ink"]} !important; font-weight: 700;
    }}
    .hero {{
        background: linear-gradient(135deg, #0a0f1e 0%, #1a3060 52%, #0d3d34 100%);
        border-radius: 22px; padding: 1.6rem 2rem;
        color: white; margin-bottom: 1.4rem;
        box-shadow: 0 16px 48px rgba(10,15,30,0.18);
        position: relative; overflow: hidden;
    }}
    .hero::before, .hero::after {{
        content:""; position:absolute; border-radius:50%;
        background: rgba(255,255,255,0.04);
    }}
    .hero::before {{ width:300px; height:300px; right:-80px; top:-80px; }}
    .hero::after  {{ width:180px; height:180px; left:40%; bottom:-60px; }}
    .hero-tag {{
        display:inline-block; padding:3px 12px; border-radius:99px;
        background:rgba(255,255,255,0.10); border:1px solid rgba(255,255,255,0.12);
        font-size:0.68rem; font-weight:800; letter-spacing:0.12em;
        text-transform:uppercase; margin-bottom:0.75rem;
    }}
    .hero-title {{ font-family:'Figtree',sans-serif; font-size:1.95rem; font-weight:800; margin:0; line-height:1.1; }}
    .hero-sub   {{ font-size:0.9rem; color:rgba(255,255,255,0.72); margin:0.5rem 0 0; max-width:680px; }}
    .hero-chips {{ display:flex; gap:8px; flex-wrap:wrap; margin-top:1rem; }}
    .hero-chip  {{
        padding:4px 12px; border-radius:99px;
        background:rgba(255,255,255,0.09); border:1px solid rgba(255,255,255,0.10);
        font-size:0.78rem; font-weight:500;
    }}
    .sec-hdr {{
        font-size:0.72rem; font-weight:800; color:{C["muted"]};
        text-transform:uppercase; letter-spacing:0.10em;
        margin:1.6rem 0 0.8rem; padding-bottom:5px;
        border-bottom:2px solid {C["border"]};
    }}
    .badge {{
        display:inline-flex; align-items:center; gap:5px;
        padding:4px 12px; border-radius:99px;
        font-weight:700; font-size:0.80rem;
    }}
    .b-red    {{ background:#fef2f2; color:#b91c1c; border:1px solid #fecaca; }}
    .b-amber  {{ background:#fffbeb; color:#92400e; border:1px solid #fde68a; }}
    .b-green  {{ background:#f0fdf4; color:#166534; border:1px solid #bbf7d0; }}
    .b-blue   {{ background:#eff6ff; color:#1e40af; border:1px solid #bfdbfe; }}
    .rank-card {{
        border-radius:14px; padding:11px 14px; margin-bottom:8px;
        transition: transform .15s;
    }}
    .rank-card:hover {{ transform: translateX(3px); }}
    .rank-top  {{ background:linear-gradient(135deg,#f0fdf4,#dcfce7); border:1px solid #86efac; }}
    .rank-flop {{ background:linear-gradient(135deg,#fff7ed,#ffedd5); border:1px solid #fdba74; }}
    .rank-num  {{ font-size:0.65rem; font-weight:800; margin-bottom:4px; }}
    .rank-name {{ font-weight:700; color:{C["ink"]}; font-size:0.88rem; line-height:1.2; }}
    .rank-val  {{ font-weight:800; font-size:1.05rem; margin-top:4px; }}
    .rank-top  .rank-num {{ color:#16a34a; }}
    .rank-top  .rank-val {{ color:#15803d; }}
    .rank-flop .rank-num {{ color:#ea580c; }}
    .rank-flop .rank-val {{ color:#c2410c; }}
    </style>
    """, unsafe_allow_html=True)


def hero(title: str, subtitle: str, chips: list):
    """Affiche la bannière hero en haut du dashboard."""
    chips_html = "".join(f"<span class='hero-chip'>{c}</span>" for c in chips)
    st.markdown(f"""
    <div class="hero">
      <div class="hero-tag">Pilotage Commercial B2B — SMG</div>
      <h1 class="hero-title">{title}</h1>
      <p class="hero-sub">{subtitle}</p>
      <div class="hero-chips">{chips_html}</div>
    </div>""", unsafe_allow_html=True)


def section(title: str):
    """Affiche un en-tête de section avec bordure."""
    st.markdown(f"<div class='sec-hdr'>{title}</div>", unsafe_allow_html=True)


def badge(text: str, tone: str = "blue"):
    """Badge coloré (red, amber, green, blue)."""
    cls = {"red": "b-red", "amber": "b-amber", "green": "b-green", "blue": "b-blue"}.get(tone, "b-blue")
    st.markdown(f"<span class='badge {cls}'>{text}</span>", unsafe_allow_html=True)


def rank_card(rank: int, name: str, value: str, variant: str = "top"):
    """Carte de classement Top ou Flop."""
    cls = "rank-top" if variant == "top" else "rank-flop"
    label = f"#{rank} TOP" if variant == "top" else f"#{rank} FLOP"
    st.markdown(f"""
    <div class="rank-card {cls}">
      <div class="rank-num">{label}</div>
      <div class="rank-name">{name}</div>
      <div class="rank-val">{value}</div>
    </div>""", unsafe_allow_html=True)
