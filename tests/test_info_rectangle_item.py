import pytest
import math # Added for calculations in resize tests
from PyQt5.QtCore import QPointF, Qt, QRectF, QPoint
from PyQt5.QtGui import QColor, QFont, QTextOption, QCursor
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsSceneMouseEvent, QGraphicsSceneHoverEvent, QGraphicsItem
from pytestqt.qt_compat import qt_api
from unittest.mock import Mock, patch

from src.info_area_item import InfoAreaItem
from src import utils # For default config

# QApplication instance is typically managed by pytest-qt's qapp fixture.

# Constants for resize handles
TOP_LEFT = InfoAreaItem.ResizeHandle.TOP_LEFT
TOP = InfoAreaItem.ResizeHandle.TOP
TOP_RIGHT = InfoAreaItem.ResizeHandle.TOP_RIGHT
LEFT = InfoAreaItem.ResizeHandle.LEFT
RIGHT = InfoAreaItem.ResizeHandle.RIGHT
BOTTOM_LEFT = InfoAreaItem.ResizeHandle.BOTTOM_LEFT
BOTTOM = InfoAreaItem.ResizeHandle.BOTTOM
BOTTOM_RIGHT = InfoAreaItem.ResizeHandle.BOTTOM_RIGHT
NONE = InfoAreaItem.ResizeHandle.NONE


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
            'font_color': default_text_config_values['font_color'],
            'font_size': default_text_config_values['font_size'],
            'background_color': default_text_config_values['background_color'],
            'padding': default_text_config_values['padding'],
            'vertical_alignment': default_text_config_values['vertical_alignment'],
            'horizontal_alignment': default_text_config_values['horizontal_alignment'],
            'shape': 'rectangle',
        }
        if custom_config:
            base_config.update(custom_config)

        item = InfoAreaItem(base_config)
        item.parent_window = parent_window

        scene = None
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
    (QPointF(InfoAreaItem.RESIZE_MARGIN + 5, InfoAreaItem.RESIZE_MARGIN + 5), NONE, 100, 50),
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
    (InfoAreaItem.ResizeHandle.TOP_LEFT, QPointF(1,1), Qt.SizeFDiagCursor),
    (InfoAreaItem.ResizeHandle.TOP, QPointF(50,1), Qt.SizeVerCursor),
    (InfoAreaItem.ResizeHandle.TOP_RIGHT, QPointF(99,1), Qt.SizeBDiagCursor),
    (InfoAreaItem.ResizeHandle.LEFT, QPointF(1,25), Qt.SizeHorCursor),
    (InfoAreaItem.ResizeHandle.RIGHT, QPointF(99,25), Qt.SizeHorCursor),
    (InfoAreaItem.ResizeHandle.BOTTOM_LEFT, QPointF(1,49), Qt.SizeBDiagCursor),
    (InfoAreaItem.ResizeHandle.BOTTOM, QPointF(50,49), Qt.SizeVerCursor),
    (InfoAreaItem.ResizeHandle.BOTTOM_RIGHT, QPointF(99,49), Qt.SizeFDiagCursor),
])
def test_mouse_press_on_resize_handles(create_item_with_scene, handle_type, press_pos, expected_cursor_shape):
    item, scene, mock_parent_window = create_item_with_scene(custom_config={'width':100, 'height':50})
    mock_parent_window.current_mode = "edit"
    item.setSelected(True)
    item.setFlag(QGraphicsItem.ItemIsMovable, True)
    was_movable_before_press = bool(item.flags() & QGraphicsItem.ItemIsMovable)

    event_scene_pos = item.mapToScene(press_pos)
    event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_pos, scene_pos=event_scene_pos)

    with patch.object(InfoAreaItem, 'super', create=True) as mock_super:
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
    assert item._w == pytest.approx(expected_final_width)
    assert item._h == pytest.approx(expected_final_height)
    assert item.text_item.textWidth() == pytest.approx(expected_final_width)
    assert event.isAccepted() is True

@pytest.mark.parametrize("handle_type, mouse_delta_scene, expected_dim, expected_val, final_pos_attr, final_pos_val", [
    (LEFT, QPointF(90,0), "_w", InfoAreaItem.MIN_WIDTH, "x", 50 + 100 - InfoAreaItem.MIN_WIDTH),
    (RIGHT, QPointF(-90,0), "_w", InfoAreaItem.MIN_WIDTH, "x", 50),
    (TOP, QPointF(0,40), "_h", InfoAreaItem.MIN_HEIGHT, "y", 50 + 50 - InfoAreaItem.MIN_HEIGHT),
    (BOTTOM, QPointF(0,-40), "_h", InfoAreaItem.MIN_HEIGHT, "y", 50),
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
    item._current_resize_handle = InfoAreaItem.ResizeHandle.BOTTOM_RIGHT
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

    with patch('src.info_area_item.utils.get_default_config', return_value=mock_defaults):
        item.update_text_from_config()
    assert item.text_item.font().pixelSize() == 12

    item.config_data['font_size'] = "another_invalid"
    mock_defaults["defaults"]["info_rectangle_text_display"]['font_size'] = "bad_default_px"
    with patch('src.info_area_item.utils.get_default_config', return_value=mock_defaults):
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

def test_update_appearance_view_mode_visibility(create_item_with_scene):
    item_hover, _, _ = create_item_with_scene(custom_config={'show_on_hover': True})
    item_hover.update_appearance(False, True)
    assert not item_hover.text_item.isVisible()

    item_always, _, _ = create_item_with_scene(custom_config={'show_on_hover': False})
    item_always.update_appearance(False, True)
    assert item_always.text_item.isVisible()


def test_paint_ellipse_calls_correct_method(create_item_with_scene):
    item, _, _ = create_item_with_scene(custom_config={'shape': 'ellipse'}, add_to_scene=False)
    painter = Mock()
    item.paint(painter, None)
    painter.drawEllipse.assert_called_once()
    painter.drawRect.assert_not_called()


# --- Tests for Angle Functionality ---

def test_info_area_item_initialization_with_angle(create_item_with_scene):
    """Test item initializes with a specific angle from config."""
    item, _, _ = create_item_with_scene(custom_config={'angle': 45.0})
    assert item.angle == pytest.approx(45.0)
    assert item.rotation() == pytest.approx(45.0)
    assert item.config_data['angle'] == pytest.approx(45.0)

def test_info_area_item_initialization_default_angle(create_item_with_scene):
    """Test item initializes with a default angle (0.0) if not in config."""
    item, _, _ = create_item_with_scene(custom_config={}) # No angle specified
    assert item.angle == pytest.approx(0.0)
    assert item.rotation() == pytest.approx(0.0)
    assert item.config_data.get('angle', 0.0) == pytest.approx(0.0)

def test_info_area_item_set_angle_updates_rotation(create_item_with_scene):
    """Test setting angle in config_data and calling update_geometry_from_config applies rotation."""
    item, _, _ = create_item_with_scene()

    # Initial state (default angle)
    assert item.angle == pytest.approx(0.0)
    assert item.rotation() == pytest.approx(0.0)

    item.config_data['angle'] = 30.0
    item.update_geometry_from_config()

    assert item.angle == pytest.approx(30.0)
    assert item.rotation() == pytest.approx(30.0)
    assert item.config_data['angle'] == pytest.approx(30.0)

def test_info_area_item_transform_origin_is_center(create_item_with_scene):
    """Test transformOriginPoint is at the center of the item and updates with size."""
    initial_width = 100
    initial_height = 50
    item, _, _ = create_item_with_scene(custom_config={'width': initial_width, 'height': initial_height})

    assert item.transformOriginPoint().x() == pytest.approx(initial_width / 2)
    assert item.transformOriginPoint().y() == pytest.approx(initial_height / 2)

    # Change width and height and update
    new_width = 120
    new_height = 60
    item.config_data['width'] = new_width
    item.config_data['height'] = new_height
    item.update_geometry_from_config()

    assert item.transformOriginPoint().x() == pytest.approx(new_width / 2)
    assert item.transformOriginPoint().y() == pytest.approx(new_height / 2)


# --- Tests for Resizing Rotated Item ---

def test_resize_rotated_right_handle(create_item_with_scene, qtbot):
    angle_deg = 30.0
    initial_width, initial_height = 100, 50
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 100, 'center_y': 100},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_pos = item.pos()

    # Press on the right handle
    press_local_pos = QPointF(item._w, item._h / 2) # Approx middle of right edge
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.RIGHT # Manually set for test clarity
    item.mousePressEvent(press_event)

    # Simulate mouse move: drag by delta_val_local_x along item's X-axis
    delta_val_local_x = 20
    angle_rad = math.radians(angle_deg)
    item_x_axis_scene = QPointF(math.cos(angle_rad), math.sin(angle_rad))
    mouse_move_delta_scene = item_x_axis_scene * delta_val_local_x
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(initial_width + delta_val_local_x)
    assert item._h == pytest.approx(initial_height)
    # For right handle drag, pos_change_x_local and pos_change_y_local are 0, so item.pos() should be initial_pos.
    assert item.pos().x() == pytest.approx(initial_pos.x())
    assert item.pos().y() == pytest.approx(initial_pos.y())
    assert item.rotation() == pytest.approx(angle_deg)

def test_resize_rotated_left_handle(create_item_with_scene, qtbot):
    angle_deg = 45.0
    initial_width, initial_height = 100, 50
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 150, 'center_y': 150},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_item_pos = item.pos()

    # Press on the left handle
    press_local_pos = QPointF(0, item._h / 2)
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.LEFT
    item.mousePressEvent(press_event)

    # Simulate mouse move: drag by delta_val_local_x along item's negative X-axis (increasing width to the left)
    delta_val_local_x = -20 # Mouse moves left relative to item's X-axis, so delta_local_x in formula is positive
                            # mouse_move_event.scenePos() - _resize_start_mouse_scene_pos projected on item_x_axis gives delta_local_x
                            # If we want to increase width by 20 to the left, mouse must move by -20 along item's X axis.
                            # The delta_local_x in the item's code will be positive 20 due to "new_w -= delta_local_x" logic.
                            # So, the mouse movement needs to result in a positive delta_local_x in the item's calculation.
                            # This means the mouse_delta_scene projected on item_x_axis_scene should be +20 if we use the formula's delta_local_x
                            # Let's use a positive "increase_amount" and adjust the scene delta.
    increase_amount = 20
    angle_rad = math.radians(angle_deg)
    item_x_axis_scene = QPointF(math.cos(angle_rad), math.sin(angle_rad))
    # Mouse moves opposite to item's X-axis to increase width to the left
    mouse_move_delta_scene = item_x_axis_scene * (-increase_amount)
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(initial_width + increase_amount)
    assert item._h == pytest.approx(initial_height)

    # Expected position change: left edge moved left by increase_amount
    expected_final_pos_x = initial_item_pos.x() - item_x_axis_scene.x() * increase_amount
    expected_final_pos_y = initial_item_pos.y() - item_x_axis_scene.y() * increase_amount

    assert item.pos().x() == pytest.approx(expected_final_pos_x)
    assert item.pos().y() == pytest.approx(expected_final_pos_y)
    assert item.rotation() == pytest.approx(angle_deg)

def test_resize_rotated_top_handle(create_item_with_scene, qtbot):
    angle_deg = 20.0
    initial_width, initial_height = 100, 50
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 120, 'center_y': 80},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_item_pos = item.pos()

    press_local_pos = QPointF(item._w / 2, 0)
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.TOP
    item.mousePressEvent(press_event)

    increase_amount = 15 # How much we want to increase height by moving mouse "up" relative to item
    angle_rad = math.radians(angle_deg)
    item_y_axis_scene = QPointF(-math.sin(angle_rad), math.cos(angle_rad))

    mouse_move_delta_scene = item_y_axis_scene * (-increase_amount) # Mouse moves opposite to item's Y-axis
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(initial_width)
    assert item._h == pytest.approx(initial_height + increase_amount)

    # Expected position change: top edge moved up by increase_amount
    expected_final_pos_x = initial_item_pos.x() - item_y_axis_scene.x() * increase_amount
    expected_final_pos_y = initial_item_pos.y() - item_y_axis_scene.y() * increase_amount

    assert item.pos().x() == pytest.approx(expected_final_pos_x)
    assert item.pos().y() == pytest.approx(expected_final_pos_y)
    assert item.rotation() == pytest.approx(angle_deg)


def test_resize_rotated_bottom_handle(create_item_with_scene, qtbot):
    angle_deg = 60.0
    initial_width, initial_height = 100, 50
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 100, 'center_y': 100},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_pos = item.pos()

    press_local_pos = QPointF(item._w / 2, item._h)
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.BOTTOM
    item.mousePressEvent(press_event)

    delta_val_local_y = 25
    angle_rad = math.radians(angle_deg)
    item_y_axis_scene = QPointF(-math.sin(angle_rad), math.cos(angle_rad))
    mouse_move_delta_scene = item_y_axis_scene * delta_val_local_y
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(initial_width)
    assert item._h == pytest.approx(initial_height + delta_val_local_y)
    # For bottom handle drag, pos_change_x_local and pos_change_y_local are 0.
    assert item.pos().x() == pytest.approx(initial_pos.x())
    assert item.pos().y() == pytest.approx(initial_pos.y())
    assert item.rotation() == pytest.approx(angle_deg)


def test_resize_rotated_with_min_height_constraint(create_item_with_scene, qtbot):
    angle_deg = 30.0
    initial_width, initial_height = 50, 50 # Start near MIN_HEIGHT
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 100, 'center_y': 100},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_item_pos = item.pos()

    press_local_pos = QPointF(item._w / 2, 0) # Top handle
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.TOP
    item.mousePressEvent(press_event)

    decrease_amount_attempt = 40 # Try to decrease height by 40 (50 - 40 = 10, which is < MIN_HEIGHT)

    angle_rad = math.radians(angle_deg)
    item_y_axis_scene = QPointF(-math.sin(angle_rad), math.cos(angle_rad))

    mouse_move_delta_scene = item_y_axis_scene * decrease_amount_attempt # Mouse moves towards item's positive Y-axis
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(initial_width)
    assert item._h == pytest.approx(InfoAreaItem.MIN_HEIGHT)

    # The amount the item's origin (top-left point) shifts in its local Y direction.
    pos_change_y_local_effective = initial_height - InfoAreaItem.MIN_HEIGHT

    expected_final_pos_x = initial_item_pos.x() + item_y_axis_scene.x() * pos_change_y_local_effective
    expected_final_pos_y = initial_item_pos.y() + item_y_axis_scene.y() * pos_change_y_local_effective

    assert item.pos().x() == pytest.approx(expected_final_pos_x)
    assert item.pos().y() == pytest.approx(expected_final_pos_y)
    assert item.rotation() == pytest.approx(angle_deg)


def test_resize_rotated_bottom_right_handle(create_item_with_scene, qtbot):
    angle_deg = 45.0
    initial_width, initial_height = 100, 50
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 100, 'center_y': 100},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_pos = item.pos() # Top-left of the item's bounding box in scene coords

    # Press on the bottom-right handle
    press_local_pos = QPointF(item._w, item._h)
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.BOTTOM_RIGHT
    item.mousePressEvent(press_event)

    # Simulate mouse move: drag by (delta_x, delta_y) in item's local rotated coordinates
    delta_local_x_val = 20
    delta_local_y_val = 15

    angle_rad = math.radians(angle_deg)
    item_x_axis_scene = QPointF(math.cos(angle_rad), math.sin(angle_rad))
    item_y_axis_scene = QPointF(-math.sin(angle_rad), math.cos(angle_rad)) # Item's Y in scene

    mouse_move_delta_scene = (item_x_axis_scene * delta_local_x_val) + (item_y_axis_scene * delta_local_y_val)
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(initial_width + delta_local_x_val)
    assert item._h == pytest.approx(initial_height + delta_local_y_val)
    # For bottom-right handle, pos_change_x_local and pos_change_y_local are 0. Item's (0,0) point should be stable.
    assert item.pos().x() == pytest.approx(initial_pos.x())
    assert item.pos().y() == pytest.approx(initial_pos.y())
    assert item.rotation() == pytest.approx(angle_deg)


def test_resize_rotated_top_left_handle(create_item_with_scene, qtbot):
    angle_deg = 45.0
    initial_width, initial_height = 100, 50
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 150, 'center_y': 150},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_item_pos = item.pos()

    # Press on the top-left handle
    press_local_pos = QPointF(0, 0)
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.TOP_LEFT
    item.mousePressEvent(press_event)

    # Simulate mouse move: increase width by 'increase_w' and height by 'increase_h' by moving mouse towards top-left
    increase_w = 20
    increase_h = 10

    angle_rad = math.radians(angle_deg)
    item_x_axis_scene = QPointF(math.cos(angle_rad), math.sin(angle_rad))
    item_y_axis_scene = QPointF(-math.sin(angle_rad), math.cos(angle_rad))

    # Mouse moves opposite to item's X-axis and Y-axis
    mouse_move_delta_scene = (item_x_axis_scene * (-increase_w)) + (item_y_axis_scene * (-increase_h))
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(initial_width + increase_w)
    assert item._h == pytest.approx(initial_height + increase_h)

    # Expected position change: both edges moved outward by increase_w/increase_h
    expected_pos_change_scene_x = item_x_axis_scene * (-increase_w)
    expected_pos_change_scene_y = item_y_axis_scene * (-increase_h)
    total_expected_scene_shift = expected_pos_change_scene_x + expected_pos_change_scene_y

    expected_final_pos_x = initial_item_pos.x() + total_expected_scene_shift.x()
    expected_final_pos_y = initial_item_pos.y() + total_expected_scene_shift.y()

    assert item.pos().x() == pytest.approx(expected_final_pos_x)
    assert item.pos().y() == pytest.approx(expected_final_pos_y)
    assert item.rotation() == pytest.approx(angle_deg)


def test_resize_rotated_with_min_width_constraint(create_item_with_scene, qtbot):
    angle_deg = 30.0
    initial_width, initial_height = 50, 50 # Start near MIN_WIDTH
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'angle': angle_deg, 'width': initial_width, 'height': initial_height, 'center_x': 100, 'center_y': 100},
        add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    initial_item_pos = item.pos()

    # Press on the left handle
    press_local_pos = QPointF(0, item._h / 2)
    press_scene_pos = item.mapToScene(press_local_pos)
    press_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMousePress, press_local_pos, scene_pos=press_scene_pos)
    item._current_resize_handle = InfoAreaItem.ResizeHandle.LEFT
    item.mousePressEvent(press_event)

    # Try to decrease width by 40 (50 - 40 = 10, which is < MIN_WIDTH)
    decrease_amount_attempt = 40
    # This means mouse moves towards item's positive X-axis by 'decrease_amount_attempt'

    angle_rad = math.radians(angle_deg)
    item_x_axis_scene = QPointF(math.cos(angle_rad), math.sin(angle_rad))

    mouse_move_delta_scene = item_x_axis_scene * decrease_amount_attempt
    move_to_scene_pos = item._resize_start_mouse_scene_pos + mouse_move_delta_scene

    move_event = create_mock_mouse_event(QGraphicsSceneMouseEvent.GraphicsSceneMouseMove, QPointF(0,0), scene_pos=move_to_scene_pos, button=Qt.LeftButton)
    item.mouseMoveEvent(move_event)

    assert item._w == pytest.approx(InfoAreaItem.MIN_WIDTH)
    assert item._h == pytest.approx(initial_height)

    # Calculate expected position:
    # new_w becomes MIN_WIDTH. Original was initial_width.
    # delta_local_x from mouse was 'decrease_amount_attempt'.
    # actual_dw = MIN_WIDTH - initial_width  (e.g. 20 - 50 = -30)
    # constrained_dw = MIN_WIDTH - initial_width (same)
    # dw_diff = constrained_dw - actual_dw (where actual_dw was based on delta_local_x before constraint)
    # The pos_change_x_local is adjusted by dw_diff.
    # Original delta_local_x (from mouse) is decrease_amount_attempt = 40.
    # new_w (before constraint) = initial_width - decrease_amount_attempt = 50 - 40 = 10.
    # pos_change_x_local (before constraint) = decrease_amount_attempt = 40.
    # After constraint: new_w = MIN_WIDTH (20).
    # actual_dw_unconstrained = 10 - 50 = -40
    # constrained_dw = MIN_WIDTH - initial_width = 20 - 50 = -30
    # dw_diff = constrained_dw - actual_dw_unconstrained = -30 - (-40) = 10
    # pos_change_x_local (after constraint) = pos_change_x_local_before_constraint + dw_diff = 40 + 10 = 50. No, this is wrong.
    # Let's re-evaluate from item code:
    # pos_change_x_local = delta_local_x (which is decrease_amount_attempt = 40 here)
    # actual_dw = new_w (10) - self._resize_start_item_width (50) = -40
    # new_w (10) < self.MIN_WIDTH (20) is true.
    # constrained_dw = self.MIN_WIDTH (20) - self._resize_start_item_width (50) = -30
    # dw_diff = constrained_dw (-30) - actual_dw (-40) = 10
    # pos_change_x_local += dw_diff  => pos_change_x_local = 40 + 10 = 50.
    # This means the item's origin effectively moved by 50 units along its local X-axis.

    expected_pos_change_local = initial_width - InfoAreaItem.MIN_WIDTH # How much the left edge actually moved in local units
                                                                       # This is the amount the item's origin had to shift
                                                                       # If width changed from 50 to 20, left edge moved by 30.
                                                                       # So pos_change_x_local should be 30.

    # The actual shift of the item's origin (top-left point)
    # is by `pos_change_x_local` along `item_x_axis_scene`.
    # `pos_change_x_local` is `delta_local_x` (from mouse) + `dw_diff` (from constraint).
    # `delta_local_x` (from mouse) = `decrease_amount_attempt` = 40.
    # `dw_diff` = 10.
    # So, effective `pos_change_x_local` for position update = 40 + 10 = 50. This still feels high.
    # Let's trace: Initial left edge at 0. Target left edge at 40. Width becomes 10. Origin moves by 40.
    # Constraint: Width becomes 20. Left edge was at 0. Width is 50. Target left edge at 30 (50-20). Origin moves by 30.
    # So pos_change_x_local should be 30.
    # delta_local_x = 40. new_w = 10. pos_change_x_local = 40.
    # actual_dw = 10 - 50 = -40.
    # new_w < MIN_WIDTH: 10 < 20.
    # constrained_dw = 20 - 50 = -30.
    # dw_diff = -30 - (-40) = 10.
    # pos_change_x_local (40) += dw_diff (10) => pos_change_x_local = 50.
    # This means self.setPos(self._resize_start_item_pos + item_x_axis_scene * 50). This is a large shift.

    # The amount the item's origin (top-left point) shifts in its local X direction.
    # If width changes from W_start to W_end, and it's a left-handle drag,
    # the item's origin shifts by (W_start - W_end) in its local X.
    pos_change_x_local_effective = initial_width - InfoAreaItem.MIN_WIDTH

    expected_final_pos_x = initial_item_pos.x() + item_x_axis_scene.x() * pos_change_x_local_effective
    expected_final_pos_y = initial_item_pos.y() + item_x_axis_scene.y() * pos_change_x_local_effective

    assert item.pos().x() == pytest.approx(expected_final_pos_x)
    assert item.pos().y() == pytest.approx(expected_final_pos_y)
    assert item.rotation() == pytest.approx(angle_deg)


def test_rotation_handle_position(create_item_with_scene):
    item, _, _ = create_item_with_scene()
    rect = item._get_rotation_handle_rect()
    assert rect.center().x() == pytest.approx(item._w + InfoAreaItem.ROTATE_HANDLE_OFFSET)
    assert rect.center().y() == pytest.approx(-InfoAreaItem.ROTATE_HANDLE_OFFSET)


def test_rotate_via_handle_updates_angle(create_item_with_scene, qtbot):
    item, scene, mock_parent_window = create_item_with_scene(
        custom_config={'center_x': 100, 'center_y': 100}, add_to_scene=True
    )
    item.setSelected(True)
    mock_parent_window.current_mode = "edit"
    handle_center_local = item._get_rotation_handle_rect().center()
    press_event = create_mock_mouse_event(
        QGraphicsSceneMouseEvent.GraphicsSceneMousePress,
        handle_center_local,
        scene_pos=item.mapToScene(handle_center_local)
    )
    item.mousePressEvent(press_event)

    center_local = QPointF(item._w / 2, item._h / 2)
    vec = handle_center_local - center_local
    radius = math.hypot(vec.x(), vec.y())
    start_ang = math.atan2(vec.y(), vec.x())
    target_ang = start_ang + math.radians(90)
    target_local = QPointF(center_local.x() + radius * math.cos(target_ang),
                           center_local.y() + radius * math.sin(target_ang))
    move_event = create_mock_mouse_event(
        QGraphicsSceneMouseEvent.GraphicsSceneMouseMove,
        QPointF(0, 0),
        scene_pos=item.mapToScene(target_local),
        button=Qt.LeftButton
    )
    item.mouseMoveEvent(move_event)

    release_event = create_mock_mouse_event(
        QGraphicsSceneMouseEvent.GraphicsSceneMouseRelease,
        target_local,
        scene_pos=item.mapToScene(target_local),
        button=Qt.LeftButton
    )
    item.mouseReleaseEvent(release_event)

    assert item.rotation() == pytest.approx(90.0)
    assert item.config_data['angle'] == pytest.approx(90.0)


def test_rotation_handle_in_shape(create_item_with_scene):
    item, _, _ = create_item_with_scene()
    handle_center = item._get_rotation_handle_rect().center()
    assert item.shape().contains(handle_center)


def test_rotation_handle_in_bounding_rect(create_item_with_scene):
    item, _, _ = create_item_with_scene()
    handle_center = item._get_rotation_handle_rect().center()
    assert item.boundingRect().contains(handle_center)
