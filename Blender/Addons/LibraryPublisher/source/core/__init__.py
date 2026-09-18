"""LibraryPublisher core - pure Python, no bpy.

Modules:
    config     schema, defaults, load/save, dotted-path edits, validation
    selection  scope config -> concrete deterministic file list
    catalogs   blender_assets.cats.txt parsing + the ST3E_Ext rename (Variant A)
    criteria   pluggable publish checks: plan, interpret, apply block/warn policy
    manifest   content hashes, incremental diff, provenance stamps
    delivery   local staging + rclone / robocopy / copy backends
    publish    the orchestrator that wires all of the above together
    shell      subprocess, git provenance, Blender discovery
"""

__all__ = [
    "catalogs",
    "config",
    "criteria",
    "delivery",
    "manifest",
    "publish",
    "selection",
    "shell",
]
