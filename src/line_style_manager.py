# src/line_style_manager.py

from PyQt5.QtWidgets import QColorDialog, QInputDialog, QMessageBox
from PyQt5.QtGui import QColor

from src.connection_line_item import ConnectionLineItem

class LineStyleManager:
    def __init__(self, app):
        self.app = app

    def load_styles_into_dropdown(self):
        if not hasattr(self.app, 'line_style_combo'):
            return
        self.app.line_style_combo.blockSignals(True)
        self.app.line_style_combo.clear()
        self.app.line_style_combo.addItem('Default')
        self.app.line_style_combo.addItem('Custom')
        for style in self.app.config.get('line_styles', []):
            if isinstance(style, dict) and 'name' in style:
                self.app.line_style_combo.addItem(style['name'])
        self.app.line_style_combo.blockSignals(False)

    def handle_style_selection(self, style_name):
        if not isinstance(self.app.selected_item, ConnectionLineItem) or not style_name:
            return

        item_config = self.app.selected_item.config_data
        defaults = {'line_color': '#00ffff', 'thickness': 2, 'opacity': 1.0}

        if style_name == 'Default':
            item_config.pop('line_style_ref', None)
            self.app.selected_item.apply_style(defaults)
        elif style_name == 'Custom':
            item_config.pop('line_style_ref', None)
        else:
            found_style = None
            for s in self.app.config.get('line_styles', []):
                if isinstance(s, dict) and s.get('name') == style_name:
                    found_style = s
                    break
            if found_style:
                item_config['line_style_ref'] = style_name
                self.app.selected_item.apply_style(found_style)
            else:
                if hasattr(self.app, 'line_style_combo'):
                    self.app.line_style_combo.setCurrentText('Custom')
                item_config.pop('line_style_ref', None)

        if hasattr(self.app, 'update_properties_panel'):
            self.app.update_properties_panel()

    def save_current_item_style(self):
        if not isinstance(self.app.selected_item, ConnectionLineItem):
            QMessageBox.warning(
                self.app.main_window if hasattr(self.app, 'main_window') else None,
                'Save Style',
                'Please select a connection line to save its style.'
            )
            return

        item_config = self.app.selected_item.config_data
        defaults = {'line_color': '#00ffff', 'thickness': 2, 'opacity': 1.0}
        style_name, ok = QInputDialog.getText(
            self.app.main_window if hasattr(self.app, 'main_window') else None,
            'Save Line Style',
            'Enter style name:'
        )
        if not ok or not style_name:
            if ok and not style_name:
                QMessageBox.warning(
                    self.app.main_window if hasattr(self.app, 'main_window') else None,
                    'Save Style',
                    'Style name cannot be empty.'
                )
            return

        current_style_dict = {
            'name': style_name,
            'line_color': item_config.get('line_color', defaults['line_color']),
            'thickness': item_config.get('thickness', defaults['thickness']),
            'opacity': item_config.get('opacity', defaults['opacity']),
        }

        existing_styles = self.app.config.setdefault('line_styles', [])
        style_object_updated = None
        found_existing = False
        for s in existing_styles:
            if s.get('name') == style_name:
                reply = QMessageBox.question(
                    self.app.main_window if hasattr(self.app, 'main_window') else None,
                    'Overwrite Style',
                    f"Style '{style_name}' already exists. Overwrite it?",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                if reply == QMessageBox.No:
                    return
                s.clear()
                s.update(current_style_dict)
                style_object_updated = s
                found_existing = True
                break
        if not found_existing:
            existing_styles.append(current_style_dict)
            style_object_updated = current_style_dict

        if style_object_updated is None:
            return

        self.app.save_config()
        self.load_styles_into_dropdown()

        for item in self.app.item_map.values():
            if isinstance(item, ConnectionLineItem):
                if item.config_data.get('line_style_ref') == style_name:
                    item.apply_style(style_object_updated)

        if self.app.selected_item:
            self.app.selected_item.config_data['line_style_ref'] = style_name
            self.app.selected_item.apply_style(style_object_updated)

        if hasattr(self.app, 'line_style_combo'):
            self.app.line_style_combo.blockSignals(True)
            self.app.line_style_combo.setCurrentText(style_name)
            self.app.line_style_combo.blockSignals(False)

        if hasattr(self.app, 'statusBar'):
            self.app.statusBar().showMessage(
                f"Line style '{style_name}' saved and applied.", 2000
            )
