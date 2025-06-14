import os
import shutil
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QHBoxLayout, QPushButton, QMessageBox, QInputDialog
)
from PyQt5.QtCore import pyqtSignal, Qt

from . import utils # Assuming utils.py is in the same directory (src)
# Or from src import utils if running from parent directory

# Placeholder for constants, will be replaced by utils.CONSTANT_NAME
# PROJECTS_BASE_DIR = "..."
# PROJECT_CONFIG_FILENAME = "..."


class ProjectManagerDialog(QDialog):
    # Signal to indicate a project might need to be reloaded or UI reset in main window
    project_deleted_signal = pyqtSignal(str)

    def __init__(self, parent=None, current_project_name=None):
        super().__init__(parent)
        self.parent_window = parent # To access main window methods if needed
        self.current_project_name_on_open = current_project_name
        self.setWindowTitle("Manage Projects")
        self.setMinimumWidth(400) # Slightly wider for new button
        self.selected_project_name = None # For loading/creating
        self.project_to_delete = None # For deletion confirmation

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Existing Projects:"))
        self.project_list_widget = QListWidget()
        self.project_list_widget.itemDoubleClicked.connect(self.load_selected_project)
        layout.addWidget(self.project_list_widget)

        self.populate_project_list()

        buttons_layout = QHBoxLayout()
        self.load_button = QPushButton("Load Selected")
        self.load_button.clicked.connect(self.load_selected_project)
        buttons_layout.addWidget(self.load_button)

        self.new_button = QPushButton("Create New Project")
        self.new_button.clicked.connect(self.create_new_project)
        buttons_layout.addWidget(self.new_button)

        self.save_as_button = QPushButton("Save Current As...")
        self.save_as_button.setObjectName("save_as_button")
        self.save_as_button.clicked.connect(self.save_project_as)
        buttons_layout.addWidget(self.save_as_button)

        self.delete_button = QPushButton("Delete Selected Project")
        self.delete_button.setStyleSheet("background-color: #dc3545; color: white;")
        self.delete_button.clicked.connect(self.confirm_delete_project)
        buttons_layout.addWidget(self.delete_button)

        layout.addLayout(buttons_layout)

        self.cancel_button = QPushButton("Close Manager")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button, 0, Qt.AlignRight)


        self.setLayout(layout)

    def save_project_as(self):
        if not self.current_project_name_on_open:
            QMessageBox.warning(self, "No Project Open", "No project is currently open to save from.")
            return

        new_project_name, ok = QInputDialog.getText(self, "Save Project As", "Enter new project name:")

        if not ok:
            return # User cancelled

        new_project_name = new_project_name.strip()
        if not new_project_name:
            QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
            return

        # Validate project name (similar to create_new_project)
        if not all(c.isalnum() or c in (' ', '_', '-') for c in new_project_name):
            QMessageBox.warning(self, "Invalid Name", "Project name can only contain letters, numbers, spaces, underscores, or hyphens.")
            return

        new_project_path = os.path.join(utils.PROJECTS_BASE_DIR, new_project_name)
        if os.path.exists(new_project_path):
            QMessageBox.warning(self, "Project Exists", f"A project named '{new_project_name}' already exists.")
            return

        # Assume self.parent_window.project_io exists and has copy_project_data
        # This part relies on future implementation of ProjectIO class
        if hasattr(self.parent_window, 'project_io') and \
           hasattr(self.parent_window.project_io, 'copy_project_data'):
            try:
                success = self.parent_window.project_io.copy_project_data(
                    self.current_project_name_on_open,
                    new_project_name
                )
                if success:
                    self.populate_project_list()
                    QMessageBox.information(self, "Project Saved", f"Project saved as '{new_project_name}' successfully.")
                else:
                    # Specific error handled by copy_project_data, generic message here
                    QMessageBox.critical(self, "Save Error", f"Failed to save project as '{new_project_name}'. Check logs for details.")
            except Exception as e:
                # Catch any unexpected errors during the copy operation itself
                QMessageBox.critical(self, "Save Error", f"An unexpected error occurred while saving the project: {e}")
        else:
            # This case is for development if project_io or method is not yet available
            QMessageBox.critical(self, "Error", "ProjectIO not available. Cannot save project.")


    def populate_project_list(self):
        self.project_list_widget.clear()
        if not os.path.exists(utils.PROJECTS_BASE_DIR):
            return
        for item_name in os.listdir(utils.PROJECTS_BASE_DIR):
            item_path = os.path.join(utils.PROJECTS_BASE_DIR, item_name)
            if os.path.isdir(item_path) and os.path.exists(os.path.join(item_path, utils.PROJECT_CONFIG_FILENAME)): # Check if it's a valid project dir
                self.project_list_widget.addItem(QListWidgetItem(item_name))

    def load_selected_project(self):
        current_item = self.project_list_widget.currentItem()
        if current_item:
            self.selected_project_name = current_item.text()
            self.accept()
        else:
            QMessageBox.warning(self, "No Project Selected", "Please select a project from the list to load.")

    def create_new_project(self):
        project_name, ok = QInputDialog.getText(self, "New Project", "Enter project name:")
        if ok and project_name:
            project_name = project_name.strip()
            if not project_name:
                QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")
                return

            # Basic validation for project name (avoid special chars that are bad for dir names)
            if not all(c.isalnum() or c in (' ', '_', '-') for c in project_name):
                QMessageBox.warning(self, "Invalid Name", "Project name can only contain letters, numbers, spaces, underscores, or hyphens.")
                return

            new_project_path = os.path.join(utils.PROJECTS_BASE_DIR, project_name)
            if os.path.exists(new_project_path):
                QMessageBox.warning(self, "Project Exists", f"A project named '{project_name}' already exists.")
                return

            self.selected_project_name = project_name
            self.accept()
        elif ok and not project_name:
             QMessageBox.warning(self, "Invalid Name", "Project name cannot be empty.")

    def confirm_delete_project(self):
        current_item = self.project_list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "No Project Selected", "Please select a project from the list to delete.")
            return

        project_name_to_delete = current_item.text()
        reply = QMessageBox.question(self, "Confirm Delete",
                                     f"Are you sure you want to permanently delete the project '{project_name_to_delete}'?\nThis action cannot be undone.",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.delete_project(project_name_to_delete)

    def delete_project(self, project_name):
        project_path_to_delete = os.path.join(utils.PROJECTS_BASE_DIR, project_name)
        try:
            shutil.rmtree(project_path_to_delete)
            QMessageBox.information(self, "Project Deleted", f"Project '{project_name}' has been deleted.")
            self.populate_project_list() # Refresh the list

            # Emit signal if the deleted project was the currently open one
            if project_name == self.current_project_name_on_open:
                self.project_deleted_signal.emit(project_name)
                # self.accept() # Close dialog after deleting current project to force main window reset
                # Or, keep dialog open if user might want to do more.
                # For now, let main window handle reset via signal.

        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Error deleting project '{project_name}': {e}")
