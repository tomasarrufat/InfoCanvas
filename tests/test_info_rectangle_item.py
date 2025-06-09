from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QGraphicsScene

from src.info_rectangle_item import InfoRectangleItem


def create_item():
    config = {
        'width': 100,
        'height': 50,
        'center_x': 50,
        'center_y': 25,
        'text': 'hello',
        'defaults': {'info_rectangle_text_display': {'padding': '5px'}},
    }
    return InfoRectangleItem(config)


def test_update_geometry_from_config(qtbot):
    item = create_item()
    item.config_data['width'] = 150
    item.config_data['height'] = 60
    item.config_data['center_x'] = 80
    item.config_data['center_y'] = 40
    item.update_geometry_from_config()
    assert item.boundingRect().width() == 150
    assert item.pos() == QPointF(80 - 150/2, 40 - 60/2)


def test_set_display_text(qtbot):
    item = create_item()
    item.set_display_text('updated')
    assert item.text_item.toPlainText() == 'updated'


def test_update_text_from_config(qtbot):
    item = create_item()
    item.config_data['text'] = 'again'
    item.update_text_from_config()
    assert item.text_item.toPlainText() == 'again'


def test_update_appearance_selected(qtbot):
    item = create_item()
    item.update_appearance(is_selected=True, is_view_mode=False)
    assert item._pen.color() == QColor(255, 0, 0, 200)


def test_get_resize_handle_at(qtbot):
    item = create_item()
    pos = QPointF(1, 1)
    assert item._get_resize_handle_at(pos) == InfoRectangleItem.ResizeHandle.TOP_LEFT

def test_item_change_updates_config(qtbot):
    item = create_item()
    scene = QGraphicsScene()
    scene.addItem(item)
    item.setPos(10, 15)
    assert item.config_data['center_x'] == 10 + item.boundingRect().width() / 2
    assert item.config_data['center_y'] == 15 + item.boundingRect().height() / 2

def test_update_appearance_view_mode(qtbot):
    item = create_item()
    item.update_appearance(is_view_mode=True)
    assert not item.text_item.isVisible()
    assert item._pen.color() == QColor(0, 0, 0, 0)

def test_center_text_respects_padding(qtbot):
    item = create_item()
    item.config_data['defaults']['info_rectangle_text_display']['padding'] = '20px'
    item.set_display_text('multi\nline text')
    assert item.text_item.y() >= 20

def test_item_moved_signal_emitted(qtbot):
    item = create_item()
    scene = QGraphicsScene()
    scene.addItem(item)
    moved = []
    item.item_moved.connect(lambda obj: moved.append(True))
    item.setPos(5, 5)
    assert moved and item.config_data['center_x'] == 5 + item.boundingRect().width() / 2
