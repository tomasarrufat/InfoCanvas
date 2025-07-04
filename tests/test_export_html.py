import os
import re # For more flexible style checking
from unittest.mock import MagicMock, patch # Keep patch if other tests use it
from PyQt5.QtWidgets import QMessageBox # Keep if other tests use it
# Import base_app_fixture if any test still needs it.
# from tests.test_app import base_app_fixture # Not used in these new tests
from src import utils
from src.exporter import HtmlExporter
from bs4 import BeautifulSoup # <--- NEW IMPORT

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
    bg_config = utils.get_default_config()['background']


    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).extend([
        {'id': 'a1', 'center_x': 10, 'center_y': 10, 'width': 20, 'height': 20, 'text': 'a', 'shape': 'rectangle'}, # Defaults to show_on_hover: True
        {'id': 'a2', 'center_x': 40, 'center_y': 40, 'width': 20, 'height': 20, 'text': 'b', 'shape': 'rectangle'}, # Defaults to show_on_hover: True
    ])
    conn_opacity = 0.5
    sample_config.setdefault('connections', []).append({
        'id': 'c1', 'source': 'a1', 'destination': 'a2',
        'thickness': 3, 'z_index': 5, 'line_color': '#ff0000', 'opacity': conn_opacity
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "conn_export.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()

    line_svg_str = f"<svg class='connection-line' data-source='a1' data-destination='a2' data-original-opacity='{conn_opacity}'"
    assert line_svg_str in content

    assert "stroke='#ff0000'" in content # Check color within the <line> element or its style
    assert "stroke-width='3'" in content # Check thickness

    # Both a1 and a2 default to show_on_hover:True, so line should be initially hidden.
    expected_style = f"position:absolute;left:0;top:0;width:{bg_config.get('width',800)}px;height:{bg_config.get('height',600)}px;pointer-events:none;z-index:5;opacity:0;"
    assert f"style='{expected_style}'" in content # Check the SVG style


def test_export_html_lines_follow_drag(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_follow")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)
    bg_config = utils.get_default_config()['background']

    sample_config = utils.get_default_config()
    sample_config.setdefault('info_areas', []).extend([
        {'id': 'a1', 'center_x': 10, 'center_y': 10, 'width': 20, 'height': 20, 'text': 'a', 'shape': 'rectangle'}, # Defaults to show_on_hover: True
        {'id': 'a2', 'center_x': 40, 'center_y': 40, 'width': 20, 'height': 20, 'text': 'b', 'shape': 'rectangle'}, # Defaults to show_on_hover: True
    ])
    conn_opacity = 1.0 # Explicit full opacity for the line itself
    sample_config.setdefault('connections', []).append({
        'id': 'c1', 'source': 'a1', 'destination': 'a2', 'opacity': conn_opacity
    })

    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    out_file = tmp_path / "follow_export.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert 'updateConnectionLines()' in content

    line_svg_str = f"<svg class='connection-line' data-source='a1' data-destination='a2' data-original-opacity='{conn_opacity}'"
    assert line_svg_str in content

    # Both a1 and a2 default to show_on_hover:True, so line should be initially hidden (opacity:0)
    # Default z_index is 0 for connections.
    expected_style = f"position:absolute;left:0;top:0;width:{bg_config.get('width',800)}px;height:{bg_config.get('height',600)}px;pointer-events:none;z-index:0;opacity:0;"
    assert f"style='{expected_style}'" in content

# Keep other tests like test_export_to_html_write_error,
# test_export_to_html_uses_dialog, etc., as they are, because they test
# app.py's handling of HtmlExporter's results or app.py's dialog logic.
# Ensure they still have `base_app_fixture` and `monkeypatch` if they need them.

# --- MODIFIED TEST CASES FOR LINE OPACITY ---

def test_export_html_connection_line_visibility_on_hover(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_line_hover_custom_opacity")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)
    bg_config = utils.get_default_config()['background']
    line_custom_opacity = 0.6

    config = {
        'project_name': "Line Hover Custom Opacity Test",
        'background': bg_config,
        'info_areas': [
            {'id': 'ia1', 'center_x': 50, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 1', 'show_on_hover': True, 'shape': 'rectangle'},
            {'id': 'ia2', 'center_x': 200, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 2', 'show_on_hover': True, 'shape': 'rectangle'}
        ],
        'connections': [
            {'id': 'conn1', 'source': 'ia1', 'destination': 'ia2', 'line_color': '#0000FF', 'thickness': 2, 'opacity': line_custom_opacity} # z_index defaults to 0
        ],
        'defaults': utils.get_default_config()['defaults']
    }

    exporter = HtmlExporter(config=config, project_path=str(project_path))
    out_file = tmp_path / "line_hover_custom_opacity_export.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()

    # 1. Assert data-original-opacity and initial style (opacity:0 because both ends are show_on_hover:true)
    expected_line_data_attr = f"data-original-opacity='{line_custom_opacity}'"
    initial_expected_style = f"position:absolute;left:0;top:0;width:{bg_config.get('width',800)}px;height:{bg_config.get('height',600)}px;pointer-events:none;z-index:0;opacity:0;"

    line_svg_regex = rf"<svg class='connection-line' data-source='ia1' data-destination='ia2' {expected_line_data_attr} style='{initial_expected_style}'>"
    assert re.search(line_svg_regex, content), f"SVG line for conn1 not found with correct data-original-opacity and initial style. Searched for: {line_svg_regex}"


# --- New tests for show_on_hover_connected ---

def test_export_data_attributes_for_hover_connected(tmp_path_factory):
    project_path = tmp_path_factory.mktemp("project_data_attr")
    sample_config = utils.get_default_config()
    sample_config['info_areas'] = [{
        'id': 'rect1', 'center_x': 10, 'center_y': 10, 'width': 20, 'height': 20,
        'text': 'Test Area', 'shape': 'rectangle',
        'show_on_hover': False,
        'show_on_hover_connected': True
    }]
    exporter = HtmlExporter(config=sample_config, project_path=str(project_path))
    html_content = exporter._generate_html_content()
    soup = BeautifulSoup(html_content, 'html.parser')

    rect_div = soup.find('div', attrs={'data-id': 'rect1'})
    assert rect_div is not None, "Could not find info area div for rect1"
    assert rect_div.get('data-show-on-hover') == 'false', \
        "data-show-on-hover attribute is incorrect"
    assert rect_div.get('data-show-on-hover-connected') == 'true', \
        "data-show-on-hover-connected attribute is incorrect"

def test_export_initial_visibility_info_areas(tmp_path_factory):
    project_path_base = tmp_path_factory.mktemp("project_visibility_areas")

    scenarios = [
        ("scenario1_hover_true", {'show_on_hover': True, 'show_on_hover_connected': False}, "opacity:0;"),
        ("scenario2_all_false", {'show_on_hover': False, 'show_on_hover_connected': False}, None), # None means opacity:0 should NOT be present
        ("scenario3_connected_true", {'show_on_hover': False, 'show_on_hover_connected': True}, "opacity:0;")
    ]

    for name, props, expected_style_part in scenarios:
        project_path = project_path_base / name
        os.makedirs(project_path, exist_ok=True) # Ensure subdirectory exists if needed by exporter logic for images etc.

        config = utils.get_default_config()
        info_area_config = {
            'id': 'area1', 'center_x': 50, 'center_y': 50, 'width': 100, 'height': 50,
            'text': f'Test {name}', 'shape': 'rectangle',
        }
        info_area_config.update(props)
        config['info_areas'] = [info_area_config]

        exporter = HtmlExporter(config=config, project_path=str(project_path))
        html_content = exporter._generate_html_content()
        soup = BeautifulSoup(html_content, 'html.parser')

        area_div = soup.find('div', attrs={'data-id': 'area1'})
        assert area_div is not None, f"Info area div not found for {name}"

        style_attr = area_div.get('style', '').replace(' ', '').lower()

        if expected_style_part:
            assert expected_style_part in style_attr, \
                f"Expected style '{expected_style_part}' not found in '{style_attr}' for {name}"
        else:
            assert "opacity:0;" not in style_attr, \
                f"Style 'opacity:0;' should not be present in '{style_attr}' for {name}"


def test_export_initial_visibility_connection_lines(tmp_path_factory):
    project_path_base = tmp_path_factory.mktemp("project_visibility_lines")
    default_bg_config = utils.get_default_config()['background']

    base_config_info_areas = [
        {'id': 'ia1', 'center_x': 50, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 1', 'shape': 'rectangle'},
        {'id': 'ia2', 'center_x': 250, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 2', 'shape': 'rectangle'}
    ]
    base_config_connections = [{
        'id': 'conn1', 'source': 'ia1', 'destination': 'ia2',
        'line_color': '#FF0000', 'thickness': 2, 'opacity': 0.8, 'z_index': 1
    }]

    scenarios = [
        ("case_A_both_visible",
            {'ia1': {'show_on_hover': False, 'show_on_hover_connected': False},
             'ia2': {'show_on_hover': False, 'show_on_hover_connected': False}},
            f"opacity:{base_config_connections[0]['opacity']};"),
        ("case_B_ia1_hidden_hover",
            {'ia1': {'show_on_hover': True, 'show_on_hover_connected': False},
             'ia2': {'show_on_hover': False, 'show_on_hover_connected': False}},
            "opacity:0;"),
        ("case_C_ia2_hidden_connected",
            {'ia1': {'show_on_hover': False, 'show_on_hover_connected': False},
             'ia2': {'show_on_hover': False, 'show_on_hover_connected': True}},
            "opacity:0;"),
        ("case_D_both_hidden_mix",
            {'ia1': {'show_on_hover': True, 'show_on_hover_connected': False},
             'ia2': {'show_on_hover': False, 'show_on_hover_connected': True}},
            "opacity:0;")
    ]

    for name, area_props_map, expected_line_style_part in scenarios:
        project_path = project_path_base / name
        os.makedirs(project_path, exist_ok=True)

        config = utils.get_default_config()
        config['info_areas'] = []
        for area_base_conf in base_config_info_areas:
            new_area_conf = area_base_conf.copy()
            if area_base_conf['id'] in area_props_map:
                new_area_conf.update(area_props_map[area_base_conf['id']])
            config['info_areas'].append(new_area_conf)

        config['connections'] = base_config_connections

        exporter = HtmlExporter(config=config, project_path=str(project_path))
        html_content = exporter._generate_html_content()
        soup = BeautifulSoup(html_content, 'html.parser')

        line_svg = soup.find('svg', attrs={'data-id': None, 'data-source': 'ia1', 'data-destination': 'ia2'}) # Connections don't have data-id in current exporter
        assert line_svg is not None, f"Connection line svg not found for {name}"

        style_attr = line_svg.get('style', '').replace(' ', '').lower()

        # Normalize expected part for robust comparison
        normalized_expected_part = expected_line_style_part.replace(' ', '').lower()
        assert normalized_expected_part in style_attr, \
            f"Expected style part '{normalized_expected_part}' not found in '{style_attr}' for {name}"

        # Additionally, if opacity is not 0, ensure it's not accidentally 0
        if "opacity:0;" not in normalized_expected_part:
            assert "opacity:0;" not in style_attr, f"Line style should not be opacity:0 for {name}, got '{style_attr}'"


    # 2. Assert JavaScript logic for mouseenter/mouseleave
    script_content_start = content.find("<script>")
    script_content_end = content.find("</script>", script_content_start)
    script_content = content[script_content_start:script_content_end]

    # Check mouseenter logic uses data-original-opacity
    assert "h.addEventListener('mouseenter',function(){" in script_content
    assert "h.style.opacity='1';" in script_content
    assert "if(line.dataset.source === hotspotId || line.dataset.destination === hotspotId){" in script_content
    assert "line.style.opacity = line.dataset.originalOpacity;" in script_content # MODIFIED JS CHECK

    # Check mouseleave logic still sets to 0
    assert "h.addEventListener('mouseleave',function(){" in script_content
    assert "if(!otherHotspotVisible){" in script_content
    assert "line.style.opacity = '0';" in script_content

def test_export_html_connection_line_always_visible_if_one_area_is_always_visible(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_line_one_always_visible_custom_opacity")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)
    bg_config = utils.get_default_config()['background']
    line_custom_opacity = 0.8

    config = {
        'project_name': "Line One Always Visible Custom Opacity",
        'background': bg_config,
        'info_areas': [
            {'id': 'ia1', 'center_x': 50, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 1 (Hover)', 'show_on_hover': True, 'shape': 'rectangle'},
            {'id': 'ia2', 'center_x': 200, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 2 (Always Visible)', 'show_on_hover': False, 'shape': 'rectangle'}
        ],
        'connections': [
            {'id': 'conn1', 'source': 'ia1', 'destination': 'ia2', 'line_color': '#00FF00', 'thickness': 3, 'opacity': line_custom_opacity} # z_index defaults to 0
        ],
        'defaults': utils.get_default_config()['defaults']
    }

    exporter = HtmlExporter(config=config, project_path=str(project_path))
    out_file = tmp_path / "line_one_always_visible_custom_opacity.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()

    # Line should be initially visible with its own custom opacity
    expected_line_data_attr = f"data-original-opacity='{line_custom_opacity}'"
    initial_expected_style = f"position:absolute;left:0;top:0;width:{bg_config.get('width',800)}px;height:{bg_config.get('height',600)}px;pointer-events:none;z-index:0;opacity:{line_custom_opacity};"

    line_svg_regex = rf"<svg class='connection-line' data-source='ia1' data-destination='ia2' {expected_line_data_attr} style='{initial_expected_style}'>"
    assert re.search(line_svg_regex, content), f"SVG line for conn1 not found with correct data-original-opacity and initial style. Searched for: {line_svg_regex}"


def test_export_html_connection_line_respects_own_opacity_if_not_hidden_by_hover(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_line_own_opacity_both_always_visible")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)
    bg_config = utils.get_default_config()['background']
    line_custom_opacity = 0.7

    config = {
        'project_name': "Line Own Opacity Both Always Visible",
        'background': bg_config,
        'info_areas': [
            {'id': 'ia1', 'center_x': 50, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 1 (Visible)', 'show_on_hover': False, 'shape': 'rectangle'},
            {'id': 'ia2', 'center_x': 200, 'center_y': 50, 'width': 100, 'height': 50, 'text': 'Area 2 (Visible)', 'show_on_hover': False, 'shape': 'rectangle'}
        ],
        'connections': [
            {'id': 'conn1', 'source': 'ia1', 'destination': 'ia2', 'line_color': '#FF0000', 'thickness': 4, 'opacity': line_custom_opacity} # z_index defaults to 0
        ],
        'defaults': utils.get_default_config()['defaults']
    }

    exporter = HtmlExporter(config=config, project_path=str(project_path))
    out_file = tmp_path / "line_own_opacity_both_always_visible.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()

    # Line should be initially visible with its own configured opacity
    expected_line_data_attr = f"data-original-opacity='{line_custom_opacity}'"
    initial_expected_style = f"position:absolute;left:0;top:0;width:{bg_config.get('width',800)}px;height:{bg_config.get('height',600)}px;pointer-events:none;z-index:0;opacity:{line_custom_opacity};"

    line_svg_regex = rf"<svg class='connection-line' data-source='ia1' data-destination='ia2' {expected_line_data_attr} style='{initial_expected_style}'>"
    assert re.search(line_svg_regex, content), f"SVG line for conn1 not found with correct data-original-opacity and initial style. Searched for: {line_svg_regex}"


def test_export_html_contains_toggle_button(tmp_path_factory, tmp_path):
    project_path = tmp_path_factory.mktemp("project_toggle")
    os.makedirs(project_path / utils.PROJECT_IMAGES_DIRNAME, exist_ok=True)

    config = utils.get_default_config()
    exporter = HtmlExporter(config=config, project_path=str(project_path))
    out_file = tmp_path / "toggle.html"

    assert exporter.export(str(out_file)) is True
    content = out_file.read_text()
    assert "<button id='toggle-all-info'" in content
    assert "var showAllInfo" in content
