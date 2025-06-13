# New InputHandler for keyboard shortcuts and layering operations
from PyQt5.QtWidgets import QApplication, QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox
from PyQt5.QtCore import Qt

from . import utils


class InputHandler:
    """Handles keyboard shortcuts and z-order actions for the main application."""

    def __init__(self, app):
        self.app = app

    # -- Keyboard Shortcut Handling -------------------------------------
    def handle_key_press(self, event):
        """Process key press events. Returns True if the event was handled."""
        focused_widget = QApplication.focusWidget()
        is_input_focused = isinstance(
            focused_widget, (QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox)
        )

        if event.modifiers() == Qt.ControlModifier:
            if event.key() == Qt.Key_C:
                if (
                    self.app.current_mode == "edit"
                    and not is_input_focused
                    and self.app.item_operations.copy_selected_item_to_clipboard()
                ):
                    event.accept()
                    return True
            elif event.key() == Qt.Key_V:
                if self.app.current_mode == "edit" and not is_input_focused:
                    if self.app.item_operations.paste_item_from_clipboard():
                        event.accept()
                        return True
        elif event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if (
                self.app.current_mode == "edit"
                and not is_input_focused
                and self.app.item_operations.delete_selected_item_on_canvas()
            ):
                event.accept()
                return True
        event.ignore()
        return False

    # -- Z-Order Manipulation ------------------------------------------
    def bring_to_front_selected(self):
        if self.app.selected_item:
            utils.bring_to_front(self.app.selected_item)
            self.app.save_config()

    def send_to_back_selected(self):
        if self.app.selected_item:
            utils.send_to_back(self.app.selected_item)
            self.app.save_config()

    def bring_forward_selected(self):
        if self.app.selected_item:
            utils.bring_forward(self.app.selected_item)
            self.app.save_config()

    def send_backward_selected(self):
        if self.app.selected_item:
            utils.send_backward(self.app.selected_item)
            self.app.save_config()
