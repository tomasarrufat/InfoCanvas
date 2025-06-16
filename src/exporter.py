import os
import shutil
import html
from PyQt5.QtGui import QTextDocument
from . import utils # Assuming utils.py is in the same src directory

class HtmlExporter:
    def __init__(self, config, project_path):
        self.config = config
        self.project_path = project_path
        self.default_text_config = utils.get_default_config()["defaults"]["info_rectangle_text_display"]

    def _replace_relative_font_sizes(self, html_fragment, base_font_px):
        """Convert CSS relative font sizes like 'xx-large' to pixel values."""
        size_map = {
            "xx-small": 0.6,
            "x-small": 0.75,
            "small": 0.8,
            "medium": 1.0,
            "large": 1.2,
            "x-large": 1.5,
            "xx-large": 2.0,
        }
        for name, factor in size_map.items():
            px = int(round(base_font_px * factor))
            html_fragment = html_fragment.replace(f"font-size:{name};", f"font-size:{px}px;")
        return html_fragment

    def _get_project_images_folder(self):
        if not self.project_path:
            print("Error: Project path is not set in HtmlExporter.")
            return None
        return os.path.join(self.project_path, utils.PROJECT_IMAGES_DIRNAME)

    def _copy_project_images(self, output_dir):
        if not self.config:
            print("Warning: No config loaded in HtmlExporter, cannot copy images.")
            return False
        src_images_folder = self._get_project_images_folder()
        if not src_images_folder or not os.path.isdir(src_images_folder):
            print(f"Warning: Source images folder '{src_images_folder}' not found or not a directory. No images will be copied.")
            return False
        dest_images_folder = os.path.join(output_dir, 'images')
        os.makedirs(dest_images_folder, exist_ok=True)
        copied_any = False
        image_configs = self.config.get('images', [])
        if not image_configs:
            print("No images listed in config to copy.")
            return True # No images to copy, considered successful.

        for img_conf in image_configs:
            relative_image_path = img_conf.get('path', '')
            if not relative_image_path:
                print(f"Warning: Image config missing path for ID '{img_conf.get('id', 'Unknown')}'. Skipping copy.")
                continue
            src_file_path = os.path.join(src_images_folder, relative_image_path)
            dest_file_path = os.path.join(dest_images_folder, relative_image_path)
            os.makedirs(os.path.dirname(dest_file_path), exist_ok=True)
            if os.path.exists(src_file_path):
                try:
                    shutil.copy2(src_file_path, dest_file_path)
                    copied_any = True # Mark true if at least one copy action is attempted
                except Exception as e:
                    print(f"Error copying image '{src_file_path}' to '{dest_file_path}': {e}")
                    # Depending on desired behavior, you might want to return False here or collect errors.
            else:
                print(f"Warning: Source image file not found: '{src_file_path}'. Skipping copy.")

        # Return True if the process completed, even if some individual files were missing.
        # The calling function can check logs for specific errors if needed.
        return True


    def _generate_html_content(self):
        # ... (previous implementation from step 2 - content is long, so omitted for brevity in this subtask description) ...
        # For the subtask runner, assume this method is already correctly defined as per previous steps.
        # Actual content of _generate_html_content:
        project_name = self.config.get('project_name', 'Project')
        bg = self.config.get('background', {})
        lines = [
            "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='utf-8'>",
            f"<title>{html.escape(project_name)}</title>",
            "<style>", "#canvas{position:relative;}", ".hotspot{position:absolute;}",
            ".tooltip{position:absolute;border:1px solid #333;padding:2px;background:rgba(255,255,255,0.9);display:none;z-index:1000;}",
            "</style>", "</head>", "<body>",
            f"<div id='canvas' style='width:{bg.get('width',800)}px;height:{bg.get('height',600)}px;background-color:{bg.get('color','#FFFFFF')};'>",
        ]
        for img_conf in self.config.get('images', []):
            scale = img_conf.get('scale', 1.0)
            width = img_conf.get('original_width', 0) * scale
            height = img_conf.get('original_height', 0) * scale
            left = img_conf.get('center_x', 0) - width / 2
            top = img_conf.get('center_y', 0) - height / 2
            src = os.path.join('images', img_conf.get('path', ''))
            lines.append(
                f"<img src='{html.escape(src)}' style='position:absolute;left:{left}px;top:{top}px;width:{width}px;height:{height}px;'>"
            )
        for rect_conf in self.config.get('info_rectangles', []):
            rect_width = rect_conf.get('width', 0)
            rect_height = rect_conf.get('height', 0)
            left = rect_conf.get('center_x', 0) - rect_width / 2
            top = rect_conf.get('center_y', 0) - rect_height / 2
            doc = QTextDocument()
            doc.setMarkdown(html.escape(rect_conf.get('text', '')))
            full_html = doc.toHtml()
            body_start = full_html.find('<body')
            if body_start != -1:
                body_start = full_html.find('>', body_start) + 1
                body_end = full_html.rfind('</body>')
                text_content = full_html[body_start:body_end]
            else:
                text_content = full_html
            font_color = rect_conf.get('font_color', self.default_text_config['font_color'])
            font_size_str = rect_conf.get('font_size', self.default_text_config['font_size'])
            if isinstance(font_size_str, (int, float)) or str(font_size_str).isdigit():
                base_font_px = int(float(font_size_str))
                font_size = f"{font_size_str}px"
            else:
                try:
                    base_font_px = int(str(font_size_str).replace('px', ''))
                except ValueError:
                    base_font_px = int(str(self.default_text_config['font_size']).replace('px', ''))
                font_size = font_size_str
            text_content = self._replace_relative_font_sizes(text_content, base_font_px)
            padding_str = rect_conf.get('padding', self.default_text_config['padding'])
            if isinstance(padding_str, (int, float)) or str(padding_str).isdigit(): padding = f"{padding_str}px"
            else: padding = padding_str
            h_align = rect_conf.get('horizontal_alignment', self.default_text_config['horizontal_alignment'])
            v_align = rect_conf.get('vertical_alignment', self.default_text_config['vertical_alignment'])
            outer_style = f"position:absolute; left:{left}px; top:{top}px; width:{rect_width}px; height:{rect_height}px; display:flex; box-sizing: border-box;"
            if v_align == "top": outer_style += "align-items:flex-start;"
            elif v_align == "center" or v_align == "middle": outer_style += "align-items:center;"
            elif v_align == "bottom": outer_style += "align-items:flex-end;"
            inner_style_list = [
                "width:100%;", "box-sizing:border-box;", "overflow-wrap:break-word;", "word-wrap:break-word;",
                f"color:{font_color};", f"font-size:{font_size};", "background-color:transparent;",
                f"padding:{padding};", f"text-align:{h_align};"
            ]
            current_inner_style = "".join(inner_style_list)
            show_on_hover = rect_conf.get('show_on_hover', True)
            display_style = 'none' if show_on_hover else 'block'
            text_content_div_style = current_inner_style + f" display: {display_style};"
            data_attr = f"data-show-on-hover='{str(show_on_hover).lower()}'"
            lines.append(
                f"<div class='hotspot info-rectangle-export' {data_attr} style='{outer_style}'>"
                f"<div class='text-content' style='{text_content_div_style}'>{text_content}</div></div>"
            )
        lines.extend([
            "</div>", "<script>",
            "document.querySelectorAll('.hotspot.info-rectangle-export').forEach(function(h){",
            "  var textContentDiv = h.querySelector('.text-content');",
            "  if (!textContentDiv) return;",
            "  if (h.dataset.showOnHover !== 'false') {",
            "    h.addEventListener('mouseenter', function(e){ textContentDiv.style.display = 'block'; });",
            "    h.addEventListener('mouseleave', function(e){ textContentDiv.style.display = 'none'; });",
            "  }",
            "  var origLeft = h.offsetLeft;",
            "  var origTop = h.offsetTop;",
            "  var isDrag = false, animating = false, offX = 0, offY = 0;",
            "  h.addEventListener('mousedown', function(e){",
            "    if(animating) return;",
            "    isDrag = true;",
            "    offX = e.clientX - h.offsetLeft;",
            "    offY = e.clientY - h.offsetTop;",
            "    h.style.transition = 'none';",
            "    e.preventDefault();",
            "  });",
            "  document.addEventListener('mousemove', function(e){",
            "    if(!isDrag) return;",
            "    h.style.left = (e.clientX - offX) + 'px';",
            "    h.style.top = (e.clientY - offY) + 'px';",
            "  });",
            "  document.addEventListener('mouseup', function(){",
            "    if(!isDrag) return;",
            "    isDrag = false;",
            "    var l = parseFloat(h.style.left);",
            "    var t = parseFloat(h.style.top);",
            "    var vx = 0, vy = 0;",
            "    animating = true;",
            "    function anim(){",
            "      var dx = origLeft - l;",
            "      var dy = origTop - t;",
            "      vx += dx*0.1;",
            "      vy += dy*0.1 + 0.5;",
            "      l += vx;",
            "      t += vy;",
            "      vx *= 0.8;",
            "      vy *= 0.8;",
            "      h.style.left = l + 'px';",
            "      h.style.top = t + 'px';",
            "      if(Math.abs(dx) > 0.5 || Math.abs(dy) > 0.5 || Math.abs(vx) > 0.5 || Math.abs(vy) > 0.5){",
            "        requestAnimationFrame(anim);",
            "      } else {",
            "        h.style.left = origLeft + 'px';",
            "        h.style.top = origTop + 'px';",
            "        animating = false;",
            "      }",
            "    }",
            "    requestAnimationFrame(anim);",
            "  });",
            "});", "</script>", "</body></html>"
        ])
        return "\n".join(lines)

    def export(self, output_html_path):
        """
        Exports the project view to an HTML file and copies associated images.

        Args:
            output_html_path (str): The full path where the HTML file will be saved.

        Returns:
            bool: True if export was successful (HTML written, images attempted to be copied),
                  False otherwise (e.g., error writing HTML).
        """
        if not output_html_path:
            print("Error: Output HTML path is not provided to HtmlExporter.export().")
            return False

        html_content = self._generate_html_content()
        output_dir = os.path.dirname(str(output_html_path))

        # Create output directory if it doesn't exist (e.g., if output_html_path is "new_folder/export.html")
        # This should usually be handled by QFileDialog or the caller, but good to ensure.
        if not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except Exception as e:
                print(f"Error creating output directory '{output_dir}': {e}")
                return False # Cannot proceed if output directory cannot be created

        # Copy images
        # The success of image copying might not necessarily halt the HTML export,
        # but errors/warnings will be printed by _copy_project_images.
        self._copy_project_images(output_dir) # We can check its return value if needed

        # Write the HTML file
        try:
            with open(str(output_html_path), 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"HTML content successfully written to {output_html_path}")
            return True
        except Exception as e:
            print(f"Error writing HTML file to '{output_html_path}': {e}")
            return False

if __name__ == '__main__':
    print("HtmlExporter class defined. To be used by the main application.")
