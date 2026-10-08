@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Lidertax - proba urodzin: podglady tylko do pm@lidertax.co.uk
"C:\Users\kento\AppData\Local\hermes\hermes-agent\venv\Scripts\python.exe" projekty\bitrix24-urodziny\birthday_pilot.py --run
if errorlevel 1 (
  echo Proces wymaga sprawdzenia. Zobacz reports\bitrix24-urodziny\pilot\pilot.log
  pause
  exit /b 1
)
exit /b 0
