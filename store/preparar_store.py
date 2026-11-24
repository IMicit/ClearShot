"""Genera todos los recursos visuales, capturas promocionales HD (1920x1080)
y estructura MSIX necesarios para publicar ClearShot en la Microsoft Store."""
import io
import json
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import clearshot as cs  # noqa: E402
from clearshot import (ACCENT, BEAUTIFY_THEMES, QApplication, QColor, QFont,  # noqa: E402
                       QImage, QLinearGradient, QPainter, QPainterPath, QPen,
                       QPointF, QPolygonF, QRect, QRectF, Qt, apply_beautifier,
                       draw_icon, tool_icon)

STORE_DIR = ROOT / "store"
ASSETS_DIR = STORE_DIR / "assets"
SHOTS_DIR = STORE_DIR / "screenshots"
MSIX_STAGE = STORE_DIR / "msix_layout"


def make_logo_tile(w: int, h: int, icon_size: int) -> QImage:
    img = QImage(w, h, QImage.Format.Format_ARGB32_Premultiplied)
    img.fill(Qt.GlobalColor.transparent)
    pm = draw_icon(icon_size)
    p = QPainter(img)
    p.setRenderHints(QPainter.RenderHint.Antialiasing |
                     QPainter.RenderHint.SmoothPixmapTransform)
    p.drawPixmap((w - icon_size) // 2, (h - icon_size) // 2, pm)
    p.end()
    return img


def generate_store_icons():
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    # Iconos requeridos dentro del paquete MSIX
    make_logo_tile(50, 50, 46).save(str(ASSETS_DIR / "StoreLogo.png"), "PNG")
    make_logo_tile(44, 44, 40).save(str(ASSETS_DIR / "Square44x44Logo.png"), "PNG")
    make_logo_tile(150, 150, 116).save(str(ASSETS_DIR / "Square150x150Logo.png"), "PNG")
    make_logo_tile(310, 150, 116).save(str(ASSETS_DIR / "Wide310x150Logo.png"), "PNG")
    # Logos para subir en la ficha de Partner Center (Store Listing)
    make_logo_tile(300, 300, 280).save(str(ASSETS_DIR / "StoreListing_300x300.png"), "PNG")


def _draw_mock_desktop(p: QPainter, w: int, h: int):
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0.0, QColor("#0f172a"))
    grad.setColorAt(0.5, QColor("#1e1b4b"))
    grad.setColorAt(1.0, QColor("#0f172a"))
    p.fillRect(0, 0, w, h, grad)

    # Ventana simulada de código/dashboard
    win = QRectF(260, 160, 1400, 740)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 110))
    p.drawRoundedRect(win.adjusted(0, 14, 0, 14), 16, 16)
    p.setBrush(QColor("#161922"))
    p.setPen(QPen(QColor("#2e3446"), 2))
    p.drawRoundedRect(win, 16, 16)

    # Barra de título con 3 puntos
    for i, col in enumerate(("#ff5f56", "#ffbd2e", "#27c93f")):
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(col))
        p.drawEllipse(QPointF(295 + i * 24, 192), 7, 7)

    f_title = QFont("Segoe UI", 13)
    f_title.setBold(True)
    p.setFont(f_title)
    p.setPen(QColor("#9aa0b0"))
    p.drawText(QRectF(380, 176, 500, 32), Qt.AlignmentFlag.AlignVCenter,
               "ClearShot Pro — Captura 4K Lossless para Windows")

    # Tarjetas y gráficos dentro de la ventana simulada
    cards = [
        (310, 240, 400, 210, "#7C4DFF", "Resolución Física 1:1", "PNG 100% sin pérdida\nDPI Per-Monitor V2"),
        (740, 240, 420, 210, "#00C2E0", "0% CPU en Reposo", "Atajo nativo RegisterHotKey\nArranque instantáneo"),
        (1190, 240, 420, 210, "#22c55e", "100% Privado y Local", "Sin nube ni telemetría\nOCR nativo sin internet"),
    ]
    for x, y, cw, ch, col, title, desc in cards:
        r = QRectF(x, y, cw, ch)
        p.setBrush(QColor("#1e2230"))
        p.setPen(QPen(QColor(col), 2))
        p.drawRoundedRect(r, 12, 12)
        ft = QFont("Segoe UI", 16)
        ft.setBold(True)
        p.setFont(ft)
        p.setPen(QColor("white"))
        p.drawText(QRectF(x + 24, y + 24, cw - 48, 36), Qt.AlignmentFlag.AlignVCenter, title)
        fd = QFont("Segoe UI", 13)
        p.setFont(fd)
        p.setPen(QColor("#b8bfd1"))
        p.drawText(QRectF(x + 24, y + 76, cw - 48, 100), desc)

    # Bloque inferior simulado de código
    code_r = QRectF(310, 480, 1300, 380)
    p.setBrush(QColor("#11131a"))
    p.setPen(QPen(QColor("#2a2f3d"), 1.5))
    p.drawRoundedRect(code_r, 12, 12)
    fc = QFont("Consolas", 14)
    p.setFont(fc)
    lines = [
        ("#7C4DFF", "def ", "#00C2E0", "capture_lossless", "#e8e8ee", "(screen, area):"),
        ("#6b7280", "    # Captura a resolución nativa real sin recomprimir", "", "", "", ""),
        ("#e8e8ee", "    img = screen.grabWindow(", "#ffcc00", "0", "#e8e8ee", ").copy(area)"),
        ("#e8e8ee", "    text = ", "#34c759", "extract_windows_ocr", "#e8e8ee", "(img)   # OCR offline en 0.5s"),
        ("#7C4DFF", "    return ", "#e8e8ee", "apply_beautifier(img, theme=", "#ff9500", "'Violeta Cyber'", "#e8e8ee", ")"),
    ]
    for idx, parts in enumerate(lines):
        cx = 345
        cy = 520 + idx * 42
        for i in range(0, len(parts), 2):
            col, txt = parts[i], parts[i + 1]
            if not txt:
                continue
            p.setPen(QColor(col))
            p.drawText(QPointF(cx, cy), txt)
            cx += p.fontMetrics().horizontalAdvance(txt)


def _draw_banner_header(p: QPainter, title: str, subtitle: str):
    r = QRectF(0, 0, 1920, 118)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(15, 18, 26, 220))
    p.drawRect(r)
    p.drawPixmap(48, 22, draw_icon(74))
    ft = QFont("Segoe UI", 24)
    ft.setBold(True)
    p.setFont(ft)
    p.setPen(QColor("white"))
    p.drawText(QRectF(142, 18, 1700, 44), Qt.AlignmentFlag.AlignVCenter, title)
    fs = QFont("Segoe UI", 14)
    p.setFont(fs)
    p.setPen(QColor("#00C2E0"))
    p.drawText(QRectF(142, 64, 1700, 34), Qt.AlignmentFlag.AlignVCenter, subtitle)


def generate_promotional_screenshots():
    """Genera 3 capturas promocionales 1920x1080 listas para subir a Microsoft Store."""
    SHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # --- Captura 1: Selección + Anotaciones + Lupa 8x ---
    s1 = QImage(1920, 1080, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(s1)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
    _draw_mock_desktop(p, 1920, 1080)
    bright = s1.copy()
    p.fillRect(0, 0, 1920, 1080, QColor(0, 0, 0, 120))
    sel = QRect(290, 220, 1340, 520)
    p.drawImage(sel, bright, sel)
    p.setPen(QPen(QColor(ACCENT), 3))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawRect(QRectF(sel))

    # Flecha y pasos simulados
    cs.draw_annotation(p, {"tool": "rect", "color": "#ff3b30", "width": 4,
                           "p1": QPointF(735, 235), "p2": QPointF(1165, 455)}, s1, 1.0)
    cs.draw_annotation(p, {"tool": "arrow", "color": "#ffcc00", "width": 5,
                           "p1": QPointF(620, 560), "p2": QPointF(735, 430)}, s1, 1.0)
    cs.draw_annotation(p, {"tool": "step", "color": "#7C4DFF", "width": 5,
                           "pos": QPointF(735, 235), "n": 1}, s1, 1.0)
    cs.draw_annotation(p, {"tool": "step", "color": "#00C2E0", "width": 5,
                           "pos": QPointF(1195, 235), "n": 2}, s1, 1.0)

    _draw_banner_header(
        p,
        "ClearShot — Capturas de pantalla sin pérdida de calidad (Lossless PNG)",
        "Anotaciones instantáneas · Lupa 8x con color HEX · Resolución física real 4K / HiDPI"
    )
    p.end()
    s1.save(str(SHOTS_DIR / "01_captura_y_anotaciones.png"), "PNG")

    # --- Captura 2: Modo Fondo Bonito (Beautifier) ---
    s2 = QImage(1920, 1080, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(s2)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
    s2.fill(QColor("#0d1017"))
    card_src = bright.copy(QRect(260, 160, 1400, 700))
    beautified = apply_beautifier(card_src, 1.0, 0)
    scaled_b = beautified.scaled(1460, 780, Qt.AspectRatioMode.KeepAspectRatio,
                                 Qt.TransformationMode.SmoothTransformation)
    p.drawImage((1920 - scaled_b.width()) // 2, 180, scaled_b)
    _draw_banner_header(
        p,
        "Modo Fondo Bonito (Beautifier) en 1 Clic",
        "5 fondos degradados profesionales · Esquinas redondeadas · Sombra suave multicapa lista para compartir"
    )
    p.end()
    s2.save(str(SHOTS_DIR / "02_modo_fondo_bonito.png"), "PNG")

    # --- Captura 3: Fijar en pantalla (Pin) + Extractor de texto OCR ---
    s3 = QImage(1920, 1080, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(s3)
    p.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
    _draw_mock_desktop(p, 1920, 1080)
    # Ventana flotante Pin simulada encima
    pin_r = QRectF(1120, 470, 620, 380)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(0, 0, 0, 150))
    p.drawRoundedRect(pin_r.adjusted(-8, 8, 8, 16), 12, 12)
    p.drawImage(pin_r, bright, QRectF(295, 225, 440, 250))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(ACCENT), 4))
    p.drawRect(pin_r)
    # Badge de Pin + OCR
    badge = QRectF(1136, 486, 360, 40)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(20, 22, 28, 235))
    p.drawRoundedRect(badge, 8, 8)
    fb = QFont("Segoe UI", 13)
    fb.setBold(True)
    p.setFont(fb)
    p.setPen(QColor("white"))
    p.drawText(badge, Qt.AlignmentFlag.AlignCenter, "📌 Captura fijada (Pin) · Zoom 125%")

    _draw_banner_header(
        p,
        "Fijar en Pantalla (Pin) y Extractor de Texto OCR sin Internet",
        "Deja recortes flotando siempre visibles con zoom y opacidad · Copia texto de cualquier imagen con OCR nativo (tecla O)"
    )
    p.end()
    s3.save(str(SHOTS_DIR / "03_pin_y_ocr_offline.png"), "PNG")


def write_appx_manifest(identity_name: str = "CristbalMuoz.ClearShotPro",
                        publisher_id: str = "CN=C6827F92-4142-476D-B093-94A5E19E14FA",
                        publisher_display: str = "Cristóbal Muñoz",
                        display_name: str = "ClearShot Pro",
                        version: str = "1.2.0.0"):
    manifest = f"""<?xml version="1.0" encoding="utf-8"?>
<Package
  xmlns="http://schemas.microsoft.com/appx/manifest/foundation/windows10"
  xmlns:uap="http://schemas.microsoft.com/appx/manifest/uap/windows10"
  xmlns:uap5="http://schemas.microsoft.com/appx/manifest/uap/windows10/5"
  xmlns:rescap="http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"
  IgnorableNamespaces="uap uap5 rescap">

  <Identity
    Name="{identity_name}"
    Publisher="{publisher_id}"
    Version="{version}"
    ProcessorArchitecture="x64" />

  <Properties>
    <DisplayName>{display_name}</DisplayName>
    <PublisherDisplayName>{publisher_display}</PublisherDisplayName>
    <Logo>assets\\StoreLogo.png</Logo>
  </Properties>

  <Dependencies>
    <TargetDeviceFamily Name="Windows.Desktop" MinVersion="10.0.17763.0" MaxVersionTested="10.0.22631.0" />
  </Dependencies>

  <Resources>
    <Resource Language="es-cl" />
    <Resource Language="es-es" />
    <Resource Language="en-us" />
  </Resources>

  <Applications>
    <Application Id="ClearShotPro" Executable="ClearShot.exe" EntryPoint="Windows.FullTrustApplication">
      <uap:VisualElements
        DisplayName="{display_name}"
        Description="Capturador de pantalla sin pérdida de calidad con Pin en pantalla, OCR offline y Modo Fondo bonito."
        BackgroundColor="transparent"
        Square150x150Logo="assets\\Square150x150Logo.png"
        Square44x44Logo="assets\\Square44x44Logo.png">
        <uap:DefaultTile Wide310x150Logo="assets\\Wide310x150Logo.png" />
      </uap:VisualElements>
      <Extensions>
        <uap5:Extension Category="windows.startupTask" Executable="ClearShot.exe" EntryPoint="Windows.FullTrustApplication">
          <uap5:StartupTask TaskId="ClearShotStartup" Enabled="true" DisplayName="{display_name}" />
        </uap5:Extension>
      </Extensions>
    </Application>
  </Applications>

  <Capabilities>
    <rescap:Capability Name="runFullTrust" />
  </Capabilities>
</Package>
"""
    (STORE_DIR / "AppxManifest.xml").write_text(manifest, encoding="utf-8")


def ensure_makeappx() -> Path:
    """Obtiene makeappx.exe oficial de Microsoft.Windows.SDK.BuildTools (NuGet)
    sin necesidad de instalar los 4 GB del Windows SDK completo."""
    tools_dir = ROOT / "build" / "sdk_tools"
    exe = tools_dir / "makeappx.exe"
    if exe.exists():
        return exe
    print("Descargando makeappx.exe oficial de Microsoft SDK BuildTools...")
    tools_dir.mkdir(parents=True, exist_ok=True)
    idx_url = "https://api.nuget.org/v3-flatcontainer/microsoft.windows.sdk.buildtools/index.json"
    with urllib.request.urlopen(idx_url) as r:
        versions = [v for v in json.loads(r.read())["versions"] if "-" not in v]
    v = versions[-1]
    pkg_url = (f"https://api.nuget.org/v3-flatcontainer/"
               f"microsoft.windows.sdk.buildtools/{v}/"
               f"microsoft.windows.sdk.buildtools.{v}.nupkg")
    data = urllib.request.urlopen(pkg_url).read()
    zf = zipfile.ZipFile(io.BytesIO(data))
    prefix = f"bin/{v.rsplit('.', 1)[0]}.0/x64/"
    for name in zf.namelist():
        if name.startswith(prefix) and not name.endswith("/"):
            rel = name[len(prefix):]
            dest = tools_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(name))
    return exe


def build_msix(identity_name: str, publisher_id: str, publisher_display: str,
               display_name: str = "ClearShot Pro", version: str = "1.2.0.0") -> Path:
    """Empaqueta dist/ClearShot + AppxManifest.xml + assets en store/ClearShot.msix."""
    dist_dir = ROOT / "dist" / "ClearShot"
    if not (dist_dir / "ClearShot.exe").exists():
        raise FileNotFoundError("No se encontró dist/ClearShot/ClearShot.exe. Compila primero.")

    write_appx_manifest(identity_name, publisher_id, publisher_display, display_name, version)
    if MSIX_STAGE.exists():
        shutil.rmtree(MSIX_STAGE)
    shutil.copytree(dist_dir, MSIX_STAGE)
    shutil.copytree(ASSETS_DIR, MSIX_STAGE / "assets", dirs_exist_ok=True)
    shutil.copy2(STORE_DIR / "AppxManifest.xml", MSIX_STAGE / "AppxManifest.xml")

    makeappx = ensure_makeappx()
    out_msix = STORE_DIR / "ClearShot.msix"
    if out_msix.exists():
        out_msix.unlink()
    subprocess.run([str(makeappx), "pack", "/d", str(MSIX_STAGE), "/p", str(out_msix), "/o"],
                   check=True)
    shutil.rmtree(MSIX_STAGE, ignore_errors=True)
    return out_msix


def main():
    app = QApplication(sys.argv)
    generate_store_icons()
    generate_promotional_screenshots()

    identity_name = "CristbalMuoz.ClearShotPro"
    publisher_id = "CN=C6827F92-4142-476D-B093-94A5E19E14FA"
    publisher_display = "Cristóbal Muñoz"
    display_name = "ClearShot Pro"
    id_file = STORE_DIR / "partner_identity.json"
    if id_file.exists():
        cfg_data = json.loads(id_file.read_text(encoding="utf-8"))
        identity_name = cfg_data.get("identity_name", identity_name)
        publisher_id = cfg_data.get("publisher_id", publisher_id)
        publisher_display = cfg_data.get("publisher_display", publisher_display)
        display_name = cfg_data.get("display_name", display_name)

    write_appx_manifest(identity_name, publisher_id, publisher_display, display_name)
    print("OK: Iconos de Microsoft Store generados en:", ASSETS_DIR)
    print("OK: 3 capturas promocionales Full HD (1920x1080) generadas en:", SHOTS_DIR)
    print("OK: AppxManifest.xml generado en:", STORE_DIR / "AppxManifest.xml")

    if "--pack" in sys.argv:
        msix = build_msix(identity_name, publisher_id, publisher_display, display_name)
        print("OK: Paquete Microsoft Store generado en:", msix)


if __name__ == "__main__":
    main()
