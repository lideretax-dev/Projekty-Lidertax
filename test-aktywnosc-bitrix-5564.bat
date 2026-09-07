@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Bitrix24 - test aktywnosci e-mail, kontakt 5564
echo ===============================================
echo.
echo Najpierw sprawdzam kontakt bez zmian w Bitrix24.
echo.

"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\bitrix_activity_test.py --contact-id 5564
if errorlevel 1 goto end

echo.
echo UWAGA: kolejny krok utworzy jedna TESTOWA aktywnosc e-mail w Bitrix24.
echo Nie wysyla masowo wiadomosci do klientow.
echo.
set /p CONFIRM=Wpisz TAK i nacisnij Enter, aby utworzyc testowa aktywnosc: 
if /I not "%CONFIRM%"=="TAK" (
  echo Pominieto tworzenie aktywnosci.
  goto end
)

echo.
"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\bitrix_activity_test.py --contact-id 5564 --create-activity

:end
echo.
pause
