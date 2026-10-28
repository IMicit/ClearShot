@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Instalando ClearShot

echo ================================
echo   Instalador de ClearShot
echo ================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

%PY% --version >nul 2>&1
if errorlevel 1 (
  echo No se encontro Python. Instalalo desde https://www.python.org/downloads/
  echo y marca la casilla "Add python.exe to PATH". Luego vuelve a ejecutar este archivo.
  goto fin
)

echo [1/4] Instalando dependencias...
%PY% -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto error

echo.
echo [2/4] Creando el programa ClearShot.exe (puede tardar un minuto)...
if exist icon.ico del /q icon.ico
%PY% clearshot.py --make-icon icon.ico
set "ICONARG="
if exist icon.ico set "ICONARG=--icon icon.ico"
%PY% -m PyInstaller --noconsole --onefile --clean --noconfirm --name ClearShot %ICONARG% clearshot.py
if errorlevel 1 goto error

echo.
echo [3/4] Copiando a su ubicacion final...
set "DEST=%LOCALAPPDATA%\ClearShot"
if not exist "%DEST%" mkdir "%DEST%"
taskkill /f /im ClearShot.exe >nul 2>&1
timeout /t 1 /nobreak >nul
copy /y "dist\ClearShot.exe" "%DEST%\ClearShot.exe" >nul
if errorlevel 1 goto error

echo.
echo [4/4] Configurando inicio automatico con Windows...
powershell -NoProfile -Command "$w=New-Object -ComObject WScript.Shell; foreach($f in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('Programs'))){ $s=$w.CreateShortcut($f+'\ClearShot.lnk'); $s.TargetPath='%DEST%\ClearShot.exe'; $s.WorkingDirectory='%DEST%'; $s.IconLocation='%DEST%\ClearShot.exe,0'; $s.Save() }"
if errorlevel 1 goto error

start "" "%DEST%\ClearShot.exe"

echo.
echo ================================
echo  Listo! ClearShot ya esta corriendo
echo  (icono azul junto al reloj) y se
echo  abrira solo cada vez que inicies
echo  Windows. Atajo: Impr Pant
echo ================================
goto fin

:error
echo.
echo Ocurrio un error. Copia el mensaje de arriba y envialo para revisarlo.

:fin
echo.
pause
