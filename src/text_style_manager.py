# src/text_style_manager.py

from PyQt5.QtWidgets import QColorDialog, QInputDialog, QMessageBox
from PyQt5.QtGui import QColor

from src import utils
from src.info_rectangle_item import InfoRectangleItem

class TextStyleManager:
    def __init__(self, app):
        """
        Initializes the TextStyleManager.

        Args:
            app: The main InfoCanvasApp instance.
        """
        self.app = app

    def get_contrasting_text_color(self, hex_color):
        try:
            hex_color = hex_color.lstrip('#')
            r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
            luminance = (0.299 * r + 0.587 * g + 0.114 * b)
            return "#FFFFFF" if luminance < 128 else "#000000"
        except Exception:
            return "#000000"

    def does_item_match_default_style(self, item_config):
        defaults = utils.get_default_config()["defaults"]["info_rectangle_text_display"].copy()
        style_keys = ["font_color", "font_size",
                      "horizontal_alignment", "vertical_alignment", "padding"]
        for key in style_keys:
            if item_config.get(key, defaults.get(key)) != defaults.get(key):
                return False
        return True

    def find_matching_style_name(self, item_config):
        styles = self.app.config.get('text_styles', [])
        style_keys_to_check = ["font_color", "font_size",
                               "horizontal_alignment", "vertical_alignment", "padding"]
        for style_dict in styles:
            if not isinstance(style_dict, dict): continue
            match = True
            for key in style_keys_to_check:
                # Use .get for item_config as well for safety, though it should ideally have these keys
                item_value = item_config.get(key)
                style_value = style_dict.get(key)
                if item_value != style_value:
                    match = False
                    break
            if match:
                return style_dict.get('name')
        return None

    def load_styles_into_dropdown(self):
        if not hasattr(self.app, 'rect_style_combo'): return
        self.app.rect_style_combo.blockSignals(True)
        self.app.rect_style_combo.clear()
        self.app.rect_style_combo.addItem("Default")
        self.app.rect_style_combo.addItem("Custom")

        styles = self.app.config.get('text_styles', [])
        for style in styles:
            if isinstance(style, dict) and 'name' in style:
                 self.app.rect_style_combo.addItem(style['name'])
        self.app.rect_style_combo.blockSignals(False)

    def save_current_item_style(self):
        if not isinstance(self.app.selected_item, InfoRectangleItem):
            QMessageBox.warning(self.app.main_window if hasattr(self.app, 'main_window') else None, "Save Style", "Please select an Info Area to save its style.")
            return

        item_config = self.app.selected_item.config_data
        default_display_conf = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

        style_name, ok = QInputDialog.getText(self.app.main_window if hasattr(self.app, 'main_window') else None, "Save Text Style", "Enter style name:")
        if not ok or not style_name:
            if ok and not style_name:
                QMessageBox.warning(self.app.main_window if hasattr(self.app, 'main_window') else None, "Save Style", "Style name cannot be empty.")
            return

        current_style_dict = {
            "name": style_name,
            "font_color": item_config.get('font_color', default_display_conf['font_color']),
            "font_size": item_config.get('font_size', default_display_conf['font_size']),
            "horizontal_alignment": item_config.get('horizontal_alignment', default_display_conf['horizontal_alignment']),
            "vertical_alignment": item_config.get('vertical_alignment', default_display_conf['vertical_alignment']),
            "padding": item_config.get('padding', default_display_conf['padding']),
        }

        existing_styles = self.app.config.setdefault('text_styles', [])
        style_object_updated = None

        found_existing_style_for_update = False
        for s in existing_styles:
            if s['name'] == style_name:
                reply = QMessageBox.question(self.app.main_window if hasattr(self.app, 'main_window') else None, "Overwrite Style",
                                             f"Style '{style_name}' already exists. Overwrite it?",
                                             QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if reply == QMessageBox.No:
                    return
                else:
                    s.clear()
                    s.update(current_style_dict)
                    style_object_updated = s
                    found_existing_style_for_update = True
                    break

        if not found_existing_style_for_update:
            existing_styles.append(current_style_dict)
            style_object_updated = current_style_dict

        if style_object_updated is None:
            return

        self.app.save_config()
        self.load_styles_into_dropdown()

        for item_in_map in self.app.item_map.values():
            if isinstance(item_in_map, InfoRectangleItem):
                if item_in_map.config_data.get('text_style_ref') == style_name:
                    item_in_map.apply_style(style_object_updated)

        if self.app.selected_item:
            self.app.selected_item.config_data['text_style_ref'] = style_name
            self.app.selected_item.apply_style(style_object_updated)


        if hasattr(self.app, 'rect_style_combo'):
            self.app.rect_style_combo.blockSignals(True)
            self.app.rect_style_combo.setCurrentText(style_name)
            self.app.rect_style_combo.blockSignals(False)

        if hasattr(self.app, 'statusBar'):
            self.app.statusBar().showMessage(f"Text style '{style_name}' saved and applied.", 2000)

    def handle_style_selection(self, style_name):
        if not isinstance(self.app.selected_item, InfoRectangleItem) or not style_name :
            return

        controls_to_block = []
        if hasattr(self.app, 'rect_style_combo'): controls_to_block.append(self.app.rect_style_combo)
        if hasattr(self.app, 'rect_h_align_combo'): controls_to_block.append(self.app.rect_h_align_combo)
        if hasattr(self.app, 'rect_v_align_combo'): controls_to_block.append(self.app.rect_v_align_combo)
        if hasattr(self.app, 'rect_font_size_combo'): controls_to_block.append(self.app.rect_font_size_combo)

        for control in controls_to_block:
            control.blockSignals(True)

        item_config = self.app.selected_item.config_data
        style_applied_or_defaulted = False

        if style_name == "Default":
            default_settings = utils.get_default_config()["defaults"]["info_rectangle_text_display"]
            style_to_apply = default_settings.copy()
            item_config.pop('text_style_ref', None)
            self.app.selected_item.apply_style(style_to_apply)
            style_applied_or_defaulted = True
        elif style_name == "Custom":
            item_config.pop('text_style_ref', None)
        else:
            found_style = None
            for s in self.app.config.get('text_styles', []):
                if isinstance(s, dict) and s.get('name') == style_name:
                    found_style = s
                    break
            if found_style:
                style_to_apply = found_style.copy()
                item_config['text_style_ref'] = style_name
                self.app.selected_item.apply_style(style_to_apply)
                style_applied_or_defaulted = True
            else:
                 if hasattr(self.app, 'rect_style_combo'):
                    self.app.rect_style_combo.setCurrentText("Custom")
                 item_config.pop('text_style_ref', None)

        for control in controls_to_block:
            control.blockSignals(False)

        if style_applied_or_defaulted: # Update panel if a style was applied or defaulted
            if hasattr(self.app, 'update_properties_panel'):
                self.app.update_properties_panel()
        elif style_name == "Custom": # Explicitly ensure custom is set if that's the selection
             if hasattr(self.app, 'rect_style_combo'):
                self.app.rect_style_combo.blockSignals(True)
                self.app.rect_style_combo.setCurrentText("Custom")
                self.app.rect_style_combo.blockSignals(False)
             if hasattr(self.app, 'update_properties_panel'): # Also update panel for custom
                self.app.update_properties_panel()


    def handle_format_change(self, value=None):
        if isinstance(self.app.selected_item, InfoRectangleItem):
            config = self.app.selected_item.config_data
            default_display_conf = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

            if hasattr(self.app, 'rect_h_align_combo'):
                config['horizontal_alignment'] = self.app.rect_h_align_combo.currentText().lower()
            if hasattr(self.app, 'rect_v_align_combo'):
                config['vertical_alignment'] = self.app.rect_v_align_combo.currentText().lower()
            if hasattr(self.app, 'rect_font_size_combo'):
                font_size_text = self.app.rect_font_size_combo.currentText()
                if font_size_text.isdigit():
                    config['font_size'] = f"{font_size_text}px"
                else: # Fallback to default if not a digit
                    config['font_size'] = default_display_conf["font_size"]
                    self.app.rect_font_size_combo.blockSignals(True)
                    self.app.rect_font_size_combo.setCurrentText(default_display_conf["font_size"].replace("px",""))
                    self.app.rect_font_size_combo.blockSignals(False)

            config.pop('text_style_ref', None)
            self.app.selected_item.apply_style(config) # This will trigger properties_changed -> update_properties_panel

            # Update style combo based on new state
            if hasattr(self.app, 'rect_style_combo'):
                self.app.rect_style_combo.blockSignals(True)
                if self.does_item_match_default_style(config):
                    self.app.rect_style_combo.setCurrentText("Default")
                else:
                    matched_style_name = self.find_matching_style_name(config)
                    if matched_style_name:
                        config['text_style_ref'] = matched_style_name # Restore ref if it matches a style
                        self.app.rect_style_combo.setCurrentText(matched_style_name)
                    else:
                        self.app.rect_style_combo.setCurrentText("Custom")
                self.app.rect_style_combo.blockSignals(False)


    def handle_font_color_change(self):
        if not self.app.selected_item or not isinstance(self.app.selected_item, InfoRectangleItem):
            return

        item_config = self.app.selected_item.config_data
        default_color = utils.get_default_config()["defaults"]["info_rectangle_text_display"]['font_color']
        initial_color_str = item_config.get('font_color', default_color)

        q_initial_color = QColor(initial_color_str)
        if not q_initial_color.isValid():
            q_initial_color = QColor(default_color)

        parent_widget = self.app.main_window if hasattr(self.app, 'main_window') else None
        color = QColorDialog.getColor(q_initial_color, parent_widget, "Select Text Color")

        if color.isValid():
            new_color_hex = color.name()
            item_config['font_color'] = new_color_hex
            item_config.pop('text_style_ref', None)

            # apply_style expects a complete style dictionary.
            # We should pass the modified item_config directly if it's what apply_style expects,
            # or construct a style dict. Assuming apply_style can take the item_config.
            self.app.selected_item.apply_style(item_config) # This will trigger properties_changed -> update_properties_panel

            if hasattr(self.app, 'rect_font_color_button'):
                contrasting_text_color = self.get_contrasting_text_color(new_color_hex)
                self.app.rect_font_color_button.setStyleSheet(
                    f"background-color: {new_color_hex}; color: {contrasting_text_color};"
                )

            # Update style combo
            if hasattr(self.app, 'rect_style_combo'):
                self.app.rect_style_combo.blockSignals(True)
                if self.does_item_match_default_style(item_config): # Use item_config post-change
                    self.app.rect_style_combo.setCurrentText("Default")
                else:
                    matched_style_name = self.find_matching_style_name(item_config) # Use item_config post-change
                    if matched_style_name:
                        item_config['text_style_ref'] = matched_style_name # Restore ref
                        self.app.rect_style_combo.setCurrentText(matched_style_name)
                    else:
                        self.app.rect_style_combo.setCurrentText("Custom")
                self.app.rect_style_combo.blockSignals(False)


if __name__ == '__main__':
    print("TextStyleManager module loaded.")
