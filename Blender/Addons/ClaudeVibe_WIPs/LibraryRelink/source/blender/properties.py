"""PropertyGroups for Library Relink."""

from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import PropertyGroup

STATUS_ITEMS = [
    ('RELINK', "Relink", "File found in the new folder — will be relinked"),
    ('MISSING', "Missing", "No file with this name in the new folder — left untouched"),
    ('FILTERED', "Filtered", "Outside the source-folder filter — left untouched"),
    ('SAME', "Unchanged", "Already points at the new folder"),
]


class LIBRELINK_PG_plan_item(PropertyGroup):
    lib_name: StringProperty(name="Library")
    current_path: StringProperty(name="Current Path")
    target_path: StringProperty(name="New Path")
    status: EnumProperty(name="Status", items=STATUS_ITEMS, default='SAME')
    enabled: BoolProperty(
        name="Include", default=True,
        description="Include this library when relinking")


class LIBRELINK_PG_settings(PropertyGroup):
    new_dir: StringProperty(
        name="New Folder", subtype='DIR_PATH',
        description="Folder the linked libraries should point to")
    old_dir_filter: StringProperty(
        name="Only From", subtype='DIR_PATH',
        description="Only touch libraries currently inside this folder "
                    "(empty = consider all linked libraries)")
    make_relative: BoolProperty(
        name="Relative Paths", default=False,
        description="Store the new library paths relative to this .blend file")
    plan: CollectionProperty(type=LIBRELINK_PG_plan_item)
    plan_index: IntProperty(default=0)


classes = (
    LIBRELINK_PG_plan_item,
    LIBRELINK_PG_settings,
)
