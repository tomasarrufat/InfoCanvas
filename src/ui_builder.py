import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QComboBox, QSpinBox, QTextEdit, QGraphicsScene,
    QGraphicsView, QDoubleSpinBox, QMessageBox, QStackedLayout, QCheckBox,
    QScrollArea, QStatusBar
)

# When running as root (e.g., in certain test environments), Qt WebEngine
# requires sandboxing to be disabled.  Set the environment variables now so that
# if the real WebEngine is used later it won't fail.
if os.geteuid() == 0:
    os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")
    os.environ.setdefault("QTWEBENGINE_DISABLE_SANDBOX", "1")

# Provide a lightweight stub for QWebEngineView.  The real class will be
# imported on demand in ``build`` if the environment allows it.
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

        # Main content area widget and its layout
        main_content_area_widget = QWidget()
        main_content_layout = QHBoxLayout(main_content_area_widget)
        main_content_layout.setContentsMargins(0, 0, 0, 0) # No margin for this layout
        main_content_layout.setSpacing(5) # Spacing between controls and canvas

        # Controls widget (main container for the left panel)
        app.controls_widget = QWidget()
        app.controls_widget.setFixedWidth(350)
        main_content_layout.addWidget(app.controls_widget)

        # Outer layout for app.controls_widget (to hold scrollArea and status_label)
        outer_controls_layout = QVBoxLayout(app.controls_widget)
        outer_controls_layout.setContentsMargins(0,0,0,0) # No margins for the outer layout itself
        outer_controls_layout.setSpacing(0) # No spacing for the outer layout

        # Scroll Area for the actual controls
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.NoFrame) # Optional: remove scroll area border

        scroll_area_content_widget = QWidget() # This widget will contain app.controls_layout
        scroll_area.setWidget(scroll_area_content_widget)

        # The existing app.controls_layout is now for scroll_area_content_widget
        app.controls_layout = QVBoxLayout(scroll_area_content_widget)
        app.controls_layout.setContentsMargins(5,5,5,5) # Keep existing margins for content
        app.controls_layout.setSpacing(5)     # Keep existing spacing for content

        # Add scroll_area to the outer_controls_layout, making it expand
        outer_controls_layout.addWidget(scroll_area, 1) # The '1' makes it take available space

        # Mode switcher
        mode_group = QWidget()
        mode_layout = QHBoxLayout(mode_group)
        mode_layout.addWidget(QLabel("Mode:"))
        app.mode_switcher = QComboBox()
        app.mode_switcher.addItems(["Edit Mode", "View Mode"])
        app.mode_switcher.currentTextChanged.connect(app.on_mode_changed)
        mode_layout.addWidget(app.mode_switcher)
        app.controls_layout.addWidget(mode_group)

        # Edit mode controls container
        app.edit_mode_controls_widget = QWidget()
        edit_mode_layout = QVBoxLayout(app.edit_mode_controls_widget)
        edit_mode_layout.setContentsMargins(0,0,0,0)
        edit_mode_layout.setSpacing(5)


        # Background controls
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

        app.connect_rects_button = QPushButton("Connect Selected Areas")
        app.connect_rects_button.clicked.connect(app.on_connect_disconnect_clicked)
        app.connect_rects_button.setVisible(False)
        rect_props_layout.addWidget(app.connect_rects_button)

        # Container for individual info area controls so it can be hidden when multiple items are selected
        app.info_rect_detail_widget = QWidget()
        detail_layout = QVBoxLayout(app.info_rect_detail_widget)

        app.info_rect_text_input = QTextEdit()
        app.info_rect_text_input.setPlaceholderText("Enter information here...")
        app.info_rect_text_input.setFixedHeight(80)
        app.info_rect_text_input.textChanged.connect(app.update_selected_rect_text)
        detail_layout.addWidget(app.info_rect_text_input)

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
        style_selection_layout.addWidget(QLabel("Area Style:"))
        app.rect_style_combo = QComboBox()
        app.rect_style_combo.currentIndexChanged.connect(
            lambda: app.text_style_manager.handle_style_selection(app.rect_style_combo.currentText())
        )
        style_selection_layout.addWidget(app.rect_style_combo)
        app.rect_save_style_button = QPushButton("Save Current as Style")
        app.rect_save_style_button.clicked.connect(app.text_style_manager.save_current_item_style)

        detail_layout.addWidget(text_format_group)

        rect_width_layout = QHBoxLayout()
        rect_width_layout.addWidget(QLabel("Width (px):"))
        app.info_rect_width_input = QSpinBox()
        from .info_area_item import InfoAreaItem
        app.info_rect_width_input.setRange(InfoAreaItem.MIN_WIDTH, 2000)
        app.info_rect_width_input.valueChanged.connect(app.update_selected_rect_dimensions)
        rect_width_layout.addWidget(app.info_rect_width_input)
        detail_layout.addLayout(rect_width_layout)

        rect_height_layout = QHBoxLayout()
        rect_height_layout.addWidget(QLabel("Height (px):"))
        app.info_rect_height_input = QSpinBox()
        app.info_rect_height_input.setRange(InfoAreaItem.MIN_HEIGHT, 2000)
        app.info_rect_height_input.valueChanged.connect(app.update_selected_rect_dimensions)
        rect_height_layout.addWidget(app.info_rect_height_input)
        detail_layout.addLayout(rect_height_layout)

        # Angle control
        angle_layout = QHBoxLayout()
        angle_layout.addWidget(QLabel("Angle:"))
        app.info_rect_angle_input = QDoubleSpinBox()
        app.info_rect_angle_input.setRange(-360.0, 360.0)
        app.info_rect_angle_input.setSingleStep(1.0)
        app.info_rect_angle_input.setValue(0.0)
        app.info_rect_angle_input.valueChanged.connect(app.update_selected_item_angle)
        angle_layout.addWidget(app.info_rect_angle_input)
        detail_layout.addLayout(angle_layout)

        shape_layout = QHBoxLayout()
        shape_layout.addWidget(QLabel("Area Shape:"))
        app.area_shape_combo = QComboBox()
        app.area_shape_combo.addItems(["Rectangle", "Ellipse"])
        app.area_shape_combo.currentTextChanged.connect(app.update_selected_area_shape)
        shape_layout.addWidget(app.area_shape_combo)
        detail_layout.addLayout(shape_layout)

        app.rect_show_on_hover_checkbox = QCheckBox("Show info area on hover only")
        app.rect_show_on_hover_checkbox.stateChanged.connect(app.update_selected_rect_show_on_hover)
        detail_layout.addWidget(app.rect_show_on_hover_checkbox)

        app.rect_show_on_hover_connected_checkbox = QCheckBox("Show info area on hover on connected")
        # We will connect its stateChanged signal later in app.py
        detail_layout.addWidget(app.rect_show_on_hover_connected_checkbox)
        app.rect_show_on_hover_connected_checkbox.setVisible(False) # Initially hidden

        area_color_layout = QHBoxLayout()
        area_color_layout.addWidget(QLabel("Area Color:"))
        app.rect_area_color_button = QPushButton("Select Color")
        app.rect_area_color_button.clicked.connect(app.choose_info_area_color)
        area_color_layout.addWidget(app.rect_area_color_button)
        detail_layout.addLayout(area_color_layout)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        app.rect_area_opacity_spin = QDoubleSpinBox()
        app.rect_area_opacity_spin.setRange(0.0, 1.0)
        app.rect_area_opacity_spin.setSingleStep(0.05)
        app.rect_area_opacity_spin.setDecimals(2)
        app.rect_area_opacity_spin.valueChanged.connect(app.update_selected_area_opacity)
        opacity_layout.addWidget(app.rect_area_opacity_spin)
        detail_layout.addLayout(opacity_layout)

        detail_layout.addLayout(style_selection_layout)
        detail_layout.addWidget(app.rect_save_style_button)

        app.delete_info_rect_button = QPushButton("Delete Selected Info Area")
        app.delete_info_rect_button.setStyleSheet("background-color: #dc3545; color: white;")
        app.delete_info_rect_button.clicked.connect(app.delete_selected_info_rect)
        detail_layout.addWidget(app.delete_info_rect_button)

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
        detail_layout.addLayout(rect_layer_layout_vertical)

        rect_props_layout.addWidget(app.info_rect_detail_widget)

        app.line_properties_widget = QWidget()
        line_props_layout = QVBoxLayout(app.line_properties_widget)
        thickness_layout = QHBoxLayout()
        thickness_layout.addWidget(QLabel("Thickness:"))
        app.line_thickness_spin = QSpinBox()
        app.line_thickness_spin.setRange(1, 20)
        app.line_thickness_spin.valueChanged.connect(app.update_selected_line_thickness)
        thickness_layout.addWidget(app.line_thickness_spin)
        line_props_layout.addLayout(thickness_layout)

        z_layout = QHBoxLayout()
        z_layout.addWidget(QLabel("Z-Index:"))
        app.line_z_index_spin = QSpinBox()
        app.line_z_index_spin.setRange(-1000, 1000)
        app.line_z_index_spin.valueChanged.connect(app.update_selected_line_z_index)
        z_layout.addWidget(app.line_z_index_spin)
        line_props_layout.addLayout(z_layout)

        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(QLabel("Opacity:"))
        app.line_opacity_spin = QDoubleSpinBox()
        app.line_opacity_spin.setRange(0.0, 1.0)
        app.line_opacity_spin.setSingleStep(0.05)
        app.line_opacity_spin.setDecimals(2)
        app.line_opacity_spin.valueChanged.connect(app.update_selected_line_opacity)
        opacity_layout.addWidget(app.line_opacity_spin)
        line_props_layout.addLayout(opacity_layout)

        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Line Color:"))
        app.line_color_button = QPushButton("Select Color")
        app.line_color_button.clicked.connect(app.choose_line_color)
        color_layout.addWidget(app.line_color_button)
        line_props_layout.addLayout(color_layout)

        style_layout = QHBoxLayout()
        style_layout.addWidget(QLabel("Line Style:"))
        app.line_style_combo = QComboBox()
        app.line_style_combo.currentIndexChanged.connect(
            lambda: app.line_style_manager.handle_style_selection(app.line_style_combo.currentText())
        )
        style_layout.addWidget(app.line_style_combo)
        line_props_layout.addLayout(style_layout)

        app.line_save_style_button = QPushButton("Save Current as Style")
        app.line_save_style_button.clicked.connect(app.line_style_manager.save_current_item_style)
        line_props_layout.addWidget(app.line_save_style_button)

        rect_props_layout.addWidget(app.line_properties_widget)
        app.info_rect_properties_widget.setVisible(False)
        app.line_properties_widget.setVisible(False)
        rect_layout.addWidget(app.info_rect_properties_widget)
        rect_layout.addWidget(app.line_properties_widget)
        edit_mode_layout.addWidget(rect_group)

        app.controls_layout.addWidget(app.edit_mode_controls_widget)

        app.view_mode_message_label = QLabel("<i>Hover over areas on the image to see information.</i>")
        app.view_mode_message_label.setWordWrap(True)
        app.controls_layout.addWidget(app.view_mode_message_label)

        app.export_html_button = QPushButton("Export to HTML")
        app.export_html_button.clicked.connect(lambda checked=False: app.export_to_html())
        app.controls_layout.addWidget(app.export_html_button) # This is the one shown in view mode

        # QStatusBar (modern status bar, replaces status_label)
        from PyQt5.QtWidgets import QStatusBar
        app.status_bar = QStatusBar()
        app.status_bar.setObjectName("StatusBar")
        app.status_bar.setFixedHeight(25)
        app.status_bar.setStyleSheet("""
            QStatusBar#StatusBar {
                background-color: #222;
                color: white;
                padding-left: 10px;
                font-size: 9pt;
                border-top: 1px solid #444;
            }
        """)
        app.status_bar.showMessage(f"Project '{app.current_project_name}' loaded. Ready.")
        # Add status_bar to the outer_controls_layout, after the scroll_area
        outer_controls_layout.addWidget(app.status_bar)

        # Central widget (canvas area)
        central_widget = QWidget()
        app.central_layout = QStackedLayout(central_widget)
        app.central_layout.setContentsMargins(0,0,0,0)

        app.scene = QGraphicsScene(app)
        app.scene.setBackgroundBrush(QBrush(QColor(app.config['background']['color'])))
        app.scene.setSceneRect(0, 0,
                               app.config['background']['width'],
                               app.config['background']['height'])
        app.scene.selectionChanged.connect(app.on_scene_selection_changed)
        app.scene.parent_window = app # For item context menu

        app.view = QGraphicsView(app.scene)
        app.view.setRenderHint(QPainter.SmoothPixmapTransform)
        app.view.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        app.central_layout.addWidget(app.view)

        webengine_disabled = os.environ.get("QT_QPA_PLATFORM") == "offscreen" or \
            os.environ.get("INFOCANVAS_NO_WEBENGINE") == "1"
        if not webengine_disabled:
            try:
                from PyQt5.QtWebEngineWidgets import QWebEngineView as RealWebView
                app.web_view = RealWebView()
            except Exception:
                webengine_disabled = True
        if webengine_disabled:
            app.web_view = QWebEngineView()
        app.central_layout.addWidget(app.web_view)
        app.central_layout.setCurrentWidget(app.view)

        main_content_layout.addWidget(central_widget, 1) # Add central_widget with stretch factor

        # Add the main_content_area_widget to the FramelessWindow's content_layout
        app.content_layout.addWidget(main_content_area_widget)
