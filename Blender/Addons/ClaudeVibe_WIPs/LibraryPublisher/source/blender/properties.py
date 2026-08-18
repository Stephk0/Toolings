"""Addon preferences and transient UI state. The bpy boundary starts here."""

import os

import bpy
from bpy.props import BoolProperty, StringProperty
from bpy.types import AddonPreferences, PropertyGroup


def guess_tool_root() -> str:
    """Find the repo's LibraryPublisher folder.

    When the addon runs from the repo itself (`source/` sitting next to
    `publish_config.json`), the parent directory is already the tool root. Once
    installed as an extension the addon is a *copy* in Blender's extensions dir,
    so it cannot know where the repo lives - that is what the preference is for.
    """
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../source
    parent = os.path.dirname(here)
    if os.path.isfile(os.path.join(parent, "publish_config.json")):
        return parent
    return ""


class ST3E_LibraryPublishState(PropertyGroup):
    """Runtime state only - lives on the WindowManager so nothing is saved."""

    busy: BoolProperty(
        name="Publishing",
        description="A publish is currently running in the background",
        default=False,
    )
    report_text: StringProperty(
        name="Last Report",
        description="Summary of the last publish or status run",
        default="",
    )
    report_ok: BoolProperty(name="Last Run Succeeded", default=True)
    headline: StringProperty(
        name="Headline",
        description="One-line result of the last run",
        default="",
    )


class ST3E_LibraryPublisherPreferences(AddonPreferences):
    bl_idname = __package__.split(".")[0] if __package__ else "library_publisher"

    tool_root: StringProperty(
        name="LibraryPublisher Folder",
        description=(
            "Path to the LibraryPublisher folder inside the git repo (the one "
            "containing publish_config.json). Needed because the installed addon "
            "is a copy and cannot locate the repo on its own"
        ),
        subtype="DIR_PATH",
        default=guess_tool_root(),
    )
    confirm_before_publish: BoolProperty(
        name="Confirm Before Publishing",
        description="Ask for confirmation before writing to the shared drive",
        default=True,
    )

    def draw(self, context):
        layout = self.layout
        col = layout.column()
        col.prop(self, "tool_root")
        resolved = bpy.path.abspath(self.tool_root) if self.tool_root else ""
        if not resolved:
            col.label(text="Set this to …/ClaudeVibe_WIPs/LibraryPublisher", icon="ERROR")
        elif not os.path.isfile(os.path.join(resolved, "publish_config.json")):
            col.label(text="No publish_config.json in that folder", icon="ERROR")
            col.label(text="Run: cli.py config init", icon="INFO")
        else:
            col.label(text="Config found", icon="CHECKMARK")
        col.prop(self, "confirm_before_publish")


def get_prefs(context):
    addon = context.preferences.addons.get(ST3E_LibraryPublisherPreferences.bl_idname)
    return addon.preferences if addon else None


def resolved_tool_root(context) -> str:
    prefs = get_prefs(context)
    if prefs and prefs.tool_root:
        return os.path.normpath(bpy.path.abspath(prefs.tool_root))
    return guess_tool_root()


classes = (ST3E_LibraryPublishState, ST3E_LibraryPublisherPreferences)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.st3e_library_publish = bpy.props.PointerProperty(
        type=ST3E_LibraryPublishState
    )


def unregister():
    del bpy.types.WindowManager.st3e_library_publish
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
