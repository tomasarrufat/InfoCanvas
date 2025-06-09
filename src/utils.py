import os
import json
from datetime import datetime

# Path to the repository root
BASE_SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_ROOT_DIR_NAME = "static"  # Main directory for all projects
PROJECTS_BASE_DIR = os.path.join(BASE_SCRIPT_DIR, PROJECTS_ROOT_DIR_NAME)
PROJECT_CONFIG_FILENAME = "config.json"
PROJECT_IMAGES_DIRNAME = "images"
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
# Z-values used for stacking graphics items
Z_VALUE_INFO_RECT = 1  # Info rectangles on top
Z_VALUE_IMAGE = 0      # Images below


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
                "padding": "5px"
            }
        },
        "background": {
            "width": 800,
            "height": 600,
            "color": "#DDDDDD"
        },
        "images": [],
        "info_rectangles": []
    }
