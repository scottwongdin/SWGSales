@echo off
title SWG Vendor Manager

set SCRIPT_DIR=C:\Users\scott\OneDrive\Documents\SWGSales

echo =====================================
echo   SWG Vendor Manager
echo =====================================
echo.

echo [1/3] Processing mail files...
echo.
python "%SCRIPT_DIR%\process_mails.py"

echo.
echo [2/3] Starting Factory API...
start "Factory API" python "%SCRIPT_DIR%\factory_api.py"
timeout /t 2 /nobreak >nul

echo.
echo [3/3] Launching dashboard...
echo      Opening browser at http://localhost:8501
echo      Press Ctrl+C in this window to stop the dashboard.
echo.
python -m streamlit run "%SCRIPT_DIR%\swg_dashboard.py"

pause