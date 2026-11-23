# ClearShot

Capturador de pantalla para Windows estilo Lightshot, **sin pérdida de calidad**. Captura a la resolución física real de tu pantalla, anota la imagen y la copia o guarda en PNG, todo con atajos de teclado y desde la bandeja del sistema.

<!-- Agrega aquí una captura de pantalla:
![ClearShot](docs/captura.png)
-->

## Características

- **Sin pérdida y máxima nitidez:** captura a resolución física real (DPI Awareness Per-Monitor V2 nativo de Windows) y guarda en PNG lossless. Renderizado tipográfico avanzado con subpixel hinting. Al copiar al portapapeles no se recomprime.
- **Atajo global:** `Impr Pant` o `Ctrl+Alt+S`, desde cualquier programa.
- **Carpeta de guardado fija:** el botón **Guardar** siempre va a la carpeta que elijas (por defecto `Imágenes\ClearShot`), sin diálogos innecesarios.
- **Anotaciones libres (estilo Lightshot):** dibuja con total libertad dentro o fuera de la selección (apuntes, flechas, etc.); al guardar o copiar, se exporta estrictamente el área seleccionada original.
- **Notificación clickeable:** al guardar, haz clic en la notificación de Windows para abrir la captura inmediatamente.
- **📌 Fijar en pantalla (*Pin to screen* — tecla `F`):** deja el recorte flotando siempre visible encima de cualquier ventana; muévelo arrastrando, haz zoom con la rueda del ratón o ajusta su opacidad con `Ctrl + rueda`.
- **🔤 Extraer texto con OCR nativo (tecla `O`):** reconoce y copia al portapapeles el texto dentro de la selección usando el motor OCR nativo de Windows, 100% offline y en menos de un segundo.
- **✨ Modo Fondo bonito (*Beautifier* — tecla `B` / `Shift+B`):** envuelve la captura en un marco de alta resolución con degradado moderno (5 temas incluidos), esquinas redondeadas y sombra suave.
- **Colores y grosor:** paleta rápida (teclas 1-9), selector personalizado y slider, botones `- / +` o rueda del ratón para el grosor.
- **Selección ajustable:** mueve y redimensiona con 8 tiradores, con una lupa 8x que muestra coordenadas y color HEX bajo el cursor.
- **Ligero:** vive en la bandeja del sistema e inicia con Windows. El atajo usa `RegisterHotKey` de Windows (sin hook de teclado), así que en reposo no consume CPU.

## Instalación (Windows)

1. Instala [Python 3.10 o superior](https://www.python.org/downloads/) y marca **"Add python.exe to PATH"**.
2. Descarga o clona este repositorio:
   ```bash
   git clone https://github.com/IMicit/ClearShot.git
   ```
3. Haz doble clic en **`instalar.bat`**.

El instalador instala las dependencias, compila `ClearShot.exe`, lo copia a `%LOCALAPPDATA%\ClearShot`, crea los accesos directos y lo deja corriendo. Verás el icono junto al reloj y se abrirá solo cada vez que inicies Windows.

Para actualizar, vuelve a ejecutar `instalar.bat`: reemplaza la copia anterior.

### Actualizar y sincronizar entre computadores (Notebook ↔ PC)

- **Para bajar las últimas actualizaciones desde GitHub** en cualquier equipo:
  ```bash
  git pull
  ```
  Luego haz doble clic en **`instalar.bat`** para recompilar y actualizar el `ClearShot.exe` instalado en Windows.

- **Para subir cambios nuevos a GitHub** después de editar el código:
  ```bash
  git add .
  git commit -m "Descripción de los cambios"
  git push
  ```

- **Si descargaste el proyecto como `.zip`** (`ClearShot-main`) y quieres conectarlo a Git sin borrar la carpeta:
  ```bash
  git init
  git remote add origin https://github.com/IMicit/ClearShot.git
  git fetch origin
  git checkout -B main origin/main
  ```

### Ejecutar sin instalar

```bash
pip install -r requirements.txt
python clearshot.py
```

## Uso

1. Pulsa **`Impr Pant`** (o `Ctrl+Alt+S`, o haz clic en el icono de la bandeja).
2. Arrastra para seleccionar el área.
3. Anota si quieres, usando la barra de herramientas.
4. **Copiar** (`Enter`) o **Guardar** (`Ctrl+S`).

### Carpeta de guardado

Por defecto las capturas van a `Imágenes\ClearShot` con el nombre `captura_AAAA-MM-DD_HH-MM-SS.png`.

Para cambiarla, usa el icono de carpeta de la barra de herramientas o el menú de la bandeja → **Cambiar carpeta de capturas…**. Queda guardada hasta que la cambies de nuevo.

Si necesitas elegir nombre, carpeta o formato (PNG, JPG, BMP) solo para una captura, usa **`Ctrl+Shift+S`**.

## Atajos

### Herramientas

| Tecla | Herramienta |
|:---:|---|
| `V` | Área (seleccionar / mover) |
| `P` | Lápiz |
| `L` | Línea |
| `A` | Flecha |
| `R` | Rectángulo |
| `E` | Elipse |
| `H` | Resaltador |
| `T` | Texto |
| `N` | Número de paso |
| `M` | Pixelar (ocultar datos) |

### Acciones

| Atajo | Acción |
|---|---|
| `Enter` / `Ctrl+C` | Copiar al portapapeles |
| `Ctrl+S` | Guardar en la carpeta configurada |
| `Ctrl+Shift+C` | Guardar en carpeta **y** copiar al portapapeles a la vez |
| `Ctrl+Shift+S` | Guardar como… (elegir carpeta/formato) |
| `F` | **Fijar captura flotante en pantalla** (*Pin to screen*) |
| `O` | **Extraer texto de la imagen al portapapeles** (OCR offline) |
| `B` / `Shift+B` | Activar **Modo Fondo bonito** / Cambiar entre los 5 degradados |
| `Ctrl+Z` | Deshacer |
| `Ctrl+Shift+Z` / `Ctrl+Y` | Rehacer |
| `1` a `9` | Elegir color de la paleta |
| `-` / `+` o rueda del ratón | Cambiar grosor |
| `Shift` al dibujar | Líneas rectas / formas cuadradas |
| Clic derecho | Descartar la selección |
| `Esc` | Cancelar |

## Solución de problemas

**`Impr Pant` abre también el recortes de Windows.**
En Windows 11 ve a *Configuración → Accesibilidad → Teclado* y desactiva *"Usar el botón Impr Pant para abrir el recorte de pantalla"*. También puedes usar `Ctrl+Alt+S`.

**No funciona el atajo global.**
En Windows, ClearShot registra los atajos con `RegisterHotKey`. Si otro programa (Greenshot, ShareX, Lightshot, Recortes…) ya usa `Impr Pant`, verás un aviso al iniciar: cierra ese programa o usa `Ctrl+Alt+S`. En macOS/Linux se usa `pynput` (`pip install pynput`).

**Python no se encuentra al ejecutar `instalar.bat`.**
Reinstala Python marcando **"Add python.exe to PATH"** y vuelve a ejecutar el archivo.

**No se abre una segunda copia.**
Es intencional: ClearShot permite una sola instancia a la vez para no duplicar el atajo global.

## Limitaciones

- Con varios monitores, captura solo el monitor donde está el cursor.
- Las anotaciones no se mueven con el área si la desplazas después de dibujar.
- El texto es de una sola línea.

## Desarrollo

- **Stack:** Python + PyQt6. Todo el código está en `clearshot.py`. Atajos globales con `RegisterHotKey` (Windows) o `pynput` (otros sistemas).
- **Rendimiento:** el overlay repinta solo la zona que cambia (lupa, trazo en curso o selección), con el fondo oscurecido y las anotaciones terminadas precalculadas en caché.
- **Compilación:** `instalar.bat` usa PyInstaller en modo `--onedir` (arranque rápido, sin descomprimir a una carpeta temporal en cada inicio).
- **Configuración:** se guarda con `QSettings` (en Windows, en el registro bajo `HKCU\Software\ClearShot`).
- Para generar el icono: `python clearshot.py --make-icon icon.ico`.

## Licencia

Indica aquí la licencia elegida (por ejemplo, MIT).
