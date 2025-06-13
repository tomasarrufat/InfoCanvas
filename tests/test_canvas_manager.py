import datetime
import pytest
from src.canvas_manager import CanvasManager
from src.info_rectangle_item import InfoRectangleItem

class TestCanvasManagerAlignment:
    def test_horizontal_alignment_logic(self, base_app_fixture, monkeypatch):
        app_window = base_app_fixture
        manager = CanvasManager(app_window)
        app_window.config['info_rectangles'] = []
        app_window.item_map.clear()
        app_window.scene.clear()
        manager.render_canvas_from_config()

        rect_details = [
            (50, 100, 80, 40, "R1_h"),
            (120, 110, 80, 40, "R2_h"),
            (180, 120, 80, 40, "R3_h")
        ]
        items = []
        for i, (cx, cy, w, h, name_part) in enumerate(rect_details):
            rect_id = f"{name_part}_{datetime.datetime.now().timestamp()}_{i}"
            rect_config = {"id": rect_id, "text": name_part, "center_x": cx, "center_y": cy, "width": w, "height": h, "z_index": i}
            app_window.config['info_rectangles'].append(rect_config)
            item = InfoRectangleItem(rect_config)
            manager.scene.addItem(item)
            app_window.item_map[rect_id] = item
            items.append(item)
        rect_a, rect_b, rect_c = items
        rect_a.setSelected(True)
        manager.on_scene_selection_changed()
        rect_b.setSelected(True)
        manager.on_scene_selection_changed()
        rect_c.setSelected(True)
        manager.on_scene_selection_changed()
        target_x = manager.app.chronologically_first_selected_item.config_data['center_x']
        manager.align_selected_rects_horizontally()
        for item in items:
            assert item.config_data['center_x'] == pytest.approx(target_x)

    def test_vertical_alignment_logic(self, base_app_fixture, monkeypatch):
        app_window = base_app_fixture
        manager = CanvasManager(app_window)
        app_window.config['info_rectangles'] = []
        app_window.item_map.clear()
        app_window.scene.clear()
        manager.render_canvas_from_config()

        rect_details = [
            (100, 50, 80, 40, "R1_v"),
            (110, 120, 80, 40, "R2_v"),
            (120, 180, 80, 40, "R3_v")
        ]
        items = []
        for i, (cx, cy, w, h, name_part) in enumerate(rect_details):
            rect_id = f"{name_part}_{datetime.datetime.now().timestamp()}_{i}"
            rect_config = {"id": rect_id, "text": name_part, "center_x": cx, "center_y": cy, "width": w, "height": h, "z_index": i}
            app_window.config['info_rectangles'].append(rect_config)
            item = InfoRectangleItem(rect_config)
            manager.scene.addItem(item)
            app_window.item_map[rect_id] = item
            items.append(item)
        rect_a, rect_b, rect_c = items
        rect_a.setSelected(True)
        manager.on_scene_selection_changed()
        rect_b.setSelected(True)
        manager.on_scene_selection_changed()
        rect_c.setSelected(True)
        manager.on_scene_selection_changed()
        target_y = manager.app.chronologically_first_selected_item.config_data['center_y']
        manager.align_selected_rects_vertically()
        for item in items:
            assert item.config_data['center_y'] == pytest.approx(target_y)
