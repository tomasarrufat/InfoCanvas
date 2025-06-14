from unittest.mock import MagicMock, patch

import pytest
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QKeyEvent
from PyQt5.QtWidgets import QLineEdit

from src.input_handler import InputHandler
from src.info_rectangle_item import InfoRectangleItem


def create_key_event(key, modifiers=Qt.NoModifier, text=""):
    return QKeyEvent(QKeyEvent.KeyPress, key, modifiers, text)


# --- Z-Order Manipulation Tests ---
@patch('src.utils.bring_to_front')
def test_bring_to_front_action(mock_btf, base_app_fixture, monkeypatch):
    app = base_app_fixture
    handler = app.input_handler
    app.selected_item = MagicMock()
    monkeypatch.setattr(app, 'save_config', MagicMock())
    handler.bring_to_front_selected()
    mock_btf.assert_called_once_with(app.selected_item)
    app.save_config.assert_called_once()


@patch('src.utils.send_to_back')
def test_send_to_back_action(mock_stb, base_app_fixture, monkeypatch):
    app = base_app_fixture
    handler = app.input_handler
    app.selected_item = MagicMock()
    monkeypatch.setattr(app, 'save_config', MagicMock())
    handler.send_to_back_selected()
    mock_stb.assert_called_once_with(app.selected_item)
    app.save_config.assert_called_once()


@patch('src.utils.bring_forward')
def test_bring_forward_action(mock_bf, base_app_fixture, monkeypatch):
    app = base_app_fixture
    handler = app.input_handler
    app.selected_item = MagicMock()
    monkeypatch.setattr(app, 'save_config', MagicMock())
    handler.bring_forward_selected()
    mock_bf.assert_called_once_with(app.selected_item)
    app.save_config.assert_called_once()


@patch('src.utils.send_backward')
def test_send_backward_action(mock_sb, base_app_fixture, monkeypatch):
    app = base_app_fixture
    handler = app.input_handler
    app.selected_item = MagicMock()
    monkeypatch.setattr(app, 'save_config', MagicMock())
    handler.send_backward_selected()
    mock_sb.assert_called_once_with(app.selected_item)
    app.save_config.assert_called_once()


def test_z_order_actions_no_selected_item(base_app_fixture, monkeypatch):
    app = base_app_fixture
    handler = app.input_handler
    app.selected_item = None
    mock_btf = MagicMock()
    monkeypatch.setattr('src.utils.bring_to_front', mock_btf)
    mock_stb = MagicMock()
    monkeypatch.setattr('src.utils.send_to_back', mock_stb)
    mock_bf = MagicMock()
    monkeypatch.setattr('src.utils.bring_forward', mock_bf)
    mock_sb = MagicMock()
    monkeypatch.setattr('src.utils.send_backward', mock_sb)
    mock_save = MagicMock()
    monkeypatch.setattr(app, 'save_config', mock_save)
    handler.bring_to_front_selected()
    handler.send_to_back_selected()
    handler.bring_forward_selected()
    handler.send_backward_selected()
    mock_btf.assert_not_called()
    mock_stb.assert_not_called()
    mock_bf.assert_not_called()
    mock_sb.assert_not_called()
    mock_save.assert_not_called()


# --- Keyboard Shortcut Tests ---
@patch('src.input_handler.QApplication.focusWidget')
def test_key_press_shortcuts_wrong_mode(mock_focus_widget, base_app_fixture):
    app = base_app_fixture
    handler = app.input_handler
    mock_focus_widget.return_value = app.view
    app.current_mode = "view"
    app.selected_item = MagicMock(spec=InfoRectangleItem)
    app.clipboard_data = None
    app.item_operations.copy_selected_item_to_clipboard = MagicMock(return_value=False)
    app.item_operations.paste_item_from_clipboard = MagicMock(return_value=False)
    app.item_operations.delete_selected_item_on_canvas = MagicMock(return_value=False)

    event_copy = create_key_event(Qt.Key_C, modifiers=Qt.ControlModifier)
    handled = handler.handle_key_press(event_copy)
    app.item_operations.copy_selected_item_to_clipboard.assert_not_called()
    assert not event_copy.isAccepted() and handled is False

    event_paste = create_key_event(Qt.Key_V, modifiers=Qt.ControlModifier)
    handled = handler.handle_key_press(event_paste)
    app.item_operations.paste_item_from_clipboard.assert_not_called()
    assert not event_paste.isAccepted() and handled is False

    event_delete = create_key_event(Qt.Key_Delete)
    handled = handler.handle_key_press(event_delete)
    app.item_operations.delete_selected_item_on_canvas.assert_not_called()
    assert not event_delete.isAccepted() and handled is False


@patch('src.input_handler.QApplication.focusWidget')
def test_key_press_shortcuts_input_focused(mock_focus_widget, base_app_fixture):
    app = base_app_fixture
    handler = app.input_handler
    mock_focus_widget.return_value = MagicMock(spec=['__class__', '__name__'])
    mock_focus_widget.return_value.__class__ = QLineEdit
    app.current_mode = "edit"
    app.selected_item = MagicMock(spec=InfoRectangleItem)
    app.clipboard_data = None
    app.item_operations.copy_selected_item_to_clipboard = MagicMock(return_value=False)
    app.item_operations.paste_item_from_clipboard = MagicMock(return_value=False)
    app.item_operations.delete_selected_item_on_canvas = MagicMock(return_value=False)

    event_copy = create_key_event(Qt.Key_C, modifiers=Qt.ControlModifier)
    handled = handler.handle_key_press(event_copy)
    app.item_operations.copy_selected_item_to_clipboard.assert_not_called()
    assert not event_copy.isAccepted() and handled is False

    event_paste = create_key_event(Qt.Key_V, modifiers=Qt.ControlModifier)
    handled = handler.handle_key_press(event_paste)
    app.item_operations.paste_item_from_clipboard.assert_not_called()
    assert not event_paste.isAccepted() and handled is False

    event_delete = create_key_event(Qt.Key_Delete)
    handled = handler.handle_key_press(event_delete)
    app.item_operations.delete_selected_item_on_canvas.assert_not_called()
    assert not event_delete.isAccepted() and handled is False


@patch('src.input_handler.QApplication.focusWidget')
def test_ctrl_z_triggers_undo(mock_focus_widget, base_app_fixture, monkeypatch):
    app = base_app_fixture
    handler = app.input_handler
    mock_focus_widget.return_value = app.view
    app.current_mode = "edit"
    monkeypatch.setattr(app, 'undo_last_action', MagicMock())

    event_undo = create_key_event(Qt.Key_Z, modifiers=Qt.ControlModifier)
    handled = handler.handle_key_press(event_undo)
    app.undo_last_action.assert_called_once()
    assert event_undo.isAccepted() and handled is True


@patch('src.input_handler.QApplication.focusWidget')
def test_ctrl_z_ignored_when_input_focused(mock_focus_widget, base_app_fixture, monkeypatch):
    app = base_app_fixture
    handler = app.input_handler
    mock_focus_widget.return_value = MagicMock(spec=['__class__', '__name__'])
    mock_focus_widget.return_value.__class__ = QLineEdit
    app.current_mode = "edit"
    monkeypatch.setattr(app, 'undo_last_action', MagicMock())

    event_undo = create_key_event(Qt.Key_Z, modifiers=Qt.ControlModifier)
    handled = handler.handle_key_press(event_undo)
    app.undo_last_action.assert_not_called()
    assert not event_undo.isAccepted() and handled is False
