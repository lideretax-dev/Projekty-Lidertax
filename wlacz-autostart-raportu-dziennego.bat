@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo.
echo ===============================================
echo  Wlaczanie autostartu raportu dziennego
echo ===============================================
echo.

powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$startup=[Environment]::GetFolderPath('Startup');" ^
  "$root=(Get-Location).Path;" ^
  "$shell=New-Object -ComObject WScript.Shell;" ^
  "$shortcut=$shell.CreateShortcut((Join-Path $startup 'Raport urodzin dzienny - autostart.lnk'));" ^
  "$shortcut.TargetPath=(Join-Path $root 'raport-dzienny.bat');" ^
  "$shortcut.WorkingDirectory=$root;" ^
  "$shortcut.IconLocation='C:\Windows\System32\shell32.dll,44';" ^
  "$shortcut.Save();"

echo Gotowe. Raport dzienny uruchomi sie automatycznie po zalogowaniu do Windows.
echo Laptop musi byc wlaczony, a uzytkownik zalogowany.
echo.
pause
