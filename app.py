import sys
import os
import json
import datetime
import shutil  # For copying files
import copy  # For deep copying objects
import html

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QLineEdit, QColorDialog, QFileDialog, QGraphicsScene, QGraphicsView,
    QGraphicsTextItem, QGraphicsItem, QDockWidget, QComboBox, QSpinBox,
    QTextEdit, QMessageBox, QSizePolicy, QAction, QDoubleSpinBox,
    QGraphicsObject, QDialog, QListWidget, QListWidgetItem, QInputDialog
)
from PyQt5.QtGui import (
    QPixmap, QColor, QBrush, QPen, QFont, QImageReader, QTransform, QPainter, QFontMetrics, QCursor
)
from PyQt5.QtCore import Qt, QRectF, QPointF, pyqtSignal, QObject, QRect, QTimer

from src import utils
from src.draggable_image_item import DraggableImageItem
from src.info_rectangle_item import InfoRectangleItem
from src.project_manager_dialog import ProjectManagerDialog
from src.project_io import ProjectIO
from src.ui_builder import UIBuilder
from src.item_operations import ItemOperations
from src.text_style_manager import TextStyleManager
from src.exporter import HtmlExporter # <--- NEW IMPORT
# --- Main Application Window ---
class InteractiveToolApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1200, 700)
        utils.ensure_base_projects_directory_exists()
        self.project_io = ProjectIO()
        self.current_project_name = None
        self.current_project_path = None
        self.config = {}
        self.clipboard_data = None
        self.chronologically_first_selected_item = None

        if not self._initial_project_setup():
            QTimer.singleShot(0, self.close)
            return

        self.current_mode = "edit"
        self.selected_item = None
        self.item_map = {}
        self.text_style_manager = TextStyleManager(self) # Moved up
        UIBuilder(self).build()
        self.item_operations = ItemOperations(self)
        self.text_style_manager.load_styles_into_dropdown() # Ensure dropdown is populated early
        self.populate_controls_from_config()
        self.render_canvas_from_config()
        self.update_mode_ui()

    def _get_project_config_path(self, project_name_or_path):
        return self.project_io.get_project_config_path(project_name_or_path)

    def _get_project_images_folder(self, project_name_or_path):
        return self.project_io.get_project_images_folder(project_name_or_path)

    def _ensure_project_structure_exists(self, project_path):
        return self.project_io.ensure_project_structure_exists(project_path)

    def _update_window_title(self):
        if self.current_project_name:
            self.setWindowTitle(f"PyQt5 Interactive Image Tool - {self.current_project_name}")
        else:
            self.setWindowTitle("PyQt5 Interactive Image Tool - No Project Loaded")

    def _reset_application_to_no_project_state(self):
        """Resets the UI and internal state when no project is loaded or current is deleted."""
        self.current_project_name = None
        self.current_project_path = None
        self.config = {}
        self.selected_item = None
        self.item_map.clear()
        if hasattr(self, 'scene') and self.scene:
            self.scene.clear()
            # Optionally set a placeholder background or message on the scene
            self.scene.setBackgroundBrush(QBrush(QColor("#AAAAAA"))) 
        if hasattr(self, 'info_rect_properties_widget'): # Check if UI elements exist
            self.update_properties_panel() # Hide properties panels
            self.edit_mode_controls_widget.setEnabled(False) # Disable edit controls
        self._update_window_title()
        self.statusBar().showMessage("No project loaded. Please create or load a project from the File menu.")
        
        # Force user to select a project again
        QTimer.singleShot(100, self._show_project_manager_dialog_and_handle_outcome)


    def _show_project_manager_dialog_and_handle_outcome(self):
        """Shows project manager and handles if user cancels (closes app)."""
        if not self._initial_project_setup(): # Re-use initial setup logic
             QTimer.singleShot(0, self.close) # Close app if user cancels project selection again
        else:
            # If a project was successfully loaded/created, re-enable controls
            if hasattr(self, 'edit_mode_controls_widget'):
                self.edit_mode_controls_widget.setEnabled(True)
            self.populate_controls_from_config()
            self.render_canvas_from_config()
            self.update_mode_ui()


    def _handle_deleted_current_project(self, deleted_project_name):
        """Called when the currently loaded project is deleted."""
        if self.current_project_name == deleted_project_name:
            QMessageBox.information(self, "Project Deleted", 
                                    f"The current project '{deleted_project_name}' has been deleted. Please select or create a new project.")
            self._reset_application_to_no_project_state()


    def _initial_project_setup(self):
        dialog = ProjectManagerDialog(self, self.current_project_name)
        dialog.project_deleted_signal.connect(self._handle_deleted_current_project)
        if dialog.exec_() == QDialog.Accepted and dialog.selected_project_name:
            project_name = dialog.selected_project_name
            project_path = os.path.join(utils.PROJECTS_BASE_DIR, project_name)
            is_new = not os.path.exists(project_path)
            return self._switch_to_project(project_name, is_new_project=is_new)
        return False

    def _show_project_manager_dialog(self):
        dialog = ProjectManagerDialog(self, self.current_project_name) # Pass current project name
        dialog.project_deleted_signal.connect(self._handle_deleted_current_project)

        if dialog.exec_() == QDialog.Accepted and dialog.selected_project_name:
            project_name = dialog.selected_project_name
            
            if project_name == self.current_project_name and os.path.exists(self._get_project_config_path(project_name)):
                self.statusBar().showMessage(f"Project '{project_name}' is already loaded.", 2000)
                return

            is_new = not os.path.exists(os.path.join(utils.PROJECTS_BASE_DIR, project_name))
            
            if self._switch_to_project(project_name, is_new_project=is_new):
                if hasattr(self, 'scene') and self.scene:
                    self.scene.clear() 
                    self.item_map.clear()
                    self.selected_item = None
                    self.populate_controls_from_config()
                    self.render_canvas_from_config()
                    self.update_mode_ui()
                    if hasattr(self, 'edit_mode_controls_widget'):
                        self.edit_mode_controls_widget.setEnabled(True) # Ensure controls are enabled
                self.statusBar().showMessage(f"Switched to project: {project_name}", 3000)
            else:
                QMessageBox.warning(self, "Project Switch Failed", f"Could not switch to project '{project_name}'.")
                self._reset_application_to_no_project_state() # If switch fails, reset

    def _switch_to_project(self, project_name, is_new_project=False):
        success = self.project_io.switch_to_project(project_name, is_new_project)
        self.current_project_name = self.project_io.current_project_name
        self.current_project_path = self.project_io.current_project_path
        self.config = self.project_io.config
        if success:
            self._update_window_title()
            if hasattr(self, 'edit_mode_controls_widget'):
                self.edit_mode_controls_widget.setEnabled(True)
            if hasattr(self, 'text_style_manager') and self.text_style_manager: # Defensive check
                self.text_style_manager.load_styles_into_dropdown()
        return success

    def _load_config_for_current_project(self):
        return self.project_io.load_config_for_current_project()

    def save_config(self, config_data_to_save=None):
        config_to_save = config_data_to_save if config_data_to_save is not None else self.config
        return self.project_io.save_config(
            self.current_project_path,
            config_to_save,
            item_map=self.item_map,
            status_bar=self.statusBar() if hasattr(self, "statusBar") else None,
            current_project_name=self.current_project_name,
        )

    def setup_ui(self):
        UIBuilder(self).build()

    def populate_controls_from_config(self):
        if not self.config or not hasattr(self, 'bg_width_input'):
            return
        self.bg_width_input.blockSignals(True)
        self.bg_height_input.blockSignals(True)
        self.bg_width_input.setValue(self.config.get('background', {}).get('width', 800))
        self.bg_height_input.setValue(self.config.get('background', {}).get('height', 600))
        self.bg_width_input.blockSignals(False)
        self.bg_height_input.blockSignals(False)

    def on_mode_changed(self, mode_text):
        if "Edit" in mode_text:
            self.current_mode = "edit"
        else:
            self.current_mode = "view"
        self.update_mode_ui()
        self.render_canvas_from_config()

    def update_mode_ui(self):
        if not hasattr(self, 'edit_mode_controls_widget'): return
        is_edit_mode = self.current_mode == "edit"
        self.edit_mode_controls_widget.setVisible(is_edit_mode)
        self.view_mode_message_label.setVisible(not is_edit_mode)
        if hasattr(self, 'export_html_button'):
            self.export_html_button.setVisible(not is_edit_mode)
        for item_id, graphics_item in self.item_map.items():
            if isinstance(graphics_item, (DraggableImageItem, InfoRectangleItem)):
                graphics_item.setEnabled(is_edit_mode) 
                if isinstance(graphics_item, InfoRectangleItem):
                    graphics_item.update_appearance(graphics_item.isSelected(), not is_edit_mode)
            
            if is_edit_mode:
                 if isinstance(graphics_item, DraggableImageItem): 
                    graphics_item.setCursor(Qt.PointingHandCursor if graphics_item.isEnabled() else Qt.ArrowCursor)
            else: 
                graphics_item.setCursor(Qt.ArrowCursor)
                if isinstance(graphics_item, InfoRectangleItem):
                    graphics_item.setToolTip(graphics_item.config_data.get('text', ''))
                else:
                    graphics_item.setToolTip('')

        if not is_edit_mode:
            if hasattr(self, 'scene') and self.scene: self.scene.clearSelection()
            self.selected_item = None
        self.update_properties_panel()


    def choose_bg_color(self):
        current_color_hex = self.config.get('background', {}).get('color', '#DDDDDD')
        current_color = QColor(current_color_hex)
        color = QColorDialog.getColor(current_color, self, "Choose Background Color")
        if color.isValid():
            self.config['background']['color'] = color.name()
            if hasattr(self, 'scene') and self.scene : self.scene.setBackgroundBrush(QBrush(color))
            self.save_config()

    def update_bg_dimensions(self):
        if not self.config: return
        self.config['background']['width'] = self.bg_width_input.value()
        self.config['background']['height'] = self.bg_height_input.value()
        if hasattr(self, 'scene') and self.scene:
            self.scene.setSceneRect(0, 0,
                                     self.config['background']['width'],
                                     self.config['background']['height'])
        if hasattr(self, 'view') and self.view : self.view.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
        self.save_config()

    def render_canvas_from_config(self):
        if not self.config or not hasattr(self, 'scene') or not self.scene: return
        selected_item_id = None
        if self.selected_item:
            for item_id, gi in self.item_map.items():
                if gi == self.selected_item:
                    selected_item_id = item_id
                    break
        self.scene.clear()
        self.item_map.clear()
        bg_conf = self.config.get('background', utils.get_default_config()['background'])
        self.scene.setBackgroundBrush(QBrush(QColor(bg_conf['color'])))
        self.scene.setSceneRect(0, 0, bg_conf['width'], bg_conf['height'])
        current_project_images_folder = self._get_project_images_folder(self.current_project_path)
        if not current_project_images_folder:
            QMessageBox.critical(self, "Render Error", "Cannot determine images folder for the current project.")
            return
        for img_conf in self.config.get('images', []):
            image_path_in_config = img_conf.get('path', '')
            if not image_path_in_config:
                print(f"Warning: Image config missing path: {img_conf.get('id', 'Unknown ID')}")
                continue
            image_full_path = os.path.join(current_project_images_folder, image_path_in_config)
            pixmap = QPixmap(image_full_path)
            if pixmap.isNull():
                print(f"Warning: Could not load image '{image_path_in_config}' from '{current_project_images_folder}'. Creating placeholder.")
                pixmap = QPixmap(100, 100)
                pixmap.fill(Qt.lightGray)
                if not img_conf.get('original_width') or img_conf.get('original_width',0) <=0 : img_conf['original_width'] = 100
                if not img_conf.get('original_height') or img_conf.get('original_height',0) <=0 : img_conf['original_height'] = 100
            if not img_conf.get('original_width') or img_conf.get('original_width',0) <=0:
                img_conf['original_width'] = pixmap.width()
            if not img_conf.get('original_height') or img_conf.get('original_height',0) <=0:
                img_conf['original_height'] = pixmap.height()
            item = DraggableImageItem(pixmap, img_conf) # Z-value set in item's __init__
            scale = img_conf.get('scale', 1.0)
            transform = QTransform()
            transform.scale(scale, scale)
            item.setTransform(transform)
            center_x = img_conf.get('center_x', self.scene.width() / 2)
            center_y = img_conf.get('center_y', self.scene.height() / 2)
            scaled_width = img_conf['original_width'] * scale
            scaled_height = img_conf['original_height'] * scale
            item.setPos(center_x - scaled_width / 2, center_y - scaled_height / 2)
            item.item_selected.connect(self.on_graphics_item_selected)
            item.item_moved.connect(self.on_graphics_item_moved)
            self.scene.addItem(item)
            self.item_map[img_conf['id']] = item
        for rect_conf in self.config.get('info_rectangles', []):
            item = InfoRectangleItem(rect_conf) # Z-value set in item's __init__
            item.item_selected.connect(self.on_graphics_item_selected)
            item.item_moved.connect(self.on_graphics_item_moved)
            item.properties_changed.connect(self.on_graphics_item_properties_changed)
            self.scene.addItem(item)
            self.item_map[rect_conf['id']] = item

            # Apply referenced text style if it exists
            if 'text_style_ref' in rect_conf:
                style_name_to_apply = rect_conf['text_style_ref']
                found_style_object = None
                for style_obj in self.config.get('text_styles', []):
                    if style_obj.get('name') == style_name_to_apply:
                        found_style_object = style_obj
                        break

                if found_style_object:
                    item.apply_style(found_style_object) # This sets _style_config_ref and updates appearance
                else:
                    # Style reference exists but the style itself is not found.
                    print(f"Warning: InfoRectangle {rect_conf.get('id')} references style '{style_name_to_apply}' which was not found in text_styles.")
                    # Item will use its own rect_conf properties as fallback.
                    # InfoRectangleItem.__init__ already called update_text_from_config based on its own config.

        if selected_item_id and selected_item_id in self.item_map:
            self.selected_item = self.item_map[selected_item_id]
            if self.selected_item:
                self.selected_item.setSelected(True)
        else:
            self.selected_item = None
        self.update_mode_ui()
        self.update_properties_panel()

    def on_scene_selection_changed(self):
        if not hasattr(self, 'scene') or not self.scene:
            self.chronologically_first_selected_item = None
            self.selected_item = None
            self.update_properties_panel()
            return

        selected_items_from_scene = self.scene.selectedItems()
        current_selected_info_rects = [
            item for item in selected_items_from_scene if isinstance(item, InfoRectangleItem)
        ]
        num_selected = len(current_selected_info_rects)

        if num_selected == 0:
            self.chronologically_first_selected_item = None
        elif num_selected == 1:
            self.chronologically_first_selected_item = current_selected_info_rects[0]
        elif num_selected > 1:
            # If a chronologically_first_selected_item was already set and is still selected, keep it.
            # Otherwise, pick a new one based on sorting by ID (oldest).
            if self.chronologically_first_selected_item is None or \
               self.chronologically_first_selected_item not in current_selected_info_rects:
                # Sort by 'id' string. Assuming 'id' format is like 'rect_timestamp'.
                sorted_rects = sorted(current_selected_info_rects, key=lambda r: r.config_data.get('id', ''))
                if sorted_rects:
                    self.chronologically_first_selected_item = sorted_rects[0]
                else: # Should not happen if num_selected > 1
                    self.chronologically_first_selected_item = None
            # Else, if self.chronologically_first_selected_item is still valid and in the selection, do nothing to it.

        # Update appearance for all InfoRectangleItems based on their selection state
        # This should ideally happen after updating chronologically_first_selected_item and self.selected_item
        for item_in_scene_list in self.scene.items(): # Iterate over all items in scene to update appearance
            if isinstance(item_in_scene_list, InfoRectangleItem):
                item_in_scene_list.update_appearance(item_in_scene_list.isSelected(), self.current_mode == "view")

        # Update self.selected_item (potentially the last item clicked or primary selected item)
        # This logic might need adjustment based on how primary selection vs. multi-selection is handled.
        # The original logic was:
        if self.selected_item not in selected_items_from_scene: # If the old primary selected is no longer selected at all
            self.selected_item = selected_items_from_scene[-1] if selected_items_from_scene else None
        # If the old self.selected_item is still in selected_items_from_scene, it remains self.selected_item.
        # If there are multiple items and the old self.selected_item was deselected,
        # the last item in the current selection becomes the new self.selected_item.
        # This part might need to be harmonized with chronologically_first_selected_item if they are intended
        # to be the same under certain multi-selection scenarios (e.g., if only one item ends up being "active" for properties).
        # For now, keeping original logic for self.selected_item update mostly intact.
        # If selected_items_from_scene is not empty, and self.selected_item is not in it, update self.selected_item
        if selected_items_from_scene and self.selected_item not in selected_items_from_scene:
             self.selected_item = selected_items_from_scene[-1]
        elif not selected_items_from_scene: # No items selected
             self.selected_item = None


        self.update_properties_panel()

    def on_graphics_item_selected(self, graphics_item):
        if self.current_mode == "view":
            if hasattr(self, 'scene') and self.scene: self.scene.clearSelection()
            self.selected_item = None
            self.update_properties_panel()
            return

        ctrl_pressed = QApplication.keyboardModifiers() & Qt.ControlModifier

        if ctrl_pressed and isinstance(graphics_item, InfoRectangleItem):
            # Let Qt handle the selection toggle. Just update selected_item to
            # the item under the cursor if it ends up selected, otherwise fall
            # back to another selected item if any remain.
            if graphics_item.isSelected():
                self.selected_item = graphics_item
            else:
                remaining = self.scene.selectedItems() if hasattr(self, 'scene') else []
                self.selected_item = remaining[-1] if remaining else None
            self.update_properties_panel()
            return
        
        if self.selected_item is graphics_item and isinstance(self.selected_item, InfoRectangleItem):
            self.selected_item.update_appearance(True, self.current_mode == "view")
        
        if self.selected_item is not graphics_item :
            if self.selected_item and isinstance(self.selected_item, InfoRectangleItem): 
                self.selected_item.update_appearance(False, self.current_mode == "view")
            
            self.selected_item = graphics_item 
            
            if self.selected_item: 
                try:
                    if hasattr(self, 'scene') and self.scene: self.scene.selectionChanged.disconnect(self.on_scene_selection_changed)
                except TypeError: 
                    pass 
                
                if hasattr(self, 'scene') and self.scene:
                    for item_in_scene in self.scene.items():
                        if item_in_scene is not self.selected_item and item_in_scene.isSelected():
                            item_in_scene.setSelected(False)
                            if isinstance(item_in_scene, InfoRectangleItem): 
                                item_in_scene.update_appearance(False, self.current_mode == "view")
                
                self.selected_item.setSelected(True) 
                if isinstance(self.selected_item, InfoRectangleItem): 
                    self.selected_item.update_appearance(True, self.current_mode == "view")
                
                try:
                    if hasattr(self, 'scene') and self.scene: self.scene.selectionChanged.connect(self.on_scene_selection_changed)
                except TypeError: 
                    pass
        
        self.update_properties_panel()


    def on_graphics_item_moved(self, graphics_item):
        self.save_config()

    def on_graphics_item_properties_changed(self, graphics_item):
        self.save_config()
        if isinstance(graphics_item, InfoRectangleItem):
            graphics_item.update_geometry_from_config() 
            self.update_properties_panel() 

    def update_properties_panel(self):
        if not hasattr(self, 'image_properties_widget'): return # UI not fully set up
        self.image_properties_widget.setVisible(False)
        self.info_rect_properties_widget.setVisible(False)
        if not self.selected_item or self.current_mode == "view":
            return
        if isinstance(self.selected_item, DraggableImageItem):
            img_conf = self.selected_item.config_data
            self.img_scale_input.blockSignals(True)
            self.img_scale_input.setValue(img_conf.get('scale', 1.0))
            self.img_scale_input.blockSignals(False)
            self.image_properties_widget.setVisible(True)
        elif isinstance(self.selected_item, InfoRectangleItem):
            rect_conf = self.selected_item.config_data
            self.info_rect_text_input.blockSignals(True)
            self.info_rect_width_input.blockSignals(True)
            self.info_rect_height_input.blockSignals(True)
            self.info_rect_text_input.setPlainText(rect_conf.get('text', ''))
            self.info_rect_width_input.setValue(int(rect_conf.get('width', 100)))
            self.info_rect_height_input.setValue(int(rect_conf.get('height', 50)))

            # Update new formatting controls
            self.rect_h_align_combo.blockSignals(True)
            self.rect_v_align_combo.blockSignals(True)
            self.rect_font_size_combo.blockSignals(True)
            self.rect_font_bold_button.blockSignals(True)
            self.rect_font_italic_button.blockSignals(True)
            self.rect_style_combo.blockSignals(True)

            default_text_config = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
            current_style_ref = rect_conf.get('text_style_ref')

            # Set style combo based on item's state
            determined_style_name = "Custom" # Default to custom
            if current_style_ref:
                style_exists = any(s.get('name') == current_style_ref for s in self.config.get('text_styles', []))
                if style_exists:
                    # If text_style_ref is present and valid, use it.
                    # Changes by manager methods would clear text_style_ref if current props don't match.
                    determined_style_name = current_style_ref
                else:
                    # Referenced style does not exist, clear the reference
                    rect_conf.pop('text_style_ref', None)
                    # Fall through to determine if it's Default or matches another saved style or Custom

            if not rect_conf.get('text_style_ref'): # If no ref, or ref was just cleared
                if self.text_style_manager.does_item_match_default_style(rect_conf):
                    determined_style_name = "Default"
                else:
                    matched_style_name = self.text_style_manager.find_matching_style_name(rect_conf)
                    if matched_style_name:
                        determined_style_name = matched_style_name
                        # If it matches a style, the manager might have already re-linked it.
                        # Or, if we want to ensure it's linked when panel updates:
                        # rect_conf['text_style_ref'] = matched_style_name
                    else:
                        determined_style_name = "Custom"

            # Set the combo box
            style_idx = self.rect_style_combo.findText(determined_style_name)
            if style_idx != -1:
                self.rect_style_combo.setCurrentIndex(style_idx)
            else:
                # Fallback to Custom if determined_style_name is somehow not in the combo
                custom_idx = self.rect_style_combo.findText("Custom")
                if custom_idx != -1:
                    self.rect_style_combo.setCurrentIndex(custom_idx)

            h_align = rect_conf.get('horizontal_alignment', default_text_config['horizontal_alignment'])
            v_align = rect_conf.get('vertical_alignment', default_text_config['vertical_alignment'])
            font_style = rect_conf.get('font_style', default_text_config['font_style'])
            font_size = str(rect_conf.get('font_size', default_text_config['font_size'])).replace("px", "")

            self.rect_h_align_combo.setCurrentText(h_align.capitalize())
            self.rect_v_align_combo.setCurrentText(v_align.capitalize())

            # Ensure font_size is in the combo or set as current text
            f_size_idx = self.rect_font_size_combo.findText(font_size)
            if f_size_idx != -1:
                self.rect_font_size_combo.setCurrentIndex(f_size_idx)
            else:
                self.rect_font_size_combo.setEditText(font_size)

            self.rect_font_bold_button.setChecked(font_style == "bold")
            # Ensure italic is not checked if bold is true, and vice-versa if that's the desired logic.
            # Current rect_item logic: font_style can be "bold", "italic", or "normal" (exclusive)
            self.rect_font_italic_button.setChecked(font_style == "italic")

            self.rect_h_align_combo.blockSignals(False)
            self.rect_v_align_combo.blockSignals(False)
            self.rect_font_size_combo.blockSignals(False)
            self.rect_font_bold_button.blockSignals(False)
            self.rect_font_italic_button.blockSignals(False)
            self.rect_style_combo.blockSignals(False)

            # Update font color button preview
            current_font_color = rect_conf.get('font_color', default_text_config['font_color'])
            contrasting_color = self.text_style_manager.get_contrasting_text_color(current_font_color)
            self.rect_font_color_button.setStyleSheet(
                f"background-color: {current_font_color}; color: {contrasting_color};"
            )


            self.info_rect_text_input.blockSignals(False)
            self.info_rect_width_input.blockSignals(False)
            self.info_rect_height_input.blockSignals(False)
            self.info_rect_properties_widget.setVisible(True)

        # Alignment buttons visibility
        if hasattr(self, 'scene') and self.scene:
            selected_graphics_items = self.scene.selectedItems()
            selected_info_rect_count = 0
            for item in selected_graphics_items:
                if isinstance(item, InfoRectangleItem):
                    selected_info_rect_count += 1

            if selected_info_rect_count >= 2: # Changed condition from > 2 to >= 2
                self.align_horizontal_button.setVisible(True)
                self.align_vertical_button.setVisible(True)
            else:
                self.align_horizontal_button.setVisible(False)
                self.align_vertical_button.setVisible(False)
        else:
            self.align_horizontal_button.setVisible(False)
            self.align_vertical_button.setVisible(False)

        if not isinstance(self.selected_item, InfoRectangleItem) or self.current_mode == "view": # Also hide if not an InfoRect or in view mode
             # This check is a bit redundant if info_rect_properties_widget is already hidden,
             # but ensures buttons are hidden if the main widget for them is hidden.
             self.align_horizontal_button.setVisible(False)
             self.align_vertical_button.setVisible(False)
             # The rest of the else block for non-InfoRectangleItem selection
             if hasattr(self, 'rect_h_align_combo'): # Check if one of the new controls exists
                # Find the parent QWidget for the text_format_group to hide it
                # Assuming rect_props_layout.itemAt(1) is text_format_group (index might change based on final layout)
                # A safer way would be to keep a reference to text_format_group if it's complex
                # For now, let's assume it's the second direct widget in rect_props_layout (after text input)
                # Or, more simply, hide specific controls or the entire info_rect_properties_widget if no item is selected
                # The existing logic already hides info_rect_properties_widget if no item is selected or item is not InfoRect.
                # So, specific hiding of text_format_group might not be needed if it's part of info_rect_properties_widget.
                pass
        # Final check: if the main properties widget is hidden, alignment buttons should also be hidden.
        # This handles cases where self.selected_item might be None or not an InfoRectangleItem,
        # leading to info_rect_properties_widget being hidden earlier in this method.
        if not self.info_rect_properties_widget.isVisible():
            self.align_horizontal_button.setVisible(False)
            self.align_vertical_button.setVisible(False)


    # --- Handler for new formatting controls ---
    # def _on_rect_format_changed(self, value=None): # MOVED to TextStyleManager
    # def _on_rect_font_style_changed(self, checked=None): # MOVED to TextStyleManager
    # def _on_rect_font_color_button_clicked(self): # MOVED to TextStyleManager
    # def _get_contrasting_text_color(self, hex_color): # MOVED to TextStyleManager
    # def _load_text_styles_into_dropdown(self): # MOVED to TextStyleManager
    # def _save_current_text_style(self): # MOVED to TextStyleManager
    # def _on_rect_style_selected(self, style_name): # MOVED to TextStyleManager
    # def _does_current_rect_match_default_style(self, rect_config): # MOVED to TextStyleManager
    # def _find_matching_style_name(self, rect_config): # MOVED to TextStyleManager

    def upload_image(self):
        self.item_operations.upload_image()

    def update_selected_image_scale(self):
        self.item_operations.update_selected_image_scale()

    def delete_selected_image(self):
        self.item_operations.delete_selected_image()

    def add_info_rectangle(self):
        self.item_operations.add_info_rectangle()

    def update_selected_rect_text(self):
        """Called when the text in the info_rect_text_input (QTextEdit) changes."""
        if isinstance(self.selected_item, InfoRectangleItem):
            rect_conf = self.selected_item.config_data
            new_text = self.info_rect_text_input.toPlainText()

            if rect_conf.get('text') != new_text:
                rect_conf['text'] = new_text 
                self.selected_item.set_display_text(new_text) 
                self.save_config() 

    def update_selected_rect_dimensions(self): 
        """Called when width/height spinboxes in the properties panel change."""
        if isinstance(self.selected_item, InfoRectangleItem):
            rect_conf = self.selected_item.config_data
            new_width = self.info_rect_width_input.value()
            new_height = self.info_rect_height_input.value()

            rect_conf['width'] = max(self.selected_item.MIN_WIDTH, new_width)
            rect_conf['height'] = max(self.selected_item.MIN_HEIGHT, new_height)
            
            self.selected_item.properties_changed.emit(self.selected_item)


    def delete_selected_info_rect(self):
        self.item_operations.delete_selected_info_rect()

    def paste_info_rectangle(self): # Name remains same in app.py for now
        self.item_operations.paste_item_from_clipboard()

    # --- Z-order manipulation ---
    def bring_to_front(self):
        if self.selected_item:
            utils.bring_to_front(self.selected_item)
            self.save_config()

    def send_to_back(self):
        if self.selected_item:
            utils.send_to_back(self.selected_item)
            self.save_config()

    def bring_forward(self):
        if self.selected_item:
            utils.bring_forward(self.selected_item)
            self.save_config()

    def send_backward(self):
        if self.selected_item:
            utils.send_backward(self.selected_item)
            self.save_config()

    # --- Export functionality ---
    # def _generate_view_html(self): <--- THIS METHOD WILL BE ENTIRELY REMOVED

    def export_to_html(self, filepath=None): # Argument can be bool due to signal connection
        """Export the current project view to an HTML file."""
        if isinstance(filepath, bool) or filepath is None: # Handle signal default arg or no arg
            if not self.current_project_name: # Check if a project is loaded
                QMessageBox.warning(self, "Export Error", "No project loaded to export.")
                return

            default_name = f"{self.current_project_name}.html"
            filepath_tuple = QFileDialog.getSaveFileName(
                self,
                "Export to HTML",
                default_name,
                "HTML Files (*.html)",
                options=QFileDialog.Options()
            )
            # QFileDialog.getSaveFileName returns a tuple (filepath, filter)
            # or (False, False) if PySide/PyQt version differences, or just empty string
            if isinstance(filepath_tuple, tuple):
                filepath = filepath_tuple[0]
            else: # Should be caught by the 'if not filepath' check anyway
                filepath = str(filepath_tuple)


            if not filepath: # User cancelled dialog or no path entered
                return

        # Ensure config is present (though current_project_name check above often implies config exists)
        if not self.config:
            QMessageBox.warning(self, "Export Error", "Configuration is missing. Cannot export.")
            return

        # Ensure current_project_path is set, which HtmlExporter will need
        if not self.current_project_path:
            QMessageBox.warning(self, "Export Error", "Current project path is not set. Cannot export.")
            return

        try:
            exporter = HtmlExporter(config=self.config, project_path=self.current_project_path)
            success = exporter.export(str(filepath)) # Ensure filepath is a string

            if success:
                QMessageBox.information(self, "Export Complete", f"Exported to {filepath}")
            else:
                # HtmlExporter.export() now prints its own errors to console.
                # A general message here is still good for the UI.
                QMessageBox.critical(self, "Export Error", f"Failed to export HTML to {filepath}. Check console for details.")
        except Exception as e:
            # Catch any unexpected errors during exporter instantiation or call
            QMessageBox.critical(self, "Export Error", f"An unexpected error occurred during export: {e}")


    def keyPressEvent(self, event):
        focused_widget = QApplication.focusWidget()
        is_input_focused = isinstance(focused_widget, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox))

        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_C:
                if self.current_mode == "edit" and not is_input_focused and self.item_operations.copy_selected_item_to_clipboard():
                    event.accept()
                    return
            elif event.key() == Qt.Key_V:
                if self.current_mode == "edit" and not is_input_focused: # Basic check
                    if self.item_operations.paste_item_from_clipboard(): # Directly call item_operations method
                         event.accept()
                         return
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            if self.current_mode == "edit" and not is_input_focused and self.item_operations.delete_selected_item_on_canvas():
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)

    # Placeholder methods for alignment
    def align_selected_rects_horizontally(self):
        if not hasattr(self, 'scene') or not self.scene:
            return

        selected_graphics_items = self.scene.selectedItems()
        selected_info_rects = []
        for item in selected_graphics_items:
            if isinstance(item, InfoRectangleItem):
                selected_info_rects.append(item)

        if len(selected_info_rects) < 2:
            return

        if self.chronologically_first_selected_item is None or \
           self.chronologically_first_selected_item not in selected_info_rects:
            self.statusBar().showMessage("Cannot determine the source item for alignment. Please select items one by one if issues persist.", 3000)
            return

        source_rect = self.chronologically_first_selected_item
        target_x = source_rect.config_data.get('center_x', 0)

        for rect in selected_info_rects:
            rect.config_data['center_x'] = target_x
            # rect.config_data['center_y'] remains unchanged
            rect.update_geometry_from_config()
            # Ensure properties_changed is emitted so save_config and UI updates are triggered
            # if rect has such a signal and it's connected to on_graphics_item_properties_changed
            if hasattr(rect, 'properties_changed') and hasattr(rect.properties_changed, 'emit'):
                 rect.properties_changed.emit(rect)
            # Fallback to directly calling on_graphics_item_properties_changed if signal not present/connected
            # elif hasattr(self, 'on_graphics_item_properties_changed'):
            #    self.on_graphics_item_properties_changed(rect)


        # self.save_config() # This should be triggered by the properties_changed signal chain

    def align_selected_rects_vertically(self):
        if not hasattr(self, 'scene') or not self.scene:
            return

        selected_graphics_items = self.scene.selectedItems()
        selected_info_rects = []
        for item in selected_graphics_items:
            if isinstance(item, InfoRectangleItem):
                selected_info_rects.append(item)

        if len(selected_info_rects) < 2:
            return

        if self.chronologically_first_selected_item is None or \
           self.chronologically_first_selected_item not in selected_info_rects:
            self.statusBar().showMessage("Cannot determine the source item for alignment. Please select items one by one if issues persist.", 3000)
            return

        source_rect = self.chronologically_first_selected_item
        target_y = source_rect.config_data.get('center_y', 0)

        for rect in selected_info_rects:
            # rect.config_data['center_x'] remains unchanged
            rect.config_data['center_y'] = target_y
            rect.update_geometry_from_config()
            # Ensure properties_changed is emitted so save_config and UI updates are triggered
            if hasattr(rect, 'properties_changed') and hasattr(rect.properties_changed, 'emit'):
                 rect.properties_changed.emit(rect)
            # Fallback for safety, though direct signal emission is preferred.
            # elif hasattr(self, 'on_graphics_item_properties_changed'):
            #    self.on_graphics_item_properties_changed(rect)

        # self.save_config() # This should be triggered by the properties_changed signal chain

if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    
    main_window = InteractiveToolApp()
    if main_window.current_project_name: 
        main_window.show()
        sys.exit(app.exec_())
    else:
        print("Application initialization failed: No project loaded or startup cancelled.")
        if not main_window.isVisible(): 
            sys.exit(0) 
