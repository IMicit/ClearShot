@echo off
chcp 65001 >nul
taskkill /f /im ClearShot.exe >nul 2>&1
ping -n 2 127.0.0.1 >nul
del /q "%LOCALAPPDATA%\ClearShot\ClearShot.exe" >nul 2>&1
rmdir "%LOCALAPPDATA%\ClearShot" >nul 2>&1
powershell -NoProfile -Command "foreach($f in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('Programs'))){ Remove-Item ($f+'\ClearShot.lnk') -ErrorAction SilentlyContinue }; Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\ClearShot.exe' -Recurse -ErrorAction SilentlyContinue; Remove-Item 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ClearShot' -Recurse -ErrorAction SilentlyContinue"
echo ClearShot fue desinstalado. Tus capturas en Imagenes\ClearShot no se borraron.
pause
