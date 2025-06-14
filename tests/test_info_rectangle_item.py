import pytest
from PyQt5.QtCore import QPointF, Qt, QRectF, QPoint
from PyQt5.QtGui import QColor, QFont, QTextOption, QCursor
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsSceneMouseEvent, QGraphicsSceneHoverEvent, QGraphicsItem
from pytestqt.qt_compat import qt_api
from unittest.mock import Mock, patch

from src.info_rectangle_item import InfoRectangleItem
from src import utils # For default config

# QApplication instance is typically managed by pytest-qt's qapp fixture.

# Constants for resize handles
TOP_LEFT = InfoRectangleItem.ResizeHandle.TOP_LEFT
TOP = InfoRectangleItem.ResizeHandle.TOP
TOP_RIGHT = InfoRectangleItem.ResizeHandle.TOP_RIGHT
LEFT = InfoRectangleItem.ResizeHandle.LEFT
RIGHT = InfoRectangleItem.ResizeHandle.RIGHT
BOTTOM_LEFT = InfoRectangleItem.ResizeHandle.BOTTOM_LEFT
BOTTOM = InfoRectangleItem.ResizeHandle.BOTTOM
BOTTOM_RIGHT = InfoRectangleItem.ResizeHandle.BOTTOM_RIGHT
NONE = InfoRectangleItem.ResizeHandle.NONE


@pytest.fixture
def default_text_config_values(): # Renamed to avoid conflict with a potential fixture named default_text_config
    return utils.get_default_config()["defaults"]["info_rectangle_text_display"]

@pytest.fixture
def mock_parent_window():
    window = Mock()
    window.current_mode = "edit" # Default to edit mode
    mock_scene = Mock(spec=QGraphicsScene)
    mock_scene.parent_window = window
    window.scene = Mock(return_value=mock_scene)
    return window

@pytest.fixture
def create_item_with_scene(default_text_config_values, qtbot, mock_parent_window):
    def _create_item_with_scene(custom_config=None, add_to_scene=True, selectable=False, parent_window=mock_parent_window):
        base_config = {
            'id': 'rect1', 'width': 100, 'height': 50,
            'center_x': 50, 'center_y': 25, 'text': 'hello world',
            'font_color': default_text_config_values['font_color'], 'font_size': default_text_config_values['font_size'],
            'background_color': default_text_config_values['background_color'], 'padding': default_text_config_values['padding'],
            'vertical_alignment': default_text_config_values['vertical_alignment'],
            'horizontal_alignment': default_text_config_values['horizontal_alignment'],
        }
        if custom_config:
            base_config.update(custom_config)

        item = InfoRectangleItem(base_config)
        item.parent_window = parent_window

        if add_to_scene:
            scene = QGraphicsScene()
            scene.setSceneRect(0, 0, 200, 200)
            scene.parent_window = parent_window
            scene.addItem(item)

            view = QGraphicsView(scene)
            view.setMouseTracking(True)
            qtbot.addWidget(view)
            view.show()
            view.resize(300,300)
            item._test_scene_ref = scene
            item._test_view_ref = view

        if selectable:
            item.setFlag(QGraphicsItem.ItemIsSelectable, True)

        return item, scene, parent_window
    return _create_item_with_scene

@pytest.fixture
def item_fixture(create_item_with_scene):
    item, _, _ = create_item_with_scene()
    return item


# --- Test _get_resize_handle_at (Re-verified) ---
@pytest.mark.parametrize("pos, expected_handle, item_width, item_height", [
    (QPointF(1, 1), TOP_LEFT, 100, 50),
    (QPointF(50, 1), TOP, 100, 50),
    (QPointF(99, 1), TOP_RIGHT, 100, 50),
    (QPointF(99, 25), RIGHT, 100, 50),
    (QPointF(99, 49), BOTTOM_RIGHT, 100, 50),
    (QPointF(50, 49), BOTTOM, 100, 50),
    (QPointF(1, 49), BOTTOM_LEFT, 100, 50),
    (QPointF(1, 25), LEFT, 100, 50),
    (QPointF(InfoRectangleItem.RESIZE_MARGIN + 5, InfoRectangleItem.RESIZE_MARGIN + 5), NONE, 100, 50),
    (QPointF(50, 25), NONE, 100, 50),
])
def test_get_all_resize_handles(create_item_with_scene, pos, expected_handle, item_width, item_height):
    item, _, _ = create_item_with_scene(custom_config={'width': item_width, 'height': item_height})
    assert item._get_resize_handle_at(pos) == expected_handle


# Helper to create mock mouse events (remains unchanged from previous state)
def create_mock_mouse_event(event_type, pos, button=Qt.LeftButton, scene_pos=None, modifiers=Qt.NoModifier):
    event = Mock(spec=QGraphicsSceneMouseEvent)
    event.type.return_value = event_type
    event.button.return_value = button
    event.buttons.return_value = button if event_type == QGraphicsSceneMouseEvent.MouseButtonPress else Qt.NoButton
    event.pos.return_value = pos
    event.scenePos.return_value = scene_pos if scene_pos is not None else pos
    event.screenPos.return_value = QPointF()
    event.lastPos.return_value = QPointF()
    event.lastScenePos.return_value = QPointF()
    event.lastScreenPos.return_value = QPointF()
    event.modifiers.return_value = modifiers
    event.accepted = False
    event.accept = Mock(side_effect=lambda: setattr(event, 'accepted', True))
    event.ignore = Mock(side_effect=lambda: setattr(event, 'accepted', False))
    event.isAccepted = Mock(side_effect=lambda: event.accepted)
    return event

# Helper to create mock hover events (remains unchanged)
def create_mock_hover_event(pos, scene_pos=None):
    event = Mock(spec=QGraphicsSceneHoverEvent)
    event.pos.return_value = pos
    event.scenePos.return_value = scene_pos if scene_pos is not None else pos
    event.lastPos.return_value = QPointF()
    event.lastScenePos.return_value = QPointF()
    event.modifiers.return_value = Qt.NoModifier
    return event


# --- Test mousePressEvent (Focus on Resize Logic, Direct Call) ---
@pytest.mark.parametrize("handle_type, press_pos, expected_cursor_shape", [
    (InfoRectangleItem.ResizeHandle.TOP_LEFT, QPointF(1,1), Qt.SizeFDiagCursor),
    (InfoRectangleItem.ResizeHandle.TOP, QPointF(50,1), Qt.SizeVerCursor),
    (InfoRectangleItem.ResizeHandle.TOP_RIGHT, QPointF(99,1), Qt.SizeBDiagCursor),
    (InfoRectangleItem.ResizeHandle.LEFT, QPointF(1,25), Qt.SizeHorCursor),
    (InfoRectangleItem.ResizeHandle.RIGHT, QPointF(99,25), Qt.SizeHorCursor),
    (InfoRectangleItem.ResizeHandle.BOTTOM_LEFT, QPointF(1,49), Qt.SizeBDiagCursor),
    (InfoRectangleItem.ResizeHandle.BOTTOM, QPointF(50,49), Qt.SizeVerCursor),
    (InfoRectangleItem.ResizeHandle.BOTTOM_RIGHT, QPointF(99,49), Qt.SizeFDiagCursor),
])
def test_mouse_press_on_resize_handles(create_item_with_scene, handle_type, press_pos, expected_cursor_shape):
    item, scene, mock_parent_window = create_item_with_scene(custom_config={'width':100, 'height':50})
    mock_parent_window.current_mode = "edit"
    item.setSelected(True)
    item.setFlag(QGraphicsItem.ItemIsMovable, True)
    was_movable_before_press = bool(item.flags() & QGraphicsItem.ItemIsMovable)

    event_scene_pos = item.mapToScene(press_pos)
    event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_pos, scene_pos=event_scene_pos)

    with patch.object(InfoRectangleItem, 'super', create=True) as mock_super:
        mock_super.return_value.mousePressEvent = Mock()
        item.mousePressEvent(event)
        if handle_type != NONE:
             mock_super().mousePressEvent.assert_not_called()

    assert item._is_resizing is True
    assert item._current_resize_handle == handle_type
    assert item._resizing_initial_mouse_pos == event_scene_pos
    assert item._resizing_initial_rect == item.sceneBoundingRect()
    assert not (item.flags() & QGraphicsItem.ItemIsMovable)
    assert item._was_movable == was_movable_before_press
    assert item.cursor().shape() == expected_cursor_shape
    assert event.isAccepted() is True

def test_mouse_press_not_on_handle_emits_selected_and_calls_super(create_item_with_scene):
    item, scene, mock_parent_window = create_item_with_scene(custom_config={'width':100, 'height':50})
    mock_parent_window.current_mode = "edit"
    item.setSelected(False)
    item.setFlag(QGraphicsItem.ItemIsSelectable, True)

    press_pos = item.boundingRect().center()
    event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_pos, scene_pos=item.mapToScene(press_pos))

    mock_slot = Mock()
    item.item_selected.connect(mock_slot)

    with patch.object(QGraphicsItem, 'mousePressEvent', Mock()) as mock_super_press:
        item.mousePressEvent(event)
        mock_super_press.assert_called_once_with(event)

    assert item._is_resizing is False
    mock_slot.assert_called_once_with(item)


# --- Test hoverMoveEvent (Focus on Cursor Setting for Handles, Direct Call) ---
@pytest.mark.parametrize("hover_pos, expected_cursor_shape", [
    (QPointF(1,1), Qt.SizeFDiagCursor), (QPointF(50,1), Qt.SizeVerCursor), (QPointF(99,1), Qt.SizeBDiagCursor),
    (QPointF(1,25), Qt.SizeHorCursor), (QPointF(99,25), Qt.SizeHorCursor),
    (QPointF(1,49), Qt.SizeBDiagCursor), (QPointF(50,49), Qt.SizeVerCursor), (QPointF(99,49), Qt.SizeFDiagCursor),
])
def test_hover_over_resize_handles_sets_cursor(create_item_with_scene, hover_pos, expected_cursor_shape):
    item, scene, mock_parent_window = create_item_with_scene(custom_config={'width':100, 'height':50})
    mock_parent_window.current_mode = "edit"
    item.setSelected(True)
    item._is_resizing = False
    item.setAcceptHoverEvents(True)

    event = create_mock_hover_event(hover_pos, scene_pos=item.mapToScene(hover_pos))

    with patch.object(QGraphicsItem, 'hoverMoveEvent', Mock()) as mock_super_hover:
        item.hoverMoveEvent(event)
    assert item.cursor().shape() == expected_cursor_shape

def test_hover_not_on_handle_movable_item_sets_pointing_hand(create_item_with_scene):
    item, scene, mock_parent_window = create_item_with_scene(custom_config={'width':100, 'height':50})
    mock_parent_window.current_mode = "edit"
    item.setSelected(True)
    item._is_resizing = False
    item.setFlag(QGraphicsItem.ItemIsMovable, True)
    item.setAcceptHoverEvents(True)

    hover_pos = item.boundingRect().center()
    event = create_mock_hover_event(hover_pos, scene_pos=item.mapToScene(hover_pos))
    with patch.object(QGraphicsItem, 'hoverMoveEvent', Mock()) as mock_super_hover:
        item.hoverMoveEvent(event)
    assert item.cursor().shape() == Qt.PointingHandCursor

def test_hover_not_on_handle_not_movable_item_sets_arrow_cursor(create_item_with_scene):
    item, scene, mock_parent_window = create_item_with_scene(custom_config={'width':100, 'height':50})
    mock_parent_window.current_mode = "edit"
    item.setSelected(True)
    item._is_resizing = False
    item.setFlag(QGraphicsItem.ItemIsMovable, False)
    item.setAcceptHoverEvents(True)

    hover_pos = item.boundingRect().center()
    event = create_mock_hover_event(hover_pos, scene_pos=item.mapToScene(hover_pos))
    with patch.object(QGraphicsItem, 'hoverMoveEvent', Mock()) as mock_super_hover:
        item.hoverMoveEvent(event)
    assert item.cursor().shape() == Qt.ArrowCursor

# --- Test mouseMoveEvent (Resizing Logic - Direct Call with Mocks) ---
@pytest.mark.parametrize("handle_type, initial_item_pos_scene, initial_width, initial_height, mouse_delta_scene, expected_final_pos_scene, expected_final_width, expected_final_height", [
    (TOP_LEFT, QPointF(50,50), 100, 50, QPointF(-10,-10), QPointF(40,40), 110, 60),
    (BOTTOM_RIGHT, QPointF(50,50), 100, 50, QPointF(20,15), QPointF(50,50), 120, 65),
    (TOP, QPointF(50,50), 100, 50, QPointF(0,-5), QPointF(50,45), 100, 55),
    (RIGHT, QPointF(50,50), 100, 50, QPointF(12,0), QPointF(50,50), 112, 50),
])
def test_mouse_move_resizing_handles(create_item_with_scene, handle_type, initial_item_pos_scene, initial_width, initial_height, mouse_delta_scene, expected_final_pos_scene, expected_final_width, expected_final_height):
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'width': initial_width, 'height': initial_height,
                       'center_x': initial_item_pos_scene.x() + initial_width/2,
                       'center_y': initial_item_pos_scene.y() + initial_height/2}
    )
    mock_parent_window.current_mode = "edit"
    item.setSelected(True)
    item.setPos(initial_item_pos_scene)

    item._is_resizing = True
    item._current_resize_handle = handle_type
    item._resizing_initial_rect = item.sceneBoundingRect()
    item._resizing_initial_mouse_pos = item.sceneBoundingRect().center()

    event_scene_pos = item._resizing_initial_mouse_pos + mouse_delta_scene
    event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(), scene_pos=event_scene_pos, button=Qt.LeftButton)

    with patch.object(QGraphicsItem, 'mouseMoveEvent', Mock()) as mock_super_move:
        item.mouseMoveEvent(event)
        mock_super_move.assert_not_called()

    assert item.pos() == expected_final_pos_scene
    assert item.boundingRect().width() == pytest.approx(expected_final_width)
    assert item.boundingRect().height() == pytest.approx(expected_final_height)
    assert item.text_item.textWidth() == pytest.approx(expected_final_width)
    assert event.isAccepted() is True

@pytest.mark.parametrize("handle_type, mouse_delta_scene, expected_dim, expected_val, final_pos_attr, final_pos_val", [
    (LEFT, QPointF(90,0), "_w", InfoRectangleItem.MIN_WIDTH, "x", 50 + 100 - InfoRectangleItem.MIN_WIDTH),
    (RIGHT, QPointF(-90,0), "_w", InfoRectangleItem.MIN_WIDTH, "x", 50),
    (TOP, QPointF(0,40), "_h", InfoRectangleItem.MIN_HEIGHT, "y", 50 + 50 - InfoRectangleItem.MIN_HEIGHT),
    (BOTTOM, QPointF(0,-40), "_h", InfoRectangleItem.MIN_HEIGHT, "y", 50),
])
def test_mouse_move_resizing_min_constraints(create_item_with_scene, handle_type, mouse_delta_scene, expected_dim, expected_val, final_pos_attr, final_pos_val):
    initial_pos = QPointF(50,50)
    initial_width = 100
    initial_height = 50
    item, _, _ = create_item_with_scene(custom_config={'width': initial_width, 'height': initial_height, 'center_x': initial_pos.x()+initial_width/2, 'center_y': initial_pos.y()+initial_height/2})
    item.setSelected(True); item.parent_window.current_mode = "edit"; item.setPos(initial_pos)

    item._is_resizing = True
    item._current_resize_handle = handle_type
    item._resizing_initial_rect = item.sceneBoundingRect()
    item._resizing_initial_mouse_pos = item.sceneBoundingRect().center()

    event_scene_pos = item._resizing_initial_mouse_pos + mouse_delta_scene
    event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(), scene_pos=event_scene_pos, button=Qt.LeftButton)

    with patch.object(QGraphicsItem, 'mouseMoveEvent', Mock()):
        item.mouseMoveEvent(event)

    assert getattr(item, expected_dim) == expected_val
    if final_pos_attr == "x":
        assert item.pos().x() == pytest.approx(final_pos_val)
    else:
        assert item.pos().y() == pytest.approx(final_pos_val)


# --- Test mouseReleaseEvent (After Resizing - Direct Call with Mocks) ---
def test_mouse_release_after_resizing(create_item_with_scene):
    item, scene, mock_parent_window = create_item_with_scene()
    mock_parent_window.current_mode = "edit"
    item.setSelected(True)
    item.setFlag(QGraphicsItem.ItemIsMovable, True)

    item.setPos(10,20); item._w = 120; item._h = 60
    item.text_item.setTextWidth(item._w)
    scene.update()
    QApplication.processEvents()

    item._is_resizing = True
    item._current_resize_handle = InfoRectangleItem.ResizeHandle.BOTTOM_RIGHT
    item._was_movable = bool(item.flags() & QGraphicsItem.ItemIsMovable)
    item.setFlag(QGraphicsItem.ItemIsMovable, False)

    event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseRelease, QPointF(), button=Qt.LeftButton)

    mock_slot = Mock()
    item.properties_changed.connect(mock_slot)

    with patch.object(QGraphicsItem, 'mouseReleaseEvent', Mock()) as mock_super_release:
        item.mouseReleaseEvent(event)
        mock_super_release.assert_not_called()

    assert item._is_resizing is False
    assert bool(item.flags() & QGraphicsItem.ItemIsMovable) == item._was_movable
    assert item.config_data['width'] == item._w
    assert item.config_data['height'] == item._h
    expected_center_x = item.pos().x() + item._w / 2
    expected_center_y = item.pos().y() + item._h / 2
    assert item.config_data['center_x'] == expected_center_x
    assert item.config_data['center_y'] == expected_center_y
    mock_slot.assert_called_once_with(item)
    assert event.isAccepted() is True
    assert item.cursor().shape() == (Qt.PointingHandCursor if item._was_movable else Qt.ArrowCursor)

# --- Tests for _get_style_value ---
def test_get_style_value_logic(item_fixture, default_text_config_values):
    item = item_fixture
    default_font_color = default_text_config_values['font_color']

    # 1. Item has _style_config_ref and key is in it
    item._style_config_ref = {"font_color": "#111111"}
    item.config_data = {"font_color": "#222222"}
    assert item._get_style_value("font_color", default_font_color) == "#111111"

    # 2. Item has _style_config_ref, key not in it, but key is in item.config_data
    item._style_config_ref = {"font_size": "12px"}
    item.config_data = {"font_color": "#333333"}
    assert item._get_style_value("font_color", default_font_color) == "#333333"

    # 3. Item has _style_config_ref, key not in it, key not in item.config_data
    item._style_config_ref = {"font_size": "12px"}
    item.config_data = {"font_size": "10px"}
    assert item._get_style_value("font_color", default_font_color) == default_font_color

    # 4. Item _style_config_ref is None, key is in item.config_data
    item._style_config_ref = None
    item.config_data = {"font_color": "#444444"}
    assert item._get_style_value("font_color", default_font_color) == "#444444"

    # 5. Item _style_config_ref is None, key not in item.config_data
    item._style_config_ref = None
    item.config_data = {"font_size": "10px"}
    assert item._get_style_value("font_color", default_font_color) == default_font_color

# --- Tests for _center_text ---
def test_center_text_no_text_item(item_fixture):
    item = item_fixture
    item.text_item = None
    try:
        item._center_text()
    except Exception as e:
        pytest.fail(f"_center_text raised an exception with no text_item: {e}")

def test_center_text_invalid_padding(item_fixture, default_text_config_values):
    item = item_fixture
    item.config_data['padding'] = "invalid_value"
    item.text_item.setPlainText("Test")
    item._center_text()
    assert item.text_item.y() >= 5

@pytest.mark.parametrize("v_align", ["top", "center", "bottom"])
@pytest.mark.parametrize("h_align", ["left", "center", "right"])
def test_center_text_all_alignments(create_item_with_scene, v_align, h_align):
    item, _, _ = create_item_with_scene(custom_config={'height': 100, 'padding': '10px'})
    item.text_item.setPlainText("Line1\nLine2")

    item.vertical_alignment = v_align
    item.horizontal_alignment = h_align
    item._center_text()

    h_align_map = {"left": Qt.AlignLeft, "center": Qt.AlignCenter, "right": Qt.AlignRight}
    assert item.text_item.document().defaultTextOption().alignment() == h_align_map[h_align]

    y_pos = item.text_item.y()
    if v_align == "top":
        assert y_pos == pytest.approx(10)
    elif v_align == "center":
        assert 10 < y_pos < (100 - item.text_item.boundingRect().height() - 10)
    elif v_align == "bottom":
        padding_val = 10
        text_bottom_edge = item.text_item.y() + item.text_item.boundingRect().height()
        expected_bottom_edge = item._h - padding_val
        assert abs(text_bottom_edge - expected_bottom_edge) < 2.0


# --- Test update_text_from_config Error Handling ---
def test_update_text_from_config_invalid_font_size(create_item_with_scene, default_text_config_values):
    item, _, _ = create_item_with_scene()

    item.config_data['font_size'] = "invalid_size"

    mock_defaults = {"defaults": {"info_rectangle_text_display": default_text_config_values.copy()}}
    mock_defaults["defaults"]["info_rectangle_text_display"]['font_size'] = "12px"

    with patch('src.info_rectangle_item.utils.get_default_config', return_value=mock_defaults):
        item.update_text_from_config()
    assert item.text_item.font().pixelSize() == 12

    item.config_data['font_size'] = "another_invalid"
    mock_defaults["defaults"]["info_rectangle_text_display"]['font_size'] = "bad_default_px"
    with patch('src.info_rectangle_item.utils.get_default_config', return_value=mock_defaults):
        item.update_text_from_config()
    assert item.text_item.font().pixelSize() == 14

# --- Test apply_style Method ---
def test_apply_style_with_name(item_fixture):
    item = item_fixture
    style = {"name": "MyStyle", "font_color": "#111111", "font_size": "16px"}
    item.apply_style(style)
    assert item.config_data['text_style_ref'] == "MyStyle"
    assert item._style_config_ref == style
    assert item.config_data['font_color'] == "#111111"
    assert item.text_item.defaultTextColor() == QColor("#111111")
    assert item.text_item.font().pixelSize() == 16

def test_apply_style_none_removes_ref(item_fixture, default_text_config_values):
    item = item_fixture
    style = {"name": "MyStyle", "font_color": "#123456", "font_size": "22px"}
    item.apply_style(style)
    assert item.config_data.get('text_style_ref') == "MyStyle"

    item.config_data['font_color'] = "#ABCDEF"
    item.apply_style(None)

    assert 'text_style_ref' not in item.config_data
    assert item._style_config_ref is None
    assert item.text_item.defaultTextColor() == QColor("#ABCDEF")
    expected_default_size = int(default_text_config_values['font_size'].replace('px',''))
    assert item.text_item.font().pixelSize() == expected_default_size


def test_apply_style_key_precedence(item_fixture, default_text_config_values):
    item = item_fixture
    item.config_data['text'] = "Original Text"
    item.config_data['font_size'] = "10px"

    style = {"font_size": "20px", "text": "Styled Text"}
    item.apply_style(style)

    assert item.config_data['text'] == "Styled Text"
    assert item.config_data['font_size'] == "20px"
    assert item.text_item.toPlainText() == "Styled Text"
    assert item.text_item.font().pixelSize() == 20

def test_markdown_rendering_in_scene(item_fixture):
    item = item_fixture
    item.set_display_text("**Bold** text")
    html_content = item.text_item.document().toHtml()
    assert "font-weight" in html_content
    assert "Bold text" == item.text_item.document().toPlainText()

def test_apply_style_emits_properties_changed(item_fixture):
    item = item_fixture
    mock_slot = Mock()
    item.properties_changed.connect(mock_slot)
    item.apply_style({"font_color": "#222222"})
    mock_slot.assert_called_once_with(item)

# --- Test itemChange for Non-Resizing Moves ---
def test_item_change_position_not_resizing(item_fixture):
    item = item_fixture
    item._is_resizing = False
    item.setFlag(QGraphicsItem.ItemIsMovable, True)

    mock_slot = Mock()
    item.item_moved.connect(mock_slot)

    initial_cx = item.config_data['center_x']
    initial_cy = item.config_data['center_y']

    new_pos = QPointF(item.pos().x() + 10, item.pos().y() + 10)

    item.itemChange(QGraphicsItem.ItemPositionHasChanged, new_pos)

    mock_slot.assert_not_called()
    expected_cx = new_pos.x() + item._w / 2
    expected_cy = new_pos.y() + item._h / 2
    assert item.config_data['center_x'] == expected_cx
    assert item.config_data['center_y'] == expected_cy
    assert item.config_data['center_x'] != initial_cx
    assert item.config_data['center_y'] != initial_cy


def test_item_moved_emitted_on_mouse_release(create_item_with_scene):
    item, _, _ = create_item_with_scene(selectable=True)
    item._is_resizing = False
    item.setFlag(QGraphicsItem.ItemIsMovable, True)

    item.itemChange(QGraphicsItem.ItemPositionHasChanged, QPointF(item.pos().x() + 5, item.pos().y() + 5))

    release_event = create_mock_mouse_event(
        QGraphicsSceneMouseEvent.GraphicsSceneMouseRelease,
        QPointF(),
        button=Qt.LeftButton,
    )

    mock_slot = Mock()
    item.item_moved.connect(mock_slot)

    with patch.object(QGraphicsItem, "mouseReleaseEvent", Mock()) as mock_super:
        item.mouseReleaseEvent(release_event)
        mock_super.assert_called_once()

    mock_slot.assert_called_once_with(item)
