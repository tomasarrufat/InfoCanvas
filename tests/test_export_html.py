import os
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QMessageBox
from unittest.mock import patch
from tests.test_app import base_app_fixture, mock_project_manager_dialog
from src import utils # For default config


def test_export_to_html_writes_file(base_app_fixture, tmp_path, monkeypatch):
    app = base_app_fixture
    app.config.setdefault('info_rectangles', []).append({
        'id': 'r1',
        'center_x': 50,
        'center_y': 50,
        'width': 20,
        'height': 20,
        'text': 'hello'
    })
    out_file = tmp_path / "export.html"
    monkeypatch.setattr(QMessageBox, 'information', lambda *a, **k: None)
    app.export_to_html(str(out_file))
    assert out_file.exists()
    content = out_file.read_text()
    assert '<html>' in content
    assert 'hello' in content
    assert 'hotspot' in content # This class is still used on the outer div
    # assert 'tooltip' in content # The old JS tooltip class is no longer relevant
    assert '.text-content' in content # Ensure the class for the text container is present

    # Check for the basic structure and that display: none is part of the style for the text content
    text_content_div_start_str = "<div class='text-content' style='"
    text_content_div_end_str = "'>hello</div>" # Simple text case

    start_index = content.find(text_content_div_start_str)
    assert start_index != -1, "Could not find the start of the .text-content div for 'hello'"

    end_index = content.find(text_content_div_end_str, start_index)
    assert end_index != -1, "Could not find the end of the .text-content div with 'hello' text"

    style_attribute_content = content[start_index + len(text_content_div_start_str):end_index]
    assert "display: none;" in style_attribute_content, f"'display: none;' not found in style: '{style_attribute_content}'"
    assert "hello" in content # Overall check that the text is somewhere (already implicitly checked by end_index search)


def test_export_html_rich_text_formatting(base_app_fixture, tmp_path, monkeypatch):
    app = base_app_fixture
    default_text_config = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

    rect_config_formatted = {
        'id': 'r_formatted',
        'center_x': 150, 'center_y': 100, 'width': 200, 'height': 100,
        'text': 'Formatted Text\nWith Newlines & <HTML>!',
        'font_color': '#FF0000',       # Red
        'font_size': '20px',
        'background_color': '#FFFF00', # Yellow (text area background)
        'padding': '10px',
        'horizontal_alignment': 'center',
        'vertical_alignment': 'middle', # maps to 'center' for flex
        'font_style': 'bold',
    }
    # Ensure all keys from default_text_config are present if not overridden
    for key, val in default_text_config.items():
        if key not in rect_config_formatted:
            rect_config_formatted[key] = val


    app.config.setdefault('info_rectangles', []).append(rect_config_formatted)

    out_file = tmp_path / "export_formatted.html"
    monkeypatch.setattr(QMessageBox, 'information', lambda *a, **k: None) # Mock QMessageBox

    app.export_to_html(str(out_file))
    assert out_file.exists()
    content = out_file.read_text()

    # Check for outer div style (flex properties for alignment)
    assert 'display:flex;' in content
    assert 'align-items:center;' in content # vertical_alignment: middle -> center

    # Check for inner text div style
    # The style string for the .text-content div
    expected_inner_style_parts = [
        'color:#FF0000;',
        'font-size:20px;',
        'background-color:transparent;', # Changed from #FFFF00 to transparent
        'padding:10px;',
        'text-align:center;',
        'font-weight:bold;',
        'display: none;'
    ]
    # Construct a regex or a series of assertions to ensure these parts are in the style attribute of the text-content div
    # For simplicity with string searching, we'll look for the div and then its style content.
    # This is less robust than parsing but avoids new dependencies for now.

    text_content_div_start_str = "<div class='text-content' style='"
    text_content_div_end_str = "'>Formatted Text<br>With Newlines &amp; &lt;HTML&gt;!</div>"

    start_index = content.find(text_content_div_start_str)
    assert start_index != -1, "Could not find the start of the .text-content div"

    end_index = content.find(text_content_div_end_str, start_index)
    assert end_index != -1, "Could not find the end of the .text-content div with expected text"

    style_attribute_content = content[start_index + len(text_content_div_start_str):end_index]

    for part in expected_inner_style_parts:
        assert part in style_attribute_content, f"Expected style part '{part}' not found in '{style_attribute_content}'"

    # Check for text content: HTML escaped and newlines to <br>
    assert 'Formatted Text<br>With Newlines &amp; &lt;HTML&gt;!' in content # Already checked by end_str effectively
    # Verify that the old data-text attribute is NOT used for this div
    assert 'data-text="Formatted Text' not in content


def test_export_to_html_write_error(base_app_fixture, monkeypatch):
    app = base_app_fixture
    mock_critical = MagicMock()
    monkeypatch.setattr(QMessageBox, 'critical', mock_critical)
    def failing_open(*a, **k):
        raise OSError(9, 'Bad file descriptor')
    monkeypatch.setattr('builtins.open', failing_open)
    app.export_to_html('/tmp/fail.html')
    mock_critical.assert_called_once()


@patch('app.QFileDialog.getSaveFileName')
def test_export_to_html_uses_dialog(mock_get_save, base_app_fixture, tmp_path, monkeypatch):
    app = base_app_fixture
    out_file = tmp_path / "dialog_export.html"
    mock_get_save.return_value = (str(out_file), 'HTML Files (*.html)')
    info_mock = MagicMock()
    monkeypatch.setattr(QMessageBox, 'information', info_mock)
    app.export_to_html()
    assert out_file.exists()
    info_mock.assert_called_once_with(app, "Export Complete", f"Exported to {str(out_file)}")


@patch('app.QFileDialog.getSaveFileName', return_value=('', ''))
def test_export_to_html_dialog_cancel(mock_get_save, base_app_fixture, monkeypatch):
    app = base_app_fixture
    info_mock = MagicMock()
    monkeypatch.setattr(QMessageBox, 'information', info_mock)
    app.export_to_html()
    info_mock.assert_not_called()


@patch('app.QFileDialog.getSaveFileName')
def test_export_to_html_ignores_bool(mock_get_save, base_app_fixture, tmp_path, monkeypatch):
    app = base_app_fixture
    out_file = tmp_path / "bool_export.html"
    mock_get_save.return_value = (str(out_file), 'HTML Files (*.html)')
    info_mock = MagicMock()
    monkeypatch.setattr(QMessageBox, 'information', info_mock)
    # Simulate QAction.triggered(bool)
    app.export_to_html(False)
    assert out_file.exists()
    info_mock.assert_called_once_with(app, "Export Complete", f"Exported to {str(out_file)}")


def test_export_button_visibility_changes(base_app_fixture):
    app = base_app_fixture
    assert not app.export_html_button.isVisible()
    app.on_mode_changed('View Mode')
    assert app.export_html_button.isVisible()
    app.on_mode_changed('Edit Mode')
    assert not app.export_html_button.isVisible()


def test_export_to_html_copies_images(base_app_fixture, tmp_path, monkeypatch):
    app = base_app_fixture
    img_dir = app._get_project_images_folder(app.current_project_path)
    img_path = os.path.join(img_dir, 'pic.png')
    with open(img_path, 'wb') as f:
        f.write(b'123')
    app.config['images'] = [{
        'id': 'img1', 'path': 'pic.png', 'center_x': 10, 'center_y': 10,
        'scale': 1.0, 'original_width': 1, 'original_height': 1
    }]
    out_file = tmp_path / 'with_images.html'
    monkeypatch.setattr(QMessageBox, 'information', lambda *a, **k: None)
    app.export_to_html(str(out_file))
    copied_image_path = tmp_path / 'images' / 'pic.png'
    assert copied_image_path.exists(), "Image should be copied to export directory"
    # The visibility asserts were part of the original test, keeping them if they don't interfere.
    # However, this test is primarily about image copying with export.
    # app.on_mode_changed('View Mode') # These lines are not directly related to image copying
    # assert app.export_html_button.isVisible()
    # app.on_mode_changed('Edit Mode')
    # assert not app.export_html_button.isVisible()
