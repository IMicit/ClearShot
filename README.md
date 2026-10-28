# ClearShot

Capturador de pantalla para Windows estilo Lightshot, **sin pérdida de calidad**. Captura a la resolución física real de tu pantalla, anota la imagen y la copia o guarda en PNG, todo con atajos de teclado y desde la bandeja del sistema.

<!-- Agrega aquí una captura de pantalla:
![ClearShot](docs/captura.png)
-->

## Características

- **Sin pérdida:** captura a resolución física real (respeta el escalado de Windows) y guarda en PNG. Al copiar al portapapeles no se recomprime.
- **Atajo global:** `Impr Pant` o `Ctrl+Alt+S`, desde cualquier programa.
- **Carpeta de guardado fija:** el botón **Guardar** siempre va a la carpeta que elijas (por defecto `Imágenes\ClearShot`), sin diálogos.
- **Anotaciones:** lápiz, línea, flecha, rectángulo, elipse, resaltador, texto, números de paso y pixelado para ocultar datos sensibles.
- **Colores y grosor:** paleta a la vista, selector de color personalizado y slider de grosor.
- **Selección ajustable:** mueve y redimensiona el área con tiradores, con una lupa que muestra coordenadas y color bajo el cursor.
- **Ligero:** vive en la bandeja del sistema e inicia con Windows.

## Instalación (Windows)

1. Instala [Python 3.10 o superior](https://www.python.org/downloads/) y marca **"Add python.exe to PATH"**.
2. Descarga o clona este repositorio:
   ```bash
   git clone https://github.com/IMicit/ClearShot.git
   ```
3. Haz doble clic en **`instalar.bat`**.

El instalador instala las dependencias, compila `ClearShot.exe`, lo copia a `%LOCALAPPDATA%\ClearShot`, crea los accesos directos y lo deja corriendo. Verás el icono junto al reloj y se abrirá solo cada vez que inicies Windows.

Para actualizar, vuelve a ejecutar `instalar.bat`: reemplaza la copia anterior.

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
| `Ctrl+Shift+S` | Guardar como… |
| `Ctrl+Z` | Deshacer |
| `Ctrl+Shift+Z` / `Ctrl+Y` | Rehacer |
| `1` a `9` | Elegir color de la paleta |
| Rueda del ratón | Cambiar grosor |
| `Shift` al dibujar | Líneas rectas / formas cuadradas |
| Clic derecho | Descartar la selección |
| `Esc` | Cancelar |

## Solución de problemas

**`Impr Pant` abre también el recortes de Windows.**
En Windows 11 ve a *Configuración → Accesibilidad → Teclado* y desactiva *"Usar el botón Impr Pant para abrir el recorte de pantalla"*. También puedes usar `Ctrl+Alt+S`.

**No funciona el atajo global.**
Comprueba que `pynput` esté instalado (`pip install pynput`). Si otro programa usa el mismo atajo, usa el alternativo.

**Python no se encuentra al ejecutar `instalar.bat`.**
Reinstala Python marcando **"Add python.exe to PATH"** y vuelve a ejecutar el archivo.

**No se abre una segunda copia.**
Es intencional: ClearShot permite una sola instancia a la vez para no duplicar el atajo global.

## Limitaciones

- Con varios monitores, captura solo el monitor donde está el cursor.
- Las anotaciones no se mueven con el área si la desplazas después de dibujar.
- El texto es de una sola línea.

## Desarrollo

- **Stack:** Python + PyQt6 + pynput. Todo el código está en `clearshot.py`.
- **Configuración:** se guarda con `QSettings` (en Windows, en el registro bajo `HKCU\Software\ClearShot`).
- Para generar el icono: `python clearshot.py --make-icon icon.ico`.

## Licencia

Indica aquí la licencia elegida (por ejemplo, MIT).
