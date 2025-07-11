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
        for rect_conf in self.config.get('info_areas', []):
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
            z_index = rect_conf.get('z_index', utils.Z_VALUE_INFO_RECT)
            outer_style = f"position:absolute; left:{left}px; top:{top}px; width:{rect_width}px; height:{rect_height}px; display:flex; box-sizing: border-box; z-index:{z_index};"
            fill_hex = rect_conf.get('fill_color', utils.get_default_config()["defaults"].get("info_area_appearance", {}).get("fill_color", "#007BFF"))
            fill_alpha = rect_conf.get('fill_alpha', utils.get_default_config()["defaults"].get("info_area_appearance", {}).get("fill_alpha", 0.1))
            try:
                fill_alpha = float(fill_alpha)
            except Exception:
                fill_alpha = 0.1
            if fill_alpha > 1:
                fill_alpha = fill_alpha / 255.0
            fill_alpha = max(0.0, min(fill_alpha, 1.0))
            rgba_color = utils.hex_to_rgba(fill_hex, fill_alpha)
            outer_style += f"background-color:{rgba_color};"
            if rect_conf.get('shape', 'rectangle') == 'ellipse':
                outer_style += "border-radius:50%;"
            angle = rect_conf.get('angle', 0)
            try:
                angle = float(angle)
            except (ValueError, TypeError):
                angle = 0
            if angle:
                outer_style += f"transform-origin:center center; transform:rotate({angle}deg);"
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
            show_on_hover_connected = rect_conf.get('show_on_hover_connected', False) # New
            if show_on_hover or (not show_on_hover and show_on_hover_connected): # Updated logic
                outer_style += "opacity:0;"
            text_content_div_style = current_inner_style
            # Updated data_attr to include the new property
            data_attr = f"data-show-on-hover='{str(show_on_hover).lower()}' data-show-on-hover-connected='{str(show_on_hover_connected).lower()}'"
            extra_data = (
                f"data-id='{rect_conf.get('id')}' "
                f"data-width='{rect_width}' data-height='{rect_height}' "
                f"data-shape='{rect_conf.get('shape','rectangle')}'"
            )
            lines.append(
                f"<div class='hotspot info-rectangle-export' {extra_data} {data_attr} style='{outer_style}'>"
                f"<div class='text-content' style='{text_content_div_style}'>{text_content}</div></div>"
            )
        for conn in self.config.get('connections', []):
            src = next((r for r in self.config.get('info_areas', []) if r.get('id') == conn.get('source')), None)
            dst = next((r for r in self.config.get('info_areas', []) if r.get('id') == conn.get('destination')), None)
            if not src or not dst:
                continue
            start_x, start_y, end_x, end_y = utils.compute_connection_points(src, dst)
            color = conn.get('line_color', '#00ffff')
            thickness = conn.get('thickness', 2)
            configured_opacity = conn.get('opacity', 1.0) # Store configured opacity
            z = conn.get('z_index', 0)

            info_areas_list = self.config.get('info_areas', [])

            src_conf = next((r for r in info_areas_list if r.get('id') == conn.get('source')), None)
            dst_conf = next((r for r in info_areas_list if r.get('id') == conn.get('destination')), None)

            src_initially_hidden = False
            if src_conf:
                src_show_on_hover_val = src_conf.get('show_on_hover', True)
                src_show_on_hover_connected_val = src_conf.get('show_on_hover_connected', False)
                if src_show_on_hover_val or (not src_show_on_hover_val and src_show_on_hover_connected_val):
                    src_initially_hidden = True

            dst_initially_hidden = False
            if dst_conf:
                dst_show_on_hover_val = dst_conf.get('show_on_hover', True)
                dst_show_on_hover_connected_val = dst_conf.get('show_on_hover_connected', False)
                if dst_show_on_hover_val or (not dst_show_on_hover_val and dst_show_on_hover_connected_val):
                    dst_initially_hidden = True

            base_style_part = f"position:absolute;left:0;top:0;width:{bg.get('width',800)}px;height:{bg.get('height',600)}px;pointer-events:none;z-index:{z};"
            opacity_part_for_line = ""
            if src_initially_hidden or dst_initially_hidden:
                opacity_part_for_line = "opacity:0;"
            else:
                line_opacity_val = conn.get('opacity', 1.0) # Use the line's own configured opacity
                opacity_part_for_line = f"opacity:{line_opacity_val};"

            initial_line_style = f"{base_style_part}{opacity_part_for_line}"

            line_data = (
                f"data-source='{conn.get('source')}' data-destination='{conn.get('destination')}' "
                f"data-original-opacity='{configured_opacity}'" # Add data attribute
            )
            lines.append(
                f"<svg class='connection-line' {line_data} style='{initial_line_style}'><line x1='{start_x}' y1='{start_y}' x2='{end_x}' y2='{end_y}' stroke='{color}' stroke-width='{thickness}' /></svg>"
            )
        lines.append(
            "<button id='toggle-all-info' style='position:absolute;right:10px;bottom:10px;z-index:1000;'>Show All Info</button>"
        )
        lines.extend([
"</div>", "<script>",
"var showAllInfo=false;",
"document.getElementById('toggle-all-info').addEventListener('click',function(){",
"  showAllInfo=!showAllInfo;",
"  this.textContent=showAllInfo?'Hide All Info':'Show All Info';",
"  updateAllVisibilities();",
"  updateConnectionLines();",
"});",
"function computeRectBoundaryPoint(rect,target){",
"  var cx=parseFloat(rect.style.left)+rect.offsetWidth/2;",
"  var cy=parseFloat(rect.style.top)+rect.offsetHeight/2;",
"  var tx=parseFloat(target.style.left)+target.offsetWidth/2;",
"  var ty=parseFloat(target.style.top)+target.offsetHeight/2;",
"  var dx=tx-cx, dy=ty-cy;",
"  if(dx===0&&dy===0) return [cx,cy];",
"  var sx=(rect.offsetWidth/2)/Math.abs(dx||1e-6);",
"  var sy=(rect.offsetHeight/2)/Math.abs(dy||1e-6);",
"  var t=Math.min(sx,sy);",
"  return [cx+dx*t, cy+dy*t];",
"}",
"function updateConnectionLines(){",
            """  document.querySelectorAll('.connection-line').forEach(function(svg){""",
            """    var src=document.querySelector('.info-rectangle-export[data-id="' + svg.dataset.source + '"]');""",
            """    var dst=document.querySelector('.info-rectangle-export[data-id="' + svg.dataset.destination + '"]');""",
            """    if(!src||!dst) return;""",
            """    var s=computeRectBoundaryPoint(src,dst);""",
            """    var e=computeRectBoundaryPoint(dst,src);""",
            "    var line=svg.querySelector('line');",
"    line.setAttribute('x1',s[0]);",
"    line.setAttribute('y1',s[1]);",
"    line.setAttribute('x2',e[0]);",
"    line.setAttribute('y2',e[1]);",
"  });",
"}",
"function updateAllVisibilities(currentlyHoveredItemId = null) {",
"    if(showAllInfo){",
"        document.querySelectorAll('.hotspot.info-rectangle-export').forEach(h=>h.style.opacity='1');",
"        document.querySelectorAll('.connection-line').forEach(line=>line.style.opacity=line.dataset.originalOpacity);",
"        return;",
"    }",
"    // First, reset all hover-dependent items to hidden (opacity 0)",
"    document.querySelectorAll('.hotspot.info-rectangle-export').forEach(h => {",
"        // An item is hover-dependent if show_on_hover is true, OR if show_on_hover is false but show_on_hover_connected is true",
"        if (h.dataset.showOnHover !== 'false' || (h.dataset.showOnHover === 'false' && h.dataset.showOnHoverConnected === 'true')) {",
"            h.style.opacity = '0';",
"        }",
"    });",
"    // Also reset all connection lines to hidden (opacity 0) initially for this update cycle",
"    document.querySelectorAll('.connection-line').forEach(line => {",
"        line.style.opacity = '0';",
"    });",
"",
"    // If an item is actually being hovered:",
"    if (currentlyHoveredItemId) {",
"        const hoveredHotspot = document.querySelector(`.hotspot.info-rectangle-export[data-id='${currentlyHoveredItemId}']`);",
"        if (hoveredHotspot) {",
"            // Make the directly hovered item visible if it's meant to be shown on any kind of hover.",
"            if (hoveredHotspot.dataset.showOnHover !== 'false') { // Only make visible if it's a standard show_on_hover item",
"                hoveredHotspot.style.opacity = '1';",
"            }",
"            // If it's a show_on_hover_connected item (i.e., showOnHover === 'false' && showOnHoverConnected === 'true'),",
"            // direct hover on ITSELF does not make it visible. Its visibility is handled purely by the",
"            // section below that checks for connected items.",
"",
"            // Now, find items connected to 'hoveredHotspot' that have 'show_on_hover_connected=\"true\"' and 'show_on_hover=\"false\"'",
"            document.querySelectorAll('.connection-line').forEach(line => {",
"                let otherItemId = null;",
"                if (line.dataset.source === currentlyHoveredItemId) {",
"                    otherItemId = line.dataset.destination;",
"                } else if (line.dataset.destination === currentlyHoveredItemId) {",
"                    otherItemId = line.dataset.source;",
"                }",
"",
"                if (otherItemId) {",
"                    const otherHotspot = document.querySelector(`.hotspot.info-rectangle-export[data-id='${otherItemId}']`);",
"                    if (otherHotspot && otherHotspot.dataset.showOnHover === 'false' && otherHotspot.dataset.showOnHoverConnected === 'true') {",
"                        otherHotspot.style.opacity = '1';",
"                    }",
"                }",
"            });",
"        }",
"    }",
"",
"    // Second pass: Ensure items that are *always* visible (not hover-dependent at all) are set to opacity 1.",
"    document.querySelectorAll('.hotspot.info-rectangle-export').forEach(h => {",
"        if (h.dataset.showOnHover === 'false' && h.dataset.showOnHoverConnected === 'false') {",
"            h.style.opacity = '1';",
"        }",
"    });",
"",
"    // Final pass for connection lines: A line is visible if both its source and destination hotspots are currently visible (opacity 1).",
"    document.querySelectorAll('.connection-line').forEach(line => {",
"        const srcHotspot = document.querySelector(`.hotspot.info-rectangle-export[data-id='${line.dataset.source}']`);",
"        const dstHotspot = document.querySelector(`.hotspot.info-rectangle-export[data-id='${line.dataset.destination}']`);",
"",
"        if (srcHotspot && dstHotspot && srcHotspot.style.opacity === '1' && dstHotspot.style.opacity === '1') {",
"            line.style.opacity = line.dataset.originalOpacity;",
"        } else {",
"            line.style.opacity = '0';",
"        }",
"    });",
"}",
"",
"// Event listeners for DRAGGING hotspots (preserving existing dragging logic)",
"document.querySelectorAll('.hotspot.info-rectangle-export').forEach(function(h){",
"  // OLD HOVER MOUSEENTER/MOUSELEAVE LISTENERS ARE REMOVED FROM HERE",
"",
"  var origLeft=0,origTop=0;",
"  var isDrag=false,animating=false,offX=0,offY=0,animId=0;",
"  h.addEventListener('mousedown',function(e){",
"    if(animating){cancelAnimationFrame(animId);animating=false;}",
"    origLeft=parseFloat(h.style.left);",
"    origTop=parseFloat(h.style.top);",
"    isDrag=true;",
"    offX=e.clientX-h.offsetLeft;",
"    offY=e.clientY-h.offsetTop;",
"    h.style.transition='none';",
"    e.preventDefault();",
"  });",
"  document.addEventListener('mousemove',function(e){",
"    if(!isDrag) return;",
"    h.style.left=(e.clientX-offX)+'px';",
"    h.style.top=(e.clientY-offY)+'px';",
"    updateConnectionLines();",
"  });",
"  document.addEventListener('mouseup',function(){",
"    if(!isDrag) return;",
"    isDrag=false;",
"    var l=parseFloat(h.style.left);",
"    var t=parseFloat(h.style.top);",
"    var vx=0,vy=0;",
"    animating = true;",
"    function anim(){",
"      var dx=origLeft-l;",
"      var dy=origTop-t;",
"      vx+=dx*0.1;",
"      vy+=dy*0.1;",
"      l+=vx;",
"      t+=vy;",
"      vx*=0.8;",
"      vy*=0.8;",
"      h.style.left=l+'px';",
"      h.style.top=t+'px';",
"      updateConnectionLines();",
"      if(Math.abs(dx)>0.5||Math.abs(dy)>0.5||Math.abs(vx)>0.5||Math.abs(vy)>0.5){",
"        animId=requestAnimationFrame(anim);",
"      }else{",
"        h.style.left=origLeft+'px';",
"        h.style.top=origTop+'px';",
"        updateConnectionLines();",
"        animating=false;",
"      }",
"    }",
"    animId=requestAnimationFrame(anim);",
"  });",
"});",
"",
"// Event listeners for HOVER effects (NEW - using updateAllVisibilities)",
"document.querySelectorAll('.hotspot.info-rectangle-export').forEach(function(h) {",
"    h.addEventListener('mouseenter', function() {",
"        updateAllVisibilities(h.dataset.id);",
"    });",
"    h.addEventListener('mouseleave', function(e) {",
"        const leaveX = e.clientX;",
"        const leaveY = e.clientY;",
"        setTimeout(() => {",
"            let newHoveredItemId = null;",
"            const elems = document.elementsFromPoint(leaveX, leaveY);",
"            for (const el of elems) {",
"                const hotspot = el.closest ? el.closest('.hotspot.info-rectangle-export') : null;",
"                if (hotspot) {",
"                    newHoveredItemId = hotspot.dataset.id;",
"                    break;",
"                }",
"            }",
"            updateAllVisibilities(newHoveredItemId);",
"        }, 0);",
"    });",
"});",
"",
"// Initial setup calls",
"updateConnectionLines();",
"updateAllVisibilities();",
"</script>", "</body></html>",
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
