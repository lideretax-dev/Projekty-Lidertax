@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Bitrix24 - testowy eksport historii klienta
echo ===============================================
echo.
echo Tryb tylko do odczytu. Skrypt niczego nie zmienia w CRM.
echo.
echo Podaj ID kontaktow do testu, oddzielone przecinkami.
echo Przyklad: 5564,1234,2345
echo.
set /p CONTACT_IDS=ID kontaktow: 

if "%CONTACT_IDS%"=="" (
  echo Nie podano ID kontaktow.
  goto end
)

"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\bitrix_history_export.py --contact-id "%CONTACT_IDS%" --output-dir exports\bitrix-historia-test

:end
echo.
pause
