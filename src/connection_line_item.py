from PyQt5.QtWidgets import QGraphicsLineItem, QGraphicsItem
from PyQt5.QtGui import QPen, QColor
from PyQt5.QtCore import Qt, pyqtSignal

from .info_area_item import InfoAreaItem
from . import utils

class ConnectionLineItem(QGraphicsLineItem):
    """Graphics item representing a connection line between two info areas."""

    item_selected = pyqtSignal(QGraphicsItem)
    properties_changed = pyqtSignal(QGraphicsItem)

    def __init__(self, line_config, item_map, parent=None):
        super().__init__(parent)
        self.config_data = line_config
        self.item_map = item_map
        self.setFlags(QGraphicsItem.ItemIsSelectable)
        self.setZValue(self.config_data.get('z_index', utils.Z_VALUE_INFO_RECT))
        self._update_pen()
        self.update_position()

    def _update_pen(self):
        color = QColor(self.config_data.get('line_color', '#00ffff'))
        thickness = self.config_data.get('thickness', 2)
        self.setPen(QPen(color, thickness))

    def update_position(self):
        src_item = self.item_map.get(self.config_data.get('source'))
        dst_item = self.item_map.get(self.config_data.get('destination'))
        if isinstance(src_item, InfoAreaItem) and isinstance(dst_item, InfoAreaItem):
            src_center = src_item.mapToScene(src_item.boundingRect().center())
            dst_center = dst_item.mapToScene(dst_item.boundingRect().center())
            self.setLine(src_center.x(), src_center.y(), dst_center.x(), dst_center.y())

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.item_selected.emit(self)
        super().mousePressEvent(event)

    def set_thickness(self, value):
        self.config_data['thickness'] = value
        self._update_pen()
        self.properties_changed.emit(self)

    def set_line_color(self, color_str):
        self.config_data['line_color'] = color_str
        self._update_pen()
        self.properties_changed.emit(self)

    def set_z_index(self, z):
        self.config_data['z_index'] = z
        self.setZValue(z)
        self.properties_changed.emit(self)
