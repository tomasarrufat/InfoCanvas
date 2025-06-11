import os
from unittest.mock import MagicMock
from PyQt5.QtWidgets import QMessageBox
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
