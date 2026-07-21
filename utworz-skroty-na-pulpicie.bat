@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Tworzenie skrotow raportow na pulpicie
echo ===============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$desktop=[Environment]::GetFolderPath('Desktop');" ^
  "$root=(Get-Location).Path;" ^
  "$shell=New-Object -ComObject WScript.Shell;" ^
  "$shortcut=$shell.CreateShortcut((Join-Path $desktop 'Raport urodzin dzienny.lnk'));" ^
  "$shortcut.TargetPath=(Join-Path $root 'raport-dzienny.bat');" ^
  "$shortcut.WorkingDirectory=$root;" ^
  "$shortcut.IconLocation='C:\Windows\System32\shell32.dll,44';" ^
  "$shortcut.Save();" ^
  "$shortcut=$shell.CreateShortcut((Join-Path $desktop 'Raport urodzin tygodniowy.lnk'));" ^
  "$shortcut.TargetPath=(Join-Path $root 'raport-tygodniowy.bat');" ^
  "$shortcut.WorkingDirectory=$root;" ^
  "$shortcut.IconLocation='C:\Windows\System32\shell32.dll,44';" ^
  "$shortcut.Save();"

echo Gotowe. Na pulpicie powinny byc teraz dwa skroty:
echo - Raport urodzin dzienny
echo - Raport urodzin tygodniowy
echo.
pause
