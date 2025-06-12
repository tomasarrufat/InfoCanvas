from PyQt5.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsTextItem, QApplication
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QRect
from PyQt5.QtGui import QColor, QBrush, QPen, QFontMetrics, QCursor, QTextOption, QFont

from . import utils


class InfoRectangleItem(QGraphicsObject):
    item_selected = pyqtSignal(QGraphicsItem)
    item_moved = pyqtSignal(QGraphicsItem)
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
        self.font_style = self.config_data.get('font_style', text_format_defaults['font_style'])

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
        self._was_movable = self.flags() & QGraphicsItem.ItemIsMovable

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

                self._was_movable = self.flags() & QGraphicsItem.ItemIsMovable
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
        if event.button() == Qt.LeftButton:
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
        self.text_item.setPos(0,0) # Ensure text_item origin is top-left of InfoRectangleItem
        # Use QFontMetrics to calculate the actual height of the text block
        font_metrics = QFontMetrics(self.text_item.font())
        # Need to use a QRect that respects the width of the text item for word wrapping
        # Use current horizontal alignment for bounding rect calculation
        align_flag = Qt.AlignLeft
        if self.horizontal_alignment == "center":
            align_flag = Qt.AlignCenter
        elif self.horizontal_alignment == "right":
            align_flag = Qt.AlignRight
        text_bounding_rect = font_metrics.boundingRect(QRect(0, 0, int(self.text_item.textWidth()), 10000), Qt.TextWordWrap | align_flag, self.text_item.toPlainText()) # Large height for calculation
        text_height = text_bounding_rect.height()

        # Get padding from config, default to 5 if not found or invalid
        # Use the actual config_data for padding, not defaults, as it might be styled
        padding_str = self._get_style_value("padding", "5px")
        try:
            padding_val = int(padding_str.lower().replace("px", "")) if "px" in padding_str.lower() else 5
        except ValueError:
            padding_val = 5 # Default padding if conversion fails

        if self.vertical_alignment == "top":
            text_y_offset = padding_val
        elif self.vertical_alignment == "bottom":
            text_y_offset = self._h - text_height - padding_val
        else: # center (default)
            text_y_offset = (self._h - text_height) / 2
            # Ensure centered text also respects top padding if content is large
            text_y_offset = max(padding_val, text_y_offset)
            # And bottom padding
            if text_y_offset + text_height > self._h - padding_val:
                 text_y_offset = self._h - text_height - padding_val


        self.text_item.setY(text_y_offset)


    def set_display_text(self, text):
        """Sets the display text and recenters, optimized for live editing from properties panel."""
        self.config_data['text'] = text # Update config_data as well
        self.text_item.setPlainText(text)
        self._center_text() # Recenter after text change
        self.update() # Ensure repaint

    def update_text_from_config(self):
        """Updates the text content and formatting from config_data."""
        # If a style is applied, 'text' should also come from it if specified.
        # Fallback to an empty string if not in style or config_data.
        default_text = self.config_data.get('text', '') # Original text from item's own config as ultimate fallback.
        self.text_item.setPlainText(self._get_style_value('text', default_text))

        # Update formatting options from config_data, falling back to defaults if necessary
        text_format_defaults = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

        self.vertical_alignment = self._get_style_value('vertical_alignment', text_format_defaults['vertical_alignment'])
        self.horizontal_alignment = self._get_style_value('horizontal_alignment', text_format_defaults['horizontal_alignment'])
        self.font_style = self._get_style_value('font_style', text_format_defaults['font_style'])
        font_color = self._get_style_value('font_color', text_format_defaults['font_color'])
        font_size_str = self._get_style_value('font_size', text_format_defaults['font_size'])

        try:
            # Ensure font_size_str is treated as a string before string methods are called
            font_size = int(str(font_size_str).lower().replace("px", ""))
        except ValueError:
            # Fallback to parsing the default font_size from text_format_defaults
            try:
                default_font_size_val = int(str(text_format_defaults['font_size']).lower().replace("px",""))
                font_size = default_font_size_val
            except ValueError:
                font_size = 14 # Ultimate fallback default font size if default config is also bad

        font = self.text_item.font()
        font.setPointSize(font_size)

        if self.font_style == "bold":
            font.setWeight(QFont.Bold)
            font.setItalic(False)
        elif self.font_style == "italic":
            font.setWeight(QFont.Normal)
            font.setItalic(True)
        else: # normal
            font.setWeight(QFont.Normal)
            font.setItalic(False)

        self.text_item.setFont(font)
        self.text_item.setDefaultTextColor(QColor(font_color))

        # Set horizontal alignment for the text item
        # Get the document's current default text option
        current_doc_option = self.text_item.document().defaultTextOption()

        # Create a mapping for alignment strings to Qt alignment flags
        h_align_map = {
            "left": Qt.AlignLeft,
            "center": Qt.AlignCenter, # Use Qt.AlignCenter for QTextOption horizontal centering
            "right": Qt.AlignRight
        }
        # Get the appropriate flag, defaulting to AlignLeft
        alignment_flag = h_align_map.get(self.horizontal_alignment, Qt.AlignLeft)

        # Set its alignment
        current_doc_option.setAlignment(alignment_flag)

        # Apply the modified option back to the document
        self.text_item.document().setDefaultTextOption(current_doc_option)

        # Setting text width is important for alignment to work correctly with wrapped text
        self.text_item.setTextWidth(self._w)


        self._center_text() # Recenter/re-align after text and format change
        self.update() # Ensure repaint

    def update_appearance(self, is_selected=False, is_view_mode=False):
        if is_view_mode:
            self._pen = QPen(Qt.transparent) # Make border transparent
            self._brush = QBrush(Qt.transparent) # Make background transparent
            self.text_item.setVisible(False) # Hide text in view mode
        else:
            self.text_item.setVisible(True) # Ensure text is visible in edit mode
            if is_selected:
                self._pen = QPen(QColor(255, 0, 0, 200), 2, Qt.SolidLine)  # More visible selection: Red, thicker
                self._brush = QBrush(QColor(255, 0, 0, 30))  # Light red fill for selection
            else:
                # Default appearance (not selected, in edit mode)
                self._pen = QPen(QColor(0, 123, 255, 180), 2, Qt.DashLine) # Blue dashed line
                self._brush = QBrush(QColor(0, 123, 255, 25)) # Light blue fill
        self.update()

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene() and not self._is_resizing:
            # Update config with new center based on top-left position (value) and current dimensions
            self.config_data['center_x'] = value.x() + self._w / 2
            self.config_data['center_y'] = value.y() + self._h / 2
            self.item_moved.emit(self)
        return super().itemChange(change, value)

    def apply_style(self, style_config_object):
        """
        Applies a style configuration object to the item.
        The item will hold a reference to this object.
        """
        self._style_config_ref = style_config_object

        if style_config_object and style_config_object.get('name'):
            self.config_data['text_style_ref'] = style_config_object['name']
        else:
            self.config_data.pop('text_style_ref', None)

        # Flatten style properties into self.config_data
        text_format_defaults = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
        all_style_keys = [
            'text', 'font_color', 'font_size', 'font_style',
            'vertical_alignment', 'horizontal_alignment', 'padding'
        ]

        if style_config_object: # A specific style dictionary is provided (e.g. a named style or "Default")
            for key in all_style_keys:
                if key in style_config_object:
                    self.config_data[key] = style_config_object[key]
                elif key in text_format_defaults:
                    # If the applied style object *omits* a key that has a defined default,
                    # the item's config_data should adopt that default for that key.
                    self.config_data[key] = text_format_defaults[key]
                elif key == 'text':
                    # If 'text' is not in style_config_object, self.config_data['text'] should remain.
                    # It should not be defaulted to empty or popped here by the style application process
                    # unless the style itself defines text as empty.
                    pass # Do nothing to self.config_data['text'] if key 'text' is not in style_config_object
                else:
                    # For other formatting keys not in style and not in defaults (unlikely for well-defined defaults)
                    self.config_data.pop(key, None)
        # If style_config_object is None (meaning detach style, go to fully custom),
        # then self.config_data already holds the custom values. No flattening needed from a None object.
        # The _style_config_ref is None, and text_style_ref is popped.
        # update_text_from_config will then read directly from self.config_data via _get_style_value's fallback.

        self.update_text_from_config()
        self.update_appearance(self.isSelected())
        self.properties_changed.emit(self)
