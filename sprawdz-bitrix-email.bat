@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Bitrix24 - sprawdzenie mozliwosci e-mail
echo ===============================================
echo.

"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\bitrix_email_check.py

echo.
pause
