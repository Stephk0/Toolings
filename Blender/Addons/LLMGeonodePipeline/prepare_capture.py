"""prepare_capture.py -- get Blender ready for a GeoNode Layout MCP capture.

`capture_graph` fails loud unless a NODE_EDITOR area is open showing the target
tree. This helper does that setup in one shot: (optionally) open a .blend, make
the object holding the tree active, switch an area to a Geometry Nodes editor,
frame all nodes, and (re)start the layout socket server.

Run it in the LIVE Blender (paste via the geonode-layout `execute_blender_code`
tool -- the bridge's own, no blender-mcp needed -- or from the Text editor).
Not a headless script: the MCP needs a live UI.

    prepare(tree="GN_NormalTransfer", filepath="D:/.../GN_NormalTransfer.blend")
    prepare()  # active object's active GN tree, current file

After it prints "ready", call the MCP `capture_graph` tool.
"""

import bpy


def _find_object_for_tree(ng):
    for obj in bpy.data.objects:
        for m in obj.modifiers:
            if m.type == 'NODES' and m.node_group == ng:
                return obj
    return None


def prepare(tree=None, filepath=None, start_server=True):
    if filepath:
        bpy.ops.wm.open_mainfile(filepath=filepath)

    # resolve the tree
    if tree:
        ng = bpy.data.node_groups.get(tree)
        if ng is None:
            raise ValueError(f"node group '{tree}' not found")
    else:
        obj = bpy.context.active_object
        ng = next((m.node_group for m in obj.modifiers
                   if m.type == 'NODES' and m.node_group), None)
        if ng is None:
            raise ValueError("no active Geometry Nodes tree")

    # make an object holding the tree active (so the editor resolves it)
    obj = _find_object_for_tree(ng)
    if obj:
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)

    # switch an area to a GN node editor and frame it
    area = win = None
    for w in bpy.context.window_manager.windows:
        for a in w.screen.areas:
            if a.type in ('VIEW_3D', 'NODE_EDITOR'):
                area, win = a, w
                if a.type == 'NODE_EDITOR':
                    break
        if area and area.type == 'NODE_EDITOR':
            break
    if area is None:
        raise RuntimeError("no VIEW_3D or NODE_EDITOR area to repurpose")

    area.type = 'NODE_EDITOR'
    sp = area.spaces.active
    sp.tree_type = 'GeometryNodeTree'
    if hasattr(sp, "node_tree"):
        sp.node_tree = ng
    region = next(r for r in area.regions if r.type == 'WINDOW')
    with bpy.context.temp_override(window=win, area=area, region=region):
        bpy.ops.node.view_all()
    area.tag_redraw()

    if start_server:
        try:
            bpy.ops.gnlayout.start_server()
        except Exception as exc:  # already running / addon absent
            print("[prepare] server note:", exc)

    shown = getattr(sp, "edit_tree", None) or getattr(sp, "node_tree", None)
    print(f"[prepare] ready -- editor showing '{shown.name if shown else None}' "
          f"({len(ng.nodes)} nodes). Now call the MCP capture_graph tool.")
    return ng


if __name__ == "__main__":
    prepare()
