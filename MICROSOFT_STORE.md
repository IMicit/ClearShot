# Guía para publicar y monetizar ClearShot en Microsoft Store (Costo $0)

Esta guía resume paso a paso cómo subir **ClearShot** a la Microsoft Store y cobrar por ella **sin gastar un solo peso**.

---

## 1. Preparar la versión comercial (Licencia LGPLv3 — $0)

`clearshot.py` ya está programado para usar **`PySide6`** automáticamente cuando está instalado.
A diferencia de `PyQt6` (que es GPLv3), **`PySide6`** tiene licencia **LGPLv3**, lo que te permite **vender tu aplicación comercialmente con código cerrado sin pagar licencias**.

Antes de generar el ejecutable para la tienda, instala `PySide6`:

```powershell
pip install PySide6 pyinstaller
```

Y compila excluyendo `PyQt6`:

```powershell
python clearshot.py --make-icon icon.ico
python -m PyInstaller --noconsole --onedir --clean --noconfirm --name ClearShot --exclude-module PyQt6 --exclude-module pynput --icon icon.ico clearshot.py
```

El programa listo quedará en la carpeta `dist\ClearShot`.

---

## 2. Crear tu cuenta de desarrollador en Microsoft ($0)

1. Entra a [Microsoft Partner Center](https://partner.microsoft.com/dashboard/registration/AccountEnrollment).
2. Inicia sesión con tu cuenta personal de Microsoft (Outlook / Hotmail).
3. Elige **Cuenta Individual (Individual)** — es **gratuita ($0)** para desarrolladores individuales.
4. Completa tu perfil y verifica tu identidad.
5. En la sección **Payout and Tax Profiles (Pagos e impuestos)**, conecta tu cuenta bancaria o PayPal y completa el formulario tributario digital para recibir el **85% de cada venta**.

---

## 3. Empaquetar en formato MSIX ($0)

Para cobrar directamente con el botón **"Comprar"** de la Microsoft Store (y que Microsoft firme digitalmente tu ejecutable gratis para evitar el cartel azul de SmartScreen), debes subir un paquete `.msix`:

1. Instala gratis **MSIX Packaging Tool** desde la propia Microsoft Store.
2. Ábrela y elige **Application package → Create package on this computer**.
3. Cuando te pida ejecutar el instalador, ejecuta `instalar.bat` (que copia `ClearShot` a `%LOCALAPPDATA%\ClearShot` y crea el acceso directo).
4. En **Package Information**:
   - **Package Name / Identity:** el nombre exacto que te asigne Microsoft Partner Center cuando reserves el nombre `ClearShot` (ej. `12345TuNombre.ClearShot`).
   - **Publisher Name:** el código `CN=...` que aparece en tu Partner Center (*Account Settings → Organization Profile → Legal Info*).
   - **Version:** `1.2.0.0`
   - **Sign package:** marca **Do not sign package** (la Microsoft Store lo firma automáticamente gratis al aprobarlo).
5. Guarda el archivo `ClearShot.msix`.

---

## 4. Configurar la ficha en Microsoft Partner Center para vender más

- **Precio recomendado:** **$2.99 USD** o **$3.99 USD** (pago único) con **Prueba gratuita (Free Trial) de 7 días** activada en la sección *Pricing and availability*.
- **URL de Política de Privacidad (obligatoria):**
  Usa el enlace directo al archivo [PRIVACY.md](PRIVACY.md) de tu repositorio:
  `https://github.com/IMicit/ClearShot/blob/main/PRIVACY.md`
- **Puntos clave para la descripción de la tienda:**
  - 🎯 **100% Sin pérdida de calidad (Lossless PNG)** a la resolución física real de tu monitor 4K / HiDPI.
  - 📌 **Fijar en pantalla (Pin to screen):** deja tus recortes flotando encima de cualquier ventana con zoom y control de opacidad.
  - 🔤 **Extractor de texto OCR instantáneo y sin internet:** copia texto de cualquier imagen o video en medio segundo.
  - ✨ **Modo Fondo bonito (Beautifier):** agrega degradados modernos, bordes redondeados y sombra profesional en un clic.
  - 🔒 **100% Privado y 0% CPU en reposo:** sin anuncios, sin telemetría y sin subir tus capturas a servidores externos.
