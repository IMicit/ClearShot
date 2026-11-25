"""
ClearShot - Capturador de pantalla estilo Lightshot, SIN pérdida de calidad.

- Captura a la resolución física real de la pantalla (respeta escalado HiDPI).
- Guarda en PNG (lossless) y copia al portapapeles sin recomprimir.
- Guardar va SIEMPRE a la carpeta configurada (por defecto Imágenes\\ClearShot).
  Se cambia desde la bandeja o desde el botón de carpeta de la barra.
- Herramientas: área, lápiz, línea, flecha, rectángulo, elipse, resaltador,
  texto, números de paso y pixelado para ocultar datos.
- Funciones Pro: fijar captura flotante en pantalla (F), extraer texto con OCR
  nativo sin internet (O) y modo Fondo bonito con degradado y sombra (B).
- Atajo global: Impr Pant (o Ctrl+Alt+S). Corre en la bandeja del sistema.
"""
import math
import os
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from functools import lru_cache
from pathlib import Path

# Soporta PySide6 (LGPLv3: uso comercial libre en Microsoft Store) y PyQt6
try:
    from PySide6.QtCore import (QAbstractNativeEventFilter, QDir, QLockFile, QObject,
                                QPoint, QPointF, QRect, QRectF, QSettings, QSize,
                                QStandardPaths, Qt, QTimer, QUrl, Signal as pyqtSignal)
    from PySide6.QtGui import (QAction, QColor, QConicalGradient, QCursor,
                               QDesktopServices, QFont, QFontMetrics, QGuiApplication,
                               QIcon, QImage, QLinearGradient, QPainter, QPainterPath,
                               QPen, QPixmap, QPolygonF)
    from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup,
                                   QColorDialog, QFileDialog, QFrame, QHBoxLayout,
                                   QLabel, QLineEdit, QMenu, QSlider,
                                   QSystemTrayIcon, QToolButton, QVBoxLayout, QWidget)
except ImportError:
    from PyQt6.QtCore import (QAbstractNativeEventFilter, QDir, QLockFile, QObject,
                              QPoint, QPointF, QRect, QRectF, QSettings, QSize,
                              QStandardPaths, Qt, QTimer, QUrl, pyqtSignal)
    from PyQt6.QtGui import (QAction, QColor, QConicalGradient, QCursor,
                             QDesktopServices, QFont, QFontMetrics, QGuiApplication,
                             QIcon, QImage, QLinearGradient, QPainter, QPainterPath,
                             QPen, QPixmap, QPolygonF)
    from PyQt6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup,
                                 QColorDialog, QFileDialog, QFrame, QHBoxLayout,
                                 QLabel, QLineEdit, QMenu, QSlider,
                                 QSystemTrayIcon, QToolButton, QVBoxLayout, QWidget)

ACCENT = "#7C4DFF"
PALETTE = ["#ff3b30", "#ff9500", "#ffcc00", "#34c759", "#00c2e0",
           "#1e90ff", "#af52de", "#ffffff", "#000000"]
BEAUTIFY_THEMES = [
    ("Violeta Cyber", "#7C4DFF", "#00C2E0"),
    ("Atardecer", "#FF512F", "#DD2476"),
    ("Océano", "#2193B0", "#6DD5ED"),
    ("Esmeralda", "#11998E", "#38EF7D"),
    ("Carbón", "#1F2229", "#3A3F4D"),
]
# (clave, nombre, atajo)
TOOLS = [("select", "Área: seleccionar / mover", "V"),
         ("pen", "Lápiz", "P"),
         ("line", "Línea", "L"),
         ("arrow", "Flecha", "A"),
         ("rect", "Rectángulo", "R"),
         ("ellipse", "Elipse", "E"),
         ("marker", "Resaltador", "H"),
         ("text", "Texto", "T"),
         ("step", "Número de paso", "N"),
         ("mosaic", "Pixelar (ocultar datos)", "M")]
TOOL_KEYS = {sc.lower(): key for key, _, sc in TOOLS}

HANDLE_CURSORS = {
    "tl": Qt.CursorShape.SizeFDiagCursor, "br": Qt.CursorShape.SizeFDiagCursor,
    "tr": Qt.CursorShape.SizeBDiagCursor, "bl": Qt.CursorShape.SizeBDiagCursor,
    "t": Qt.CursorShape.SizeVerCursor, "b": Qt.CursorShape.SizeVerCursor,
    "l": Qt.CursorShape.SizeHorCursor, "r": Qt.CursorShape.SizeHorCursor,
}

BAR_QSS = f"""
#bar {{ background:#1b1d24; border:1px solid #343845; border-radius:12px; }}
QToolButton {{ color:#e8e8ee; background:transparent; border:none;
               border-radius:8px; padding:4px; }}
QToolButton:hover {{ background:#2c303b; }}
QToolButton:checked {{ background:{ACCENT}; }}
QToolButton:disabled {{ background:transparent; }}
QToolButton#copy {{ background:{ACCENT}; color:white; padding:4px 12px; font-weight:600; }}
QToolButton#copy:hover {{ background:#9170ff; }}
QToolButton#save {{ background:#16a34a; color:white; padding:4px 12px; font-weight:600; }}
QToolButton#save:hover {{ background:#22c55e; }}
QToolButton#close {{ background:#3b1f26; color:#fecaca; border:1px solid #7f1d1d; padding:4px 10px; font-weight:600; }}
QToolButton#close:hover {{ background:#dc2626; color:white; border:1px solid #ef4444; }}
QLabel {{ color:#9aa0b0; font-size:11px; background:transparent; }}
QFrame#sep {{ background:#343845; border:none; }}
QSlider::groove:horizontal {{ height:4px; background:#343845; border-radius:2px; }}
QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
QSlider::handle:horizontal {{ background:white; width:14px; height:14px;
                              margin:-5px 0; border-radius:7px; }}
QFrame#wstep {{ background:#232630; border:1px solid #343845; border-radius:7px; }}
QToolButton#wminus, QToolButton#wplus {{ border-radius:5px; padding:0px; }}
QToolButton#wminus:hover, QToolButton#wplus:hover {{ background:#323746; }}
QToolButton#wminus:pressed, QToolButton#wplus:pressed {{ background:{ACCENT}; }}
"""


# ============================================================ configuración
_settings: QSettings | None = None


def cfg() -> QSettings:
    """Instancia única de QSettings (antes se creaba una nueva en cada llamada)."""
    global _settings
    if _settings is None:
        _settings = QSettings("ClearShot", "ClearShot")
    return _settings


def default_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation)
    root = Path(base) if base else Path.home() / "Pictures"
    return root / "ClearShot"


def get_save_dir() -> Path:
    v = cfg().value("save_dir", "", type=str)
    return Path(v) if v else default_dir()


def set_save_dir(p: Path):
    s = cfg()
    s.setValue("save_dir", str(p))
    s.sync()


def pick_folder(parent=None) -> Path | None:
    """Pide una carpeta y la guarda como destino definitivo."""
    d = QFileDialog.getExistingDirectory(
        parent, "Elige la carpeta donde se guardarán las capturas",
        str(get_save_dir()))
    if not d:
        return None
    set_save_dir(Path(d))
    return Path(d)


# ============================================================ iconos
def draw_icon(size: int) -> QPixmap:
    """Logo: cuadrado redondeado con degradado y visor de captura."""
    pm = QPixmap(size, size)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.scale(size / 256, size / 256)

    grad = QLinearGradient(0, 0, 256, 256)
    grad.setColorAt(0.0, QColor("#7C4DFF"))
    grad.setColorAt(1.0, QColor("#00C2E0"))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(grad)
    p.drawRoundedRect(QRectF(8, 8, 240, 240), 58, 58)

    pen = QPen(QColor("white"), 20)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    a, b, n = 64, 192, 46          # esquinas del visor y largo de cada brazo
    for x, y, dx, dy in ((a, a, 1, 1), (b, a, -1, 1), (a, b, 1, -1), (b, b, -1, -1)):
        path = QPolygonF([QPointF(x + dx * n, y), QPointF(x, y), QPointF(x, y + dy * n)])
        p.drawPolyline(path)

    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("white"))
    p.drawEllipse(QPointF(128, 128), 21, 21)
    p.end()
    return pm


def make_icon() -> QIcon:
    icon = QIcon()
    for s in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(draw_icon(s))
    return icon


@lru_cache(maxsize=None)
def tool_icon(key: str, color: str = "#e8e8ee") -> QIcon:
    """Iconos de la barra, dibujados en vectorial (nítidos en HiDPI).
    Se cachean: así el overlay no los vuelve a dibujar en cada captura."""
    pm = QPixmap(44, 44)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color)
    pen = QPen(c, 1.8)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)

    if key == "select":
        dash = QPen(pen)
        dash.setStyle(Qt.PenStyle.DashLine)
        dash.setWidthF(1.5)
        p.setPen(dash)
        p.drawRect(QRectF(4, 5, 14, 12))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        for x, y in ((4, 5), (18, 5), (4, 17), (18, 17)):
            p.drawEllipse(QPointF(x, y), 1.8, 1.8)
    elif key == "pen":
        path = QPainterPath(QPointF(3, 14))
        path.cubicTo(6, 3, 10, 3, 11, 11)
        path.cubicTo(12, 18, 16, 17, 19, 7)
        p.drawPath(path)
    elif key == "line":
        p.drawLine(QPointF(4, 18), QPointF(18, 4))
    elif key == "arrow":
        p.drawLine(QPointF(4, 18), QPointF(16, 6))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(c)
        p.drawPolygon(QPolygonF([QPointF(19, 3), QPointF(10.5, 5.5), QPointF(16.5, 11.5)]))
    elif key == "rect":
        p.drawRoundedRect(QRectF(4, 5, 14, 12), 1.5, 1.5)
    elif key == "ellipse":
        p.drawEllipse(QRectF(3.5, 5, 15, 12))
    elif key == "marker":
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(255, 214, 10, 210))
        p.drawRoundedRect(QRectF(3, 5, 16, 8), 2, 2)
        p.setPen(pen)
        p.drawLine(QPointF(5, 17), QPointF(17, 17))
    elif key == "text":
        p.drawLine(QPointF(5, 5.5), QPointF(17, 5.5))
        p.drawLine(QPointF(11, 5.5), QPointF(11, 18))
    elif key == "step":
        p.drawEllipse(QRectF(3, 3, 16, 16))
        f = QFont("Segoe UI")
        f.setPixelSize(11)
        f.setBold(True)
        p.setFont(f)
        p.drawText(QRectF(3, 3, 16, 16), Qt.AlignmentFlag.AlignCenter, "1")
    elif key == "mosaic":
        p.setPen(Qt.PenStyle.NoPen)
        for i in range(3):
            for j in range(3):
                col = QColor(c)
                col.setAlpha(255 if (i + j) % 2 == 0 else 90)
                p.fillRect(QRectF(3.5 + i * 5, 3.5 + j * 5, 5, 5), col)
    elif key in ("undo", "redo"):
        if key == "redo":
            p.translate(22, 0)
            p.scale(-1, 1)
        body = QPainterPath(QPointF(5, 9))
        body.lineTo(13, 9)
        body.cubicTo(19, 9, 19, 17, 13, 17)
        body.lineTo(8, 17)
        p.drawPath(body)
        p.drawPolyline(QPolygonF([QPointF(9, 5), QPointF(5, 9), QPointF(9, 13)]))
    elif key == "copy":
        p.drawPolyline(QPolygonF([QPointF(8, 7), QPointF(8, 4), QPointF(18, 4),
                                  QPointF(18, 14), QPointF(15, 14)]))
        p.drawRoundedRect(QRectF(4, 8, 10, 10), 1.5, 1.5)
    elif key == "save":
        p.drawLine(QPointF(11, 4), QPointF(11, 14))
        p.drawPolyline(QPolygonF([QPointF(7, 10), QPointF(11, 14), QPointF(15, 10)]))
        p.drawPolyline(QPolygonF([QPointF(4, 14), QPointF(4, 18), QPointF(18, 18),
                                  QPointF(18, 14)]))
    elif key == "folder":
        p.drawPolygon(QPolygonF([QPointF(3, 6), QPointF(8, 6), QPointF(10, 8),
                                 QPointF(19, 8), QPointF(19, 17), QPointF(3, 17)]))
    elif key == "close":
        p.drawLine(QPointF(6, 6), QPointF(16, 16))
        p.drawLine(QPointF(16, 6), QPointF(6, 16))
    elif key == "minus":
        p.drawLine(QPointF(6, 11), QPointF(16, 11))
    elif key == "plus":
        p.drawLine(QPointF(6, 11), QPointF(16, 11))
        p.drawLine(QPointF(11, 6), QPointF(11, 16))
    elif key == "pin":
        # Chincheta / Pin
        p.drawLine(QPointF(7, 4), QPointF(15, 4))
        p.drawLine(QPointF(8, 4), QPointF(7, 11))
        p.drawLine(QPointF(14, 4), QPointF(15, 11))
        p.drawLine(QPointF(5, 11), QPointF(17, 11))
        p.drawLine(QPointF(11, 11), QPointF(11, 18.5))
    elif key == "ocr":
        # Visor de reconocimiento de texto [T]
        for x, y, dx, dy in ((4, 4, 1, 1), (18, 4, -1, 1), (4, 18, 1, -1), (18, 18, -1, -1)):
            p.drawPolyline(QPolygonF([QPointF(x + dx * 3.5, y), QPointF(x, y), QPointF(x, y + dy * 3.5)]))
        p.drawLine(QPointF(7.5, 7.5), QPointF(14.5, 7.5))
        p.drawLine(QPointF(11, 7.5), QPointF(11, 15))
    elif key == "beautify":
        # Marco con destello (Fondo bonito)
        p.drawRoundedRect(QRectF(3.5, 5, 15, 12), 2.5, 2.5)
        p.drawLine(QPointF(11, 7.5), QPointF(11, 14.5))
        p.drawLine(QPointF(7.5, 11), QPointF(14.5, 11))
    p.end()
    return QIcon(pm)


# ============================================================ anotaciones
@lru_cache(maxsize=64)
def _font(size: int, bold: bool = True) -> QFont:
    f = QFont("Segoe UI")
    f.setPixelSize(size)
    f.setBold(bold)
    f.setStyleStrategy(QFont.StyleStrategy.PreferAntialias | QFont.StyleStrategy.PreferQuality)
    f.setHintingPreference(QFont.HintingPreference.PreferFullHinting)
    return f


@lru_cache(maxsize=64)
def _fm(size: int, bold: bool = True) -> QFontMetrics:
    return QFontMetrics(_font(size, bold))


def _pen(color, width, cap=Qt.PenCapStyle.RoundCap) -> QPen:
    pen = QPen(QColor(color), width)
    pen.setCapStyle(cap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    return pen


def _draw_mosaic(p: QPainter, a: dict, img: QImage, dpr: float):
    r = QRectF(a["p1"], a["p2"]).normalized()
    src = QRect(math.floor(r.x() * dpr), math.floor(r.y() * dpr),
                math.ceil(r.width() * dpr), math.ceil(r.height() * dpr))
    src = src.intersected(QRect(0, 0, img.width(), img.height()))
    if src.width() < 2 or src.height() < 2:
        return
    block = max(6, round(9 * dpr))
    # El pixelado se calcula una sola vez por zona y se reutiliza en cada repintado
    key = (src.x(), src.y(), src.width(), src.height(), block)
    cached = a.get("_mosaic")
    if cached is not None and cached[0] == key:
        big = cached[1]
    else:
        sub = img.copy(src)
        small = sub.scaled(max(1, src.width() // block), max(1, src.height() // block),
                           Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
        big = small.scaled(src.width(), src.height(),
                           Qt.AspectRatioMode.IgnoreAspectRatio,
                           Qt.TransformationMode.FastTransformation)
        a["_mosaic"] = (key, big)
    dest = QRectF(src.x() / dpr, src.y() / dpr, src.width() / dpr, src.height() / dpr)
    p.drawImage(dest, big)


def _poly(a: dict) -> QPolygonF:
    """Polígono del trazo, construido de forma incremental (no en cada cuadro)."""
    poly = a.get("_poly")
    pts = a["points"]
    if poly is None or poly.count() > len(pts):
        poly = QPolygonF(pts)
    else:
        for i in range(poly.count(), len(pts)):
            poly.append(pts[i])
    a["_poly"] = poly
    return poly


def draw_annotation(p: QPainter, a: dict, img: QImage, dpr: float):
    """Dibuja una anotación. Las coordenadas son lógicas (como el overlay)."""
    t = a["tool"]
    w = a.get("width", 3)
    p.save()
    try:
        if t == "mosaic":
            _draw_mosaic(p, a, img, dpr)
        elif t == "text":
            f = _font(a["size"], bold=True)
            p.setFont(f)
            p.setPen(QColor(a["color"]))
            fm = _fm(a["size"], True)
            p.drawText(QRectF(a["pos"].x() + 3, a["pos"].y() + 3, 4000, fm.height() + 8),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, a["text"])
        elif t == "step":
            col = QColor(a["color"])
            r = 11 + w * 1.2
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
            p.setBrush(col)
            p.drawEllipse(a["pos"], r, r)
            lum = 0.299 * col.red() + 0.587 * col.green() + 0.114 * col.blue()
            f = _font(max(9, int(r * 1.1)), bold=True)
            p.setFont(f)
            p.setPen(QColor("#111111") if lum > 150 else QColor("white"))
            p.drawText(QRectF(a["pos"].x() - r, a["pos"].y() - r, 2 * r, 2 * r),
                       Qt.AlignmentFlag.AlignCenter, str(a["n"]))
        elif t == "marker":
            col = QColor(a["color"])
            col.setAlpha(110)
            p.setPen(_pen(col, max(12, w * 3.5), Qt.PenCapStyle.FlatCap))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if len(a["points"]) > 1:
                p.drawPolyline(_poly(a))
        else:
            p.setPen(_pen(a["color"], w))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if t == "pen":
                pts = a["points"]
                if len(pts) == 1:
                    p.drawPoint(pts[0])
                else:
                    p.drawPolyline(_poly(a))
            elif t == "rect":
                p.drawRect(QRectF(a["p1"], a["p2"]).normalized())
            elif t == "ellipse":
                p.drawEllipse(QRectF(a["p1"], a["p2"]).normalized())
            elif t == "line":
                p.drawLine(a["p1"], a["p2"])
            elif t == "arrow":
                p1, p2 = a["p1"], a["p2"]
                dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
                length = math.hypot(dx, dy)
                if length < 1:
                    return
                ang = math.atan2(dy, dx)
                size = 12 + w * 3
                base = QPointF(p2.x() - math.cos(ang) * size * 0.8,
                               p2.y() - math.sin(ang) * size * 0.8)
                if length > size * 0.8:
                    p.drawLine(p1, base)
                pts = [p2]
                for d in (math.pi - 0.5, math.pi + 0.5):
                    pts.append(QPointF(p2.x() + size * math.cos(ang + d),
                                       p2.y() + size * math.sin(ang + d)))
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor(a["color"]))
                p.drawPolygon(QPolygonF(pts))
    finally:
        p.restore()


# ============================================================ widgets
class Panel(QWidget):
    """Contenedor que absorbe el ratón para no iniciar selecciones debajo."""
    def mousePressEvent(self, e): e.accept()
    def mouseMoveEvent(self, e): e.accept()
    def mouseReleaseEvent(self, e): e.accept()
    def mouseDoubleClickEvent(self, e): e.accept()
    def wheelEvent(self, e): e.accept()


class Swatch(QAbstractButton):
    """Botón circular de color. col=None -> selector de color personalizado."""
    def __init__(self, color=None, tip=""):
        super().__init__()
        self.col = QColor(color) if color else None
        self.setCheckable(True)
        self.setFixedSize(26, 26)
        self.setToolTip(tip)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def set_color(self, c):
        self.col = QColor(c)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = QRectF(self.rect()).adjusted(4.5, 4.5, -4.5, -4.5)
        if self.col is None:
            g = QConicalGradient(r.center(), 0)
            for i in range(7):
                g.setColorAt(i / 6, QColor.fromHsv(int(i / 6 * 359), 220, 255))
            p.setBrush(g)
        else:
            p.setBrush(self.col)
        p.setPen(QPen(QColor(255, 255, 255, 70), 1))
        p.drawEllipse(r)
        if self.isChecked():
            p.setPen(QPen(QColor("white"), 2))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5))
        elif self.underMouse():
            p.setPen(QPen(QColor(255, 255, 255, 90), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QRectF(self.rect()).adjusted(2, 2, -2, -2))


class Dot(QWidget):
    """Vista previa del color y grosor activos."""
    def __init__(self):
        super().__init__()
        self.setFixedSize(30, 30)
        self.col = QColor("white")
        self.w = 4

    def set(self, col, w):
        self.col = QColor(col)
        self.w = w
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        d = min(26, self.w + 3)
        p.setPen(QPen(QColor(255, 255, 255, 80), 1))
        p.setBrush(self.col)
        p.drawEllipse(QPointF(15, 15), d / 2, d / 2)


class TextEdit(QLineEdit):
    escaped = pyqtSignal(bool)  # True si estaba vacío (cerrar captura), False si solo canceló texto

    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:
            was_empty = not self.text().strip()
            self.clear()
            e.accept()
            self.escaped.emit(was_empty)
            return
        super().keyPressEvent(e)


def _sep() -> QFrame:
    f = QFrame()
    f.setObjectName("sep")
    f.setFixedSize(1, 22)
    return f


# ============================================================ funciones Pro
def apply_beautifier(img: QImage, dpr: float, theme_idx: int = 0) -> QImage:
    """Envuelve la captura en un marco de alta resolución con degradado,
    esquinas redondeadas y sombra multicapa suave (100% sin pérdida)."""
    _, c1, c2 = BEAUTIFY_THEMES[theme_idx % len(BEAUTIFY_THEMES)]
    w, h = img.width(), img.height()
    pad = max(round(36 * dpr), min(round(min(w, h) * 0.12), round(72 * dpr)))
    rad = max(round(8 * dpr), min(round(12 * dpr), min(w, h) // 4))
    out = QImage(w + pad * 2, h + pad * 2, QImage.Format.Format_ARGB32_Premultiplied)
    p = QPainter(out)
    p.setRenderHints(QPainter.RenderHint.Antialiasing |
                     QPainter.RenderHint.SmoothPixmapTransform)

    grad = QLinearGradient(0, 0, out.width(), out.height())
    grad.setColorAt(0.0, QColor(c1))
    grad.setColorAt(1.0, QColor(c2))
    p.fillRect(out.rect(), grad)

    card = QRectF(pad, pad, w, h)
    # Sombra multicapa suave
    p.setPen(Qt.PenStyle.NoPen)
    for i in range(10, 0, -1):
        spread = i * 2.2 * dpr
        dy = i * 0.9 * dpr
        alpha = int(38 * ((11 - i) / 10) ** 1.6)
        p.setBrush(QColor(0, 0, 0, alpha))
        p.drawRoundedRect(card.adjusted(-spread, -spread + dy, spread, spread + dy),
                          rad + spread * 0.55, rad + spread * 0.55)

    # Tarjeta con esquinas redondeadas
    p.save()
    clip = QPainterPath()
    clip.addRoundedRect(card, rad, rad)
    p.setClipPath(clip)
    p.drawImage(QPointF(pad, pad), img)
    p.restore()

    # Borde sutil de cristal
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(QColor(255, 255, 255, 65), max(1.0, 1.0 * dpr)))
    p.drawRoundedRect(card, rad, rad)
    p.end()
    return out


_OCR_PS = r"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile,Windows.Storage,ContentType=WindowsRuntime]
$null = [Windows.Media.Ocr.OcrEngine,Windows.Foundation,ContentType=WindowsRuntime]
$null = [Windows.Graphics.Imaging.BitmapDecoder,Windows.Foundation,ContentType=WindowsRuntime]
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]
function Await($op, $t) {
    $m = $asTask.MakeGenericMethod($t)
    $tk = $m.Invoke($null, @($op))
    $tk.Wait(-1) | Out-Null
    return $tk.Result
}
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($env:CS_OCR_IMG)) ([Windows.Storage.StorageFile])
$stream = Await ($file.OpenAsync([Windows.Storage.FileAccessMode]::Read)) ([Windows.Storage.Streams.IRandomAccessStream])
$dec = Await ([Windows.Graphics.Imaging.BitmapDecoder]::CreateAsync($stream)) ([Windows.Graphics.Imaging.BitmapDecoder])
$bmp = Await ($dec.GetSoftwareBitmapAsync()) ([Windows.Graphics.Imaging.SoftwareBitmap])
$eng = [Windows.Media.Ocr.OcrEngine]::TryCreateFromUserProfileLanguages()
$res = Await ($eng.RecognizeAsync($bmp)) ([Windows.Media.Ocr.OcrResult])
$stream.Dispose()
foreach ($line in $res.Lines) { Write-Output $line.Text }
"""


def run_windows_ocr(img: QImage) -> str:
    """Extrae texto usando el motor OCR nativo de Windows (100% offline y gratis)."""
    if sys.platform != "win32":
        return ""
    work = img
    # Si el recorte es pequeño, escalar 2x y añadir margen mejora mucho la lectura
    if work.width() < 200 or work.height() < 90:
        work = work.scaled(work.width() * 2, work.height() * 2,
                           Qt.AspectRatioMode.KeepAspectRatio,
                           Qt.TransformationMode.SmoothTransformation)
    pad = 20
    padded = QImage(work.width() + pad * 2, work.height() + pad * 2,
                    QImage.Format.Format_RGB32)
    padded.fill( work.pixelColor(0, 0) if not work.isNull() else QColor("white"))
    p = QPainter(padded)
    p.drawImage(pad, pad, work)
    p.end()

    tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
    tmp.close()
    try:
        padded.save(tmp.name, "PNG")
        env = os.environ.copy()
        env["CS_OCR_IMG"] = tmp.name
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        r = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", _OCR_PS],
            capture_output=True, text=True, encoding="utf-8", env=env,
            creationflags=flags, timeout=15)
        return r.stdout.strip()
    except Exception:
        return ""
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass


class PinnedWindow(QWidget):
    """Captura flotante fijada siempre encima (Pin to screen)."""
    closed = pyqtSignal(object)
    saved = pyqtSignal(str)
    message = pyqtSignal(str)
    ocr_requested = pyqtSignal(QImage)

    def __init__(self, img: QImage, pos: QPoint, dpr: float):
        super().__init__()
        self.raw_img = img
        self.dpr = dpr
        self.base_w = max(48, round(img.width() / dpr))
        self.base_h = max(36, round(img.height() / dpr))
        self.zoom = 1.0
        self.opac = 1.0
        self._drag_offset: QPoint | None = None
        self._badge = ""
        self._badge_timer = QTimer(self)
        self._badge_timer.setSingleShot(True)
        self._badge_timer.timeout.connect(self._clear_badge)

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setCursor(Qt.CursorShape.SizeAllCursor)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setToolTip("Captura fijada (Pin)\n"
                        "· Arrastrar: mover   · Doble clic / Ctrl+C: copiar\n"
                        "· Rueda: zoom        · Ctrl+Rueda: opacidad\n"
                        "· Clic derecho: menú · Esc: cerrar")
        self.setGeometry(pos.x(), pos.y(), self.base_w, self.base_h)

    def _flash(self, text: str):
        self._badge = text
        self._badge_timer.start(1100)
        self.update()

    def _clear_badge(self):
        self._badge = ""
        self.update()

    def _set_zoom(self, z: float):
        self.zoom = max(0.4, min(3.0, round(z, 2)))
        self.resize(max(48, round(self.base_w * self.zoom)),
                    max(36, round(self.base_h * self.zoom)))
        self._flash(f"Zoom {round(self.zoom * 100)}%")

    def _set_opac(self, o: float):
        self.opac = max(0.25, min(1.0, round(o, 2)))
        self.setWindowOpacity(self.opac)
        self._flash(f"Opacidad {round(self.opac * 100)}%")

    def copy_img(self):
        QApplication.clipboard().setImage(self.raw_img)
        self._flash("Copiada")

    def save_img(self):
        folder = get_save_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"captura_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
            if self.raw_img.save(str(path), "PNG"):
                self._flash("Guardada")
                self.saved.emit(str(path))
            else:
                self.message.emit("No se pudo guardar la captura fijada")
        except OSError:
            self.message.emit("No se pudo acceder a la carpeta de capturas")

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHints(QPainter.RenderHint.Antialiasing |
                         QPainter.RenderHint.SmoothPixmapTransform)
        p.drawImage(QRectF(self.rect()), self.raw_img)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawRect(QRectF(self.rect()).adjusted(1, 1, -1, -1))
        if self._badge:
            f = _font(11, bold=True)
            p.setFont(f)
            bw = _fm(11, True).horizontalAdvance(self._badge) + 18
            r = QRectF(8, 8, bw, 22)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 22, 28, 225))
            p.drawRoundedRect(r, 6, 6)
            p.setPen(QColor("white"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self._badge)

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            e.accept()
        elif e.button() == Qt.MouseButton.RightButton:
            self._show_menu(e.globalPosition().toPoint())

    def mouseMoveEvent(self, e):
        if self._drag_offset is not None and (e.buttons() & Qt.MouseButton.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            e.accept()

    def mouseReleaseEvent(self, _):
        self._drag_offset = None

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.copy_img()

    def wheelEvent(self, e):
        step = 1 if e.angleDelta().y() > 0 else -1
        if e.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self._set_opac(self.opac + step * 0.1)
        else:
            self._set_zoom(self.zoom + step * 0.15)

    def keyPressEvent(self, e):
        k = e.key()
        ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        if k == Qt.Key.Key_Escape:
            self.close_pin()
        elif (ctrl and k == Qt.Key.Key_C) or k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.copy_img()
        elif ctrl and k == Qt.Key.Key_S:
            self.save_img()
        elif k == Qt.Key.Key_O:
            self._flash("Extrayendo texto…")
            self.ocr_requested.emit(self.raw_img)
        elif k == Qt.Key.Key_0:
            self._set_opac(1.0)
            self._set_zoom(1.0)

    def _show_menu(self, gpos: QPoint):
        m = QMenu(self)
        m.addAction("Copiar al portapapeles (Doble clic / Ctrl+C)", self.copy_img)
        m.addAction("Guardar en carpeta (Ctrl+S)", self.save_img)
        m.addAction("Extraer texto con OCR (O)", lambda: (
            self._flash("Extrayendo texto…"), self.ocr_requested.emit(self.raw_img)))
        m.addSeparator()
        m.addAction("Tamaño original 100% (0)", lambda: self._set_zoom(1.0))
        for pct in (100, 75, 50):
            m.addAction(f"Opacidad {pct}%", lambda p=pct: self._set_opac(p / 100))
        m.addSeparator()
        m.addAction("Cerrar (Esc)", self.close_pin)
        m.exec(gpos)

    def close_pin(self):
        self.hide()
        self.closed.emit(self)
        self.deleteLater()


# ============================================================ overlay
class Overlay(QWidget):
    closed = pyqtSignal()
    message = pyqtSignal(str)
    saved = pyqtSignal(str)   # emitida con la ruta completa al guardar con éxito
    pinned = pyqtSignal(QImage, QPoint, float)
    ocr_requested = pyqtSignal(QImage)

    def __init__(self, pixmap: QPixmap, screen):
        super().__init__()
        self.dpr = pixmap.devicePixelRatio()
        # Una sola copia en píxeles físicos (calidad completa): se usa para pintar,
        # recortar, la lupa y el pixelado. No se guarda el QPixmap original.
        self.img = pixmap.toImage()
        self.img.setDevicePixelRatio(1.0)
        # Fondo oscurecido precalculado UNA vez (antes se oscurecía en cada cuadro)
        self.dim = self.img.copy()
        q = QPainter(self.dim)
        q.fillRect(self.dim.rect(), QColor(0, 0, 0, 120))
        q.end()
        self.dim.setDevicePixelRatio(self.dpr)
        self._layer: QImage | None = None      # caché de anotaciones terminadas
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowStaysOnTopHint |
                            Qt.WindowType.Tool)
        self.setGeometry(screen.geometry())
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        s = cfg()
        self.pen_color = QColor(s.value("color", PALETTE[0], type=str)).name()
        self.pen_w = max(1, min(20, s.value("width", 4, type=int)))
        self.custom_color = s.value("custom_color", "", type=str)
        self.beautify = False
        self.beautify_theme = s.value("beautify_theme", 0, type=int) % len(BEAUTIFY_THEMES)

        self.sel: QRect | None = None
        self.drag: dict | None = None
        self.tool = "select"
        self.annots: list[dict] = []
        self.redo_stack: list[dict] = []
        self.cur: dict | None = None
        self.text_edit: TextEdit | None = None
        self.text_pos = QPointF()
        self.text_size = 16
        self.text_color = "#ffffff"
        self._closing = False
        self._exit_hover = False
        self.mouse = QPointF(QCursor.pos() - screen.geometry().topLeft())
        # El overlay pinta todos sus píxeles: Qt no necesita borrar el fondo antes
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)

        self._build_toolbar()
        self._width_dirty = False

    # ---------- UI ----------
    def _tbtn(self, icon_key: str, tip: str, checkable=False) -> QToolButton:
        b = QToolButton()
        b.setIcon(tool_icon(icon_key))
        b.setIconSize(QSize(22, 22))
        b.setFixedSize(34, 34)
        b.setToolTip(tip)
        b.setCheckable(checkable)
        b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        return b

    def _build_toolbar(self):
        self.bar = Panel(self)
        self.bar.setObjectName("bar")
        self.bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.bar.setStyleSheet(BAR_QSS)
        self.bar.setCursor(Qt.CursorShape.ArrowCursor)
        self.bar.setMouseTracking(True)
        root = QVBoxLayout(self.bar)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ---- fila 1: herramientas + acciones
        row1 = QHBoxLayout()
        row1.setSpacing(2)
        self.tool_group = QButtonGroup(self)
        self.tool_btns = {}
        for key, label, sc in TOOLS:
            b = self._tbtn(key, f"{label}  ({sc})", checkable=True)
            b.setChecked(key == self.tool)
            b.clicked.connect(lambda _, k=key: self._set_tool(k))
            self.tool_group.addButton(b)
            self.tool_btns[key] = b
            row1.addWidget(b)
        row1.addSpacing(6)
        row1.addWidget(_sep())
        row1.addSpacing(6)
        self.undo_btn = self._tbtn("undo", "Deshacer  (Ctrl+Z)")
        self.undo_btn.clicked.connect(self.undo)
        self.redo_btn = self._tbtn("redo", "Rehacer  (Ctrl+Shift+Z)")
        self.redo_btn.clicked.connect(self.redo)
        row1.addWidget(self.undo_btn)
        row1.addWidget(self.redo_btn)
        row1.addSpacing(6)
        row1.addWidget(_sep())
        row1.addSpacing(6)
        self.beautify_btn = self._tbtn(
            "beautify",
            "Modo Fondo bonito con degradado y sombra  (B)\n"
            "Cambiar estilo de fondo  (Shift+B o clic derecho)",
            checkable=True)
        self.beautify_btn.clicked.connect(self._toggle_beautify)
        self.beautify_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.beautify_btn.customContextMenuRequested.connect(lambda _: self._cycle_beautify_theme())
        self.pin_btn = self._tbtn("pin", "Fijar captura flotante en pantalla  (F)")
        self.pin_btn.clicked.connect(self.pin_capture)
        self.ocr_btn = self._tbtn("ocr", "Extraer texto de la imagen al portapapeles (OCR)  (O)")
        self.ocr_btn.clicked.connect(self.ocr_capture)
        row1.addWidget(self.beautify_btn)
        row1.addWidget(self.pin_btn)
        row1.addWidget(self.ocr_btn)
        row1.addSpacing(6)
        row1.addWidget(_sep())
        row1.addSpacing(6)
        self.folder_btn = self._tbtn("folder", "")
        self.folder_btn.clicked.connect(self._change_folder)
        row1.addWidget(self.folder_btn)
        row1.addSpacing(4)
        for name, text, icon, fn in (("copy", "Copiar", "copy", self.copy),
                                     ("save", "Guardar", "save", self.save)):
            b = QToolButton()
            b.setObjectName(name)
            b.setText(text)
            b.setIcon(tool_icon(icon, "#ffffff"))
            b.setIconSize(QSize(20, 20))
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            b.setFixedHeight(34)
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(fn)
            row1.addWidget(b)
            setattr(self, name + "_btn", b)
        self.copy_btn.setToolTip("Copiar al portapapeles  (Enter / Ctrl+C)\nGuardar y copiar  (Ctrl+Shift+C)")
        row1.addSpacing(2)
        self.close_btn = QToolButton()
        self.close_btn.setObjectName("close")
        self.close_btn.setText("Salir (Esc)")
        self.close_btn.setIcon(tool_icon("close", "#fecaca"))
        self.close_btn.setIconSize(QSize(18, 18))
        self.close_btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.close_btn.setFixedHeight(34)
        self.close_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.setToolTip("Salir de la captura  (Esc / Clic derecho)")
        self.close_btn.clicked.connect(self.cancel)
        row1.addWidget(self.close_btn)
        root.addLayout(row1)

        # ---- fila 2: colores y grosor (se oculta con la herramienta Área)
        self.row2 = QWidget()
        r2 = QHBoxLayout(self.row2)
        r2.setContentsMargins(2, 0, 2, 0)
        r2.setSpacing(2)
        self.swatch_group = QButtonGroup(self)
        self.swatch_group.setExclusive(True)
        self.swatches = []
        for i, hexcol in enumerate(PALETTE):
            sw = Swatch(hexcol, f"{hexcol}  ({i + 1})")
            sw.clicked.connect(lambda _, s=sw: self._pick_swatch(s))
            self.swatch_group.addButton(sw)
            self.swatches.append(sw)
            r2.addWidget(sw)
        self.custom_sw = Swatch(None, "Color personalizado (clic para elegir)")
        if self.custom_color:
            self.custom_sw.set_color(self.custom_color)
        self.custom_sw.clicked.connect(lambda _: self._pick_swatch(self.custom_sw))
        self.swatch_group.addButton(self.custom_sw)
        r2.addWidget(self.custom_sw)
        r2.addSpacing(8)
        r2.addWidget(_sep())
        r2.addSpacing(8)
        r2.addWidget(QLabel("Grosor"))
        self.wslider = QSlider(Qt.Orientation.Horizontal)
        self.wslider.setRange(1, 20)
        self.wslider.setValue(self.pen_w)
        self.wslider.setFixedWidth(110)
        self.wslider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.wslider.setToolTip("Grosor del trazo (también con - / + o la rueda del ratón)")
        self.wslider.valueChanged.connect(self._set_width)
        r2.addWidget(self.wslider)
        r2.addSpacing(4)
        wstep = QFrame()
        wstep.setObjectName("wstep")
        ws_lay = QHBoxLayout(wstep)
        ws_lay.setContentsMargins(2, 2, 2, 2)
        ws_lay.setSpacing(1)
        self.wminus_btn = self._tbtn("minus", "Disminuir grosor  (-)")
        self.wminus_btn.setObjectName("wminus")
        self.wminus_btn.setFixedSize(24, 22)
        self.wminus_btn.setIconSize(QSize(16, 16))
        self.wminus_btn.setAutoRepeat(True)
        self.wminus_btn.setAutoRepeatDelay(300)
        self.wminus_btn.setAutoRepeatInterval(60)
        self.wminus_btn.clicked.connect(lambda: self.wslider.setValue(self.pen_w - 1))
        wsep = _sep()
        wsep.setFixedSize(1, 14)
        self.wplus_btn = self._tbtn("plus", "Aumentar grosor  (+)")
        self.wplus_btn.setObjectName("wplus")
        self.wplus_btn.setFixedSize(24, 22)
        self.wplus_btn.setIconSize(QSize(16, 16))
        self.wplus_btn.setAutoRepeat(True)
        self.wplus_btn.setAutoRepeatDelay(300)
        self.wplus_btn.setAutoRepeatInterval(60)
        self.wplus_btn.clicked.connect(lambda: self.wslider.setValue(self.pen_w + 1))
        ws_lay.addWidget(self.wminus_btn)
        ws_lay.addWidget(wsep)
        ws_lay.addWidget(self.wplus_btn)
        r2.addWidget(wstep)
        r2.addSpacing(4)
        self.wlabel = QLabel()
        self.wlabel.setFixedWidth(34)
        r2.addWidget(self.wlabel)
        self.dot = Dot()
        r2.addWidget(self.dot)
        r2.addStretch()
        root.addWidget(self.row2)

        self._sync_swatches()
        self._set_width(self.pen_w)
        self._refresh_folder_tips()
        self._annots_changed()
        self.row2.setVisible(self.tool != "select")
        self.bar.hide()

    def _refresh_folder_tips(self):
        d = get_save_dir()
        self.folder_btn.setToolTip(f"Carpeta de guardado:\n{d}\n(clic para cambiarla)")
        self.save_btn.setToolTip(
            f"Guardar en {d}\n(Ctrl+S)  ·  Guardar como…  (Ctrl+Shift+S)")

    def _refresh_undo(self):
        self.undo_btn.setEnabled(bool(self.annots))
        self.redo_btn.setEnabled(bool(self.redo_stack))

    def _annots_changed(self):
        """Llamar cada vez que cambia la lista de anotaciones terminadas."""
        self._layer = None
        self._refresh_undo()

    # ---------- estado: herramienta / color / grosor ----------
    def _set_tool(self, k):
        self._commit_text()
        self.tool = k
        self.tool_btns[k].setChecked(True)
        self.row2.setVisible(k != "select")
        if self.sel:
            self._place_bar()
        self.update()

    def _set_width(self, v):
        self.pen_w = max(1, min(20, int(v)))
        self.wlabel.setText(f"{self.pen_w} px")
        self.dot.set(self.pen_color, self.pen_w)
        self.wminus_btn.setEnabled(self.pen_w > 1)
        self.wplus_btn.setEnabled(self.pen_w < 20)
        self._width_dirty = True       # se guarda al cerrar, no en cada paso del slider

    def _set_color(self, c):
        self.pen_color = QColor(c).name()
        cfg().setValue("color", self.pen_color)
        self._sync_swatches()
        self.dot.set(self.pen_color, self.pen_w)

    def _sync_swatches(self):
        target = None
        for sw in self.swatches:
            if sw.col.name() == self.pen_color:
                target = sw
        if target is None:
            self.custom_sw.set_color(self.pen_color)
            target = self.custom_sw
        target.setChecked(True)
        for sw in self.swatches + [self.custom_sw]:
            sw.update()

    def _pick_swatch(self, sw: Swatch):
        if sw is self.custom_sw:
            c = QColorDialog.getColor(QColor(self.pen_color), self, "Elige un color")
            if c.isValid():
                self.custom_sw.set_color(c)
                cfg().setValue("custom_color", c.name())
                self._set_color(c.name())
            else:
                self._sync_swatches()
            self.activateWindow()
            self.setFocus()
        else:
            self._set_color(sw.col.name())

    def _change_folder(self):
        d = pick_folder(self)
        self.activateWindow()
        self.setFocus()
        if d:
            self._refresh_folder_tips()
            self.message.emit(f"Las capturas se guardarán en: {d}")

    def _place_bar(self):
        if not self.sel:
            return
        self.bar.layout().activate()
        self.bar.adjustSize()
        w, h = self.bar.width(), self.bar.height()
        x = self.sel.right() + 1 - w
        x = min(max(x, 6), self.width() - w - 6)
        y = self.sel.bottom() + 10
        if y + h > self.height() - 6:
            y = self.sel.top() - h - 32            # arriba (deja sitio a la etiqueta)
            if y < 6:
                y = self.sel.bottom() - h - 10     # dentro, abajo
        self.bar.move(x, max(y, 6))
        self.bar.show()
        self.bar.raise_()

    # ---------- geometría de la selección ----------
    def _handle_points(self):
        s = self.sel
        l, t, r, b = s.left(), s.top(), s.right() + 1, s.bottom() + 1
        cx, cy = (l + r) / 2, (t + b) / 2
        return {"tl": (l, t), "t": (cx, t), "tr": (r, t), "l": (l, cy),
                "r": (r, cy), "bl": (l, b), "b": (cx, b), "br": (r, b)}

    def _hit_handle(self, ip: QPoint):
        if not self.sel:
            return None
        for k, (x, y) in self._handle_points().items():
            if abs(ip.x() - x) <= 8 and abs(ip.y() - y) <= 8:
                return k
        return None

    def _update_cursor(self, ip: QPoint):
        cur = Qt.CursorShape.CrossCursor
        if self.sel:
            h = self._hit_handle(ip)
            if h:
                cur = HANDLE_CURSORS[h]
            elif self.sel.contains(ip):
                if self.tool == "select":
                    cur = Qt.CursorShape.SizeAllCursor
                elif self.tool == "text":
                    cur = Qt.CursorShape.IBeamCursor
            elif self.tool == "text":
                # fuera del área: cursor de texto para coherencia
                cur = Qt.CursorShape.IBeamCursor
        self.setCursor(cur)

    # ---------- dibujo ----------
    def _annot_layer(self) -> QImage:
        """Anotaciones terminadas pre-renderizadas en una capa (resolución física).
        Se rehace solo cuando cambia la lista, no en cada movimiento del ratón."""
        if self._layer is None:
            layer = QImage(self.img.size(), QImage.Format.Format_ARGB32_Premultiplied)
            layer.fill(Qt.GlobalColor.transparent)
            layer.setDevicePixelRatio(self.dpr)
            q = QPainter(layer)
            q.setRenderHints(QPainter.RenderHint.Antialiasing |
                             QPainter.RenderHint.TextAntialiasing |
                             QPainter.RenderHint.SmoothPixmapTransform)
            for a in self.annots:
                draw_annotation(q, a, self.img, self.dpr)
            q.end()
            self._layer = layer
        return self._layer

    def _label_geom(self, s: QRect):
        label = f"{round(s.width() * self.dpr)} × {round(s.height() * self.dpr)} px"
        if self.beautify:
            tname = BEAUTIFY_THEMES[self.beautify_theme][0]
            label += f"  ·  Fondo: {tname} (Shift+B)"
        lw = _fm(12, False).horizontalAdvance(label) + 16
        ly = s.top() - 26 if s.top() > 30 else s.top() + 6
        lx = s.left() if s.top() > 30 else s.left() + 6
        return QRectF(lx, ly, lw, 20), label

    def _mag_visible(self) -> bool:
        d = self.drag
        return self.sel is None or bool(d and d["mode"] in ("new", "resize"))

    def _mag_geom(self, pos: QPointF):
        size, info_h = 120, 40
        ox, oy = pos.x() + 24, pos.y() + 24
        if ox + size + 4 > self.width():
            ox = pos.x() - 24 - size
        if oy + size + info_h + 8 > self.height():
            oy = pos.y() - 24 - size - info_h - 8
        return QRectF(ox, oy, size, size), QRectF(ox, oy + size + 6, size, info_h)

    # Zonas que hay que repintar (en vez de repintar la pantalla completa)
    def _sel_bounds(self) -> QRectF | None:
        if not self.sel:
            return None
        r = QRectF(self.sel).adjusted(-7, -7, 8, 8)
        return r.united(self._label_geom(self.sel)[0].adjusted(-2, -2, 2, 2))

    def _mag_bounds(self) -> QRectF | None:
        if not self._mag_visible():
            return None
        rect, panel = self._mag_geom(self.mouse)
        return rect.united(panel).adjusted(-3, -3, 3, 3)

    @staticmethod
    def _annot_bounds(a: dict, tail: bool = False) -> QRectF:
        m = 16 + a.get("width", 3) * 4          # cubre grosor, puntas de flecha, etc.
        if "points" in a:
            pts = a["points"][-2:] if tail else a["points"]
            r = QPolygonF(pts).boundingRect()
        else:
            r = QRectF(a["p1"], a["p2"]).normalized()
        return r.adjusted(-m, -m, m, m)

    def paintEvent(self, _):
        # Qt recorta automáticamente al área sucia: si solo cambió la lupa,
        # solo se procesan esos píxeles.
        p = QPainter(self)
        p.drawImage(QPointF(0, 0), self.dim)
        p.setRenderHints(QPainter.RenderHint.Antialiasing |
                         QPainter.RenderHint.TextAntialiasing |
                         QPainter.RenderHint.SmoothPixmapTransform)
        if self.sel:
            s = self.sel
            src = QRectF(s.x() * self.dpr, s.y() * self.dpr,
                         s.width() * self.dpr, s.height() * self.dpr)
            p.drawImage(QRectF(s), self.img, src)
            # Sin clip: las anotaciones pueden extenderse fuera del área seleccionada
            if self.annots:
                p.drawImage(QPointF(0, 0), self._annot_layer())
            if self.cur:
                draw_annotation(p, self.cur, self.img, self.dpr)

            border_col = BEAUTIFY_THEMES[self.beautify_theme][1] if self.beautify else ACCENT
            p.setPen(QPen(QColor(border_col), 2.0 if self.beautify else 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(s))
            if not self.cur:
                p.setBrush(QColor("white"))
                for x, y in self._handle_points().values():
                    p.drawRoundedRect(QRectF(x - 4, y - 4, 8, 8), 2, 2)

            lrect, label = self._label_geom(s)
            p.setFont(_font(12, bold=False))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 22, 28, 220))
            p.drawRoundedRect(lrect, 6, 6)
            p.setPen(QColor("white"))
            p.drawText(lrect, Qt.AlignmentFlag.AlignCenter, label)
        else:
            self._draw_hint(p)

        if self._mag_visible():
            self._draw_magnifier(p)

    def _hint_rects(self):
        text = "Arrastra para seleccionar el área   ·   Clic derecho para cancelar"
        btn_text = "✕  Salir (Esc)"
        tw = _fm(14, False).horizontalAdvance(text)
        bw = _fm(13, True).horizontalAdvance(btn_text) + 24
        total_w = tw + 28 + bw + 18
        x0 = (self.width() - total_w) / 2
        pill = QRectF(x0, 26, total_w, 40)
        btn = QRectF(pill.right() - bw - 6, 31, bw, 30)
        return pill, btn, text, btn_text

    def _draw_hint(self, p: QPainter):
        pill, btn, text, btn_text = self._hint_rects()
        p.setPen(QPen(QColor(255, 255, 255, 35), 1))
        p.setBrush(QColor(20, 22, 28, 232))
        p.drawRoundedRect(pill, 20, 20)

        p.setFont(_font(14, bold=False))
        p.setPen(QColor("#e8e8ee"))
        text_r = QRectF(pill.left() + 18, pill.top(), pill.width() - btn.width() - 30, pill.height())
        p.drawText(text_r, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, text)

        if self._exit_hover:
            p.setPen(QPen(QColor("#f87171"), 1.2))
            p.setBrush(QColor("#dc2626"))
            p.setFont(_font(13, bold=True))
            p.drawRoundedRect(btn, 15, 15)
            p.setPen(QColor("white"))
        else:
            p.setPen(QPen(QColor("#7f1d1d"), 1.0))
            p.setBrush(QColor("#3b1f26"))
            p.setFont(_font(13, bold=True))
            p.drawRoundedRect(btn, 15, 15)
            p.setPen(QColor("#fecaca"))
        p.drawText(btn, Qt.AlignmentFlag.AlignCenter, btn_text)

    def _draw_magnifier(self, p: QPainter):
        pos = self.mouse
        size, zoom = 120, 8
        side = size / zoom * self.dpr
        cx, cy = pos.x() * self.dpr, pos.y() * self.dpr
        src = QRectF(cx - side / 2, cy - side / 2, side, side)
        rect, panel = self._mag_geom(pos)

        p.save()
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        p.setClipPath(path)
        p.fillRect(rect, QColor(0, 0, 0))
        p.drawImage(rect, self.img, src)
        cell = size / (size / zoom)
        mid = QRectF(rect.center().x() - cell / 2, rect.center().y() - cell / 2, cell, cell)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(0, 0, 0, 200), 3))
        p.drawRect(mid)
        p.setPen(QPen(QColor("white"), 1))
        p.drawRect(mid)
        p.restore()

        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(QColor(ACCENT), 2))
        p.drawRoundedRect(rect, 10, 10)

        ix = int(min(max(cx, 0), self.img.width() - 1))
        iy = int(min(max(cy, 0), self.img.height() - 1))
        col = self.img.pixelColor(ix, iy)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 22, 28, 235))
        p.drawRoundedRect(panel, 8, 8)
        f = _font(12, bold=False)
        p.setFont(f)
        p.setPen(QColor("white"))
        p.drawText(QRectF(panel.x(), panel.y() + 3, panel.width(), 18),
                   Qt.AlignmentFlag.AlignCenter, f"X {ix}   Y {iy}")
        p.setPen(QPen(QColor(255, 255, 255, 90), 1))
        p.setBrush(col)
        p.drawRoundedRect(QRectF(panel.x() + 14, panel.y() + 23, 12, 12), 3, 3)
        p.setPen(QColor("#c9cdd8"))
        p.drawText(QRectF(panel.x() + 32, panel.y() + 20, panel.width() - 36, 18),
                   Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   col.name().upper())

    # ---------- texto ----------
    def _start_text(self, pos: QPointF):
        self.text_size = int(12 + self.pen_w * 2.2)
        self.text_color = self.pen_color
        self.text_pos = QPointF(pos)
        f = _font(self.text_size, bold=True)
        fm = _fm(self.text_size, True)
        e = TextEdit(self)
        e.setFont(f)
        e.setStyleSheet(
            f"QLineEdit{{background:rgba(0,0,0,70);color:{self.text_color};"
            f"border:1px dashed {self.text_color};padding:0px 2px;"
            f"selection-background-color:{ACCENT};}}")
        e.setFixedHeight(fm.height() + 6)

        def fit():
            e.setFixedWidth(max(70, fm.horizontalAdvance(e.text()) + 16))
        e.textChanged.connect(lambda _: fit())
        fit()
        e.move(pos.toPoint())
        e.editingFinished.connect(self._commit_text)
        e.escaped.connect(self._on_text_escaped)
        self.text_edit = e
        e.show()
        e.setFocus()

    def _on_text_escaped(self, was_empty: bool):
        self._commit_text()
        if was_empty:
            self.cancel()
        else:
            self.activateWindow()
            self.setFocus()

    def _commit_text(self):
        e = self.text_edit
        if e is None:
            return
        self.text_edit = None
        txt = e.text().strip()
        e.hide()
        e.deleteLater()
        if txt:
            self.annots.append({"tool": "text", "color": self.text_color,
                                "pos": self.text_pos, "text": txt,
                                "size": self.text_size})
            self.redo_stack.clear()
            self._annots_changed()
        self.setFocus()
        self.update()

    # ---------- ratón ----------
    def mousePressEvent(self, e):
        self._commit_text()
        pos = e.position()
        ip = pos.toPoint()
        if e.button() == Qt.MouseButton.RightButton:
            if self.sel:                       # clic derecho: descartar selección
                self.sel = None
                self.annots.clear()
                self.redo_stack.clear()
                self.bar.hide()
                self._annots_changed()
                self.update()
            else:
                self.cancel()
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return

        if not self.sel and self._hint_rects()[1].contains(pos):
            self.cancel()
            return

        if self.sel:
            h = self._hit_handle(ip)
            if h:
                self.bar.hide()
                self.drag = {"mode": "resize", "handle": h, "origin": ip,
                             "rect": QRect(self.sel)}
                self.update()
                return
            if self.tool == "select":
                # Herramienta área: mover solo dentro del área, fuera = nueva selección
                if self.sel.contains(ip):
                    self.bar.hide()
                    self.drag = {"mode": "move", "origin": ip, "rect": QRect(self.sel)}
                    self.update()
                    return
            else:
                # Herramientas de dibujo: funcionan en toda la pantalla (igual que Lightshot)
                if self.tool == "text":
                    self._start_text(pos)
                elif self.tool == "step":
                    n = sum(1 for a in self.annots if a["tool"] == "step") + 1
                    self.annots.append({"tool": "step", "color": self.pen_color,
                                        "width": self.pen_w, "pos": pos, "n": n})
                    self.redo_stack.clear()
                    self._annots_changed()
                elif self.tool in ("pen", "marker"):
                    self.cur = {"tool": self.tool, "color": self.pen_color,
                                "width": self.pen_w, "points": [pos]}
                else:
                    self.cur = {"tool": self.tool, "color": self.pen_color,
                                "width": self.pen_w, "p1": pos, "p2": pos}
                self.update()
                return

        # clic fuera con herramienta área: nueva selección
        self.bar.hide()
        self.annots.clear()
        self.redo_stack.clear()
        self._annots_changed()
        self.sel = None
        self.drag = {"mode": "new", "origin": ip}
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        ip = pos.toPoint()
        if self.cur:
            # Dibujando: solo se repinta el último tramo / la figura en curso
            c = self.cur
            before = self._annot_bounds(c, tail=True)
            self.mouse = pos
            if c["tool"] in ("pen", "marker"):
                last = c["points"][-1]
                if abs(pos.x() - last.x()) + abs(pos.y() - last.y()) < 1:
                    return                     # movimiento sub-píxel: nada que dibujar
                c["points"].append(pos)
            else:
                p1, p2 = c["p1"], pos
                shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
                if shift and c["tool"] in ("line", "arrow"):
                    if abs(p2.x() - p1.x()) > abs(p2.y() - p1.y()):
                        p2 = QPointF(p2.x(), p1.y())
                    else:
                        p2 = QPointF(p1.x(), p2.y())
                elif shift and c["tool"] in ("rect", "ellipse", "mosaic"):
                    dx, dy = p2.x() - p1.x(), p2.y() - p1.y()
                    m = max(abs(dx), abs(dy))
                    p2 = QPointF(p1.x() + math.copysign(m, dx or 1),
                                 p1.y() + math.copysign(m, dy or 1))
                c["p2"] = p2
            after = self._annot_bounds(c, tail=True)
            self.update(before.united(after).toAlignedRect())
            return

        had_sel = bool(self.sel)
        dirty = [self._mag_bounds()]
        if self.drag:
            dirty.append(self._sel_bounds())
        self.mouse = pos
        if self.drag:
            d = self.drag
            if d["mode"] == "new":
                self.sel = QRect(d["origin"], ip).normalized().intersected(self.rect())
            elif d["mode"] == "move":
                o = d["rect"]
                dx, dy = ip.x() - d["origin"].x(), ip.y() - d["origin"].y()
                nx = min(max(o.left() + dx, 0), self.width() - o.width())
                ny = min(max(o.top() + dy, 0), self.height() - o.height())
                step_dx = nx - self.sel.left()
                step_dy = ny - self.sel.top()
                self.sel = QRect(nx, ny, o.width(), o.height())
                if (step_dx or step_dy) and self.annots:
                    self._shift_annots(step_dx, step_dy)
            elif d["mode"] == "resize":
                o, h = d["rect"], d["handle"]
                dx, dy = ip.x() - d["origin"].x(), ip.y() - d["origin"].y()
                l, t, r, b = o.left(), o.top(), o.right() + 1, o.bottom() + 1
                if "l" in h:
                    l += dx
                if "r" in h:
                    r += dx
                if "t" in h:
                    t += dy
                if "b" in h:
                    b += dy
                if l > r:
                    l, r = r, l
                if t > b:
                    t, b = b, t
                l, t = max(l, 0), max(t, 0)
                r, b = min(r, self.width()), min(b, self.height())
                self.sel = QRect(l, t, max(r - l, 1), max(b - t, 1))
        else:
            if not self.sel:
                pill, btn, _, _ = self._hint_rects()
                hov = btn.contains(pos)
                if hov != self._exit_hover:
                    self._exit_hover = hov
                    dirty.append(pill.adjusted(-2, -2, 2, 2))
                self.setCursor(Qt.CursorShape.PointingHandCursor if hov
                               else Qt.CursorShape.CrossCursor)
            else:
                self._update_cursor(ip)

        if bool(self.sel) != had_sel:
            self.update()                      # aparece/desaparece la pista superior
            return
        dirty.append(self._mag_bounds())
        if self.drag:
            dirty.append(self._sel_bounds())
        dirty = [r for r in dirty if r is not None]
        if dirty:                              # con selección y sin arrastre: nada
            u = dirty[0]
            for r in dirty[1:]:
                u = u.united(r)
            self.update(u.toAlignedRect())

    def _shift_annots(self, dx: float, dy: float):
        """Desplaza todas las anotaciones junto con el área seleccionada."""
        delta = QPointF(dx, dy)
        for a in self.annots:
            if "points" in a:
                a["points"] = [pt + delta for pt in a["points"]]
                a.pop("_poly", None)
            elif "p1" in a and "p2" in a:
                a["p1"] = a["p1"] + delta
                a["p2"] = a["p2"] + delta
                a.pop("_mosaic", None)
            elif "pos" in a:
                a["pos"] = a["pos"] + delta
        self._layer = None

    def mouseReleaseEvent(self, e):
        if e.button() != Qt.MouseButton.LeftButton:
            return
        if self.cur:
            a, self.cur = self.cur, None
            t = a["tool"]
            if t == "pen":
                keep = True
            elif t == "marker":
                keep = len(a["points"]) > 1
            else:
                keep = (a["p2"] - a["p1"]).manhattanLength() >= 3
            if keep:
                self.annots.append(a)
                self.redo_stack.clear()
                self._annots_changed()
        elif self.drag:
            mode = self.drag["mode"]
            self.drag = None
            if mode == "new" and not (self.sel and self.sel.width() > 3
                                      and self.sel.height() > 3):
                self.sel = None
            if self.sel:
                self._place_bar()
        self.update()

    def wheelEvent(self, e):
        if self.sel and self.tool != "select":
            step = 1 if e.angleDelta().y() > 0 else -1
            self.wslider.setValue(self.wslider.value() + step)

    def keyPressEvent(self, e):
        k = e.key()
        ctrl = bool(e.modifiers() & Qt.KeyboardModifier.ControlModifier)
        shift = bool(e.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        if k == Qt.Key.Key_Escape:
            self.cancel()
        elif ctrl and k == Qt.Key.Key_C:
            self.save_and_copy() if shift else self.copy()
        elif ctrl and k == Qt.Key.Key_S:
            self.save_as() if shift else self.save()
        elif ctrl and k == Qt.Key.Key_Z:
            self.redo() if shift else self.undo()
        elif ctrl and k == Qt.Key.Key_Y:
            self.redo()
        elif k in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.copy()
        elif not ctrl:
            t = e.text().lower()
            if t in TOOL_KEYS:
                self._set_tool(TOOL_KEYS[t])
            elif t == "b":
                if shift:
                    self._cycle_beautify_theme()
                else:
                    self.beautify_btn.toggle()
                    self._toggle_beautify()
            elif t == "f":
                self.pin_capture()
            elif t == "o":
                self.ocr_capture()
            elif t.isdigit() and 1 <= int(t) <= len(PALETTE):
                self._set_color(PALETTE[int(t) - 1])
            elif t == "-" or k == Qt.Key.Key_Minus:
                self.wslider.setValue(self.pen_w - 1)
            elif t == "+" or k in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
                self.wslider.setValue(self.pen_w + 1)

    # ---------- acciones ----------
    def _toggle_beautify(self):
        self.beautify = self.beautify_btn.isChecked()
        self.update()

    def _cycle_beautify_theme(self):
        self.beautify_theme = (self.beautify_theme + 1) % len(BEAUTIFY_THEMES)
        cfg().setValue("beautify_theme", self.beautify_theme)
        if not self.beautify:
            self.beautify = True
            self.beautify_btn.setChecked(True)
        self.update()

    def undo(self):
        self._commit_text()
        if self.annots:
            self.redo_stack.append(self.annots.pop())
            self._annots_changed()
            self.update()

    def redo(self):
        if self.redo_stack:
            self.annots.append(self.redo_stack.pop())
            self._annots_changed()
            self.update()

    def render_result(self, beautify: bool | None = None):
        """Recorta a resolución nativa y dibuja las anotaciones encima.
        Guarda estrictamente el área seleccionada, descartando lo que quede fuera."""
        self._commit_text()
        if not self.sel:
            return None
        s = self.sel
        dev = QRect(round(s.x() * self.dpr), round(s.y() * self.dpr),
                    round(s.width() * self.dpr), round(s.height() * self.dpr))
        dev = dev.intersected(QRect(0, 0, self.img.width(), self.img.height()))
        img = self.img.copy(dev)

        if self.annots:
            p = QPainter(img)
            p.setRenderHints(QPainter.RenderHint.Antialiasing |
                             QPainter.RenderHint.TextAntialiasing |
                             QPainter.RenderHint.SmoothPixmapTransform)
            p.scale(self.dpr, self.dpr)
            p.translate(-s.x(), -s.y())
            for a in self.annots:
                draw_annotation(p, a, self.img, self.dpr)
            p.end()
        use_b = self.beautify if beautify is None else beautify
        if use_b:
            img = apply_beautifier(img, self.dpr, self.beautify_theme)
        return img

    def pin_capture(self):
        """Deja la captura flotando siempre visible en pantalla (Pin to screen)."""
        img = self.render_result()
        if img is None or not self.sel:
            return
        gpos = self.mapToGlobal(self.sel.topLeft())
        self.pinned.emit(img, gpos, self.dpr)
        self.cancel()

    def ocr_capture(self):
        """Extrae el texto de la captura con OCR nativo y lo copia al portapapeles."""
        img = self.render_result(beautify=False)
        if img is None:
            return
        self.ocr_requested.emit(img)
        self.cancel()

    def copy(self):
        img = self.render_result()
        if img is None:
            return
        QApplication.clipboard().setImage(img)  # sin recompresión
        self.message.emit("Captura copiada al portapapeles")
        self.cancel()

    def save(self):
        """Guarda SIEMPRE en la carpeta configurada, sin preguntar."""
        img = self.render_result()
        if img is None:
            return
        folder = get_save_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.message.emit("No se pudo usar la carpeta de capturas. Elige otra.")
            d = pick_folder(self)
            self.activateWindow()
            self.setFocus()
            if not d:
                return
            folder = d
            self._refresh_folder_tips()
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError:
                self.message.emit("No se pudo crear la carpeta elegida")
                return
        path = folder / f"captura_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
        if img.save(str(path), "PNG"):  # PNG = sin pérdida
            self.saved.emit(str(path))
            self.cancel()
        else:
            self.message.emit("No se pudo guardar la captura")

    def save_and_copy(self):
        """Guarda en la carpeta configurada Y copia al portapapeles. (Ctrl+Shift+C)"""
        img = self.render_result()
        if img is None:
            return
        # Copiar primero (siempre funciona, independiente del guardado)
        QApplication.clipboard().setImage(img)
        folder = get_save_dir()
        try:
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"captura_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
            if img.save(str(path), "PNG"):
                self.saved.emit(str(path))
            else:
                self.message.emit("Copiada al portapapeles (no se pudo guardar)")
        except OSError:
            self.message.emit("Copiada al portapapeles (error al acceder a la carpeta)")
        self.cancel()

    def save_as(self):
        """Extra (Ctrl+Shift+S): elegir nombre/carpeta/formato solo esta vez."""
        img = self.render_result()
        if img is None:
            return
        default = get_save_dir() / f"captura_{datetime.now():%Y-%m-%d_%H-%M-%S}.png"
        fn, flt = QFileDialog.getSaveFileName(
            self, "Guardar captura como…", str(default),
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;BMP (*.bmp)")
        self.activateWindow()
        self.setFocus()
        if not fn:
            return
        ext = Path(fn).suffix.lower()
        if ext not in (".png", ".jpg", ".jpeg", ".bmp"):
            ext = ".jpg" if "JPEG" in flt else ".bmp" if "BMP" in flt else ".png"
            fn += ext
        fmt = {".png": "PNG", ".jpg": "JPG", ".jpeg": "JPG", ".bmp": "BMP"}[ext]
        ok = img.save(fn, fmt, 100) if fmt == "JPG" else img.save(fn, fmt)
        if ok:
            self.saved.emit(str(fn))
            self.cancel()
        else:
            self.message.emit("No se pudo guardar la captura")

    def cancel(self):
        if self._closing:
            return
        self._closing = True
        if self._width_dirty:
            cfg().setValue("width", self.pen_w)
        self.hide()
        self.closed.emit()
        self.deleteLater()


# ============================================================ atajos globales
class WinHotkeys(QAbstractNativeEventFilter):
    """Atajos globales con RegisterHotKey de Windows.

    A diferencia de un hook de teclado (pynput), Windows solo avisa a la app
    cuando se pulsa el atajo: costo cero en segundo plano, sin pasar cada tecla
    del sistema por Python. Además Windows consume la tecla, así que Impr Pant
    no dispara también la captura nativa."""
    WM_HOTKEY = 0x0312
    MOD_ALT, MOD_CONTROL, MOD_NOREPEAT = 0x0001, 0x0002, 0x4000

    def __init__(self, callback):
        super().__init__()
        import ctypes
        from ctypes import wintypes
        self._user32 = ctypes.windll.user32
        self._user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int,
                                                wintypes.UINT, wintypes.UINT]
        self._user32.RegisterHotKey.restype = wintypes.BOOL
        self._user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
        self._MSG = wintypes.MSG
        self._default_cb = callback
        self._callbacks: dict[int, object] = {}

    def register(self, hid: int, mods: int, vk: int, callback=None) -> bool:
        if hid in self._callbacks:
            return True
        if self._user32.RegisterHotKey(None, hid, mods | self.MOD_NOREPEAT, vk):
            self._callbacks[hid] = callback or self._default_cb
            return True
        return False

    def unregister(self, hid: int):
        if hid in self._callbacks:
            self._user32.UnregisterHotKey(None, hid)
            self._callbacks.pop(hid, None)

    def unregister_all(self):
        for hid in list(self._callbacks):
            self._user32.UnregisterHotKey(None, hid)
        self._callbacks.clear()

    def nativeEventFilter(self, event_type, message):
        if message and bytes(event_type) in (b"windows_dispatcher_MSG", b"windows_generic_MSG"):
            msg = self._MSG.from_address(int(message))
            if msg.message == self.WM_HOTKEY and msg.wParam in self._callbacks:
                cb = self._callbacks[msg.wParam]
                # Diferido: no abrir ventanas dentro del filtro de mensajes nativo
                QTimer.singleShot(0, cb)
                return True, 0
        return False, 0


def force_foreground_window(widget: QWidget):
    """Fuerza a Windows a entregar el foco de teclado al overlay aunque la app
    estuviera en segundo plano en la bandeja del sistema."""
    widget.raise_()
    widget.activateWindow()
    widget.setFocus()
    if sys.platform != "win32":
        return
    try:
        import ctypes
        u32 = ctypes.windll.user32
        k32 = ctypes.windll.kernel32
        hwnd = int(widget.winId())
        fg = u32.GetForegroundWindow()
        cur_tid = k32.GetCurrentThreadId()
        fg_tid = u32.GetWindowThreadProcessId(fg, None) if fg else 0
        attached = False
        if fg_tid and fg_tid != cur_tid:
            attached = bool(u32.AttachThreadInput(fg_tid, cur_tid, True))
        u32.BringWindowToTop(hwnd)
        u32.SetForegroundWindow(hwnd)
        u32.SetFocus(hwnd)
        if attached:
            u32.AttachThreadInput(fg_tid, cur_tid, False)
    except Exception:
        pass
    widget.activateWindow()
    widget.setFocus()


# ============================================================ aplicación
class App(QObject):
    hotkey = pyqtSignal()
    ocr_done = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.overlay = None
        self.pins: list[PinnedWindow] = []
        self._last_path: str | None = None   # última captura guardada (para abrir al clic)
        self.ocr_done.connect(self._on_ocr_done)
        self.tray = QSystemTrayIcon(make_icon())
        menu = QMenu()
        self.a_dir = QAction("", menu)
        self.a_dir.setEnabled(False)
        a1 = QAction("Capturar (Impr Pant)", menu)
        a1.triggered.connect(self.capture)
        a2 = QAction("Abrir carpeta de capturas", menu)
        a2.triggered.connect(self.open_folder)
        a3 = QAction("Cambiar carpeta de capturas…", menu)
        a3.triggered.connect(self.change_folder)
        a4 = QAction("Salir", menu)
        a4.triggered.connect(QApplication.quit)
        menu.addAction(a1)
        menu.addSeparator()
        menu.addAction(self.a_dir)
        menu.addAction(a2)
        menu.addAction(a3)
        menu.addSeparator()
        menu.addAction(a4)
        menu.aboutToShow.connect(self._refresh_menu)
        self.menu = menu
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(
            lambda r: self.capture() if r == QSystemTrayIcon.ActivationReason.Trigger else None)
        self._refresh_menu()
        self.tray.show()
        self.hotkey.connect(self.capture)
        self.tray.messageClicked.connect(self._open_last_saved)
        self._hk: WinHotkeys | None = None
        self._start_hotkeys()
        # Al arrancar Windows, explorer.exe puede tardar unos segundos en mostrar la bandeja;
        # re-verificamos y pre-calentamos iconos/fuentes para que la 1ª captura sea instantánea.
        QTimer.singleShot(400, self._prewarm_caches)
        QTimer.singleShot(2500, self._ensure_tray_and_hotkeys)
        QTimer.singleShot(6000, self._ensure_tray_and_hotkeys)

        s = cfg()
        if not s.value("welcomed", False, type=bool):
            s.setValue("welcomed", True)
            self.tray.showMessage(
                "ClearShot listo",
                f"Pulsa Impr Pant para capturar.\nSe guarda en: {get_save_dir()}")

    def _prewarm_caches(self):
        """Pre-renderiza iconos vectoriales y fuentes en segundo plano tras iniciar."""
        for key, _, _ in TOOLS:
            tool_icon(key)
        for key in ("undo", "redo", "beautify", "pin", "ocr", "folder",
                    "copy", "save", "close", "minus", "plus"):
            tool_icon(key)
        tool_icon("copy", "#ffffff")
        tool_icon("save", "#ffffff")
        tool_icon("close", "#fecaca")
        for sz in (11, 12, 13, 14, 16):
            _fm(sz, False)
            _fm(sz, True)

    def _ensure_tray_and_hotkeys(self):
        """Reintenta mostrar el icono de bandeja y registrar atajos si Windows aún
        estaba terminando de cargar el escritorio durante el arranque."""
        if not self.tray.isVisible():
            self.tray.show()
        if self._hk is not None:
            self._hk.register(1, 0, 0x2C)
            self._hk.register(2, WinHotkeys.MOD_CONTROL | WinHotkeys.MOD_ALT, ord("S"))

    def _refresh_menu(self):
        d = get_save_dir()
        text = str(d)
        if len(text) > 48:
            text = "…" + text[-47:]
        self.a_dir.setText(f"Carpeta: {text}")
        self.tray.setToolTip(f"ClearShot\nGuardando en: {d}")

    def _start_hotkeys(self):
        emit = self.hotkey.emit
        if sys.platform == "win32":
            self._hk = WinHotkeys(emit)
            QApplication.instance().installNativeEventFilter(self._hk)
            QApplication.instance().aboutToQuit.connect(self._hk.unregister_all)
            ok_prt = self._hk.register(1, 0, 0x2C)                     # Impr Pant
            ok_alt = self._hk.register(2, WinHotkeys.MOD_CONTROL | WinHotkeys.MOD_ALT,
                                       ord("S"))                         # Ctrl+Alt+S
            if not ok_prt or not ok_alt:
                # Reintentar tras 3 segundos (útil al encender el PC cuando el shell aún carga)
                QTimer.singleShot(3000, self._check_hotkeys_after_boot)
            return

        # Otros sistemas: atajos con pynput
        try:
            from pynput import keyboard
        except ImportError:
            self.tray.showMessage("ClearShot", "Instala pynput para usar atajos globales.")
            return
        try:
            self.listener = keyboard.GlobalHotKeys(
                {"<print_screen>": emit, "<ctrl>+<alt>+s": emit})
            self.listener.start()
        except Exception:
            pass

    def _check_hotkeys_after_boot(self):
        if self._hk is None:
            return
        ok_prt = self._hk.register(1, 0, 0x2C)
        ok_alt = self._hk.register(2, WinHotkeys.MOD_CONTROL | WinHotkeys.MOD_ALT, ord("S"))
        if not ok_prt and not ok_alt:
            self.tray.showMessage(
                "ClearShot", "No se pudieron registrar los atajos globales "
                "(otro programa los está usando). Captura desde el icono de la bandeja.")
        elif not ok_prt:
            self.tray.showMessage(
                "ClearShot", "Impr Pant está en uso por otro programa o por Recortes "
                "de Windows. Usa Ctrl+Alt+S (ver README → Solución de problemas).")

    def _on_escape_hotkey(self):
        """Garantiza que la tecla Esc cierre la captura el 100% de las veces,
        incluso si Windows no había entregado el foco de teclado al overlay."""
        if self.overlay is not None:
            e = self.overlay.text_edit
            if e is not None and e.text().strip():
                e.clear()
                self.overlay._commit_text()
                force_foreground_window(self.overlay)
            else:
                self.overlay.cancel()
        elif self._hk is not None:
            self._hk.unregister(3)

    def capture(self):
        if self.overlay is not None:
            force_foreground_window(self.overlay)
            return
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        pm = screen.grabWindow(0)  # resolución física completa
        self.overlay = Overlay(pm, screen)
        self.overlay.closed.connect(self._overlay_closed)
        self.overlay.message.connect(lambda m: self.tray.showMessage("ClearShot", m))
        self.overlay.saved.connect(self._on_saved)
        self.overlay.pinned.connect(self._on_pinned)
        self.overlay.ocr_requested.connect(self._start_ocr)
        if self._hk is not None:
            self._hk.register(3, 0, 0x1B, self._on_escape_hotkey)   # VK_ESCAPE mientras captura
        self.overlay.show()
        force_foreground_window(self.overlay)
        QTimer.singleShot(30, lambda: force_foreground_window(self.overlay) if self.overlay else None)

    def _overlay_closed(self):
        if self._hk is not None:
            self._hk.unregister(3)
        self.overlay = None
        self._refresh_menu()

    def _on_pinned(self, img: QImage, gpos: QPoint, dpr: float):
        pin = PinnedWindow(img, gpos, dpr)
        pin.closed.connect(lambda w: self.pins.remove(w) if w in self.pins else None)
        pin.saved.connect(self._on_saved)
        pin.message.connect(lambda m: self.tray.showMessage("ClearShot", m))
        pin.ocr_requested.connect(self._start_ocr)
        self.pins.append(pin)
        pin.show()
        pin.raise_()
        pin.activateWindow()

    def _start_ocr(self, img: QImage):
        def worker():
            txt = run_windows_ocr(img)
            self.ocr_done.emit(txt)
        threading.Thread(target=worker, daemon=True).start()

    def _on_ocr_done(self, txt: str):
        if txt:
            QApplication.clipboard().setText(txt)
            preview = txt if len(txt) <= 120 else txt[:117] + "…"
            self.tray.showMessage("ClearShot — Texto copiado (OCR)", preview)
        else:
            self.tray.showMessage("ClearShot — OCR",
                                  "No se detectó texto reconocible en el área seleccionada.")

    def _on_saved(self, path: str):
        """Muestra notificación clickeable al guardar una captura."""
        self._last_path = path
        name = Path(path).name
        self.tray.showMessage(
            "ClearShot — Guardada",
            f"{name}\nClic para abrir",
            QSystemTrayIcon.MessageIcon.Information,
            4000)

    def _open_last_saved(self):
        """Abre la última captura guardada al hacer clic en la notificación."""
        if self._last_path and Path(self._last_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_path))

    def open_folder(self):
        d = get_save_dir()
        d.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(d)))

    def change_folder(self):
        d = pick_folder(None)
        if d:
            self._refresh_menu()
            self.tray.showMessage("ClearShot", f"Las capturas se guardarán en:\n{d}")


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            # Registrar identificador único de aplicación para Windows (Start Menu, barra de tareas y notificaciones)
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("IMicit.ClearShot.App.1")
            user32 = ctypes.windll.user32
            user32.SetProcessDpiAwarenessContext.argtypes = [ctypes.c_void_p]
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))  # Per-Monitor V2
        except Exception:
            try:
                import ctypes
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-Monitor
            except Exception:
                pass

    app = QApplication(sys.argv)
    if "--make-icon" in sys.argv:  # usado por instalar.bat para el .exe
        out = sys.argv[sys.argv.index("--make-icon") + 1]
        draw_icon(256).save(out)
        return
    # Evita abrir dos copias a la vez: en Windows usamos un Mutex del kernel en RAM
    # (se libera solo al apagar o reiniciar el PC, sin dejar archivos .lock huérfanos en disco).
    _win_mutex = None
    lock = None
    if sys.platform == "win32":
        import ctypes
        # Limpiar cualquier archivo .lock antiguo de versiones anteriores
        try:
            old_lock = Path(QDir.temp().filePath("clearshot.lock"))
            if old_lock.exists():
                old_lock.unlink()
        except OSError:
            pass
        _win_mutex = ctypes.windll.kernel32.CreateMutexW(
            None, False, "Local\\ClearShot_SingleInstance_Mutex")
        if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            sys.exit(0)
    else:
        lock = QLockFile(QDir.temp().filePath("clearshot.lock"))
        lock.setStaleLockTime(0)
        if not lock.tryLock(100):
            sys.exit(0)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(make_icon())
    app.aboutToQuit.connect(lambda: cfg().sync())
    clearshot = App()  # noqa: F841 (mantener referencia)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
