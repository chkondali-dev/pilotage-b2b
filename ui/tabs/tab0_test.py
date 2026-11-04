import streamlit as st

def render(ctx):
    st.title("TEST - Dashboard OK")
    st.write("La fonction render() fonctionne !")
    st.write(f"Année sélectionnée: {ctx.annee_sel if hasattr(ctx, 'annee_sel') else 'non défini'}")

# Minimum contexte pour test
class MockCtx:
    annee_sel = 2024
    df_vc_filt = None
    df_vc = None
    risk_mat = None
    objectif_m = 1000

render(MockCtx)