@echo off
chcp 65001 >nul
taskkill /f /im ClearShot.exe >nul 2>&1
timeout /t 1 /nobreak >nul
del /q "%LOCALAPPDATA%\ClearShot\ClearShot.exe" >nul 2>&1
rmdir "%LOCALAPPDATA%\ClearShot" >nul 2>&1
powershell -NoProfile -Command "foreach($f in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('Programs'))){ Remove-Item ($f+'\ClearShot.lnk') -ErrorAction SilentlyContinue }"
echo ClearShot fue desinstalado. Tus capturas en Imagenes\ClearShot no se borraron.
pause
