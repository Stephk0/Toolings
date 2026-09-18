"""Version-specific names / API shims kept in ONE place.

Geometry-Nodes API, operator names and ``blf``/``gpu`` signatures drift between
Blender releases.  Anything that differs across 4.2 LTS .. 5.x lives here so the
rest of the addon stays version-agnostic.

Tested against:
  * Blender 4.2.x LTS
  * Blender 5.0.x

If you port to another build and something visual breaks, look here first.
"""

import bpy
import blf
import gpu

# ``node.location`` is in node space; ``node.dimensions`` is in pixels and only
# valid *after* the editor has drawn.  Convert px -> node space with ui_scale.
def ui_scale():
    try:
        return bpy.context.preferences.system.ui_scale
    except Exception:
        return 1.0


# blf.size dropped its ``dpi`` arg in Blender 4.0.
def blf_size(font_id, size):
    try:
        blf.size(font_id, size)
    except TypeError:  # pre-4.0 fallback
        blf.size(font_id, size, 72)


# 'UNIFORM_COLOR' has been the 2D solid-fill builtin since 3.4; stable in 4.2/5.x.
def solid_shader():
    return gpu.shader.from_builtin('UNIFORM_COLOR')


# Area-screenshot operator. ``screen.screenshot_area`` exists from 3.x onward and
# captures a single area's framebuffer (overlay draw handlers included).
SCREENSHOT_AREA_OP = "screenshot_area"


def screenshot_area(window, area, region, filepath):
    """Capture one editor area to ``filepath`` (PNG), overlays included."""
    op = getattr(bpy.ops.screen, SCREENSHOT_AREA_OP)
    with bpy.context.temp_override(window=window, area=area, region=region):
        op(filepath=filepath)
