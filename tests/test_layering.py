from PyQt5.QtWidgets import QGraphicsScene
from PyQt5.QtGui import QPixmap

from src.info_area_item import InfoAreaItem
from src.draggable_image_item import DraggableImageItem
from src.utils import bring_to_front, send_to_back, bring_forward, send_backward


def create_scene_items():
    scene = QGraphicsScene()
    cfg1 = {'id': 'r1', 'width': 10, 'height': 10, 'center_x': 5, 'center_y': 5, 'text': '', 'z_index': 0}
    cfg2 = {'id': 'r2', 'width': 10, 'height': 10, 'center_x': 15, 'center_y': 5, 'text': '', 'z_index': 1}
    item1 = InfoAreaItem(cfg1)
    item2 = InfoAreaItem(cfg2)
    scene.addItem(item1)
    scene.addItem(item2)
    return scene, item1, item2


def create_image_and_rect():
    scene = QGraphicsScene()
    pix = QPixmap(10, 10)
    img_cfg = {'id': 'img1', 'original_width': 10, 'original_height': 10, 'scale': 1.0,
               'center_x': 5, 'center_y': 5, 'z_index': 0}
    rect_cfg = {'id': 'r1', 'width': 10, 'height': 10, 'center_x': 5, 'center_y': 5,
                'text': '', 'z_index': 1}
    img = DraggableImageItem(pix, img_cfg)
    rect = InfoAreaItem(rect_cfg)
    scene.addItem(img)
    scene.addItem(rect)
    return scene, img, rect


def test_bring_to_front(qtbot):
    scene, item1, item2 = create_scene_items()
    bring_to_front(item1)
    assert item1.zValue() > item2.zValue() and item1.config_data['z_index'] == item1.zValue()


def test_send_to_back(qtbot):
    scene, item1, item2 = create_scene_items()
    send_to_back(item2)
    assert item2.zValue() < item1.zValue() and item2.config_data['z_index'] == item2.zValue()


def test_bring_forward(qtbot):
    scene, item1, item2 = create_scene_items()
    z_before = item1.zValue()
    bring_forward(item1)
    assert item1.zValue() == z_before + 1 and item1.config_data['z_index'] == item1.zValue()


def test_send_backward(qtbot):
    scene, item1, item2 = create_scene_items()
    z_before = item2.zValue()
    send_backward(item2)
    assert item2.zValue() == z_before - 1 and item2.config_data['z_index'] == item2.zValue()


def test_backward_then_forward(qtbot):
    scene, item1, item2 = create_scene_items()
    send_backward(item2)
    assert item2.zValue() < item1.zValue()
    bring_forward(item2)
    assert item2.zValue() > item1.zValue()


def test_mixed_items_backward_forward(qtbot):
    scene, img, rect = create_image_and_rect()
    send_backward(rect)
    assert rect.zValue() < img.zValue()
    bring_forward(rect)
    assert rect.zValue() > img.zValue()
