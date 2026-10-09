@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0ustaw-harmonogram-urodzin.ps1"
if errorlevel 1 (
  echo Nie zarejestrowano zadania. Przeczytaj blad powyzej.
) else (
  echo Harmonogram urodzin zostal wlaczony.
)
pause
