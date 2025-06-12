import pytest
from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtGui import QColor, QFont, QTextOption
from PyQt5.QtWidgets import QGraphicsScene

from src.info_rectangle_item import InfoRectangleItem
from src import utils # For default config

@pytest.fixture
def default_text_config():
    return utils.get_default_config()["defaults"]["info_rectangle_text_display"]

@pytest.fixture
def create_item_with_scene(default_text_config, qtbot): # qtbot can manage scene lifetime
    def _create_item_with_scene(custom_config=None):
        base_config = {
            'id': 'rect1',
            'width': 100,
            'height': 80,
            'center_x': 50,
            'center_y': 40,
            'text': 'hello world',
            'font_color': default_text_config['font_color'],
            'font_size': default_text_config['font_size'],
            'background_color': default_text_config['background_color'],
            'padding': default_text_config['padding'],
            'vertical_alignment': default_text_config['vertical_alignment'],
            'horizontal_alignment': default_text_config['horizontal_alignment'],
            'font_style': default_text_config['font_style'],
        }
        if custom_config:
            base_config.update(custom_config)

        # Scene managed by test scope or qtbot if possible. Here, let's ensure it's returned.
        scene = QGraphicsScene()
        item = InfoRectangleItem(base_config)
        scene.addItem(item)
        # Keep the scene alive by making it an attribute of the item for test duration
        # This is a common workaround for tests to prevent premature garbage collection.
        item._test_scene_ref = scene
        return item
    return _create_item_with_scene

# Old fixture name, updated to use the new one that returns item with scene ref
@pytest.fixture
def create_item(create_item_with_scene): # create_item_with_scene now just returns item
    def _create_item_wrapper(custom_config=None):
        item = create_item_with_scene(custom_config)
        return item
    return _create_item_wrapper


def test_update_geometry_from_config(qtbot, create_item):
    item = create_item()
    item.config_data['width'] = 150
    item.config_data['height'] = 60 # Keep height reasonable for text
    item.config_data['center_x'] = 80
    item.config_data['center_y'] = 40
    item.update_geometry_from_config()
    assert item.boundingRect().width() == 150
    assert item.pos() == QPointF(80 - 150/2, 40 - 60/2)


def test_set_display_text(qtbot, create_item):
    item = create_item()
    item.set_display_text('updated')
    assert item.text_item.toPlainText() == 'updated'
    assert item.config_data['text'] == 'updated' # Check config_data update


def test_update_text_from_config(qtbot, create_item):
    item = create_item()
    item.config_data['text'] = 'again'
    item.update_text_from_config() # This should also update formatting options
    assert item.text_item.toPlainText() == 'again'


def test_update_appearance_selected(qtbot, create_item):
    item = create_item()
    item.update_appearance(is_selected=True, is_view_mode=False)
    assert item._pen.color() == QColor(255, 0, 0, 200)


def test_get_resize_handle_at(qtbot, create_item):
    item = create_item()
    pos = QPointF(1, 1)
    assert item._get_resize_handle_at(pos) == InfoRectangleItem.ResizeHandle.TOP_LEFT

def test_item_change_updates_config(qtbot, create_item):
    item = create_item()
    # scene = QGraphicsScene() # Item already added to scene in fixture
    # scene.addItem(item)
    item.setPos(10, 15)
    assert item.config_data['center_x'] == 10 + item.boundingRect().width() / 2
    assert item.config_data['center_y'] == 15 + item.boundingRect().height() / 2

def test_update_appearance_view_mode(qtbot, create_item):
    item = create_item()
    item.update_appearance(is_view_mode=True)
    assert not item.text_item.isVisible()
    assert item._pen.color() == QColor(0, 0, 0, 0)

def test_center_text_respects_padding(qtbot, create_item):
    item = create_item({'padding': '20px'}) # Pass padding in custom_config
    item.set_display_text('multi\nline text') # This calls _center_text
    # item._center_text() # Call explicitly if set_display_text doesn't or for clarity
    assert item.text_item.y() >= 20

def test_item_moved_signal_emitted(qtbot, create_item):
    item = create_item()
    # scene = QGraphicsScene() # Item already added to scene in fixture
    # scene.addItem(item)
    moved = []
    item.item_moved.connect(lambda obj: moved.append(True))
    item.setPos(5, 5)
    assert moved and item.config_data['center_x'] == 5 + item.boundingRect().width() / 2

# --- New Tests for Rich Text Formatting ---

def test_default_values_applied(qtbot, default_text_config):
    # Create item with minimal config, let it pick up defaults
    minimal_config = {
        'id': 'rect_minimal',
        'width': 100, 'height': 50, 'center_x': 50, 'center_y': 25, 'text': 'test'
    }
    item = InfoRectangleItem(minimal_config)
    # scene = QGraphicsScene(); scene.addItem(item) # Add to scene if needed for full init

    assert item.vertical_alignment == default_text_config['vertical_alignment']
    assert item.horizontal_alignment == default_text_config['horizontal_alignment']
    assert item.font_style == default_text_config['font_style']
    assert item.text_item.font().pointSize() == int(default_text_config['font_size'].replace('px',''))
    assert item.text_item.defaultTextColor() == QColor(default_text_config['font_color'])

    # Check text_item properties (after update_text_from_config which is called in __init__)
    expected_h_align = Qt.AlignLeft # Default
    if default_text_config['horizontal_alignment'] == "center": expected_h_align = Qt.AlignCenter
    elif default_text_config['horizontal_alignment'] == "right": expected_h_align = Qt.AlignRight
    assert item.text_item.document().defaultTextOption().alignment() == expected_h_align

    assert not item.text_item.font().bold() # Default is normal
    assert not item.text_item.font().italic() # Default is normal


def test_apply_vertical_alignment(qtbot, create_item):
    item = create_item({'height': 100, 'padding': '10px', 'font_size': '10px'})
    item.text_item.setPlainText("Line1\nLine2") # Ensure some text height

    # Approximate text height (very rough, use fixed value for reliable test if needed)
    # For more precise testing, mock QFontMetrics or use a known font and text.
    # Let's assume text_height is roughly 2 lines * 10px font = 20-25px
    # However, _center_text calculates this, so we check resulting y.

    # Top alignment
    item.config_data['vertical_alignment'] = 'top'
    item.vertical_alignment = 'top'
    item._center_text()
    assert item.text_item.y() == 10 # Should be at top padding

    # Center alignment
    item.config_data['vertical_alignment'] = 'center'
    item.vertical_alignment = 'center'
    item._center_text()
    # y should be (item_height - text_block_height)/2, but >= padding_top
    # (100 - text_height)/2. If text_height is ~25, (100-25)/2 = 37.5
    assert item.text_item.y() > 10
    # More specific check would require knowing text_height accurately

    # Bottom alignment
    item.config_data['vertical_alignment'] = 'bottom'
    item.vertical_alignment = 'bottom'
    item._center_text()
    # y should be item_height - text_block_height - padding_bottom
    # 100 - text_height - 10. If text_height ~25, 100 - 25 - 10 = 65
    # This needs QFontMetrics to be accurate, so we check it's greater than center pos
    assert item.text_item.y() > 30 # Greater than a typical centered position


def test_apply_horizontal_alignment(qtbot, create_item):
    item = create_item()

    item.config_data['horizontal_alignment'] = 'left'
    item.update_text_from_config() # This applies the alignment
    assert item.text_item.document().defaultTextOption().alignment() == Qt.AlignLeft

    item.config_data['horizontal_alignment'] = 'center'
    item.update_text_from_config()
    assert item.text_item.document().defaultTextOption().alignment() == Qt.AlignCenter

    item.config_data['horizontal_alignment'] = 'right'
    item.update_text_from_config()
    assert item.text_item.document().defaultTextOption().alignment() == Qt.AlignRight


def test_apply_font_style(qtbot, create_item):
    item = create_item()

    item.config_data['font_style'] = 'normal'
    item.update_text_from_config()
    assert not item.text_item.font().bold()
    assert not item.text_item.font().italic()

    item.config_data['font_style'] = 'bold'
    item.update_text_from_config()
    assert item.text_item.font().bold()
    assert not item.text_item.font().italic()

    item.config_data['font_style'] = 'italic'
    item.update_text_from_config()
    assert not item.text_item.font().bold()
    assert item.text_item.font().italic()

    # If InfoRectangleItem comes to support "bold italic"
    # item.config_data['font_style'] = 'bold italic'
    # item.update_text_from_config()
    # assert item.text_item.font().bold()
    # assert item.text_item.font().italic()

def test_apply_font_size_and_color(qtbot, create_item):
    item = create_item()
    item.config_data['font_size'] = '22px'
    item.config_data['font_color'] = '#FF00FF'
    item.update_text_from_config()
    # Qt might use pointSize or pixelSize depending on how font was set.
    # If set with setPointSize, pointSize is primary. If setPixelSize, pixelSize.
    # InfoRectangleItem uses setPointSize after parsing "px" value.
    assert item.text_item.font().pointSize() == 22
    assert item.text_item.defaultTextColor() == QColor("#FF00FF")


def test_apply_style_method(qtbot, create_item):
    item = create_item()
    style_config = {
        "font_color": "#112233",
        "font_size": "18px",
        "font_style": "bold",
        "horizontal_alignment": "center",
        "vertical_alignment": "bottom",
        "padding": "8px",
        # "background_color" # This is part of rect_config, not a style applied by apply_style directly to item.text_item's font/alignment
    }

    item.apply_style(style_config)

    # Assert that item.config_data now reflects the flattened style properties.
    assert item.config_data['font_color'] == style_config["font_color"]
    assert item.config_data['font_size'] == style_config["font_size"]
    assert item.config_data['font_style'] == style_config["font_style"]
    assert item.config_data['horizontal_alignment'] == style_config["horizontal_alignment"]
    assert item.config_data['vertical_alignment'] == style_config["vertical_alignment"]
    assert item.config_data['padding'] == style_config["padding"]

    # Since style_config is anonymous (no 'name'), 'text_style_ref' should be None or not present.
    assert item.config_data.get('text_style_ref') is None

    # The item's direct attributes (like self.font_style) ARE updated by update_text_from_config
    # which is called by apply_style and now reads from the updated self.config_data (via _get_style_value's fallback).
    assert item.font_style == "bold"
    assert item.horizontal_alignment == "center"
    assert item.vertical_alignment == "bottom"

    # Check QGraphicsTextItem properties
    assert item.text_item.defaultTextColor() == QColor("#112233")
    assert item.text_item.font().pointSize() == 18
    assert item.text_item.font().bold()
    assert not item.text_item.font().italic()
    assert item.text_item.document().defaultTextOption().alignment() == Qt.AlignCenter
    # Vertical alignment check for text_item.y() would be similar to test_apply_vertical_alignment
    # and depends on item height and text block height.
    # For now, checking the internal attribute is sufficient for apply_style coverage.


def test_style_updates_reflect_on_items(qtbot, create_item_with_scene):
    """
    Tests that if the style dictionary held by _style_config_ref is modified externally,
    the item reflects these changes after its update methods are called.
    """
    # 1. Create two InfoRectangleItem instances with minimal config
    item1_config = {'id': 'item1', 'width': 100, 'height': 50, 'center_x': 50, 'center_y': 25, 'text': 'Initial1'}
    item2_config = {'id': 'item2', 'width': 120, 'height': 60, 'center_x': 60, 'center_y': 30, 'text': 'Initial2'}
    item1 = create_item_with_scene(item1_config)
    item2 = create_item_with_scene(item2_config)

    # 2. Define and apply original_style
    original_style = {
        'font_color': '#FF0000',  # Red
        'font_size': '12px',
        'text': 'Styled Text'  # Style can also set text
    }
    item1.apply_style(original_style)
    item2.apply_style(original_style)
    # apply_style calls update_text_from_config, so properties should be set

    # 3. Initial Assertions
    assert item1.text_item.defaultTextColor() == QColor('#FF0000')
    assert item1.text_item.font().pointSize() == 12
    assert item1.text_item.toPlainText() == 'Styled Text'

    assert item2.text_item.defaultTextColor() == QColor('#FF0000')
    assert item2.text_item.font().pointSize() == 12
    assert item2.text_item.toPlainText() == 'Styled Text'

    # 4. Modify the original_style dictionary
    # This simulates a scenario where a style manager updates the style object
    # that items are referencing.
    original_style['font_color'] = '#00FF00'  # Green
    original_style['font_size'] = '15px'
    # 'text' remains 'Styled Text'

    # 5. Trigger Refresh
    # Items need to be told to re-read their style config.
    # In a real app, this might be part of a style update notification system.
    item1.update_text_from_config()
    item2.update_text_from_config()

    # 6. Final Assertions
    # Both items should now reflect the modified style because they hold a reference
    # to the 'original_style' dictionary via _style_config_ref, and _get_style_value
    # reads from it.
    assert item1.text_item.defaultTextColor() == QColor('#00FF00')
    assert item1.text_item.font().pointSize() == 15
    assert item1.text_item.toPlainText() == 'Styled Text' # Text content from style is still the same

    assert item2.text_item.defaultTextColor() == QColor('#00FF00')
    assert item2.text_item.font().pointSize() == 15
    assert item2.text_item.toPlainText() == 'Styled Text'
