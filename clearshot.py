"""
ClearShot - Capturador de pantalla estilo Lightshot, SIN pérdida de calidad.

- Captura a la resolución física real de la pantalla (respeta escalado HiDPI).
- Guarda en PNG (lossless) y copia al portapapeles sin recomprimir.
- Guardar va SIEMPRE a la carpeta configurada (por defecto Imágenes\\ClearShot).
  Se cambia desde la bandeja o desde el botón de carpeta de la barra.
- Herramientas: área, lápiz, línea, flecha, rectángulo, elipse, resaltador,
  texto, números de paso y pixelado para ocultar datos.
- Atajo global: Impr Pant (o Ctrl+Alt+S). Corre en la bandeja del sistema.
"""
import math
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import (QDir, QLockFile, QObject, QPoint, QPointF, QRect,
                          QRectF, QSettings, QSize, QStandardPaths, Qt, QUrl,
                          pyqtSignal)
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
QLabel {{ color:#9aa0b0; font-size:11px; background:transparent; }}
QFrame#sep {{ background:#343845; border:none; }}
QSlider::groove:horizontal {{ height:4px; background:#343845; border-radius:2px; }}
QSlider::sub-page:horizontal {{ background:{ACCENT}; border-radius:2px; }}
QSlider::handle:horizontal {{ background:white; width:14px; height:14px;
                              margin:-5px 0; border-radius:7px; }}
"""


# ============================================================ configuración
def cfg() -> QSettings:
    return QSettings("ClearShot", "ClearShot")


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


def tool_icon(key: str, color: str = "#e8e8ee") -> QIcon:
    """Iconos de la barra, dibujados en vectorial (nítidos en HiDPI)."""
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
    p.end()
    return QIcon(pm)


# ============================================================ anotaciones
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
    sub = img.copy(src)
    block = max(6, round(9 * dpr))
    small = sub.scaled(max(1, src.width() // block), max(1, src.height() // block),
                       Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.SmoothTransformation)
    big = small.scaled(src.width(), src.height(),
                       Qt.AspectRatioMode.IgnoreAspectRatio,
                       Qt.TransformationMode.FastTransformation)
    dest = QRectF(src.x() / dpr, src.y() / dpr, src.width() / dpr, src.height() / dpr)
    p.drawImage(dest, big)


def draw_annotation(p: QPainter, a: dict, img: QImage, dpr: float):
    """Dibuja una anotación. Las coordenadas son lógicas (como el overlay)."""
    t = a["tool"]
    w = a.get("width", 3)
    p.save()
    try:
        if t == "mosaic":
            _draw_mosaic(p, a, img, dpr)
        elif t == "text":
            f = QFont("Segoe UI")
            f.setPixelSize(a["size"])
            f.setBold(True)
            p.setFont(f)
            p.setPen(QColor(a["color"]))
            fm = QFontMetrics(f)
            p.drawText(QRectF(a["pos"].x() + 3, a["pos"].y() + 3, 4000, fm.height() + 8),
                       Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, a["text"])
        elif t == "step":
            col = QColor(a["color"])
            r = 11 + w * 1.2
            p.setPen(QPen(QColor(255, 255, 255, 200), 1.5))
            p.setBrush(col)
            p.drawEllipse(a["pos"], r, r)
            lum = 0.299 * col.red() + 0.587 * col.green() + 0.114 * col.blue()
            f = QFont("Segoe UI")
            f.setPixelSize(max(9, int(r * 1.1)))
            f.setBold(True)
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
                p.drawPolyline(QPolygonF(a["points"]))
        else:
            p.setPen(_pen(a["color"], w))
            p.setBrush(Qt.BrushStyle.NoBrush)
            if t == "pen":
                pts = a["points"]
                if len(pts) == 1:
                    p.drawPoint(pts[0])
                else:
                    p.drawPolyline(QPolygonF(pts))
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
    def keyPressEvent(self, e):
        if e.key() == Qt.Key.Key_Escape:   # cancela el texto sin cerrar la captura
            self.clear()
            self.clearFocus()
            e.accept()
            return
        super().keyPressEvent(e)


def _sep() -> QFrame:
    f = QFrame()
    f.setObjectName("sep")
    f.setFixedSize(1, 22)
    return f


# ============================================================ overlay
class Overlay(QWidget):
    closed = pyqtSignal()
    message = pyqtSignal(str)

    def __init__(self, pixmap: QPixmap, screen):
        super().__init__()
        self.pm = pixmap                       # píxeles físicos (calidad completa)
        self.dpr = pixmap.devicePixelRatio()
        self.img = pixmap.toImage()            # copia en píxeles físicos para recortes
        self.img.setDevicePixelRatio(1.0)
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
        self.mouse = QPointF(QCursor.pos() - screen.geometry().topLeft())

        self._build_toolbar()

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
        self.copy_btn.setToolTip("Copiar al portapapeles  (Enter / Ctrl+C)")
        close = self._tbtn("close", "Cancelar  (Esc)")
        close.clicked.connect(self.cancel)
        row1.addWidget(close)
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
        self.wslider.setFixedWidth(120)
        self.wslider.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.wslider.setToolTip("Grosor del trazo (también con la rueda del ratón)")
        self.wslider.valueChanged.connect(self._set_width)
        r2.addWidget(self.wslider)
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
        self._refresh_undo()
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
        self.pen_w = int(v)
        self.wlabel.setText(f"{self.pen_w} px")
        self.dot.set(self.pen_color, self.pen_w)
        s = cfg()
        s.setValue("width", self.pen_w)

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
        self.setCursor(cur)

    # ---------- dibujo ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.drawPixmap(self.rect(), self.pm)
        p.fillRect(self.rect(), QColor(0, 0, 0, 120))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.sel:
            s = self.sel
            src = QRectF(s.x() * self.dpr, s.y() * self.dpr,
                         s.width() * self.dpr, s.height() * self.dpr)
            p.drawPixmap(QRectF(s), self.pm, src)
            p.save()
            p.setClipRect(s)
            for a in self.annots + ([self.cur] if self.cur else []):
                draw_annotation(p, a, self.img, self.dpr)
            p.restore()

            p.setPen(QPen(QColor(ACCENT), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(QRectF(s))
            if not self.cur:
                p.setBrush(QColor("white"))
                for x, y in self._handle_points().values():
                    p.drawRoundedRect(QRectF(x - 4, y - 4, 8, 8), 2, 2)

            f = QFont("Segoe UI")
            f.setPixelSize(12)
            p.setFont(f)
            label = f"{round(s.width() * self.dpr)} × {round(s.height() * self.dpr)} px"
            lw = QFontMetrics(f).horizontalAdvance(label) + 16
            ly = s.top() - 26 if s.top() > 30 else s.top() + 6
            lx = s.left() if s.top() > 30 else s.left() + 6
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(20, 22, 28, 220))
            p.drawRoundedRect(QRectF(lx, ly, lw, 20), 6, 6)
            p.setPen(QColor("white"))
            p.drawText(QRectF(lx, ly, lw, 20), Qt.AlignmentFlag.AlignCenter, label)
        else:
            self._draw_hint(p)

        d = self.drag
        if self.sel is None or (d and d["mode"] in ("new", "resize")):
            self._draw_magnifier(p)

    def _draw_hint(self, p: QPainter):
        f = QFont("Segoe UI")
        f.setPixelSize(14)
        p.setFont(f)
        text = "Arrastra para seleccionar el área   ·   Esc para salir"
        w = QFontMetrics(f).horizontalAdvance(text) + 32
        r = QRectF((self.width() - w) / 2, 28, w, 36)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 22, 28, 225))
        p.drawRoundedRect(r, 18, 18)
        p.setPen(QColor("white"))
        p.drawText(r, Qt.AlignmentFlag.AlignCenter, text)

    def _draw_magnifier(self, p: QPainter):
        pos = self.mouse
        size, zoom, info_h = 120, 8, 40
        side = size / zoom * self.dpr
        cx, cy = pos.x() * self.dpr, pos.y() * self.dpr
        src = QRectF(cx - side / 2, cy - side / 2, side, side)
        ox, oy = pos.x() + 24, pos.y() + 24
        if ox + size + 4 > self.width():
            ox = pos.x() - 24 - size
        if oy + size + info_h + 8 > self.height():
            oy = pos.y() - 24 - size - info_h - 8
        rect = QRectF(ox, oy, size, size)

        p.save()
        path = QPainterPath()
        path.addRoundedRect(rect, 10, 10)
        p.setClipPath(path)
        p.fillRect(rect, QColor(0, 0, 0))
        p.drawPixmap(rect, self.pm, src)
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
        panel = QRectF(ox, oy + size + 6, size, info_h)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(20, 22, 28, 235))
        p.drawRoundedRect(panel, 8, 8)
        f = QFont("Segoe UI")
        f.setPixelSize(12)
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
        f = QFont("Segoe UI")
        f.setPixelSize(self.text_size)
        f.setBold(True)
        fm = QFontMetrics(f)
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
        self.text_edit = e
        e.show()
        e.setFocus()

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
            self._refresh_undo()
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
                self._refresh_undo()
                self.update()
            else:
                self.cancel()
            return
        if e.button() != Qt.MouseButton.LeftButton:
            return

        if self.sel:
            h = self._hit_handle(ip)
            if h:
                self.bar.hide()
                self.drag = {"mode": "resize", "handle": h, "origin": ip,
                             "rect": QRect(self.sel)}
                self.update()
                return
            if self.sel.contains(ip):
                if self.tool == "select":
                    self.bar.hide()
                    self.drag = {"mode": "move", "origin": ip, "rect": QRect(self.sel)}
                elif self.tool == "text":
                    self._start_text(pos)
                elif self.tool == "step":
                    n = sum(1 for a in self.annots if a["tool"] == "step") + 1
                    self.annots.append({"tool": "step", "color": self.pen_color,
                                        "width": self.pen_w, "pos": pos, "n": n})
                    self.redo_stack.clear()
                    self._refresh_undo()
                elif self.tool == "pen" or self.tool == "marker":
                    self.cur = {"tool": self.tool, "color": self.pen_color,
                                "width": self.pen_w, "points": [pos]}
                else:
                    self.cur = {"tool": self.tool, "color": self.pen_color,
                                "width": self.pen_w, "p1": pos, "p2": pos}
                self.update()
                return

        # clic fuera: nueva selección
        self.bar.hide()
        self.annots.clear()
        self.redo_stack.clear()
        self._refresh_undo()
        self.sel = None
        self.drag = {"mode": "new", "origin": ip}
        self.update()

    def mouseMoveEvent(self, e):
        pos = e.position()
        ip = pos.toPoint()
        self.mouse = pos
        if self.cur:
            c = self.cur
            if c["tool"] in ("pen", "marker"):
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
        elif self.drag:
            d = self.drag
            if d["mode"] == "new":
                self.sel = QRect(d["origin"], ip).normalized().intersected(self.rect())
            elif d["mode"] == "move":
                o = d["rect"]
                dx, dy = ip.x() - d["origin"].x(), ip.y() - d["origin"].y()
                nx = min(max(o.left() + dx, 0), self.width() - o.width())
                ny = min(max(o.top() + dy, 0), self.height() - o.height())
                self.sel = QRect(nx, ny, o.width(), o.height())
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
            self._update_cursor(ip)
        self.update()

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
                self._refresh_undo()
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
            self.copy()
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
            elif t.isdigit() and 1 <= int(t) <= len(PALETTE):
                self._set_color(PALETTE[int(t) - 1])

    # ---------- acciones ----------
    def undo(self):
        self._commit_text()
        if self.annots:
            self.redo_stack.append(self.annots.pop())
            self._refresh_undo()
            self.update()

    def redo(self):
        if self.redo_stack:
            self.annots.append(self.redo_stack.pop())
            self._refresh_undo()
            self.update()

    def render_result(self):
        """Recorta a resolución nativa y dibuja las anotaciones encima."""
        self._commit_text()
        if not self.sel:
            return None
        s = self.sel
        dev = QRect(round(s.x() * self.dpr), round(s.y() * self.dpr),
                    round(s.width() * self.dpr), round(s.height() * self.dpr))
        img = self.img.copy(dev)
        if self.annots:
            p = QPainter(img)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.scale(self.dpr, self.dpr)
            p.translate(-s.x(), -s.y())
            for a in self.annots:
                draw_annotation(p, a, self.img, self.dpr)
            p.end()
        return img

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
            self.message.emit(f"Guardada en: {path}")
            self.cancel()
        else:
            self.message.emit("No se pudo guardar la captura")

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
            self.message.emit(f"Guardada en: {fn}")
            self.cancel()
        else:
            self.message.emit("No se pudo guardar la captura")

    def cancel(self):
        if self._closing:
            return
        self._closing = True
        self.hide()
        self.closed.emit()
        self.deleteLater()


# ============================================================ aplicación
class App(QObject):
    hotkey = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.overlay = None
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
        self._start_hotkeys()

        s = cfg()
        if not s.value("welcomed", False, type=bool):
            s.setValue("welcomed", True)
            self.tray.showMessage(
                "ClearShot listo",
                f"Pulsa Impr Pant para capturar.\nSe guarda en: {get_save_dir()}")

    def _refresh_menu(self):
        d = get_save_dir()
        text = str(d)
        if len(text) > 48:
            text = "…" + text[-47:]
        self.a_dir.setText(f"Carpeta: {text}")
        self.tray.setToolTip(f"ClearShot\nGuardando en: {d}")

    def _start_hotkeys(self):
        try:
            from pynput import keyboard
        except ImportError:
            self.tray.showMessage("ClearShot", "Instala pynput para usar atajos globales.")
            return
        emit = self.hotkey.emit
        for mapping in ({"<print_screen>": emit, "<ctrl>+<alt>+s": emit},
                        {"<ctrl>+<alt>+s": emit}):
            try:
                self.listener = keyboard.GlobalHotKeys(mapping)
                self.listener.start()
                break
            except Exception:
                continue

    def capture(self):
        if self.overlay is not None:
            return
        screen = QGuiApplication.screenAt(QCursor.pos()) or QGuiApplication.primaryScreen()
        pm = screen.grabWindow(0)  # resolución física completa
        self.overlay = Overlay(pm, screen)
        self.overlay.closed.connect(self._overlay_closed)
        self.overlay.message.connect(lambda m: self.tray.showMessage("ClearShot", m))
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()
        self.overlay.setFocus()

    def _overlay_closed(self):
        self.overlay = None
        self._refresh_menu()

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
    app = QApplication(sys.argv)
    if "--make-icon" in sys.argv:  # usado por instalar.bat para el .exe
        out = sys.argv[sys.argv.index("--make-icon") + 1]
        draw_icon(256).save(out)
        return
    # Evita abrir dos copias a la vez (dos atajos globales)
    lock = QLockFile(QDir.temp().filePath("clearshot.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(100):
        sys.exit(0)
    app.setQuitOnLastWindowClosed(False)
    app.setWindowIcon(make_icon())
    clearshot = App()  # noqa: F841 (mantener referencia)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
