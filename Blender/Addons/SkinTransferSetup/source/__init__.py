# Single source of truth for the addon version. bl_info + blender_manifest.toml
# both derive from this; bump here AND in blender_manifest.toml only.
VERSION = (1, 3, 0)

bl_info = {
    "name": "Skin Transfer Setup",
    "author": "Stephan Viranyi",
    "version": VERSION,
    "blender": (4, 2, 0),
    "location": "3D View > N-Panel > Skin Transfer",
    "description": "Per-part skin setup helper: tag each mesh in a collection as As-is, Data Transfer from a weighted base model, or Bind-to-bone via Vertex Weight Edit. Stores rig + base model centrally so swapping the base retargets every transfer in one click.",
    "category": "Rigging",
}

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    PointerProperty,
    StringProperty,
)
from bpy.types import Operator, Panel, PropertyGroup


# Modifier names this addon owns. We look these up by name to update / remove
# them safely without touching user-added modifiers on the same object.
MOD_DATA_TRANSFER = "SkinTransfer_DataXfer"
MOD_VERTEX_WEIGHT = "SkinTransfer_VWEdit"


# ---------------------------------------------------------------------------
# Poll helpers for PointerProperty pickers
# ---------------------------------------------------------------------------

def _poll_armature(self, obj):
    return obj is not None and obj.type == 'ARMATURE'


def _poll_mesh(self, obj):
    return obj is not None and obj.type == 'MESH'


# ---------------------------------------------------------------------------
# Modifier management
# ---------------------------------------------------------------------------

def _remove_addon_modifier(obj, name):
    mod = obj.modifiers.get(name)
    if mod is not None:
        obj.modifiers.remove(mod)


def _ensure_vertex_group(obj, name, weight=1.0):
    """Create vertex group `name` if missing and weight every vertex to it."""
    vg = obj.vertex_groups.get(name)
    if vg is None:
        vg = obj.vertex_groups.new(name=name)
    if obj.data and obj.data.vertices:
        vg.add([v.index for v in obj.data.vertices], weight, 'REPLACE')
    return vg


def _apply_transfer(obj, base_model):
    """Configure obj with a Data Transfer modifier sourcing all vertex
    groups from base_model. Removes any bind-to-bone modifier first.
    Reads vert_mapping + ray_radius from the per-object settings."""
    _remove_addon_modifier(obj, MOD_VERTEX_WEIGHT)

    mod = obj.modifiers.get(MOD_DATA_TRANSFER)
    if mod is None:
        mod = obj.modifiers.new(name=MOD_DATA_TRANSFER, type='DATA_TRANSFER')

    st = obj.skin_transfer
    mod.object = base_model
    mod.use_vert_data = True
    mod.data_types_verts = {'VGROUP_WEIGHTS'}
    mod.vert_mapping = st.transfer_vert_mapping
    mod.layers_vgroup_select_src = 'ALL'
    mod.layers_vgroup_select_dst = 'NAME'
    mod.mix_mode = 'REPLACE'
    mod.mix_factor = 1.0
    mod.ray_radius = st.transfer_ray_radius


def _apply_bind_to_bone(obj, bone_name, scene_props):
    """Configure obj with a Vertex Weight Edit modifier pinning every vert
    to `bone_name` at weight 1.0. Removes the Data Transfer modifier first.
    Honors auto_create / auto_strip toggles when the bone differs from the
    one the modifier currently references."""
    _remove_addon_modifier(obj, MOD_DATA_TRANSFER)

    if not bone_name:
        # No bone picked yet — clean slate so the user sees they need to choose.
        _remove_addon_modifier(obj, MOD_VERTEX_WEIGHT)
        return

    mod = obj.modifiers.get(MOD_VERTEX_WEIGHT)
    prev_bone = mod.vertex_group if mod is not None else ""

    if scene_props.auto_create_vg_on_bone_change:
        _ensure_vertex_group(obj, bone_name, weight=1.0)

    if mod is None:
        mod = obj.modifiers.new(name=MOD_VERTEX_WEIGHT, type='VERTEX_WEIGHT_EDIT')

    mod.vertex_group = bone_name
    mod.default_weight = 1.0
    mod.use_add = True
    mod.add_threshold = 0.0
    mod.use_remove = False

    # Strip the prior bone's VG only when (a) it actually changed,
    # (b) the toggle is on, and (c) the prior name was a rig bone (so we
    # don't nuke a user-named group that happened to share the bone slot).
    if (scene_props.auto_strip_vg_on_bone_change
            and prev_bone
            and prev_bone != bone_name
            and prev_bone in _rig_bone_names(scene_props)):
        vg = obj.vertex_groups.get(prev_bone)
        if vg is not None:
            obj.vertex_groups.remove(vg)


def _apply_skin_setup(obj, scene_props):
    """Dispatch on mode and update/clean modifiers accordingly."""
    if obj is None or obj.type != 'MESH':
        return
    mode = obj.skin_transfer.mode
    if mode == 'AS_IS':
        _remove_addon_modifier(obj, MOD_DATA_TRANSFER)
        _remove_addon_modifier(obj, MOD_VERTEX_WEIGHT)
    elif mode == 'TRANSFER':
        _apply_transfer(obj, scene_props.base_model)
    elif mode == 'BIND_TO_BONE':
        _apply_bind_to_bone(obj, obj.skin_transfer.bone, scene_props)


def _retarget_all_transfer_objects(scene_props):
    """Walk every mesh tagged TRANSFER and point its Data Transfer modifier
    at the current base_model. Called when base_model changes."""
    base = scene_props.base_model
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        st = getattr(obj, 'skin_transfer', None)
        if st is None or st.mode != 'TRANSFER':
            continue
        mod = obj.modifiers.get(MOD_DATA_TRANSFER)
        if mod is not None:
            mod.object = base


# ---------------------------------------------------------------------------
# Vertex group ensure / strip
# ---------------------------------------------------------------------------

def _rig_bone_names(scene_props):
    rig = scene_props.rig
    if rig is None or rig.type != 'ARMATURE':
        return set()
    return {b.name for b in rig.data.bones}


def _base_model_vgroup_names(scene_props):
    base = scene_props.base_model
    if base is None or base.type != 'MESH':
        return set()
    return {vg.name for vg in base.vertex_groups}


def _strip_keep_set(obj, scene_props):
    """Bone-named VGs the addon considers 'in use' for `obj` and therefore
    must NOT strip. Returns None to mean 'skip stripping this object'.

    Bind-to-Bone: just the bound bone.
    Transfer: only bones the weighted base model actually has weights for —
    everything else the data transfer would never write to.
    As-is: skipped entirely (user opted out of addon-managed setup)."""
    mode = obj.skin_transfer.mode
    if mode == 'BIND_TO_BONE':
        bone = obj.skin_transfer.bone
        return {bone} if bone else set()
    if mode == 'TRANSFER':
        return _base_model_vgroup_names(scene_props)
    return None


def _ensure_vgroups_for_mesh(obj, scene_props):
    """Make sure the VGs required by `obj`'s mode exist.

    Bind-to-Bone: ensure the bound bone exists and is fully weighted.
    Transfer: ensure an empty VG exists for each bone the data transfer will
    actually populate. When `bone_filter_weighted_only` is on (default), that's
    `rig_bones ∩ base_model_vgs` — control bones aren't created. When off,
    every rig bone gets a VG.
    As-is: nothing to do."""
    if obj is None or obj.type != 'MESH':
        return
    mode = obj.skin_transfer.mode
    if mode == 'BIND_TO_BONE':
        bone = obj.skin_transfer.bone
        if bone:
            _ensure_vertex_group(obj, bone, weight=1.0)
        return
    if mode == 'TRANSFER':
        bones = _rig_bone_names(scene_props)
        if scene_props.bone_filter_weighted_only:
            bones &= _base_model_vgroup_names(scene_props)
        for name in bones:
            if obj.vertex_groups.get(name) is None:
                obj.vertex_groups.new(name=name)


def _selected_meshes(context):
    """Mesh objects the panel actions should act on. Prefers `selected_objects`
    filtered to MESH; falls back to `[active_object]` when nothing useful is
    selected. Empty list if neither yields a mesh."""
    meshes = [o for o in context.selected_objects if o.type == 'MESH']
    if meshes:
        return meshes
    act = context.active_object
    if act is not None and act.type == 'MESH':
        return [act]
    return []


def _rebuild_weighted_bones_cache(scene_props):
    """Refill `weighted_bones` with the intersection of rig bone names and
    base model VG names — i.e. bones the base model has weights for. This is
    what the filtered bone picker sees."""
    coll = scene_props.weighted_bones
    coll.clear()
    weighted = sorted(_rig_bone_names(scene_props) & _base_model_vgroup_names(scene_props))
    for name in weighted:
        item = coll.add()
        item.name = name


def _strip_unused_vgroups_for_mesh(obj, scene_props):
    """Remove bone-named VGs not in this mesh's keep-set. Non-bone-named
    groups (shape keys, edge selections, user data) are always preserved.
    Returns count removed. No-op if no rig is set (can't classify names)."""
    if obj is None or obj.type != 'MESH':
        return 0
    keep = _strip_keep_set(obj, scene_props)
    if keep is None:
        return 0
    bones = _rig_bone_names(scene_props)
    if not bones:
        return 0
    removed = 0
    for vg in list(obj.vertex_groups):
        if vg.name in bones and vg.name not in keep:
            obj.vertex_groups.remove(vg)
            removed += 1
    return removed


# ---------------------------------------------------------------------------
# Property update callbacks
# ---------------------------------------------------------------------------

def _on_object_mode_update(self, context):
    obj = self.id_data
    if isinstance(obj, bpy.types.Object):
        _apply_skin_setup(obj, context.scene.skin_transfer_props)


def _on_object_bone_update(self, context):
    # Only re-apply if currently in bind-to-bone mode; otherwise the bone
    # field is just dormant state we don't want to act on.
    obj = self.id_data
    if isinstance(obj, bpy.types.Object) and self.mode == 'BIND_TO_BONE':
        _apply_skin_setup(obj, context.scene.skin_transfer_props)


def _on_object_transfer_param_update(self, context):
    # Re-apply only when the object is currently in Transfer mode — the
    # modifier needs to pick up the new vert_mapping / ray_radius.
    obj = self.id_data
    if isinstance(obj, bpy.types.Object) and self.mode == 'TRANSFER':
        _apply_skin_setup(obj, context.scene.skin_transfer_props)


def _on_base_model_update(self, context):
    _retarget_all_transfer_objects(self)
    _rebuild_weighted_bones_cache(self)


def _on_rig_update(self, context):
    _rebuild_weighted_bones_cache(self)


def _on_bone_filter_update(self, context):
    if self.bone_filter_weighted_only:
        _rebuild_weighted_bones_cache(self)


# ---------------------------------------------------------------------------
# Property groups
# ---------------------------------------------------------------------------

class WeightedBoneItem(PropertyGroup):
    """One entry in the filtered bone picker — a bone name the base model
    actually has weights for."""
    name: StringProperty()


class SkinTransferObjectProps(PropertyGroup):
    mode: EnumProperty(
        name="Mode",
        description="How weights are assigned to this mesh",
        items=[
            ('AS_IS', "As-is",
             "Use this mesh's existing vertex groups; no modifier added"),
            ('TRANSFER', "Transfer",
             "Data Transfer of all vertex groups from the weighted base model"),
            ('BIND_TO_BONE', "Bind to Bone",
             "Vertex Weight Edit pinning every vertex to a single bone at weight 1.0"),
        ],
        default='AS_IS',
        update=_on_object_mode_update,
    )
    bone: StringProperty(
        name="Bone",
        description="Bone to bind this mesh to (used when Mode = Bind to Bone)",
        default="",
        update=_on_object_bone_update,
    )
    transfer_vert_mapping: EnumProperty(
        name="Vertex Mapping",
        description="How source vertices map onto this mesh (Data Transfer modifier's vert_mapping field)",
        items=[
            ('NEAREST', "Nearest Vertex", "Pick the closest source vertex"),
            ('EDGE_NEAREST', "Nearest Edge Vertex", "Pick the closest vertex on the closest source edge"),
            ('EDGEINTERP_NEAREST', "Nearest Edge Interpolated", "Interpolate along the closest source edge"),
            ('POLY_NEAREST', "Nearest Face Vertex", "Pick the closest vertex on the closest source face"),
            ('POLYINTERP_NEAREST', "Nearest Face Interpolated", "Interpolate within the closest source face"),
            ('POLYINTERP_VNORPROJ', "Projected Face Interpolated", "Project along vertex normal onto source face (uses Ray Radius)"),
            ('TOPOLOGY', "Topology", "Match by vertex index — requires identical topology"),
        ],
        default='NEAREST',
        update=_on_object_transfer_param_update,
    )
    transfer_ray_radius: FloatProperty(
        name="Ray Radius",
        description="Ray radius for projection-based vertex mapping (only used by Projected Face Interpolated)",
        default=0.5,
        min=0.0,
        soft_max=10.0,
        subtype='DISTANCE',
        update=_on_object_transfer_param_update,
    )


class SkinTransferSceneProps(PropertyGroup):
    rig: PointerProperty(
        name="Rig",
        description="Armature the meshes will deform with — bone picker pulls from here",
        type=bpy.types.Object,
        poll=_poll_armature,
        update=_on_rig_update,
    )
    base_model: PointerProperty(
        name="Weighted Base Model",
        description="Mesh holding vertex groups for every bone — used as the Data Transfer source. Changing this re-targets every Transfer object",
        type=bpy.types.Object,
        poll=_poll_mesh,
        update=_on_base_model_update,
    )
    active_collection: PointerProperty(
        name="Collection",
        description="Collection to batch-configure parts in",
        type=bpy.types.Collection,
    )
    refresh_with_vgroup_cleanup: BoolProperty(
        name="Also Ensure / Strip VGs",
        description=("When refreshing, also ensure the bind setup's required "
                     "vertex groups exist AND strip bone-named groups not "
                     "used by the current setup (non-bone-named groups are "
                     "preserved)"),
        default=False,
    )
    bone_filter_weighted_only: BoolProperty(
        name="Only Weighted Bones",
        description=("Filter the Bind-to-Bone picker to bones the weighted "
                     "base model actually has vertex groups for — i.e. "
                     "deformation bones only, no control bones"),
        default=True,
        update=_on_bone_filter_update,
    )
    weighted_bones: CollectionProperty(type=WeightedBoneItem)
    auto_create_vg_on_bone_change: BoolProperty(
        name="Auto-Create VG",
        description=("When the bound bone changes, ensure the new bone's "
                     "vertex group exists and is fully weighted"),
        default=True,
    )
    auto_strip_vg_on_bone_change: BoolProperty(
        name="Auto-Strip Prior VG",
        description=("When the bound bone changes, remove the previously "
                     "bound bone's vertex group (only if its name matches a "
                     "rig bone — protects user-named groups)"),
        default=True,
    )


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

class SKINTRANSFER_OT_refresh_targets(Operator):
    bl_idname = "skintransfer.refresh_targets"
    bl_label = "Refresh All Transfer Targets"
    bl_description = ("Walk every Transfer / Bind-to-Bone tagged object and "
                      "rebuild its addon modifier from current settings")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.skin_transfer_props
        do_cleanup = props.refresh_with_vgroup_cleanup
        count = 0
        stripped = 0
        for obj in bpy.data.objects:
            if obj.type != 'MESH':
                continue
            if not hasattr(obj, 'skin_transfer'):
                continue
            _apply_skin_setup(obj, props)
            count += 1
            if do_cleanup:
                _ensure_vgroups_for_mesh(obj, props)
                stripped += _strip_unused_vgroups_for_mesh(obj, props)
        if do_cleanup:
            self.report({'INFO'},
                        f"Refreshed {count} mesh(es); stripped {stripped} VG(s)")
        else:
            self.report({'INFO'}, f"Refreshed Skin Transfer setup on {count} mesh(es)")
        return {'FINISHED'}


class SKINTRANSFER_OT_apply_selected(Operator):
    bl_idname = "skintransfer.apply_selected"
    bl_label = "Re-apply"
    bl_description = ("Rebuild the Skin Transfer modifier on every selected "
                      "mesh from its current mode (falls back to active if "
                      "nothing is selected)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(_selected_meshes(context))

    def execute(self, context):
        props = context.scene.skin_transfer_props
        meshes = _selected_meshes(context)
        for obj in meshes:
            _apply_skin_setup(obj, props)
        self.report({'INFO'}, f"Re-applied on {len(meshes)} mesh(es)")
        return {'FINISHED'}


class SKINTRANSFER_OT_clear_selected(Operator):
    bl_idname = "skintransfer.clear_selected"
    bl_label = "Clear"
    bl_description = ("Reset every selected mesh to As-is and remove its "
                      "Skin Transfer modifiers")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(_selected_meshes(context))

    def execute(self, context):
        meshes = _selected_meshes(context)
        # Setting mode triggers the update callback which removes modifiers.
        for obj in meshes:
            obj.skin_transfer.mode = 'AS_IS'
        self.report({'INFO'}, f"Cleared {len(meshes)} mesh(es)")
        return {'FINISHED'}


class SKINTRANSFER_OT_refresh_bone_filter(Operator):
    bl_idname = "skintransfer.refresh_bone_filter"
    bl_label = "Refresh Weighted Bone List"
    bl_description = ("Re-scan the weighted base model and rebuild the "
                      "filtered bone picker (use after editing weights on the "
                      "base model)")
    bl_options = {'REGISTER'}

    def execute(self, context):
        _rebuild_weighted_bones_cache(context.scene.skin_transfer_props)
        return {'FINISHED'}


class SKINTRANSFER_OT_create_vgroups_selected(Operator):
    bl_idname = "skintransfer.create_vgroups_selected"
    bl_label = "Create VG"
    bl_description = ("Create the vertex groups required by each selected "
                      "mesh's bind setup (Bind: the bound bone fully weighted; "
                      "Transfer: an empty VG for each bone the data transfer "
                      "will populate — weighted-bones only by default, "
                      "or every rig bone if the filter is off)")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(_selected_meshes(context))

    def execute(self, context):
        props = context.scene.skin_transfer_props
        meshes = _selected_meshes(context)
        for obj in meshes:
            _ensure_vgroups_for_mesh(obj, props)
        self.report({'INFO'}, f"Created VGs on {len(meshes)} mesh(es)")
        return {'FINISHED'}


class SKINTRANSFER_OT_strip_unused_selected(Operator):
    bl_idname = "skintransfer.strip_unused_selected"
    bl_label = "Strip Unused"
    bl_description = ("Remove bone-named vertex groups not used by each "
                      "selected mesh's bind setup. Non-bone-named groups "
                      "(shape keys, edge selections, user data) are preserved")
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return bool(_selected_meshes(context))

    def execute(self, context):
        props = context.scene.skin_transfer_props
        if props.rig is None:
            self.report({'ERROR'}, "Pick a Rig first — needed to classify which VGs are bone groups")
            return {'CANCELLED'}
        meshes = _selected_meshes(context)
        total = 0
        for obj in meshes:
            total += _strip_unused_vgroups_for_mesh(obj, props)
        self.report({'INFO'}, f"Stripped {total} vertex group(s) across {len(meshes)} mesh(es)")
        return {'FINISHED'}


class SKINTRANSFER_OT_strip_unused_collection(Operator):
    bl_idname = "skintransfer.strip_unused_collection"
    bl_label = "Strip Unused (Collection)"
    bl_description = ("Walk every mesh in the active collection and strip its "
                      "bone-named vertex groups not used by its bind setup")
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        props = context.scene.skin_transfer_props
        coll = props.active_collection
        if coll is None:
            self.report({'ERROR'}, "Pick a collection first")
            return {'CANCELLED'}
        if props.rig is None:
            self.report({'ERROR'}, "Pick a Rig first — needed to classify which VGs are bone groups")
            return {'CANCELLED'}
        total = 0
        meshes = 0
        for obj in coll.all_objects:
            if obj.type != 'MESH':
                continue
            meshes += 1
            total += _strip_unused_vgroups_for_mesh(obj, props)
        self.report({'INFO'}, f"Stripped {total} vertex group(s) across {meshes} mesh(es)")
        return {'FINISHED'}


class SKINTRANSFER_OT_set_mode_selected(Operator):
    bl_idname = "skintransfer.set_mode_selected"
    bl_label = "Set Mode for Selected"
    bl_description = "Set every selected mesh to the chosen mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name="Mode",
        items=[
            ('AS_IS', "As-is", ""),
            ('TRANSFER', "Transfer", ""),
            ('BIND_TO_BONE', "Bind to Bone", ""),
        ],
    )

    @classmethod
    def poll(cls, context):
        return bool(_selected_meshes(context))

    def execute(self, context):
        meshes = _selected_meshes(context)
        for obj in meshes:
            obj.skin_transfer.mode = self.mode
        self.report({'INFO'}, f"Set {len(meshes)} mesh(es) to {self.mode}")
        return {'FINISHED'}


class SKINTRANSFER_OT_set_mode_batch(Operator):
    bl_idname = "skintransfer.set_mode_batch"
    bl_label = "Set Mode for All in Collection"
    bl_description = "Set every mesh in the active collection to the chosen mode"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name="Mode",
        items=[
            ('AS_IS', "As-is", ""),
            ('TRANSFER', "Transfer", ""),
            ('BIND_TO_BONE', "Bind to Bone", ""),
        ],
    )

    def execute(self, context):
        props = context.scene.skin_transfer_props
        coll = props.active_collection
        if coll is None:
            self.report({'ERROR'}, "Pick a collection first")
            return {'CANCELLED'}
        count = 0
        for obj in coll.all_objects:
            if obj.type != 'MESH':
                continue
            obj.skin_transfer.mode = self.mode
            count += 1
        self.report({'INFO'}, f"Set {count} object(s) to {self.mode}")
        return {'FINISHED'}


# ---------------------------------------------------------------------------
# Panels
# ---------------------------------------------------------------------------

class SKINTRANSFER_PT_main(Panel):
    bl_label = "Skin Transfer"
    bl_idname = "SKINTRANSFER_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skin Transfer"

    def draw(self, context):
        layout = self.layout
        props = context.scene.skin_transfer_props

        col = layout.column(align=True)
        col.prop(props, "rig")
        col.prop(props, "base_model")

        filter_row = layout.row(align=True)
        filter_row.prop(props, "bone_filter_weighted_only", toggle=True,
                        icon='FILTER')
        sub = filter_row.row(align=True)
        sub.enabled = props.bone_filter_weighted_only
        sub.operator("skintransfer.refresh_bone_filter", text="",
                     icon='FILE_REFRESH')

        layout.separator()
        layout.operator("skintransfer.refresh_targets", icon='FILE_REFRESH')
        layout.prop(props, "refresh_with_vgroup_cleanup")


class SKINTRANSFER_PT_active_object(Panel):
    bl_label = "Selection"
    bl_idname = "SKINTRANSFER_PT_active_object"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skin Transfer"
    bl_parent_id = "SKINTRANSFER_PT_main"

    def draw(self, context):
        layout = self.layout
        scene_props = context.scene.skin_transfer_props
        meshes = _selected_meshes(context)

        if not meshes:
            layout.label(text="Select a mesh object", icon='INFO')
            return

        # Multi-selection: header + bulk mode setter
        if len(meshes) > 1:
            layout.label(text=f"{len(meshes)} meshes selected", icon='MESH_DATA')
            layout.label(text="Set mode for all:")
            row = layout.row(align=True)
            op = row.operator("skintransfer.set_mode_selected", text="As-is")
            op.mode = 'AS_IS'
            op = row.operator("skintransfer.set_mode_selected", text="Transfer")
            op.mode = 'TRANSFER'
            op = row.operator("skintransfer.set_mode_selected", text="Bind")
            op.mode = 'BIND_TO_BONE'
            layout.separator()

        # Per-active controls (mode dropdown + bone picker for the active mesh)
        active = context.active_object
        active_is_mesh = active is not None and active.type == 'MESH'

        if active_is_mesh:
            layout.label(text=f"Active: {active.name}", icon='MESH_DATA')
            layout.prop(active.skin_transfer, "mode", text="Mode")

            if active.skin_transfer.mode == 'BIND_TO_BONE':
                row = layout.row()
                if scene_props.rig and scene_props.rig.type == 'ARMATURE':
                    if scene_props.bone_filter_weighted_only and scene_props.base_model:
                        row.prop_search(active.skin_transfer, "bone",
                                        scene_props, "weighted_bones", text="Bone")
                    else:
                        row.prop_search(active.skin_transfer, "bone",
                                        scene_props.rig.data, "bones", text="Bone")
                else:
                    row.enabled = False
                    row.label(text="Pick a rig first", icon='ERROR')

                auto_col = layout.column(align=True)
                auto_col.prop(scene_props, "auto_create_vg_on_bone_change")
                auto_col.prop(scene_props, "auto_strip_vg_on_bone_change")

            elif active.skin_transfer.mode == 'TRANSFER':
                xfer_col = layout.column(align=True)
                xfer_col.prop(active.skin_transfer, "transfer_vert_mapping",
                              text="Mapping")
                xfer_col.prop(active.skin_transfer, "transfer_ray_radius",
                              text="Ray Radius")
        else:
            layout.label(text="(no active mesh — actions apply to selection)",
                         icon='INFO')

        layout.separator()
        row = layout.row(align=True)
        row.operator("skintransfer.apply_selected", icon='FILE_REFRESH')
        row.operator("skintransfer.clear_selected", icon='X')

        vg_row = layout.row(align=True)
        vg_row.operator("skintransfer.create_vgroups_selected", icon='GROUP_VERTEX')
        vg_row.operator("skintransfer.strip_unused_selected", icon='TRASH')

        # Status: what addon-owned modifiers are present on the active mesh
        if active_is_mesh:
            header, body = layout.panel("skintransfer_active_status", default_closed=True)
            header.label(text="Modifier Status", icon='MODIFIER')
            if body is not None:
                dx = active.modifiers.get(MOD_DATA_TRANSFER)
                vw = active.modifiers.get(MOD_VERTEX_WEIGHT)
                if dx is None and vw is None:
                    body.label(text="No Skin Transfer modifiers", icon='RADIOBUT_OFF')
                if dx is not None:
                    target = dx.object.name if dx.object else "<missing>"
                    body.label(text=f"Data Transfer → {target}",
                               icon='MOD_DATA_TRANSFER')
                if vw is not None:
                    body.label(text=f"Vertex Weight Edit → {vw.vertex_group or '<none>'}",
                               icon='MOD_VERTEX_WEIGHT')


class SKINTRANSFER_PT_batch(Panel):
    bl_label = "Batch by Collection"
    bl_idname = "SKINTRANSFER_PT_batch"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Skin Transfer"
    bl_parent_id = "SKINTRANSFER_PT_main"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.skin_transfer_props

        layout.prop(props, "active_collection", text="Collection")
        coll = props.active_collection
        if coll is None:
            layout.label(text="Pick a collection to list parts", icon='INFO')
            return

        header, body = layout.panel("skintransfer_batch_setall", default_closed=True)
        header.label(text="Set all to…", icon='COLLAPSEMENU')
        if body is not None:
            row = body.row(align=True)
            op = row.operator("skintransfer.set_mode_batch", text="As-is")
            op.mode = 'AS_IS'
            op = row.operator("skintransfer.set_mode_batch", text="Transfer")
            op.mode = 'TRANSFER'
            op = row.operator("skintransfer.set_mode_batch", text="Bind")
            op.mode = 'BIND_TO_BONE'

        layout.operator("skintransfer.strip_unused_collection", icon='TRASH')

        layout.separator()
        layout.label(text="Parts:")

        mesh_count = 0
        for obj in coll.all_objects:
            if obj.type != 'MESH':
                continue
            mesh_count += 1
            row = layout.row(align=True)
            row.label(text=obj.name, icon='MESH_DATA')
            row.prop(obj.skin_transfer, "mode", text="")
            if obj.skin_transfer.mode == 'BIND_TO_BONE':
                if props.rig and props.rig.type == 'ARMATURE':
                    if props.bone_filter_weighted_only and props.base_model:
                        row.prop_search(obj.skin_transfer, "bone",
                                        props, "weighted_bones", text="")
                    else:
                        row.prop_search(obj.skin_transfer, "bone",
                                        props.rig.data, "bones", text="")
                else:
                    row.label(text="", icon='ERROR')

        if mesh_count == 0:
            layout.label(text="(no meshes in this collection)", icon='INFO')


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

classes = [
    WeightedBoneItem,
    SkinTransferObjectProps,
    SkinTransferSceneProps,
    SKINTRANSFER_OT_refresh_targets,
    SKINTRANSFER_OT_refresh_bone_filter,
    SKINTRANSFER_OT_apply_selected,
    SKINTRANSFER_OT_clear_selected,
    SKINTRANSFER_OT_create_vgroups_selected,
    SKINTRANSFER_OT_strip_unused_selected,
    SKINTRANSFER_OT_strip_unused_collection,
    SKINTRANSFER_OT_set_mode_selected,
    SKINTRANSFER_OT_set_mode_batch,
    SKINTRANSFER_PT_main,
    SKINTRANSFER_PT_active_object,
    SKINTRANSFER_PT_batch,
]


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.skin_transfer_props = PointerProperty(type=SkinTransferSceneProps)
    bpy.types.Object.skin_transfer = PointerProperty(type=SkinTransferObjectProps)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.skin_transfer_props
    del bpy.types.Object.skin_transfer


if __name__ == "__main__":
    register()
