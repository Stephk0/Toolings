import bpy

from . import operators, preferences


def draw_header(self, context):
    space = context.space_data
    if space.local_view is None or not preferences.get(context).show_header:
        return
    n = operators.depth(space)
    self.layout.operator(
        "view3d.smart_isolate_exit",
        text=f"Isolated {n}" if n > 1 else "Isolated",
        icon="HIDE_ON",
        depress=True,
    )


def register():
    bpy.types.VIEW3D_HT_header.append(draw_header)


def unregister():
    bpy.types.VIEW3D_HT_header.remove(draw_header)
