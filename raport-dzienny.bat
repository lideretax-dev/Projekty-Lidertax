@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Bitrix24 - raport urodzin na dzis
echo ===============================================
echo.

"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\bitrix_birthdays.py --show-pii --output-dir reports\bitrix24-urodziny

echo.
echo Raport zapisano w folderze:
echo %CD%\reports\bitrix24-urodziny
echo.
pause
