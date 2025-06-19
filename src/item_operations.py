import datetime
import os
import shutil
import copy

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QApplication
from PyQt5.QtGui import QImageReader, QPixmap, QTransform

from src import utils
from src.draggable_image_item import DraggableImageItem
from src.info_area_item import InfoAreaItem

class ItemOperations:
    def __init__(self, app):
        self.app = app
        self.scene = app.scene
        self.config = app.config
        self.item_map = app.item_map
        # self.selected_item will be accessed via self.app.selected_item
        # self.current_project_path will be accessed via self.app.current_project_path

    def _get_project_images_folder(self):
        # Helper to get the current project's images folder
        if not self.app.current_project_path:
            return None
        return self.app.project_io.get_project_images_folder(self.app.current_project_path)

    def _get_next_z_index(self):
         if hasattr(self, 'scene') and self.scene and self.scene.items(): # self.scene is app.scene
             return max(item.zValue() for item in self.scene.items()) + 1
         return 0

    def upload_image(self):
        if not self.app.current_project_path:
            QMessageBox.critical(self.app, "Upload Error", "No project loaded. Cannot upload image.")
            return
        current_project_images_folder = self._get_project_images_folder() # Uses internal helper
        if not current_project_images_folder:
             QMessageBox.critical(self.app, "Upload Error", "Cannot determine project images folder.")
             return

        filepath, _ = QFileDialog.getOpenFileName(
            self.app, "Upload Image", current_project_images_folder, # parent is self.app
            f"Images ({' '.join(['*.' + ext for ext in utils.ALLOWED_EXTENSIONS])})"
        )
        if not filepath:
            return

        filename = os.path.basename(filepath)
        if not utils.allowed_file(filename):
            QMessageBox.warning(self.app, "Upload Error", "Selected file type is not allowed.") # parent is self.app
            return

        base, ext = os.path.splitext(filename)
        counter = 1
        unique_filename = filename
        while os.path.exists(os.path.join(current_project_images_folder, unique_filename)):
            unique_filename = f"{base}_{counter}{ext}"
            counter += 1

        target_path = os.path.join(current_project_images_folder, unique_filename)
        try:
            shutil.copy(filepath, target_path)
        except Exception as e:
            QMessageBox.critical(self.app, "Upload Error", f"Could not copy image to '{target_path}': {e}") # parent is self.app
            return

        img_id = f"img_{datetime.datetime.now().timestamp()}"
        reader = QImageReader(target_path)
        original_size = reader.size()
        original_width = original_size.width()
        original_height = original_size.height()

        if original_width <= 0 or original_height <= 0:
            QMessageBox.warning(self.app, "Image Error", f"Could not read valid dimensions for image: {unique_filename}. Using fallback 100x100.") # parent is self.app
            original_width, original_height = 100, 100

        new_image_config = {
            "id": img_id,
            "path": unique_filename,
            "center_x": self.scene.width() / 2, # self.scene is app.scene
            "center_y": self.scene.height() / 2, # self.scene is app.scene
            "scale": 1.0,
            "original_width": original_width,
            "original_height": original_height,
            "z_index": self._get_next_z_index(), # Local method
        }

        if 'images' not in self.config: self.config['images'] = [] # self.config is app.config
        self.config['images'].append(new_image_config)

        pixmap = QPixmap(target_path)
        item = DraggableImageItem(pixmap, new_image_config) # Z-value set in item's __init__
        item.setTransform(QTransform().scale(new_image_config['scale'], new_image_config['scale']))
        item.setPos(
            new_image_config['center_x'] - (original_width * new_image_config['scale']) / 2,
            new_image_config['center_y'] - (original_height * new_image_config['scale']) / 2
        )

        # Connect signals to app's CanvasManager handlers
        item.item_selected.connect(self.app.canvas_manager.on_graphics_item_selected)
        item.item_moved.connect(self.app.canvas_manager.on_graphics_item_moved)

        self.scene.addItem(item) # self.scene is app.scene
        self.item_map[img_id] = item # self.item_map is app.item_map

        self.app.save_config() # Call app's save_config
        self.app.statusBar().showMessage(f"Image '{unique_filename}' uploaded to project '{self.app.current_project_name}'.", 3000) # app's statusBar and current_project_name

        self.scene.clearSelection()
        item.setSelected(True)

    def update_selected_image_scale(self):
        if isinstance(self.app.selected_item, DraggableImageItem): # Access via self.app
            new_scale = self.app.img_scale_input.value() # Access via self.app
            img_conf = self.app.selected_item.config_data
            img_conf['scale'] = new_scale

            # Ensure original_width and original_height are present, otherwise try to calculate from pixmap
            # This part needs careful handling if original dimensions aren't in config for some reason.
            # Assuming DraggableImageItem.config_data always has 'original_width' and 'original_height' after upload.
            original_width = img_conf.get('original_width')
            original_height = img_conf.get('original_height')

            if original_width is None or original_height is None:
                # Fallback if original dimensions somehow not set (should not happen with current upload logic)
                # This might occur if config was manually edited or from older versions.
                # The original code tried to calculate from pixmap().width()/scale, which can be circular.
                # A safer fallback might be to use the pixmap's current size if scale is 1, or not scale if unknown.
                # For now, let's assume they exist. If issues arise, this needs robust handling.
                # A simple fix: if not present, then maybe cannot reliably scale from center.
                # However, DraggableImageItem itself should store its original pixmap dimensions ideally.
                # For now, adhering to the logic of trying to get it from config:
                if self.app.selected_item.pixmap():
                     # Avoid division by zero if scale is 0, though UI constraints likely prevent this.
                    current_scale_in_config = img_conf.get('scale', 1.0) if img_conf.get('scale', 1.0) != 0 else 1.0
                    if original_width is None:
                        original_width = self.app.selected_item.pixmap().width() / current_scale_in_config
                    if original_height is None:
                        original_height = self.app.selected_item.pixmap().height() / current_scale_in_config
                else: # No pixmap to derive from
                    QMessageBox.warning(self.app, "Scale Error", "Cannot determine original image dimensions to scale correctly.")
                    return


            new_scaled_width = original_width * new_scale
            new_scaled_height = original_height * new_scale

            current_center_x = img_conf['center_x']
            current_center_y = img_conf['center_y']

            new_top_left_x = current_center_x - new_scaled_width / 2
            new_top_left_y = current_center_y - new_scaled_height / 2

            self.app.selected_item.setPos(new_top_left_x, new_top_left_y)

            transform = QTransform()
            transform.scale(new_scale, new_scale)
            self.app.selected_item.setTransform(transform)

            self.app.save_config() # Call app's save_config
            self.scene.update() # self.scene is app.scene

    def delete_selected_image(self):
        if not isinstance(self.app.selected_item, DraggableImageItem): # Access via self.app
            QMessageBox.information(self.app, "Delete Image", "No image selected to delete.") # parent is self.app
            return

        img_conf = self.app.selected_item.config_data
        reply = QMessageBox.question(self.app, "Confirm Delete", # parent is self.app
                                     f"Are you sure you want to permanently delete the image '{img_conf['path']}' from project '{self.app.current_project_name}'?", # app's project name
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            current_project_images_folder = self._get_project_images_folder() # Use internal helper
            if not current_project_images_folder:
                QMessageBox.warning(self.app, "Delete Error", "Cannot determine project images folder. Cannot delete image file.")
                # Decide if we should still proceed to remove from config. For now, let's be consistent with original:
                # it would proceed to remove from config.
            else:
                image_file_path = os.path.join(current_project_images_folder, img_conf['path'])
                try:
                    if os.path.exists(image_file_path):
                        os.remove(image_file_path)
                except OSError as e:
                    QMessageBox.warning(self.app, "Delete Error", f"Could not delete image file '{img_conf['path']}': {e}. It will still be removed from the configuration.") # parent is self.app

            if img_conf in self.config.get('images', []): # self.config is app.config
                self.config['images'].remove(img_conf)

            self.scene.removeItem(self.app.selected_item) # self.scene is app.scene
            if img_conf.get('id') in self.item_map: del self.item_map[img_conf['id']] # self.item_map is app.item_map

            self.app.selected_item = None # Update app's selected_item

            self.app.save_config() # Call app's save_config
            self.app.update_properties_panel() # Call app's method
            self.app.statusBar().showMessage(f"Image '{img_conf['path']}' deleted.", 3000) # app's statusBar

    def add_info_area(self):
        rect_id = f"rect_{datetime.datetime.now().timestamp()}"
        # Access app's config for defaults, then utils if not found
        default_display_conf = self.config.get("defaults", {}).get("info_rectangle_text_display", utils.get_default_config()["defaults"]["info_rectangle_text_display"])

        new_rect_config = {
            "id": rect_id,
            "center_x": self.scene.width() / 2, # self.scene is app.scene
            "center_y": self.scene.height() / 2, # self.scene is app.scene
            "width": default_display_conf.get("box_width", 150), # Use resolved default
            "height": 50, # Default height
            "text": "New Information",
            "show_on_hover": True,
            "shape": "rectangle",
            "z_index": self._get_next_z_index(), # Local method
        }

        if 'info_areas' not in self.config: self.config['info_areas'] = [] # self.config is app.config
        self.config['info_areas'].append(new_rect_config)

        item = InfoAreaItem(new_rect_config) # Z-value set in item's __init__

        # Connect signals to app's CanvasManager handlers
        item.item_selected.connect(self.app.canvas_manager.on_graphics_item_selected)
        item.item_moved.connect(self.app.canvas_manager.on_graphics_item_moved)
        item.properties_changed.connect(self.app.canvas_manager.on_graphics_item_properties_changed)

        self.scene.addItem(item) # self.scene is app.scene
        self.item_map[rect_id] = item # self.item_map is app.item_map

        self.app.save_config() # Call app's save_config
        self.app.statusBar().showMessage("Info rectangle added.", 2000) # app's statusBar

        self.scene.clearSelection() # self.scene is app.scene
        item.setSelected(True)

    def delete_selected_info_rect(self):
        if not isinstance(self.app.selected_item, InfoAreaItem): # Access app's selected_item
            QMessageBox.information(self.app, "Delete Info Area", "No info area selected.") # parent is self.app
            return

        rect_conf = self.app.selected_item.config_data
        reply = QMessageBox.question(self.app, "Confirm Delete", # parent is self.app
                                     "Are you sure you want to delete this info area?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            if rect_conf in self.config.get('info_areas', []): # self.config is app.config
                self.config['info_areas'].remove(rect_conf)

            self.scene.removeItem(self.app.selected_item) # self.scene is app.scene
            if rect_conf.get('id') in self.item_map: del self.item_map[rect_conf['id']] # self.item_map is app.item_map

            self.app.selected_item = None # Update app's selected_item

            self.app.save_config() # Call app's save_config
            self.app.update_properties_panel() # Call app's method
            self.app.statusBar().showMessage("Info rectangle deleted.", 2000) # app's statusBar

    def paste_item_from_clipboard(self): # Renamed and refactored
        """Pastes an item from the app's clipboard."""
        if self.app.clipboard_data is None:
            self.app.statusBar().showMessage("Clipboard is empty.", 2000)
            return False # Indicate failure

        # Currently, only InfoAreaItem paste is supported from original logic
        if not isinstance(self.app.clipboard_data, dict) or 'text' not in self.app.clipboard_data:
            self.app.statusBar().showMessage("Clipboard data is not for an info area.", 2000)
            return False # Indicate failure

        new_item_config = copy.deepcopy(self.app.clipboard_data) # Use app's clipboard_data

        # Assuming it's an InfoRectangle for now, based on original logic
        new_item_config['id'] = f"rect_{datetime.datetime.now().timestamp()}"
        new_item_config['center_x'] = new_item_config.get('center_x', self.scene.width() / 2) + 20 # self.scene is app.scene
        new_item_config['center_y'] = new_item_config.get('center_y', self.scene.height() / 2) + 20 # self.scene is app.scene
        new_item_config['z_index'] = self._get_next_z_index() # Local method

        if 'info_areas' not in self.config: # self.config is app.config
            self.config['info_areas'] = []
        self.config['info_areas'].append(new_item_config)

        item = InfoAreaItem(new_item_config) # Z-value set in item's __init__

        # Connect signals to app's CanvasManager handlers
        item.item_selected.connect(self.app.canvas_manager.on_graphics_item_selected)
        item.item_moved.connect(self.app.canvas_manager.on_graphics_item_moved)
        item.properties_changed.connect(self.app.canvas_manager.on_graphics_item_properties_changed)

        self.scene.addItem(item) # self.scene is app.scene
        self.item_map[new_item_config['id']] = item # self.item_map is app.item_map

        self.app.save_config() # Call app's save_config
        self.app.statusBar().showMessage("Info rectangle pasted.", 2000) # app's statusBar

        self.scene.clearSelection() # self.scene is app.scene
        item.setSelected(True)
        return True # Indicate success

    def connect_selected_info_areas(self):
        selected = [i for i in self.scene.selectedItems() if isinstance(i, InfoAreaItem)]
        if len(selected) != 2:
            return
        src_item, dst_item = selected[0], selected[1]
        line_id = f"conn_{datetime.datetime.now().timestamp()}"
        line_conf = {
            "id": line_id,
            "source": src_item.config_data.get('id'),
            "destination": dst_item.config_data.get('id'),
            "thickness": 2,
            "z_index": self._get_next_z_index(),
            "line_color": "#00ffff",
        }
        self.config.setdefault('connections', []).append(line_conf)
        from .connection_line_item import ConnectionLineItem
        line_item = ConnectionLineItem(line_conf, self.item_map)
        line_item.item_selected.connect(self.app.canvas_manager.on_graphics_item_selected)
        line_item.properties_changed.connect(self.app.canvas_manager.on_graphics_item_properties_changed)
        self.scene.addItem(line_item)
        self.item_map[line_id] = line_item
        line_item.update_position()
        self.app.save_config()
        self.scene.clearSelection()
        line_item.setSelected(True)
        self.app.selected_item = line_item
        self.app.update_properties_panel()

    def copy_selected_item_to_clipboard(self):
        if self.app.selected_item and isinstance(self.app.selected_item, InfoAreaItem) and \
           self.app.current_mode == "edit": # Check app's current_mode
            self.app.clipboard_data = copy.deepcopy(self.app.selected_item.config_data) # Use app's clipboard
            self.app.statusBar().showMessage("Info rectangle copied to clipboard.", 2000) # Use app's status bar
            return True
        return False

    def delete_selected_item_on_canvas(self):
        if self.app.selected_item and self.app.current_mode == "edit": # Check app's selected_item and current_mode
            if isinstance(self.app.selected_item, DraggableImageItem):
                self.delete_selected_image() # This method now uses self.app.selected_item
                return True
            elif isinstance(self.app.selected_item, InfoAreaItem):
                self.delete_selected_info_rect() # This method now uses self.app.selected_item
                return True
        return False
