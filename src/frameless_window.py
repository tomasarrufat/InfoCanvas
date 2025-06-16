from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QApplication
)
from PyQt5.QtCore import Qt, QPoint, QRect, QEvent
from PyQt5.QtGui import QMouseEvent


class CustomTitleBar(QWidget):
    """Title bar with minimize, maximize, and close buttons."""
    def __init__(self, parent: QMainWindow):
        super().__init__(parent)
        self.parent = parent
        self.setFixedHeight(30)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.title = QLabel("InfoCanvas", self)
        self.title.setFixedHeight(30)
        self.title.setStyleSheet(
            "background-color: #333; color: white; padding-left: 10px; font-weight: bold;"
        )
        layout.addWidget(self.title)
        layout.addStretch()

        self.btn_minimize = QPushButton("—", self)
        self.btn_maximize = QPushButton("[]", self)
        self.btn_close = QPushButton("X", self)

        for btn in (self.btn_minimize, self.btn_maximize, self.btn_close):
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(
                "QPushButton {background-color: #333; color: white; border: none; font-weight: bold;}"
                "QPushButton:hover {background-color: #555;}"
                "QPushButton:pressed {background-color: #222;}"
            )
        self.btn_close.setStyleSheet(
            "QPushButton {background-color: #333; color: white; border: none; font-weight: bold;}"
            "QPushButton:hover {background-color: #c42b1c;}"
            "QPushButton:pressed {background-color: #9b2216;}"
        )

        layout.addWidget(self.btn_minimize)
        layout.addWidget(self.btn_maximize)
        layout.addWidget(self.btn_close)

        self.btn_close.clicked.connect(parent.close)
        self.btn_minimize.clicked.connect(parent.showMinimized)
        self.btn_maximize.clicked.connect(self.toggle_maximize)

    def toggle_maximize(self):
        if self.parent.isMaximized():
            if not hasattr(self.parent, 'normal_geometry') or self.parent.normal_geometry.isNull():
                self.parent.normal_geometry = QRect(100, 100, 800, 600)
            self.parent.showNormal()
            self.parent.setGeometry(self.parent.normal_geometry)
            self.btn_maximize.setText("[]")
        else:
            self.parent.normal_geometry = self.parent.geometry()
            self.parent.showMaximized()
            self.btn_maximize.setText("[ ]")

class FramelessWindow(QMainWindow):
    """Main window without native frame, supports dragging and resizing."""
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setMinimumSize(400, 300)

        self.normal_geometry = self.geometry()
        self.grip_size = 8
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = QPoint()
        self.resize_start_geometry = QRect()
        self._mouse_press_pos = None
        self._mouse_move_pos = None
        self._restoring_from_max = False

        self._setup_ui()

    def _setup_ui(self):
        container = QWidget(self)
        container.setStyleSheet("background-color: #333; border-radius: 5px;")
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        self.title_bar = CustomTitleBar(self)
        self.title_bar.installEventFilter(self)
        main_layout.addWidget(self.title_bar)

        self.content = QWidget(self)
        self.content_layout = QVBoxLayout(self.content)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.content)

        outer = QWidget(self)
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(container)
        super().setCentralWidget(outer)

    def set_content_widget(self, widget: QWidget):
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.takeAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        if widget:
            self.content_layout.addWidget(widget)

    # --- Title bar movement ---
    def eventFilter(self, obj, event):
        if obj is self.title_bar:
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                self._mouse_press_pos = event.globalPos()
                self._mouse_move_pos = event.globalPos()
                if self.isMaximized():
                    self._restoring_from_max = True
                return True
            if event.type() == QEvent.MouseMove and event.buttons() == Qt.LeftButton:
                if self._restoring_from_max:
                    self.title_bar.toggle_maximize()
                    ratio = event.x() / self.title_bar.width()
                    new_x = event.globalPos().x() - self.normal_geometry.width() * ratio
                    self.move(int(new_x), event.globalPos().y() - self.title_bar.height() // 2)
                    self._restoring_from_max = False
                    self._mouse_move_pos = event.globalPos()
                    return True
                if not self.isMaximized():
                    screen_rect = QApplication.desktop().availableGeometry(self)
                    if event.globalPos().y() <= screen_rect.top():
                        self.title_bar.toggle_maximize()
                        return True
                    move_delta = event.globalPos() - self._mouse_move_pos
                    self.move(self.pos() + move_delta)
                    self._mouse_move_pos = event.globalPos()
                    return True
            if event.type() in (QEvent.MouseButtonRelease, QEvent.MouseButtonDblClick):
                if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                    self.title_bar.toggle_maximize()
                self._mouse_press_pos = None
                self._mouse_move_pos = None
                self._restoring_from_max = False
                return True
        return super().eventFilter(obj, event)

    # --- Resizing ---
    def check_resize_edge(self, pos):
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()
        on_left = 0 <= x < self.grip_size
        on_right = w - self.grip_size <= x < w
        on_top = 0 <= y < self.grip_size
        on_bottom = h - self.grip_size <= y < h
        if on_top and on_left:
            return Qt.TopLeftCorner
        if on_top and on_right:
            return Qt.TopRightCorner
        if on_bottom and on_left:
            return Qt.BottomLeftCorner
        if on_bottom and on_right:
            return Qt.BottomRightCorner
        if on_left:
            return Qt.LeftEdge
        if on_right:
            return Qt.RightEdge
        if on_top:
            return Qt.TopEdge
        if on_bottom:
            return Qt.BottomEdge
        return None

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton and not self.isMaximized():
            self.resize_edge = self.check_resize_edge(event.pos())
            if self.resize_edge:
                self.resizing = True
                self.resize_start_pos = event.globalPos()
                self.resize_start_geometry = self.geometry()
                event.accept()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.resizing = False
            self.resize_edge = None
            self.unsetCursor()
            event.accept()
        super().mouseReleaseEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.resizing and not self.isMaximized():
            delta = event.globalPos() - self.resize_start_pos
            geom = QRect(self.resize_start_geometry)
            if self.resize_edge in (Qt.LeftEdge, Qt.TopLeftCorner, Qt.BottomLeftCorner):
                geom.setLeft(geom.left() + delta.x())
            if self.resize_edge in (Qt.RightEdge, Qt.TopRightCorner, Qt.BottomRightCorner):
                geom.setRight(geom.right() + delta.x())
            if self.resize_edge in (Qt.TopEdge, Qt.TopLeftCorner, Qt.TopRightCorner):
                geom.setTop(geom.top() + delta.y())
            if self.resize_edge in (Qt.BottomEdge, Qt.BottomLeftCorner, Qt.BottomRightCorner):
                geom.setBottom(geom.bottom() + delta.y())
            if geom.width() < self.minimumWidth():
                if self.resize_edge in (Qt.LeftEdge, Qt.TopLeftCorner, Qt.BottomLeftCorner):
                    geom.setLeft(geom.right() - self.minimumWidth())
            if geom.height() < self.minimumHeight():
                if self.resize_edge in (Qt.TopEdge, Qt.TopLeftCorner, Qt.TopRightCorner):
                    geom.setTop(geom.bottom() - self.minimumHeight())
            self.setGeometry(geom)
        elif not self.isMaximized():
            edge = self.check_resize_edge(event.pos())
            if edge in (Qt.TopLeftCorner, Qt.BottomRightCorner):
                self.setCursor(Qt.SizeFDiagCursor)
            elif edge in (Qt.TopRightCorner, Qt.BottomLeftCorner):
                self.setCursor(Qt.SizeBDiagCursor)
            elif edge in (Qt.LeftEdge, Qt.RightEdge):
                self.setCursor(Qt.SizeHorCursor)
            elif edge in (Qt.TopEdge, Qt.BottomEdge):
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.unsetCursor()
        super().mouseMoveEvent(event)

    def changeEvent(self, event):
        if event.type() == QEvent.WindowStateChange:
            if self.isMaximized():
                if not hasattr(self, 'normal_geometry') or self.normal_geometry.isNull():
                    self.normal_geometry = self.geometry()
            elif not self.isMaximized():
                if hasattr(self, 'normal_geometry') and not self.normal_geometry.isNull():
                    self.setGeometry(self.normal_geometry)
        super().changeEvent(event)
