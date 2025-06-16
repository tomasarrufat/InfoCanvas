import os
import json
from datetime import datetime
from PyQt5.QtCore import Qt

# Path to the repository root
BASE_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_ROOT_DIR_NAME = "static"  # Main directory for all projects
PROJECTS_BASE_DIR = os.path.join(BASE_SCRIPT_DIR, PROJECTS_ROOT_DIR_NAME)
PROJECT_CONFIG_FILENAME = "config.json"
PROJECT_IMAGES_DIRNAME = "images"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# Z-values used for stacking graphics items
Z_VALUE_INFO_RECT = 1  # Default z for info rectangles
Z_VALUE_IMAGE = 0      # Default z for images


# --- Helper Functions ---
def allowed_file(filename):
    """Checks if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def ensure_base_projects_directory_exists():
    """Creates the base directory for all projects if it doesn't exist."""
    os.makedirs(PROJECTS_BASE_DIR, exist_ok=True)

def get_default_config():
    """Returns the default configuration structure for a new project."""
    return {
        "last_modified": datetime.utcnow().isoformat() + "Z",
        "defaults": {
            "info_rectangle_text_display": {
                "font_color": "#000000",
                "font_size": "14px",
                "background_color": "#FFFFFF",
                "box_width": 200,
                "padding": "5px",
                "vertical_alignment": "top",
                "horizontal_alignment": "left"
            }
        },
        "text_styles": [],
        "background": {
            "width": 800,
            "height": 600,
            "color": "#DDDDDD"
        },
        "images": [],
        "info_areas": []
    }

# --- Z-index Management Helpers ---

def normalize_z_indices(scene):
    """Ensures that all top-level items in the scene have consecutive z-values."""
    if not scene:
        return
    # Consider only top-level items to avoid modifying child items like text fields
    top_items = [obj for obj in scene.items() if obj.parentItem() is None]
    sorted_items = sorted(top_items, key=lambda obj: obj.zValue())
    for idx, obj in enumerate(sorted_items):
        if obj.zValue() != idx:
            obj.setZValue(idx)
        if hasattr(obj, "config_data"):
            obj.config_data["z_index"] = idx


def bring_to_front(item):
    """Moves item above all others in its scene."""
    scene = item.scene() if hasattr(item, "scene") else None
    if scene:
        max_z = max((obj.zValue() for obj in scene.items()), default=0)
        new_z = max_z + 1
        item.setZValue(new_z)
        if hasattr(item, "config_data"):
            item.config_data["z_index"] = new_z
        normalize_z_indices(scene)


def send_to_back(item):
    """Moves item below all others in its scene."""
    scene = item.scene() if hasattr(item, "scene") else None
    if scene:
        min_z = min((obj.zValue() for obj in scene.items()), default=0)
        new_z = min_z - 1
        item.setZValue(new_z)
        if hasattr(item, "config_data"):
            item.config_data["z_index"] = new_z
        normalize_z_indices(scene)


def bring_forward(item):
    """Raises item one layer up."""
    scene = item.scene() if hasattr(item, "scene") else None
    if scene:
        top_items = [obj for obj in scene.items(Qt.AscendingOrder) if obj.parentItem() is None]
        if item in top_items:
            idx = top_items.index(item)
            if idx < len(top_items) - 1:
                above = top_items[idx + 1]
                current_z = item.zValue()
                item.setZValue(above.zValue())
                above.setZValue(current_z)
                if hasattr(above, "config_data"):
                    above.config_data["z_index"] = above.zValue()
        new_z = item.zValue()
        if hasattr(item, "config_data"):
            item.config_data["z_index"] = new_z
        normalize_z_indices(scene)
    else:
        new_z = item.zValue() + 1
        item.setZValue(new_z)
        if hasattr(item, "config_data"):
            item.config_data["z_index"] = new_z


def send_backward(item):
    """Lowers item one layer down."""
    scene = item.scene() if hasattr(item, "scene") else None
    if scene:
        top_items = [obj for obj in scene.items(Qt.AscendingOrder) if obj.parentItem() is None]
        if item in top_items:
            idx = top_items.index(item)
            if idx > 0:
                below = top_items[idx - 1]
                current_z = item.zValue()
                item.setZValue(below.zValue())
                below.setZValue(current_z)
                if hasattr(below, "config_data"):
                    below.config_data["z_index"] = below.zValue()
        new_z = item.zValue()
        if hasattr(item, "config_data"):
            item.config_data["z_index"] = new_z
        normalize_z_indices(scene)
    else:
        new_z = item.zValue() - 1
        item.setZValue(new_z)
        if hasattr(item, "config_data"):
            item.config_data["z_index"] = new_z
