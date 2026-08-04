"""
Dashboard (habituel) — page de la MG Convention Suite.

Wrapper minimal : exécute app.py existant (dashboard pilotage B2B complet)
sans duplication. streamlit run suite.py → sidebar → Dashboard.
"""
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

runpy.run_path(str(ROOT / "app.py"), run_name="__main__")
