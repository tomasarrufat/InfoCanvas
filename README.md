# Interactive Image Tool

## Basic Purpose

This tool is a desktop application built with PyQt5 for creating interactive learning materials. Users can create projects, add images to a canvas, position and scale them, and then define rectangular "hotspot" areas over these images. In "View Mode", hovering over these hotspots displays associated explanatory text. This is useful for applications like labeling anatomical diagrams, explaining parts of a machine, or creating simple interactive guides.

## File Structure

The project follows this basic structure:

```
/interactive-image-tool/
|-- app.py                 # Main Python PyQt5 application
|-- requirements.txt       # Python package dependencies
|-- README.md              # This file
|-- /static/               # Root directory for project-specific files
|   |-- /<project_name>/   # Folder for a specific project
|   |   |-- config.json    # Stores background, image, and hotspot data for this project
|   |   |-- /images/       # Stores images uploaded for this project
|   |   |   |-- (uploaded images will appear here)
|-- /doc/                  # Contains documentation like toolRequirements.md
|   |-- toolRequirements.md
```

-   **`app.py`**: Contains the main PyQt5 application logic, including UI, event handling, and project management.
-   **`requirements.txt`**: Lists the Python packages needed to run the application (e.g., PyQt5).
-   **`README.md`**: This file.
-   **`static/`**: This directory serves as the root for storing all project-specific data.
    -   **`/<project_name>/`**: Each sub-directory within `static/` represents an individual project.
        -   **`config.json`**: Located within each project's folder, this file stores the specific configuration for that project, including background settings, image details (paths, positions, scales), and info rectangle data.
        -   **`images/`**: Also within each project's folder, this sub-directory holds all images uploaded by the user for that particular project.
-   **`doc/`**: Contains additional documentation for the project.
    -   **`toolRequirements.md`**: Describes the (original) requirements for the tool.

## Installation

1.  **Clone or Download:** Get the project files onto your local machine.
    
2.  **Navigate:** Open a terminal or command prompt and navigate into the project's root directory (`/interactive-image-tool/`).
    
3.  **Create Virtual Environment (Recommended):**
    
    ```bash
    python -m venv venv
    # On Windows:
    # venv\Scripts\activate  
    # On macOS/Linux:
    # source venv/bin/activate 
    ```
    Activate the virtual environment. For example:
    - On Windows: `venv\Scripts\activate`
    - On macOS/Linux: `source venv/bin/activate`
    
4.  **Install Requirements:** Install the necessary Python packages using pip and the `requirements.txt` file. This will include PyQt5 and other dependencies.
    
    ```bash
    pip install -r requirements.txt
    ```
    *(Note: Ensure `PyQt5` is listed in your `requirements.txt` file.)*

## Usage

1.  **Run the Application:**
    -   Ensure your virtual environment (if created) is activated.
    -   Navigate to the project's root directory in your terminal.
    -   Run the PyQt5 application:
        ```bash
        python app.py
        ```
2.  **Initial Project Setup:**
    -   Upon first launch, or if no projects exist, you might be prompted by the "Project Manager" to create a new project or load an existing one.
    -   Refer to the "Project Management" section below for more details on creating and managing projects.
3.  **Using the Tool:**
    -   The application window will open, displaying the main interface.
    -   **Mode Selection:**
        -   Use the "Mode" dropdown in the "Controls" panel (usually docked on the left) to switch between "Edit Mode" and "View Mode".
    -   **Edit Mode:**
        -   **Background:** Adjust canvas background color and dimensions (width, height) using the controls.
        -   **Images:**
            -   Click "Upload Image" to add an image to the current project's canvas. Images are stored within the project's dedicated `images` folder.
            -   Select an image on the canvas to enable its properties in the control panel (scale, delete).
            -   Drag selected images to reposition them.
        -   **Info Rectangles (Hotspots):**
            -   Click "Add Info Rectangle" to create a new hotspot on the canvas.
            -   Select a hotspot to edit its properties (text content, width, height) in the control panel.
            -   Drag selected hotspots to reposition them.
            -   Resize selected hotspots by dragging their handles.
            -   Copy (Ctrl+C) and Paste (Ctrl+V) selected hotspots (when an input field is not focused).
            -   Delete selected hotspots or images using the 'Delete' key (when an input field is not focused) or the respective delete buttons in the control panel (confirmation may be required).
        -   **Saving:** All changes to a project (background, images, hotspots) are automatically saved to its `config.json` file. You can also manually save using "File > Save Configuration" (Ctrl+S).
    -   **View Mode:**
        -   In this mode, the canvas is not editable.
        -   Hover your mouse cursor over the areas where you defined info rectangles (hotspots) to see their associated text appear in a pop-up.
        -   The control panel is mostly hidden or shows a brief message; editing controls are disabled.

## Project Management

This application supports managing multiple distinct interactive image projects. Each project has its own canvas, images, and hotspot configurations.

-   **Project Storage:**
    -   All projects are stored as subdirectories within the `static/` folder in the application's root directory.
    -   Each project subdirectory (e.g., `static/<project_name>/`) contains:
        -   A `config.json` file: Stores all settings for that project (background, image details, hotspot data).
        -   An `images/` folder: Stores all images uploaded specifically for that project.

-   **Managing Projects (Project Manager Dialog):**
    -   You can manage projects via the "File > Manage Projects..." menu option. This opens the "Project Manager" dialog.
    -   **Creating a New Project:**
        -   Click the "Create New Project" button.
        -   Enter a unique name for your project when prompted.
        -   A new folder with this name will be created in the `static/` directory, along with a default `config.json` and an `images/` subfolder.
        -   The application will then load this new project.
    -   **Loading an Existing Project:**
        -   Select a project from the list of existing projects displayed in the dialog.
        -   Click the "Load Selected" button (or double-click the project name).
        -   The application will load the selected project's configuration and images.
    -   **Deleting a Project:**
        -   Select a project from the list.
        -   Click the "Delete Selected Project" button.
        -   You will be asked for confirmation before the project's entire folder (including its `config.json` and all its images) is permanently deleted. This action cannot be undone.
        -   If you delete the currently open project, you will be prompted to select or create another project.
    -   **Initial Startup:** If you run the application without any existing projects, the Project Manager dialog may appear automatically, prompting you to create your first project.

## Stopping the Application

-   To stop the application, simply close the main application window (e.g., by clicking the 'X' button in the window's title bar or using File > Exit / Ctrl+Q).
