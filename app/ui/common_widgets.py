import numpy as np
from PySide6.QtCore import Signal, QRectF, QPointF, QSizeF, Qt
from PySide6.QtGui import QPainter, QColor, QPen
from PySide6.QtWidgets import QWidget, QSizePolicy, QGraphicsView, QGraphicsObject, QGraphicsItem

# ---------------------------------------------------
# RangeSlider: 2つのハンドルで範囲を指定するカスタムウィジェット
# ---------------------------------------------------
class RangeSlider(QWidget):
    valueChanged = Signal(int, int)

    def __init__(self, parent=None, min_value=0, max_value=255):
        super().__init__(parent)
        self.min_value = min_value
        self.max_value = max_value
        self.left_value = min_value
        self.right_value = max_value
        self.bar_height = 20
        self.handle_radius = 10
        self.margin = self.handle_radius  # 左右の余白
        self.setMinimumHeight(self.bar_height + 2 * self.handle_radius)
        self.setMaximumHeight(self.bar_height + 2 * self.handle_radius)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.active_handle = None
        self.setMouseTracking(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        width = self.width() - 2 * self.margin
        height = self.bar_height
        y = (self.height() - height) / 2

        # 背景バー
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(200, 200, 200))
        painter.drawRect(QRectF(self.margin, y, width, height))

        # 選択範囲
        left = self.value_to_position(self.left_value)
        right = self.value_to_position(self.right_value)
        painter.setBrush(QColor(100, 100, 250))
        painter.drawRect(QRectF(left, y, right - left, height))

        # 左ハンドル
        painter.setBrush(QColor(150, 150, 250))
        painter.drawEllipse(QRectF(left - self.handle_radius, y + (height / 2) - self.handle_radius,
                                   2 * self.handle_radius, 2 * self.handle_radius))
        # 右ハンドル
        painter.setBrush(QColor(150, 150, 250))
        painter.drawEllipse(QRectF(right - self.handle_radius, y + (height / 2) - self.handle_radius,
                                   2 * self.handle_radius, 2 * self.handle_radius))

    def mousePressEvent(self, event):
        pos = event.pos()
        left = self.value_to_position(self.left_value)
        right = self.value_to_position(self.right_value)
        left_handle_rect = QRectF(left - self.handle_radius, (self.height() - 2 * self.handle_radius) / 2,
                                  2 * self.handle_radius, 2 * self.handle_radius)
        right_handle_rect = QRectF(right - self.handle_radius, (self.height() - 2 * self.handle_radius) / 2,
                                   2 * self.handle_radius, 2 * self.handle_radius)
        if left_handle_rect.contains(pos):
            self.active_handle = 'left'
        elif right_handle_rect.contains(pos):
            self.active_handle = 'right'
        else:
            self.active_handle = None

    def mouseMoveEvent(self, event):
        if self.active_handle is not None:
            pos = event.pos().x()
            new_value = self.position_to_value(pos)
            if self.active_handle == 'left':
                if new_value < self.min_value:
                    new_value = self.min_value
                if new_value > self.right_value:
                    new_value = self.right_value
                if new_value != self.left_value:
                    self.left_value = new_value
                    self.valueChanged.emit(self.left_value, self.right_value)
                    self.update()
            elif self.active_handle == 'right':
                if new_value > self.max_value:
                    new_value = self.max_value
                if new_value < self.left_value:
                    new_value = self.left_value
                if new_value != self.right_value:
                    self.right_value = new_value
                    self.valueChanged.emit(self.left_value, self.right_value)
                    self.update()

    def mouseReleaseEvent(self, event):
        self.active_handle = None

    def value_to_position(self, value):
        ratio = (value - self.min_value) / (self.max_value - self.min_value)
        return self.margin + ratio * (self.width() - 2 * self.margin)

    def position_to_value(self, pos):
        ratio = (pos - self.margin) / (self.width() - 2 * self.margin)
        ratio = max(0.0, min(1.0, ratio))
        return int(ratio * (self.max_value - self.min_value) + self.min_value)

# ---------------------------------------------------
# ResizableGraphicsRectItem: マウス操作でリサイズ可能な矩形アイテム
# ---------------------------------------------------
class ResizableGraphicsRectItem(QGraphicsObject):
    positionChanged = Signal(QPointF)
    sizeChanged = Signal(QSizeF)
    HANDLE_SIZE = 8.0  # ハンドルのサイズ

    def __init__(self, rect: QRectF, color: QColor = QColor(0, 255, 0), parent: QGraphicsItem = None):
        super().__init__(parent)
        self.rect = rect
        self.setFlags(QGraphicsItem.ItemIsMovable | QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.pen = QPen(color, 2, Qt.SolidLine)
        # 半透明のブラシ設定
        self.brush = QColor(color.red(), color.green(), color.blue(), 50)
        self.handles = {}
        self.handle_selected = None
        self.update_handles()

    def boundingRect(self) -> QRectF:
        adjust = self.HANDLE_SIZE / 2
        return self.rect.adjusted(-adjust, -adjust, adjust, adjust)

    def paint(self, painter: QPainter, option, widget=None):
        pen = self.pen
        if self.isSelected():
            pen.setStyle(Qt.DashLine)
        else:
            pen.setStyle(Qt.SolidLine)
        painter.setPen(pen)
        painter.setBrush(self.brush)
        painter.drawRect(self.rect)
        # 各ハンドルを描画
        for handle_rect in self.handles.values():
            painter.drawRect(handle_rect)

    def update_handles(self):
        rect = self.rect
        self.handles = {
            "top_left": QRectF(rect.left() - self.HANDLE_SIZE / 2, rect.top() - self.HANDLE_SIZE / 2,
                               self.HANDLE_SIZE, self.HANDLE_SIZE),
            "top_right": QRectF(rect.right() - self.HANDLE_SIZE / 2, rect.top() - self.HANDLE_SIZE / 2,
                                self.HANDLE_SIZE, self.HANDLE_SIZE),
            "bottom_left": QRectF(rect.left() - self.HANDLE_SIZE / 2, rect.bottom() - self.HANDLE_SIZE / 2,
                                  self.HANDLE_SIZE, self.HANDLE_SIZE),
            "bottom_right": QRectF(rect.right() - self.HANDLE_SIZE / 2, rect.bottom() - self.HANDLE_SIZE / 2,
                                   self.HANDLE_SIZE, self.HANDLE_SIZE),
            "top": QRectF(rect.center().x() - self.HANDLE_SIZE / 2, rect.top() - self.HANDLE_SIZE / 2,
                          self.HANDLE_SIZE, self.HANDLE_SIZE),
            "bottom": QRectF(rect.center().x() - self.HANDLE_SIZE / 2, rect.bottom() - self.HANDLE_SIZE / 2,
                             self.HANDLE_SIZE, self.HANDLE_SIZE),
            "left": QRectF(rect.left() - self.HANDLE_SIZE / 2, rect.center().y() - self.HANDLE_SIZE / 2,
                           self.HANDLE_SIZE, self.HANDLE_SIZE),
            "right": QRectF(rect.right() - self.HANDLE_SIZE / 2, rect.center().y() - self.HANDLE_SIZE / 2,
                            self.HANDLE_SIZE, self.HANDLE_SIZE),
        }

    def hoverMoveEvent(self, event):
        handle = self.get_handle_at(event.pos())
        cursor = Qt.SizeAllCursor
        if handle:
            if handle in ("top_left", "bottom_right"):
                cursor = Qt.SizeFDiagCursor
            elif handle in ("top_right", "bottom_left"):
                cursor = Qt.SizeBDiagCursor
            elif handle in ("top", "bottom"):
                cursor = Qt.SizeVerCursor
            elif handle in ("left", "right"):
                cursor = Qt.SizeHorCursor
        else:
            cursor = Qt.SizeAllCursor
        self.setCursor(cursor)
        super().hoverMoveEvent(event)

    def mousePressEvent(self, event):
        self.handle_selected = self.get_handle_at(event.pos())
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.handle_selected:
            self.resize_rect(event.pos())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.handle_selected = None
        super().mouseReleaseEvent(event)

    def get_handle_at(self, pos: QPointF):
        for handle, rect in self.handles.items():
            if rect.contains(pos):
                return handle
        return None

    def resize_rect(self, pos: QPointF):
        rect = self.rect
        if self.handle_selected == "top_left":
            new_rect = QRectF(pos, rect.bottomRight()).normalized()
        elif self.handle_selected == "top_right":
            new_rect = QRectF(QPointF(rect.left(), pos.y()), QPointF(pos.x(), rect.bottom())).normalized()
        elif self.handle_selected == "bottom_left":
            new_rect = QRectF(QPointF(pos.x(), rect.top()), QPointF(rect.right(), pos.y())).normalized()
        elif self.handle_selected == "bottom_right":
            new_rect = QRectF(rect.topLeft(), pos).normalized()
        elif self.handle_selected == "top":
            new_rect = QRectF(rect.left(), pos.y(), rect.width(), rect.bottom() - pos.y()).normalized()
        elif self.handle_selected == "bottom":
            new_rect = QRectF(rect.left(), rect.top(), rect.width(), pos.y() - rect.top()).normalized()
        elif self.handle_selected == "left":
            new_rect = QRectF(pos.x(), rect.top(), rect.right() - pos.x(), rect.height()).normalized()
        elif self.handle_selected == "right":
            new_rect = QRectF(rect.left(), rect.top(), pos.x() - rect.left(), rect.height()).normalized()
        else:
            return

        # 最小サイズの設定（例: 20x20）
        min_width = 20
        min_height = 20
        if new_rect.width() < min_width:
            new_rect.setWidth(min_width)
        if new_rect.height() < min_height:
            new_rect.setHeight(min_height)

        self.rect = new_rect
        self.update_handles()
        self.update()
        self.positionChanged.emit(self.pos())
        self.sizeChanged.emit(self.rect.size())

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            self.update_handles()
            self.positionChanged.emit(self.pos())
        return super().itemChange(change, value)

    def get_rect(self) -> QRectF:
        return self.rect

# ---------------------------------------------------
# GraphicsView: ズーム機能を持つカスタムQGraphicsView
# ---------------------------------------------------
class GraphicsView(QGraphicsView):
    def __init__(self, scene, parent=None):
        super().__init__(scene, parent)
        self.setRenderHint(QPainter.Antialiasing, True)
        self.setRenderHint(QPainter.SmoothPixmapTransform, True)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.zoom_factor = 1.15
        self.current_zoom = 1.0
        self.max_zoom = 5.0
        self.min_zoom = 0.2
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            zoom = self.zoom_factor
        else:
            zoom = 1 / self.zoom_factor
        new_zoom = self.current_zoom * zoom
        if new_zoom < self.min_zoom or new_zoom > self.max_zoom:
            return
        self.scale(zoom, zoom)
        self.current_zoom = new_zoom

    def reset_zoom(self):
        self.resetTransform()
        self.fitInView(self.sceneRect(), Qt.KeepAspectRatio)
        self.current_zoom = 1.0
