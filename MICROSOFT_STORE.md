# Guía Rápida para Publicar ClearShot en Microsoft Store ($0)

Ya tienes **todo automatizado** en este proyecto:
- **Licencia comercial libre (`PySide6-Essentials` / LGPLv3):** ya instalada y configurada.
- **Generador automático de paquete `.MSIX` (`empaquetar_store.bat`):** descarga `makeappx.exe` oficial de Microsoft y crea `store\ClearShot.msix` sin que tengas que instalar los 4 GB del Windows SDK.
- **Iconos y 3 Capturas Promocionales Full HD (`1920x1080`):** ya generadas en `store\assets\` y `store\screenshots\`.

---

## Paso 1: Crear tu cuenta y reservar el nombre "ClearShot" (5 minutos)

1. Abre **[Microsoft Partner Center](https://partner.microsoft.com/dashboard/registration/AccountEnrollment)** e inicia sesión con tu cuenta Microsoft.
2. Elige **Cuenta Individual (Individual)** (es **gratis / $0**).
3. En el menú izquierdo, entra a **Apps and games → + New product → MSIX or PWA app**.
4. Escribe el nombre **`ClearShot`** (o **`ClearShot Pro`** si prefieres) y haz clic en **Reserve product name**.
5. En el menú izquierdo de tu app, haz clic en **Product management → Product identity** y copia estos 3 valores:
   - `Package/Identity/Name` (ej: `12345TuNombre.ClearShot`)
   - `Package/Identity/Publisher` (ej: `CN=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)
   - `Package/Properties/PublisherDisplayName` (tu nombre de editor)

---

## Paso 2: Generar tu archivo `ClearShot.msix` con 1 clic

1. Haz doble clic en **`empaquetar_store.bat`**.
2. Pega los 3 valores que copiaste en el Paso 1 cuando te los pida en la consola.
3. En menos de 1 minuto te dejará creado el archivo **`store\ClearShot.msix`** compilado con `PySide6` (100% LGPLv3 comercial).

---

## Paso 3: Completar el envío en Partner Center (Copiar y Pegar)

En tu panel de Partner Center haz clic en **Start your submission** y completa las secciones:

### 1. Pricing and availability (Precio y disponibilidad)
- **Markets:** Todos los mercados.
- **Base price:** **$2.99 USD** (o **$3.99 USD**).
- **Free trial:** Selecciona **Time-limited trial → 7 days** (aumenta muchísimo las descargas y conversiones).

### 2. Properties (Propiedades)
- **Category:** *Utilities & tools* (Utilidades y herramientas).
- **Privacy policy URL:**
  ```text
  https://github.com/IMicit/ClearShot/blob/main/PRIVACY.md
  ```
- **System requirements:** Windows 10 versión 1809 (compilación 17763) o superior, arquitectura x64.

### 3. Packages (Paquetes)
- Arrastra el archivo **`store\ClearShot.msix`** generado por `empaquetar_store.bat`.

### 4. Store listings (Ficha de la tienda — Textos listos para copiar y pegar)

- **Description (Descripción):**
  ```text
  ClearShot es un capturador de pantalla ultrarrápido y sin pérdida de calidad (100% Lossless PNG) diseñado para monitores modernos 4K y HiDPI en Windows.

  A diferencia de otros capturadores que recomprimen tus imágenes, consumen CPU constantemente en segundo plano o suben tus capturas a servidores externos dudosos, ClearShot funciona 100% en tu equipo local con 0% de uso de CPU en reposo.

  FUNCIONES PRINCIPALES Y PRO:
  • Nitidez 1:1 sin pérdida de calidad: Captura a la resolución física real de tu pantalla (DPI Awareness Per-Monitor V2) y exporta en PNG sin compresión destructiva.
  • Fijar captura en pantalla (Pin to screen - Tecla F): Deja cualquier recorte flotando siempre visible encima de tus demás ventanas. Muévelo libremente, haz zoom con la rueda del ratón o ajusta su opacidad con Ctrl + Rueda para comparar código, datos o diseños.
  • Extractor de texto OCR sin internet (Tecla O): Selecciona cualquier zona de la pantalla y copia instantáneamente el texto que contiene al portapapeles usando reconocimiento óptico local.
  • Modo Fondo bonito / Beautifier (Tecla B / Shift+B): Envuelve tus capturas en un marco profesional de alta resolución con 5 estilos de degradado, esquinas redondeadas y sombra suave multicapa en un solo clic.
  • Herramientas completas de anotación: Lápiz, línea, flecha, rectángulo, elipse, resaltador, texto nítido, números de paso (1, 2, 3...) y pixelado seguro para ocultar datos sensibles.
  • Lupa 8x de precisión: Muestra coordenadas exactas y el código de color HEX bajo el cursor.
  • 100% Privado y ligero: Sin anuncios, sin suscripciones, sin telemetría y sin conexión a la nube.
  ```

- **Product features (Características destacadas — agrega una por línea):**
  - `Captura 100% sin pérdida de calidad (Lossless PNG) a resolución nativa 4K/HiDPI`
  - `Fijar capturas flotantes en pantalla (Pin to screen) con zoom y opacidad`
  - `Extractor de texto OCR instantáneo y 100% offline`
  - `Modo Fondo bonito (Beautifier) con 5 fondos degradados y sombra suave`
  - `Anotaciones rápidas, números de paso, pixelado de datos y lupa 8x HEX`
  - `0% consumo de CPU en reposo y privacidad total sin servidores externos`

- **Screenshots (Capturas de pantalla):**
  Sube las 3 imágenes Full HD (`1920x1080`) que ya están listas en tu carpeta **`store\screenshots\`**:
  1. `01_captura_y_anotaciones.png`
  2. `02_modo_fondo_bonito.png`
  3. `03_pin_y_ocr_offline.png`

- **Store logos (Icono 300x300):**
  Sube **`store\assets\StoreListing_300x300.png`**.

- **Search terms (Palabras clave — hasta 7):**
  `screenshot`, `captura de pantalla`, `lightshot`, `snipping tool`, `ocr`, `pin to screen`, `screen capture`

### 5. Notes for certification (Notas para el revisor de Microsoft)
Copia esto en el cuadro *Notes for certification* para que la aprueben rápido en la primera revisión:
```text
ClearShot runs in the Windows system tray (notification area next to the clock) and starts minimized to the tray.
To test the app:
1. Click the blue ClearShot icon in the system tray, or press PrintScreen (Impr Pant) / Ctrl+Alt+S.
2. Drag to select any area of the screen.
3. Use the floating toolbar to annotate, toggle Beautifier background (B), extract text via offline OCR (O), pin the capture on screen (F), copy to clipboard (Enter / Ctrl+C), or save to Pictures\ClearShot (Ctrl+S).
```

Haz clic en **Submit to the Store** y Microsoft la revisará y publicará (usualmente tarda entre 24 y 48 horas).
