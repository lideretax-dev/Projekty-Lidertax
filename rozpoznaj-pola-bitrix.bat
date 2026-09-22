@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Bitrix24 - rozpoznanie pol kontaktu
echo ===============================================
echo.
echo Tryb tylko do odczytu. Skrypt niczego nie zmienia w CRM.
echo.

"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\bitrix_field_discovery.py --output-dir reports\bitrix24-audyt

echo.
pause
