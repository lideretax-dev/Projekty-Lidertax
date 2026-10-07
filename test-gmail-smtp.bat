@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Lidertax - test Gmail SMTP
echo ===============================================
echo.
echo Ten test wysyla jedna wiadomosc testowa na adres GMAIL_TEST_TO.
echo Nie pobiera danych z Bitrixa i nie wysyla nic do klientow.
echo.

"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\gmail_smtp_test.py

echo.
pause
