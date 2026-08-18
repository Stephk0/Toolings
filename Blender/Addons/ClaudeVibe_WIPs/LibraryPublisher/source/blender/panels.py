"""Sidebar panel: the in-Blender trigger."""

import os

import bpy
from bpy.types import Panel

from ..core import config
from . import properties


class ST3E_PT_library_publisher(Panel):
    bl_label = "Library Publisher"
    bl_idname = "ST3E_PT_library_publisher"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "ST3E"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        state = context.window_manager.st3e_library_publish

        tool_root = properties.resolved_tool_root(context)
        if not tool_root or not os.path.isfile(config.config_path(tool_root)):
            col = layout.column()
            col.label(text="Not configured", icon="ERROR")
            col.label(text="Set the folder in Preferences > Add-ons")
            col.operator("preferences.addon_show", text="Open Preferences").module = (
                properties.ST3E_LibraryPublisherPreferences.bl_idname
            )
            return

        try:
            cfg = config.load(config.config_path(tool_root))
        except config.ConfigError as exc:
            layout.label(text=str(exc), icon="ERROR")
            return

        box = layout.box()
        col = box.column(align=True)
        col.label(text=cfg.get("library_name", "?"), icon="ASSET_MANAGER")
        dely = cfg["delivery"]
        if dely["backend"] == "rclone":
            target = "%s:%s" % (dely["rclone"].get("remote") or "?", dely["rclone"].get("path") or "")
        else:
            target = dely.get("local", {}).get("path") or "?"
        col.label(text=target, icon="EXPORT")
        if dely.get("dry_run"):
            col.label(text="DRY RUN is on", icon="INFO")

        renames = cfg["catalog"].get("rename") or []
        if cfg["catalog"].get("enabled") and renames:
            row = col.row()
            row.label(
                text="catalogs: %s" % ", ".join(
                    "%s>%s" % (r.get("from"), r.get("to")) for r in renames
                ),
                icon="OUTLINER_COLLECTION",
            )

        problems = config.validate(cfg)
        if problems:
            warn = layout.column(align=True)
            warn.alert = True
            warn.label(text="Config not ready:", icon="ERROR")
            for problem in problems[:3]:
                warn.label(text=problem)
            return

        col = layout.column(align=True)
        col.enabled = not state.busy
        col.operator("st3e.library_publish_status", icon="VIEWZOOM")
        row = col.row(align=True)
        row.scale_y = 1.4
        row.operator("st3e.library_publish", text="Publish", icon="EXPORT")
        sub = col.row(align=True)
        sub.operator("st3e.library_publish", text="Force").force = True

        if state.busy:
            layout.label(text="publishing…", icon="SORTTIME")
        elif state.headline:
            box = layout.box()
            box.alert = not state.report_ok
            box.label(
                text=state.headline,
                icon="CHECKMARK" if state.report_ok else "ERROR",
            )
            box.operator("st3e.library_publish_report", text="Full Report", icon="TEXT")


classes = (ST3E_PT_library_publisher,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
