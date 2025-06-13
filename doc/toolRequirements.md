# InfoCanvas: Requirements & JSON Configuration

This document outlines the requirements for a web-based Python tool designed for creating interactive images with informational overlays. It also proposes a JSON format for storing the configuration data.

## I. General Requirements

* **G1. Web-Based Interface:** The tool must have a user interface accessible via a standard web browser.
* **G2. Two Operational Modes:** The tool will feature two distinct modes:
    * **Edit Mode:** For creating and modifying interactive image setups.
    * **View Mode:** For displaying and interacting with the created setups.
* **G3. Python Backend:** The server-side logic of the tool will be implemented in Python.
* **G4. Image Storage:** All user-uploaded images will be stored in a designated `/images` folder, located relative to the application's root directory.
* **G5. Configuration Storage:** The scene configuration (background, images, info rectangles) will be stored in a single JSON file named `config.json` (or a similar fixed name) located within a designated `/config` folder, relative to the application's root directory.
* **G6. Intuitive User Interface:** The interface should be designed to be user-friendly, even for individuals without technical expertise.

## II. Edit Mode Requirements

* **EM1. Mode Activation:** Clear visual indication and mechanism to switch into Edit Mode.
* **EM2. Background Canvas Configuration:**
    * **EM2.1. Size Definition:** Users must be able to specify the width and height of the background canvas (e.g., in pixels).
    * **EM2.2. Color Selection:** Users must be able to choose a background color for the canvas (e.g., via a color picker or by inputting a hex color code).
* **EM3. Image Management:**
    * **EM3.1. Image Upload:** Users must be able to upload image files (common formats like JPG, PNG, GIF should be supported) from their local computer.
    * **EM3.2. Image Persistence:** Uploaded images must be saved to the `/images` folder. The JSON configuration will store a reference (path) to these images.
    * **EM3.3. Image Display on Canvas:** Uploaded images must be rendered on the background canvas.
    * **EM3.4. Image Repositioning:** Users must be able to interactively drag and drop images to change their position on the canvas. The new center coordinates (x, y) of the image must be recorded.
    * **EM3.5. Image Scaling:** Users must be able to resize (scale) images using the controls panel when an image is selected. The scaling factor must be recorded.
    * **EM3.6. Image Deletion:** Upon image deletion from the canvas (via button click), the corresponding image file must be permanently deleted from the `/images` folder (relative to the application's root directory), and its reference removed from the project's configuration. The system should clearly inform the user that this action is permanent before proceeding.
    * **EM3.7. Image Layering (Z-index):** When images overlap, users can control their order using "Bring to Front", "Send to Back", "Bring Forward", and "Send Backward" buttons.
* **EM4. Info Rectangle Management:**
    * **EM4.1. Add Info Rectangle:** Users must be able to add new rectangular areas onto the canvas via a button click. New rectangles appear centered.
    * **EM4.2. Info Rectangle Sizing (Manual Input):** Users must be able to define the width and height of each info rectangle using input fields in the controls panel when a rectangle is selected.
    * **EM4.3. Info Rectangle Sizing (Interactive):** When an info rectangle is selected, resize handles must appear. Users must be able to drag these handles to interactively change the width and height of the rectangle.
    * **EM4.4. Info Rectangle Positioning:** Users must be able to interactively drag and drop info rectangles to position them. The center coordinates (x, y) of the rectangle must be recorded.
    * **EM4.5. Text Association & Editing:** For each info rectangle, users must be able to input and edit the associated explanatory text (plain text) using a textarea in the controls panel when the rectangle is selected.
        * In View Mode, this text will appear with styling (e.g., black text on a white rectangular background) as defined globally in the configuration file (see `defaults.info_rectangle_text_display` in Section V).
        * The width of this text background rectangle is specified by the global `box_width` setting.
        * The height of the text background rectangle will automatically adjust to fit the multi-line text content.
        * If a line of text is longer than the specified global `box_width`, the text will wrap to a new line.
        * The global text display settings (e.g., font size, `box_width`, colors, padding) are defined with default values in the JSON configuration.
        * These global text display settings can only be edited directly in the JSON configuration file and are not editable via the GUI in Edit Mode.
    * **EM4.6. Info Rectangle Visibility (Edit Mode):** Info rectangles (the hoverable areas) should be clearly visible and distinguishable in Edit Mode (e.g., with a semi-transparent fill, distinct border). Selected rectangles should be highlighted and show resize handles.
    * **EM4.7. Info Rectangle Deletion (Button):** Users must be able to delete the selected info rectangle using a button in the controls panel (with confirmation).
    * **EM4.8. Info Rectangle Deletion (Key):** Users must be able to delete the selected info rectangle by pressing the 'Delete' key (with confirmation), provided an input field is not currently focused.
    * **EM4.9. Info Rectangle Copy/Paste:** Users must be able to copy the selected info rectangle's data using Ctrl+C and paste it using Ctrl+V. The pasted rectangle should appear centered on the canvas with a new unique ID but otherwise identical properties (text, dimensions). Copy/paste should not interfere with text copy/paste within input fields.
    * **EM4.10. Info Rectangle Layering:** Rectangles can be reordered in the same way as images using the layering buttons.
* **EM5. Configuration Auto-Saving:**
    * **EM5.1. Automatic Save on Change:** Any modification made by the user in Edit Mode (e.g., moving/scaling an image, moving/resizing/editing text of an info rectangle, changing background) should trigger an automatic save of the current configuration to the JSON file in the `/config` folder.
    * **EM5.2. Save Throttling:** To prevent excessive write operations, the auto-save mechanism should be throttled (e.g., maximum rate of once per second).

## III. View Mode Requirements

* **VM1. Mode Activation:** Clear mechanism to switch into View Mode. The tool will load the single configuration file.
* **VM2. Static Display:** In View Mode, the background, images (at their defined positions and scales), should be displayed as configured. All elements should be static and not editable.
* **VM3. Info Rectangle Invisibility:** The info rectangles themselves (their borders/fills representing the hoverable area) should not be visually rendered in View Mode. They function as invisible hover target areas.
* **VM4. Hover Interaction for Text Display:**
    * **VM4.1. Hover Detection:** The system must detect when the user's mouse cursor hovers over an area defined by an info rectangle.
    * **VM4.2. Text Pop-up/Overlay:** Upon hovering over an info rectangle, its associated text must appear on screen, styled and sized according to the global text display settings in the JSON configuration (see `defaults.info_rectangle_text_display`). The text should be clearly legible and its placement will be handled automatically (e.g., near the cursor or info rectangle).
    * **VM4.3. Text Hiding:** When the mouse cursor moves out of the info rectangle's area, the displayed text and its background must disappear.
* **VM5. Scrolling Interaction:** If the overall canvas content (background with images) is larger than the browser's viewport, standard browser scrolling should be possible. Hover interactions must continue to work correctly regardless of the scroll position.
* **VM6. Collapsible Sidebar:** In View Mode, a toggle button must be present to allow the user to collapse and expand the (normally hidden) controls panel area. When collapsed, the canvas container should expand to fill the available space.

## IV. Backend and Data Requirements

* **BD1. JSON Configuration File Structure:** The configuration will be stored in a well-defined JSON format (see section V). The file itself will reside in the `/config` folder (relative to the application's root directory) with a fixed name (e.g., `config.json`).
* **BD2. JSON Read/Write Operations:** The Python backend must be capable of:
    * Reading the JSON configuration file (from the `/config` folder) to populate the Edit or View mode.
    * Writing the current configuration (from Edit Mode, triggered by auto-save) to the JSON file (in the `/config` folder).
* **BD3. Image Path Management:** The JSON file will store relative paths to the image files located in the `/images` folder. Both the `/images` and `/config` folders are relative to the application's root directory.
* **BD4. Coordinate System Definition:** A consistent coordinate system must be established for the canvas and all elements (images, info rectangles). Typically, (0,0) is at the top-left. Positions should clearly define whether they refer to the top-left corner or the center of an element (center is often easier for scaling and rotation if added later). The JSON proposal below uses center positions.
* **BD5. Error Handling:** The backend should handle potential errors gracefully (e.g., missing image files referenced in JSON, malformed JSON during load, file write errors during auto-save, errors during image file deletion).

## V. Proposed JSON Configuration File Format

```json
{
  "project_name": "Interactive Learning Module",    // Optional: A general name for the content if needed
  "last_modified": "2025-05-08T20:15:00Z",         // Optional: Timestamp of the last save operation
  "defaults": {
    "info_rectangle_text_display": {              // Global display settings for all info rectangle text pop-ups
      "font_color": "#000000",                    // Text color (default black)
      "font_size": "14px",                        // Default text font size
      "background_color": "#FFFFFF",              // Background color of the text box (default white)
      "box_width": 200,                           // Default width in pixels for the text background box
      "padding": "5px"                            // Default padding within the text box
    }
  },
  "background": {
    "width": 800,                                  // Width of the background canvas in pixels
    "height": 600,                                 // Height of the background canvas in pixels
    "color": "#DDDDDD"                             // Background color (CSS hex format)
  },
  "images": [
    {
      "id": "img_1746653696530",                   // Unique identifier for the image
      "path": "images/some_image.jpg",             // Relative path to the image file from the application root
      "center_x": 976,                             // X-coordinate of the image's center on the canvas
      "center_y": 969,                             // Y-coordinate of the image's center on the canvas
      "scale": 1.3,                                // Scaling factor (1.0 = original size)
      "original_width": 1400,                      // Optional: Store original dimensions
      "original_height": 1095,                     // Optional: Store original dimensions
      "z_index": 0                                 // Optional: for layering if implemented
    }
    // ... more image objects
  ],
  "info_rectangles": [
    {
      "id": "rect_1746653875327",                  // Unique identifier for the info rectangle
      "target_image_id": null,                     // Optional: ID of an image this rectangle is logically associated with
      "center_x": 537.0,                           // X-coordinate of the info rectangle's center on the canvas
      "center_y": 454.0,                           // Y-coordinate of the info rectangle's center on the canvas
      "width": 100,                                // Width of the hoverable info rectangle in pixels
      "height": 100,                               // Height of the hoverable info rectangle in pixels
      "text": "System Pages"
      // text_display_options are globally defined under "defaults"
    }
    // ... more info rectangle objects
  ]
}

```

### JSON Field Explanations:

* **`project_name` (Optional):** A general name for the content.
* **`last_modified` (Optional):** ISO 8601 timestamp for when the project was last saved.
* **`defaults` Object:**
    * `info_rectangle_text_display`: Contains global default styling options that apply to all info rectangle text pop-ups in View Mode. These settings are editable only directly within the JSON configuration file.
        * `font_color`: Default color of the text (e.g., "#000000" for black).
        * `font_size`: Default font size for the text (e.g., "14px").
        * `background_color`: Default background color of the text box (e.g., "#FFFFFF" for white).
        * `box_width`: Default width in pixels for the text background box. Text will wrap if it exceeds this width.
        * `padding` (Optional): Default inner padding for the text box (e.g., "5px").
* **`background` Object:**
    * `width`, `height`: Dimensions of the main interactive area.
    * `color`: Background color of the canvas.
* **`images` Array:** List of image objects.
    * `id`: Unique string identifier for the image.
    * `path`: Relative path to the image file.
    * `center_x`, `center_y`: Coordinates of the image's center.
    * `scale`: Scaling factor.
    * `original_width`, `original_height` (Optional): Original image dimensions.
    * `z_index` (Optional): Stacking order.
* **`info_rectangles` Array:** List of info rectangle objects.
    * `id`: Unique string identifier for the info rectangle.
    * `target_image_id` (Optional): ID of an associated image.
    * `center_x`, `center_y`: Coordinates of the hoverable rectangle's center.
    * `width`, `height`: Dimensions of the hoverable rectangle.
    * `text`: The informational string.
        *(Note: `text_display_options` is no longer part of individual info_rectangles; styling is handled globally via `defaults.info_rectangle_text_display`)*
