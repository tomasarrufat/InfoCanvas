import sys
import os
import json
import datetime
import shutil # For copying files
import copy # For deep copying objects

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

# --- Project Structure Constants ---
BASE_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_ROOT_DIR_NAME = "static"  # Main directory for all projects
PROJECTS_BASE_DIR = os.path.join(BASE_SCRIPT_DIR, PROJECTS_ROOT_DIR_NAME)
PROJECT_CONFIG_FILENAME = "config.json"
PROJECT_IMAGES_DIRNAME = "images"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# --- Z-Values for Item Stacking ---
Z_VALUE_INFO_RECT = 0
Z_VALUE_IMAGE = 1


# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_base_projects_directory_exists():
    """Creates the base directory for all projects if it doesn't exist."""
    os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)

def get_default_config():
    """Returns the default configuration structure for a new project."""
    return {
        "last_modified": datetime.datetime.utcnow().isoformat() + "Z",
        "defaults": {
            "info_rectangle_text_display": {
                "font_color": "#000000",
                "font_size": "14px",
                "background_color": "#FFFFFF",
                "box_width": 200,
                "padding": "5px"
            }
        },
        "background": {
            "width": 800,
            "height": 600,
            "color": "#DDDDDD"
        },
        "images": [],
        "info_rectangles": []
    }

# --- Custom Graphics Items ---

class DraggableImageItem(QGraphicsObject):
    item_selected = pyqtSignal(QGraphicsItem)
    item_moved = pyqtSignal(QGraphicsItem)

    def __init__(self, pixmap, config_data, parent_item=None):
        super().__init__(parent_item)
        self._pixmap = pixmap
        self.config_data = config_data
        self.setFlags(QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemIsMovable |
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.initial_pos = self.pos()
        self.setZValue(Z_VALUE_IMAGE) # Ensure images are on top

    def pixmap(self):
        return self._pixmap

    def setPixmap(self, pixmap):
        self.prepareGeometryChange()
        self._pixmap = pixmap
        self.update()

    def boundingRect(self):
        if self._pixmap.isNull():
            return QRectF()
        return QRectF(0, 0, self._pixmap.width(), self._pixmap.height())

    def paint(self, painter, option, widget=None):
        if not self._pixmap.isNull():
            painter.drawPixmap(0, 0, self._pixmap)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged and self.scene():
            current_scale = self.config_data.get('scale', 1.0)
            original_width = self.config_data.get('original_width', self._pixmap.width())
            original_height = self.config_data.get('original_height', self._pixmap.height())
            scaled_width_at_current_scale = original_width * current_scale
            scaled_height_at_current_scale = original_height * current_scale
            new_center_x = value.x() + scaled_width_at_current_scale / 2
            new_center_y = value.y() + scaled_height_at_current_scale / 2
            self.config_data['center_x'] = new_center_x
            self.config_data['center_y'] = new_center_y
            self.item_moved.emit(self)
        return super().itemChange(change, value)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if event.button() == Qt.LeftButton:
            self.item_selected.emit(self)
            self.initial_pos = self.pos()

    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)

    def hoverEnterEvent(self, event):
        scene = self.scene()
        if scene and hasattr(scene, 'parent_window') and scene.parent_window.current_mode == "edit":
            QApplication.setOverrideCursor(Qt.PointingHandCursor)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        QApplication.restoreOverrideCursor()
        super().hoverLeaveEvent(event)


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
        self._w = self.config_data.get('width', 100)
        self._h = self.config_data.get('height', 50)
        self._pen = QPen(Qt.NoPen)
        self._brush = QBrush(Qt.NoBrush)

        self.setFlags(QGraphicsItem.ItemIsSelectable |
                      QGraphicsItem.ItemIsMovable | 
                      QGraphicsItem.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)
        self.setZValue(Z_VALUE_INFO_RECT) # Ensure info rects are below images

        self.text_item = QGraphicsTextItem('', self)
        self.text_item.setDefaultTextColor(QColor("#000000"))

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

    def _center_text(self):
        if not self.text_item: return
        self.text_item.setPos(0,0)
        font_metrics = QFontMetrics(self.text_item.font())
        text_bounding_rect = font_metrics.boundingRect(QRect(0, 0, int(self._w), 10000),
                                                       Qt.TextWordWrap | Qt.AlignLeft,
                                                       self.text_item.toPlainText())
        text_height = text_bounding_rect.height()
        padding_str = self.config_data.get("defaults", {}).get("info_rectangle_text_display", {}).get("padding", "5px")
        try:
            padding_val = int(padding_str.lower().replace("px", "")) if "px" in padding_str.lower() else 5
        except ValueError:
            padding_val = 5
        text_y_offset = (self._h - text_height) / 2
        self.text_item.setY(max(padding_val, text_y_offset))

    def set_display_text(self, text):
        """Sets the display text and recenters, optimized for live editing from properties panel."""
        self.text_item.setPlainText(text)
        self._center_text()
        self.update() 

    def update_text_from_config(self): 
        """Updates the text content from config_data (e.g., on load) and adjusts text centering."""
        self.text_item.setPlainText(self.config_data.get('text', ''))
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
            self.item_moved.emit(self)
        return super().itemChange(change, value)


# --- Project Manager Dialog ---
class ProjectManagerDialog(QDialog):
    # Signal to indicate a project might need to be reloaded or UI reset in main window
    project_deleted_signal = pyqtSignal(str) 

    def __init__(self, parent=None, current_project_name=None):
        super().__init__(parent)
        self.parent_window = parent # To access main window methods if needed
        self.current_project_name_on_open = current_project_name
        self.setWindowTitle("Manage Projects")
        self.setMinimumWidth(400) # Slightly wider for new button
        self.selected_project_name = None # For loading/creating
        self.project_to_delete = None # For deletion confirmation

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Existing Projects:"))
        self.project_list_widget = QListWidget()
        self.project_list_widget.itemDoubleClicked.connect(self.load_selected_project)
        layout.addWidget(self.project_list_widget)

        self.populate_project_list()

        buttons_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Selected")
        self.load_button.clicked.connect(self.load_selected_project)
        buttons_layout.addWidget(self.load_button)

        self.new_button = QPushButton("Create New Project")
        self.new_button.clicked.connect(self.create_new_project)
        buttons_layout.addWidget(self.new_button)
        
        self.delete_button = QPushButton("Delete Selected Project")
        self.delete_button.setStyleSheet("background-color: #dc3545; color: white;")
        self.delete_button.clicked.connect(self.confirm_delete_project)
        buttons_layout.addWidget(self.delete_button)

        layout.addLayout(buttons_layout)
        
        self.cancel_button = QPushButton("Close Manager")
        self.cancel_button.clicked.connect(self.reject) 
        layout.addWidget(self.cancel_button, 0, Qt.AlignRight)


        self.setLayout(layout)

    def populate_project_list(self):
        self.project_list_widget.clear()
        if not os.path.exists(PROJECTS_BASE_DIR):
            return
        for item_name in os.listdir(PROJECTS_BASE_DIR):
            item_path = os.path.join(PROJECTS_BASE_DIR, item_name)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, PROJECT_CONFIG_FILENAME)): # Check if it's a valid project dir
                self.project_list_widget.addItem(QListWidgetItem(item_name))

    def load_selected_project(self):
        current_item = self.project_list_widget.currentItem()
        if current_item:
            self.selected_project_name = current_item.text()
            self.accept() 
        else:
            QMessageBox.warning(self, "No Project Selected", "Please select a project from the list to load.")

    def create_new_project(self):
        project_name, ok = QInputDialog.getText(self, "New Project", "Enter project name:")
        if ok and project_name:
            project_name = project_name.strip()
            if not project_name:
                QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
                return
            
            # Basic validation for project name (avoid special chars that are bad for dir names)
            if not all(c.isalnum() or c in (' ', '_', '-') for c in project_name):
                QMessageBox.warning(self, "Invalid Name", "Project name can only contain letters, numbers, spaces, underscores, or hyphens.")
                return

            new_project_path = os.path.join(PROJECTS_BASE_DIR, project_name)
            if os.path.exists(new_project_path):
                QMessageBox.warning(self, "Project Exists", f"A project named '{project_name}' already exists.")
                return
            
            self.selected_project_name = project_name
            self.accept() 
        elif ok and not project_name:
             QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
    
    def confirm_delete_project(self):
        current_item = self.project_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Project Selected", "Please select a project from the list to delete.")
            return

        project_name_to_delete = current_item.text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to permanently delete the project '{project_name_to_delete}'?\nThis action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.delete_project(project_name_to_delete)

    def delete_project(self, project_name):
        project_path_to_delete = os.path.join(PROJECTS_BASE_DIR, project_name)
        try:
            shutil.rmtree(project_path_to_delete)
            QMessageBox.information(self, "Project Deleted", f"Project '{project_name}' has been deleted.")
            self.populate_project_list() # Refresh the list

            # Emit signal if the deleted project was the currently open one
            if project_name == self.current_project_name_on_open:
                self.project_deleted_signal.emit(project_name)
                # self.accept() # Close dialog after deleting current project to force main window reset
                # Or, keep dialog open if user might want to do more. 
                # For now, let main window handle reset via signal.

        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Error deleting project '{project_name}': {e}")


# --- Main Application Window ---
class InteractiveToolApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1200, 700)
        ensure_base_projects_directory_exists()
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
        self.populate_controls_from_config()
        self.render_canvas_from_config()
        self.update_mode_ui()

    def _get_project_config_path(self, project_name_or_path):
        if os.path.isabs(project_name_or_path) and os.path.isdir(project_name_or_path):
             path = project_name_or_path
        else:
             path = os.path.join(PROJECTS_BASE_DIR, project_name_or_path)
        return os.path.join(path, PROJECT_CONFIG_FILENAME)

    def _get_project_images_folder(self, project_name_or_path):
        if os.path.isabs(project_name_or_path) and os.path.isdir(project_name_or_path):
             path = project_name_or_path
        else:
             path = os.path.join(PROJECTS_BASE_DIR, project_name_or_path)
        return os.path.join(path, PROJECT_IMAGES_DIRNAME)

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
            project_path = os.path.join(PROJECTS_BASE_DIR, project_name)
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

            is_new = not os.path.exists(os.path.join(PROJECTS_BASE_DIR, project_name))
            
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
        self.current_project_path = os.path.join(PROJECTS_BASE_DIR, self.current_project_name)
        if not self._ensure_project_structure_exists(self.current_project_path):
            self.current_project_name = None
            self.current_project_path = None
            return False
        if is_new_project:
            self.config = get_default_config()
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
                return False # Indicate failure if config load fails
            self.config = loaded_config
        
        self._update_window_title()
        if hasattr(self, 'edit_mode_controls_widget'): # Ensure controls are enabled after successful switch
            self.edit_mode_controls_widget.setEnabled(True)
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
                temp_project_path = os.path.join(PROJECTS_BASE_DIR, config_data_to_save["project_name"])
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
        self.info_rect_properties_widget.setVisible(False)
        rect_layout.addWidget(self.info_rect_properties_widget)
        edit_mode_layout.addWidget(rect_group)
        self.controls_layout.addWidget(self.edit_mode_controls_widget)
        self.view_mode_message_label = QLabel("<i>Hover over areas on the image to see information.</i>")
        self.view_mode_message_label.setWordWrap(True)
        self.controls_layout.addWidget(self.view_mode_message_label)
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
        bg_conf = self.config.get('background', get_default_config()['background'])
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
            self.info_rect_text_input.blockSignals(False)
            self.info_rect_width_input.blockSignals(False)
            self.info_rect_height_input.blockSignals(False)
            self.info_rect_properties_widget.setVisible(True)

    def upload_image(self):
        if not self.current_project_path:
            QMessageBox.critical(self, "Upload Error", "No project loaded. Cannot upload image.")
            return
        current_project_images_folder = self._get_project_images_folder(self.current_project_path)
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Upload Image", current_project_images_folder,
            f"Images ({' '.join(['*.' + ext for ext in ALLOWED_EXTENSIONS])})"
        )
        if not filepath:
            return
        filename = os.path.basename(filepath)
        if not allowed_file(filename):
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
            "id": img_id, "path": unique_filename,
            "center_x": self.scene.width() / 2, "center_y": self.scene.height() / 2,
            "scale": 1.0, "original_width": original_width, "original_height": original_height
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
        default_display_conf = self.config.get("defaults", {}).get("info_rectangle_text_display", get_default_config()["defaults"]["info_rectangle_text_display"])
        new_rect_config = {
            "id": rect_id,
            "center_x": self.scene.width() / 2, "center_y": self.scene.height() / 2,
            "width": default_display_conf.get("box_width", 150), "height": 50,
            "text": "New Information"
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
    app = QApplication(sys.argv)
    if not QApplication.instance(): 
        app = QApplication(sys.argv) 
    
    main_window = InteractiveToolApp()
    if main_window.current_project_name: 
        main_window.show()
        sys.exit(app.exec_())
    else:
        print("Application initialization failed: No project loaded or startup cancelled.")
        if not main_window.isVisible(): 
            sys.exit(0) 
