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
%PY% -m PyInstaller --noconsole --onedir --clean --noconfirm --name ClearShot --exclude-module pynput %ICONARG% clearshot.py
if errorlevel 1 goto error

echo.
echo [3/4] Copiando a su ubicacion final...
set "DEST=%LOCALAPPDATA%\ClearShot"
taskkill /f /im ClearShot.exe >nul 2>&1
ping -n 2 127.0.0.1 >nul
if exist "%DEST%\_internal" rmdir /s /q "%DEST%\_internal"
if not exist "%DEST%" mkdir "%DEST%"
xcopy "dist\ClearShot\*" "%DEST%\" /E /I /Y /Q >nul
if errorlevel 1 goto error
if exist desinstalar.bat copy /y "desinstalar.bat" "%DEST%\desinstalar.bat" >nul
if errorlevel 1 goto error

echo.
echo [4/4] Configurando aplicacion e inicio con Windows...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$w=New-Object -ComObject WScript.Shell; foreach($f in @([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('Programs'))){ $s=$w.CreateShortcut($f+'\ClearShot.lnk'); $s.TargetPath='%DEST%\ClearShot.exe'; $s.WorkingDirectory='%DEST%'; $s.IconLocation='%DEST%\ClearShot.exe,0'; $s.Description='ClearShot - Capturador de pantalla sin perdida'; $s.Save() }; $ap='HKCU:\Software\Microsoft\Windows\CurrentVersion\App Paths\ClearShot.exe'; if(-not(Test-Path $ap)){New-Item $ap -Force|Out-Null}; Set-ItemProperty $ap '(Default)' '%DEST%\ClearShot.exe'; Set-ItemProperty $ap 'Path' '%DEST%'; $un='HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\ClearShot'; if(-not(Test-Path $un)){New-Item $un -Force|Out-Null}; Set-ItemProperty $un 'DisplayName' 'ClearShot'; Set-ItemProperty $un 'DisplayVersion' '1.1.0'; Set-ItemProperty $un 'Publisher' 'IMicit'; Set-ItemProperty $un 'DisplayIcon' '%DEST%\ClearShot.exe,0'; Set-ItemProperty $un 'InstallLocation' '%DEST%'; Set-ItemProperty $un 'UninstallString' '%DEST%\desinstalar.bat'; Set-ItemProperty $un 'NoModify' 1 -Type DWord; Set-ItemProperty $un 'NoRepair' 1 -Type DWord"
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
