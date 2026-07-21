@echo off
chcp 65001 >nul

echo.
echo ===============================================
echo  Wylaczanie autostartu raportu dziennego
echo ===============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$startup=[Environment]::GetFolderPath('Startup');" ^
  "$path=Join-Path $startup 'Raport urodzin dzienny - autostart.lnk';" ^
  "if (Test-Path $path) { Remove-Item -LiteralPath $path; Write-Host 'Usunieto skrot autostartu.' } else { Write-Host 'Nie znaleziono skrotu autostartu.' }"

echo.
pause
