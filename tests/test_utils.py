import os
import shutil
import tempfile

import pytest
from PyQt5.QtWidgets import QGraphicsScene

from src import utils
from src.info_rectangle_item import InfoRectangleItem


def test_allowed_file_positive():
    assert utils.allowed_file('picture.png')

def test_allowed_file_negative():
    assert not utils.allowed_file('document.txt')

def test_get_default_config_structure():
    cfg = utils.get_default_config()
    assert 'background' in cfg and 'images' in cfg and 'info_rectangles' in cfg

def test_ensure_base_projects_directory_exists(tmp_path, monkeypatch):
    temp_dir = tmp_path / 'projects'
    monkeypatch.setattr(utils, 'PROJECTS_BASE_DIR', str(temp_dir))
    utils.ensure_base_projects_directory_exists()
    assert temp_dir.exists()


def test_normalize_z_indices(qtbot):
    scene = QGraphicsScene()
    cfg1 = {'id': 'r1', 'width': 10, 'height': 10, 'center_x': 5, 'center_y': 5,
            'text': '', 'z_index': 0}
    cfg2 = {'id': 'r2', 'width': 10, 'height': 10, 'center_x': 15, 'center_y': 5,
            'text': '', 'z_index': 10}
    item1 = InfoRectangleItem(cfg1)
    item2 = InfoRectangleItem(cfg2)
    scene.addItem(item1)
    scene.addItem(item2)
    utils.normalize_z_indices(scene)
    assert set([item1.zValue(), item2.zValue()]) == {0, 1}
    assert abs(item1.zValue() - item2.zValue()) == 1
    assert item1.config_data['z_index'] == item1.zValue()
    assert item2.config_data['z_index'] == item2.zValue()
