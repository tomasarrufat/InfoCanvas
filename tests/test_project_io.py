import os
import json
from unittest.mock import mock_open, patch, MagicMock

import pytest

from src import utils
from src.project_io import ProjectIO

@pytest.fixture
def project_io_fixture(tmp_path, monkeypatch):
    monkeypatch.setattr(utils, 'PROJECTS_BASE_DIR', str(tmp_path))
    return ProjectIO()

# --- switch_to_project tests ---

def test_switch_to_new_project(project_io_fixture, monkeypatch):
    pio = project_io_fixture
    new_project = "switched_new_project"

    save_calls = []
    def mock_save(project_path, config_data, **kwargs):
        save_calls.append(dict(config_data))
        os.makedirs(project_path, exist_ok=True)
        os.makedirs(os.path.join(project_path, utils.PROJECT_IMAGES_DIRNAME), exist_ok=True)
        return True
    monkeypatch.setattr(pio, 'save_config', mock_save)

    success = pio.switch_to_project(new_project, is_new_project=True)
    assert success is True
    project_path = os.path.join(utils.PROJECTS_BASE_DIR, new_project)
    assert pio.current_project_name == new_project
    assert pio.current_project_path == project_path
    assert os.path.isdir(project_path)
    assert os.path.isdir(os.path.join(project_path, utils.PROJECT_IMAGES_DIRNAME))
    assert save_calls and save_calls[0]["project_name"] == new_project


def test_switch_to_existing_project(project_io_fixture):
    pio = project_io_fixture
    existing = "switched_existing_project"
    project_path = os.path.join(utils.PROJECTS_BASE_DIR, existing)
    os.makedirs(os.path.join(project_path, utils.PROJECT_IMAGES_DIRNAME), exist_ok=True)
    cfg = utils.get_default_config()
    cfg["project_name"] = existing
    cfg["background"]["color"] = "#abcdef"
    with open(os.path.join(project_path, utils.PROJECT_CONFIG_FILENAME), 'w') as f:
        json.dump(cfg, f)

    success = pio.switch_to_project(existing, is_new_project=False)
    assert success is True
    assert pio.current_project_name == existing
    assert pio.current_project_path == project_path
    assert pio.config["background"]["color"] == "#abcdef"


def test_switch_to_project_load_failure(project_io_fixture, monkeypatch):
    pio = project_io_fixture
    bad = "bad_config_project"
    project_path = os.path.join(utils.PROJECTS_BASE_DIR, bad)
    os.makedirs(os.path.join(project_path, utils.PROJECT_IMAGES_DIRNAME), exist_ok=True)
    with open(os.path.join(project_path, utils.PROJECT_CONFIG_FILENAME), 'w') as f:
        f.write("not json")
    monkeypatch.setattr('src.project_io.QMessageBox.warning', lambda *a, **k: None)

    success = pio.switch_to_project(bad, is_new_project=False)
    assert success is False
    assert pio.current_project_name == bad
    assert pio.config is None

# --- path helpers ---

def test_get_project_config_path(project_io_fixture):
    pio = project_io_fixture
    expected = os.path.join(utils.PROJECTS_BASE_DIR, "my_project", utils.PROJECT_CONFIG_FILENAME)
    assert pio.get_project_config_path("my_project") == expected
    abs_dir = os.path.join(utils.PROJECTS_BASE_DIR, "abs_project_dir")
    os.makedirs(abs_dir, exist_ok=True)
    expected_abs = os.path.join(abs_dir, utils.PROJECT_CONFIG_FILENAME)
    assert pio.get_project_config_path(abs_dir) == expected_abs


def test_get_project_images_folder(project_io_fixture):
    pio = project_io_fixture
    expected = os.path.join(utils.PROJECTS_BASE_DIR, "my_project", utils.PROJECT_IMAGES_DIRNAME)
    assert pio.get_project_images_folder("my_project") == expected
    abs_dir = os.path.join(utils.PROJECTS_BASE_DIR, "abs_project_dir")
    os.makedirs(abs_dir, exist_ok=True)
    expected_abs = os.path.join(abs_dir, utils.PROJECT_IMAGES_DIRNAME)
    assert pio.get_project_images_folder(abs_dir) == expected_abs

# --- save/load config ---

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open)
def test_save_config_success(mock_file_open, mock_os_exists, project_io_fixture, monkeypatch):
    pio = project_io_fixture
    mock_os_exists.return_value = True
    monkeypatch.setattr(pio, 'ensure_project_structure_exists', lambda path: True)
    status = MagicMock()
    pio.current_project_name = "test_save_proj"
    pio.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, pio.current_project_name)

    cfg = {"project_name": pio.current_project_name, "setting1": "value1"}
    result = pio.save_config(pio.current_project_path, cfg, item_map={}, status_bar=status, current_project_name=pio.current_project_name)
    assert result is True
    mock_file_open.assert_called_once_with(pio.get_project_config_path(pio.current_project_path), 'w')
    handle = mock_file_open()
    written = "".join(c[0][0] for c in handle.write.call_args_list if c[0])
    data = json.loads(written)
    assert data["setting1"] == "value1"
    assert "last_modified" in data
    assert data["project_name"] == pio.current_project_name
    status.showMessage.assert_called_with(f"Configuration for '{pio.current_project_name}' saved.", 2000)

@patch('os.path.exists')
@patch('builtins.open', side_effect=IOError("Disk full"))
def test_save_config_io_error(mock_file_open_error, mock_os_exists, project_io_fixture, monkeypatch):
    pio = project_io_fixture
    mock_os_exists.return_value = True
    monkeypatch.setattr(pio, 'ensure_project_structure_exists', lambda path: True)
    mock_crit = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.critical', mock_crit)
    pio.current_project_name = "test_io_error_proj"
    pio.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, pio.current_project_name)
    cfg = {"project_name": pio.current_project_name, "data": "some"}
    result = pio.save_config(pio.current_project_path, cfg, item_map={}, status_bar=None, current_project_name=pio.current_project_name)
    assert result is False
    mock_file_open_error.assert_called_once_with(pio.get_project_config_path(pio.current_project_path), 'w')
    mock_crit.assert_called_once()
    assert mock_crit.call_args[0][1] == "Save Error"


def test_save_config_no_project_path(project_io_fixture, monkeypatch):
    pio = project_io_fixture
    pio.current_project_path = None
    pio.current_project_name = None
    pio.config = {}
    crit = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.critical', crit)
    result = pio.save_config(None, {}, item_map={})
    assert result is False
    crit.assert_called_with(None, "Save Error", "No project selected. Cannot save configuration.")

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open)
def test_load_config_for_current_project_success(mock_file_open, mock_os_exists, project_io_fixture):
    pio = project_io_fixture
    pio.current_project_name = "test_load_proj"
    pio.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, pio.current_project_name)
    mock_os_exists.return_value = True
    expected = {"project_name": pio.current_project_name, "data": "loaded"}
    mock_file_open.return_value.read.return_value = json.dumps(expected)
    loaded = pio.load_config_for_current_project()
    assert loaded == expected
    mock_file_open.assert_called_once_with(pio.get_project_config_path(pio.current_project_path), 'r')

@patch('os.path.exists')
def test_load_config_file_not_found(mock_os_exists, project_io_fixture, monkeypatch):
    pio = project_io_fixture
    pio.current_project_name = "non_existent"
    pio.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, pio.current_project_name)
    warn = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.warning', warn)
    mock_os_exists.return_value = False
    loaded = pio.load_config_for_current_project()
    assert loaded is None
    warn.assert_called_once()
    assert warn.call_args[0][1] == "Load Error"

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open)
def test_load_config_json_decode_error(mock_file_open, mock_os_exists, project_io_fixture, monkeypatch):
    pio = project_io_fixture
    pio.current_project_name = "json_error"
    pio.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, pio.current_project_name)
    warn = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.warning', warn)
    mock_os_exists.return_value = True
    mock_file_open.return_value.read.return_value = "not json"
    loaded = pio.load_config_for_current_project()
    assert loaded is None
    warn.assert_called_once()
    assert warn.call_args[0][1] == "Load Error"


def test_load_config_no_project_path(project_io_fixture, monkeypatch):
    pio = project_io_fixture
    pio.current_project_path = None
    crit = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.critical', crit)
    loaded = pio.load_config_for_current_project()
    assert loaded is None
    crit.assert_called_with(None, "Load Error", "No project path set. Cannot load configuration.")

@patch('os.path.exists')
@patch('builtins.open', new_callable=mock_open)
@patch('src.project_io.QImageReader')
def test_save_config_populates_missing_image_dimensions(mock_reader_cls, mock_file_open, mock_os_exists, project_io_fixture, monkeypatch):
    pio = project_io_fixture
    mock_os_exists.return_value = True
    monkeypatch.setattr(pio, 'ensure_project_structure_exists', lambda path: True)
    status = MagicMock()
    reader_instance = MagicMock()
    reader_instance.canRead.return_value = True
    size_mock = MagicMock()
    size_mock.width.return_value = 800
    size_mock.height.return_value = 600
    reader_instance.size.return_value = size_mock
    mock_reader_cls.return_value = reader_instance

    pio.current_project_name = "image_dim_proj"
    pio.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, pio.current_project_name)
    os.makedirs(pio.current_project_path, exist_ok=True)
    img_folder = pio.get_project_images_folder(pio.current_project_path)
    os.makedirs(img_folder, exist_ok=True)
    filename = "test_image.png"

    pio.config = {"project_name": pio.current_project_name, "images": [{"id": "img1", "path": filename}]}
    pio.save_config(pio.current_project_path, pio.config, item_map={}, status_bar=status, current_project_name=pio.current_project_name)
    written = "".join(c[0][0] for c in mock_file_open.return_value.write.call_args_list if c[0])
    data = json.loads(written)
    img_conf = data["images"][0]
    assert img_conf["original_width"] == 800
    assert img_conf["original_height"] == 600


# --- copy_project_data tests ---

SOURCE_PROJECT_NAME = "test_source_project"
NEW_PROJECT_NAME = "test_new_project"
IMAGE_FILENAME = "image1.png"
SOURCE_CONFIG_DATA = {
    "project_name": SOURCE_PROJECT_NAME,
    "version": "1.0",
    "last_modified": "2023-01-01T00:00:00Z",
    "images": [{"id": "img1", "path": IMAGE_FILENAME, "original_width": 100, "original_height": 100, "x": 5, "y": 5, "scale": 1.0, "rotation": 0.0}],
    "scene_items": [{"type": "image", "id": "img1", "x": 10, "y": 10, "scale": 1.0, "rotation": 0}],
    "background": {"color": "#FFFFFF", "grid_visible": True, "grid_spacing": 10},
    "camera": {"x":0, "y":0, "zoom":1.0}
}

def setup_source_project(base_path, project_name, config_data, image_filename=None):
    """Helper to create a source project structure."""
    source_project_path = os.path.join(base_path, project_name)
    source_images_path = os.path.join(source_project_path, utils.PROJECT_IMAGES_DIRNAME)
    os.makedirs(source_images_path, exist_ok=True)

    with open(os.path.join(source_project_path, utils.PROJECT_CONFIG_FILENAME), 'w') as f:
        json.dump(config_data, f, indent=2)

    if image_filename:
        with open(os.path.join(source_images_path, image_filename), 'w') as f:
            f.write("dummy image data") # Content doesn't matter for copy2
    return source_project_path


def test_copy_project_data_successful_copy(project_io_fixture, monkeypatch):
    pio = project_io_fixture # project_io_fixture already patches utils.PROJECTS_BASE_DIR

    mock_q_critical = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.critical', mock_q_critical)

    # Setup source project
    setup_source_project(utils.PROJECTS_BASE_DIR, SOURCE_PROJECT_NAME, SOURCE_CONFIG_DATA, IMAGE_FILENAME)
    original_last_modified = SOURCE_CONFIG_DATA["last_modified"]

    # Perform copy operation
    result = pio.copy_project_data(SOURCE_PROJECT_NAME, NEW_PROJECT_NAME)

    # Assertions
    assert result is True
    mock_q_critical.assert_not_called()

    new_project_path = os.path.join(utils.PROJECTS_BASE_DIR, NEW_PROJECT_NAME)
    new_images_path = os.path.join(new_project_path, utils.PROJECT_IMAGES_DIRNAME)
    new_config_path = os.path.join(new_project_path, utils.PROJECT_CONFIG_FILENAME)

    assert os.path.isdir(new_project_path)
    assert os.path.isdir(new_images_path)
    assert os.path.isfile(new_config_path)
    assert os.path.isfile(os.path.join(new_images_path, IMAGE_FILENAME))

    with open(new_config_path, 'r') as f:
        new_config_data = json.load(f)

    assert new_config_data["project_name"] == NEW_PROJECT_NAME
    assert new_config_data["last_modified"] != original_last_modified
    # Could add a more specific time check if necessary, e.g., using datetime.fromisoformat
    assert new_config_data["images"] == SOURCE_CONFIG_DATA["images"] # Should be an exact copy
    assert new_config_data["scene_items"] == SOURCE_CONFIG_DATA["scene_items"] # Should be an exact copy
    assert new_config_data["background"] == SOURCE_CONFIG_DATA["background"]
    assert new_config_data["camera"] == SOURCE_CONFIG_DATA["camera"]
    assert new_config_data["version"] == SOURCE_CONFIG_DATA["version"]


def test_copy_project_data_source_project_does_not_exist(project_io_fixture, monkeypatch):
    pio = project_io_fixture
    mock_q_critical = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.critical', mock_q_critical)

    result = pio.copy_project_data("non_existent_source", NEW_PROJECT_NAME)

    assert result is False
    new_project_path = os.path.join(utils.PROJECTS_BASE_DIR, NEW_PROJECT_NAME)
    assert not os.path.exists(new_project_path)

    # Check that QMessageBox.critical was called.
    # The ProjectIO.copy_project_data first checks for source_config_file existence.
    mock_q_critical.assert_called_once()
    # Example: assert "Source project configuration file not found" in mock_q_critical.call_args[0][1]
    # We rely on the method's internal logging/messaging for specific error.
    # The key is that it failed and reported an error.


def test_copy_project_data_empty_images_directory(project_io_fixture, monkeypatch):
    pio = project_io_fixture
    mock_q_critical = MagicMock()
    monkeypatch.setattr('src.project_io.QMessageBox.critical', mock_q_critical)

    source_empty_img_project_name = "source_empty_images"
    config_empty_images = SOURCE_CONFIG_DATA.copy()
    config_empty_images["project_name"] = source_empty_img_project_name
    config_empty_images["images"] = [] # No images in config
    config_empty_images["scene_items"] = [] # No scene items referencing images

    # Setup source project without image file, and config reflecting no images
    setup_source_project(utils.PROJECTS_BASE_DIR, source_empty_img_project_name, config_empty_images, image_filename=None)

    target_project_name = "new_empty_images_target"
    result = pio.copy_project_data(source_empty_img_project_name, target_project_name)

    assert result is True
    mock_q_critical.assert_not_called()

    new_project_path = os.path.join(utils.PROJECTS_BASE_DIR, target_project_name)
    new_images_path = os.path.join(new_project_path, utils.PROJECT_IMAGES_DIRNAME)
    new_config_path = os.path.join(new_project_path, utils.PROJECT_CONFIG_FILENAME)

    assert os.path.isdir(new_project_path)
    assert os.path.isdir(new_images_path)
    assert not os.listdir(new_images_path) # Images directory should be empty
    assert os.path.isfile(new_config_path)

    with open(new_config_path, 'r') as f:
        new_config_data = json.load(f)

    assert new_config_data["project_name"] == target_project_name
    assert new_config_data["images"] == [] # Preserved empty images list
    assert new_config_data["scene_items"] == [] # Preserved empty scene_items list
