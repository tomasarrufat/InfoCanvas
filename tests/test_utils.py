import os
import shutil
import tempfile

import pytest

from src import utils


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
