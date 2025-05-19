# Interactive Image Tool

## Basic Purpose

This tool provides a web-based interface for creating interactive learning materials. Users can upload images onto a canvas, position and scale them, and then define rectangular "hotspot" areas over the images. When hovering over these hotspots in "View Mode", associated explanatory text appears. This is useful for applications like labeling anatomical diagrams, explaining parts of a machine, or creating simple interactive guides.

## File Structure

The project follows this basic structure:

```
/interactive-image-tool/
|-- app.py                 # Main Python Flask application
|-- requirements.txt       # Python package dependencies
|-- README.md              # This file
|-- /templates/
|   |-- index.html         # HTML structure for the frontend
|-- /static/
|   |-- style.css          # CSS styles for the frontend
|   |-- script.js          # JavaScript logic for the frontend
|   |-- /config/
|   |   |-- config.json    # Stores background, image, and hotspot data (auto-generated)
|   |-- /images/
|   |   |-- (uploaded images will appear here)

```

-   **`app.py`**: Contains the Flask backend logic, handling API requests, configuration management, and file operations.
    
-   **`requirements.txt`**: Lists the Python packages needed to run the backend.
    
-   **`templates/index.html`**: The main HTML page rendered by Flask.
    
-   **`static/`**: Folder served by Flask for static assets.
    
    -   **`style.css`**: Contains all the CSS styling.
        
    -   **`script.js`**: Contains all the JavaScript for frontend interactions (Edit/View modes, canvas handling, API calls, etc.).
        
    -   **`config/config.json`**: Automatically created/updated file storing the state of your interactive image setup.
        
    -   **`images/`**: Folder where uploaded images are stored.
        

## Installation

1.  **Clone or Download:** Get the project files onto your local machine.
    
2.  **Navigate:** Open a terminal or command prompt and navigate into the project's root directory (`/interactive-image-tool/`).
    
3.  **Create Virtual Environment (Recommended):**
    
    ```
    python -m venv venv
    # On Windows:
    venv\Scripts\activate
    # On macOS/Linux:
    source venv/bin/activate
    
    ```
    
4.  **Install Requirements:** Install the necessary Python packages using pip and the `requirements.txt` file:
    
    ```
    pip install -r requirements.txt
    
    ```
    

## Usage

1.  **Run the Application:** From the project's root directory in your terminal (make sure your virtual environment is activated), run the Flask application:
    
    ```
    python app.py
    
    ```
    
2.  **Access the Tool:** Open your web browser and navigate to the address shown in the terminal, usually: `http://127.0.0.1:5001/`
    
3.  **Using the Tool:**
    
    -   **Edit Mode (Default):**
        
        -   Adjust background size and color.
            
        -   Upload images using the file input.
            
        -   Click images to select them, then use the controls panel to adjust scale or the delete button. Drag selected images to reposition.
            
        -   Click "Add Info Rectangle" to create a hotspot.
            
        -   Click a hotspot (the dashed rectangle) to select it.
            
        -   Use the controls panel to edit the hotspot's text, width, and height.
            
        -   Drag selected hotspots to reposition.
            
        -   Drag the handles on a selected hotspot to resize it.
            
        -   Use Ctrl+C (when a hotspot is selected and _not_ focused on an input) to copy its data.
            
        -   Use Ctrl+V (when _not_ focused on an input) to paste the copied hotspot data as a new hotspot centered on the canvas.
            
        -   Press the 'Delete' key (when a hotspot is selected and _not_ focused on an input) to delete it (requires confirmation).
            
        -   All changes are auto-saved to `static/config/config.json`.
            
    -   **View Mode:**
        
        -   Select "View Mode" from the dropdown.
            
        -   Hover over the areas where you placed info rectangles to see the associated text pop up.
            
        -   Use the toggle button (`<` or `>`) to collapse/expand the sidebar area.
            

## Stopping the Application

-   Go back to the terminal where `python app.py` is running and press `Ctrl+C`.