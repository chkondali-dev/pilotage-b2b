@echo off
rem Lance le dashboard Pilotage B2B (Streamlit) - port 8501
cd /d C:\Users\hachk\pilotage_b2b
python -m streamlit run app.py
if errorlevel 1 (
  echo.
  echo Le demarrage a echoue. Appuyez sur une touche pour fermer...
  pause >nul
)
