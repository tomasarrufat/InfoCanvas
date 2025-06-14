from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem, QApplication

from .base_draggable_item import BaseDraggableItem
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QRect
from PyQt5.QtGui import QColor, QBrush, QPen, QCursor, QTextOption

from . import utils


class InfoRectangleItem(BaseDraggableItem):
    item_selected = pyqtSignal(QGraphicsItem)
    properties_changed = pyqtSignal(QGraphicsItem)

    RESIZE_MARGIN = 8
    MIN_WIDTH = 20
    MIN_HEIGHT = 20

    class ResizeHandle:
        NONE = 0
        TOP_LEFT = 1
        TOP = 2
        TOP_RIGHT = 3
        RIGHT = 4
        BOTTOM_RIGHT = 5
        BOTTOM = 6
        BOTTOM_LEFT = 7
        LEFT = 8

    def __init__(self, rect_config, parent_item=None):
        super().__init__(parent_item)
        self.config_data = rect_config
        self._style_config_ref = None
        self._w = self.config_data.get('width', 100)
        self._h = self.config_data.get('height', 50)
        self._pen = QPen(Qt.NoPen)
        self._brush = QBrush(Qt.NoBrush)

        # Formatting options
        text_format_defaults = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
        self.vertical_alignment = self.config_data.get('vertical_alignment', text_format_defaults['vertical_alignment'])
        self.horizontal_alignment = self.config_data.get('horizontal_alignment', text_format_defaults['horizontal_alignment'])

        self.setFlags(QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        # Set initial stacking value
        self.setZValue(self.config_data.get('z_index', utils.Z_VALUE_INFO_RECT))

        self.text_item = QGraphicsTextItem('', self)
        # Default text color will be set in update_text_from_config
        # self.text_item.setDefaultTextColor(QColor("#000000")) # Removed, handled by update_text_from_config

        self._current_resize_handle = self.ResizeHandle.NONE
        self._resizing_initial_mouse_pos = QPointF()
        self._resizing_initial_rect = QRectF()
        self._is_resizing = False
        self._was_movable = bool(self.flags() & QGraphicsItem.ItemIsMovable) # Ensure it's a boolean
        self._applied_style_values = {} # To track values set by the current style

        self.update_geometry_from_config()
        self.update_text_from_config()
        self.update_appearance()
        self.initial_pos = self.pos()

    def boundingRect(self):
        return QRectF(0, 0, self._w, self._h)

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        painter.drawRect(self.boundingRect())

    def _get_resize_handle_at(self, pos):
        r = self.boundingRect()
        m = self.RESIZE_MARGIN
        on_left = abs(pos.x() - r.left()) < m
        on_right = abs(pos.x() - r.right()) < m
        on_top = abs(pos.y() - r.top()) < m
        on_bottom = abs(pos.y() - r.bottom()) < m

        if on_top and on_left: return self.ResizeHandle.TOP_LEFT
        if on_bottom and on_right: return self.ResizeHandle.BOTTOM_RIGHT
        if on_top and on_right: return self.ResizeHandle.TOP_RIGHT
        if on_bottom and on_left: return self.ResizeHandle.BOTTOM_LEFT
        if on_top: return self.ResizeHandle.TOP
        if on_bottom: return self.ResizeHandle.BOTTOM
        if on_left: return self.ResizeHandle.LEFT
        if on_right: return self.ResizeHandle.RIGHT
        return self.ResizeHandle.NONE

    def hoverMoveEvent(self, event):
        parent_win = None
        if self.scene() and hasattr(self.scene(), 'parent_window'):
            parent_win = self.scene().parent_window

        if self.isSelected() and parent_win and parent_win.current_mode == "edit" and not self._is_resizing :
            handle = self._get_resize_handle_at(event.pos())
            cursor_shape = Qt.ArrowCursor
            if handle != self.ResizeHandle.NONE:
                if handle == self.ResizeHandle.TOP_LEFT or handle == self.ResizeHandle.BOTTOM_RIGHT:
                    cursor_shape = Qt.SizeFDiagCursor
                elif handle == self.ResizeHandle.TOP_RIGHT or handle == self.ResizeHandle.BOTTOM_LEFT:
                    cursor_shape = Qt.SizeBDiagCursor
                elif handle == self.ResizeHandle.TOP or handle == self.ResizeHandle.BOTTOM:
                    cursor_shape = Qt.SizeVerCursor
                elif handle == self.ResizeHandle.LEFT or handle == self.ResizeHandle.RIGHT:
                    cursor_shape = Qt.SizeHorCursor
            elif self.flags() & QGraphicsItem.ItemIsMovable:
                 cursor_shape = Qt.PointingHandCursor

            if self.cursor().shape() != cursor_shape:
                self.setCursor(QCursor(cursor_shape))
        elif not self._is_resizing:
            default_cursor_shape = Qt.ArrowCursor
            if parent_win and parent_win.current_mode == "edit" and (self.flags() & QGraphicsItem.ItemIsMovable):
                 default_cursor_shape = Qt.PointingHandCursor
            if self.cursor().shape() != default_cursor_shape:
                self.setCursor(QCursor(default_cursor_shape))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._is_resizing:
            default_cursor_shape = Qt.ArrowCursor
            if self.scene() and hasattr(self.scene(), 'parent_window') and self.scene().parent_window.current_mode == "edit" and (self.flags() & QGraphicsItem.ItemIsMovable):
                default_cursor_shape = Qt.PointingHandCursor
            self.setCursor(QCursor(default_cursor_shape))
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        parent_win = None
        if self.scene() and hasattr(self.scene(), 'parent_window'):
            parent_win = self.scene().parent_window

        if event.button() == Qt.LeftButton and self.isSelected() and parent_win and parent_win.current_mode == "edit":
            self._current_resize_handle = self._get_resize_handle_at(event.pos())
            if self._current_resize_handle != self.ResizeHandle.NONE:
                self._is_resizing = True
                self._resizing_initial_mouse_pos = event.scenePos()
                self._resizing_initial_rect = self.sceneBoundingRect()

                self._was_movable = bool(self.flags() & QGraphicsItem.ItemIsMovable) # Store as bool
                self.setFlag(QGraphicsItem.ItemIsMovable, False)

                cursor_shape = Qt.ArrowCursor
                if self._current_resize_handle == self.ResizeHandle.TOP_LEFT or self._current_resize_handle == self.ResizeHandle.BOTTOM_RIGHT:
                    cursor_shape = Qt.SizeFDiagCursor
                elif self._current_resize_handle == self.ResizeHandle.TOP_RIGHT or self._current_resize_handle == self.ResizeHandle.BOTTOM_LEFT:
                    cursor_shape = Qt.SizeBDiagCursor
                elif self._current_resize_handle == self.ResizeHandle.TOP or self._current_resize_handle == self.ResizeHandle.BOTTOM:
                    cursor_shape = Qt.SizeVerCursor
                elif self._current_resize_handle == self.ResizeHandle.LEFT or self._current_resize_handle == self.ResizeHandle.RIGHT:
                    cursor_shape = Qt.SizeHorCursor
                self.setCursor(QCursor(cursor_shape))

                event.accept()
                return

        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton: # This logic might need review if item_selected should only emit on actual selection change
            self.item_selected.emit(self)
            self.initial_pos = self.pos()


    def mouseMoveEvent(self, event):
        if self._is_resizing and self._current_resize_handle != self.ResizeHandle.NONE:
            current_mouse_pos = event.scenePos()
            delta = current_mouse_pos - self._resizing_initial_mouse_pos

            new_rect = QRectF(self._resizing_initial_rect)

            if self._current_resize_handle in [self.ResizeHandle.TOP_LEFT, self.ResizeHandle.LEFT, self.ResizeHandle.BOTTOM_LEFT]:
                new_rect.setLeft(self._resizing_initial_rect.left() + delta.x())
            if self._current_resize_handle in [self.ResizeHandle.TOP_LEFT, self.ResizeHandle.TOP, self.ResizeHandle.TOP_RIGHT]:
                new_rect.setTop(self._resizing_initial_rect.top() + delta.y())
            if self._current_resize_handle in [self.ResizeHandle.TOP_RIGHT, self.ResizeHandle.RIGHT, self.ResizeHandle.BOTTOM_RIGHT]:
                new_rect.setRight(self._resizing_initial_rect.right() + delta.x())
            if self._current_resize_handle in [self.ResizeHandle.BOTTOM_LEFT, self.ResizeHandle.BOTTOM, self.ResizeHandle.BOTTOM_RIGHT]:
                new_rect.setBottom(self._resizing_initial_rect.bottom() + delta.y())

            if new_rect.width() < self.MIN_WIDTH:
                if self._current_resize_handle in [self.ResizeHandle.TOP_LEFT, self.ResizeHandle.LEFT, self.ResizeHandle.BOTTOM_LEFT]:
                    new_rect.setLeft(new_rect.right() - self.MIN_WIDTH)
                else:
                    new_rect.setRight(new_rect.left() + self.MIN_WIDTH)

            if new_rect.height() < self.MIN_HEIGHT:
                if self._current_resize_handle in [self.ResizeHandle.TOP_LEFT, self.ResizeHandle.TOP, self.ResizeHandle.TOP_RIGHT]:
                    new_rect.setTop(new_rect.bottom() - self.MIN_HEIGHT)
                else:
                    new_rect.setBottom(new_rect.top() + self.MIN_HEIGHT)

            self.prepareGeometryChange()

            self._w = new_rect.width()
            self._h = new_rect.height()
            self.text_item.setTextWidth(self._w)
            self.setPos(new_rect.topLeft())
            self._center_text()

            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_resizing and event.button() == Qt.LeftButton:
            self._is_resizing = False

            self.setFlag(QGraphicsItem.ItemIsMovable, self._was_movable)

            current_top_left_scene = self.scenePos()
            self.config_data['width'] = self._w
            self.config_data['height'] = self._h
            self.config_data['center_x'] = current_top_left_scene.x() + self._w / 2
            self.config_data['center_y'] = current_top_left_scene.y() + self._h / 2

            self.properties_changed.emit(self)

            default_cursor_shape = Qt.ArrowCursor
            if self.scene() and hasattr(self.scene(), 'parent_window') and self.scene().parent_window.current_mode == "edit":
                if self.flags() & QGraphicsItem.ItemIsMovable:
                     default_cursor_shape = Qt.PointingHandCursor
            self.setCursor(QCursor(default_cursor_shape))

            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def update_geometry_from_config(self):
        self.prepareGeometryChange()
        self._w = self.config_data.get('width', 100)
        self._h = self.config_data.get('height', 50)
        center_x = self.config_data.get('center_x', 0)
        center_y = self.config_data.get('center_y', 0)
        self.setPos(center_x - self._w / 2, center_y - self._h / 2)

        self.text_item.setTextWidth(self._w)
        self._center_text()
        self.update()

    def _get_style_value(self, key, default_value):
        if self._style_config_ref and key in self._style_config_ref:
            return self._style_config_ref[key]
        return self.config_data.get(key, default_value)

    def _center_text(self):
        if not self.text_item: return
        self.text_item.setPos(0,0) # Reset position, alignment handles actual placement

        # Use the text item's own bounding rect for height calculation,
        # as it's more accurate for final positioning than font_metrics alone.
        text_height = self.text_item.boundingRect().height()

        padding_str = self._get_style_value("padding", "5px")
        try:
            padding_val = int(padding_str.lower().replace("px", "")) if "px" in padding_str.lower() else 5
        except ValueError:
            padding_val = 5

        if self.vertical_alignment == "top":
            text_y_offset = padding_val
        elif self.vertical_alignment == "bottom":
            text_y_offset = self._h - text_height - padding_val
        else: # center (default)
            text_y_offset = (self._h - text_height) / 2
            text_y_offset = max(padding_val, text_y_offset)
            if text_y_offset + text_height > self._h - padding_val:
                 text_y_offset = self._h - text_height - padding_val

        self.text_item.setY(text_y_offset)

        # Ensure horizontal alignment is also applied by _center_text
        current_doc_option = self.text_item.document().defaultTextOption()
        h_align_map = {"left": Qt.AlignLeft, "center": Qt.AlignCenter, "right": Qt.AlignRight}
        alignment_flag = h_align_map.get(self.horizontal_alignment, Qt.AlignLeft)
        current_doc_option.setAlignment(alignment_flag)
        self.text_item.document().setDefaultTextOption(current_doc_option)


    def set_display_text(self, text):
        self.config_data['text'] = text
        self.text_item.document().setMarkdown(text)
        self._center_text()
        self.update()

    def update_text_from_config(self):
        default_text = self.config_data.get('text', '')
        self.text_item.document().setMarkdown(self._get_style_value('text', default_text))

        text_format_defaults = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

        self.vertical_alignment = self._get_style_value('vertical_alignment', text_format_defaults['vertical_alignment'])
        self.horizontal_alignment = self._get_style_value('horizontal_alignment', text_format_defaults['horizontal_alignment'])
        font_color = self._get_style_value('font_color', text_format_defaults['font_color'])
        font_size_str = self._get_style_value('font_size', text_format_defaults['font_size'])

        try:
            font_size = int(str(font_size_str).lower().replace("px", ""))
        except ValueError:
            try:
                default_font_size_val = int(str(text_format_defaults['font_size']).lower().replace("px",""))
                font_size = default_font_size_val
            except ValueError:
                font_size = 14

        font = self.text_item.font()
        font.setPixelSize(font_size)

        self.text_item.setFont(font)
        self.text_item.setDefaultTextColor(QColor(font_color))

        current_doc_option = self.text_item.document().defaultTextOption()
        h_align_map = {
            "left": Qt.AlignLeft, "center": Qt.AlignCenter, "right": Qt.AlignRight
        }
        alignment_flag = h_align_map.get(self.horizontal_alignment, Qt.AlignLeft)
        current_doc_option.setAlignment(alignment_flag)
        self.text_item.document().setDefaultTextOption(current_doc_option)
        self.text_item.setTextWidth(self._w)
        self._center_text()
        self.update()

    def update_appearance(self, is_selected=False, is_view_mode=False):
        if is_view_mode:
            self._pen = QPen(Qt.transparent)
            self._brush = QBrush(Qt.transparent)
            self.text_item.setVisible(False)
        else:
            self.text_item.setVisible(True)
            if is_selected:
                self._pen = QPen(QColor(255, 0, 0, 200), 2, Qt.SolidLine)
                self._brush = QBrush(QColor(255, 0, 0, 30))
            else:
                self._pen = QPen(QColor(0, 123, 255, 180), 2, Qt.DashLine)
                self._brush = QBrush(QColor(0, 123, 255, 25))
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene() and not self._is_resizing:
            self.config_data['center_x'] = value.x() + self._w / 2
            self.config_data['center_y'] = value.y() + self._h / 2
            self._has_moved = True
        return super().itemChange(change, value)

    def apply_style(self, style_config_object):
        self._style_config_ref = style_config_object

        if style_config_object and style_config_object.get('name'):
            self.config_data['text_style_ref'] = style_config_object['name']
        else:
            self.config_data.pop('text_style_ref', None)

        text_format_defaults = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
        all_style_keys = [
            'text', 'font_color', 'font_size',
            'vertical_alignment', 'horizontal_alignment', 'padding'
        ]

        if style_config_object:
            self._applied_style_values.clear() # Clear previous record
            for key in all_style_keys:
                if key in style_config_object:
                    self.config_data[key] = style_config_object[key]
                    # Record that this value in config_data came directly from this style application
                    if key != 'name': # 'name' is metadata for the style object itself
                        self._applied_style_values[key] = style_config_object[key]
                elif key in text_format_defaults:
                    # If style doesn't have this key, config_data property reverts to global default.
                    # (This includes 'text' if it's in text_format_defaults and not in style_config_object,
                    # though 'text' often has special handling or might not be in text_format_defaults.)
                    self.config_data[key] = text_format_defaults[key]
                elif key == 'text':
                    # This case ensures that if 'text' is not in style_config_object AND
                    # not in text_format_defaults (which would be unusual for 'text'),
                    # then item's current text is preserved.
                    pass
                else:
                    # If key from all_style_keys is not in style, not in defaults, and not 'text',
                    # then remove it from config_data. This is for cleanup of obsolete keys.
                    self.config_data.pop(key, None)
        else:
            # style_config_object is None (style is being removed)
            if self._applied_style_values: # Check if there were values from a previous style
                for key, style_set_value in self._applied_style_values.items():
                    # Only revert if current config value is THE SAME as what the style had set
                    if key in self.config_data and self.config_data[key] == style_set_value:
                        if key in text_format_defaults: # Revert to default
                            self.config_data[key] = text_format_defaults[key]
                        else: # Should not happen if keys are well-defined
                            # If a key was defined by style but has no default, remove it.
                            self.config_data.pop(key, None)
                self._applied_style_values.clear()
            # If a property was manually changed after style was applied (e.g. font_color in test),
            # it won't match style_set_value, so it will persist.
            # If _applied_style_values is empty (e.g. no style was active or style had no relevant keys),
            # this block effectively does nothing to config_data values.

        self.update_text_from_config()
        self.update_appearance(self.isSelected())
        self.properties_changed.emit(self)
