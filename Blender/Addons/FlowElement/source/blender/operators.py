"""Flow Element operator: BMesh in, core solve, BMesh out."""

import time

import bmesh
import bpy
from bpy.props import BoolProperty, EnumProperty, FloatProperty, IntProperty

from ..core import flow
from ..core.topology import Topology


class _BMeshPositions:
    """Read-only ``index -> (x, y, z)`` view of a BMesh (lookup table ensured)."""

    def __init__(self, bm):
        self.verts = bm.verts

    def __getitem__(self, i):
        return self.verts[i].co.to_tuple()

    def __contains__(self, i):
        return 0 <= i < len(self.verts)


def _bmesh_topology(bm):
    verts = bm.verts

    def corner_links(i):
        return [(l.link_loop_prev.vert.index, l.link_loop_next.vert.index)
                for l in verts[i].link_loops]

    def neighbors(i):
        v = verts[i]
        return [e.other_vert(v).index for e in v.link_edges]

    return Topology(corner_links, neighbors)


def resolve_mode(mode, select_mode, bm):
    if mode != 'AUTO':
        return mode
    if select_mode[2] and any(f.select for f in bm.faces):
        return flow.MODE_FACE
    if select_mode[1]:
        return flow.MODE_EDGE
    return flow.MODE_VERTEX


class MESH_OT_st3e_flow_element(bpy.types.Operator):
    """Rebuild lost curvature of the selection from the surrounding geometry
(3ds Max Edge / Vertex Flow). Edges flow across their loop, vertices and faces along
every edge line through them"""

    bl_idname = "mesh.st3e_flow_element"
    bl_label = "Flow Element"
    bl_options = {'REGISTER', 'UNDO'}

    mode: EnumProperty(
        name="Mode",
        items=(
            ('AUTO', "Auto", "Follow the mesh select mode (face > edge > vertex)"),
            ('VERTEX', "Vertex", "Flow selected vertices along every edge line through them"),
            ('EDGE', "Edge", "Flow selected edge loops across their crossing edges"),
            ('FACE', "Face", "Flow every vertex of the selected faces from the geometry "
                             "around the selection"),
        ),
        default='AUTO',
    )
    tension: FloatProperty(
        name="Tension", default=1.0, soft_min=0.0, soft_max=2.0, min=-1.0, max=3.0,
        description="Curvature strength. 1 matches the surrounding curvature, 0 is "
                    "straight (linear), above 1 overshoots",
    )
    mix: FloatProperty(
        name="Mix", default=1.0, min=0.0, max=1.0, subtype='FACTOR',
        description="Blend between the original and the flowed position",
    )
    passes: IntProperty(
        name="Refine Passes", default=4, min=1, soft_max=10, max=50,
        description="Re-evaluate the curves at the corrected positions. More passes help "
                    "heavily distorted or large selections",
    )
    debug: BoolProperty(name="Debug Log", default=False,
                        description="Print timing and counts to the system console")

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH' and context.mode == 'EDIT_MESH'

    def draw(self, context):
        layout = self.layout
        layout.use_property_split = True
        col = layout.column()
        col.prop(self, "mode")
        col.prop(self, "tension")
        col.prop(self, "mix")
        col.prop(self, "passes")
        col.prop(self, "debug")

    def execute(self, context):
        select_mode = context.tool_settings.mesh_select_mode
        moved = skipped = 0
        start = time.perf_counter()

        for obj in context.objects_in_mode_unique_data:
            if obj.type != 'MESH':
                continue
            me = obj.data
            bm = bmesh.from_edit_mesh(me)
            bm.verts.ensure_lookup_table()

            mode = resolve_mode(self.mode, select_mode, bm)
            excluded = []
            if mode == flow.MODE_FACE:
                faces = [[v.index for v in f.verts] for f in bm.faces if f.select]
                moving = flow.moving_vertices(mode, selected_faces=faces)
            elif mode == flow.MODE_EDGE:
                excluded = [(e.verts[0].index, e.verts[1].index) for e in bm.edges if e.select]
                moving = flow.moving_vertices(mode, selected_edges=excluded)
            else:
                moving = flow.moving_vertices(
                    mode, selected_verts=[v.index for v in bm.verts if v.select])
            moving = {i for i in moving if not bm.verts[i].hide}
            if not moving:
                continue

            result = flow.solve(_BMeshPositions(bm), _bmesh_topology(bm), moving,
                                excluded_edges=excluded, tension=self.tension,
                                passes=self.passes)
            for i, p in result.items():
                v = bm.verts[i]
                v.co = v.co.lerp(p, self.mix)
            moved += len(result)
            skipped += len(moving) - len(result)

            bm.normal_update()
            bmesh.update_edit_mesh(me)

        if self.debug:
            print(f"[FlowElement] moved {moved}, skipped {skipped} "
                  f"in {(time.perf_counter() - start) * 1000:.1f} ms")

        if moved == 0:
            self.report({'WARNING'}, "Nothing to flow: select vertices, edge loops or faces "
                                     "with surrounding geometry on both sides")
            return {'CANCELLED'}
        if skipped:
            self.report({'INFO'}, f"Flowed {moved} vertices; {skipped} had no surrounding "
                                  "geometry to flow from (mesh border or closed selection)")
        return {'FINISHED'}


classes = (MESH_OT_st3e_flow_element,)


def register():
    for c in classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)
