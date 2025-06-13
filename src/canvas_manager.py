import os
from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QPixmap, QTransform
from PyQt5.QtWidgets import QGraphicsScene, QMessageBox

from . import utils
from .draggable_image_item import DraggableImageItem
from .info_rectangle_item import InfoRectangleItem


class CanvasManager(QObject):
    """Encapsulates QGraphicsScene related logic for InteractiveToolApp."""

    selection_changed = pyqtSignal()

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.scene: QGraphicsScene = app.scene
        if self.scene:
            self.scene.selectionChanged.connect(self.on_scene_selection_changed)

    # ---- Rendering -----------------------------------------------------
    def render_canvas_from_config(self):
        app = self.app
        config = app.config
        if not config or not self.scene:
            return

        selected_item_id = None
        if app.selected_item:
            for item_id, gi in app.item_map.items():
                if gi == app.selected_item:
                    selected_item_id = item_id
                    break

        self.scene.clear()
        app.item_map.clear()

        bg_conf = config.get('background', utils.get_default_config()['background'])
        self.scene.setBackgroundBrush(QBrush(QColor(bg_conf['color'])))
        self.scene.setSceneRect(0, 0, bg_conf['width'], bg_conf['height'])

        current_images_folder = app._get_project_images_folder(app.current_project_path)
        if not current_images_folder:
            QMessageBox.critical(app, "Render Error", "Cannot determine images folder for the current project.")
            return

        for img_conf in config.get('images', []):
            image_path = img_conf.get('path', '')
            if not image_path:
                continue
            image_full_path = os.path.join(current_images_folder, image_path)
            pixmap = QPixmap(image_full_path)
            if pixmap.isNull():
                pixmap = QPixmap(100, 100)
                pixmap.fill(Qt.lightGray)
                if not img_conf.get('original_width') or img_conf.get('original_width', 0) <= 0:
                    img_conf['original_width'] = 100
                if not img_conf.get('original_height') or img_conf.get('original_height', 0) <= 0:
                    img_conf['original_height'] = 100
            if not img_conf.get('original_width') or img_conf.get('original_width', 0) <= 0:
                img_conf['original_width'] = pixmap.width()
            if not img_conf.get('original_height') or img_conf.get('original_height', 0) <= 0:
                img_conf['original_height'] = pixmap.height()

            item = DraggableImageItem(pixmap, img_conf)
            scale = img_conf.get('scale', 1.0)
            transform = QTransform()
            transform.scale(scale, scale)
            item.setTransform(transform)
            center_x = img_conf.get('center_x', self.scene.width() / 2)
            center_y = img_conf.get('center_y', self.scene.height() / 2)
            scaled_w = img_conf['original_width'] * scale
            scaled_h = img_conf['original_height'] * scale
            item.setPos(center_x - scaled_w / 2, center_y - scaled_h / 2)
            item.item_selected.connect(self.on_graphics_item_selected)
            item.item_moved.connect(self.on_graphics_item_moved)
            self.scene.addItem(item)
            app.item_map[img_conf['id']] = item

        for rect_conf in config.get('info_rectangles', []):
            item = InfoRectangleItem(rect_conf)
            item.item_selected.connect(self.on_graphics_item_selected)
            item.item_moved.connect(self.on_graphics_item_moved)
            item.properties_changed.connect(self.on_graphics_item_properties_changed)
            self.scene.addItem(item)
            app.item_map[rect_conf['id']] = item

            if 'text_style_ref' in rect_conf:
                style_name = rect_conf['text_style_ref']
                found = None
                for style_obj in config.get('text_styles', []):
                    if style_obj.get('name') == style_name:
                        found = style_obj
                        break
                if found:
                    item.apply_style(found)
                else:
                    print(f"Warning: InfoRectangle {rect_conf.get('id')} references style '{style_name}' which was not found in text_styles.")

        if selected_item_id and selected_item_id in app.item_map:
            app.selected_item = app.item_map[selected_item_id]
            if app.selected_item:
                app.selected_item.setSelected(True)
        else:
            app.selected_item = None

        app.update_mode_ui()
        app.update_properties_panel()

    # ---- Selection Handling -------------------------------------------
    def on_scene_selection_changed(self):
        app = self.app
        if not self.scene:
            app.chronologically_first_selected_item = None
            app.selected_item = None
            app.update_properties_panel()
            return

        selected_items = self.scene.selectedItems()
        current_info_rects = [i for i in selected_items if isinstance(i, InfoRectangleItem)]
        num_selected = len(current_info_rects)

        if num_selected == 0:
            app.chronologically_first_selected_item = None
        elif num_selected == 1:
            app.chronologically_first_selected_item = current_info_rects[0]
        else:
            if app.chronologically_first_selected_item is None or app.chronologically_first_selected_item not in current_info_rects:
                sorted_rects = sorted(current_info_rects, key=lambda r: r.config_data.get('id', ''))
                app.chronologically_first_selected_item = sorted_rects[0] if sorted_rects else None

        for item in self.scene.items():
            if isinstance(item, InfoRectangleItem):
                item.update_appearance(item.isSelected(), app.current_mode == "view")

        if selected_items and app.selected_item not in selected_items:
            app.selected_item = selected_items[-1]
        elif not selected_items:
            app.selected_item = None

        app.update_properties_panel()
        self.selection_changed.emit()

    def on_graphics_item_selected(self, graphics_item):
        app = self.app
        if app.current_mode == "view":
            self.scene.clearSelection()
            app.selected_item = None
            app.update_properties_panel()
            return

        ctrl_pressed = QApplication.keyboardModifiers() & Qt.ControlModifier
        if ctrl_pressed and isinstance(graphics_item, InfoRectangleItem):
            if graphics_item.isSelected():
                app.selected_item = graphics_item
            else:
                remaining = self.scene.selectedItems()
                app.selected_item = remaining[-1] if remaining else None
            app.update_properties_panel()
            return

        if app.selected_item is graphics_item and isinstance(app.selected_item, InfoRectangleItem):
            app.selected_item.update_appearance(True, app.current_mode == "view")

        if app.selected_item is not graphics_item:
            if app.selected_item and isinstance(app.selected_item, InfoRectangleItem):
                app.selected_item.update_appearance(False, app.current_mode == "view")

            app.selected_item = graphics_item

            if app.selected_item:
                try:
                    self.scene.selectionChanged.disconnect(self.on_scene_selection_changed)
                except TypeError:
                    pass
                for item_in_scene in self.scene.items():
                    if item_in_scene is not app.selected_item and item_in_scene.isSelected():
                        item_in_scene.setSelected(False)
                        if isinstance(item_in_scene, InfoRectangleItem):
                            item_in_scene.update_appearance(False, app.current_mode == "view")
                app.selected_item.setSelected(True)
                if isinstance(app.selected_item, InfoRectangleItem):
                    app.selected_item.update_appearance(True, app.current_mode == "view")
                try:
                    self.scene.selectionChanged.connect(self.on_scene_selection_changed)
                except TypeError:
                    pass
        app.update_properties_panel()
        self.selection_changed.emit()

    def on_graphics_item_moved(self, graphics_item):
        self.app.save_config()

    def on_graphics_item_properties_changed(self, graphics_item):
        self.app.save_config()
        if isinstance(graphics_item, InfoRectangleItem):
            graphics_item.update_geometry_from_config()
            self.app.update_properties_panel()

    # ---- Alignment Helpers -------------------------------------------
    def align_selected_rects_horizontally(self):
        if not self.scene:
            return
        selected_items = self.scene.selectedItems()
        rects = [i for i in selected_items if isinstance(i, InfoRectangleItem)]
        if len(rects) < 2:
            return
        app = self.app
        if app.chronologically_first_selected_item is None or app.chronologically_first_selected_item not in rects:
            app.statusBar().showMessage(
                "Cannot determine the source item for alignment. Please select items one by one if issues persist.",
                3000,
            )
            return
        source_rect = app.chronologically_first_selected_item
        target_x = source_rect.config_data.get('center_x', 0)
        for rect in rects:
            rect.config_data['center_x'] = target_x
            rect.update_geometry_from_config()
            if hasattr(rect, 'properties_changed') and hasattr(rect.properties_changed, 'emit'):
                rect.properties_changed.emit(rect)

    def align_selected_rects_vertically(self):
        if not self.scene:
            return
        selected_items = self.scene.selectedItems()
        rects = [i for i in selected_items if isinstance(i, InfoRectangleItem)]
        if len(rects) < 2:
            return
        app = self.app
        if app.chronologically_first_selected_item is None or app.chronologically_first_selected_item not in rects:
            app.statusBar().showMessage(
                "Cannot determine the source item for alignment. Please select items one by one if issues persist.",
                3000,
            )
            return
        source_rect = app.chronologically_first_selected_item
        target_y = source_rect.config_data.get('center_y', 0)
        for rect in rects:
            rect.config_data['center_y'] = target_y
            rect.update_geometry_from_config()
            if hasattr(rect, 'properties_changed') and hasattr(rect.properties_changed, 'emit'):
                rect.properties_changed.emit(rect)
