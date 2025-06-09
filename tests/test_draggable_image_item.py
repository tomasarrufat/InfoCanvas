from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QGraphicsScene

from src.draggable_image_item import DraggableImageItem


def create_item(width=10, height=10):
    pixmap = QPixmap(width, height)
    config = {
        'original_width': width,
        'original_height': height,
        'scale': 1.0,
        'center_x': width / 2,
        'center_y': height / 2,
    }
    item = DraggableImageItem(pixmap, config)
    return item, config


def test_bounding_rect(qtbot):
    item, _ = create_item(20, 15)
    rect = item.boundingRect()
    assert rect.width() == 20 and rect.height() == 15


def test_bounding_rect_null_pixmap(qtbot):
    pixmap = QPixmap()
    item = DraggableImageItem(pixmap, {})
    rect = item.boundingRect()
    assert rect.width() == 0 and rect.height() == 0


def test_set_pixmap_updates_size(qtbot):
    item, _ = create_item(10, 10)
    new_pixmap = QPixmap(30, 40)
    item.setPixmap(new_pixmap)
    rect = item.boundingRect()
    assert rect.width() == 30 and rect.height() == 40


def test_item_position_updates_config(qtbot):
    item, cfg = create_item(10, 10)
    scene = QGraphicsScene()
    scene.addItem(item)
    item.setPos(5, 5)
    assert cfg['center_x'] == 5 + 10/2 and cfg['center_y'] == 5 + 10/2

def test_item_moved_signal_emitted(qtbot):
    item, cfg = create_item(10, 10)
    scene = QGraphicsScene()
    scene.addItem(item)
    moved = []
    item.item_moved.connect(lambda obj: moved.append(True))
    item.setPos(3, 4)
    assert moved and cfg['center_x'] == 3 + 5 and cfg['center_y'] == 4 + 5

def test_item_position_scaled_update(qtbot):
    item, cfg = create_item(10, 10)
    cfg['scale'] = 2.0
    scene = QGraphicsScene()
    scene.addItem(item)
    item.setPos(1, 1)
    assert cfg['center_x'] == 1 + 20/2 and cfg['center_y'] == 1 + 20/2
