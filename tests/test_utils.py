import os
import shutil
import tempfile

import pytest
from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtCore import QRectF

from src import utils
from src.info_area_item import InfoAreaItem


def test_allowed_file_positive():
    assert utils.allowed_file('picture.png')

def test_allowed_file_negative():
    assert not utils.allowed_file('document.txt')

def test_get_default_config_structure():
    cfg = utils.get_default_config()
    assert 'background' in cfg and 'images' in cfg and 'info_areas' in cfg and 'connections' in cfg

def test_ensure_base_projects_directory_exists(tmp_path, monkeypatch):
    temp_dir = tmp_path / 'projects'
    monkeypatch.setattr(utils, 'PROJECTS_BASE_DIR', str(temp_dir))
    utils.ensure_base_projects_directory_exists()
    assert temp_dir.exists()


def test_normalize_z_indices(qtbot):
    scene = QGraphicsScene()
    cfg1 = {
        'id': 'r1', 'width': 10, 'height': 10, 'center_x': 5, 'center_y': 5,
        'text': '', 'z_index': 0, 'shape': 'rectangle'
    }
    cfg2 = {
        'id': 'r2', 'width': 10, 'height': 10, 'center_x': 15, 'center_y': 5,
        'text': '', 'z_index': 10, 'shape': 'rectangle'
    }
    item1 = InfoAreaItem(cfg1)
    item2 = InfoAreaItem(cfg2)
    scene.addItem(item1)
    scene.addItem(item2)
    utils.normalize_z_indices(scene)
    assert set([item1.zValue(), item2.zValue()]) == {0, 1}
    assert abs(item1.zValue() - item2.zValue()) == 1
    assert item1.config_data['z_index'] == item1.zValue()
    assert item2.config_data['z_index'] == item2.zValue()


def test_compute_connection_points(qtbot):
    src = {'id': 's', 'center_x': 10, 'center_y': 10, 'width': 20, 'height': 20, 'shape': 'rectangle'}
    dst = {'id': 'd', 'center_x': 40, 'center_y': 40, 'width': 20, 'height': 20, 'shape': 'rectangle'}
    x1, y1, x2, y2 = utils.compute_connection_points(src, dst)

    assert (x1, y1) != (src['center_x'], src['center_y'])
    assert (x2, y2) != (dst['center_x'], dst['center_y'])
