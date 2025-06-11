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
