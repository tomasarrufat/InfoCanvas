import os
import sys
import pytest
import copy
from PyQt5.QtWidgets import QApplication, QDialog
from app import InfoCanvasApp
from src import utils

class DummyQtBot:
    def addWidget(self, widget):
        widget.show()

@pytest.fixture(scope="session")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app

# The qtbot fixture is automatically provided by pytest-qt if it's installed.
# Removing the custom one below to ensure the real one is used.
# @pytest.fixture
# def qtbot(qapp):
#     # return DummyQtBot() # Commented out to use the real pytest-qt bot
#     # If pytest-qt is properly installed, it should provide its own qtbot fixture.
#     # If a real qtbot is not available and tests fail, pytest-qt might not be installed
#     # or the test environment isn't set up for it.
#     # For now, we assume pytest-qt will provide the fixture.
#     # If specific tests truly need a dummy bot, they might need a custom fixture name
#     # or conditional logic, but the default 'qtbot' should be the real one.
#     pass # Let pytest-qt inject its fixture.

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
        self_app.config_history = [copy.deepcopy(default_config)]
        self_app.item_map = {}
        self_app.selected_item = None
        self_app.current_mode = "edit" # Initialize current_mode before UI updates

        return True

    monkeypatch.setattr(InfoCanvasApp, "_initial_project_setup", mock_successful_initial_setup)

    test_app = InfoCanvasApp()
    qtbot.addWidget(test_app)
    test_app.show()

    yield test_app
    # Cleanup is handled by tmp_path_factory


# Example test to ensure fixture setup is working
