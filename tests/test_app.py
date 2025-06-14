import sys
import os
import datetime # Ensure datetime is imported
from unittest.mock import mock_open, patch, MagicMock, ANY # Ensure ANY is imported
import pytest
from pytestqt.qt_compat import qt_api
from PyQt5.QtWidgets import QApplication, QDialog, QGraphicsScene, QGraphicsView, QMessageBox, QLineEdit, QWidget
from PyQt5.QtCore import QTimer, Qt, QRectF, QUrl
from PyQt5.QtGui import QColor, QKeyEvent # Added QKeyEvent

import shutil
import json
# PyQt5.QtCore.QTimer is already imported above
import os
import copy # Ensure copy is imported for clipboard data


# Add project root to sys.path to allow importing app and src
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app import InfoCanvasApp
from src import utils # For utils.PROJECTS_BASE_DIR etc.
from src.project_manager_dialog import ProjectManagerDialog # For mocking
from src.draggable_image_item import DraggableImageItem # Added
from src.info_rectangle_item import InfoRectangleItem # Added
from src.project_io import ProjectIO
from src.ui_builder import UIBuilder

# Mock global functions or classes that interact with filesystem or UI dialogs early
@pytest.fixture(autouse=True)
def mock_ensure_base_projects_directory(monkeypatch):
    # Mock to prevent actual directory creation during tests
    monkeypatch.setattr(utils, "ensure_base_projects_directory_exists", lambda: None)

# Define MockProjectManagerDialog at the module level
class MockProjectManagerDialog:
    def __init__(self, parent=None, current_project_name=None):
        self.parent = parent
        self.current_project_name = current_project_name
        self.selected_project_name = None
        # Mock QSignal: create a dummy class with a connect method
        class MockSignal:
            def connect(self, slot):
                pass
        self.project_deleted_signal = MockSignal()
        self._outcome = QDialog.Rejected # Default to rejected/cancelled

    def exec_(self):
        return self._outcome # Controlled by the test

    def set_outcome(self, outcome, project_name=None):
        self._outcome = outcome
        self.selected_project_name = project_name

@pytest.fixture
def mock_project_manager_dialog(monkeypatch):
    # This fixture now uses the module-level MockProjectManagerDialog
    monkeypatch.setattr('app.ProjectManagerDialog', MockProjectManagerDialog)
    # Also mock it for the app module if it's imported there directly
    if hasattr(sys.modules.get('app'), 'ProjectManagerDialog'): # Check if 'app' module is loaded
         monkeypatch.setattr(sys.modules['app'], 'ProjectManagerDialog', MockProjectManagerDialog)
    return MockProjectManagerDialog

@pytest.fixture
def base_app_fixture(qtbot, mock_project_manager_dialog, monkeypatch, tmp_path_factory):
    """
    Fixture to create a basic InfoCanvasApp instance for testing.
    It simulates a successful initial project setup by default.
    Tests that need different initial dialog outcomes should create their own app instance
    or use monkeypatch to alter the dialog's behavior before app creation.
    """

    # Use a temporary directory for PROJECTS_BASE_DIR
    temp_projects_base = tmp_path_factory.mktemp("projects_base")
    monkeypatch.setattr(utils, 'PROJECTS_BASE_DIR', str(temp_projects_base))

    # Mock _initial_project_setup to simulate a successful setup
    def mock_successful_initial_setup(self_app):
        self_app.current_project_name = "test_project"
        self_app.current_project_path = os.path.join(str(temp_projects_base), "test_project")

        monkeypatch.setattr(self_app, '_get_project_config_path', lambda name_or_path: os.path.join(self_app.current_project_path, utils.PROJECT_CONFIG_FILENAME))
        monkeypatch.setattr(self_app, '_get_project_images_folder', lambda name_or_path: os.path.join(self_app.current_project_path, utils.PROJECT_IMAGES_DIRNAME))
        monkeypatch.setattr(self_app, '_ensure_project_structure_exists', lambda path: True)

        dummy_config_path = self_app._get_project_config_path("test_project")
        dummy_project_dir = os.path.dirname(dummy_config_path)
        os.makedirs(dummy_project_dir, exist_ok=True)

        dummy_images_dir = self_app._get_project_images_folder("test_project")
        os.makedirs(dummy_images_dir, exist_ok=True)

        default_config = utils.get_default_config()
        default_config["project_name"] = "test_project"
        with open(dummy_config_path, 'w') as f:
            import json
            json.dump(default_config, f)

        self_app.config = default_config
        self_app.item_map = {}
        self_app.selected_item = None
        self_app.current_mode = "edit" # Initialize current_mode before UI updates
        # Initialize text_style_manager before UIBuilder
        from src.text_style_manager import TextStyleManager # Local import
        self_app.text_style_manager = TextStyleManager(self_app)

        # Patch QWebEngineView used in UIBuilder to avoid heavy initialization
        created_web_view = []
        class DummyWebView(QWidget):
            def __init__(self, *a, **k):
                super().__init__(*a, **k)
                self.setHtml = MagicMock()
                self.show = MagicMock()
                self.hide = MagicMock()
        def create_web_view(*a, **k):
            vw = DummyWebView()
            created_web_view.append(vw)
            return vw

        monkeypatch.setattr('src.ui_builder.QWebEngineView', create_web_view)

        # Ensure UIBuilder is called to initialize scene and other UI elements
        # This is critical as ItemOperations now depends on self.scene
        UIBuilder(self_app).build()
        self_app.web_view = created_web_view[0]
        # Initialize item_operations after UI build and scene creation
        from src.item_operations import ItemOperations # Local import
        self_app.item_operations = ItemOperations(self_app)
        return True

    monkeypatch.setattr(InfoCanvasApp, "_initial_project_setup", mock_successful_initial_setup)

    test_app = InfoCanvasApp()
    qtbot.addWidget(test_app)
    test_app.show()

    yield test_app
    # Cleanup is handled by tmp_path_factory


# Example test to ensure fixture setup is working
def test_app_creation(base_app_fixture):
    assert base_app_fixture is not None
    assert base_app_fixture.current_project_name == "test_project"
    assert base_app_fixture.isVisible()
    assert base_app_fixture.config is not None
    assert "project_name" in base_app_fixture.config
    assert base_app_fixture.config["project_name"] == "test_project"
    assert base_app_fixture.current_project_path == os.path.join(utils.PROJECTS_BASE_DIR, "test_project")

# More tests will be added below

# Helper function to clean up a project directory if it was created outside tmp_path
# For tests NOT using base_app_fixture, if they create projects in the default utils.PROJECTS_BASE_DIR
def cleanup_project_dir(project_name):
    project_path = os.path.join(utils.PROJECTS_BASE_DIR, project_name)
    if os.path.exists(project_path):
        shutil.rmtree(project_path)

@pytest.fixture
def app_for_initial_setup_test_environment(monkeypatch, tmp_path):
    """Fixture to set up the environment for testing _initial_project_setup directly."""
    original_projects_base_dir = utils.PROJECTS_BASE_DIR
    test_projects_dir = tmp_path / "projects_for_initial_setup"
    test_projects_dir.mkdir()
    monkeypatch.setattr(utils, 'PROJECTS_BASE_DIR', str(test_projects_dir))

    # Mock QMainWindow's close method to check if it's called
    # This will be patched onto the class before instance creation in the test
    closed_flags = {'closed': False}
    def mock_close_method(self_app):
        closed_flags['closed'] = True

    # Prevent UI methods from running during these specific tests
    monkeypatch.setattr(UIBuilder, 'build', lambda self: None)
    monkeypatch.setattr(InfoCanvasApp, 'populate_controls_from_config', lambda self: None)
    monkeypatch.setattr(InfoCanvasApp, 'render_canvas_from_config', lambda self: None)
    monkeypatch.setattr(InfoCanvasApp, 'update_mode_ui', lambda self: None)
    monkeypatch.setattr(InfoCanvasApp, '_update_window_title', lambda self: None)

    # Patch TextStyleManager for the app module so that InfoCanvasApp instances get a mock.
    # Using a plain MagicMock without spec as a last resort.
    from src.text_style_manager import TextStyleManager # Still good to have for context, though spec is removed
    monkeypatch.setattr('app.TextStyleManager', lambda app_arg: MagicMock())

    # Ensure scene is at least a MagicMock before ItemOperations is initialized
    monkeypatch.setattr(InfoCanvasApp, 'scene', MagicMock(spec=QGraphicsScene), raising=False)

    # Mock ProjectIO.save_config as it's called by _switch_to_project
    save_config_calls = []
    def mock_save_config(self_io, project_path, config_data, **kwargs):
        save_config_calls.append(dict(config_data))
        return True
    monkeypatch.setattr(ProjectIO, 'save_config', mock_save_config)

    yield {
        "mock_dialog_class": MockProjectManagerDialog, # Use the locally defined mock
        "closed_flags": closed_flags,
        "projects_dir": str(test_projects_dir),
        "mock_close_method": mock_close_method,
        "save_config_calls": save_config_calls
    }
    # Teardown: Restore original PROJECTS_BASE_DIR if necessary (monkeypatch handles scope)
    # shutil.rmtree(test_projects_dir) # tmp_path handles cleanup


def test_initial_setup_new_project(app_for_initial_setup_test_environment, monkeypatch, qtbot):
    env = app_for_initial_setup_test_environment
    mock_dialog_class = env["mock_dialog_class"]
    closed_flags = env["closed_flags"]
    projects_dir = env["projects_dir"]
    save_config_calls = env["save_config_calls"]
    save_config_calls.clear() # Ensure clear from previous test if fixture scope is larger
    closed_flags['closed'] = False # Reset for this test

    mock_dialog_instance = mock_dialog_class(None)
    mock_dialog_instance.set_outcome(QDialog.Accepted, "new_project_test")
    monkeypatch.setattr('app.ProjectManagerDialog', lambda *args, **kwargs: mock_dialog_instance)
    monkeypatch.setattr(InfoCanvasApp, 'close', env["mock_close_method"]) # Patch close before creating instance

    test_app_new_project = InfoCanvasApp() # __init__ calls _initial_project_setup
    # text_style_manager should be mocked by the app_for_initial_setup_test_environment fixture's patch
    qtbot.addWidget(test_app_new_project)

    assert test_app_new_project.current_project_name == "new_project_test"
    project_path = os.path.join(projects_dir, "new_project_test")
    assert test_app_new_project.current_project_path == project_path
    assert os.path.exists(project_path)
    assert os.path.exists(os.path.join(project_path, utils.PROJECT_IMAGES_DIRNAME))
    assert len(save_config_calls) > 0
    assert save_config_calls[0]["project_name"] == "new_project_test"
    assert closed_flags['closed'] is False


def test_initial_setup_load_project(app_for_initial_setup_test_environment, monkeypatch, qtbot):
    env = app_for_initial_setup_test_environment
    mock_dialog_class = env["mock_dialog_class"]
    closed_flags = env["closed_flags"]
    projects_dir = env["projects_dir"]
    closed_flags['closed'] = False # Reset for this test

    existing_project_name = "existing_project_test"
    existing_project_path = os.path.join(projects_dir, existing_project_name)
    os.makedirs(os.path.join(existing_project_path, utils.PROJECT_IMAGES_DIRNAME), exist_ok=True)
    dummy_config = utils.get_default_config()
    dummy_config["project_name"] = existing_project_name
    dummy_config["background"]["color"] = "#123456"
    with open(os.path.join(existing_project_path, utils.PROJECT_CONFIG_FILENAME), 'w') as f:
        json.dump(dummy_config, f)

    mock_dialog_instance = mock_dialog_class(None)
    mock_dialog_instance.set_outcome(QDialog.Accepted, existing_project_name)
    monkeypatch.setattr('app.ProjectManagerDialog', lambda *args, **kwargs: mock_dialog_instance)
    monkeypatch.setattr(InfoCanvasApp, 'close', env["mock_close_method"])

    test_app_load_project = InfoCanvasApp()
    # text_style_manager should be mocked by the app_for_initial_setup_test_environment fixture's patch
    qtbot.addWidget(test_app_load_project)

    assert test_app_load_project.current_project_name == existing_project_name
    assert test_app_load_project.current_project_path == existing_project_path
    assert test_app_load_project.config["background"]["color"] == "#123456"
    assert closed_flags['closed'] is False


def test_initial_setup_cancel(app_for_initial_setup_test_environment, monkeypatch, qtbot):
    env = app_for_initial_setup_test_environment
    mock_dialog_class = env["mock_dialog_class"]
    closed_flags = env["closed_flags"]
    closed_flags['closed'] = False # Reset for this test

    mock_dialog_instance = mock_dialog_class(None)
    mock_dialog_instance.set_outcome(QDialog.Rejected) # Simulate user cancelling
    monkeypatch.setattr('app.ProjectManagerDialog', lambda *args, **kwargs: mock_dialog_instance)
    monkeypatch.setattr(InfoCanvasApp, 'close', env["mock_close_method"]) # Use the flag-setting close

    expected_underlying_function = env["mock_close_method"]

    original_qtimer_singleShot = QTimer.singleShot
    timer_fired_close = {'called': False}
    def mock_singleShot_capture(delay, callback_func):
        if hasattr(callback_func, '__func__') and \
           hasattr(callback_func, '__self__') and \
           isinstance(callback_func.__self__, InfoCanvasApp) and \
           callback_func.__func__ is expected_underlying_function:
            timer_fired_close['called'] = True
            callback_func()
        else:
            original_qtimer_singleShot(delay, callback_func)

    monkeypatch.setattr('app.QTimer.singleShot', mock_singleShot_capture)

    test_app_cancel = InfoCanvasApp()
    qtbot.addWidget(test_app_cancel)

    assert timer_fired_close['called'] is True, "QTimer.singleShot with app.close was not called"
    assert closed_flags['closed'] is True, "The app's close method was not called by the timer mock"
    monkeypatch.setattr('app.QTimer.singleShot', original_qtimer_singleShot) # Restore


# --- Tests for Basic UI Interactions --- #

def test_on_mode_changed(base_app_fixture, monkeypatch):
    app = base_app_fixture
    monkeypatch.setattr(app, 'render_canvas_from_config', MagicMock())
    html_content = "<html>content</html>"
    mock_exporter_instance = MagicMock()
    mock_exporter_instance._generate_html_content.return_value = html_content
    mock_exporter_cls = MagicMock(return_value=mock_exporter_instance)
    monkeypatch.setattr('app.HtmlExporter', mock_exporter_cls)
    app.web_view.show = MagicMock()
    app.web_view.hide = MagicMock()
    app.web_view.setHtml = MagicMock()
    app.view.show = MagicMock()
    app.view.hide = MagicMock()
    mock_image_item = MagicMock(spec=DraggableImageItem)
    mock_image_item.config_data = {'id': 'img1'}
    mock_image_item.isEnabled.return_value = True
    mock_info_rect_item = MagicMock(spec=InfoRectangleItem)
    mock_info_rect_item.config_data = {'id': 'rect1'}
    mock_info_rect_item.isSelected.return_value = False
    mock_info_rect_item.isEnabled.return_value = True
    app.item_map = {"img1": mock_image_item, "rect1": mock_info_rect_item}
    if not hasattr(app, 'scene') or app.scene is None:
        app.scene = MagicMock(spec=QGraphicsScene)
    app.scene.items = MagicMock(return_value=[mock_image_item, mock_info_rect_item])

    mock_image_item.reset_mock()
    mock_info_rect_item.reset_mock()
    mock_info_rect_item.isSelected.return_value = False

    app.on_mode_changed("Edit Mode")

    assert app.current_mode == "edit"
    assert app.edit_mode_controls_widget.isVisible() is True
    assert app.view_mode_message_label.isVisible() is False
    mock_image_item.setEnabled.assert_called_with(True)
    mock_info_rect_item.setEnabled.assert_called_with(True)
    mock_info_rect_item.update_appearance.assert_called_with(mock_info_rect_item.isSelected(), False)

    mock_image_item.reset_mock()
    mock_info_rect_item.reset_mock()
    mock_info_rect_item.isSelected.return_value = False
    app.on_mode_changed("View Mode")
    assert app.current_mode == "view"
    assert app.edit_mode_controls_widget.isVisible() is False
    assert app.view_mode_message_label.isVisible() is True
    mock_image_item.setEnabled.assert_called_with(False)
    mock_info_rect_item.setEnabled.assert_called_with(False)
    mock_info_rect_item.update_appearance.assert_called_with(mock_info_rect_item.isSelected(), True)
    mock_image_item.setCursor.assert_called_with(Qt.ArrowCursor)
    mock_info_rect_item.setCursor.assert_called_with(Qt.ArrowCursor)
    mock_info_rect_item.setToolTip.assert_called()

    mock_exporter_cls.assert_called_once_with(config=app.config, project_path=app.current_project_path)
    mock_exporter_instance._generate_html_content.assert_called_once()
    app.web_view.setHtml.assert_called_once()
    set_html_args = app.web_view.setHtml.call_args[0]
    assert html_content in set_html_args[0]
    expected_base_url = QUrl.fromLocalFile(os.path.join(app.current_project_path, ""))
    assert set_html_args[1] == expected_base_url
    app.web_view.show.assert_called_once()
    app.view.hide.assert_called_once()

    mock_image_item.reset_mock()
    mock_info_rect_item.reset_mock()
    mock_info_rect_item.isSelected.return_value = False
    app.on_mode_changed("Edit Mode") # Call it again to ensure it switches back
    assert app.current_mode == "edit"
    assert app.edit_mode_controls_widget.isVisible() is True
    mock_image_item.setEnabled.assert_called_with(True)
    mock_info_rect_item.setEnabled.assert_called_with(True)
    mock_image_item.setCursor.assert_called_with(Qt.PointingHandCursor)
    mock_info_rect_item.update_appearance.assert_called_with(mock_info_rect_item.isSelected(), False)
    app.web_view.hide.assert_called()
    app.view.show.assert_called()


@patch('app.QColorDialog.getColor')
def test_choose_bg_color(mock_get_color, base_app_fixture, monkeypatch):
    app = base_app_fixture
    if "background" not in app.config or "color" not in app.config["background"]:
        app.config["background"] = {"color": "#DDDDDD", "width": 800, "height": 600}
    initial_color_hex = app.config['background']['color']
    new_color_hex = "#123456"
    mock_get_color.return_value = QColor(new_color_hex)
    monkeypatch.setattr(app, 'save_config', MagicMock())
    if not hasattr(app, 'scene') or app.scene is None:
        app.scene = MagicMock(spec=QGraphicsScene)
        app.scene.backgroundBrush = MagicMock(return_value=QBrush(QColor(initial_color_hex)))
    app.choose_bg_color()
    mock_get_color.assert_called_once()
    assert app.config['background']['color'] == new_color_hex
    assert app.scene.backgroundBrush().color().name() == new_color_hex
    app.save_config.assert_called_once()

@patch('app.QColorDialog.getColor')
def test_choose_bg_color_invalid_color(mock_get_color, base_app_fixture, monkeypatch):
    app = base_app_fixture
    if "background" not in app.config or "color" not in app.config["background"]:
        app.config["background"] = {"color": "#DDDDDD", "width": 800, "height": 600}
    initial_color_hex = app.config['background']['color']
    mock_get_color.return_value = QColor()
    monkeypatch.setattr(app, 'save_config', MagicMock())
    if not hasattr(app, 'scene') or app.scene is None:
        app.scene = MagicMock(spec=QGraphicsScene)
        app.scene.backgroundBrush = MagicMock(return_value=QBrush(QColor(initial_color_hex)))
    app.choose_bg_color()
    mock_get_color.assert_called_once()
    assert app.config['background']['color'] == initial_color_hex
    assert app.scene.backgroundBrush().color().name().lower() == initial_color_hex.lower()
    app.save_config.assert_not_called()

def test_update_bg_dimensions(base_app_fixture, monkeypatch):
    app = base_app_fixture
    monkeypatch.setattr(app, 'save_config', MagicMock())
    if not hasattr(app, 'scene') or app.scene is None:
        app.scene = MagicMock(spec=QGraphicsScene)
        app.scene.sceneRect = MagicMock(return_value=QRectF(0,0, app.config['background']['width'], app.config['background']['height']))
    if not hasattr(app, 'view') or app.view is None:
        app.view = MagicMock(spec=QGraphicsView)
    monkeypatch.setattr(app.view, 'fitInView', MagicMock())
    initial_width = app.config['background']['width']
    initial_height = app.config['background']['height']
    if isinstance(app.scene.sceneRect, MagicMock):
         app.scene.sceneRect.return_value = QRectF(0,0, initial_width, initial_height)
    else:
        assert app.scene.sceneRect().width() == initial_width
        assert app.scene.sceneRect().height() == initial_height
    new_width = 1500
    new_height = 1000
    app.bg_width_input.blockSignals(True)
    app.bg_height_input.blockSignals(True)
    app.bg_width_input.setValue(new_width)
    app.bg_height_input.setValue(new_height)
    app.bg_width_input.blockSignals(False)
    app.bg_height_input.blockSignals(False)
    app.update_bg_dimensions()
    assert app.config['background']['width'] == new_width
    assert app.config['background']['height'] == new_height
    if isinstance(app.scene.setSceneRect, MagicMock):
        app.scene.setSceneRect.assert_called_with(0, 0, new_width, new_height)
    else:
        assert app.scene.sceneRect().width() == new_width
        assert app.scene.sceneRect().height() == new_height
    if isinstance(app.view.fitInView, MagicMock):
        if isinstance(app.scene.sceneRect, MagicMock):
            app.view.fitInView.assert_called_with(app.scene.sceneRect(), Qt.KeepAspectRatio)
        else:
            app.view.fitInView.assert_called_with(QRectF(0,0, new_width, new_height), Qt.KeepAspectRatio)
    app.save_config.assert_called_once()


# --- Tests for Info Rectangle Management (methods remaining in app.py) --- #

def test_update_selected_rect_text(base_app_fixture, monkeypatch):
    app = base_app_fixture
    rect_id = "rect_to_edit_text"
    initial_text = "Old Text"
    app.config['info_rectangles'] = [{
        "id": rect_id, "text": initial_text, "center_x": 10, "center_y": 10,
        "width": 100, "height": 50, "z_index": 1
    }]
    monkeypatch.setattr(app.scene, 'clear', MagicMock())
    monkeypatch.setattr(app.scene, 'addItem', MagicMock())
    app.render_canvas_from_config()
    selected_rect_item = app.item_map.get(rect_id)
    assert selected_rect_item is not None, "Rect item not found in item_map after render"
    app.selected_item = selected_rect_item
    app.update_properties_panel()
    monkeypatch.setattr(app, 'save_config', MagicMock())
    monkeypatch.setattr(selected_rect_item, 'set_display_text', MagicMock())
    new_text = "This is the new text for the rectangle."
    app.info_rect_text_input.setPlainText(new_text)
    app.update_selected_rect_text()
    assert app.config['info_rectangles'][0]['text'] == new_text
    selected_rect_item.set_display_text.assert_called_once_with(new_text)
    app.save_config.assert_called_once()


def test_update_selected_rect_dimensions(base_app_fixture, monkeypatch):
    app = base_app_fixture
    rect_id = "rect_to_resize"
    app.config['info_rectangles'] = [{
        "id": rect_id, "text": "Resize me", "center_x": 20, "center_y": 20,
        "width": 100, "height": 50, "z_index": 1
    }]
    monkeypatch.setattr(app.scene, 'clear', MagicMock())
    monkeypatch.setattr(app.scene, 'addItem', MagicMock())
    app.render_canvas_from_config()
    selected_rect_item = app.item_map.get(rect_id)
    assert selected_rect_item is not None
    app.selected_item = selected_rect_item
    app.update_properties_panel()
    mock_slot_for_properties_changed = MagicMock()
    selected_rect_item.properties_changed.connect(mock_slot_for_properties_changed)
    monkeypatch.setattr(app, 'save_config', MagicMock())
    monkeypatch.setattr(selected_rect_item, 'update_geometry_from_config', MagicMock())
    new_width = 180
    new_height = 75
    app.info_rect_width_input.blockSignals(True)
    app.info_rect_height_input.blockSignals(True)
    app.info_rect_width_input.setValue(new_width)
    app.info_rect_height_input.setValue(new_height)
    app.info_rect_width_input.blockSignals(False)
    app.info_rect_height_input.blockSignals(False)
    app.update_selected_rect_dimensions()
    assert app.config['info_rectangles'][0]['width'] == new_width
    assert app.config['info_rectangles'][0]['height'] == new_height
    mock_slot_for_properties_changed.assert_called_once_with(selected_rect_item)
    app.save_config.assert_called_once()
    selected_rect_item.update_geometry_from_config.assert_called_once()




# --- Tests for Application State Reset --- #

@patch('app.QTimer.singleShot')
def test_reset_application_to_no_project_state(mock_qtimer_singleshot, base_app_fixture, monkeypatch):
    app = base_app_fixture
    app.current_project_name = "project_to_reset"
    app.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, "project_to_reset")
    app.config = {"project_name": "project_to_reset", "data": "some_data"}
    app.selected_item = MagicMock()
    app.item_map = {"item1": MagicMock()}
    if not hasattr(app.scene, 'items') or isinstance(app.scene.items, MagicMock):
        app.scene.items = MagicMock(return_value=[MagicMock()])
    from PyQt5.QtWidgets import QGraphicsTextItem # Local import
    dummy_scene_item = QGraphicsTextItem("dummy")
    app.scene.addItem(dummy_scene_item)
    assert len(app.scene.items()) > 0
    app.scene.setBackgroundBrush(Qt.blue)
    if not hasattr(app, 'edit_mode_controls_widget'): app.edit_mode_controls_widget = MagicMock()
    if not hasattr(app, 'info_rect_properties_widget'): app.info_rect_properties_widget = MagicMock()
    if not hasattr(app, 'image_properties_widget'): app.image_properties_widget = MagicMock()
    monkeypatch.setattr(app.edit_mode_controls_widget, 'setEnabled', MagicMock())
    monkeypatch.setattr(app, '_update_window_title', MagicMock())
    monkeypatch.setattr(app.statusBar(), 'showMessage', MagicMock())
    monkeypatch.setattr(app.info_rect_properties_widget, 'setVisible', MagicMock())
    monkeypatch.setattr(app.image_properties_widget, 'setVisible', MagicMock())
    spy_scene_clear = MagicMock()
    monkeypatch.setattr(app.scene, 'clear', spy_scene_clear)
    app._reset_application_to_no_project_state()
    assert app.current_project_name is None
    assert app.current_project_path is None
    assert app.config == {}
    assert app.selected_item is None
    assert not app.item_map
    spy_scene_clear.assert_called_once()
    assert app.scene.backgroundBrush().color().name().lower() == "#aaaaaa"
    app.edit_mode_controls_widget.setEnabled.assert_called_with(False)
    app._update_window_title.assert_called_once()
    app.statusBar().showMessage.assert_called_with("No project loaded. Please create or load a project from the File menu.")
    app.info_rect_properties_widget.setVisible.assert_called_with(False)
    app.image_properties_widget.setVisible.assert_called_with(False)
    mock_qtimer_singleshot.assert_called_once()
    assert mock_qtimer_singleshot.call_args[0][1].__name__ == '_show_project_manager_dialog_and_handle_outcome'

@patch('app.QMessageBox.information')
@patch.object(InfoCanvasApp, '_reset_application_to_no_project_state')
def test_handle_deleted_current_project(mock_reset_method, mock_qmessagebox_info, base_app_fixture):
    app = base_app_fixture
    deleted_project_name = "current_deleted_project"
    app.current_project_name = deleted_project_name
    app._handle_deleted_current_project(deleted_project_name)
    mock_qmessagebox_info.assert_called_once_with(app, "Project Deleted",
                                    f"The current project '{deleted_project_name}' has been deleted. Please select or create a new project.")
    mock_reset_method.assert_called_once()

def test_handle_deleted_other_project(base_app_fixture, monkeypatch):
    app = base_app_fixture
    app.current_project_name = "active_project"
    mock_reset_method = MagicMock()
    monkeypatch.setattr(app, '_reset_application_to_no_project_state', mock_reset_method)
    app._handle_deleted_current_project("some_other_deleted_project")
    mock_reset_method.assert_not_called()



# --- Tests for Image Management (Should be empty or only non-movable tests) --- #

# --- Tests for Text Formatting UI --- #
# Test 'test_font_color_change_updates_item_and_ui' was REMOVED as it's now in test_text_style_manager.py
# Test 'test_project_load_style_application_and_update' was REMOVED as it's now in test_text_style_manager.py

def test_ctrl_multi_select_info_rectangles(base_app_fixture, monkeypatch):
    app = base_app_fixture
    rect1 = {
        'id': 'rect1', 'width': 50, 'height': 40,
        'center_x': 60, 'center_y': 50, 'text': 'A'
    }
    rect2 = {
        'id': 'rect2', 'width': 50, 'height': 40,
        'center_x': 150, 'center_y': 50, 'text': 'B'
    }
    app.config['info_rectangles'] = [rect1, rect2]
    app.render_canvas_from_config()
    item1 = app.item_map['rect1']
    item2 = app.item_map['rect2']
    app.scene.clearSelection()
    monkeypatch.setattr(QApplication, 'keyboardModifiers', lambda: Qt.NoModifier)
    app.canvas_manager.on_graphics_item_selected(item1)
    assert item1.isSelected()
    assert not item2.isSelected()
    monkeypatch.setattr(QApplication, 'keyboardModifiers', lambda: Qt.ControlModifier)
    # Simulate Qt's selection behavior for the second item when Ctrl is pressed
    # In a real scenario, Qt would handle adding item2 to selection.
    # Here, we manually ensure both are selected before calling the handler,
    # as the handler itself might not add to selection with Ctrl if not already selected by Qt.
    item1.setSelected(True) # Ensure item1 remains selected
    item2.setSelected(True) # Manually select item2
    app.canvas_manager.on_graphics_item_selected(item2) # Call handler, which then updates app.selected_item
    assert item1.isSelected(), "Item1 should still be selected"
    assert item2.isSelected(), "Item2 should be selected"
    assert app.selected_item is item2, "App's primary selected item should be item2"


# --- Tests for Alignment Features --- #
