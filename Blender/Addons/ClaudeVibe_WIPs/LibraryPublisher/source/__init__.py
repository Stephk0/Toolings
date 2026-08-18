"""Library Publisher - publish the ST3E Blender asset library to a Google
Shared Drive, with catalogs renamed so both libraries load side by side.

Architecture (WMH standard):
  core/     pure Python, bpy-free, unit-tested with pytest
  blender/  bpy boundary: preferences, operators, panel
  checks/   scripts that run INSIDE headless Blender (criteria inspection)
  cli.py    the entry point every trigger funnels through

The addon is only trigger 4 of 4 (a button). The CLI is the real tool: it also
backs the slash commands, the git hook and the GitHub Action.
"""

VERSION = (1, 1, 0)

bl_info = {
    "name": "Library Publisher",
    "author": "Stephan Viranyi + Claude AI",
    "version": VERSION,
    "blender": (4, 2, 0),
    "location": "3D View > Sidebar > ST3E > Library Publisher",
    "description": "Publish the ST3E asset library to a Google Shared Drive as ST3E_Ext",
    "category": "Import-Export",
}

# Import the bpy boundary only inside Blender, so core/ stays importable (and
# pytest can walk this package) in plain CPython.
try:
    import bpy  # noqa: F401

    _HAS_BPY = True
except ModuleNotFoundError:
    _HAS_BPY = False

if _HAS_BPY:
    from .blender import register, unregister  # noqa: F401
else:  # pragma: no cover - only hit when imported outside Blender
    def register():
        raise RuntimeError("Library Publisher: register() needs Blender")

    def unregister():
        raise RuntimeError("Library Publisher: unregister() needs Blender")
