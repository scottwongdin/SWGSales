@echo off
title SWG Vendor Manager [TEST]

set SCRIPT_DIR=C:\Users\scott\OneDrive\Documents\SWGSales

echo =====================================
echo   SWG Vendor Manager [TEST]
echo =====================================
echo.

echo Processing mail files against TEST database...
echo.
python "%SCRIPT_DIR%\process_mails.py" config_test

echo.
echo Done! Open swg_test.html in your browser to view reports.
echo Press any key to close this window.
pause