@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"
title Empaquetador de ClearShot para Microsoft Store (.msix)

echo =======================================================
echo   Empaquetador de ClearShot para Microsoft Store
echo   (Licencia LGPLv3 con PySide6 + Paquete .MSIX oficial)
echo =======================================================
echo.

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

echo En Microsoft Partner Center, abre tu app y ve a:
echo   Product management -^> Product identity
echo Ahi veras los 3 datos exactos que pide la tienda (presiona Enter para usar el valor entre corchetes):
echo.

set "ID_NAME=IMicit.ClearShot"
set "PUB_ID=CN=00000000-0000-0000-0000-000000000000"
set "PUB_DISP=IMicit"

set /p "IN_NAME=1) Package/Identity/Name [%ID_NAME%]: "
if not "%IN_NAME%"=="" set "ID_NAME=%IN_NAME%"

set /p "IN_PUB=2) Package/Identity/Publisher (CN=...) [%PUB_ID%]: "
if not "%IN_PUB%"=="" set "PUB_ID=%IN_PUB%"

set /p "IN_DISP=3) Package/Properties/PublisherDisplayName [%PUB_DISP%]: "
if not "%IN_DISP%"=="" set "PUB_DISP=%IN_DISP%"

%PY% -c "import json,pathlib,sys; p=pathlib.Path('store/partner_identity.json'); p.parent.mkdir(exist_ok=True); p.write_text(json.dumps({'identity_name':sys.argv[1],'publisher_id':sys.argv[2],'publisher_display':sys.argv[3]},indent=2),encoding='utf-8')" "%ID_NAME%" "%PUB_ID%" "%PUB_DISP%"

echo.
echo [1/3] Verificando PySide6-Essentials (LGPLv3 comercial) y PyInstaller...
%PY% -m pip install PySide6-Essentials pyinstaller
if errorlevel 1 goto error

echo.
echo [2/3] Compilando ClearShot.exe comercial (100%% LGPLv3, sin PyQt6)...
if exist icon.ico del /q icon.ico
%PY% clearshot.py --make-icon icon.ico
%PY% -m PyInstaller --noconsole --onedir --clean --noconfirm --name ClearShot --exclude-module PyQt6 --exclude-module pynput --icon icon.ico clearshot.py
if errorlevel 1 goto error

echo.
echo [3/3] Generando iconos, capturas HD y empaquetando store\ClearShot.msix...
%PY% store\preparar_store.py --pack
if errorlevel 1 goto error

echo.
echo =======================================================
echo  LISTO! Todo generado en la carpeta "store\":
echo    - Paquete para subir:  store\ClearShot.msix
echo    - Icono 300x300:       store\assets\StoreListing_300x300.png
echo    - 3 Capturas Full HD:  store\screenshots\*.png
echo =======================================================
goto fin

:error
echo.
echo Ocurrio un error durante el empaquetado.

:fin
echo.
pause
