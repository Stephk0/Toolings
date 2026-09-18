import bpy
from bpy.props import (
    BoolProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    IntVectorProperty,
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
    ("ACTION", "Layer / Action Name",
     "With Animation Layers active, use the layer's display name (the one shown "
     "in the AL list). Without Animation Layers, use the rig's active action name"),
    ("ARMATURE", "Armature Name", "Use the armature object's name as the base filename"),
    ("CUSTOM", "Custom", "Use the user-supplied custom name"),
]

FILENAME_LAYER_SOURCE_ITEMS = [
    ("ACTIVE", "Active Layer", "Use the currently selected layer's action name"),
    ("BASE", "Base Layer", "Use the base (first) layer's action name"),
]

EXPORT_MODE_ITEMS = [
    ("MERGED", "Merged",
     "Bake all Animation Layers into one merged clip and export a single FBX. "
     "Without Animation Layers, exports the rig's current animation as-is."),
    ("PER_LAYER", "Per Layer",
     "Export each Animation Layer as its own FBX. Requires the Animation Layers addon."),
]

# Mirror of Animation_Layers' merge dialog enums so we can drive obj.als at merge time.
AL_BAKETYPE_ITEMS = [
    ("AL", "Anim Layers", "Use Animation Layers' bake (preserves layer keyframe density)"),
    ("NLA", "NLA Bake", "Use Blender's internal NLA bake"),
]
AL_OPERATOR_ITEMS = [
    ("MERGE", "Merge", "Merge layers down into one"),
    ("NEW", "New Baked Layer", "Bake into a new layer (preserves originals)"),
]
AL_DIRECTION_ITEMS = [
    ("ALL", "All", "Merge every layer into a single clip"),
    ("DOWN", "Down", "Merge from the active layer downwards"),
    ("UP", "Up", "Merge from the active layer upwards"),
]
AL_BAKE_RANGE_ITEMS = [
    ("SCENE", "Scene", "Use the scene's frame range"),
    ("ACTION", "Action", "Use each action's own length"),
    ("CUSTOM", "Custom", "Use a custom frame range"),
]
AL_HANDLES_ITEMS = [
    ("FREE", "Free", ""),
    ("ALIGNED", "Aligned", ""),
    ("VECTOR", "Vector", ""),
    ("AUTO", "Auto", ""),
    ("AUTO_CLAMPED", "Auto Clamped", ""),
]

# Animation clip (= FBX AnimStack) naming, configured independently from filename.
CLIP_NAME_SOURCE_ITEMS = [
    ("SAME_AS_FILENAME", "Same as Filename",
     "Use the resolved filename as the clip name. Keeps the existing behaviour "
     "where one file = one clip with the same label"),
    ("ACTION", "Layer / Action Name",
     "With Animation Layers active, use the layer's display name. Without "
     "Animation Layers, use the rig's active action name"),
    ("ARMATURE", "Armature Name", "Use the armature object's name"),
    ("CUSTOM", "Custom", "Use the user-supplied custom clip name"),
]

CLIP_LAYER_TOKEN_ITEMS = [
    ("NONE", "None", "No per-layer token in the clip name"),
    ("LAYER_NAME", "Layer Name",
     "Append the layer's display name (e.g. BasePose)"),
    ("LAYER_INDEX", "Layer Index",
     "Append the zero-padded layer index (e.g. 00, 01, 02)"),
    ("INDEX_NAME", "Index then Name",
     "Append the index then the layer name (e.g. 00_BasePose)"),
    ("NAME_INDEX", "Name then Index",
     "Append the layer name then the index (e.g. BasePose_00)"),
]


class QAEProperties(bpy.types.PropertyGroup):

    # ---- Output ----------------------------------------------------------------

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

    # ---- AL bake/merge mirror --------------------------------------------------
    # These mirror Animation_Layers' merge dialog so the user can configure the
    # full bake here. They are pushed onto obj.als / scene.als at merge-time and
    # restored along with the rest of the AL state.

    al_baketype: EnumProperty(
        name="Bake Type",
        description="Use Animation Layers' bake or Blender's NLA bake",
        items=AL_BAKETYPE_ITEMS,
        default="AL",
    )

    al_operator: EnumProperty(
        name="Bake Operator",
        description="Merge layers down or bake into a new layer",
        items=AL_OPERATOR_ITEMS,
        default="MERGE",
    )

    al_direction: EnumProperty(
        name="Direction",
        description="Direction of merge from the active layer",
        items=AL_DIRECTION_ITEMS,
        default="ALL",
    )

    al_mergefcurves: BoolProperty(
        name="Merge Cyclic & Fcurve Modifiers",
        description="Include Fcurve modifiers (cyclic, etc.) in the bake",
        default=True,
    )

    al_smartbake: BoolProperty(
        name="Smart Bake",
        description="Stay with the same amount of keyframes after merging and baking",
        default=False,
    )

    al_handles_type: EnumProperty(
        name="Smart Bake Handle Type",
        description="Handle type used by Smart Bake when recalculating handle values",
        items=AL_HANDLES_ITEMS,
        default="FREE",
    )

    al_onlyselected: BoolProperty(
        name="Only Selected Bones",
        description="Bake only selected armature controls (active object must be in pose mode)",
        default=False,
    )

    al_clearconstraints: BoolProperty(
        name="Clear Constraints",
        description="Clear constraints during bake (NLA bake only)",
        default=False,
    )

    al_actioncopy: BoolProperty(
        name="Copy Original Merged Action",
        description=(
            "Animation Layers' option to keep a copy of the original action being overwritten. "
            "Quick Animation Export already preserves and restores actions independently, so this "
            "is normally safe to leave off"
        ),
        default=False,
    )

    al_bake_range_type: EnumProperty(
        name="Frame Range",
        description="Source for the bake's frame range",
        items=AL_BAKE_RANGE_ITEMS,
        default="SCENE",
    )

    al_bake_range_custom: IntVectorProperty(
        name="Custom Range",
        description="Custom frame range used when Frame Range is set to Custom",
        size=2,
        default=(1, 250),
    )

    al_step: IntProperty(
        name="Bake Step",
        description="Bake every Nth frame during the layer merge",
        default=1,
        min=1,
        max=20,
    )

    # ---- Per-Layer extras ------------------------------------------------------
    # Sub-toggles that only matter when export_mode == PER_LAYER.

    bundle_per_layer: BoolProperty(
        name="Bundle into single FBX",
        description=(
            "Instead of one FBX per layer, write all layers as separate animation "
            "clips inside a single FBX. Each layer becomes its own AnimStack via "
            "the FBX exporter's NLA-strip mode"
        ),
        default=False,
    )

    per_layer_only_visible: BoolProperty(
        name="Only Visible Layers",
        description=(
            "Skip layers whose mute flag is on (the eye icon in the Animation "
            "Layers list). Applies to both the file-per-layer and bundled modes"
        ),
        default=False,
    )

    # ---- Clip naming -----------------------------------------------------------
    # Controls the AnimStack labels written into the FBX. Independent from the
    # filename so the user can ship "human_idle.fbx" containing a clip named
    # "00_BasePose" (or whatever convention their engine expects).

    clip_name_source: EnumProperty(
        name="Clip Source",
        description="How to derive the animation clip name(s) inside the FBX",
        items=CLIP_NAME_SOURCE_ITEMS,
        default="SAME_AS_FILENAME",
    )

    clip_custom_name: StringProperty(
        name="Custom Clip Name",
        description="Used when Clip Source is set to Custom",
        default="anim",
    )

    clip_layer_source: EnumProperty(
        name="Clip Layer Source",
        description=(
            "In Merged mode with Clip Source = Layer/Action Name, which layer's "
            "name to use as the clip base"
        ),
        items=FILENAME_LAYER_SOURCE_ITEMS,
        default="ACTIVE",
    )

    clip_prefix: StringProperty(
        name="Clip Prefix",
        description=(
            "Prepended to every clip name. Common usage: a project/rig tag like "
            "'animclip_human_'"
        ),
        default="",
    )

    clip_suffix: StringProperty(
        name="Clip Suffix",
        description="Literal string appended to every clip name AFTER the layer token",
        default="",
    )

    clip_layer_token: EnumProperty(
        name="Layer Token",
        description=(
            "Per-clip differentiator inserted between the base name and the "
            "literal suffix. Especially useful when bundling layers as multiple "
            "clips, so the engine sees distinct names"
        ),
        items=CLIP_LAYER_TOKEN_ITEMS,
        default="NONE",
    )

    clip_index_padding: IntProperty(
        name="Index Padding",
        description="Zero-pad the layer index to N digits (e.g. 2 → '00', '01')",
        default=2,
        min=0,
        max=4,
    )

    clip_index_separator: StringProperty(
        name="Token Separator",
        description=(
            "Inserted between the base name, the index, and the layer name when "
            "the token is enabled (e.g. '_' produces 'BasePose_00')"
        ),
        default="_",
    )

    # ---- FBX (animation) -------------------------------------------------------

    bake_anim: BoolProperty(
        name="Baked Animation",
        description=(
            "Export baked keyframe animation. Master toggle for the FBX exporter's "
            "animation block — disable to ship a rest-pose-only FBX"
        ),
        default=True,
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

    # ---- FBX (armature) --------------------------------------------------------

    add_leaf_bones: BoolProperty(
        name="Add Leaf Bones",
        description="Append a final bone to the end of each chain",
        default=False,
    )

    use_armature_deform_only: BoolProperty(
        name="Only Deform Bones",
        description=(
            "Only write deforming bones (and any non-deforming bones on the path "
            "between them). Matches the FBX exporter's 'Only Deform Bones' option — "
            "strips control rig bones from the export"
        ),
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

    # ---- FBX (general) ---------------------------------------------------------

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
        default="FBX_SCALE_UNITS",
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

    # ---- UI fold state ---------------------------------------------------------

    show_bake_settings: BoolProperty(
        name="Show Bake/Merge Settings",
        description="Expand the Animation Layers bake/merge settings",
        default=True,
    )

    show_clip_settings: BoolProperty(
        name="Show Clip Name Settings",
        description="Expand the animation clip naming settings",
        default=True,
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


classes = (QAEProperties,)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.qae_props = bpy.props.PointerProperty(type=QAEProperties)


def unregister():
    if hasattr(bpy.types.Scene, "qae_props"):
        del bpy.types.Scene.qae_props
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
