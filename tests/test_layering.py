from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtGui import QPixmap
import pytest

from src.info_area_item import InfoAreaItem
from src.draggable_image_item import DraggableImageItem
from src.utils import bring_to_front, send_to_back, bring_forward, send_backward


def create_scene_items(shape='rectangle'):
    scene = QGraphicsScene()
    cfg1 = {
        'id': 'r1', 'width': 10, 'height': 10, 'center_x': 5, 'center_y': 5,
        'text': '', 'z_index': 0, 'shape': shape
    }
    cfg2 = {
        'id': 'r2', 'width': 10, 'height': 10, 'center_x': 15, 'center_y': 5,
        'text': '', 'z_index': 1, 'shape': shape
    }
    item1 = InfoAreaItem(cfg1)
    item2 = InfoAreaItem(cfg2)
    scene.addItem(item1)
    scene.addItem(item2)
    return scene, item1, item2


def create_image_and_rect(shape='rectangle'):
    scene = QGraphicsScene()
    pix = QPixmap(10, 10)
    img_cfg = {
        'id': 'img1', 'original_width': 10, 'original_height': 10, 'scale': 1.0,
        'center_x': 5, 'center_y': 5, 'z_index': 0
    }
    rect_cfg = {
        'id': 'r1', 'width': 10, 'height': 10, 'center_x': 5, 'center_y': 5,
        'text': '', 'z_index': 1, 'shape': shape
    }
    img = DraggableImageItem(pix, img_cfg)
    rect = InfoAreaItem(rect_cfg)
    scene.addItem(img)
    scene.addItem(rect)
    return scene, img, rect




@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
def test_bring_to_front(qtbot, shape):
    scene, item1, item2 = create_scene_items(shape)
    bring_to_front(item1)
    assert item1.zValue() > item2.zValue() and item1.config_data['z_index'] == item1.zValue()


@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
def test_send_to_back(qtbot, shape):
    scene, item1, item2 = create_scene_items(shape)
    send_to_back(item2)
    assert item2.zValue() < item1.zValue() and item2.config_data['z_index'] == item2.zValue()


@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
def test_bring_forward(qtbot, shape):
    scene, item1, item2 = create_scene_items(shape)
    z_before = item1.zValue()
    bring_forward(item1)
    assert item1.zValue() == z_before + 1 and item1.config_data['z_index'] == item1.zValue()


@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
def test_send_backward(qtbot, shape):
    scene, item1, item2 = create_scene_items(shape)
    z_before = item2.zValue()
    send_backward(item2)
    assert item2.zValue() == z_before - 1 and item2.config_data['z_index'] == item2.zValue()


@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
def test_backward_then_forward(qtbot, shape):
    scene, item1, item2 = create_scene_items(shape)
    send_backward(item2)
    assert item2.zValue() < item1.zValue()
    bring_forward(item2)
    assert item2.zValue() > item1.zValue()


@pytest.mark.parametrize("shape", ["rectangle", "ellipse"])
def test_mixed_items_backward_forward(qtbot, shape):
    scene, img, rect = create_image_and_rect(shape)
    send_backward(rect)
    assert rect.zValue() < img.zValue()
    bring_forward(rect)
    assert rect.zValue() > img.zValue()
