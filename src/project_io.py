import os
import json
import datetime
import shutil
import copy
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QImageReader

from . import utils
from .draggable_image_item import DraggableImageItem

class ProjectIO:
    """Handles filesystem operations for project configuration."""
    def __init__(self):
        self.current_project_name = None
        self.current_project_path = None
        self.config = {}
        self.last_saved_config = None  # Initialize last saved config

    def get_project_config_path(self, project_name_or_path):
        if os.path.isabs(project_name_or_path) and os.path.isdir(project_name_or_path):
            path = project_name_or_path
        else:
            path = os.path.join(utils.PROJECTS_BASE_DIR, project_name_or_path)
        return os.path.join(path, utils.PROJECT_CONFIG_FILENAME)

    def get_project_images_folder(self, project_name_or_path):
        if os.path.isabs(project_name_or_path) and os.path.isdir(project_name_or_path):
            path = project_name_or_path
        else:
            path = os.path.join(utils.PROJECTS_BASE_DIR, project_name_or_path)
        return os.path.join(path, utils.PROJECT_IMAGES_DIRNAME)

    def ensure_project_structure_exists(self, project_path):
        if not project_path:
            return False
        try:
            os.makedirs(project_path, exist_ok=True)
            os.makedirs(self.get_project_images_folder(project_path), exist_ok=True)
            return True
        except OSError as e:
            QMessageBox.critical(None, "Directory Error", f"Could not create project directories for {os.path.basename(project_path)}: {e}")
            return False

    def load_config_for_current_project(self):
        if not self.current_project_path:
            QMessageBox.critical(None, "Load Error", "No project path set. Cannot load configuration.")
            return None
        config_file_path = self.get_project_config_path(self.current_project_path)
        if not os.path.exists(config_file_path):
            QMessageBox.warning(None, "Load Error", f"Config file for '{self.current_project_name}' not found.")
            return None
        try:
            with open(config_file_path, 'r') as f:
                loaded_data = json.load(f)
                if not loaded_data:
                    QMessageBox.warning(None, "Load Error", "Config file is empty.")
                    return None
                return loaded_data
        except (IOError, json.JSONDecodeError) as e:
            QMessageBox.warning(None, "Load Error", f"Error loading config file{config_file_path}: {e}.")
            return None

    def save_config(self, project_path, config_data, item_map=None, status_bar=None, current_project_name=None):
        """Save configuration to file, but only if it's different from the last saved config."""
        if not project_path:
            if config_data and "project_name" in config_data:
                temp_project_path = os.path.join(utils.PROJECTS_BASE_DIR, config_data["project_name"])
                if not self.ensure_project_structure_exists(temp_project_path):
                    return False
                config_file_path = self.get_project_config_path(temp_project_path)
            else:
                QMessageBox.critical(None, "Save Error", "No project selected. Cannot save configuration.")
                return False
        else:
            if not self.ensure_project_structure_exists(project_path):
                return False
            config_file_path = self.get_project_config_path(project_path)

        if not config_data:
            print("Warning: Attempted to save empty or uninitialized configuration. Aborting save.")
            return False

        # Create a copy of config_data to avoid modifying the original
        config_to_save = config_data.copy()
        config_to_save["last_modified"] = datetime.datetime.utcnow().isoformat() + "Z"
        if "project_name" not in config_to_save and current_project_name:
            config_to_save["project_name"] = current_project_name

        # Compare with last saved config (excluding last_modified timestamp)
        if self.last_saved_config is not None:
            last_config = self.last_saved_config.copy()
            current_config = config_to_save.copy()
            
            # Remove timestamps before comparison
            last_config.pop("last_modified", None)
            current_config.pop("last_modified", None)
            
            if last_config == current_config:
                return False

        # Update dimensions for images if needed
        images_folder = self.get_project_images_folder(project_path or config_to_save.get("project_name"))
        for img_conf in config_to_save.get("images", []):
            if not img_conf.get('original_width') or not img_conf.get('original_height'):
                item = item_map.get(img_conf.get('id')) if item_map else None
                if item and isinstance(item, DraggableImageItem) and not item.pixmap().isNull():
                    img_conf['original_width'] = item.pixmap().width()
                    img_conf['original_height'] = item.pixmap().height()
                elif 'path' in img_conf and images_folder:
                    image_file_path = os.path.join(images_folder, img_conf['path'])
                    if os.path.exists(image_file_path):
                        reader = QImageReader(image_file_path)
                        if reader.canRead():
                            size = reader.size()
                            img_conf['original_width'] = size.width()
                            img_conf['original_height'] = size.height()

        try:
            with open(config_file_path, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            
            # Store the saved config
            self.last_saved_config = copy.deepcopy(config_to_save)
            
            if status_bar is not None:
                status_name = current_project_name or config_to_save.get("project_name", "Unknown Project")
                status_bar.showMessage(f"Configuration for '{status_name}' saved.", 2000)
            else:
                print(f"Configuration for '{config_to_save.get('project_name', 'Unknown Project')}' saved.")
            return True
        except IOError as e:
            QMessageBox.critical(None, "Save Error", f"Error saving config file {config_file_path}: {e}.")
            return False
        except Exception as e:
            QMessageBox.critical(None, "Save Error", f"An unexpected error occurred while saving: {e}.")
            return False

    def switch_to_project(self, project_name, is_new_project=False):
        self.current_project_name = project_name
        self.current_project_path = os.path.join(utils.PROJECTS_BASE_DIR, project_name)
        if not self.ensure_project_structure_exists(self.current_project_path):
            self.current_project_name = None
            self.current_project_path = None
            return False
        if is_new_project:
            self.config = utils.get_default_config()
            self.config["project_name"] = self.current_project_name
            if not self.save_config(self.current_project_path, self.config):
                return False
        else:
            loaded_config = self.load_config_for_current_project()
            if loaded_config is None:
                self.config = None
                return False
            self.config = loaded_config
        return True

    def copy_project_data(self, source_project_name, new_project_name):
        source_project_path = os.path.join(utils.PROJECTS_BASE_DIR, source_project_name)
        new_project_path = os.path.join(utils.PROJECTS_BASE_DIR, new_project_name)

        source_images_path = self.get_project_images_folder(source_project_path)
        new_images_path = self.get_project_images_folder(new_project_path)

        # Copy and modify project configuration file
        source_config_file = self.get_project_config_path(source_project_path)
        new_config_file = self.get_project_config_path(new_project_path)

        if not os.path.exists(source_config_file):
            QMessageBox.critical(None, "Configuration Error", f"Source project configuration file not found: {source_config_file}")
            return False

        try:
            with open(source_config_file, 'r') as f:
                config_data = json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            QMessageBox.critical(None, "Configuration Read Error", f"Error reading source project configuration '{source_config_file}': {e}")
            return False

        # Now that source config is confirmed and read, create new project directories
        try:
            os.makedirs(new_project_path, exist_ok=True)
            os.makedirs(new_images_path, exist_ok=True)
        except OSError as e:
            QMessageBox.critical(None, "Directory Creation Error", f"Could not create directories for '{new_project_name}': {e}")
            # It's debatable if we should try to remove new_project_path if new_images_path fails.
            # For now, keep it simple: if either fails, the operation fails.
            return False

        config_data["project_name"] = new_project_name
        config_data["last_modified"] = datetime.datetime.utcnow().isoformat() + "Z"
        # The lists "images" and "scene_items" should be preserved for an exact copy.

        try:
            with open(new_config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
        except (IOError, json.JSONDecodeError) as e: # json.JSONDecodeError is less likely here but good practice
            QMessageBox.critical(None, "Configuration Write Error", f"Error writing new project configuration '{new_config_file}': {e}")
            return False

        # Copy images
        if os.path.exists(source_images_path):
            try:
                for filename in os.listdir(source_images_path):
                    source_file_path = os.path.join(source_images_path, filename)
                    dest_file_path = os.path.join(new_images_path, filename)
                    if os.path.isfile(source_file_path): # Ensure it's a file, not a subdirectory
                        shutil.copy2(source_file_path, dest_file_path)
            except (IOError, shutil.Error) as e:
                QMessageBox.critical(None, "Image Copy Error", f"Error copying images to '{new_images_path}': {e}")
                return False

        return True
