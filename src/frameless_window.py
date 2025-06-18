import sys
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMenu, QAction
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent
from PyQt5.QtGui import QMouseEvent

class CustomTitleBar(QWidget):
    """
    Custom Title Bar for the frameless window.
    This class now primarily handles the UI and signals for the title bar.
    The event handling for moving and snapping is managed by the parent window's event filter.
    """
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        # Set a fixed height for the title bar
        self.setFixedHeight(30)
        self.layout = QHBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(0)

        # File Menu Button
        self.btn_file_menu = QPushButton("File")
        self.btn_file_menu.setFixedSize(50, 30) # Fixed width, height matches title bar
        self.btn_file_menu.setStyleSheet("""
            QPushButton {
                background-color: #333; color: white; border: none; font-weight: bold; padding: 0px 10px;
            }
            QPushButton:hover { background-color: #555; }
            QPushButton:pressed { background-color: #222; }
            QPushButton::menu-indicator { image: none; }
        """)
        self.file_menu = QMenu(self)
        self.file_menu.setStyleSheet("""
            QMenu {
                background-color: #333;
                color: white;
                border: 1px solid #555;
            }
            QMenu::item:selected {
                background-color: #555;
            }
            QMenu::separator {
                height: 1px;
                background: #555;
                margin-left: 10px;
                margin-right: 5px;
            }
        """)

        manage_projects_action = QAction("Manage Projects", self)
        save_config_action = QAction("Save Configuration", self)
        export_html_action = QAction("Export to HTML", self)
        exit_action = QAction("Exit", self)

        # Connect QActions (assuming parent has these methods)
        manage_projects_action.triggered.connect(self.parent._show_project_manager_dialog)
        save_config_action.triggered.connect(lambda: self.parent.save_config())
        export_html_action.triggered.connect(lambda: self.parent.export_to_html())
        exit_action.triggered.connect(self.parent.close)

        self.file_menu.addAction(manage_projects_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(save_config_action)
        self.file_menu.addAction(export_html_action)
        self.file_menu.addSeparator()
        self.file_menu.addAction(exit_action)

        self.btn_file_menu.clicked.connect(self.show_file_menu)


        self.title = QLabel("Frameless App") # Default title, app can change it
        self.title.setFixedHeight(30)
        self.title.setStyleSheet("""
            background-color: #333;
            color: white;
            padding-left: 10px;
            font-weight: bold;
        """)

        self.btn_minimize = QPushButton("—")
        self.btn_maximize = QPushButton("[]")
        self.btn_close = QPushButton("X")

        # Styling for the buttons
        for btn in [self.btn_minimize, self.btn_maximize, self.btn_close]:
            btn.setFixedSize(30, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #333;
                    color: white;
                    border: none;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QPushButton:pressed {
                    background-color: #222;
                }
            """)

        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #333;
                color: white;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c42b1c;
            }
            QPushButton:pressed {
                background-color: #9b2216;
            }
        """)

        self.layout.addWidget(self.btn_file_menu) # Add file menu button first
        self.layout.addWidget(self.title)
        self.layout.addStretch() # Pushes window control buttons to the right
        self.layout.addWidget(self.btn_minimize)
        self.layout.addWidget(self.btn_maximize)
        self.layout.addWidget(self.btn_close)

        self.setLayout(self.layout)

        # Connect signals to slots
        self.btn_close.clicked.connect(self.parent.close)
        self.btn_minimize.clicked.connect(self.parent.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize)

    def show_file_menu(self):
        menu_position = self.btn_file_menu.mapToGlobal(QPoint(0, self.btn_file_menu.height()))
        self.file_menu.exec_(menu_position)

    def toggle_maximize(self):
        """Toggle between maximized and normal window state."""
        parent = self.parent
        from PyQt5.QtWidgets import QWidget
        if not isinstance(parent, QWidget):
            return  # Safety: parent is not a QWidget
        if parent.isMaximized():
            # Fallback: if normal_geometry is not valid, use a default size/position
            if not hasattr(parent, 'normal_geometry') or parent.normal_geometry.isNull():
                parent.normal_geometry = QRect(100, 100, 800, 600)
            parent.showNormal()
            parent.setGeometry(parent.normal_geometry)
            self.btn_maximize.setText("[]")
        else:
            # Always update normal_geometry before maximizing
            parent.normal_geometry = parent.geometry()
            parent.showMaximized()
            self.btn_maximize.setText("[ ]")


class FramelessWindow(QWidget):
    """
    Main frameless window class with resizing and event filtering.
    """
    def __init__(self):
        super().__init__()
        # Set window flags to be frameless and translucent
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.setWindowTitle("Custom Frame") # This title is for OS taskbar, not the custom title bar
        # Initial geometry will be set by the subclass or user
        # self.setGeometry(100, 100, 800, 600) # Initial geometry can be set by the app itself
        self.setMinimumSize(400, 300) # Default minimum size
        self.normal_geometry = QRect()  # Initialize, will be set before first maximize

        # This attribute is necessary to enable mouse tracking for resizing.
        self.setMouseTracking(True)

        # Main layout container
        self.container = QWidget()
        self.container.setObjectName("FramelessContainer") # For styling if needed
        self.container.setStyleSheet("#FramelessContainer { background-color: #333; border-radius: 5px; }")

        # Main layout for the container (title bar + content)
        self.main_layout = QVBoxLayout(self.container)
        self.main_layout.setContentsMargins(1, 1, 1, 1) # This creates the border effect
        self.main_layout.setSpacing(0)

        # We need an outer layout for the main window for translucency and shadow effects
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0,0,0,0) # No margins for the outer layout
        outer_layout.addWidget(self.container)
        self.setLayout(outer_layout) # Set the outer_layout as the main layout for FramelessWindow


        # Custom title bar
        self.title_bar = CustomTitleBar(self)
        # Install event filter to handle title bar interactions
        self.title_bar.installEventFilter(self)

        # Content area
        self.content = QWidget()
        self.content.setObjectName("FramelessContent") # For styling
        self.content.setStyleSheet("#FramelessContent { background-color: #f0f0f0; border-bottom-left-radius: 4px; border-bottom-right-radius: 4px; }")
        self.content_layout = QVBoxLayout()
        self.content.setLayout(self.content_layout)

        # Add widgets to the main_layout (inside container)
        self.main_layout.addWidget(self.title_bar)
        self.main_layout.addWidget(self.content)

        # Variables for resizing
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = QPoint()
        self.resize_start_geometry = QRect()
        self.grip_size = 8

        # Variables for moving (from event filter)
        self._mouse_press_pos = None
        self._mouse_move_pos = None
        self._restoring_from_max = False

    def eventFilter(self, obj, event):
        # Handle events for the title bar
        if obj is self.title_bar:
            if event.type() == QEvent.MouseButtonPress:
                if event.button() == Qt.LeftButton:
                    self._mouse_press_pos = event.globalPos()
                    self._mouse_move_pos = event.globalPos()
                    if self.isMaximized():
                        self._restoring_from_max = True
                    return True # We've handled the event

            if event.type() == QEvent.MouseMove:
                if event.buttons() == Qt.LeftButton:
                    if self._restoring_from_max:
                        # Restore and prepare for move
                        self.title_bar.toggle_maximize() # This will call showNormal()
                        # Adjust position so mouse is "grabbing" the window correctly
                        restore_point_ratio = event.x() / self.title_bar.width()
                        new_x = event.globalPos().x() - self.normal_geometry.width() * restore_point_ratio
                        self.move(int(new_x), event.globalPos().y() - self.title_bar.height() // 2)
                        self._restoring_from_max = False
                        # Update mouse press position to current global pos for smooth drag after restore
                        self._mouse_press_pos = event.globalPos()
                        self._mouse_move_pos = event.globalPos() # Critical: re-init for further moves
                        return True

                    if not self.isMaximized():
                        # Snap to top to maximize
                        screen_rect = QApplication.desktop().availableGeometry(self)
                        if event.globalPos().y() <= screen_rect.top() + 5: # Small threshold for snapping
                            self.title_bar.toggle_maximize()
                            return True # Event handled

                        current_pos = event.globalPos()
                        global_move = current_pos - self._mouse_move_pos
                        self.move(self.pos() + global_move)
                        self._mouse_move_pos = current_pos
                        return True

            if event.type() == QEvent.MouseButtonRelease:
                if event.button() == Qt.LeftButton:
                    self._mouse_press_pos = None
                    self._mouse_move_pos = None
                    self._restoring_from_max = False
                    return True

            if event.type() == QEvent.MouseButtonDblClick:
                if event.button() == Qt.LeftButton:
                    self.title_bar.toggle_maximize()
                    return True

        # Pass the event on to the parent class
        return super(FramelessWindow, self).eventFilter(obj, event)

    def check_resize_edge(self, pos):
        """Check which edge the mouse is on."""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()

        on_left = x >= 0 and x < self.grip_size
        on_right = x >= w - self.grip_size and x < w
        on_top = y >= 0 and y < self.grip_size # Note: Title bar area is not for top resizing
        on_bottom = y >= h - self.grip_size and y < h

        # Adjust top resizing to only occur if not over title bar area
        # Assuming title_bar is always at the top and has a fixed height.
        title_bar_height = self.title_bar.height()
        if on_top and y < title_bar_height : # If in title bar area, not a top-edge resize
             on_top = False


        if on_top and on_left: return Qt.TopLeftCorner
        if on_top and on_right: return Qt.TopRightCorner
        if on_bottom and on_left: return Qt.BottomLeftCorner
        if on_bottom and on_right: return Qt.BottomRightCorner
        if on_left: return Qt.LeftEdge
        if on_right: return Qt.RightEdge
        if on_top: return Qt.TopEdge
        if on_bottom: return Qt.BottomEdge
        return None

    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for resizing."""
        if event.button() == Qt.LeftButton and not self.isMaximized():
            # Check if the press is within the content area (not on title bar) for resizing
            # Or if it's on the edges but not where the title bar is.
            # The title bar handles its own move events via eventFilter.
            # This logic ensures that presses on the title bar don't initiate resizing.
            if not self.title_bar.geometry().contains(event.pos()):
                self.resize_edge = self.check_resize_edge(event.pos())
                if self.resize_edge:
                    self.resizing = True
                    self.resize_start_pos = event.globalPos()
                    self.resize_start_geometry = self.geometry()
                    event.accept()
                    return # Event handled for resizing
        super().mousePressEvent(event)


    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release for resizing."""
        if event.button() == Qt.LeftButton:
            if self.resizing:
                self.resizing = False
                self.resize_edge = None
                self.unsetCursor() # Reset cursor to normal
                event.accept()
                return # Event handled
        super().mouseReleaseEvent(event)


    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for resizing and cursor changes."""
        if self.resizing and not self.isMaximized():
            delta = event.globalPos() - self.resize_start_pos
            geom = QRect(self.resize_start_geometry) # Use a copy

            new_geom = QRect(geom)

            min_width = self.minimumWidth()
            min_height = self.minimumHeight()

            if self.resize_edge == Qt.LeftEdge or self.resize_edge == Qt.TopLeftCorner or self.resize_edge == Qt.BottomLeftCorner:
                new_geom.setLeft(geom.left() + delta.x())
                if new_geom.width() < min_width:
                    new_geom.setLeft(geom.right() - min_width)
            if self.resize_edge == Qt.RightEdge or self.resize_edge == Qt.TopRightCorner or self.resize_edge == Qt.BottomRightCorner:
                new_geom.setRight(geom.right() + delta.x())
                if new_geom.width() < min_width:
                    new_geom.setRight(geom.left() + min_width)
            if self.resize_edge == Qt.TopEdge or self.resize_edge == Qt.TopLeftCorner or self.resize_edge == Qt.TopRightCorner:
                new_geom.setTop(geom.top() + delta.y())
                if new_geom.height() < min_height:
                    new_geom.setTop(geom.bottom() - min_height)
            if self.resize_edge == Qt.BottomEdge or self.resize_edge == Qt.BottomLeftCorner or self.resize_edge == Qt.BottomRightCorner:
                new_geom.setBottom(geom.bottom() + delta.y())
                if new_geom.height() < min_height:
                    new_geom.setBottom(geom.top() + min_height)

            # Prevent resizing smaller than minimum size by adjusting the geometry
            if new_geom.width() < min_width:
                if self.resize_edge in [Qt.LeftEdge, Qt.TopLeftCorner, Qt.BottomLeftCorner]:
                    new_geom.setLeft(new_geom.right() - min_width)
                else: # Right edge or corners involving right
                    new_geom.setRight(new_geom.left() + min_width)

            if new_geom.height() < min_height:
                if self.resize_edge in [Qt.TopEdge, Qt.TopLeftCorner, Qt.TopRightCorner]:
                    new_geom.setTop(new_geom.bottom() - min_height)
                else: # Bottom edge or corners involving bottom
                    new_geom.setBottom(new_geom.top() + min_height)

            self.setGeometry(new_geom)
            event.accept()
            return

        elif not self.isMaximized():
            # Update cursor if not resizing and not maximized, and not over title bar
            # (title bar has its own default cursor)
            if not self.title_bar.geometry().contains(event.pos()):
                edge = self.check_resize_edge(event.pos())
                if edge == Qt.TopLeftCorner or edge == Qt.BottomRightCorner: self.setCursor(Qt.SizeFDiagCursor)
                elif edge == Qt.TopRightCorner or edge == Qt.BottomLeftCorner: self.setCursor(Qt.SizeBDiagCursor)
                elif edge == Qt.LeftEdge or edge == Qt.RightEdge: self.setCursor(Qt.SizeHorCursor)
                elif edge == Qt.TopEdge or edge == Qt.BottomEdge: self.setCursor(Qt.SizeVerCursor)
                else: self.unsetCursor()
            else:
                self.unsetCursor() # Ensure default cursor over title bar unless a button changes it

        super().mouseMoveEvent(event)


    def changeEvent(self, event):
        """Keep normal_geometry in sync when window state changes (e.g., via window manager or maximize button)."""
        if event.type() == QEvent.WindowStateChange:
            if self.isMaximized():
                # If window is maximized, normal_geometry should have been set *before* maximizing.
                # Update the maximize button text.
                self.title_bar.btn_maximize.setText("[ ]") # Symbol for restore
            elif not self.isMaximized():
                # Window is not maximized (e.g., restored or was never maximized).
                # If we have a valid normal_geometry, this means it was likely restored from maximize.
                # The setGeometry in toggle_maximize would handle this.
                # Here, we just ensure the button text is correct for a normal state.
                self.title_bar.btn_maximize.setText("[]") # Symbol for maximize
        super().changeEvent(event)

# Example usage (optional, can be removed or commented out for library use)
# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     window = FramelessWindow()
#     # Add some dummy content to the content_layout for testing
#     test_label = QLabel("This is the content area of the FramelessWindow.")
#     test_label.setAlignment(Qt.AlignCenter)
#     window.content_layout.addWidget(test_label)
#     window.setGeometry(100,100, 800,600) # Set initial size for the example
#     window.show()
#     sys.exit(app.exec_())
