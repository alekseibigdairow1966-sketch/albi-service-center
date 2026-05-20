@echo off
echo ==========================================
echo  AUTO PUBLISH TO TELEGRAM
echo ==========================================
echo.
echo  Installing libraries...
pip install requests beautifulsoup4 --quiet 2>nul

echo  Running script...
echo.

python -u publish_all.py

echo.
echo  Check publish_log.txt for full details
pause
