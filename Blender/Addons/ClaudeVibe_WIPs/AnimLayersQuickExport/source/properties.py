import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)


SCOPE_ITEMS = [
    ("ACTIVE_ONLY", "Active Armature Only", "Export only the active armature"),
    ("ACTIVE_AND_CHILDREN", "Active Armature + Children",
     "Export the active armature and everything parented to it"),
    ("SELECTED_ARMATURES", "Selected Armatures + Children",
     "Export every selected armature and everything parented to each"),
]

FILENAME_SOURCE_ITEMS = [
    ("ACTION", "Action Name", "Use one of the layer's action names as the base filename — see Layer Source"),
    ("ARMATURE", "Armature Name", "Use the armature object's name as the base filename"),
    ("CUSTOM", "Custom", "Use the user-supplied custom name"),
]

FILENAME_LAYER_SOURCE_ITEMS = [
    ("ACTIVE", "Active Layer", "Use the currently selected layer's action name (the one highlighted in the Animation Layers list)"),
    ("BASE", "Base Layer", "Use the base (first) layer's action name"),
]

EXPORT_MODE_ITEMS = [
    ("MERGED", "Merged",
     "Bake all Animation Layers into one merged clip and export a single FBX. "
     "Best for Unity/UE workflows that take one combined animation per file."),
    ("PER_LAYER", "Per Layer",
     "Export each Animation Layer as its own FBX file (vanilla per-action workflow). "
     "Filenames are derived per layer using the same prefix/suffix conventions."),
]


class ALQEProperties(bpy.types.PropertyGroup):

    export_path: StringProperty(
        name="Export Path",
        description="Folder the FBX file(s) are written to",
        default="//exports/",
        subtype="DIR_PATH",
    )

    export_mode: EnumProperty(
        name="Export Mode",
        description="Whether to bake all layers into one merged FBX or to export each layer as its own FBX",
        items=EXPORT_MODE_ITEMS,
        default="MERGED",
    )

    filename_source: EnumProperty(
        name="Filename Source",
        description="How to derive the FBX filename",
        items=FILENAME_SOURCE_ITEMS,
        default="ACTION",
    )

    filename_layer_source: EnumProperty(
        name="Layer Source",
        description="In Merged mode with Action filename source, which layer's action name to use",
        items=FILENAME_LAYER_SOURCE_ITEMS,
        default="ACTIVE",
    )

    custom_filename: StringProperty(
        name="Custom Filename",
        description="Used when Filename Source is set to Custom",
        default="anim",
    )

    filename_prefix: StringProperty(
        name="Prefix",
        description="Prepended to the resolved filename",
        default="",
    )

    filename_suffix: StringProperty(
        name="Suffix",
        description="Appended to the resolved filename (before the .fbx extension)",
        default="",
    )

    scope: EnumProperty(
        name="Scope",
        description="What to include in the export",
        items=SCOPE_ITEMS,
        default="ACTIVE_AND_CHILDREN",
    )

    bake_step: IntProperty(
        name="Bake Step",
        description="Bake every Nth frame during the layer merge",
        default=1,
        min=1,
        max=20,
    )

    smartbake: BoolProperty(
        name="Smart Bake",
        description="Use Animation Layers' smart bake (preserves keyframe density)",
        default=False,
    )

    bake_anim_use_all_bones: BoolProperty(
        name="All Bones",
        description="Force exporting at least one key of animation for all bones",
        default=True,
    )

    bake_anim_use_nla_strips: BoolProperty(
        name="NLA Strips",
        description="Export each non-muted NLA strip as a separated FBX AnimStack",
        default=False,
    )

    bake_anim_use_all_actions: BoolProperty(
        name="All Actions",
        description="Export each action as a separated FBX AnimStack",
        default=False,
    )

    bake_anim_force_startend_keying: BoolProperty(
        name="Force Start/End Keying",
        description="Always add a keyframe at start and end of the action",
        default=True,
    )

    bake_anim_step: FloatProperty(
        name="FBX Sampling Rate",
        description="How often, in frames, to evaluate animation during export",
        default=1.0,
        min=0.01,
        max=100.0,
    )

    bake_anim_simplify_factor: FloatProperty(
        name="Simplify",
        description="Curve simplification (0 = disable)",
        default=1.0,
        min=0.0,
        max=100.0,
    )

    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Append a final bone to the end of each chain",
        default=False,
    )

    primary_bone_axis: EnumProperty(
        name="Primary Bone Axis",
        items=[(a, a, "") for a in ("X", "Y", "Z", "-X", "-Y", "-Z")],
        default="Y",
    )

    secondary_bone_axis: EnumProperty(
        name="Secondary Bone Axis",
        items=[(a, a, "") for a in ("X", "Y", "Z", "-X", "-Y", "-Z")],
        default="X",
    )

    armature_nodetype: EnumProperty(
        name="Armature FBXNode Type",
        items=[
            ("NULL", "Null", "Armature exported as 'Null'"),
            ("ROOT", "Root", "Armature exported as 'Root'"),
            ("LIMBNODE", "LimbNode", "Armature exported as 'LimbNode'"),
        ],
        default="NULL",
    )

    apply_unit_scale: BoolProperty(
        name="Apply Unit Scale",
        description="Take into account current Blender units settings",
        default=True,
    )

    apply_scale_options: EnumProperty(
        name="Apply Scalings",
        items=[
            ("FBX_SCALE_NONE", "All Local", "Apply custom scaling to FBX scale"),
            ("FBX_SCALE_UNITS", "FBX Units Scale", "Apply custom scaling to FBX scale (matrix only)"),
            ("FBX_SCALE_CUSTOM", "FBX Custom Scale", "Apply custom scaling to FBX root"),
            ("FBX_SCALE_ALL", "FBX All", "Apply both unit and custom scalings"),
        ],
        default="FBX_SCALE_NONE",
    )

    bake_space_transform: BoolProperty(
        name="Apply Transform",
        description="Bake space transform into object data (experimental)",
        default=False,
    )

    axis_forward: EnumProperty(
        name="Forward Axis",
        items=[(a, a, "") for a in ("X", "Y", "Z", "-X", "-Y", "-Z")],
        default="-Z",
    )

    axis_up: EnumProperty(
        name="Up Axis",
        items=[(a, a, "") for a in ("X", "Y", "Z", "-X", "-Y", "-Z")],
        default="Y",
    )

    path_mode: EnumProperty(
        name="Path Mode",
        items=[
            ("AUTO", "Auto", ""),
            ("ABSOLUTE", "Absolute", ""),
            ("RELATIVE", "Relative", ""),
            ("MATCH", "Match", ""),
            ("STRIP", "Strip Path", ""),
            ("COPY", "Copy", ""),
        ],
        default="AUTO",
    )

    show_fbx_animation_settings: BoolProperty(
        name="Show FBX Animation Settings",
        description="Expand the FBX animation export settings panel",
        default=False,
    )

    show_fbx_armature_settings: BoolProperty(
        name="Show FBX Armature Settings",
        description="Expand the FBX armature export settings panel",
        default=False,
    )

    show_fbx_general_settings: BoolProperty(
        name="Show FBX General Settings",
        description="Expand the FBX general export settings panel",
        default=False,
    )


classes = (ALQEProperties,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.alqe_props = bpy.props.PointerProperty(type=ALQEProperties)


def unregister():
    if hasattr(bpy.types.Scene, "alqe_props"):
        del bpy.types.Scene.alqe_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
