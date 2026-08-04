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
  .suite-card {
    background: rgba(255,255,255,0.95); border: 1px solid #e2e8f0; border-radius: 20px;
    padding: 1.8rem 1.8rem 1.4rem; height: 100%;
    box-shadow: 0 8px 28px rgba(15,23,42,0.07);
    transition: transform .15s, box-shadow .2s;
  }
  .suite-card:hover { transform: translateY(-3px); box-shadow: 0 16px 40px rgba(15,23,42,0.12); }
  .suite-icon {
    width:52px; height:52px; border-radius:14px; display:flex; align-items:center;
    justify-content:center; font-size:1.6rem; margin-bottom:1rem;
  }
  .suite-card h3 { font-size:1.15rem; font-weight:800; margin:0 0 0.3rem; color:#0f172a; }
  .suite-card .suite-desc { font-size:0.86rem; color:#64748b; line-height:1.55; margin-bottom:0.9rem; }
  .suite-chips { display:flex; gap:6px; flex-wrap:wrap; margin-bottom:1.2rem; }
  .suite-chip {
    padding:3px 10px; border-radius:99px; font-size:0.72rem; font-weight:700;
    background:#f1f5f9; border:1px solid #e2e8f0; color:#475569;
  }
  .suite-card .stLinkButton button {
    width:100%; border-radius:12px; font-weight:700; padding:0.65rem 1rem;
    border: 2px solid #dc2626; color: #dc2626; background: white;
    transition: all .15s;
  }
  .suite-card .stLinkButton button:hover {
    background:#dc2626; color:white; border-color:#dc2626;
  }
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
    <div class="suite-card">
      <div class="suite-icon" style="background:#eff6ff;">📊</div>
      <h3>Dashboard</h3>
      <div class="suite-desc">Pilotage commercial : CA MG & BATAM, tendances,
      conventions encours, magasins, EDC, risque et alertes — l'outil de
      décision direction habituel.</div>
      <div class="suite-chips">
        <span class="suite-chip">CA &amp; tendances</span>
        <span class="suite-chip">Conventions</span>
        <span class="suite-chip">Risque</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/dashboard.py", label="📊 Ouvrir le Dashboard")

with c2:
    st.markdown("""
    <div class="suite-card">
      <div class="suite-icon" style="background:#fef2f2;">🧪</div>
      <h3>Contrat Lab</h3>
      <div class="suite-desc">Laboratoire de conventions : simulateur de
      scénario client (fiche réflexion 5 étapes), template recommandé,
      garanties et niveau de risque avant rédaction.</div>
      <div class="suite-chips">
        <span class="suite-chip">Simulateur</span>
        <span class="suite-chip">7 scénarios</span>
        <span class="suite-chip">Risque</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.page_link("pages/contrat_lab.py", label="🧪 Ouvrir le Contrat Lab")

st.markdown(
    '<div class="suite-foot">MG Convention Suite v0 — portail des conventions SMG · '
    'Dashboard pilotage + Contrat Lab</div>',
    unsafe_allow_html=True,
)
