from PyQt5.QtWidgets import QGraphicsObject, QGraphicsItem
from PyQt5.QtCore import Qt, pyqtSignal


class BaseDraggableItem(QGraphicsObject):
    """Base class for draggable graphics items with move tracking."""

    item_moved = pyqtSignal(QGraphicsItem)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._has_moved = False

    def mousePressEvent(self, event):
        self._has_moved = False
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and self._has_moved:
            self.item_moved.emit(self)
            self._has_moved = False
