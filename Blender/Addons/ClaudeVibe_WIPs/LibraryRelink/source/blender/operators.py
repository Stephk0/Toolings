"""Operators for Library Relink — orchestrate core.relink against bpy.data."""

import os

import bpy
from bpy.props import BoolProperty
from bpy.types import Operator

from ..core import relink


def _gather_libraries():
    return [(lib.name, bpy.path.abspath(lib.filepath)) for lib in bpy.data.libraries]


def _run_scan(settings):
    """Rebuild the plan collection from the current libraries. Returns (plan, error)."""
    new_dir = bpy.path.abspath(settings.new_dir) if settings.new_dir else ""
    if not new_dir or not os.path.isdir(new_dir):
        return None, "New Folder is not an existing directory"

    old_filter = bpy.path.abspath(settings.old_dir_filter) if settings.old_dir_filter else ""
    available = [f for f in os.listdir(new_dir) if f.lower().endswith(".blend")]
    plan = relink.plan_relink(_gather_libraries(), new_dir, available, old_filter)

    settings.plan.clear()
    for entry in plan:
        item = settings.plan.add()
        item.lib_name = entry["name"]
        item.current_path = entry["current"]
        item.target_path = entry["target"]
        item.status = entry["status"]
        item.enabled = entry["status"] == relink.STATUS_RELINK
    settings.plan_index = max(0, min(settings.plan_index, len(settings.plan) - 1))
    return plan, ""


class LIBRELINK_OT_scan(Operator):
    bl_idname = "librelink.scan"
    bl_label = "Preview"
    bl_description = ("Scan the linked libraries and preview which of them "
                      "would be relinked to the new folder (changes nothing)")

    def execute(self, context):
        settings = context.scene.library_relink
        plan, error = _run_scan(settings)
        if plan is None:
            self.report({'ERROR'}, error)
            return {'CANCELLED'}
        counts = relink.summarize(plan)
        self.report(
            {'INFO'},
            f"{counts[relink.STATUS_RELINK]} to relink, "
            f"{counts[relink.STATUS_MISSING]} missing, "
            f"{counts[relink.STATUS_FILTERED] + counts[relink.STATUS_SAME]} skipped")
        return {'FINISHED'}


class LIBRELINK_OT_apply(Operator):
    bl_idname = "librelink.apply"
    bl_label = "Relink"
    bl_description = ("Repoint all enabled libraries to the new folder and "
                      "reload them (save the file afterwards to keep it)")

    @classmethod
    def poll(cls, context):
        settings = getattr(context.scene, "library_relink", None)
        return settings is not None and any(
            item.status == relink.STATUS_RELINK and item.enabled
            for item in settings.plan)

    def invoke(self, context, event):
        # Library reload is not undoable — always confirm.
        return context.window_manager.invoke_confirm(self, event)

    def execute(self, context):
        settings = context.scene.library_relink
        make_relative = settings.make_relative
        if make_relative and not bpy.data.filepath:
            self.report({'WARNING'},
                        "File not saved — storing absolute paths instead of relative")
            make_relative = False

        done, failed = 0, []
        for item in settings.plan:
            if item.status != relink.STATUS_RELINK or not item.enabled:
                continue
            lib = bpy.data.libraries.get(item.lib_name)
            if lib is None:
                failed.append((item.lib_name, "library no longer exists"))
                continue
            if not os.path.isfile(item.target_path):
                failed.append((item.lib_name, "target file disappeared"))
                continue
            try:
                lib.filepath = (bpy.path.relpath(item.target_path)
                                if make_relative else item.target_path)
                lib.reload()
                done += 1
            except Exception as exc:
                failed.append((item.lib_name, str(exc)))

        _run_scan(settings)  # refresh statuses after the changes

        if failed:
            for name, why in failed:
                print(f"[Library Relink] FAILED {name}: {why}")
            self.report({'WARNING'},
                        f"Relinked {done}, failed {len(failed)} (details in console)")
        else:
            self.report({'INFO'},
                        f"Relinked {done} librar{'y' if done == 1 else 'ies'} — "
                        "save the file to keep it")
        return {'FINISHED'}


class LIBRELINK_OT_set_all(Operator):
    bl_idname = "librelink.set_all"
    bl_label = "Set All"
    bl_description = "Enable or disable all relink candidates at once"
    bl_options = {'INTERNAL'}

    enable: BoolProperty(default=True, options={'SKIP_SAVE'})

    def execute(self, context):
        for item in context.scene.library_relink.plan:
            if item.status == relink.STATUS_RELINK:
                item.enabled = self.enable
        return {'FINISHED'}


classes = (
    LIBRELINK_OT_scan,
    LIBRELINK_OT_apply,
    LIBRELINK_OT_set_all,
)
