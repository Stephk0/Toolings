"""Library Relink - bulk-relink the linked libraries of the current .blend
to a new folder, with a dry-run preview instead of one-by-one Outliner relinks.

Architecture (WMH standard):
  core/     pure Python, bpy-free, unit-tested with pytest
  blender/  bpy boundary: properties, operators, panel
"""

bl_info = {
    "name": "Library Relink",
    "author": "Stephan Viranyi + Claude AI",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > Relink",
    "description": "Bulk-relink linked libraries to a new folder with dry-run preview",
    "category": "Pipeline",
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
