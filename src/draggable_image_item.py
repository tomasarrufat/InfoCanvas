from PyQt5.QtWidgets import QGraphicsObject, QGraphicsItem, QApplication
from PyQt5.QtCore import Qt, QRectF, pyqtSignal
from PyQt5.QtGui import QPixmap # Added QPixmap as it's likely used

from . import utils


class DraggableImageItem(QGraphicsObject):
    item_selected = pyqtSignal(QGraphicsItem)
    item_moved = pyqtSignal(QGraphicsItem)

    def __init__(self, pixmap, config_data, parent_item=None):
        super().__init__(parent_item)
        self._pixmap = pixmap
        self.config_data = config_data
        self.setFlags(QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.initial_pos = self.pos()
        # Set initial stacking value
        self.setZValue(self.config_data.get('z_index', utils.Z_VALUE_IMAGE))

    def pixmap(self):
        return self._pixmap

    def setPixmap(self, pixmap):
        self.prepareGeometryChange()
        self._pixmap = pixmap
        self.update()

    def boundingRect(self):
        if self._pixmap.isNull():
            return QRectF()
        return QRectF(0, 0, self._pixmap.width(), self._pixmap.height())

    def paint(self, painter, option, widget=None):
        if not self._pixmap.isNull():
            painter.drawPixmap(0, 0, self._pixmap)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            current_scale = self.config_data.get('scale', 1.0)
            original_width = self.config_data.get('original_width', self._pixmap.width())
            original_height = self.config_data.get('original_height', self._pixmap.height())
            scaled_width_at_current_scale = original_width * current_scale
            scaled_height_at_current_scale = original_height * current_scale
            new_center_x = value.x() + scaled_width_at_current_scale / 2
            new_center_y = value.y() + scaled_height_at_current_scale / 2
            self.config_data['center_x'] = new_center_x
            self.config_data['center_y'] = new_center_y
            self.item_moved.emit(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.item_selected.emit(self)
            self.initial_pos = self.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        scene = self.scene()
        if scene and hasattr(scene, 'parent_window') and scene.parent_window.current_mode == "edit":
            QApplication.setOverrideCursor(Qt.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        QApplication.restoreOverrideCursor()
        super().hoverLeaveEvent(event)
