"""
MG Convention Suite — Dashboard v2.0 (SMG / MG & BATAM).

Écran d'accueil : écran de bienvenue + 2 modules.
    - Dashboard        → app.py (dashboard pilotage habituel)
    - Contrat Lab      → pages/contrat_lab.py (simulateur de convention)

Lancement :
    streamlit run suite.py
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ui.components import inject_css

st.set_page_config(
    page_title="MG Convention Suite — SMG",
    layout="wide",
    page_icon="🏢",
    initial_sidebar_state="collapsed",
)

inject_css()

# CSS local : cartes de modules de la Suite
st.markdown("""
<style>
  .suite-hero {
    background: linear-gradient(135deg, #0a0f1e 0%, #7f1d1d 55%, #0d3d34 100%);
    border-radius: 22px; padding: 2.2rem 2.5rem; color: white;
    margin-bottom: 2rem; box-shadow: 0 16px 48px rgba(10,15,30,0.18);
    position: relative; overflow: hidden;
  }
  .suite-hero::before, .suite-hero::after {
    content:""; position:absolute; border-radius:50%; background: rgba(255,255,255,0.05);
  }
  .suite-hero::before { width:340px; height:340px; right:-90px; top:-90px; }
  .suite-hero::after  { width:200px; height:200px; left:45%; bottom:-70px; }
  .suite-tag {
    display:inline-block; padding:4px 14px; border-radius:99px;
    background:rgba(255,255,255,0.12); border:1px solid rgba(255,255,255,0.15);
    font-size:0.70rem; font-weight:800; letter-spacing:0.14em;
    text-transform:uppercase; margin-bottom:0.9rem;
  }
  .suite-hero h1 { font-size:2.1rem; font-weight:800; margin:0; }
  .suite-hero p  { font-size:0.95rem; color:rgba(255,255,255,0.75); margin:0.55rem 0 0; max-width:640px; }

  /* Cartes modules — clic sur toute la carte */
  a.suite-card-link {
    display:block; text-decoration:none; border-radius: 20px; height: 100%;
  }
  .suite-card {
    background: #fff; border: 1px solid #e2e8f0; border-radius: 20px;
    padding: 2.6rem 2rem; height: 100%;
    box-shadow: 0 8px 28px rgba(15,23,42,0.07);
    transition: transform .15s, box-shadow .2s, border-color .2s;
    position: relative; overflow: hidden;
  }
  .suite-card::after {
    content:""; position:absolute; width:240px; height:240px; border-radius:50%;
    top:-110px; right:-90px; opacity:0.14; pointer-events:none;
  }
  a.suite-card-link:hover .suite-card {
    transform: translateY(-4px); box-shadow: 0 20px 48px rgba(15,23,42,0.16);
  }
  a.suite-card-link:focus-visible .suite-card {
    outline: 3px solid #2563eb; outline-offset: 3px;
  }
  .suite-card .suite-title {
    font-size: 3rem; font-weight: 900; letter-spacing: -0.02em;
    line-height: 1.05; margin: 0.4rem 0 0.2rem;
  }
  .suite-card .suite-arrow {
    display:inline-flex; align-items:center; gap:8px;
    font-size:0.95rem; font-weight:800; margin-top:1.6rem;
    text-transform:uppercase; letter-spacing:0.12em;
  }
  .suite-card.blue  { background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 70%, #3b82f6 100%); }
  .suite-card.blue  .suite-title, .suite-card.blue .suite-arrow { color:#fff; }
  .suite-card.blue::after { background:#93c5fd; }
  .suite-card.rose  { background: linear-gradient(135deg, #7f1d1d 0%, #dc2626 70%, #ef4444 100%); }
  .suite-card.rose  .suite-title, .suite-card.rose .suite-arrow { color:#fff; }
  .suite-card.rose::after { background:#fca5a5; }
  .suite-foot { margin-top:2.4rem; text-align:center; color:#94a3b8; font-size:0.8rem; }
</style>
""", unsafe_allow_html=True)

# ── Écran de bienvenue ────────────────────────────────────────
st.markdown("""
<div class="suite-hero">
  <div class="suite-tag">SMG — MG & BATAM</div>
  <h1>MG Convention Suite</h1>
  <p>Portail unifié des conventions de vente à crédit B2B : pilotage de la
  performance et laboratoire de construction des dossiers de convention.</p>
</div>
""", unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    st.markdown("""
    <a class="suite-card-link" href="dashboard" aria-label="Ouvrir le Dashboard">
      <div class="suite-card blue">
        <div class="suite-title">Dashboard</div>
        <div class="suite-arrow">Ouvrir →</div>
      </div>
    </a>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <a class="suite-card-link" href="contrat_lab" aria-label="Ouvrir le Contrat Lab">
      <div class="suite-card rose">
        <div class="suite-title">Contrat Lab</div>
        <div class="suite-arrow">Ouvrir →</div>
      </div>
    </a>
    """, unsafe_allow_html=True)

st.markdown(
    '<div class="suite-foot">MG Convention Suite v0 — portail des conventions SMG · '
    'Dashboard pilotage + Contrat Lab</div>',
    unsafe_allow_html=True,
)
