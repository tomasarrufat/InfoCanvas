import sys
import os
import pytest
from unittest.mock import MagicMock, patch, ANY
import datetime
import copy

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from src.item_operations import ItemOperations
from src import utils
from src.draggable_image_item import DraggableImageItem
from src.info_area_item import InfoAreaItem
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QMainWindow, QFileDialog, QMessageBox
from PyQt5.QtGui import QPixmap, QImageReader, QTransform, QColor
from PyQt5.QtCore import Qt, QRectF


# --- Test Fixtures ---

@pytest.fixture
def mock_app_instance(monkeypatch, tmp_path_factory):
    app = MagicMock(spec=QMainWindow)
    app.current_project_name = "test_project"
    temp_projects_base = tmp_path_factory.mktemp("projects_base_for_item_ops_tests")
    monkeypatch.setattr(utils, 'PROJECTS_BASE_DIR', str(temp_projects_base))
    app.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, app.current_project_name)
    os.makedirs(app.current_project_path, exist_ok=True)

    app.project_io = MagicMock()
    app.project_io.get_project_images_folder.return_value = os.path.join(app.current_project_path, utils.PROJECT_IMAGES_DIRNAME)
    os.makedirs(app.project_io.get_project_images_folder.return_value, exist_ok=True)

    app.scene = MagicMock(spec=QGraphicsScene)
    app.scene.items.return_value = []
    app.scene.width.return_value = 800
    app.scene.height.return_value = 600
    app.scene.sceneRect.return_value = QRectF(0, 0, 800, 600)
    app.scene.clearSelection = MagicMock()
    app.scene.addItem = MagicMock()
    app.scene.removeItem = MagicMock()


    app.config = utils.get_default_config()
    app.config["project_name"] = app.current_project_name
    app.config.setdefault('background', {}).update({'width': 800, 'height': 600, 'color': '#DDDDDD'})
    app.config.setdefault('defaults', {}).setdefault('info_rectangle_text_display', utils.get_default_config()['defaults']['info_rectangle_text_display'])
    app.config.setdefault('images', [])
    app.config.setdefault('info_rectangles', [])


    app.item_map = {}
    app.selected_item = None
    app.clipboard_data = None

    app.img_scale_input = MagicMock()
    app.img_scale_input.value.return_value = 1.0

    app.save_config = MagicMock()
    app.statusBar = MagicMock()
    app.statusBar().showMessage = MagicMock()
    app.update_properties_panel = MagicMock()

    # Mock canvas_manager handlers used by ItemOperations
    app.canvas_manager = MagicMock()
    app.canvas_manager.on_graphics_item_selected = MagicMock()
    app.canvas_manager.on_graphics_item_moved = MagicMock()
    app.canvas_manager.on_graphics_item_properties_changed = MagicMock()

    app.current_mode = "edit"

    return app

@pytest.fixture
def item_ops(mock_app_instance):
    return ItemOperations(mock_app_instance)

# --- Initial Test ---

def test_item_operations_creation(item_ops, mock_app_instance):
    assert item_ops is not None
    assert item_ops.app == mock_app_instance
    assert item_ops.scene == mock_app_instance.scene
    assert item_ops.config == mock_app_instance.config
    assert item_ops.item_map == mock_app_instance.item_map

# --- Tests for Image Upload ---

@patch('src.item_operations.QFileDialog.getOpenFileName')
@patch('src.item_operations.shutil.copy')
@patch('src.item_operations.QImageReader')
@patch('src.item_operations.os.path.exists')
def test_upload_image_success(mock_os_path_exists, mock_qimage_reader, mock_shutil_copy, mock_qfiledialog_getopenfilename, item_ops, mock_app_instance):
    project_images_folder = item_ops._get_project_images_folder()
    source_image_path = '/fake/path/to/source_image.png'
    unique_filename = 'source_image.png'
    target_image_path = os.path.join(project_images_folder, unique_filename)
    mock_qfiledialog_getopenfilename.return_value = (source_image_path, 'Images (*.png *.jpg *.jpeg *.gif *.bmp)')
    def os_exists_side_effect(path_arg):
        if path_arg == target_image_path: return False
        return True
    mock_os_path_exists.side_effect = os_exists_side_effect
    mock_shutil_copy.return_value = target_image_path
    mock_reader_instance = MagicMock(spec=QImageReader)
    mock_reader_instance.canRead.return_value = True
    size_mock = MagicMock()
    size_mock.width.return_value = 200
    size_mock.height.return_value = 150
    mock_reader_instance.size.return_value = size_mock
    mock_qimage_reader.return_value = mock_reader_instance
    initial_image_count = len(mock_app_instance.config.get('images', []))
    item_ops.upload_image()
    mock_qfiledialog_getopenfilename.assert_called_once_with(
        mock_app_instance, "Upload Image", project_images_folder, f"Images ({' '.join(['*.' + ext for ext in utils.ALLOWED_EXTENSIONS])})"
    )
    mock_shutil_copy.assert_called_once_with(source_image_path, target_image_path)
    mock_qimage_reader.assert_called_once_with(target_image_path)
    assert len(mock_app_instance.config.get('images', [])) == initial_image_count + 1
    new_image_config = mock_app_instance.config['images'][-1]
    assert new_image_config['path'] == unique_filename
    assert new_image_config['original_width'] == 200
    assert new_image_config['original_height'] == 150
    assert 'z_index' in new_image_config
    assert new_image_config['id'] in mock_app_instance.item_map
    new_item_in_map = mock_app_instance.item_map[new_image_config['id']]
    assert isinstance(new_item_in_map, DraggableImageItem)
    mock_app_instance.scene.addItem.assert_called_once_with(new_item_in_map)
    assert new_item_in_map.isSelected() is True
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.statusBar().showMessage.assert_called_with(
        f"Image '{unique_filename}' uploaded to project '{mock_app_instance.current_project_name}'.", 3000
    )

@patch('src.item_operations.QFileDialog.getOpenFileName', return_value=('', ''))
def test_upload_image_user_cancel(mock_qfiledialog, item_ops, mock_app_instance):
    initial_image_count = len(mock_app_instance.config.get('images', []))
    item_ops.upload_image()
    assert len(mock_app_instance.config.get('images', [])) == initial_image_count
    mock_app_instance.save_config.assert_not_called()
    mock_qfiledialog.assert_called_once()

@patch('src.item_operations.QFileDialog.getOpenFileName')
@patch('src.item_operations.shutil.copy', side_effect=IOError("Disk full"))
@patch('src.item_operations.os.path.exists', return_value=False)
@patch('src.item_operations.QMessageBox.critical')
def test_upload_image_copy_fail(mock_qmessagebox_critical, mock_os_path_exists, mock_shutil_copy, mock_qfiledialog, item_ops, mock_app_instance):
    mock_qfiledialog.return_value = ('/fake/image.png', 'Images (*.png)')
    initial_image_count = len(mock_app_instance.config.get('images', []))
    item_ops.upload_image()
    assert len(mock_app_instance.config.get('images', [])) == initial_image_count
    mock_app_instance.save_config.assert_not_called()
    mock_qmessagebox_critical.assert_called_once()
    assert "Could not copy image" in mock_qmessagebox_critical.call_args[0][2]
    assert "Disk full" in mock_qmessagebox_critical.call_args[0][2]

# --- Tests for Image Scale and Delete ---

def test_update_selected_image_scale(item_ops, mock_app_instance, monkeypatch):
    img_id = "img_to_scale"
    initial_scale = 1.0
    original_width = 100
    original_height = 80
    center_x, center_y = 50, 40
    image_config = {
        "id": img_id, "path": "dummy.png", "scale": initial_scale,
        "center_x": center_x, "center_y": center_y,
        "original_width": original_width, "original_height": original_height, "z_index": 1
    }
    mock_app_instance.config['images'] = [image_config]
    mock_selected_item = MagicMock(spec=DraggableImageItem)
    mock_selected_item.config_data = image_config
    mock_pixmap = MagicMock(spec=QPixmap)
    mock_pixmap.width.return_value = original_width
    mock_pixmap.height.return_value = original_height
    mock_selected_item.pixmap.return_value = mock_pixmap
    mock_app_instance.selected_item = mock_selected_item
    mock_app_instance.item_map = {img_id: mock_selected_item}
    new_scale = 1.5
    mock_app_instance.img_scale_input.value.return_value = new_scale
    item_ops.update_selected_image_scale()
    assert mock_app_instance.config['images'][0]['scale'] == new_scale
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.scene.update.assert_called_once()
    mock_selected_item.setPos.assert_called_once()
    mock_selected_item.setTransform.assert_called_once()

@patch('src.item_operations.QMessageBox.question', return_value=QMessageBox.Yes)
@patch('src.item_operations.os.remove')
@patch('src.item_operations.os.path.exists')
def test_delete_selected_image_success(mock_os_path_exists, mock_os_remove, mock_qmessagebox_question, item_ops, mock_app_instance):
    img_id_to_delete = "img_del_1"
    img_filename = "test_delete.png"
    project_images_folder = item_ops._get_project_images_folder()
    dummy_image_file_path = os.path.join(project_images_folder, img_filename)
    os.makedirs(os.path.dirname(dummy_image_file_path), exist_ok=True)
    with open(dummy_image_file_path, 'w') as f: f.write('dummy content')
    mock_os_path_exists.return_value = True
    image_config = {
        "id": img_id_to_delete, "path": img_filename, "scale": 1.0,
        "center_x": 50, "center_y": 50, "original_width": 10, "original_height": 10, "z_index": 0
    }
    mock_app_instance.config['images'] = [image_config]
    mock_selected_item = MagicMock(spec=DraggableImageItem)
    mock_selected_item.config_data = image_config
    mock_app_instance.selected_item = mock_selected_item
    # Modify mock_app_instance.item_map in place
    mock_app_instance.item_map.clear()
    mock_app_instance.item_map[img_id_to_delete] = mock_selected_item
    original_selected_item_ref = mock_app_instance.selected_item
    initial_image_count = len(mock_app_instance.config['images'])
    item_ops.delete_selected_image()
    mock_qmessagebox_question.assert_called_once()
    mock_os_remove.assert_called_once_with(dummy_image_file_path)
    assert len(mock_app_instance.config.get('images', [])) == initial_image_count - 1
    assert img_id_to_delete not in mock_app_instance.item_map
    assert mock_app_instance.selected_item is None
    mock_app_instance.scene.removeItem.assert_called_once_with(original_selected_item_ref)
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.update_properties_panel.assert_called_once()
    mock_app_instance.statusBar().showMessage.assert_called_with(f"Image '{img_filename}' deleted.", 3000)
    if os.path.exists(dummy_image_file_path): os.remove(dummy_image_file_path)

@patch('src.item_operations.QMessageBox.question', return_value=QMessageBox.No)
def test_delete_selected_image_user_cancel(mock_qmessagebox_question, item_ops, mock_app_instance):
    img_id_stay = "img_stay_1"
    image_config = {
        "id": img_id_stay, "path": "dummy.png", "scale": 1.0,
        "center_x": 50, "center_y": 50, "original_width": 10, "original_height": 10, "z_index": 0
    }
    mock_app_instance.config['images'] = [image_config]
    mock_selected_item = MagicMock(spec=DraggableImageItem)
    mock_selected_item.config_data = image_config
    mock_app_instance.selected_item = mock_selected_item
    mock_app_instance.item_map = {img_id_stay: mock_selected_item}
    initial_image_count = len(mock_app_instance.config['images'])
    item_ops.delete_selected_image()
    assert len(mock_app_instance.config.get('images', [])) == initial_image_count
    mock_app_instance.save_config.assert_not_called()
    with patch('src.item_operations.os.remove') as mock_os_remove_cancel:
        mock_os_remove_cancel.assert_not_called()

# --- Tests for Info Area Operations ---

def test_add_info_rectangle(item_ops, mock_app_instance, monkeypatch):
    # Mock _get_next_z_index for predictable z_index
    monkeypatch.setattr(item_ops, '_get_next_z_index', lambda: 5)
    initial_rect_count = len(mock_app_instance.config.get('info_rectangles', []))
    item_ops.add_info_rectangle()
    assert len(mock_app_instance.config.get('info_rectangles', [])) == initial_rect_count + 1
    new_rect_config = mock_app_instance.config['info_rectangles'][-1]
    assert new_rect_config['text'] == "New Information"
    # Access default width from where it's defined (utils or app.config['defaults'])
    expected_width = mock_app_instance.config.get("defaults", {}).get("info_rectangle_text_display", {}).get("box_width", 150)
    assert new_rect_config['width'] == expected_width
    assert new_rect_config['height'] == 50
    assert new_rect_config['show_on_hover'] is True
    assert new_rect_config['z_index'] == 5
    assert new_rect_config['id'] in mock_app_instance.item_map
    new_item = mock_app_instance.item_map[new_rect_config['id']]
    assert isinstance(new_item, InfoAreaItem)
    mock_app_instance.scene.addItem.assert_called_once_with(new_item)
    assert new_item.isSelected()
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.statusBar().showMessage.assert_called_with("Info rectangle added.", 2000)

@patch('src.item_operations.QMessageBox.question', return_value=QMessageBox.Yes)
def test_delete_selected_info_rect_success(mock_qmessagebox, item_ops, mock_app_instance):
    rect_id_to_delete = "rect_del_1"
    rect_config = {
        "id": rect_id_to_delete, "text": "Delete Me", "center_x": 30, "center_y": 30,
        "width": 100, "height": 50, "z_index": 0
    }
    mock_app_instance.config['info_rectangles'] = [rect_config]
    mock_selected_item = MagicMock(spec=InfoAreaItem)
    mock_selected_item.config_data = rect_config
    mock_app_instance.selected_item = mock_selected_item
    mock_app_instance.item_map.clear()
    mock_app_instance.item_map[rect_id_to_delete] = mock_selected_item
    original_selected_item_ref = mock_app_instance.selected_item
    initial_rect_count = len(mock_app_instance.config['info_rectangles'])
    item_ops.delete_selected_info_rect()
    mock_qmessagebox.assert_called_once()
    assert len(mock_app_instance.config.get('info_rectangles', [])) == initial_rect_count - 1
    assert rect_id_to_delete not in mock_app_instance.item_map
    assert mock_app_instance.selected_item is None
    mock_app_instance.scene.removeItem.assert_called_once_with(original_selected_item_ref)
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.update_properties_panel.assert_called_once()
    mock_app_instance.statusBar().showMessage.assert_called_with("Info rectangle deleted.", 2000)

@patch('src.item_operations.QMessageBox.question', return_value=QMessageBox.No)
def test_delete_selected_info_rect_user_cancel(mock_qmessagebox, item_ops, mock_app_instance):
    rect_id_stay = "rect_stay_1"
    rect_config = { "id": rect_id_stay, "text": "Don't Delete" }
    mock_app_instance.config['info_rectangles'] = [rect_config]
    mock_selected_item = MagicMock(spec=InfoAreaItem)
    mock_selected_item.config_data = rect_config
    mock_app_instance.selected_item = mock_selected_item
    mock_app_instance.item_map = {rect_id_stay: mock_selected_item}
    initial_rect_count = len(mock_app_instance.config['info_rectangles'])
    item_ops.delete_selected_info_rect()
    assert len(mock_app_instance.config.get('info_rectangles', [])) == initial_rect_count
    mock_app_instance.save_config.assert_not_called()

# --- Tests for Clipboard Operations ---

def test_copy_selected_item_to_clipboard_info_rect_success(item_ops, mock_app_instance):
    mock_app_instance.current_mode = "edit"
    rect_id = "rect_for_copy"
    rect_config = {"id": rect_id, "text": "Copy Me", "width": 120, "height": 60}
    mock_selected_item = MagicMock(spec=InfoAreaItem)
    mock_selected_item.config_data = rect_config
    mock_app_instance.selected_item = mock_selected_item
    initial_clipboard_data = mock_app_instance.clipboard_data # Should be None or different

    result = item_ops.copy_selected_item_to_clipboard()

    assert result is True
    assert mock_app_instance.clipboard_data is not None
    assert mock_app_instance.clipboard_data['id'] == rect_id
    assert mock_app_instance.clipboard_data['text'] == "Copy Me"
    assert mock_app_instance.clipboard_data is not rect_config # Ensure it's a deepcopy
    mock_app_instance.statusBar().showMessage.assert_called_with("Info rectangle copied to clipboard.", 2000)

def test_copy_selected_item_to_clipboard_failure_cases(item_ops, mock_app_instance):
    # Case 1: No item selected
    mock_app_instance.selected_item = None
    mock_app_instance.current_mode = "edit"
    mock_app_instance.clipboard_data = "initial_data"
    assert item_ops.copy_selected_item_to_clipboard() is False
    assert mock_app_instance.clipboard_data == "initial_data" # Unchanged
    mock_app_instance.statusBar().showMessage.assert_not_called()

    # Case 2: Item is not an InfoAreaItem
    mock_app_instance.selected_item = MagicMock(spec=DraggableImageItem)
    mock_app_instance.selected_item.config_data = {"id": "img1"}
    assert item_ops.copy_selected_item_to_clipboard() is False
    assert mock_app_instance.clipboard_data == "initial_data"
    mock_app_instance.statusBar().showMessage.reset_mock() # Reset from previous calls if any

    # Case 3: Not in edit mode
    mock_app_instance.current_mode = "view"
    mock_selected_item_rect = MagicMock(spec=InfoAreaItem)
    mock_selected_item_rect.config_data = {"id": "rect_view_mode", "text": "Test"}
    mock_app_instance.selected_item = mock_selected_item_rect
    assert item_ops.copy_selected_item_to_clipboard() is False
    assert mock_app_instance.clipboard_data == "initial_data"
    mock_app_instance.statusBar().showMessage.reset_mock()


def test_paste_item_from_clipboard_info_rect_success(item_ops, mock_app_instance, monkeypatch):
    monkeypatch.setattr(item_ops, '_get_next_z_index', lambda: 10) # Predictable z_index
    mock_app_instance.current_mode = "edit"
    original_rect_data = {"id": "orig_rect", "text": "Pasted Text", "width": 150, "height": 70, "center_x":50, "center_y":50, "z_index":2}
    mock_app_instance.clipboard_data = copy.deepcopy(original_rect_data)
    initial_rect_count = len(mock_app_instance.config.get('info_rectangles', []))

    result = item_ops.paste_item_from_clipboard()

    assert result is True
    assert len(mock_app_instance.config.get('info_rectangles', [])) == initial_rect_count + 1
    new_rect_config = mock_app_instance.config['info_rectangles'][-1]
    assert new_rect_config['text'] == "Pasted Text"
    assert new_rect_config['id'] != "orig_rect"
    assert new_rect_config['center_x'] == original_rect_data['center_x'] + 20
    assert new_rect_config['center_y'] == original_rect_data['center_y'] + 20
    assert new_rect_config['z_index'] == 10
    assert new_rect_config['id'] in mock_app_instance.item_map
    new_item = mock_app_instance.item_map[new_rect_config['id']]
    assert isinstance(new_item, InfoAreaItem)
    mock_app_instance.scene.addItem.assert_called_once_with(new_item)
    assert new_item.isSelected()
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.statusBar().showMessage.assert_called_with("Info rectangle pasted.", 2000)

def test_paste_item_from_clipboard_failure_cases(item_ops, mock_app_instance):
    mock_app_instance.current_mode = "edit"
    initial_rect_count = len(mock_app_instance.config.get('info_rectangles', []))

    # Case 1: Clipboard is empty
    mock_app_instance.clipboard_data = None
    assert item_ops.paste_item_from_clipboard() is False
    assert len(mock_app_instance.config.get('info_rectangles', [])) == initial_rect_count
    mock_app_instance.statusBar().showMessage.assert_called_with("Clipboard is empty.", 2000)
    mock_app_instance.save_config.assert_not_called()

    # Case 2: Clipboard data is not for an InfoRectangle (current paste logic limitation)
    mock_app_instance.clipboard_data = {"id": "not_a_rect", "some_other_data": "value"}
    mock_app_instance.statusBar().showMessage.reset_mock() # Reset from previous call
    assert item_ops.paste_item_from_clipboard() is False
    assert len(mock_app_instance.config.get('info_rectangles', [])) == initial_rect_count
    mock_app_instance.statusBar().showMessage.assert_called_with("Clipboard data is not for an info area.", 2000)
    mock_app_instance.save_config.assert_not_called()

# --- Test for unified delete operation ---
@patch('src.item_operations.QMessageBox.question', return_value=QMessageBox.Yes)
@patch('src.item_operations.os.remove')
@patch('src.item_operations.os.path.exists')
def test_delete_selected_item_on_canvas_image(mock_os_exists, mock_os_remove, mock_qmessagebox, item_ops, mock_app_instance):
    img_id_to_delete = "img_del_canvas"
    img_filename = "test_delete_canvas.png"
    project_images_folder = item_ops._get_project_images_folder()
    dummy_image_file_path = os.path.join(project_images_folder, img_filename)
    os.makedirs(os.path.dirname(dummy_image_file_path), exist_ok=True)
    with open(dummy_image_file_path, 'w') as f: f.write('dummy content')
    mock_os_exists.return_value = True
    mock_image_item = MagicMock(spec=DraggableImageItem)
    mock_image_item.config_data = {
        "id": img_id_to_delete, "path": img_filename, "scale": 1.0,
        "center_x": 50, "center_y": 50, "original_width": 10, "original_height": 10, "z_index": 0
    }
    mock_app_instance.selected_item = mock_image_item
    mock_app_instance.config['images'] = [mock_image_item.config_data]
    mock_app_instance.item_map.clear()
    mock_app_instance.item_map[img_id_to_delete] = mock_image_item
    mock_app_instance.current_mode = "edit"
    original_selected_item_ref = mock_app_instance.selected_item
    deleted = item_ops.delete_selected_item_on_canvas()
    assert deleted is True
    mock_qmessagebox.assert_called_once()
    mock_os_remove.assert_called_once_with(dummy_image_file_path)
    assert img_id_to_delete not in mock_app_instance.item_map
    assert mock_app_instance.selected_item is None
    mock_app_instance.scene.removeItem.assert_called_once_with(original_selected_item_ref)
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.update_properties_panel.assert_called_once()
    mock_app_instance.statusBar().showMessage.assert_called_with(f"Image '{img_filename}' deleted.", 3000)
    if os.path.exists(dummy_image_file_path):
        os.remove(dummy_image_file_path)

@patch('src.item_operations.QMessageBox.question', return_value=QMessageBox.Yes)
def test_delete_selected_item_on_canvas_info_rect(mock_qmessagebox, item_ops, mock_app_instance):
    mock_rect_item = MagicMock(spec=InfoAreaItem)
    rect_id_to_delete = "rect_del_canvas"
    rect_config = {"id": rect_id_to_delete, "text": "Test"}
    mock_rect_item.config_data = rect_config
    mock_app_instance.selected_item = mock_rect_item
    mock_app_instance.config['info_rectangles'] = [rect_config]
    mock_app_instance.item_map.clear()
    mock_app_instance.item_map[rect_id_to_delete] = mock_rect_item
    mock_app_instance.current_mode = "edit"
    original_selected_item_ref = mock_app_instance.selected_item

    result = item_ops.delete_selected_item_on_canvas()

    assert result is True
    mock_qmessagebox.assert_called_once()
    assert rect_id_to_delete not in mock_app_instance.item_map
    assert mock_app_instance.selected_item is None
    mock_app_instance.scene.removeItem.assert_called_once_with(original_selected_item_ref)
    mock_app_instance.save_config.assert_called_once()
    mock_app_instance.update_properties_panel.assert_called_once()
    mock_app_instance.statusBar().showMessage.assert_called_with("Info rectangle deleted.", 2000)

def test_delete_selected_item_on_canvas_no_selection(item_ops, mock_app_instance):
    mock_app_instance.selected_item = None
    mock_app_instance.current_mode = "edit"
    assert item_ops.delete_selected_item_on_canvas() is False

def test_delete_selected_item_on_canvas_wrong_mode(item_ops, mock_app_instance):
    mock_app_instance.selected_item = MagicMock(spec=DraggableImageItem)
    mock_app_instance.current_mode = "view"
    assert item_ops.delete_selected_item_on_canvas() is False

# End of tests
