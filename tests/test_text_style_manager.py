import pytest
from unittest.mock import MagicMock, patch, ANY
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QComboBox, QPushButton, QMessageBox, QInputDialog, QTextEdit # Added QTextEdit for InfoAreaItem mock if needed

# Assuming utils.py and InfoAreaItem are in src and path is set up
from src import utils
from src.info_area_item import InfoAreaItem # Needed for spec and isinstance
from src.text_style_manager import TextStyleManager

@pytest.fixture
def text_style_manager_fixture(monkeypatch):
    mock_app = MagicMock()
    # Initialize config with a structure that TextStyleManager might expect.
    # Especially, ensure defaults are available if methods rely on them via app.config.
    default_config_data = utils.get_default_config()
    mock_app.config = {
        "text_styles": [],
        "defaults": default_config_data["defaults"]
    }

    # Mock UI elements that TextStyleManager interacts with directly
    # Using spec ensures that only methods/attributes that actually exist on these Qt classes can be called/accessed.
    mock_app.rect_style_combo = MagicMock(spec=QComboBox)
    mock_app.rect_font_color_button = MagicMock(spec=QPushButton)
    mock_app.rect_h_align_combo = MagicMock(spec=QComboBox)
    mock_app.rect_v_align_combo = MagicMock(spec=QComboBox)
    mock_app.rect_font_size_combo = MagicMock(spec=QComboBox)

    # Mock methods expected on the app instance
    mock_app.save_config = MagicMock()
    mock_app.statusBar = MagicMock()
    mock_app.statusBar().showMessage = MagicMock()
    mock_app.update_properties_panel = MagicMock()
    mock_app.main_window = None # For dialog parents, can be simple None or MagicMock if specific methods are called

    # Selected item setup
    # Provide a more complete mock for InfoAreaItem if its methods are called by TextStyleManager
    mock_selected_item = MagicMock(spec=InfoAreaItem)
    mock_selected_item.config_data = {} # Default empty config
    mock_selected_item.apply_style = MagicMock()
    mock_app.selected_item = mock_selected_item

    # Item map for testing style updates across multiple items
    mock_app.item_map = {}

    manager = TextStyleManager(mock_app)

    # It's often better to patch where the object is *looked up*, not where it's defined.
    # So, if TextStyleManager calls 'from PyQt5.QtWidgets import QInputDialog', then patching
    # 'src.text_style_manager.QInputDialog' is correct.
    mock_qinputdialog = MagicMock(spec=QInputDialog)
    monkeypatch.setattr('src.text_style_manager.QInputDialog', mock_qinputdialog)

    mock_qmessagebox = MagicMock(spec=QMessageBox)
    monkeypatch.setattr('src.text_style_manager.QMessageBox', mock_qmessagebox)

    mock_qcolordialog = MagicMock() # Keep it simple if only static methods like getColor are used
    monkeypatch.setattr('src.text_style_manager.QColorDialog', mock_qcolordialog)

    return manager, mock_app, mock_qinputdialog, mock_qmessagebox, mock_qcolordialog


# Test for load_styles_into_dropdown
def test_manager_load_styles_into_dropdown(text_style_manager_fixture):
    manager, mock_app, *_ = text_style_manager_fixture # Use *_ to ignore unused mock dialogs
    mock_app.config['text_styles'] = [
        {'name': 'Style1'},
        {'name': 'Style2', 'font_color': '#FF0000'}
    ]

    manager.load_styles_into_dropdown()

    mock_app.rect_style_combo.clear.assert_called_once()
    assert mock_app.rect_style_combo.addItem.call_count == 4 # Default, Custom, Style1, Style2
    mock_app.rect_style_combo.addItem.assert_any_call("Default")
    mock_app.rect_style_combo.addItem.assert_any_call("Custom")
    mock_app.rect_style_combo.addItem.assert_any_call("Style1")
    mock_app.rect_style_combo.addItem.assert_any_call("Style2")


def test_manager_font_color_change(text_style_manager_fixture):
    manager, mock_app, _, _, mock_qcolordialog = text_style_manager_fixture

    initial_item_config = {
        'id': 'rect1',
        'font_color': '#000000',
        'font_size': '12px',
        # other style properties...
    }
    mock_app.selected_item.config_data = initial_item_config.copy() # Use a copy

    # Mock QColorDialog.getColor to return a new valid QColor
    new_qcolor = QColor("#FF0000")
    mock_qcolordialog.getColor.return_value = new_qcolor

    # To correctly mock does_item_match_default_style and find_matching_style_name,
    # we can patch them directly on the manager instance if they are simple enough,
    # or ensure their dependencies (like app.config['defaults']) are set up.
    # Let's assume they work as intended and check their effects on rect_style_combo.
    # Spy on these methods to check if they are called
    manager.does_item_match_default_style = MagicMock(return_value=False)
    manager.find_matching_style_name = MagicMock(return_value=None)

    manager.handle_font_color_change()

    mock_qcolordialog.getColor.assert_called_once()
    assert mock_app.selected_item.config_data['font_color'] == new_qcolor.name()
    assert 'text_style_ref' not in mock_app.selected_item.config_data # Should be removed

    # Check that apply_style was called on the item with the updated config
    # The argument to apply_style should be the item_config itself after modification
    mock_app.selected_item.apply_style.assert_called_once_with(mock_app.selected_item.config_data)

    # Check UI updates
    mock_app.rect_font_color_button.setStyleSheet.assert_called_once()
    assert f"background-color: {new_qcolor.name()}" in mock_app.rect_font_color_button.setStyleSheet.call_args[0][0]

    # Check style combo update logic
    manager.does_item_match_default_style.assert_called_once_with(mock_app.selected_item.config_data)
    manager.find_matching_style_name.assert_called_once_with(mock_app.selected_item.config_data)
    mock_app.rect_style_combo.setCurrentText.assert_called_with("Custom")


def test_manager_style_application_and_updates(text_style_manager_fixture):
    manager, mock_app, mock_qinputdialog, mock_qmessagebox, _ = text_style_manager_fixture

    # --- Part 1: load_styles_into_dropdown (already covered by test_manager_load_styles_into_dropdown) ---
    # This part is implicitly tested if other parts rely on styles being loaded,
    # but explicit test_manager_load_styles_into_dropdown is better.

    # --- Part 2: handle_style_selection (applying a style) ---
    style1_config = {'name': 'TestStyle1', 'font_color': '#112233', 'font_size': '10px'}
    mock_app.config['text_styles'] = [style1_config]
    manager.load_styles_into_dropdown() # Ensure styles are in combo for selection

    initial_item_conf = {'id': 'rect_select', 'font_color': '#000000'}
    mock_app.selected_item.config_data = initial_item_conf.copy()

    manager.handle_style_selection('TestStyle1')

    # apply_style should be called with the style object from app.config
    mock_app.selected_item.apply_style.assert_called_with(style1_config)
    # Check that text_style_ref was added to item's config
    assert mock_app.selected_item.config_data['text_style_ref'] == 'TestStyle1'
    mock_app.update_properties_panel.assert_called()


    # --- Part 3: save_current_item_style (saving/overwriting and its effects) ---
    # Reset mocks for this part
    mock_app.selected_item.apply_style.reset_mock()
    mock_app.save_config.reset_mock()
    mock_app.rect_style_combo.setCurrentText.reset_mock() # Reset this mock specifically

    # Spy on manager's own load_styles_into_dropdown
    manager.load_styles_into_dropdown = MagicMock(wraps=manager.load_styles_into_dropdown)


    item_style_to_save = {
        'font_color': '#ABCDEF', 'font_size': '15px',
        'horizontal_alignment': 'center', 'vertical_alignment': 'middle', 'padding': '5px'
    }
    mock_app.selected_item.config_data = item_style_to_save.copy()

    # Test saving a new style
    mock_qinputdialog.getText.return_value = ("NewSavedStyle", True) # New style name

    manager.save_current_item_style()

    assert len(mock_app.config['text_styles']) == 2 # Style1 + NewSavedStyle
    new_style_in_config = next(s for s in mock_app.config['text_styles'] if s['name'] == "NewSavedStyle")
    assert new_style_in_config['font_color'] == '#ABCDEF'
    mock_app.save_config.assert_called_once()
    manager.load_styles_into_dropdown.assert_called_once()
    # Selected item should have the new style object applied, and its text_style_ref updated
    mock_app.selected_item.apply_style.assert_called_with(new_style_in_config)
    assert mock_app.selected_item.config_data['text_style_ref'] == "NewSavedStyle"
    mock_app.rect_style_combo.setCurrentText.assert_called_with("NewSavedStyle")

    # Test overwriting an existing style
    manager.load_styles_into_dropdown.reset_mock()
    mock_app.save_config.reset_mock()
    mock_app.selected_item.apply_style.reset_mock()
    mock_app.rect_style_combo.setCurrentText.reset_mock() # Reset again for overwrite check

    updated_style_details = item_style_to_save.copy()
    updated_style_details['font_color'] = '#00FF00' # Change one property
    mock_app.selected_item.config_data = updated_style_details.copy()

    mock_qinputdialog.getText.return_value = ("NewSavedStyle", True) # Same name to trigger overwrite
    mock_qmessagebox.question.return_value = QMessageBox.Yes # Confirm overwrite

    # Mock item map for testing update propagation
    mock_rect_refing_style = MagicMock(spec=InfoAreaItem)
    mock_rect_refing_style.config_data = {'id': 'rect_ref1', 'text_style_ref': 'NewSavedStyle'}
    mock_rect_refing_style.apply_style = MagicMock()

    mock_rect_not_refing_style = MagicMock(spec=InfoAreaItem)
    mock_rect_not_refing_style.config_data = {'id': 'rect_other', 'text_style_ref': 'SomeOtherStyle'}
    mock_rect_not_refing_style.apply_style = MagicMock()

    mock_app.item_map = {
        'rect_ref1': mock_rect_refing_style,
        'rect_other': mock_rect_not_refing_style,
        'selected_item_id_placeholder': mock_app.selected_item # Ensure selected_item is also in item_map if needed by logic
    }

    manager.save_current_item_style()

    assert len(mock_app.config['text_styles']) == 2 # Still 2 styles
    overwritten_style_in_config = next(s for s in mock_app.config['text_styles'] if s['name'] == "NewSavedStyle")
    assert overwritten_style_in_config['font_color'] == '#00FF00' # Check updated property

    mock_app.save_config.assert_called_once()
    manager.load_styles_into_dropdown.assert_called_once()

    # Selected item should have the overwritten style object applied
    mock_app.selected_item.apply_style.assert_called_with(overwritten_style_in_config)
    assert mock_app.selected_item.config_data['text_style_ref'] == "NewSavedStyle"
    mock_app.rect_style_combo.setCurrentText.assert_called_with("NewSavedStyle")

    # Check propagation to other items
    mock_rect_refing_style.apply_style.assert_called_once_with(overwritten_style_in_config)
    mock_rect_not_refing_style.apply_style.assert_not_called()
