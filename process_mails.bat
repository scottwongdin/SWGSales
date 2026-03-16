@echo off
title SWG Vendor Manager

set SCRIPT_DIR=C:\Users\scott\OneDrive\Documents\SWGSales

echo =====================================
echo   SWG Vendor Manager
echo =====================================
echo.

echo Processing mail files...
echo.
python "%SCRIPT_DIR%\process_mails.py"

echo.
echo Done! Open swg_dashboard.html in your browser to view reports.
echo Press any key to close this window.
pause