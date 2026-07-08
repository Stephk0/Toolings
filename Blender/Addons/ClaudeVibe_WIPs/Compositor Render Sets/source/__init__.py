"""Compositor Render Sets - render distinct collection sets through the
compositor with automatic File Output node management.

Architecture (WMH standard):
  core/     pure Python, bpy-free, unit-tested with pytest
  blender/  bpy boundary: properties, operators, panels, compat layer
"""

bl_info = {
    "name": "Compositor Render Sets",
    "author": "Stephan Viranyi + Claude AI",
    "version": (2, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > Render Sets",
    "description": "Render distinct collections through compositor with automatic File Output node management (Blender 4.x and 5.0+)",
    "category": "Render",
}

# Import the bpy boundary only inside Blender, so core/ stays importable
# (and pytest can walk this package) in plain CPython.
try:
    import bpy  # noqa: F401
    _HAS_BPY = True
except ModuleNotFoundError:
    _HAS_BPY = False

if _HAS_BPY:
    from .blender import register, unregister
