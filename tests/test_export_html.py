import os
from unittest.mock import MagicMock, patch # Keep patch if other tests use it
from PyQt5.QtWidgets import QMessageBox # Keep if other tests use it
# Import base_app_fixture if any test still needs it.
from tests.test_app import base_app_fixture
from src import utils
from src.exporter import HtmlExporter # <--- NEW IMPORT

# (pytest fixtures tmp_path, tmp_path_factory are function-scoped by default)

def test_export_to_html_writes_file(tmp_path_factory, tmp_path): # No base_app_fixture
    project_path = tmp_path_factory.mktemp("project_writes_file")
    project_images_dir = project_path / utils.PROJECT_IMAGES_DIRNAME
    os.makedirs(project_images_dir, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config['project_name'] = "Test Project HTML"
    sample_config.setdefault('info_areas', []).append({
        'id': 'r1', 'center_x': 50, 'center_y': 50, 'width': 20, 'height': 20,
        'text': 'hello', 'shape': 'rectangle'
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export.html"

    success = exporter.export(str(out_file))
    assert success is True

    assert out_file.exists()
    content = out_file.read_text()
    assert '<html>' in content
    assert 'hello' in content
    assert 'hotspot' in content
    assert "class='text-content'" in content
    hotspot_start_str = "<div class='hotspot info-rectangle-export'"
    start_index = content.find(hotspot_start_str)
    assert start_index != -1
    style_attr_start = content.find("style='", start_index)
    assert style_attr_start != -1
    style_end = content.find("'", style_attr_start + 7)
    style_attribute_content = content[style_attr_start + 7:style_end]
    assert "opacity:0;" in style_attribute_content
    assert "data-show-on-hover='true'" in content
    assert "hello</p></div>" in content

def test_export_html_rich_text_formatting(tmp_path_factory, tmp_path): # No base_app_fixture
    project_path = tmp_path_factory.mktemp("project_rich_text")
    project_images_dir = project_path / utils.PROJECT_IMAGES_DIRNAME
    os.makedirs(project_images_dir, exist_ok=True)

    default_text_config = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
    rect_config_formatted = {
        'id': 'r_formatted', 'center_x': 150, 'center_y': 100, 'width': 200, 'height': 100,
        'text': 'Formatted Text\nWith Newlines & <HTML>!', 'font_color': '#FF0000',
        'font_size': '20px', 'background_color': '#FFFF00', 'padding': '10px',
        'horizontal_alignment': 'center', 'vertical_alignment': 'middle',
        'shape': 'rectangle',
    }
    # Ensure all keys from default_text_config are present if not overridden
    for key, val in default_text_config.items():
        if key not in rect_config_formatted: rect_config_formatted[key] = val

    sample_config = utils.get_default_config()
    sample_config['project_name'] = "Rich Text Test"
    sample_config.setdefault('info_areas', []).append(rect_config_formatted)

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export_formatted.html"

    success = exporter.export(str(out_file))
    assert success is True

    assert out_file.exists()
    content = out_file.read_text()
    assert 'display:flex;' in content
    assert 'align-items:center;' in content
    expected_inner_style_parts = [
        'color:#FF0000;', 'font-size:20px;', 'background-color:transparent;',
        'padding:10px;', 'text-align:center;'
    ]
    text_content_div_start_str = "<div class='text-content' style='"
    start_index = content.find(text_content_div_start_str)
    assert start_index != -1, "Could not find start of .text-content div"
    style_end = content.find("'>", start_index)
    assert style_end != -1
    style_attribute_content = content[start_index + len(text_content_div_start_str):style_end]
    for part in expected_inner_style_parts:
        assert part in style_attribute_content, f"Expected style part '{part}' not found in '{style_attribute_content}'"
    hotspot_start_str = "<div class='hotspot info-rectangle-export'"
    start_index = content.find(hotspot_start_str)
    assert start_index != -1
    style_attr_start = content.find("style='", start_index)
    assert style_attr_start != -1
    style_end = content.find("'", style_attr_start + 7)
    outer_style = content[style_attr_start + 7:style_end]
    assert "opacity:0;" in outer_style
    assert 'Formatted Text With Newlines &amp; &lt;HTML&gt;!' in content
    assert 'data-text="Formatted Text' not in content
    assert "data-show-on-hover='true'" in content

def test_export_html_markdown(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_md")
    project_images_dir = project_path / utils.PROJECT_IMAGES_DIRNAME
    os.makedirs(project_images_dir, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config['project_name'] = "MD Test"
    sample_config.setdefault('info_areas', []).append({
        'id': 'md1', 'center_x': 10, 'center_y': 10, 'width': 50, 'height': 20,
        'text': 'This is **bold**', 'font_color': '#000000', 'shape': 'rectangle'
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export_md.html"

    success = exporter.export(str(out_file))
    assert success is True

    content = out_file.read_text()
    assert '<span style=" font-weight' in content
    assert '**bold**' not in content

def test_export_html_heading_font_sizes(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_heading")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config['project_name'] = "Heading Test"
    sample_config.setdefault('info_areas', []).append({
        'id': 'h1',
        'center_x': 5,
        'center_y': 5,
        'width': 20,
        'height': 20,
        'text': '# Heading',
        'font_color': '#000000',
        'shape': 'rectangle'
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export_heading.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert 'font-size:xx-large' not in content
    assert 'font-size:28px' in content

def test_export_html_always_visible(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_always")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)
    sample_config = utils.get_default_config()
    sample_config['project_name'] = "Always"
    sample_config.setdefault('info_areas', []).append({
        'id': 'r1', 'center_x': 10, 'center_y': 10, 'width': 30, 'height': 20,
        'text': 'show', 'show_on_hover': False, 'shape': 'rectangle'
    })
    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export_always.html"
    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert "data-show-on-hover='false'" in content
    assert "opacity:0;" not in content

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


def test_export_to_html_copies_images(tmp_path_factory, tmp_path): # No base_app_fixture
    project_path_source_images = tmp_path_factory.mktemp("project_src_images")
    project_images_dir = project_path_source_images / utils.PROJECT_IMAGES_DIRNAME
    os.makedirs(project_images_dir, exist_ok=True)

    # Create a dummy image file in the source project
    with open(project_images_dir / "pic.png", 'wb') as f:
        f.write(b'dummy image data') # Dummy content

    sample_config = utils.get_default_config()
    sample_config['project_name'] = "Image Copy Test"
    sample_config['images'] = [{
        'id': 'img1', 'path': 'pic.png', 'center_x': 10, 'center_y': 10,
        'scale': 1.0, 'original_width': 1, 'original_height': 1
    }]

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path_source_images))

    export_target_dir = tmp_path / "export_output"
    # HtmlExporter.export() should create export_target_dir if it doesn't exist.
    out_file = export_target_dir / "with_images.html"

    success = exporter.export(str(out_file))
    assert success is True

    copied_image_path = export_target_dir / "images" / "pic.png"
    assert copied_image_path.exists(), f"Image should be copied to {copied_image_path}"
    # Optionally, check content if important:
    # assert copied_image_path.read_bytes() == b'dummy image data'

def test_export_html_contains_drag_script(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_drag")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).append({
        'id': 'drag1', 'center_x': 15, 'center_y': 15, 'width': 30, 'height': 20,
        'text': 'd', 'shape': 'rectangle'
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "drag_export.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert "addEventListener('mousedown'" in content
    assert "requestAnimationFrame(anim)" in content
    assert "animating = true" in content
    assert "cancelAnimationFrame(" in content


def test_export_html_ellipse_shape(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_ellipse")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).append({
        'id': 'e1', 'center_x': 20, 'center_y': 20, 'width': 40, 'height': 30,
        'text': 'ellipse', 'shape': 'ellipse'
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export_ellipse.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert "border-radius:50%" in content


def test_export_html_rotation(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_rotate")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).append({
        'id': 'rot1', 'center_x': 20, 'center_y': 20, 'width': 40, 'height': 30,
        'angle': 45, 'text': 'rotate', 'shape': 'rectangle'
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export_rotate.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert 'transform:rotate(45' in content

def test_export_html_area_fill_and_opacity(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_fill")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).append({
        'id': 'fill1', 'center_x': 10, 'center_y': 10, 'width': 30, 'height': 20,
        'text': 'c', 'shape': 'rectangle', 'fill_color': '#ff0000', 'fill_alpha': 0.5
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "export_fill.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert 'background-color:rgba(255,0,0,0.500)' in content

def test_export_html_connections(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_conn")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).extend([
        {'id': 'a1', 'center_x': 10, 'center_y': 10, 'width': 20, 'height': 20, 'text': 'a', 'shape': 'rectangle'},
        {'id': 'a2', 'center_x': 40, 'center_y': 40, 'width': 20, 'height': 20, 'text': 'b', 'shape': 'rectangle'},
    ])
    sample_config.setdefault('connections', []).append({
        'id': 'c1', 'source': 'a1', 'destination': 'a2',
        'thickness': 3, 'z_index': 5, 'line_color': '#ff0000', 'opacity': 0.5
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "conn_export.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert '<svg' in content and 'line' in content
    assert '#ff0000' in content
    assert "stroke-opacity='0.5'" in content

def test_export_html_lines_follow_drag(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_follow")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).extend([
        {'id': 'a1', 'center_x': 10, 'center_y': 10, 'width': 20, 'height': 20, 'text': 'a', 'shape': 'rectangle'},
        {'id': 'a2', 'center_x': 40, 'center_y': 40, 'width': 20, 'height': 20, 'text': 'b', 'shape': 'rectangle'},
    ])
    sample_config.setdefault('connections', []).append({
        'id': 'c1', 'source': 'a1', 'destination': 'a2'
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "follow_export.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert 'updateConnectionLines()' in content
    assert "stroke-opacity='1.0'" in content

def test_export_html_hover_connected(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_hover_conn")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).extend([
        {
            'id': 'src', 'center_x': 10, 'center_y': 10, 'width': 20, 'height': 20,
            'text': 'A', 'shape': 'rectangle', 'show_on_hover': False,
            'show_on_hover_connected': True
        },
        {
            'id': 'dst', 'center_x': 40, 'center_y': 40, 'width': 20, 'height': 20,
            'text': 'B', 'shape': 'rectangle'
        },
    ])
    sample_config.setdefault('connections', []).append({'id': 'c1', 'source': 'src', 'destination': 'dst'})

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "hover_conn.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert "data-show-on-hover-connected='true'" in content
    assert "data-hover-target='dst'" in content

# Keep other tests like test_export_to_html_write_error,
# test_export_to_html_uses_dialog, etc., as they are, because they test
# app.py's handling of HtmlExporter's results or app.py's dialog logic.
# Ensure they still have `base_app_fixture` and `monkeypatch` if they need them.
