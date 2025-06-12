import os
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QMessageBox
from unittest.mock import patch
from tests.test_app import base_app_fixture, mock_project_manager_dialog


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
    assert 'hotspot' in content
    assert 'tooltip' in content


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
    copied = tmp_path / 'images' / 'pic.png'
    assert copied.exists()
    app.on_mode_changed('View Mode')
    assert app.export_html_button.isVisible()
    app.on_mode_changed('Edit Mode')
    assert not app.export_html_button.isVisible()


def test_generate_view_html_includes_style(base_app_fixture):
    app = base_app_fixture
    app.config['text_styles'] = {
        'highlight': {
            'font_color': '#ff0000',
            'font_size': '16px',
            'bold': True
        }
    }
    app.config.setdefault('info_rectangles', []).append({
        'id': 'r1',
        'center_x': 50,
        'center_y': 50,
        'width': 20,
        'height': 20,
        'text': 'hello',
        'style': 'highlight'
    })
    html_text = app._generate_view_html()
    assert 'data-style' in html_text
    assert 'font-size:16px' in html_text
    assert 'color:#ff0000' in html_text
