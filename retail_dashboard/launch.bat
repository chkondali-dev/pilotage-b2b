@echo off
REM ============================================
REM Launch Retail Dashboard SMG
REM ============================================

cd /d "%~dp0"

echo.
echo ============================================
echo   Lancement Dashboard Retail SMG
echo ============================================
echo.

streamlit run app.py --server.port=8502 --server.address=localhost

pause