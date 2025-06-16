from PyQt5.QtWidgets import (
    QWidget, QDockWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QTextEdit, QAction, QGraphicsScene,
    QGraphicsView, QDoubleSpinBox, QMessageBox, QStackedLayout, QCheckBox
)
try:
    from PyQt5.QtWebEngineWidgets import QWebEngineView
except Exception:  # pragma: no cover - optional dependency
    class QWebEngineView(QWidget):
        def setHtml(self, *args, **kwargs):
            pass
from PyQt5.QtGui import QColor, QBrush, QPainter
from PyQt5.QtCore import Qt

class UIBuilder:
    """Builds the main UI for :class:`InfoCanvasApp`."""

    def __init__(self, app):
        self.app = app

    def build(self):
        app = self.app
        if not app.current_project_name or not app.config:
            QMessageBox.critical(app, "UI Setup Error",
                                 "Cannot setup UI without a loaded project and configuration.")
            return

        app.scene = QGraphicsScene(app)
        app.scene.setBackgroundBrush(QBrush(QColor(app.config['background']['color'])))
        app.scene.setSceneRect(0, 0,
                               app.config['background']['width'],
                               app.config['background']['height'])
        app.scene.selectionChanged.connect(app.on_scene_selection_changed)
        app.scene.parent_window = app

        # Central widget with stacked layout to switch between graphics and web views
        central_widget = QWidget()
        app.central_layout = QStackedLayout(central_widget)

        app.view = QGraphicsView(app.scene)
        app.view.setRenderHint(QPainter.SmoothPixmapTransform)
        # Ensure the view starts at the upper-left corner of the scene
        app.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        app.central_layout.addWidget(app.view)

        app.web_view = QWebEngineView()
        app.central_layout.addWidget(app.web_view)
        app.central_layout.setCurrentWidget(app.view)
        app.setCentralWidget(central_widget)

        app.controls_dock = QDockWidget("Controls", app)
        app.controls_dock.setFixedWidth(350)
        app.controls_dock.setFeatures(QDockWidget.DockWidgetMovable)

        app.controls_widget = QWidget()
        app.controls_layout = QVBoxLayout(app.controls_widget)
        app.controls_dock.setWidget(app.controls_widget)
        app.addDockWidget(Qt.LeftDockWidgetArea, app.controls_dock)

        mode_group = QWidget()
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("Mode:"))
        app.mode_switcher = QComboBox()
        app.mode_switcher.addItems(["Edit Mode", "View Mode"])
        app.mode_switcher.currentTextChanged.connect(app.on_mode_changed)
        mode_layout.addWidget(app.mode_switcher)
        app.controls_layout.addWidget(mode_group)

        app.edit_mode_controls_widget = QWidget()
        edit_mode_layout = QVBoxLayout(app.edit_mode_controls_widget)

        bg_group = QWidget()
        bg_layout = QVBoxLayout(bg_group)
        bg_layout.addWidget(QLabel("<b>Background:</b>"))
        app.bg_color_button = QPushButton("Choose Color")
        app.bg_color_button.clicked.connect(app.choose_bg_color)
        bg_layout.addWidget(app.bg_color_button)

        bg_width_layout = QHBoxLayout()
        bg_width_layout.addWidget(QLabel("Width (px):"))
        app.bg_width_input = QSpinBox()
        app.bg_width_input.setRange(100, 10000)
        app.bg_width_input.valueChanged.connect(app.update_bg_dimensions)
        bg_width_layout.addWidget(app.bg_width_input)
        bg_layout.addLayout(bg_width_layout)

        bg_height_layout = QHBoxLayout()
        bg_height_layout.addWidget(QLabel("Height (px):"))
        app.bg_height_input = QSpinBox()
        app.bg_height_input.setRange(100, 10000)
        app.bg_height_input.valueChanged.connect(app.update_bg_dimensions)
        bg_height_layout.addWidget(app.bg_height_input)
        bg_layout.addLayout(bg_height_layout)

        edit_mode_layout.addWidget(bg_group)

        img_group = QWidget()
        img_layout = QVBoxLayout(img_group)
        img_layout.addWidget(QLabel("<b>Images:</b>"))
        app.upload_image_button = QPushButton("Upload Image")
        app.upload_image_button.clicked.connect(app.upload_image)
        img_layout.addWidget(app.upload_image_button)

        app.image_properties_widget = QWidget()
        img_props_layout = QVBoxLayout(app.image_properties_widget)
        img_props_layout.addWidget(QLabel("<u>Selected Image Properties:</u>"))

        img_scale_layout = QHBoxLayout()
        img_scale_layout.addWidget(QLabel("Scale:"))
        app.img_scale_input = QDoubleSpinBox()
        app.img_scale_input.setRange(0.01, 20.0)
        app.img_scale_input.setSingleStep(0.05)
        app.img_scale_input.setDecimals(2)
        app.img_scale_input.valueChanged.connect(app.update_selected_image_scale)
        img_scale_layout.addWidget(app.img_scale_input)
        img_props_layout.addLayout(img_scale_layout)

        app.delete_image_button = QPushButton("Delete Selected Image")
        app.delete_image_button.setStyleSheet("background-color: #dc3545; color: white;")
        app.delete_image_button.clicked.connect(app.delete_selected_image)
        img_props_layout.addWidget(app.delete_image_button)

        img_layer_layout_line1 = QHBoxLayout()
        app.img_to_front = QPushButton("Bring to Front")
        app.img_to_front.clicked.connect(app.bring_to_front)
        img_layer_layout_line1.addWidget(app.img_to_front)

        app.img_forward = QPushButton("Bring Forward")
        app.img_forward.clicked.connect(app.bring_forward)
        img_layer_layout_line1.addWidget(app.img_forward)

        img_layer_layout_line2 = QHBoxLayout()
        app.img_backward = QPushButton("Send Backward")
        app.img_backward.clicked.connect(app.send_backward)
        img_layer_layout_line2.addWidget(app.img_backward)

        app.img_to_back = QPushButton("Send to Back")
        app.img_to_back.clicked.connect(app.send_to_back)
        img_layer_layout_line2.addWidget(app.img_to_back)

        img_layer_layout_vertical = QVBoxLayout()
        img_layer_layout_vertical.addLayout(img_layer_layout_line1)
        img_layer_layout_vertical.addLayout(img_layer_layout_line2)
        img_props_layout.addLayout(img_layer_layout_vertical)
        app.image_properties_widget.setVisible(False)
        img_layout.addWidget(app.image_properties_widget)
        edit_mode_layout.addWidget(img_group)

        rect_group = QWidget()
        rect_layout = QVBoxLayout(rect_group)
        rect_layout.addWidget(QLabel("<b>Info Areas:</b>"))
        app.add_info_rect_button = QPushButton("Add Info Area")
        app.add_info_rect_button.clicked.connect(app.add_info_rectangle)
        rect_layout.addWidget(app.add_info_rect_button)

        app.info_rect_properties_widget = QWidget()
        rect_props_layout = QVBoxLayout(app.info_rect_properties_widget)

        app.align_horizontal_button = QPushButton("Align Items Horizontally")
        app.align_horizontal_button.clicked.connect(app.align_selected_rects_horizontally)
        app.align_horizontal_button.setVisible(False)
        rect_props_layout.addWidget(app.align_horizontal_button)

        app.align_vertical_button = QPushButton("Align Items Vertically")
        app.align_vertical_button.clicked.connect(app.align_selected_rects_vertically)
        app.align_vertical_button.setVisible(False)
        rect_props_layout.addWidget(app.align_vertical_button)

        app.info_rect_text_input = QTextEdit()
        app.info_rect_text_input.setPlaceholderText("Enter information here...")
        app.info_rect_text_input.setFixedHeight(80)
        app.info_rect_text_input.textChanged.connect(app.update_selected_rect_text)
        rect_props_layout.addWidget(app.info_rect_text_input)

        text_format_group = QWidget()
        text_format_layout = QVBoxLayout(text_format_group)
        text_format_layout.addWidget(QLabel("<u>Text Formatting:</u>"))

        h_align_layout = QHBoxLayout()
        h_align_layout.addWidget(QLabel("Horizontal Align:"))
        app.rect_h_align_combo = QComboBox()
        app.rect_h_align_combo.addItems(["Left", "Center", "Right"])
        # Changed: Connect to text_style_manager.handle_format_change
        app.rect_h_align_combo.currentTextChanged.connect(app.text_style_manager.handle_format_change)
        h_align_layout.addWidget(app.rect_h_align_combo)
        text_format_layout.addLayout(h_align_layout)

        v_align_layout = QHBoxLayout()
        v_align_layout.addWidget(QLabel("Vertical Align:"))
        app.rect_v_align_combo = QComboBox()
        app.rect_v_align_combo.addItems(["Top", "Center", "Bottom"])
        # Changed: Connect to text_style_manager.handle_format_change
        app.rect_v_align_combo.currentTextChanged.connect(app.text_style_manager.handle_format_change)
        v_align_layout.addWidget(app.rect_v_align_combo)
        text_format_layout.addLayout(v_align_layout)

        font_size_layout = QHBoxLayout()
        font_size_layout.addWidget(QLabel("Font Size:"))
        app.rect_font_size_combo = QComboBox()
        common_font_sizes = [
            "8", "9", "10", "11", "12", "14", "16", "18", "20", "24",
            "28", "32", "36", "48", "72"
        ]
        app.rect_font_size_combo.addItems(common_font_sizes)
        app.rect_font_size_combo.setEditable(True)
        app.rect_font_size_combo.lineEdit().setPlaceholderText("px")
        # Changed: Connect to text_style_manager.handle_format_change. Using currentTextChanged for consistency.
        app.rect_font_size_combo.currentTextChanged.connect(app.text_style_manager.handle_format_change)
        font_size_layout.addWidget(app.rect_font_size_combo)
        text_format_layout.addLayout(font_size_layout)


        font_color_layout = QHBoxLayout()
        font_color_layout.addWidget(QLabel("Font Color:"))
        app.rect_font_color_button = QPushButton("Select Color")
        app.rect_font_color_button.setToolTip("Click to select text color")
        app.rect_font_color_button.setStyleSheet("background-color: #000000; color: white;")
        # Changed: Connect to text_style_manager.handle_font_color_change
        app.rect_font_color_button.clicked.connect(app.text_style_manager.handle_font_color_change)
        font_color_layout.addWidget(app.rect_font_color_button)
        text_format_layout.addLayout(font_color_layout)

        style_selection_layout = QHBoxLayout()
        style_selection_layout.addWidget(QLabel("Text Style:"))
        app.rect_style_combo = QComboBox()
        # Changed: Connect to text_style_manager.handle_style_selection
        app.rect_style_combo.currentIndexChanged.connect(
            lambda: app.text_style_manager.handle_style_selection(app.rect_style_combo.currentText())
        )
        style_selection_layout.addWidget(app.rect_style_combo)
        text_format_layout.addLayout(style_selection_layout)

        app.rect_save_style_button = QPushButton("Save Current as Style") # Renamed from save_style_button for clarity
        # Changed: Connect to text_style_manager.save_current_item_style
        app.rect_save_style_button.clicked.connect(app.text_style_manager.save_current_item_style)
        text_format_layout.addWidget(app.rect_save_style_button)

        rect_props_layout.addWidget(text_format_group)

        rect_width_layout = QHBoxLayout()
        rect_width_layout.addWidget(QLabel("Width (px):"))
        app.info_rect_width_input = QSpinBox()
        from .info_area_item import InfoAreaItem
        app.info_rect_width_input.setRange(InfoAreaItem.MIN_WIDTH, 2000)
        app.info_rect_width_input.valueChanged.connect(app.update_selected_rect_dimensions)
        rect_width_layout.addWidget(app.info_rect_width_input)
        rect_props_layout.addLayout(rect_width_layout)

        rect_height_layout = QHBoxLayout()
        rect_height_layout.addWidget(QLabel("Height (px):"))
        app.info_rect_height_input = QSpinBox()
        app.info_rect_height_input.setRange(InfoAreaItem.MIN_HEIGHT, 2000)
        app.info_rect_height_input.valueChanged.connect(app.update_selected_rect_dimensions)
        rect_height_layout.addWidget(app.info_rect_height_input)
        rect_props_layout.addLayout(rect_height_layout)

        shape_layout = QHBoxLayout()
        shape_layout.addWidget(QLabel("Area Shape:"))
        app.area_shape_combo = QComboBox()
        app.area_shape_combo.addItems(["Rectangle", "Ellipse"])
        app.area_shape_combo.currentTextChanged.connect(app.update_selected_area_shape)
        shape_layout.addWidget(app.area_shape_combo)
        rect_props_layout.addLayout(shape_layout)

        app.rect_show_on_hover_checkbox = QCheckBox("Show text on hover only")
        app.rect_show_on_hover_checkbox.stateChanged.connect(app.update_selected_rect_show_on_hover)
        rect_props_layout.addWidget(app.rect_show_on_hover_checkbox)

        app.delete_info_rect_button = QPushButton("Delete Selected Info Area")
        app.delete_info_rect_button.setStyleSheet("background-color: #dc3545; color: white;")
        app.delete_info_rect_button.clicked.connect(app.delete_selected_info_rect)
        rect_props_layout.addWidget(app.delete_info_rect_button)

        rect_layer_layout_line1 = QHBoxLayout()
        app.rect_to_front = QPushButton("Bring to Front")
        app.rect_to_front.clicked.connect(app.bring_to_front)
        rect_layer_layout_line1.addWidget(app.rect_to_front)

        app.rect_forward = QPushButton("Bring Forward")
        app.rect_forward.clicked.connect(app.bring_forward)
        rect_layer_layout_line1.addWidget(app.rect_forward)

        rect_layer_layout_line2 = QHBoxLayout()
        app.rect_backward = QPushButton("Send Backward")
        app.rect_backward.clicked.connect(app.send_backward)
        rect_layer_layout_line2.addWidget(app.rect_backward)

        app.rect_to_back = QPushButton("Send to Back")
        app.rect_to_back.clicked.connect(app.send_to_back)
        rect_layer_layout_line2.addWidget(app.rect_to_back)

        rect_layer_layout_vertical = QVBoxLayout()
        rect_layer_layout_vertical.addLayout(rect_layer_layout_line1)
        rect_layer_layout_vertical.addLayout(rect_layer_layout_line2)
        rect_props_layout.addLayout(rect_layer_layout_vertical)
        app.info_rect_properties_widget.setVisible(False)
        rect_layout.addWidget(app.info_rect_properties_widget)
        edit_mode_layout.addWidget(rect_group)

        app.controls_layout.addWidget(app.edit_mode_controls_widget)

        app.view_mode_message_label = QLabel("<i>Hover over areas on the image to see information.</i>")
        app.view_mode_message_label.setWordWrap(True)
        app.controls_layout.addWidget(app.view_mode_message_label)

        app.export_html_button = QPushButton("Export to HTML")
        app.export_html_button.clicked.connect(lambda checked=False: app.export_to_html())
        app.controls_layout.addWidget(app.export_html_button)
        app.controls_layout.addStretch()

        menubar = app.menuBar()
        file_menu = menubar.addMenu('&File')
        project_action = QAction('&Manage Projects...', app)
        project_action.triggered.connect(app._show_project_manager_dialog)
        file_menu.addAction(project_action)
        file_menu.addSeparator()
        save_action = QAction('&Save Configuration', app)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(lambda: app.save_config())
        file_menu.addAction(save_action)
        export_action = QAction('&Export to HTML', app)
        export_action.triggered.connect(lambda checked=False: app.export_to_html())
        file_menu.addAction(export_action)
        exit_action = QAction('&Exit', app)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(app.close)
        file_menu.addAction(exit_action)

        app.statusBar().showMessage(
            f"Project '{app.current_project_name}' loaded. Ready.")
