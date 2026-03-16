@echo off
title SWG Vendor Manager

set SCRIPT_DIR=C:\Users\scott\OneDrive\Documents\SWGSales

echo =====================================
echo   SWG Vendor Manager
echo =====================================
echo.

echo [1/2] Processing mail files...
echo.
python "%SCRIPT_DIR%\process_mails.py"

echo.
echo.
echo [2/2] Launching dashboard...
echo      Opening browser at http://localhost:8501
echo      Press Ctrl+C in this window to stop the dashboard.
echo.
python -m streamlit run "%SCRIPT_DIR%\swg_dashboard.py"

pause