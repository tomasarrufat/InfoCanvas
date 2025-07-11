import sys
import os
import copy

from PyQt5.QtWidgets import (
    QApplication, QColorDialog, QFileDialog, QMessageBox, QDialog, QStatusBar
)
from PyQt5.QtGui import (
    QColor, QBrush, QPalette
)
from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.sip import isdeleted

from src.frameless_window import FramelessWindow
from src import utils
from src.draggable_image_item import DraggableImageItem
from src.info_area_item import InfoAreaItem
from src.connection_line_item import ConnectionLineItem
from src.project_manager_dialog import ProjectManagerDialog
from src.project_io import ProjectIO
from src.ui_builder import UIBuilder
from src.item_operations import ItemOperations
from src.text_style_manager import TextStyleManager
from src.line_style_manager import LineStyleManager
from src.exporter import HtmlExporter # <--- NEW IMPORT
from src.input_handler import InputHandler
from src.canvas_manager import CanvasManager
# --- Main Application Window ---
class InfoCanvasApp(FramelessWindow):
    MAX_UNDO_HISTORY = 100 # Maximum number of undo snapshots to keep
    def __init__(self):
        super().__init__()
        utils.ensure_base_projects_directory_exists()
        self.project_io = ProjectIO()
        self.current_project_name = None
        self.current_project_path = None
        self.config = {}
        self.config_snapshot_stack = []
        self.clipboard_data = None
        self.chronologically_first_selected_item = None

        self.apply_dark_palette()

        if not self._initial_project_setup():
            QTimer.singleShot(0, self.close)
            return

        self.current_mode = "edit"
        self.selected_item = None
        self.item_map = {}
        self.text_style_manager = TextStyleManager(self)
        self.line_style_manager = LineStyleManager(self)
        UIBuilder(self).build()

        self.canvas_manager = CanvasManager(self)
        self.item_operations = ItemOperations(self)
        self.input_handler = InputHandler(self)
        self.text_style_manager.load_styles_into_dropdown()
        self.line_style_manager.load_styles_into_dropdown()

        # Connect the new checkbox signal AFTER UI is built and element exists
        if hasattr(self, 'rect_show_on_hover_connected_checkbox'):
            self.rect_show_on_hover_connected_checkbox.stateChanged.connect(
                self.update_selected_rect_show_on_hover_connected_state
            )
        # else: # This case should ideally not be hit if UIBuilder works as expected.
            # print("DEBUG: rect_show_on_hover_connected_checkbox not found during app init for signal connection.")

        self.populate_controls_from_config()
        self.render_canvas_from_config()
        self.update_mode_ui()

    def statusBar(self):
        """Return the QStatusBar instance for compatibility with QMainWindow."""
        return getattr(self, "status_bar", None)

    def showEvent(self, event):
        super().showEvent(event)
        # Ensure view scrollbars are positioned at the top-left when the window first shows
        if hasattr(self, 'view'):
            hbar = self.view.horizontalScrollBar()
            vbar = self.view.verticalScrollBar()
            if hbar:
                hbar.setValue(hbar.minimum())
            if vbar:
                vbar.setValue(vbar.minimum())

    def _get_project_config_path(self, project_name_or_path):
        return self.project_io.get_project_config_path(project_name_or_path)

    def _get_project_images_folder(self, project_name_or_path):
        return self.project_io.get_project_images_folder(project_name_or_path)

    def _ensure_project_structure_exists(self, project_path):
        return self.project_io.ensure_project_structure_exists(project_path)

    def _update_window_title(self):
        if hasattr(self, 'title_bar') and self.title_bar: # Ensure title_bar exists
            if self.current_project_name:
                self.title_bar.title.setText(f"InfoCanvas - {self.current_project_name}")
            else:
                self.title_bar.title.setText("InfoCanvas - No Project Loaded")
        # Also call super's setWindowTitle for OS taskbar (optional, FramelessWindow sets a default)
        # super().setWindowTitle(f"InfoCanvas - {self.current_project_name if self.current_project_name else 'No Project'}")

    def _reset_application_to_no_project_state(self):
        """Resets the UI and internal state when no project is loaded or current is deleted."""
        self.current_project_name = None
        self.current_project_path = None
        self.config = {}
        self.config_snapshot_stack.clear()
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
        if self.status_bar is not None:
            self.status_bar.showMessage(
                "No project loaded. Please create or load a project from the File menu."
            )

        if hasattr(self, 'item_operations'):
            self.item_operations.config = self.config

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
                # status_bar = self.statusBar() # Removed
                # if status_bar is not None: # Removed
                    # status_bar.showMessage(f"Project '{project_name}' is already loaded.", 2000) # Removed
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
                # status_bar = self.statusBar() # Removed
                # if hasattr(self, 'statusBar') and status_bar is not None: # Removed
                    # status_bar.showMessage(f"Switched to project: {project_name}", 3000) # Removed
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
            if hasattr(self, 'text_style_manager') and self.text_style_manager:
                self.text_style_manager.load_styles_into_dropdown()
            if hasattr(self, 'line_style_manager') and self.line_style_manager:
                self.line_style_manager.load_styles_into_dropdown()
            # Reset snapshot history to the loaded project's state
            self.config_snapshot_stack = [copy.deepcopy(self.config)]
            if hasattr(self, 'item_operations'):
                self.item_operations.config = self.config
        return success

    def _load_config_for_current_project(self):
        return self.project_io.load_config_for_current_project()

    def save_config(self, config_data_to_save=None):
        config_to_save = config_data_to_save if config_data_to_save is not None else self.config
        
        
        # Save the config and check if it was actually saved
        was_saved = self.project_io.save_config(
            self.current_project_path,
            config_to_save,
            item_map=self.item_map,
            status_bar=self.status_bar,
            current_project_name=self.current_project_name,
        )

        # Only update the snapshot stack if the config was actually saved
        if was_saved and (not self.config_snapshot_stack or config_to_save != self.config_snapshot_stack[-1]):
            self.config_snapshot_stack.append(copy.deepcopy(config_to_save))
            if len(self.config_snapshot_stack) > self.MAX_UNDO_HISTORY:
                self.config_snapshot_stack.pop(0)
        
        return was_saved

    def undo_last_action(self):
        """Revert to the previous configuration state if available."""
        if len(self.config_snapshot_stack) <= 1:
            return
        # Remove the most recent state and restore the previous one
        self.config_snapshot_stack.pop()
        self.config = copy.deepcopy(self.config_snapshot_stack[-1])
        self.populate_controls_from_config()
        self.render_canvas_from_config()

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

        if self.current_mode == "view" and hasattr(self, "web_view"):
            exporter = HtmlExporter(config=self.config, project_path=self.current_project_path)
            html_content = exporter._generate_html_content()
            base_url = QUrl.fromLocalFile(os.path.join(self.current_project_path, ""))
            self.web_view.setHtml(html_content, base_url)
            if hasattr(self, "central_layout"):
                self.central_layout.setCurrentWidget(self.web_view)
            self.view.hide()
            self.web_view.show()
        elif self.current_mode == "edit" and hasattr(self, "web_view"):
            if hasattr(self, "central_layout"):
                self.central_layout.setCurrentWidget(self.view)
            self.web_view.hide()
            self.view.show()

    def update_mode_ui(self):
        if not hasattr(self, 'edit_mode_controls_widget'): return
        is_edit_mode = self.current_mode == "edit"
        self.edit_mode_controls_widget.setVisible(is_edit_mode)
        self.view_mode_message_label.setVisible(not is_edit_mode)
        if hasattr(self, 'export_html_button'):
            self.export_html_button.setVisible(not is_edit_mode)
        for item_id, graphics_item in self.item_map.items():
            if isinstance(graphics_item, (DraggableImageItem, InfoAreaItem)):
                graphics_item.setEnabled(is_edit_mode) 
                if isinstance(graphics_item, InfoAreaItem):
                    graphics_item.update_appearance(graphics_item.isSelected(), not is_edit_mode)
            
            if is_edit_mode:
                 if isinstance(graphics_item, DraggableImageItem):
                    graphics_item.setCursor(Qt.CursorShape.PointingHandCursor if graphics_item.isEnabled() else Qt.CursorShape.ArrowCursor)
            else:
                graphics_item.setCursor(Qt.CursorShape.ArrowCursor)
                if isinstance(graphics_item, InfoAreaItem):
                    if graphics_item.config_data.get('show_on_hover', True):
                        graphics_item.setToolTip(graphics_item.config_data.get('text', ''))
                    else:
                        graphics_item.setToolTip('')
                else:
                    graphics_item.setToolTip('')

        if not is_edit_mode:
            if hasattr(self, 'scene') and self.scene: self.scene.clearSelection()
            self.selected_item = None
        self.update_properties_panel()

    def _reset_status_bar_message(self, timeout=2000):
        """Reset the status bar message after a timeout."""
        if self.status_bar is not None:
            self.status_bar.showMessage("", timeout)

    def _show_temporary_message(self, message, timeout=2000):
        """Show a temporary message in the status bar."""
        if self.status_bar is not None:
            self.status_bar.showMessage(message, timeout)

    def _show_permanent_message(self, message):
        """Show a permanent message in the status bar (until changed)."""
        if self.status_bar is not None:
            self.status_bar.showMessage(message)

    def _clear_status_bar_message(self):
        """Clear the status bar message."""
        if self.status_bar is not None:
            self.status_bar.clearMessage()

    def _set_status_bar_style(self, background_color, text_color):
        """Set the style of the status bar."""
        if self.status_bar is not None:
            self.status_bar.setStyleSheet(f"background-color: {background_color}; color: {text_color};")

    def _reset_status_bar_style(self):
        """Reset the status bar style to default."""
        if self.status_bar is not None:
            self.status_bar.setStyleSheet("")

    class _LabelStatusBar:
        def __init__(self, label):
            self.label = label
        def showMessage(self, msg):
            if self.label:
                self.label.setText(msg)

    def choose_bg_color(self):
        # Ensure config and background section exist
        if not isinstance(self.config, dict):
            self.config = utils.get_default_config()
        if 'background' not in self.config or not isinstance(self.config['background'], dict):
            self.config['background'] = utils.get_default_config()['background']

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
        if hasattr(self, 'view') and self.view : self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.save_config()

    def render_canvas_from_config(self):
        self.canvas_manager.render_canvas_from_config()

    def on_scene_selection_changed(self):
        self.canvas_manager.on_scene_selection_changed()
        # This is a primary trigger for updating the checkbox visibility
        if hasattr(self, 'update_hover_connected_checkbox_visibility'):
            self.update_hover_connected_checkbox_visibility()

    def update_properties_panel(self):
        # Call this at the beginning of updating properties panel as well,
        # as selection might make the checkbox (in)visible or change its state.
        if hasattr(self, 'update_hover_connected_checkbox_visibility'):
            self.update_hover_connected_checkbox_visibility()

        if not hasattr(self, 'image_properties_widget'):
            return  # UI not fully set up
        # Avoid manipulating widgets that might have been deleted during shutdown
        if isdeleted(self.image_properties_widget) or isdeleted(self.info_rect_properties_widget):
            return
        self.image_properties_widget.setVisible(False)
        self.info_rect_properties_widget.setVisible(False)
        self.line_properties_widget.setVisible(False)
        self.align_horizontal_button.setVisible(False)
        self.align_vertical_button.setVisible(False)
        self.connect_rects_button.setVisible(False)
        if hasattr(self, 'info_rect_detail_widget'):
            self.info_rect_detail_widget.setVisible(False)

        if not self.selected_item or self.current_mode == "view":
            return

        selected_info_rect_count = 0
        if hasattr(self, 'scene') and self.scene:
            selected_info_rect_count = sum(
                1 for i in self.scene.selectedItems() if isinstance(i, InfoAreaItem)
            )

        if selected_info_rect_count >= 2:
            self.align_horizontal_button.setVisible(True)
            self.align_vertical_button.setVisible(True)
            if selected_info_rect_count == 2:
                rects = [i for i in self.scene.selectedItems() if isinstance(i, InfoAreaItem)]
                if len(rects) == 2:
                    id1 = rects[0].config_data.get('id')
                    id2 = rects[1].config_data.get('id')
                    if self.connection_exists(id1, id2):
                        self.connect_rects_button.setText("Disconnect Areas")
                        self.connect_rects_button.setVisible(True)
                    elif self.item_operations._connection_allowed(id1, id2):
                        self.connect_rects_button.setText("Connect Selected Areas")
                        self.connect_rects_button.setVisible(True)
                    else:
                        self.connect_rects_button.setVisible(False)
            self.info_rect_properties_widget.setVisible(True)
            return

        if isinstance(self.selected_item, DraggableImageItem):
            img_conf = self.selected_item.config_data
            self.img_scale_input.blockSignals(True)
            self.img_scale_input.setValue(img_conf.get('scale', 1.0))
            self.img_scale_input.blockSignals(False)
            self.image_properties_widget.setVisible(True)
        elif isinstance(self.selected_item, InfoAreaItem):
            rect_conf = self.selected_item.config_data
            self.info_rect_text_input.blockSignals(True)
            self.info_rect_width_input.blockSignals(True)
            self.info_rect_height_input.blockSignals(True)
            self.info_rect_text_input.setPlainText(rect_conf.get('text', ''))
            self.info_rect_width_input.setValue(int(rect_conf.get('width', 100)))
            self.info_rect_height_input.setValue(int(rect_conf.get('height', 50)))

            # Angle input
            self.info_rect_angle_input.blockSignals(True)
            self.info_rect_angle_input.setValue(rect_conf.get('angle', 0.0))
            self.info_rect_angle_input.blockSignals(False)

            self.area_shape_combo.blockSignals(True)
            current_shape = rect_conf.get('shape', 'rectangle')
            self.area_shape_combo.setCurrentText('Ellipse' if current_shape == 'ellipse' else 'Rectangle')
            self.area_shape_combo.blockSignals(False)
            self.rect_show_on_hover_checkbox.blockSignals(True)
            self.rect_show_on_hover_checkbox.setChecked(rect_conf.get('show_on_hover', True))
            self.rect_show_on_hover_checkbox.blockSignals(False)

            if hasattr(self, 'rect_area_color_button'):
                current_area_color = rect_conf.get('fill_color', '#007BFF')
                contrast = self.text_style_manager.get_contrasting_text_color(current_area_color)
                self.rect_area_color_button.setStyleSheet(f"background-color: {current_area_color}; color: {contrast};")

            if hasattr(self, 'rect_area_opacity_spin'):
                self.rect_area_opacity_spin.blockSignals(True)
                val = rect_conf.get('fill_alpha', 0.1)
                try:
                    val = float(val)
                except Exception:
                    val = 0.1
                if val > 1:
                    val = val / 255.0
                self.rect_area_opacity_spin.setValue(val)
                self.rect_area_opacity_spin.blockSignals(False)

            # Update new formatting controls
            self.rect_h_align_combo.blockSignals(True)
            self.rect_v_align_combo.blockSignals(True)
            self.rect_font_size_combo.blockSignals(True)
            self.rect_style_combo.blockSignals(True)

            default_text_config = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
            current_style_ref = rect_conf.get('style_ref')

            # Set style combo based on item's state
            determined_style_name = "Custom" # Default to custom
            if current_style_ref:
                # Ensure 's' is a dictionary before calling get()
                style_exists = any(isinstance(s, dict) and s is not None and s.get('name') == current_style_ref for s in self.config.get('info_area_styles', []))
                if style_exists:
                # If style_ref is present and valid, use it.
                # Changes by manager methods would clear style_ref if current props don't match.
                    determined_style_name = current_style_ref
                else:
                    # Referenced style does not exist, clear the reference
                    rect_conf.pop('style_ref', None)
                    # Fall through to determine if it's Default or matches another saved style or Custom

            if not rect_conf.get('style_ref'): # If no ref, or ref was just cleared
                if self.text_style_manager.does_item_match_default_style(rect_conf):
                    determined_style_name = "Default"
                else:
                    matched_style_name = self.text_style_manager.find_matching_style_name(rect_conf)
                    if matched_style_name:
                        determined_style_name = matched_style_name
                        # If it matches a style, the manager might have already re-linked it.
                        # Or, if we want to ensure it's linked when panel updates:
                        # rect_conf['style_ref'] = matched_style_name
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
            font_size = str(rect_conf.get('font_size', default_text_config['font_size'])).replace("px", "")

            self.rect_h_align_combo.setCurrentText(h_align.capitalize())
            self.rect_v_align_combo.setCurrentText(v_align.capitalize())

            # Ensure font_size is in the combo or set as current text
            f_size_idx = self.rect_font_size_combo.findText(font_size)
            if f_size_idx != -1:
                self.rect_font_size_combo.setCurrentIndex(f_size_idx)
            else:
                self.rect_font_size_combo.setEditText(font_size)

            self.rect_h_align_combo.blockSignals(False)
            self.rect_v_align_combo.blockSignals(False)
            self.rect_font_size_combo.blockSignals(False)
            self.rect_style_combo.blockSignals(False)
            self.area_shape_combo.blockSignals(False)

            # Update font color button preview
            current_font_color = rect_conf.get('font_color', default_text_config['font_color'])
            contrasting_color = self.text_style_manager.get_contrasting_text_color(current_font_color)
            self.rect_font_color_button.setStyleSheet(
                f"background-color: {current_font_color}; color: {contrasting_color};"
            )


            self.info_rect_text_input.blockSignals(False)
            self.info_rect_width_input.blockSignals(False)
            self.info_rect_height_input.blockSignals(False)
            if hasattr(self, 'info_rect_detail_widget'):
                self.info_rect_detail_widget.setVisible(True)
            self.info_rect_properties_widget.setVisible(True)
        elif isinstance(self.selected_item, ConnectionLineItem):
            line_conf = self.selected_item.config_data
            self.line_thickness_spin.blockSignals(True)
            self.line_z_index_spin.blockSignals(True)
            self.line_opacity_spin.blockSignals(True)
            self.line_thickness_spin.setValue(int(line_conf.get('thickness', 2)))
            self.line_z_index_spin.setValue(int(line_conf.get('z_index', 0)))
            self.line_opacity_spin.setValue(float(line_conf.get('opacity', 1.0)))
            self.line_thickness_spin.blockSignals(False)
            self.line_z_index_spin.blockSignals(False)
            self.line_opacity_spin.blockSignals(False)
            current_color = line_conf.get('line_color', '#00ffff')
            self.line_color_button.setStyleSheet(f"background-color: {current_color};")
            if hasattr(self, 'line_style_combo'):
                self.line_style_combo.blockSignals(True)
                determined = 'Custom'
                current_style_ref = line_conf.get('line_style_ref')
                if current_style_ref:
                    if any(
                        isinstance(s, dict) and s.get('name') == current_style_ref
                        for s in self.config.get('line_styles', [])
                    ):
                        determined = current_style_ref
                    else:
                        line_conf.pop('line_style_ref', None)
                idx = self.line_style_combo.findText(determined)
                if idx != -1:
                    self.line_style_combo.setCurrentIndex(idx)
                else:
                    custom_idx = self.line_style_combo.findText('Custom')
                    if custom_idx != -1:
                        self.line_style_combo.setCurrentIndex(custom_idx)
                self.line_style_combo.blockSignals(False)
            self.line_properties_widget.setVisible(True)

        # Final check: if the main properties widget is hidden, alignment buttons should also be hidden.
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
        self.item_operations.add_info_area()

    def update_selected_rect_text(self):
        """Called when the text in the info_rect_text_input (QTextEdit) changes."""
        if isinstance(self.selected_item, InfoAreaItem):
            rect_conf = self.selected_item.config_data
            new_text = self.info_rect_text_input.toPlainText()

            if rect_conf.get('text') != new_text:
                rect_conf['text'] = new_text 
                self.selected_item.set_display_text(new_text) 
                self.save_config() 

    def update_selected_rect_dimensions(self):
        """Called when width/height spinboxes in the properties panel change."""
        if isinstance(self.selected_item, InfoAreaItem):
            rect_conf = self.selected_item.config_data
            new_width = self.info_rect_width_input.value()
            new_height = self.info_rect_height_input.value()

            rect_conf['width'] = max(self.selected_item.MIN_WIDTH, new_width)
            rect_conf['height'] = max(self.selected_item.MIN_HEIGHT, new_height)
            
            self.selected_item.properties_changed.emit(self.selected_item)

    def update_selected_rect_show_on_hover(self, state):
        if isinstance(self.selected_item, InfoAreaItem):
            rect_conf = self.selected_item.config_data
            rect_conf['show_on_hover'] = bool(state)
            self.selected_item.update_appearance(self.selected_item.isSelected(), self.current_mode == "view")
            self.save_config()
            if hasattr(self, 'update_hover_connected_checkbox_visibility'):
                self.update_hover_connected_checkbox_visibility()

    def update_selected_rect_show_on_hover_connected_state(self, state):
        if not hasattr(self, 'scene') or not self.scene or not self.selected_item:
            return
        if isinstance(self.selected_item, InfoAreaItem):
            rect_conf = self.selected_item.config_data
            is_checked = bool(state == Qt.Checked)
            # Only update and save if the value actually changed
            if rect_conf.get('show_on_hover_connected') != is_checked:
                rect_conf['show_on_hover_connected'] = is_checked
                # Emit properties_changed which should lead to save_config via on_graphics_item_properties_changed
                self.selected_item.properties_changed.emit(self.selected_item)

    def count_connections_for_item(self, item_id):
        count = 0
        if not item_id: return 0
        for connection in self.config.get('connections', []):
            if connection.get('source') == item_id or connection.get('destination') == item_id:
                count += 1
        return count

    def update_hover_connected_checkbox_visibility(self):
        if not hasattr(self, 'rect_show_on_hover_connected_checkbox') or \
           not hasattr(self, 'rect_show_on_hover_checkbox') or \
           not hasattr(self, 'scene') or not self.scene:
            # This can happen if called too early or if UI elements are missing
            # print("DEBUG: update_hover_connected_checkbox_visibility prerequisites not met.")
            return

        selected_items = self.scene.selectedItems()
        if len(selected_items) == 1 and isinstance(selected_items[0], InfoAreaItem):
            selected_item = selected_items[0]
            item_id = selected_item.config_data.get('id')

            main_hover_checked = self.rect_show_on_hover_checkbox.isChecked()
            connection_count = self.count_connections_for_item(item_id)

            # Show the new checkbox only if the main "show on hover" is UNCHECKED and there's exactly ONE connection
            if not main_hover_checked and connection_count == 1:
                self.rect_show_on_hover_connected_checkbox.setVisible(True)
                # Set its state based on item's config, block signals to prevent immediate callback
                current_val = selected_item.config_data.get('show_on_hover_connected', False)
                self.rect_show_on_hover_connected_checkbox.blockSignals(True)
                self.rect_show_on_hover_connected_checkbox.setChecked(current_val)
                self.rect_show_on_hover_connected_checkbox.blockSignals(False)
            else:
                self.rect_show_on_hover_connected_checkbox.setVisible(False)
                self.rect_show_on_hover_connected_checkbox.blockSignals(True)
                self.rect_show_on_hover_connected_checkbox.setChecked(False) # Reset when hidden
                self.rect_show_on_hover_connected_checkbox.blockSignals(False)
        else:
            self.rect_show_on_hover_connected_checkbox.setVisible(False)
            self.rect_show_on_hover_connected_checkbox.blockSignals(True)
            self.rect_show_on_hover_connected_checkbox.setChecked(False) # Reset when hidden
            self.rect_show_on_hover_connected_checkbox.blockSignals(False)

    def update_selected_area_shape(self, shape_label):
        if isinstance(self.selected_item, InfoAreaItem):
            new_shape = 'ellipse' if shape_label.lower() == 'ellipse' else 'rectangle'
            rect_conf = self.selected_item.config_data
            if rect_conf.get('shape') != new_shape:
                rect_conf['shape'] = new_shape
                self.selected_item.shape_type = new_shape
                self.selected_item.update()
                self.selected_item.properties_changed.emit(self.selected_item)

    def update_selected_item_angle(self, angle_value):
        if isinstance(self.selected_item, InfoAreaItem):
            self.selected_item.config_data['angle'] = angle_value
            # update_geometry_from_config will handle setRotation and setTransformOriginPoint
            self.selected_item.update_geometry_from_config()
            # Emit properties_changed to ensure everything (like saving) is triggered
            self.selected_item.properties_changed.emit(self.selected_item)
            # self.save_config() # properties_changed should trigger save via on_graphics_item_properties_changed

    def delete_selected_info_rect(self):
        self.item_operations.delete_selected_info_rect()

    def paste_info_rectangle(self): # Name remains same in app.py for now
        self.item_operations.paste_item_from_clipboard()

    def connect_selected_info_areas(self):
        self.item_operations.connect_selected_info_areas()

    def disconnect_selected_info_areas(self):
        self.item_operations.disconnect_selected_info_areas()

    def on_connect_disconnect_clicked(self):
        if not hasattr(self, 'scene') or not self.scene:
            return
        selected = [i for i in self.scene.selectedItems() if isinstance(i, InfoAreaItem)]
        if len(selected) != 2:
            return
        id1 = selected[0].config_data.get('id')
        id2 = selected[1].config_data.get('id')
        if self.connection_exists(id1, id2):
            self.disconnect_selected_info_areas() # This calls item_operations
        else:
            self.connect_selected_info_areas()    # This calls item_operations

        # Call after connect/disconnect operations which are handled by item_operations.
        # These operations should ideally manage saving config and then the app can update UI state.
        if hasattr(self, 'update_hover_connected_checkbox_visibility'):
            self.update_hover_connected_checkbox_visibility()

    def connection_exists(self, id1, id2):
        for conn in self.config.get('connections', []):
            s = conn.get('source')
            d = conn.get('destination')
            if (s == id1 and d == id2) or (s == id2 and d == id1):
                return True
        return False

    def update_selected_line_thickness(self):
        if isinstance(self.selected_item, ConnectionLineItem):
            val = self.line_thickness_spin.value()
            self.selected_item.config_data.pop('line_style_ref', None)
            self.selected_item.set_thickness(val)
            self.save_config()

    def update_selected_line_z_index(self):
        if isinstance(self.selected_item, ConnectionLineItem):
            val = self.line_z_index_spin.value()
            self.selected_item.config_data.pop('line_style_ref', None)
            self.selected_item.set_z_index(val)
            self.save_config()

    def update_selected_line_opacity(self):
        if isinstance(self.selected_item, ConnectionLineItem):
            val = self.line_opacity_spin.value()
            self.selected_item.config_data.pop('line_style_ref', None)
            self.selected_item.set_opacity(val)
            self.save_config()

    def choose_line_color(self):
        if isinstance(self.selected_item, ConnectionLineItem):
            current = QColor(self.selected_item.config_data.get('line_color', '#00ffff'))
            color = QColorDialog.getColor(current, self, "Select Line Color")
            if color.isValid():
                self.selected_item.config_data.pop('line_style_ref', None)
                self.selected_item.set_line_color(color.name())
                self.save_config()

    def choose_info_area_color(self):
        if isinstance(self.selected_item, InfoAreaItem):
            current = QColor(self.selected_item.config_data.get('fill_color', '#007BFF'))
            color = QColorDialog.getColor(current, self, "Select Area Color")
            if color.isValid():
                self.selected_item.config_data['fill_color'] = color.name()
                contrasting = self.text_style_manager.get_contrasting_text_color(color.name())
                if hasattr(self, 'rect_area_color_button'):
                    self.rect_area_color_button.setStyleSheet(f"background-color: {color.name()}; color: {contrasting};")
                self.selected_item.update_appearance(self.selected_item.isSelected(), self.current_mode == "view")
                self.save_config()

    def update_selected_area_opacity(self):
        if isinstance(self.selected_item, InfoAreaItem):
            val = self.rect_area_opacity_spin.value()
            self.selected_item.config_data['fill_alpha'] = float(val)
            self.selected_item.update_appearance(self.selected_item.isSelected(), self.current_mode == "view")
            self.save_config()

    # --- Z-order manipulation ---
    def bring_to_front(self):
        self.input_handler.bring_to_front_selected()

    def send_to_back(self):
        self.input_handler.send_to_back_selected()

    def bring_forward(self):
        self.input_handler.bring_forward_selected()

    def send_backward(self):
        self.input_handler.send_backward_selected()

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


    def keyPressEvent(self, a0):
        if not self.input_handler.handle_key_press(a0):
            super().keyPressEvent(a0)

    def closeEvent(self, a0):
        super().closeEvent(a0)

    # Placeholder methods for alignment
    def align_selected_rects_horizontally(self):
        self.canvas_manager.align_selected_rects_horizontally()

    def align_selected_rects_vertically(self):
        self.canvas_manager.align_selected_rects_vertically()

    def apply_dark_palette(self):
        """Apply a dark theme to the application."""
        qapp = QApplication.instance()
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.white)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        qapp.setPalette(palette)

if __name__ == '__main__':
    app = QApplication.instance() or QApplication(sys.argv)
    
    main_window = InfoCanvasApp()
    if main_window.current_project_name:
        main_window.setGeometry(100, 100, 1200, 700)
        main_window.show()
        sys.exit(app.exec_())
    else:
        print("Application initialization failed: No project loaded or startup cancelled.")
        if not main_window.isVisible(): 
            sys.exit(0)
