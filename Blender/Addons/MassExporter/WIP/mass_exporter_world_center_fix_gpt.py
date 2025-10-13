# SPDX-License-Identifier: MIT
# Mass Exporter — World-Space Empty Centering (Fixed)
# Save as: mass_exporter_world_center_fix.py

bl_info = {
    "name": "Mass Exporter (World-Space Empty Centering)",
    "author": "You + ChatGPT",
    "version": (1, 1, 0),
    "blender": (3, 0, 0),
    "location": "3D Viewport > N-panel > Mass Exporter",
    "description": "Exports groups parented to empties. Temporarily moves parent empties to WORLD origin, exports, then restores exactly.",
    "warning": "",
    "doc_url": "",
    "category": "Import-Export",
}

import bpy
import os
from bpy.types import Operator, Panel, PropertyGroup
from bpy.props import (
    BoolProperty,
    EnumProperty,
    StringProperty,
    PointerProperty,
)
from mathutils import Vector

# ---------------------------
# Helpers
# ---------------------------

def ensure_object_mode():
    try:
        if bpy.ops.object.mode_set.poll():
            bpy.ops.object.mode_set(mode='OBJECT')
    except Exception:
        pass

def iter_parent_empties_with_mesh_children(objects=None):
    """
    Yields (empty, [mesh_children]) for each EMPTY that has at least one MESH child.
    If 'objects' is provided, only consider empties from that iterable; otherwise scans scene.
    """
    if objects is None:
        objects = bpy.context.scene.objects
    for obj in objects:
        if obj.type == 'EMPTY':
            children = [c for c in obj.children if c.type == 'MESH']
            if children:
                yield obj, children

def perform_export(filepath: str, export_format: str, apply_transforms: bool,
                   axis_forward: str, axis_up: str, debug: bool) -> bool:
    """Dispatch export based on chosen format."""
    kwargs_common = {}
    if export_format == 'FBX':
        try:
            if debug:
                print(f"[Export] FBX -> {filepath}")
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=True,
                apply_unit_scale=True,
                bake_space_transform=False,
                axis_forward=axis_forward,
                axis_up=axis_up,
                add_leaf_bones=False,
            )
            return True
        except Exception as e:
            print(f"[Export][FBX] ERROR: {e}")
            return False

    elif export_format == 'GLTF':
        try:
            if debug:
                print(f"[Export] glTF -> {filepath}")
            bpy.ops.export_scene.gltf(
                filepath=filepath,
                export_format='GLB' if filepath.lower().endswith('.glb') else 'GLTF_SEPARATE',
                use_selection=True,
            )
            return True
        except Exception as e:
            print(f"[Export][GLTF] ERROR: {e}")
            return False

    elif export_format == 'OBJ':
        try:
            if debug:
                print(f"[Export] OBJ -> {filepath}")
            bpy.ops.wm.obj_export(
                filepath=filepath,
                export_selected_objects=True,
                forward_axis=axis_forward,
                up_axis=axis_up,
            )
            return True
        except Exception as e:
            print(f"[Export][OBJ] ERROR: {e}")
            return False

    elif export_format == 'DAE':
        try:
            if debug:
                print(f"[Export] DAE -> {filepath}")
            bpy.ops.wm.collada_export(
                filepath=filepath,
                selected=True,
                apply_modifiers=True,
                triangulate=True,
            )
            return True
        except Exception as e:
            print(f"[Export][DAE] ERROR: {e}")
            return False

    return False

def select_only(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        if o and o.name in bpy.data.objects:
            o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]

# ---------------------------
# Properties
# ---------------------------

class MEProps(PropertyGroup):
    export_path: StringProperty(
        name="Export Path",
        subtype='DIR_PATH',
        default=""
    )
    export_format: EnumProperty(
        name="Format",
        items=[
            ('FBX', 'FBX', ''),
            ('GLTF', 'glTF', ''),
            ('OBJ', 'OBJ', ''),
            ('DAE', 'Collada (DAE)', ''),
        ],
        default='FBX'
    )
    axis_forward: EnumProperty(
        name="Forward",
        items=[('X','X',''),('Y','Y',''),('Z','Z',''),('-X','-X',''),('-Y','-Y',''),('-Z','-Z','')],
        default='Y'
    )
    axis_up: EnumProperty(
        name="Up",
        items=[('X','X',''),('Y','Y',''),('Z','Z',''),('-X','-X',''),('-Y','-Y',''),('-Z','-Z','')],
        default='Z'
    )
    center_parent_empties: BoolProperty(
        name="Center Parent Empties",
        description="Temporarily place the parent EMPTY at world (0,0,0) for export, then restore EXACT transform",
        default=True
    )
    combine_children: BoolProperty(
        name="Combine Children",
        description="Join all mesh children under each parent EMPTY into a single mesh before export",
        default=False
    )
    apply_transforms: BoolProperty(
        name="Apply Transforms",
        description="Apply loc/rot/scale to selected meshes just before export",
        default=False
    )
    debug: BoolProperty(
        name="Debug",
        default=False
    )

# ---------------------------
# Operator
# ---------------------------

class ME_OT_export(Operator):
    """Export all groups parented to empties, with world-space centering fix"""
    bl_idname = "me.export_groups"
    bl_label = "Export Empty Groups"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        ensure_object_mode()
        props: MEProps = context.scene.me_props

        if not props.export_path:
            self.report({'ERROR'}, "Please choose an Export Path")
            return {'CANCELLED'}

        exported = 0

        # Iterate empties that have mesh children
        for empty, children in iter_parent_empties_with_mesh_children():
            if props.debug:
                print(f"\n[Group] EMPTY: {empty.name}  children: {[c.name for c in children]}")

            # Save world transform of the parent empty
            empty_world = empty.matrix_world.copy()

            # Optionally move parent empty to world origin (WORLD SPACE)
            if props.center_parent_empties:
                if props.debug:
                    print(f"[Group] Centering EMPTY '{empty.name}' to world origin (was {empty_world.translation})")
                mw = empty.matrix_world.copy()
                mw.translation = Vector((0.0, 0.0, 0.0))
                empty.matrix_world = mw
                bpy.context.view_layer.update()

            try:
                # Select children (optionally joined) and export
                if props.combine_children and len(children) > 1:
                    # Join flow
                    select_only(children)
                    bpy.ops.object.join()
                    joined = context.active_object
                    joined.name = f"{empty.name}_combined"
                    if props.apply_transforms:
                        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

                    # Export joined
                    filename = f"{joined.name}.{props.export_format.lower() if props.export_format != 'GLTF' else 'glb'}"
                    filepath = os.path.join(props.export_path, filename)
                    ok = perform_export(filepath, props.export_format, props.apply_transforms,
                                        props.axis_forward, props.axis_up, props.debug)
                    if ok:
                        exported += 1
                    # Undo the join to restore original objects
                    bpy.ops.ed.undo()
                else:
                    # Export each child individually
                    for child in children:
                        select_only([child])
                        if props.apply_transforms:
                            bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
                        filename = f"{child.name}.{props.export_format.lower() if props.export_format != 'GLTF' else 'glb'}"
                        filepath = os.path.join(props.export_path, filename)
                        ok = perform_export(filepath, props.export_format, props.apply_transforms,
                                            props.axis_forward, props.axis_up, props.debug)
                        if ok:
                            exported += 1

            finally:
                # Restore EXACT world transform of the empty (children follow automatically)
                empty.matrix_world = empty_world
                bpy.context.view_layer.update()

        self.report({'INFO'}, f"Exported {exported} file(s).")
        return {'FINISHED'}

# ---------------------------
# Panel
# ---------------------------

class ME_PT_panel(Panel):
    bl_label = "Mass Exporter"
    bl_idname = "ME_PT_panel"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Mass Exporter"

    def draw(self, context):
        layout = self.layout
        props: MEProps = context.scene.me_props

        col = layout.column(align=True)
        col.prop(props, "export_path")
        col.prop(props, "export_format")
        row = col.row(align=True)
        row.prop(props, "axis_forward")
        row.prop(props, "axis_up")
        layout.separator()
        col = layout.column(align=True)
        col.prop(props, "center_parent_empties")
        col.prop(props, "combine_children")
        col.prop(props, "apply_transforms")
        layout.separator()
        layout.prop(props, "debug")
        layout.operator(ME_OT_export.bl_idname, icon='EXPORT')

# ---------------------------
# Registration
# ---------------------------

classes = (
    MEProps,
    ME_OT_export,
    ME_PT_panel,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.me_props = PointerProperty(type=MEProps)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
    if hasattr(bpy.types.Scene, "me_props"):
        del bpy.types.Scene.me_props

if __name__ == "__main__":
    register()
