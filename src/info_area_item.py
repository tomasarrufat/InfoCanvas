import math
from PyQt5.QtWidgets import QGraphicsItem, QGraphicsTextItem, QApplication

from .base_draggable_item import BaseDraggableItem
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QRect
from PyQt5.QtGui import QColor, QBrush, QPen, QCursor, QTextOption, QPainterPath

from . import utils


class InfoAreaItem(BaseDraggableItem):
    item_selected = pyqtSignal(QGraphicsItem)
    properties_changed = pyqtSignal(QGraphicsItem)

    RESIZE_MARGIN = 8
    MIN_WIDTH = 20
    MIN_HEIGHT = 20
    ROTATE_HANDLE_OFFSET = 15
    ROTATE_HANDLE_RADIUS = 4

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
        self.config_data.setdefault('show_on_hover', True)
        self._style_config_ref = None
        self._w = self.config_data.get('width', 100)
        self._h = self.config_data.get('height', 50)
        self.angle = self.config_data.get('angle', 0.0)
        self.setTransformOriginPoint(self._w / 2, self._h / 2)
        self._pen = QPen(Qt.NoPen)
        self._brush = QBrush(Qt.NoBrush)
        self.shape_type = rect_config.get('shape', 'rectangle')

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
        self._resize_start_mouse_scene_pos = QPointF()
        self._resizing_initial_item_pos = QPointF()
        self._resizing_initial_width = self._w
        self._resizing_initial_height = self._h
        self._is_resizing = False
        self._is_rotating = False
        self._rotation_start_scene_pos = QPointF()
        self._rotation_start_angle = 0.0
        self._rotation_center_scene = QPointF()
        self._was_movable = bool(self.flags() & QGraphicsItem.ItemIsMovable) # Ensure it's a boolean
        self._applied_style_values = {} # To track values set by the current style

        self.update_geometry_from_config()
        self.update_text_from_config()
        self.update_appearance()
        self.initial_pos = self.pos()
        self._resizing_initial_item_pos = self.pos()
        self._resizing_initial_width = self._w
        self._resizing_initial_height = self._h

    def boundingRect(self):
        rect = QRectF(0, 0, self._w, self._h)
        return rect.united(self._get_rotation_handle_rect())

    def shape(self):
        path = QPainterPath()
        path.setFillRule(Qt.WindingFill)
        path.addRect(QRectF(0, 0, self._w, self._h))
        path.addEllipse(self._get_rotation_handle_rect())
        return path

    def paint(self, painter, option, widget=None):
        painter.setPen(self._pen)
        painter.setBrush(self._brush)
        inner_rect = QRectF(0, 0, self._w, self._h)
        if self.shape_type == 'ellipse':
            painter.drawEllipse(inner_rect)
        else:
            painter.drawRect(inner_rect)

        if self.isSelected():
            handle_rect = self._get_rotation_handle_rect()
            painter.setPen(QPen(Qt.yellow))
            painter.setBrush(QBrush(Qt.yellow))
            painter.drawEllipse(handle_rect)

    def _get_resize_handle_at(self, pos):
        r = QRectF(0, 0, self._w, self._h)
        m = self.RESIZE_MARGIN
        on_left = abs(pos.x() - r.left()) <= m
        on_right = abs(pos.x() - r.right()) <= m
        on_top = abs(pos.y() - r.top()) <= m
        on_bottom = abs(pos.y() - r.bottom()) <= m

        if on_top and on_left: return self.ResizeHandle.TOP_LEFT
        if on_bottom and on_right: return self.ResizeHandle.BOTTOM_RIGHT
        if on_top and on_right: return self.ResizeHandle.TOP_RIGHT
        if on_bottom and on_left: return self.ResizeHandle.BOTTOM_LEFT
        if on_top: return self.ResizeHandle.TOP
        if on_bottom: return self.ResizeHandle.BOTTOM
        if on_left: return self.ResizeHandle.LEFT
        if on_right: return self.ResizeHandle.RIGHT
        return self.ResizeHandle.NONE

    def _get_rotation_handle_rect(self):
        center = QPointF(self._w + self.ROTATE_HANDLE_OFFSET,
                          -self.ROTATE_HANDLE_OFFSET)
        r = self.ROTATE_HANDLE_RADIUS
        return QRectF(center.x() - r, center.y() - r, 2 * r, 2 * r)

    def hoverMoveEvent(self, event):
        parent_win = None
        if self.scene() and hasattr(self.scene(), 'parent_window'):
            parent_win = self.scene().parent_window

        if self.isSelected() and parent_win and parent_win.current_mode == "edit" and not self._is_resizing and not self._is_rotating:
            if self._get_rotation_handle_rect().contains(event.pos()):
                cursor_shape = Qt.OpenHandCursor
            else:
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
        elif not self._is_resizing and not self._is_rotating:
            default_cursor_shape = Qt.ArrowCursor
            if parent_win and parent_win.current_mode == "edit" and (self.flags() & QGraphicsItem.ItemIsMovable):
                 default_cursor_shape = Qt.PointingHandCursor
            if self.cursor().shape() != default_cursor_shape:
                self.setCursor(QCursor(default_cursor_shape))
        super().hoverMoveEvent(event)

    def hoverLeaveEvent(self, event):
        if not self._is_resizing and not self._is_rotating:
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
            if self._get_rotation_handle_rect().contains(event.pos()):
                self._is_rotating = True
                self._rotation_start_scene_pos = event.scenePos()
                self._rotation_start_angle = self.angle
                self._rotation_center_scene = self.mapToScene(self.transformOriginPoint())
                self._was_movable = bool(self.flags() & QGraphicsItem.ItemIsMovable)
                self.setFlag(QGraphicsItem.ItemIsMovable, False)
                self.setCursor(QCursor(Qt.ClosedHandCursor))
                event.accept()
                return

            self._current_resize_handle = self._get_resize_handle_at(event.pos())
            if self._current_resize_handle != self.ResizeHandle.NONE:
                self._is_resizing = True
                # Store initial state for resizing
                self._resizing_initial_item_pos = self.pos()
                self._resizing_initial_width = self._w
                self._resizing_initial_height = self._h
                self._resizing_initial_mouse_pos = event.scenePos()
                self._resize_start_mouse_scene_pos = self._resizing_initial_mouse_pos
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
        if self._is_rotating:
            center = self._rotation_center_scene
            start_vec = self._rotation_start_scene_pos - center
            current_vec = event.scenePos() - center
            start_angle = math.degrees(math.atan2(start_vec.y(), start_vec.x()))
            current_angle = math.degrees(math.atan2(current_vec.y(), current_vec.x()))
            delta = current_angle - start_angle
            new_angle = self._rotation_start_angle + delta
            self.angle = new_angle
            self.config_data['angle'] = new_angle
            self.setRotation(new_angle)
            self.update()
            event.accept()
        elif self._is_resizing and self._current_resize_handle != self.ResizeHandle.NONE:
            current_mouse_scene_pos = event.scenePos()
            original_mouse_scene_pos = self._resizing_initial_mouse_pos

            angle_rad = math.radians(self.config_data.get('angle', 0.0))
            cos_a = math.cos(angle_rad)
            sin_a = math.sin(angle_rad)
            item_x_axis_scene = QPointF(cos_a, sin_a)
            item_y_axis_scene = QPointF(-sin_a, cos_a)

            mouse_delta_scene = current_mouse_scene_pos - original_mouse_scene_pos
            delta_local_x = QPointF.dotProduct(mouse_delta_scene, item_x_axis_scene)
            delta_local_y = QPointF.dotProduct(mouse_delta_scene, item_y_axis_scene)

            new_w = self._resizing_initial_width
            new_h = self._resizing_initial_height
            pos_change_x_local = 0.0
            pos_change_y_local = 0.0

            if self._current_resize_handle == self.ResizeHandle.RIGHT:
                new_w += delta_local_x
            elif self._current_resize_handle == self.ResizeHandle.LEFT:
                new_w -= delta_local_x
            elif self._current_resize_handle == self.ResizeHandle.BOTTOM:
                new_h += delta_local_y
            elif self._current_resize_handle == self.ResizeHandle.TOP:
                new_h -= delta_local_y
            elif self._current_resize_handle == self.ResizeHandle.TOP_LEFT:
                new_w -= delta_local_x
                new_h -= delta_local_y
            elif self._current_resize_handle == self.ResizeHandle.TOP_RIGHT:
                new_w += delta_local_x
                new_h -= delta_local_y
            elif self._current_resize_handle == self.ResizeHandle.BOTTOM_LEFT:
                new_w -= delta_local_x
                new_h += delta_local_y
            elif self._current_resize_handle == self.ResizeHandle.BOTTOM_RIGHT:
                new_w += delta_local_x
                new_h += delta_local_y

            # Apply Minimum Size Constraints
            if new_w < self.MIN_WIDTH:
                new_w = self.MIN_WIDTH

            if new_h < self.MIN_HEIGHT:
                new_h = self.MIN_HEIGHT

            # Recalculate position shifts based on final dimensions
            if self._current_resize_handle in [self.ResizeHandle.LEFT, self.ResizeHandle.TOP_LEFT, self.ResizeHandle.BOTTOM_LEFT]:
                pos_change_x_local = self._resizing_initial_width - new_w
            if self._current_resize_handle in [self.ResizeHandle.TOP, self.ResizeHandle.TOP_LEFT, self.ResizeHandle.TOP_RIGHT]:
                pos_change_y_local = self._resizing_initial_height - new_h

            scene_shift_for_pos_x_component = item_x_axis_scene * pos_change_x_local
            scene_shift_for_pos_y_component = item_y_axis_scene * pos_change_y_local
            total_scene_shift = scene_shift_for_pos_x_component + scene_shift_for_pos_y_component
            new_pos_scene = self._resizing_initial_item_pos + total_scene_shift

            self.prepareGeometryChange()
            self._w = new_w
            self._h = new_h
            self.setTransformOriginPoint(self._w / 2, self._h / 2) # Update origin before setting position
            self.setPos(new_pos_scene)
            self.text_item.setTextWidth(self._w)
            self._center_text()
            self.update()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._is_rotating and event.button() == Qt.LeftButton:
            self._is_rotating = False
            self.setFlag(QGraphicsItem.ItemIsMovable, self._was_movable)
            self.properties_changed.emit(self)
            default_cursor_shape = Qt.ArrowCursor
            if self.scene() and hasattr(self.scene(), 'parent_window') and self.scene().parent_window.current_mode == "edit":
                if self.flags() & QGraphicsItem.ItemIsMovable:
                    default_cursor_shape = Qt.PointingHandCursor
            self.setCursor(QCursor(default_cursor_shape))
            event.accept()
        elif self._is_resizing and event.button() == Qt.LeftButton:
            self._is_resizing = False
            self.setFlag(QGraphicsItem.ItemIsMovable, self._was_movable)

            self.config_data['width'] = self._w
            self.config_data['height'] = self._h

            # Calculate the new center point in scene coordinates
            # The item's origin (0,0) is its top-left. Transform origin is w/2, h/2.
            # Position self.pos() is the top-left point in scene coordinates.
            # To get the scene coordinates of the item's center (which is also its transform origin point):
            self.config_data['center_x'] = self.pos().x() + self._w / 2
            self.config_data['center_y'] = self.pos().y() + self._h / 2

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

        # Update origin point in case width/height changed
        self.setTransformOriginPoint(self._w / 2, self._h / 2)
        # Apply rotation
        self.angle = self.config_data.get('angle', 0.0)
        self.setRotation(self.angle)

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
            self.text_item.setVisible(not self.config_data.get('show_on_hover', True))
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
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene() and not self._is_resizing and not self._is_rotating:
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
