# ClearShot: Handoff del proyecto

Capturador de pantalla para Windows estilo Lightshot, sin pérdida de calidad. Este documento resume el estado actual, las decisiones tomadas y lo que queda pendiente, para que cualquiera pueda retomar el trabajo.

---

## 1. Resumen

- **Qué es:** app de bandeja del sistema que captura la pantalla, permite anotar y copiar o guardar el resultado.
- **Stack:** Python 3 + PyQt6 (interfaz) + pynput (atajo global).
- **Calidad:** captura a resolución física real (respeta escalado HiDPI), guardado en PNG (lossless) y copia al portapapeles sin recomprimir.
- **Atajo global:** `Impr Pant` o `Ctrl+Alt+S`.
- **Plataforma objetivo:** Windows (el instalador es un `.bat` que genera un `.exe` con PyInstaller).

## 2. Archivos

| Archivo | Estado | Descripción |
|---|---|---|
| `clearshot.py` | **Modificado** | Aplicación completa (un solo archivo). |
| `requirements.txt` | Sin cambios | `PyQt6>=6.5`, `pynput>=1.7` |
| `instalar.bat` | Sin cambios | Instala dependencias, compila `ClearShot.exe`, lo copia a `%LOCALAPPDATA%\ClearShot` y crea accesos directos en Inicio y Programas. |

Para actualizar una instalación existente basta con volver a ejecutar `instalar.bat` (cierra la copia en ejecución y la reemplaza).

## 3. Pedido original y resultado

**Pedido:**
1. Poder elegir dónde se guardan las capturas, como en Lightshot.
2. Mejorar la interfaz de captura: más bonita e interactiva, con colores elegibles sin ir "clic por clic".

**Decisión de guardado (confirmada por el usuario):** la carpeta es **definitiva**. Guardar siempre va a la carpeta configurada, sin diálogo. Por defecto es `Imágenes\ClearShot`.

**Resultado:** ambos puntos implementados (detalle abajo).

## 4. Funcionalidad actual

### Guardado
- **Guardar** (botón o `Ctrl+S`): escribe un PNG directo en la carpeta configurada con el nombre `captura_AAAA-MM-DD_HH-MM-SS.png`.
- **Cambiar carpeta:** botón de carpeta en la barra o "Cambiar carpeta de capturas…" en el menú de la bandeja. Se persiste entre reinicios.
- **Carpeta por defecto:** `QStandardPaths.PicturesLocation / ClearShot` (respeta Imágenes redirigidas a OneDrive).
- **Fallo de carpeta:** si no se puede crear o escribir, se pide elegir otra en vez de fallar en silencio. Si el guardado falla, el overlay no se cierra para poder reintentar.
- **Guardar como…** (`Ctrl+Shift+S`): extra puntual (PNG, JPG o BMP), no cambia la carpeta definitiva.
- **Copiar** (botón, `Enter` o `Ctrl+C`): imagen al portapapeles.

### Selección
- Arrastrar para elegir el área; luego se puede **mover** (herramienta Área) o **redimensionar** con 8 tiradores.
- **Lupa** (8x) con coordenadas X/Y y color hexadecimal bajo el cursor mientras se selecciona o redimensiona.
- Etiqueta con dimensiones reales en píxeles físicos.
- Clic derecho: descarta la selección (o cierra si no hay ninguna).

### Herramientas y atajos

| Tecla | Herramienta |
|---|---|
| `V` | Área (seleccionar / mover) |
| `P` | Lápiz |
| `L` | Línea |
| `A` | Flecha |
| `R` | Rectángulo |
| `E` | Elipse |
| `H` | Resaltador |
| `T` | Texto |
| `N` | Número de paso (autoincremental) |
| `M` | Pixelar (ocultar datos) |

- **Colores:** 9 colores en la paleta (teclas `1` a `9`) + selector personalizado (círculo arcoíris, usa `QColorDialog`). El color personalizado se recuerda.
- **Grosor:** slider 1–20, rueda del ratón, con vista previa del color y grosor activos.
- **Shift:** al dibujar, líneas y flechas quedan rectas; rectángulo, elipse y pixelado quedan cuadrados.
- **Deshacer / rehacer:** `Ctrl+Z`, `Ctrl+Shift+Z` o `Ctrl+Y`.
- **Salir:** `Esc`. Dentro del campo de texto, `Esc` cancela solo el texto.

### Bandeja del sistema
Capturar, ver la carpeta actual, abrir la carpeta, cambiar la carpeta y salir. Clic en el icono = capturar. Al primer arranque muestra una notificación de bienvenida con la ruta de guardado.

## 5. Arquitectura de `clearshot.py`

| Bloque | Contenido |
|---|---|
| Configuración | `cfg()`, `get_save_dir()`, `set_save_dir()`, `pick_folder()`, `default_dir()` |
| Iconos | `draw_icon` / `make_icon` (logo) y `tool_icon` (iconos vectoriales de la barra) |
| Anotaciones | `draw_annotation()` + `_draw_mosaic()`. Una anotación es un `dict` con `tool`, `color`, `width` y datos propios (`points`, `p1`/`p2`, `pos`, `text`, `n`…). |
| Widgets | `Panel` (absorbe el ratón), `Swatch`, `Dot`, `TextEdit` |
| `Overlay` | Ventana a pantalla completa: selección, barra, dibujo, lupa, guardado. |
| `App` | Bandeja, atajos globales (pynput) y ciclo de vida del overlay. |

Puntos clave de diseño:
- `Overlay.pm` (QPixmap) se usa para mostrar; `Overlay.img` (QImage con DPR 1.0) se usa para recortar y pixelar en píxeles físicos.
- Las anotaciones se guardan en **coordenadas lógicas**. En `render_result()` el painter aplica `scale(dpr)` y `translate(-sel.x, -sel.y)` para renderizarlas a resolución nativa sobre el recorte.
- El pixelado lee los píxeles originales de `img`, por lo que oculta el contenido de verdad (no es un blur reversible).
- `Panel` acepta los eventos de ratón de la barra; sin eso, un clic en el fondo de la barra iniciaría una nueva selección.
- El atributo del grosor se llama `pen_w` (no `width`) para no pisar `QWidget.width()`.

### Persistencia (`QSettings("ClearShot", "ClearShot")`)
En Windows vive en el registro, `HKCU\Software\ClearShot\ClearShot`.

| Clave | Uso |
|---|---|
| `save_dir` | Carpeta definitiva de guardado (vacío = por defecto) |
| `color` | Último color usado |
| `width` | Último grosor usado |
| `custom_color` | Color personalizado elegido |
| `welcomed` | Notificación de bienvenida ya mostrada |

Bloqueo de instancia única: `QLockFile` en `%TEMP%\clearshot.lock`.

## 6. Pruebas realizadas

Se hizo una prueba automatizada en entorno **offscreen (Linux)** que simuló: selección, redimensionado por tirador, mover, las 7 herramientas de dibujo, número de paso, texto, deshacer y rehacer, cambio de color personalizado, render a resolución nativa y guardado en una carpeta personalizada. Todo pasó sin errores y se revisó visualmente el render de la interfaz.

**No probado todavía en Windows real:** atajo global con `Impr Pant`, comportamiento de foco al abrir el overlay, diálogos de carpeta y color sobre la ventana siempre-arriba, instalador y arranque con Windows. Se recomienda una pasada manual.

## 7. Limitaciones conocidas

- **Impr Pant en Windows 11:** el sistema puede abrir también su propia herramienta de recortes. Se desactiva en *Configuración → Accesibilidad → Teclado → "Usar el botón Impr Pant para abrir el recorte de pantalla"*. Alternativa: usar `Ctrl+Alt+S`.
- **Multi-monitor:** solo se captura el monitor bajo el cursor.
- Las anotaciones quedan fijas en pantalla: si mueves o redimensionas el área después de dibujar, no se mueven con ella (se recortan al nuevo área).
- El texto es de una sola línea.
- El resaltador no tiene modo de línea recta.
- Sin edición posterior de anotaciones ya colocadas (solo deshacer o rehacer).
- No hay opción de guardar y copiar a la vez ni de subir a la nube.

## 8. Ideas para siguientes pasos

1. Probar en Windows y ajustar foco o atajos si hace falta.
2. Soporte multi-monitor (captura de todas las pantallas o elegir cuál).
3. Texto multilínea y mover o editar anotaciones existentes.
4. Opción "guardar y copiar" en un solo paso, y formato por defecto configurable (PNG, JPG).
5. Pantalla de ajustes (atajo global personalizable, nombre de archivo, iniciar con Windows).
6. Notificación con clic para abrir la captura guardada.
