import os
from PyQt5.QtWidgets import QListWidgetItem, QMessageBox, QInputDialog
from src.project_manager_dialog import ProjectManagerDialog
from src import utils

def create_dialog(tmp_path, current_project=None):
    original_base = utils.PROJECTS_BASE_DIR
    utils.PROJECTS_BASE_DIR = str(tmp_path)
    dlg = ProjectManagerDialog(current_project_name=current_project)
    return dlg, original_base

def teardown_dialog(dlg, original_base):
    utils.PROJECTS_BASE_DIR = original_base
    dlg.close()


def test_populate_project_list(tmp_path, qtbot):
    project = tmp_path / "p1"
    project.mkdir()
    (project / utils.PROJECT_CONFIG_FILENAME).write_text("{}")
    dlg, orig = create_dialog(tmp_path)
    qtbot.addWidget(dlg)
    dlg.populate_project_list()
    assert dlg.project_list_widget.count() == 1
    teardown_dialog(dlg, orig)


def test_load_selected_project(tmp_path, qtbot):
    dlg, orig = create_dialog(tmp_path)
    qtbot.addWidget(dlg)
    dlg.project_list_widget.addItem(QListWidgetItem("demo"))
    dlg.project_list_widget.setCurrentRow(0)
    dlg.load_selected_project()
    assert dlg.selected_project_name == "demo"
    teardown_dialog(dlg, orig)


def test_create_new_project_accepts_name(monkeypatch, tmp_path, qtbot):
    dlg, orig = create_dialog(tmp_path)
    qtbot.addWidget(dlg)
    monkeypatch.setattr(QInputDialog, "getText", lambda *a, **k: ("newproj", True))
    monkeypatch.setattr(os.path, "exists", lambda p: False)
    dlg.create_new_project()
    assert dlg.selected_project_name == "newproj"
    teardown_dialog(dlg, orig)


def test_confirm_delete_project_calls_delete(monkeypatch, tmp_path, qtbot):
    dlg, orig = create_dialog(tmp_path)
    qtbot.addWidget(dlg)
    dlg.project_list_widget.addItem(QListWidgetItem("todel"))
    dlg.project_list_widget.setCurrentRow(0)
    called = []
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)
    monkeypatch.setattr(dlg, "delete_project", lambda name: called.append(name))
    dlg.confirm_delete_project()
    assert called == ["todel"]
    teardown_dialog(dlg, orig)


def test_delete_project_removes_dir_and_emits_signal(monkeypatch, tmp_path, qtbot):
    proj = tmp_path / "proj"
    proj.mkdir()
    (proj / utils.PROJECT_CONFIG_FILENAME).write_text("{}")
    dlg, orig = create_dialog(tmp_path, current_project="proj")
    qtbot.addWidget(dlg)
    signals = []
    dlg.project_deleted_signal.connect(lambda name: signals.append(name))
    monkeypatch.setattr(QMessageBox, "information", lambda *a, **k: None)
    monkeypatch.setattr(dlg, "populate_project_list", lambda: None)
    dlg.delete_project("proj")
    assert not proj.exists() and signals == ["proj"]
    teardown_dialog(dlg, orig)
