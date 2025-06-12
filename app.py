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
# --- Main Application Window ---
class InteractiveToolApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1200, 700)
        utils.ensure_base_projects_directory_exists()
        self.current_project_name = None
        self.current_project_path = None
        self.config = {}
        self.clipboard_data = None 

        if not self._initial_project_setup():
            QTimer.singleShot(0, self.close)
            return

        self.current_mode = "edit"
        self.selected_item = None
        self.item_map = {}
        self.setup_ui()
        self._load_text_styles_into_dropdown() # Ensure dropdown is populated early
        self.populate_controls_from_config()
        self.render_canvas_from_config()
        self.update_mode_ui()

    def _get_project_config_path(self, project_name_or_path):
        if os.path.isabs(project_name_or_path) and os.path.isdir(project_name_or_path):
             path = project_name_or_path
        else:
             path = os.path.join(utils.PROJECTS_BASE_DIR, project_name_or_path)
        return os.path.join(path, utils.PROJECT_CONFIG_FILENAME)

    def _get_project_images_folder(self, project_name_or_path):
        if os.path.isabs(project_name_or_path) and os.path.isdir(project_name_or_path):
             path = project_name_or_path
        else:
             path = os.path.join(utils.PROJECTS_BASE_DIR, project_name_or_path)
        return os.path.join(path, utils.PROJECT_IMAGES_DIRNAME)

    def _get_next_z_index(self):
         if hasattr(self, 'scene') and self.scene and self.scene.items():
             return max(item.zValue() for item in self.scene.items()) + 1
         return 0

    def _ensure_project_structure_exists(self, project_path):
        if not project_path: return False
        try:
            os.makedirs(project_path, exist_ok=True)
            os.makedirs(self._get_project_images_folder(project_path), exist_ok=True)
            return True
        except OSError as e:
            QMessageBox.critical(self, "Directory Error", f"Could not create project directories for {os.path.basename(project_path)}: {e}")
            return False

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
        self.current_project_name = project_name
        self.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, self.current_project_name)
        if not self._ensure_project_structure_exists(self.current_project_path):
            self.current_project_name = None
            self.current_project_path = None
            return False
        if is_new_project:
            self.config = utils.get_default_config()
            self.config["project_name"] = self.current_project_name
            if not self.save_config():
                 QMessageBox.warning(self, "Save Error", f"Could not save initial configuration for new project '{project_name}'.")
                 return False # Indicate failure if initial save fails
        else:
            loaded_config = self._load_config_for_current_project()
            if loaded_config is None: # Indicates an error during load
                # QMessageBox.warning(self, "Load Error", f"Could not load configuration for '{project_name}'. Using default.")
                # self.config = get_default_config() # Already handled in _load_config
                # self.config["project_name"] = self.current_project_name
                # Forcing a default config might hide underlying issues. Better to signal failure.
                self.config = None # Explicitly set config to None
                return False # Indicate failure if config load fails
            self.config = loaded_config
        
        self._update_window_title()
        if hasattr(self, 'edit_mode_controls_widget'): # Ensure controls are enabled after successful switch
            self.edit_mode_controls_widget.setEnabled(True)

        self._load_text_styles_into_dropdown() # Load styles after config is ready
        return True

    def _load_config_for_current_project(self):
        if not self.current_project_path:
            QMessageBox.critical(self, "Load Error", "No project path set. Cannot load configuration.")
            return None # Indicate error
        config_file_path = self._get_project_config_path(self.current_project_path)
        if not os.path.exists(config_file_path):
            print(f"Config file not found at {config_file_path}. Cannot load.")
            QMessageBox.warning(self, "Load Error", f"Config file for '{self.current_project_name}' not found.")
            return None # Indicate error
        try:
            with open(config_file_path, 'r') as f:
                print(f"Loading config from {config_file_path}.")
                loaded_data = json.load(f)
                if not loaded_data:
                    print("Config file is empty. Cannot load.")
                    QMessageBox.warning(self, "Load Error", "Config file is empty.")
                    return None # Indicate error
                return loaded_data
        except (IOError, json.JSONDecodeError) as e:
            QMessageBox.warning(self, "Load Error", f"Error loading config file {config_file_path}: {e}.")
            return None # Indicate error

    def save_config(self, config_data_to_save=None):
        if not self.current_project_path:
            # Allow saving default config if creating a new project even if path isn't fully set by user yet
            # This is handled by _switch_to_project which calls save_config for new projects
            if config_data_to_save and "project_name" in config_data_to_save: # Likely a new project default config
                temp_project_path = os.path.join(utils.PROJECTS_BASE_DIR, config_data_to_save["project_name"])
                if not self._ensure_project_structure_exists(temp_project_path): return False
                config_file_path = self._get_project_config_path(temp_project_path)
            else:
                QMessageBox.critical(self, "Save Error", "No project selected. Cannot save configuration.")
                return False
        else: # Existing project
            if not self._ensure_project_structure_exists(self.current_project_path):
                return False
            config_file_path = self._get_project_config_path(self.current_project_path)

        config_to_save = config_data_to_save if config_data_to_save is not None else self.config
        
        if not config_to_save: # Should not happen if logic is correct
            print("Warning: Attempted to save empty or uninitialized configuration. Aborting save.")
            return False

        config_to_save["last_modified"] = datetime.datetime.utcnow().isoformat() + "Z"
        if "project_name" not in config_to_save and self.current_project_name:
            config_to_save["project_name"] = self.current_project_name
        
        current_project_images_folder = self._get_project_images_folder(self.current_project_path or config_to_save.get("project_name"))

        for img_conf in config_to_save.get("images", []):
            if not img_conf.get('original_width') or not img_conf.get('original_height'):
                item = self.item_map.get(img_conf.get('id'))
                if item and isinstance(item, DraggableImageItem) and not item.pixmap().isNull():
                    img_conf['original_width'] = item.pixmap().width()
                    img_conf['original_height'] = item.pixmap().height()
                elif 'path' in img_conf and current_project_images_folder:
                    image_file_path = os.path.join(current_project_images_folder, img_conf['path'])
                    if os.path.exists(image_file_path):
                        reader = QImageReader(image_file_path)
                        if reader.canRead():
                            size = reader.size()
                            img_conf['original_width'] = size.width()
                            img_conf['original_height'] = size.height()
        try:
            with open(config_file_path, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            if hasattr(self, 'statusBar') and self.statusBar() is not None:
                status_project_name = self.current_project_name or config_to_save.get("project_name", "Unknown Project")
                self.statusBar().showMessage(f"Configuration for '{status_project_name}' saved.", 2000)
            else:
                print(f"Configuration for '{status_project_name}' saved (statusBar not available).")
            return True
        except IOError as e:
            QMessageBox.critical(self, "Save Error", f"Error saving config file {config_file_path}: {e}.")
            return False
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"An unexpected error occurred while saving: {e}.")
            return False

    def setup_ui(self):
        if not self.current_project_name or not self.config:
             QMessageBox.critical(self, "UI Setup Error", "Cannot setup UI without a loaded project and configuration.")
             return
        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QBrush(QColor(self.config['background']['color'])))
        self.scene.setSceneRect(0, 0, self.config['background']['width'], self.config['background']['height'])
        self.scene.selectionChanged.connect(self.on_scene_selection_changed)
        self.scene.parent_window = self
        self.view = QGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.SmoothPixmapTransform)
        self.setCentralWidget(self.view)
        
        self.controls_dock = QDockWidget("Controls", self)
        self.controls_dock.setFixedWidth(350) 
        # Remove close and float buttons, keep it movable
        self.controls_dock.setFeatures(QDockWidget.DockWidgetMovable) 
        
        self.controls_widget = QWidget()
        self.controls_layout = QVBoxLayout(self.controls_widget)
        self.controls_dock.setWidget(self.controls_widget)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.controls_dock)
        
        mode_group = QWidget()
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("Mode:"))
        self.mode_switcher = QComboBox()
        self.mode_switcher.addItems(["Edit Mode", "View Mode"])
        self.mode_switcher.currentTextChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_switcher)
        self.controls_layout.addWidget(mode_group)
        
        self.edit_mode_controls_widget = QWidget()
        edit_mode_layout = QVBoxLayout(self.edit_mode_controls_widget)
        bg_group = QWidget()
        bg_layout = QVBoxLayout(bg_group)
        bg_layout.addWidget(QLabel("<b>Background:</b>"))
        self.bg_color_button = QPushButton("Choose Color")
        self.bg_color_button.clicked.connect(self.choose_bg_color)
        bg_layout.addWidget(self.bg_color_button)
        bg_width_layout = QHBoxLayout()
        bg_width_layout.addWidget(QLabel("Width (px):"))
        self.bg_width_input = QSpinBox()
        self.bg_width_input.setRange(100, 10000)
        self.bg_width_input.valueChanged.connect(self.update_bg_dimensions)
        bg_width_layout.addWidget(self.bg_width_input)
        bg_layout.addLayout(bg_width_layout)
        bg_height_layout = QHBoxLayout()
        bg_height_layout.addWidget(QLabel("Height (px):"))
        self.bg_height_input = QSpinBox()
        self.bg_height_input.setRange(100, 10000)
        self.bg_height_input.valueChanged.connect(self.update_bg_dimensions)
        bg_height_layout.addWidget(self.bg_height_input)
        bg_layout.addLayout(bg_height_layout)
        edit_mode_layout.addWidget(bg_group)
        img_group = QWidget()
        img_layout = QVBoxLayout(img_group)
        img_layout.addWidget(QLabel("<b>Images:</b>"))
        self.upload_image_button = QPushButton("Upload Image")
        self.upload_image_button.clicked.connect(self.upload_image)
        img_layout.addWidget(self.upload_image_button)
        self.image_properties_widget = QWidget()
        img_props_layout = QVBoxLayout(self.image_properties_widget)
        img_props_layout.addWidget(QLabel("<u>Selected Image Properties:</u>"))
        img_scale_layout = QHBoxLayout()
        img_scale_layout.addWidget(QLabel("Scale:"))
        self.img_scale_input = QDoubleSpinBox()
        self.img_scale_input.setRange(0.01, 20.0)
        self.img_scale_input.setSingleStep(0.05)
        self.img_scale_input.setDecimals(2)
        self.img_scale_input.valueChanged.connect(self.update_selected_image_scale)
        img_scale_layout.addWidget(self.img_scale_input)
        img_props_layout.addLayout(img_scale_layout)
        self.delete_image_button = QPushButton("Delete Selected Image")
        self.delete_image_button.setStyleSheet("background-color: #dc3545; color: white;")
        self.delete_image_button.clicked.connect(self.delete_selected_image)
        img_props_layout.addWidget(self.delete_image_button)

        img_layer_layout_line1 = QHBoxLayout()
        self.img_to_front = QPushButton("Bring to Front")
        self.img_to_front.clicked.connect(self.bring_to_front)
        img_layer_layout_line1.addWidget(self.img_to_front)

        self.img_forward = QPushButton("Bring Forward")
        self.img_forward.clicked.connect(self.bring_forward)
        img_layer_layout_line1.addWidget(self.img_forward)

        img_layer_layout_line2 = QHBoxLayout()
        self.img_backward = QPushButton("Send Backward")
        self.img_backward.clicked.connect(self.send_backward)
        img_layer_layout_line2.addWidget(self.img_backward)

        self.img_to_back = QPushButton("Send to Back")
        self.img_to_back.clicked.connect(self.send_to_back)
        img_layer_layout_line2.addWidget(self.img_to_back)

        img_layer_layout_vertical = QVBoxLayout()
        img_layer_layout_vertical.addLayout(img_layer_layout_line1)
        img_layer_layout_vertical.addLayout(img_layer_layout_line2)
        img_props_layout.addLayout(img_layer_layout_vertical)
        self.image_properties_widget.setVisible(False)
        img_layout.addWidget(self.image_properties_widget)
        edit_mode_layout.addWidget(img_group)
        rect_group = QWidget()
        rect_layout = QVBoxLayout(rect_group)
        rect_layout.addWidget(QLabel("<b>Info Rectangles:</b>"))
        self.add_info_rect_button = QPushButton("Add Info Rectangle")
        self.add_info_rect_button.clicked.connect(self.add_info_rectangle)
        rect_layout.addWidget(self.add_info_rect_button)
        self.info_rect_properties_widget = QWidget()
        rect_props_layout = QVBoxLayout(self.info_rect_properties_widget)
        
        self.info_rect_text_input = QTextEdit()
        self.info_rect_text_input.setPlaceholderText("Enter information here...")
        self.info_rect_text_input.setFixedHeight(80)
        self.info_rect_text_input.textChanged.connect(self.update_selected_rect_text)
        rect_props_layout.addWidget(self.info_rect_text_input)

        # --- New Text Formatting Controls ---
        text_format_group = QWidget()
        text_format_layout = QVBoxLayout(text_format_group)
        text_format_layout.addWidget(QLabel("<u>Text Formatting:</u>"))

        # Horizontal Alignment
        h_align_layout = QHBoxLayout()
        h_align_layout.addWidget(QLabel("Horizontal Align:"))
        self.rect_h_align_combo = QComboBox()
        self.rect_h_align_combo.addItems(["Left", "Center", "Right"])
        self.rect_h_align_combo.activated[str].connect(self._on_rect_format_changed)
        h_align_layout.addWidget(self.rect_h_align_combo)
        text_format_layout.addLayout(h_align_layout)

        # Vertical Alignment
        v_align_layout = QHBoxLayout()
        v_align_layout.addWidget(QLabel("Vertical Align:"))
        self.rect_v_align_combo = QComboBox()
        self.rect_v_align_combo.addItems(["Top", "Center", "Bottom"])
        self.rect_v_align_combo.activated[str].connect(self._on_rect_format_changed)
        v_align_layout.addWidget(self.rect_v_align_combo)
        text_format_layout.addLayout(v_align_layout)

        # Font Size
        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font Size:"))
        self.rect_font_size_combo = QComboBox()
        common_font_sizes = ["8", "9", "10", "11", "12", "14", "16", "18", "20", "24", "28", "32", "36", "48", "72"]
        self.rect_font_size_combo.addItems(common_font_sizes)
        self.rect_font_size_combo.setEditable(True)
        self.rect_font_size_combo.lineEdit().setPlaceholderText("px")
        self.rect_font_size_combo.activated[str].connect(self._on_rect_format_changed) # Connect to existing if using index, or custom for text
        font_size_layout.addWidget(self.rect_font_size_combo)
        text_format_layout.addLayout(font_size_layout)

        # Font Style (Bold/Italic)
        font_style_layout = QHBoxLayout()
        self.rect_font_bold_button = QPushButton("Bold")
        self.rect_font_bold_button.setCheckable(True)
        self.rect_font_bold_button.toggled.connect(self._on_rect_font_style_changed)
        font_style_layout.addWidget(self.rect_font_bold_button)

        self.rect_font_italic_button = QPushButton("Italic")
        self.rect_font_italic_button.setCheckable(True)
        self.rect_font_italic_button.toggled.connect(self._on_rect_font_style_changed)
        font_style_layout.addWidget(self.rect_font_italic_button)
        text_format_layout.addLayout(font_style_layout)

        # Font Color Button
        font_color_layout = QHBoxLayout()
        font_color_layout.addWidget(QLabel("Font Color:"))
        self.rect_font_color_button = QPushButton("Select Color")
        self.rect_font_color_button.setToolTip("Click to select text color")
        # Initial color preview (will be updated later)
        self.rect_font_color_button.setStyleSheet("background-color: #000000; color: white;")
        self.rect_font_color_button.clicked.connect(self._on_rect_font_color_button_clicked)
        font_color_layout.addWidget(self.rect_font_color_button)
        text_format_layout.addLayout(font_color_layout)

        # Text Styles Dropdown
        style_selection_layout = QHBoxLayout()
        style_selection_layout.addWidget(QLabel("Text Style:"))
        self.rect_style_combo = QComboBox()
        # self.rect_style_combo.addItem("Default") # Will be populated by _load_text_styles_into_dropdown
        self.rect_style_combo.activated[str].connect(self._on_rect_style_selected) # Connect signal
        style_selection_layout.addWidget(self.rect_style_combo)
        text_format_layout.addLayout(style_selection_layout)

        # Save Style Button
        self.rect_save_style_button = QPushButton("Save Current as Style")
        self.rect_save_style_button.clicked.connect(self._save_current_text_style) # Connect signal
        text_format_layout.addWidget(self.rect_save_style_button)

        rect_props_layout.addWidget(text_format_group)
        # --- End of New Text Formatting Controls ---

        rect_width_layout = QHBoxLayout()
        rect_width_layout.addWidget(QLabel("Width (px):"))
        self.info_rect_width_input = QSpinBox()
        self.info_rect_width_input.setRange(InfoRectangleItem.MIN_WIDTH, 2000) # Use MIN_WIDTH from item
        self.info_rect_width_input.valueChanged.connect(self.update_selected_rect_dimensions)
        rect_width_layout.addWidget(self.info_rect_width_input)
        rect_props_layout.addLayout(rect_width_layout)
        rect_height_layout = QHBoxLayout()
        rect_height_layout.addWidget(QLabel("Height (px):"))
        self.info_rect_height_input = QSpinBox()
        self.info_rect_height_input.setRange(InfoRectangleItem.MIN_HEIGHT, 2000) # Use MIN_HEIGHT from item
        self.info_rect_height_input.valueChanged.connect(self.update_selected_rect_dimensions)
        rect_height_layout.addWidget(self.info_rect_height_input)
        rect_props_layout.addLayout(rect_height_layout)
        self.delete_info_rect_button = QPushButton("Delete Selected Info Rect")
        self.delete_info_rect_button.setStyleSheet("background-color: #dc3545; color: white;")
        self.delete_info_rect_button.clicked.connect(self.delete_selected_info_rect)
        rect_props_layout.addWidget(self.delete_info_rect_button)

        rect_layer_layout_line1 = QHBoxLayout()
        self.rect_to_front = QPushButton("Bring to Front")
        self.rect_to_front.clicked.connect(self.bring_to_front)
        rect_layer_layout_line1.addWidget(self.rect_to_front)

        self.rect_forward = QPushButton("Bring Forward")
        self.rect_forward.clicked.connect(self.bring_forward)
        rect_layer_layout_line1.addWidget(self.rect_forward)

        rect_layer_layout_line2 = QHBoxLayout()
        self.rect_backward = QPushButton("Send Backward")
        self.rect_backward.clicked.connect(self.send_backward)
        rect_layer_layout_line2.addWidget(self.rect_backward)

        self.rect_to_back = QPushButton("Send to Back")
        self.rect_to_back.clicked.connect(self.send_to_back)
        rect_layer_layout_line2.addWidget(self.rect_to_back)

        rect_layer_layout_vertical = QVBoxLayout()
        rect_layer_layout_vertical.addLayout(rect_layer_layout_line1)
        rect_layer_layout_vertical.addLayout(rect_layer_layout_line2)
        rect_props_layout.addLayout(rect_layer_layout_vertical)
        self.info_rect_properties_widget.setVisible(False)
        rect_layout.addWidget(self.info_rect_properties_widget)
        edit_mode_layout.addWidget(rect_group)
        self.controls_layout.addWidget(self.edit_mode_controls_widget)
        self.view_mode_message_label = QLabel("<i>Hover over areas on the image to see information.</i>")
        self.view_mode_message_label.setWordWrap(True)
        self.controls_layout.addWidget(self.view_mode_message_label)
        self.export_html_button = QPushButton("Export to HTML")
        self.export_html_button.clicked.connect(lambda checked=False: self.export_to_html())
        self.controls_layout.addWidget(self.export_html_button)
        self.controls_layout.addStretch()
        menubar = self.menuBar()
        file_menu = menubar.addMenu('&File')
        project_action = QAction('&Manage Projects...', self)
        project_action.triggered.connect(self._show_project_manager_dialog)
        file_menu.addAction(project_action)
        file_menu.addSeparator()
        save_action = QAction('&Save Configuration', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(lambda: self.save_config())
        file_menu.addAction(save_action)
        export_action = QAction('&Export to HTML', self)
        export_action.triggered.connect(lambda checked=False: self.export_to_html())
        file_menu.addAction(export_action)
        exit_action = QAction('&Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        self.statusBar().showMessage(f"Project '{self.current_project_name}' loaded. Ready.")

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
        if not hasattr(self, 'scene') or not self.scene: return
        selected_items = self.scene.selectedItems()
        newly_selected_item = selected_items[0] if selected_items else None
        if self.selected_item is not newly_selected_item:
            if self.selected_item and isinstance(self.selected_item, InfoRectangleItem):
                self.selected_item.update_appearance(False, self.current_mode == "view")
            self.selected_item = newly_selected_item
            if self.selected_item and isinstance(self.selected_item, InfoRectangleItem):
                self.selected_item.update_appearance(True, self.current_mode == "view")
        self.update_properties_panel()

    def on_graphics_item_selected(self, graphics_item):
        if self.current_mode == "view":
            if hasattr(self, 'scene') and self.scene: self.scene.clearSelection()
            self.selected_item = None
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
            if current_style_ref:
                style_idx = self.rect_style_combo.findText(current_style_ref)
                if style_idx != -1:
                    self.rect_style_combo.setCurrentIndex(style_idx)
                else: # Style ref exists but not found (e.g. style was deleted)
                    rect_conf.pop('text_style_ref', None) # Clear invalid ref
                    # Now check if current config matches default or other saved style
                    if self._does_current_rect_match_default_style(rect_conf):
                        self.rect_style_combo.setCurrentText("Default")
                    else:
                        matched_style_name = self._find_matching_style_name(rect_conf)
                        if matched_style_name:
                            self.rect_style_combo.setCurrentText(matched_style_name)
                            rect_conf['text_style_ref'] = matched_style_name # Re-assign if it matches another
                        else:
                            self.rect_style_combo.setCurrentText("Custom")
            elif self._does_current_rect_match_default_style(rect_conf):
                 self.rect_style_combo.setCurrentText("Default")
            else:
                matched_style_name = self._find_matching_style_name(rect_conf)
                if matched_style_name:
                    self.rect_style_combo.setCurrentText(matched_style_name)
                    # Optionally set text_style_ref here if we want to "re-link" it implicitly
                    # rect_conf['text_style_ref'] = matched_style_name
                else:
                    self.rect_style_combo.setCurrentText("Custom")

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
            contrasting_color = self._get_contrasting_text_color(current_font_color)
            self.rect_font_color_button.setStyleSheet(
                f"background-color: {current_font_color}; color: {contrasting_color};"
            )


            self.info_rect_text_input.blockSignals(False)
            self.info_rect_width_input.blockSignals(False)
            self.info_rect_height_input.blockSignals(False)
            self.info_rect_properties_widget.setVisible(True)
        else: # Not an InfoRectangleItem or no selection
             # Ensure formatting controls are hidden if no relevant item is selected
            if hasattr(self, 'rect_h_align_combo'): # Check if one of the new controls exists
                # Find the parent QWidget for the text_format_group to hide it
                # Assuming rect_props_layout.itemAt(1) is text_format_group (index might change based on final layout)
                # A safer way would be to keep a reference to text_format_group if it's complex
                # For now, let's assume it's the second direct widget in rect_props_layout (after text input)
                # Or, more simply, hide specific controls or the entire info_rect_properties_widget if no item is selected
                # The existing logic already hides info_rect_properties_widget if no item is selected or item is not InfoRect.
                # So, specific hiding of text_format_group might not be needed if it's part of info_rect_properties_widget.
                pass


    # --- Handler for new formatting controls ---
    def _on_rect_format_changed(self, value=None): # value can be text from ComboBox or not used if called by buttons
        if isinstance(self.selected_item, InfoRectangleItem):
            config = self.selected_item.config_data

            # Horizontal Alignment
            config['horizontal_alignment'] = self.rect_h_align_combo.currentText().lower()

            # Vertical Alignment
            config['vertical_alignment'] = self.rect_v_align_combo.currentText().lower()

            # Font Size
            font_size_text = self.rect_font_size_combo.currentText()
            if font_size_text.isdigit():
                config['font_size'] = f"{font_size_text}px"
            else: # Reset to default or handle error if input is invalid
                default_font_size = utils.get_default_config()["defaults"]["info_rectangle_text_display"]["font_size"]
                config['font_size'] = default_font_size
                self.rect_font_size_combo.blockSignals(True)
                self.rect_font_size_combo.setCurrentText(default_font_size.replace("px",""))
                self.rect_font_size_combo.blockSignals(False)

            config.pop('text_style_ref', None) # Manual change, so remove style reference
            self.selected_item.apply_style(config)

            # Update style combo to "Custom" or matching style after manual change
            self.rect_style_combo.blockSignals(True)
            if self._does_current_rect_match_default_style(config):
                self.rect_style_combo.setCurrentText("Default")
            else:
                matched_style_name = self._find_matching_style_name(config)
                if matched_style_name:
                    self.rect_style_combo.setCurrentText(matched_style_name)
                else:
                    self.rect_style_combo.setCurrentText("Custom")
            self.rect_style_combo.blockSignals(False)
            # self.save_config() is called by apply_style's emission

    def _on_rect_font_style_changed(self, checked=None):
        if isinstance(self.selected_item, InfoRectangleItem):
            config = self.selected_item.config_data
            is_bold = self.rect_font_bold_button.isChecked()
            is_italic = self.rect_font_italic_button.isChecked()

            if is_bold:
                config['font_style'] = "bold"
            elif is_italic:
                config['font_style'] = "italic"
            else:
                config['font_style'] = "normal"

            # If bold is checked, and italic is then checked, italic should take precedence or they should combine.
            # Current InfoRectangleItem logic treats them exclusively (bold OR italic OR normal).
            # For this iteration, if bold is checked, then italic is checked, italic wins.
            # If italic is checked, then bold is checked, bold wins.
            # If one is unchecked, it might become normal or the other style.
            # This logic ensures only one state or normal is passed.
            if is_bold and self.sender() == self.rect_font_bold_button:
                self.rect_font_italic_button.blockSignals(True)
                self.rect_font_italic_button.setChecked(False)
                self.rect_font_italic_button.blockSignals(False)
                config['font_style'] = "bold"
            elif is_italic and self.sender() == self.rect_font_italic_button:
                self.rect_font_bold_button.blockSignals(True)
                self.rect_font_bold_button.setChecked(False)
                self.rect_font_bold_button.blockSignals(False)
                config['font_style'] = "italic"
            elif not is_bold and not is_italic:
                 config['font_style'] = "normal"
            # If sender was unchecked, and the other button is still checked, that style should prevail.
            elif not is_bold and is_italic: # Bold was unchecked
                config['font_style'] = "italic"
            elif not is_italic and is_bold: # Italic was unchecked or bold was re-checked
                config['font_style'] = "bold"
            else: # Should be normal if both somehow got unchecked not via sender or if logic is complex
                config['font_style'] = "normal"


            config.pop('text_style_ref', None) # Manual change, remove style reference
            self.selected_item.apply_style(config)

            # Update style combo to "Custom" or matching style after manual change
            self.rect_style_combo.blockSignals(True)
            if self._does_current_rect_match_default_style(config):
                self.rect_style_combo.setCurrentText("Default")
            else:
                matched_style_name = self._find_matching_style_name(config)
                if matched_style_name:
                    self.rect_style_combo.setCurrentText(matched_style_name)
                else:
                    self.rect_style_combo.setCurrentText("Custom")
            self.rect_style_combo.blockSignals(False)
            # self.save_config() is called by apply_style's emission

    def _on_rect_font_color_button_clicked(self):
        # Placeholder: QColorDialog logic will be implemented in the next step
        print("Font color button clicked - QColorDialog to be implemented here")
        # For now, let's simulate a color change to see button update
        # if self.selected_item and isinstance(self.selected_item, InfoRectangleItem):
        #     self.selected_item.config_data['font_color'] = "#FF0000" # Simulate red
        #     self.update_properties_panel() # To update the button color based on new config

    def _get_contrasting_text_color(self, hex_color):
        """Determines if black or white text is more readable against a given hex background color."""
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            # Calculate luminance (standard formula)
            luminance = (0.299 * r + 0.587 * g + 0.114 * b)
            return "#FFFFFF" if luminance < 128 else "#000000"
        except Exception:
            return "#000000" # Default to black text on error

    def _on_rect_font_color_button_clicked(self):
        if not self.selected_item or not isinstance(self.selected_item, InfoRectangleItem):
            return

        item_config = self.selected_item.config_data
        default_color = utils.get_default_config()["defaults"]["info_rectangle_text_display"]['font_color']
        initial_color_str = item_config.get('font_color', default_color)

        try:
            q_initial_color = QColor(initial_color_str)
            if not q_initial_color.isValid(): # Fallback if hex is somehow invalid
                q_initial_color = QColor(default_color)
        except Exception: # Catch any error during QColor creation from potentially bad hex
            q_initial_color = QColor(default_color)

        color = QColorDialog.getColor(q_initial_color, self, "Select Text Color")

        if color.isValid():
            new_color_hex = color.name()
            item_config['font_color'] = new_color_hex
            item_config.pop('text_style_ref', None) # Mark as custom modification

            # Prepare a complete style dict to pass to apply_style
            # This ensures all current text formatting aspects are preserved/updated
            current_text_config = {
                key: item_config.get(key, utils.get_default_config()["defaults"]["info_rectangle_text_display"][key])
                for key in utils.get_default_config()["defaults"]["info_rectangle_text_display"].keys()
            }
            current_text_config['font_color'] = new_color_hex # Ensure the new color is in the dict for apply_style

            self.selected_item.apply_style(current_text_config)
            # apply_style calls properties_changed, which calls save_config and update_properties_panel.
            # update_properties_panel will update the button color via its logic.
            # Explicitly update button style here for immediate feedback if update_properties_panel is slow or deferred.
            contrasting_text_color = self._get_contrasting_text_color(new_color_hex)
            self.rect_font_color_button.setStyleSheet(
                f"background-color: {new_color_hex}; color: {contrasting_text_color};"
            )
            # self.update_properties_panel() # This will be called by properties_changed signal

    def _load_text_styles_into_dropdown(self):
        if not hasattr(self, 'rect_style_combo'): return
        self.rect_style_combo.blockSignals(True)
        self.rect_style_combo.clear()
        self.rect_style_combo.addItem("Default")
        self.rect_style_combo.addItem("Custom") # For when config doesn't match any style or default

        styles = self.config.get('text_styles', [])
        for style in styles:
            if isinstance(style, dict) and 'name' in style:
                 self.rect_style_combo.addItem(style['name'])
        self.rect_style_combo.blockSignals(False)

    def _save_current_text_style(self):
        if not isinstance(self.selected_item, InfoRectangleItem):
            QMessageBox.warning(self, "Save Style", "Please select an Info Rectangle to save its style.")
            return

        item_config = self.selected_item.config_data
        default_display_conf = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

        style_name, ok = QInputDialog.getText(self, "Save Text Style", "Enter style name:")
        if not ok or not style_name:
            if ok and not style_name: # Only show warning if OK was pressed with empty name
                QMessageBox.warning(self, "Save Style", "Style name cannot be empty.")
            return

        current_style_dict = {
            "name": style_name, # Ensure name is part of the dict to be saved/updated
            "font_color": item_config.get('font_color', default_display_conf['font_color']),
            "font_size": item_config.get('font_size', default_display_conf['font_size']),
            "font_style": item_config.get('font_style', default_display_conf['font_style']),
            "horizontal_alignment": item_config.get('horizontal_alignment', default_display_conf['horizontal_alignment']),
            "vertical_alignment": item_config.get('vertical_alignment', default_display_conf['vertical_alignment']),
            "padding": item_config.get('padding', default_display_conf['padding']),
        }

        existing_styles = self.config.setdefault('text_styles', [])
        style_object_updated = None # To hold the reference to the updated or new style object

        found_existing_style_for_update = False
        for s in existing_styles:
            if s['name'] == style_name:
                reply = QMessageBox.question(self, "Overwrite Style",
                                             f"Style '{style_name}' already exists. Overwrite it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return
                else: # Overwrite: UPDATE the existing dictionary in place
                    s.clear() # Remove all old keys
                    s.update(current_style_dict) # Add all new keys from current_style_dict
                    # s['name'] = style_name # Ensured by current_style_dict having 'name'
                    style_object_updated = s # Keep a reference to the updated style object
                    found_existing_style_for_update = True
                    break

        if not found_existing_style_for_update: # Style name not found, so append new
            existing_styles.append(current_style_dict)
            style_object_updated = current_style_dict # The newly added style object

        if style_object_updated is None: # Should not happen if logic is correct (e.g. user hit No and returned)
            return

        self.save_config() # Save changes to project config file
        self._load_text_styles_into_dropdown() # Refresh dropdown

        # Update all InfoRectangleItems that reference this style by name
        for item_in_map in self.item_map.values(): # Iterate directly over values
            if isinstance(item_in_map, InfoRectangleItem):
                if item_in_map.config_data.get('text_style_ref') == style_name:
                    # Force apply the canonical, possibly updated, style object
                    # This ensures the item uses the canonical style object and refreshes.
                    item_in_map.apply_style(style_object_updated)

        # Ensure the selected item (which was the source of the style)
        # is correctly referencing the potentially new style object and its UI is updated.
        # This also updates its internal text_style_ref name.
        # The loop above would have already handled self.selected_item if its text_style_ref matched.
        # However, explicitly calling apply_style on self.selected_item ensures it's updated,
        # particularly if its text_style_ref was just set or if it was a new style.
        # This also updates its internal text_style_ref name.
        self.selected_item.apply_style(style_object_updated)

        self.rect_style_combo.blockSignals(True)
        self.rect_style_combo.setCurrentText(style_name)
        self.rect_style_combo.blockSignals(False)

        self.statusBar().showMessage(f"Text style '{style_name}' saved and applied.", 2000)
        # update_properties_panel will be called because selected_item.apply_style emits properties_changed.


    def _on_rect_style_selected(self, style_name):
        if not isinstance(self.selected_item, InfoRectangleItem) or not style_name :
            return

        # Block signals on all formatting controls during update
        controls_to_block = [
            self.rect_style_combo, self.rect_h_align_combo, self.rect_v_align_combo,
            self.rect_font_size_combo, self.rect_font_bold_button, self.rect_font_italic_button
        ]
        for control in controls_to_block:
            control.blockSignals(True)

        item_config = self.selected_item.config_data
        style_applied_or_defaulted = False

        if style_name == "Default":
            default_settings = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
            style_to_apply = default_settings.copy()
            item_config.pop('text_style_ref', None)
            self.selected_item.apply_style(style_to_apply)
            style_applied_or_defaulted = True
        elif style_name == "Custom":
            # "Custom" selection means no change to item's actual style properties.
            # UI should already reflect item_config. If item had a style_ref, it might be cleared
            # if a manual edit happened. update_properties_panel handles setting to "Custom".
            pass # Essentially, do nothing to the item's properties.
        else: # A named style is selected
            found_style = None
            for s in self.config.get('text_styles', []):
                if isinstance(s, dict) and s.get('name') == style_name:
                    found_style = s
                    break
            if found_style:
                # Pass the direct reference to the style, not a copy.
                style_to_apply = found_style
                # item_config['text_style_ref'] = style_name # This is now handled by InfoRectangleItem.apply_style
                self.selected_item.apply_style(style_to_apply)
                style_applied_or_defaulted = True
            else: # Style not found (e.g. if list got corrupted, or "Custom" was somehow passed here)
                 pass # Do nothing if style isn't found

        # Unblock signals
        for control in controls_to_block:
            control.blockSignals(False)

        if style_applied_or_defaulted:
            # This will re-read item's config (now updated by apply_style)
            # and set all UI controls, including the style_combo itself.
            self.update_properties_panel()
        elif style_name == "Custom": # Ensure combo stays on custom if that was selected
             self.rect_style_combo.blockSignals(True)
             self.rect_style_combo.setCurrentText("Custom")
             self.rect_style_combo.blockSignals(False)


    def _does_current_rect_match_default_style(self, rect_config):
        # Use a clean copy of default settings for comparison
        defaults = utils.get_default_config()["defaults"]["info_rectangle_text_display"].copy()
        # Keys that define a text style
        style_keys = ["font_color", "font_size", "font_style",
                      "horizontal_alignment", "vertical_alignment", "padding"]
        for key in style_keys:
            # If a key is missing in rect_config, it's considered default for that key.
            # So, compare rect_config.get(key, defaults[key]) with defaults[key].
            if rect_config.get(key, defaults[key]) != defaults[key]:
                return False
        return True

    def _find_matching_style_name(self, rect_config):
        """Checks if the rect_config matches any saved style."""
        styles = self.config.get('text_styles', [])
        # Keys that define a text style
        style_keys_to_check = ["font_color", "font_size", "font_style",
                               "horizontal_alignment", "vertical_alignment", "padding"]
        for style_dict in styles:
            if not isinstance(style_dict, dict): continue # Skip if style is not a dict
            match = True
            for key in style_keys_to_check:
                # Use .get for rect_config as well, to handle cases where a key might be missing
                # and should implicitly use the default (which might match the style's value if it's also default)
                # However, styles should ideally be complete.
                # For a style to match, all its defined properties must match the item's properties.
                # If item is missing a property defined in style, it's not a match unless style's value is default for it.
                # This simple check assumes styles are fully defined for these keys.
                item_value = rect_config.get(key)
                style_value = style_dict.get(key)
                if item_value != style_value:
                    match = False
                    break
            if match:
                return style_dict.get('name')
        return None

    def upload_image(self):
        if not self.current_project_path:
            QMessageBox.critical(self, "Upload Error", "No project loaded. Cannot upload image.")
            return
        current_project_images_folder = self._get_project_images_folder(self.current_project_path)
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Upload Image", current_project_images_folder,
            f"Images ({' '.join(['*.' + ext for ext in utils.ALLOWED_EXTENSIONS])})"
        )
        if not filepath:
            return
        filename = os.path.basename(filepath)
        if not utils.allowed_file(filename):
            QMessageBox.warning(self, "Upload Error", "Selected file type is not allowed.")
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
            QMessageBox.critical(self, "Upload Error", f"Could not copy image to '{target_path}': {e}")
            return
        img_id = f"img_{datetime.datetime.now().timestamp()}"
        reader = QImageReader(target_path)
        original_size = reader.size()
        original_width = original_size.width()
        original_height = original_size.height()
        if original_width <= 0 or original_height <= 0:
            QMessageBox.warning(self, "Image Error", f"Could not read valid dimensions for image: {unique_filename}. Using fallback 100x100.")
            original_width, original_height = 100, 100
        new_image_config = {
            "id": img_id,
            "path": unique_filename,
            "center_x": self.scene.width() / 2,
            "center_y": self.scene.height() / 2,
            "scale": 1.0,
            "original_width": original_width,
            "original_height": original_height,
            "z_index": self._get_next_z_index(),
        }
        if 'images' not in self.config: self.config['images'] = []
        self.config['images'].append(new_image_config)
        pixmap = QPixmap(target_path)
        item = DraggableImageItem(pixmap, new_image_config) # Z-value set in item's __init__
        item.setTransform(QTransform().scale(new_image_config['scale'], new_image_config['scale']))
        item.setPos(
            new_image_config['center_x'] - (original_width * new_image_config['scale']) / 2,
            new_image_config['center_y'] - (original_height * new_image_config['scale']) / 2
        )
        item.item_selected.connect(self.on_graphics_item_selected)
        item.item_moved.connect(self.on_graphics_item_moved)
        self.scene.addItem(item)
        self.item_map[img_id] = item
        self.save_config()
        self.statusBar().showMessage(f"Image '{unique_filename}' uploaded to project '{self.current_project_name}'.", 3000)
        self.scene.clearSelection()
        item.setSelected(True)

    def update_selected_image_scale(self):
        if isinstance(self.selected_item, DraggableImageItem):
            new_scale = self.img_scale_input.value()
            img_conf = self.selected_item.config_data
            img_conf['scale'] = new_scale
            original_width = img_conf.get('original_width', self.selected_item.pixmap().width() / img_conf.get('scale', 1.0))
            original_height = img_conf.get('original_height', self.selected_item.pixmap().height() / img_conf.get('scale', 1.0))
            new_scaled_width = original_width * new_scale
            new_scaled_height = original_height * new_scale
            current_center_x = img_conf['center_x']
            current_center_y = img_conf['center_y']
            new_top_left_x = current_center_x - new_scaled_width / 2
            new_top_left_y = current_center_y - new_scaled_height / 2
            self.selected_item.setPos(new_top_left_x, new_top_left_y)
            transform = QTransform()
            transform.scale(new_scale, new_scale)
            self.selected_item.setTransform(transform)
            self.save_config()
            self.scene.update()

    def delete_selected_image(self):
        if not isinstance(self.selected_item, DraggableImageItem):
            QMessageBox.information(self, "Delete Image", "No image selected to delete.")
            return
        img_conf = self.selected_item.config_data
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to permanently delete the image '{img_conf['path']}' from project '{self.current_project_name}'?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            current_project_images_folder = self._get_project_images_folder(self.current_project_path)
            image_file_path = os.path.join(current_project_images_folder, img_conf['path'])
            try:
                if os.path.exists(image_file_path):
                    os.remove(image_file_path)
            except OSError as e:
                QMessageBox.warning(self, "Delete Error", f"Could not delete image file '{img_conf['path']}': {e}. It will still be removed from the configuration.")
            if img_conf in self.config.get('images', []):
                self.config['images'].remove(img_conf)
            self.scene.removeItem(self.selected_item)
            if img_conf.get('id') in self.item_map: del self.item_map[img_conf['id']]
            self.selected_item = None
            self.save_config()
            self.update_properties_panel()
            self.statusBar().showMessage(f"Image '{img_conf['path']}' deleted.", 3000)

    def add_info_rectangle(self):
        rect_id = f"rect_{datetime.datetime.now().timestamp()}"
        default_display_conf = self.config.get("defaults", {}).get("info_rectangle_text_display", utils.get_default_config()["defaults"]["info_rectangle_text_display"])
        new_rect_config = {
            "id": rect_id,
            "center_x": self.scene.width() / 2, "center_y": self.scene.height() / 2,
            "width": default_display_conf.get("box_width", 150),
            "height": 50,
            "text": "New Information",
            "z_index": self._get_next_z_index(),
        }
        if 'info_rectangles' not in self.config: self.config['info_rectangles'] = []
        self.config['info_rectangles'].append(new_rect_config)
        item = InfoRectangleItem(new_rect_config) # Z-value set in item's __init__
        item.item_selected.connect(self.on_graphics_item_selected)
        item.item_moved.connect(self.on_graphics_item_moved)
        item.properties_changed.connect(self.on_graphics_item_properties_changed)
        self.scene.addItem(item)
        self.item_map[rect_id] = item
        self.save_config()
        self.statusBar().showMessage("Info rectangle added.", 2000)
        self.scene.clearSelection()
        item.setSelected(True)

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
        if not isinstance(self.selected_item, InfoRectangleItem):
            QMessageBox.information(self, "Delete Info Rectangle", "No info rectangle selected.")
            return
        rect_conf = self.selected_item.config_data
        reply = QMessageBox.question(self, "Confirm Delete",
                                     "Are you sure you want to delete this info rectangle?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.Yes:
            if rect_conf in self.config.get('info_rectangles', []):
                self.config['info_rectangles'].remove(rect_conf)
            self.scene.removeItem(self.selected_item)
            if rect_conf.get('id') in self.item_map: del self.item_map[rect_conf['id']]
            self.selected_item = None
            self.save_config()
            self.update_properties_panel()
            self.statusBar().showMessage("Info rectangle deleted.", 2000)

    def paste_info_rectangle(self):
        """Pastes an info rectangle from the internal clipboard."""
        if self.clipboard_data is None:
            self.statusBar().showMessage("Clipboard is empty.", 2000)
            return
        if not isinstance(self.clipboard_data, dict) or 'text' not in self.clipboard_data: 
            self.statusBar().showMessage("Clipboard data is not for an info rectangle.", 2000)
            return

        new_rect_config = copy.deepcopy(self.clipboard_data)
        new_rect_config['id'] = f"rect_{datetime.datetime.now().timestamp()}"
        new_rect_config['center_x'] = new_rect_config.get('center_x', self.scene.width() / 2) + 20
        new_rect_config['center_y'] = new_rect_config.get('center_y', self.scene.height() / 2) + 20
        new_rect_config['z_index'] = self._get_next_z_index()

        if 'info_rectangles' not in self.config:
            self.config['info_rectangles'] = []
        self.config['info_rectangles'].append(new_rect_config)

        item = InfoRectangleItem(new_rect_config) # Z-value set in item's __init__
        item.item_selected.connect(self.on_graphics_item_selected)
        item.item_moved.connect(self.on_graphics_item_moved)
        item.properties_changed.connect(self.on_graphics_item_properties_changed)
        
        self.scene.addItem(item)
        self.item_map[new_rect_config['id']] = item
        
        self.save_config()
        self.statusBar().showMessage("Info rectangle pasted.", 2000)
        
        self.scene.clearSelection()
        item.setSelected(True)

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
    def _generate_view_html(self):
        """Create an interactive HTML representation of the current view."""
        bg = self.config.get('background', {}) if self.config else {}
        lines = [
            "<!DOCTYPE html>",
            "<html>",
            "<head>",
            "<meta charset='utf-8'>",
            f"<title>{html.escape(self.current_project_name or 'Project')}</title>",
            "<style>#canvas{position:relative;}\n.hotspot{position:absolute;}\n.tooltip{position:absolute;border:1px solid #333;padding:2px;background:rgba(255,255,255,0.9);display:none;z-index:1000;}\n</style>",
            "</head>",
            "<body>",
            f"<div id='canvas' style='width:{bg.get('width',800)}px;height:{bg.get('height',600)}px;background-color:{bg.get('color','#FFFFFF')};'>",
        ]

        for img_conf in self.config.get('images', []):
            scale = img_conf.get('scale', 1.0)
            width = img_conf.get('original_width', 0) * scale
            height = img_conf.get('original_height', 0) * scale
            left = img_conf.get('center_x', 0) - width / 2
            top = img_conf.get('center_y', 0) - height / 2
            src = os.path.join('images', img_conf.get('path', ''))
            lines.append(
                f"<img src='{src}' style='position:absolute;left:{left}px;top:{top}px;width:{width}px;height:{height}px;'>"
            )

        for rect_conf in self.config.get('info_rectangles', []):
            rect_width = rect_conf.get('width', 0)
            rect_height = rect_conf.get('height', 0)
            left = rect_conf.get('center_x', 0) - rect_width / 2
            top = rect_conf.get('center_y', 0) - rect_height / 2

            default_text_config = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

            text_content = html.escape(rect_conf.get('text', '')).replace('\n', '<br>')
            font_color = rect_conf.get('font_color', default_text_config['font_color'])
            font_size_str = rect_conf.get('font_size', default_text_config['font_size'])
            # Ensure font_size has 'px'
            if isinstance(font_size_str, (int, float)) or font_size_str.isdigit():
                font_size = f"{font_size_str}px"
            else:
                font_size = font_size_str # Assume it already has units like 'px'

            text_bg_color = rect_conf.get('background_color', default_text_config['background_color']) # This is text area background
            padding_str = rect_conf.get('padding', default_text_config['padding'])
            if isinstance(padding_str, (int, float)) or padding_str.isdigit():
                padding = f"{padding_str}px"
            else:
                padding = padding_str


            h_align = rect_conf.get('horizontal_alignment', default_text_config['horizontal_alignment']) # left, center, right
            v_align = rect_conf.get('vertical_alignment', default_text_config['vertical_alignment']) # top, center, bottom
            font_style_prop = rect_conf.get('font_style', default_text_config['font_style']) # normal, bold, italic

            # Outer div styles (the rectangle itself)
            outer_style = f"position:absolute; left:{left}px; top:{top}px; width:{rect_width}px; height:{rect_height}px; display:flex;"

            if v_align == "top":
                outer_style += "align-items:flex-start;"
            elif v_align == "center" or v_align == "middle": # Handle "middle" as center
                outer_style += "align-items:center;"
            elif v_align == "bottom":
                outer_style += "align-items:flex-end;"

            # Inner div styles (text container)
            inner_style = f"width:100%; box-sizing:border-box; overflow-wrap:break-word; word-wrap:break-word;" # Ensure text wraps and padding is contained
            inner_style += f"color:{font_color};"
            inner_style += f"font-size:{font_size};"
            inner_style += "background-color:transparent;" # Unconditionally set to transparent
            inner_style += f"padding:{padding};"
            inner_style += f"text-align:{h_align};"

            if font_style_prop == "bold":
                inner_style += "font-weight:bold;"
            elif font_style_prop == "italic":
                inner_style += "font-style:italic;"
            # Note: "bold italic" would require both if InfoRectangleItem supports it. Assuming it's one or the other or normal.

            # The 'hotspot' class is used by the JS for hover interactions.
            # Ensure 'info-rectangle-export' class is also present.
            # The data-text attribute is no longer needed as text is in an inner div.
            inner_style += " display: none;" # Hide text content by default

            lines.append(
                f"<div class='hotspot info-rectangle-export' style='{outer_style}'>" # Ensure both classes
                f"<div class='text-content' style='{inner_style}'>{text_content}</div>" # Added display:none here
                f"</div>"
            )

        lines.append("</div>")
        # Tooltip div is no longer needed for info rectangles with the new hover mechanism
        # lines.append("<div id='tooltip' class='tooltip'></div>") # Keep this line if other things use it, or remove if only for old info rects
        lines.append("<script>")
        lines.append("document.querySelectorAll('.hotspot.info-rectangle-export').forEach(function(h){")
        lines.append("  var textContentDiv = h.querySelector('.text-content');")
        lines.append("  if (!textContentDiv) return;") # Skip if no text content
        lines.append("  h.addEventListener('mouseenter', function(e){")
        lines.append("    textContentDiv.style.display = 'block';") # Or 'flex' if it was originally flex
        lines.append("  });")
        # mousemove listener removed as per requirements
        lines.append("  h.addEventListener('mouseleave', function(e){")
        lines.append("    textContentDiv.style.display = 'none';")
        lines.append("  });")
        lines.append("});")
        lines.append("</script>")
        lines.append("</body></html>")
        return "\n".join(lines)

    def export_to_html(self, filepath=None):
        """Export the current project view to an HTML file."""
        if isinstance(filepath, bool):
            filepath = None
        if not self.config:
            QMessageBox.warning(self, "Export Error", "No project loaded to export.")
            return
        if filepath is None:
            default_name = f"{self.current_project_name or 'project'}.html"
            filepath, _ = QFileDialog.getSaveFileName(
                self,
                "Export to HTML",
                default_name,
                "HTML Files (*.html)",
                options=QFileDialog.Options()
            )
            if not filepath or filepath is False:
                return
        html = self._generate_view_html()
        dest_dir = os.path.dirname(str(filepath))
        dest_images = os.path.join(dest_dir, 'images')
        src_images = self._get_project_images_folder(self.current_project_path)
        os.makedirs(dest_images, exist_ok=True)
        for img_conf in self.config.get('images', []):
            rel = img_conf.get('path', '')
            if not rel:
                continue
            src_file = os.path.join(src_images, rel)
            dest_file = os.path.join(dest_images, rel)
            os.makedirs(os.path.dirname(dest_file), exist_ok=True)
            if os.path.exists(src_file):
                shutil.copy2(src_file, dest_file)
        try:
            with open(str(filepath), 'w', encoding='utf-8') as f:
                f.write(html)
            QMessageBox.information(self, "Export Complete", f"Exported to {filepath}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to write HTML file: {e}")


    def keyPressEvent(self, event):
        focused_widget = QApplication.focusWidget()
        is_input_focused = isinstance(focused_widget, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox))

        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_C:
                if self.selected_item and isinstance(self.selected_item, InfoRectangleItem) and \
                   self.current_mode == "edit" and not is_input_focused:
                    self.clipboard_data = copy.deepcopy(self.selected_item.config_data)
                    self.statusBar().showMessage("Info rectangle copied to clipboard.", 2000)
                    event.accept()
                    return
            elif event.key() == Qt.Key_V:
                if self.current_mode == "edit" and not is_input_focused:
                    self.paste_info_rectangle()
                    event.accept()
                    return
        elif event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            if self.selected_item and self.current_mode == "edit" and not is_input_focused:
                if isinstance(self.selected_item, DraggableImageItem):
                    self.delete_selected_image()
                elif isinstance(self.selected_item, InfoRectangleItem):
                    self.delete_selected_info_rect()
                event.accept()
                return
        super().keyPressEvent(event)

    def closeEvent(self, event):
        super().closeEvent(event)


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
