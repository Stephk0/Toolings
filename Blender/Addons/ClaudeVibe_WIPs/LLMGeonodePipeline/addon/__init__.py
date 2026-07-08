"""Geometry-Nodes Layout MCP -- Blender side.

Starts a small TCP socket server inside Blender that speaks JSON
``{"type": ..., "params": {...}}`` and answers
``{"status": "ok"|"error", "result"|"message": ...}``.

THREADING CONTRACT (read before touching this file)
---------------------------------------------------
``bpy`` is NOT thread-safe.  The socket runs on its own thread and must never
call ``bpy`` directly.  Instead every handler is pushed onto ``_TASK_QUEUE`` and
executed on Blender's main thread by ``_drain_queue`` (a ``bpy.app.timers``
callback).  The socket thread blocks on a ``threading.Event`` and reads the
result out of a shared slot.  See ``run_on_main``.

The three handlers (``capture_graph``, ``apply_layout``, ``autolayout_pass``)
all run on the main thread, so they may touch ``bpy`` freely.
"""

bl_info = {
    "name": "GeoNode Layout MCP Bridge",
    "author": "Stephan Viranyi (Stephko)",
    "version": (1, 1, 0),
    "blender": (4, 2, 0),
    "location": "View3D / Node Editor > Sidebar > GN Layout MCP",
    "description": "Socket bridge for AI-driven Geometry Nodes layout (capture / apply / autolayout).",
    "category": "Node",
}

import bpy
import gpu
import blf
import json
import queue
import socket
import base64
import tempfile
import threading
import traceback
import os

from gpu_extras.batch import batch_for_shader

from . import compat
from . import layout as layout_mod

# --------------------------------------------------------------------------- #
#  Main-thread execution queue
# --------------------------------------------------------------------------- #

_TASK_QUEUE = queue.Queue()


def _drain_queue():
    """Timer callback: run every queued callable on the main thread."""
    while True:
        try:
            fn = _TASK_QUEUE.get_nowait()
        except queue.Empty:
            break
        try:
            fn()
        except Exception:
            traceback.print_exc()
    return 0.05  # reschedule (seconds)


def run_on_main(fn, timeout=30.0):
    """Run ``fn`` on the main thread, blocking the caller until it finishes.

    Returns ``fn``'s value or re-raises its exception on the calling thread.
    """
    done = threading.Event()
    slot = {}

    def wrapper():
        try:
            slot["result"] = fn()
        except Exception as exc:  # noqa: BLE001 - relayed to client
            slot["error"] = str(exc)
            slot["traceback"] = traceback.format_exc()
        finally:
            done.set()

    _TASK_QUEUE.put(wrapper)
    if not done.wait(timeout):
        raise TimeoutError("main-thread task timed out (is Blender's UI blocked?)")
    if "error" in slot:
        raise RuntimeError(slot["error"] + "\n" + slot.get("traceback", ""))
    return slot.get("result")


# --------------------------------------------------------------------------- #
#  bpy helpers (main thread only)
# --------------------------------------------------------------------------- #

def _resolve_tree(spec):
    """Resolve a node tree from the ``tree`` param.

    ``"active"`` / ``None`` -> node group of the active object's active GN
    modifier.  Otherwise looked up by name in ``bpy.data.node_groups``.
    """
    if spec in (None, "active", ""):
        obj = bpy.context.active_object
        if obj is None:
            raise ValueError("no active object; cannot resolve active GN tree")
        mod = None
        # Prefer the object's active modifier if it is a GN modifier.
        active = getattr(obj.modifiers, "active", None)
        if active is not None and active.type == "NODES" and active.node_group:
            mod = active
        if mod is None:
            for m in obj.modifiers:
                if m.type == "NODES" and m.node_group:
                    mod = m
                    break
        if mod is None:
            raise ValueError(f"object '{obj.name}' has no Geometry Nodes modifier")
        return mod.node_group

    tree = bpy.data.node_groups.get(spec)
    if tree is None:
        raise ValueError(f"node group '{spec}' not found")
    return tree


def _find_node_editor(tree):
    """Find an open NODE_EDITOR area whose displayed tree is ``tree``.

    Returns ``(window, area, region)`` or raises with a clear message.
    """
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type != "NODE_EDITOR":
                continue
            space = area.spaces.active
            shown = getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)
            if shown is tree:
                region = next((r for r in area.regions if r.type == "WINDOW"), None)
                if region is not None:
                    return window, area, region
    raise RuntimeError(
        "no NODE_EDITOR area open showing this tree -- open a Geometry Nodes "
        "editor on it before calling capture_graph"
    )


def _abs_location(node):
    """Absolute node-space top-left, walking the parent (frame) chain."""
    x, y = node.location.x, node.location.y
    p = node.parent
    while p is not None:
        x += p.location.x
        y += p.location.y
        p = p.parent
    return x, y


def _set_abs_location(node, ax, ay):
    """Set ``node.location`` so its absolute position is ``(ax, ay)``.

    Accounts for the *current* parent-frame offset.  Callers that also move
    frames must apply ancestors first (see ``_handle_apply_layout``).
    """
    px = py = 0.0
    p = node.parent
    while p is not None:
        px += p.location.x
        py += p.location.y
        p = p.parent
    node.location = (ax - px, ay - py)


def _parent_depth(node):
    d = 0
    p = node.parent
    while p is not None:
        d += 1
        p = p.parent
    return d


def _node_index_map(tree):
    """Stable index -> node and node -> index, in ``tree.nodes`` order.

    This ordering is the identity key shared across capture / apply / autolayout
    and is stable as long as no nodes are added/removed between calls.
    """
    nodes = list(tree.nodes)
    return nodes, {n: i for i, n in enumerate(nodes)}


# --------------------------------------------------------------------------- #
#  Annotation draw handler
# --------------------------------------------------------------------------- #

def _make_stamp_draw(tree, stamps):
    """Build a POST_PIXEL draw callback stamping integer indices on nodes.

    ``stamps`` is a list of ``(index, abs_x, abs_y)`` in node space; we map each
    through the *live* region's ``view2d.view_to_region`` at draw time so labels
    are pixel-exact regardless of pan/zoom.

    The handler is registered on ``SpaceNodeEditor`` globally, so it fires for
    every node-editor region draw.  We gate on the *persistent tree datablock*
    (compared with ``==``, never on transient region/area wrapper identity --
    those wrappers are recreated per draw and ``is`` checks fail) and read the
    region/space straight from ``bpy.context`` at draw time.
    """
    shader = compat.solid_shader()
    font_id = 0
    pad = 3
    font_size = 15

    def draw():
        space = bpy.context.space_data
        region = bpy.context.region
        if space is None or region is None:
            return
        shown = getattr(space, "edit_tree", None) or getattr(space, "node_tree", None)
        if shown != tree:
            return
        # blf size is global state; set it every draw (other handlers may change it).
        compat.blf_size(font_id, font_size)
        v2d = region.view2d
        gpu.state.blend_set('ALPHA')
        for index, ax, ay in stamps:
            rx, ry = v2d.view_to_region(ax, ay, clip=False)
            label = str(index)
            tw, th = blf.dimensions(font_id, label)
            w = tw + pad * 2
            h = th + pad * 2
            # Filled high-contrast box anchored at the node's top-left corner.
            x0, y0 = rx, ry - h
            verts = [(x0, y0), (x0 + w, y0), (x0 + w, y0 + h), (x0, y0 + h)]
            batch = batch_for_shader(shader, 'TRI_FAN', {"pos": verts})
            shader.bind()
            shader.uniform_float("color", (0.05, 0.05, 0.05, 0.85))
            batch.draw(shader)
            blf.position(font_id, x0 + pad, y0 + pad, 0)
            blf.color(font_id, 1.0, 0.95, 0.2, 1.0)
            blf.draw(font_id, label)
        gpu.state.blend_set('NONE')

    return draw


# --------------------------------------------------------------------------- #
#  Handlers (main thread)
# --------------------------------------------------------------------------- #

def _serialize(tree):
    """Serialize nodes + links. Dimensions must be read post-draw by the caller."""
    nodes, idx = _node_index_map(tree)
    scale = compat.ui_scale()

    nodes_out = []
    for i, n in enumerate(nodes):
        ax, ay = _abs_location(n)
        dim = n.dimensions
        nodes_out.append({
            "index": i,
            "name": n.name,
            "type": n.bl_idname,
            "label": n.label,
            "loc": [round(n.location.x, 2), round(n.location.y, 2)],
            "abs_loc": [round(ax, 2), round(ay, 2)],
            # node-space size: dimensions are px -> divide by ui_scale.
            "dim": [round(dim.x / scale, 2), round(dim.y / scale, 2)],
            "is_frame": n.bl_idname == "NodeFrame",
            "parent": idx[n.parent] if n.parent is not None else -1,
        })

    links_out = []
    for l in tree.links:
        if l.from_node not in idx or l.to_node not in idx:
            continue
        links_out.append({
            "from_node": idx[l.from_node],
            "from_socket": l.from_socket.identifier,
            "to_node": idx[l.to_node],
            "to_socket": l.to_socket.identifier,
        })

    return nodes_out, links_out


def _handle_capture_graph(params):
    tree = _resolve_tree(params.get("tree", "active"))
    annotate = bool(params.get("annotate", True))
    window, area, region = _find_node_editor(tree)

    handle = None
    if annotate:
        nodes, _ = _node_index_map(tree)
        stamps = [(i, *_abs_location(n)) for i, n in enumerate(nodes)]
        draw = _make_stamp_draw(tree, stamps)
        handle = bpy.types.SpaceNodeEditor.draw_handler_add(
            draw, (), 'WINDOW', 'POST_PIXEL'
        )

    filepath = os.path.join(tempfile.gettempdir(), f"gn_layout_capture_{os.getpid()}.png")
    try:
        area.tag_redraw()
        # screenshot_area forces an area redraw -> draw handler runs ->
        # node.dimensions become valid.  Capture includes the overlay.
        compat.screenshot_area(window, area, region, filepath)
        nodes_out, links_out = _serialize(tree)
    finally:
        if handle is not None:
            bpy.types.SpaceNodeEditor.draw_handler_remove(handle, 'WINDOW')
            area.tag_redraw()

    with open(filepath, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("ascii")
    try:
        os.remove(filepath)
    except OSError:
        pass

    return {
        "tree": tree.name,
        "node_count": len(nodes_out),
        "nodes": nodes_out,
        "links": links_out,
        "image_png_base64": img_b64,
    }


def _handle_apply_layout(params):
    tree = _resolve_tree(params.get("tree", "active"))
    moves = params.get("moves") or []
    nodes, _ = _node_index_map(tree)
    n_total = len(nodes)

    # Apply ancestors (frames) before descendants so child abs-coords resolve
    # against already-updated parent offsets.
    ordered = sorted(moves, key=lambda m: _parent_depth(nodes[int(m["index"])])
                     if 0 <= int(m["index"]) < n_total else 0)

    applied = 0
    skipped = []
    for m in ordered:
        i = int(m["index"])
        if not (0 <= i < n_total):
            skipped.append(i)
            continue
        _set_abs_location(nodes[i], float(m["x"]), float(m["y"]))
        applied += 1

    # Nudge the depsgraph / redraw the editor.
    for window in bpy.context.window_manager.windows:
        for area in window.screen.areas:
            if area.type == "NODE_EDITOR":
                area.tag_redraw()

    return {"tree": tree.name, "applied": applied, "skipped": skipped}


def _handle_autolayout_pass(params):
    tree = _resolve_tree(params.get("tree", "active"))
    x_gap = float(params.get("x_gap", 80.0))
    y_gap = float(params.get("y_gap", 40.0))

    # Dimensions need a fresh draw to be valid; tag the editor and read them.
    try:
        _window, area, _region = _find_node_editor(tree)
        area.tag_redraw()
    except RuntimeError:
        area = None  # no editor open: fall back to node.width + estimate

    nodes, idx = _node_index_map(tree)
    scale = compat.ui_scale()

    layout_nodes = {}
    for i, n in enumerate(nodes):
        if n.bl_idname == "NodeFrame":
            continue  # frames shrink-wrap their children; never positioned
        w = n.dimensions.x / scale
        h = n.dimensions.y / scale
        if w <= 1.0:
            w = float(n.width)  # node.width is always valid (node-space units)
        if h <= 1.0:
            # Rough estimate when no draw has happened: header + sockets.
            n_sock = len(n.inputs) + len(n.outputs)
            h = 30.0 + 22.0 * max(1, n_sock)
        layout_nodes[i] = {"w": w, "h": h}

    links = []
    for l in tree.links:
        if l.from_node in idx and l.to_node in idx:
            links.append((idx[l.from_node], idx[l.to_node]))

    placement = layout_mod.compute_layout(layout_nodes, links, x_gap=x_gap, y_gap=y_gap)

    moves = [{"index": i, "x": round(x, 2), "y": round(y, 2)}
             for i, (x, y) in sorted(placement.items())]

    return {
        "tree": tree.name,
        "moves": moves,
        "note": "moves are in absolute node space; pass to apply_layout (not auto-applied)",
    }


HANDLERS = {
    "capture_graph": _handle_capture_graph,
    "apply_layout": _handle_apply_layout,
    "autolayout_pass": _handle_autolayout_pass,
    "ping": lambda params: {"pong": True},
}


# --------------------------------------------------------------------------- #
#  Socket server (background thread -- NEVER touches bpy directly)
# --------------------------------------------------------------------------- #

class LayoutSocketServer:
    def __init__(self, host="localhost", port=9877):
        self.host = host
        self.port = port
        self.running = False
        self._sock = None
        self._thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(5)
        self._sock.settimeout(1.0)
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()
        print(f"[GN Layout MCP] listening on {self.host}:{self.port}")

    def stop(self):
        self.running = False
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
            self._sock = None
        print("[GN Layout MCP] stopped")

    def _serve(self):
        while self.running:
            try:
                conn, _addr = self._sock.accept()
            except socket.timeout:
                continue
            except OSError:
                break
            try:
                self._handle_client(conn)
            except Exception:
                traceback.print_exc()
            finally:
                try:
                    conn.close()
                except OSError:
                    pass

    def _handle_client(self, conn):
        # The MCP client half-closes its write end after sending, so we can read
        # to EOF and parse the whole command in one shot.
        conn.settimeout(30.0)
        chunks = []
        while True:
            try:
                data = conn.recv(65536)
            except socket.timeout:
                break
            if not data:
                break
            chunks.append(data)
        raw = b"".join(chunks)
        if not raw:
            return

        try:
            command = json.loads(raw.decode("utf-8"))
            ctype = command.get("type")
            params = command.get("params", {}) or {}
            handler = HANDLERS.get(ctype)
            if handler is None:
                response = {"status": "error", "message": f"unknown command type: {ctype}"}
            else:
                result = run_on_main(lambda: handler(params))
                response = {"status": "ok", "result": result}
        except Exception as exc:  # noqa: BLE001 - relayed to client
            response = {"status": "error", "message": f"{exc}"}

        payload = json.dumps(response).encode("utf-8")
        try:
            conn.sendall(payload)
        except OSError:
            traceback.print_exc()


_SERVER = None


def _ensure_timer():
    if not bpy.app.timers.is_registered(_drain_queue):
        bpy.app.timers.register(_drain_queue, persistent=True)


# --------------------------------------------------------------------------- #
#  Operators / UI
# --------------------------------------------------------------------------- #

class GNLAYOUT_OT_start_server(bpy.types.Operator):
    bl_idname = "gnlayout.start_server"
    bl_label = "Start GN Layout MCP Server"
    bl_description = "Start the socket bridge for AI-driven node layout"

    def execute(self, context):
        global _SERVER
        if _SERVER is not None and _SERVER.running:
            self.report({'WARNING'}, "Server already running")
            return {'CANCELLED'}
        prefs = context.scene
        _ensure_timer()
        _SERVER = LayoutSocketServer(
            host=getattr(prefs, "gnlayout_host", "localhost"),
            port=getattr(prefs, "gnlayout_port", 9877),
        )
        try:
            _SERVER.start()
        except OSError as exc:
            self.report({'ERROR'}, f"Could not start server: {exc}")
            _SERVER = None
            return {'CANCELLED'}
        self.report({'INFO'}, f"GN Layout MCP listening on port {_SERVER.port}")
        return {'FINISHED'}


class GNLAYOUT_OT_stop_server(bpy.types.Operator):
    bl_idname = "gnlayout.stop_server"
    bl_label = "Stop GN Layout MCP Server"
    bl_description = "Stop the socket bridge"

    def execute(self, context):
        global _SERVER
        if _SERVER is not None:
            _SERVER.stop()
            _SERVER = None
            self.report({'INFO'}, "GN Layout MCP stopped")
        return {'FINISHED'}


class GNLAYOUT_PT_panel(bpy.types.Panel):
    bl_label = "GN Layout MCP"
    bl_idname = "GNLAYOUT_PT_panel"
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = "GN Layout MCP"

    def draw(self, context):
        layout = self.layout
        running = _SERVER is not None and _SERVER.running
        row = layout.row()
        row.label(text="Server: " + ("Running" if running else "Stopped"),
                  icon='RADIOBUT_ON' if running else 'RADIOBUT_OFF')
        layout.prop(context.scene, "gnlayout_port")
        if running:
            layout.operator("gnlayout.stop_server", icon='PAUSE')
        else:
            layout.operator("gnlayout.start_server", icon='PLAY')


_CLASSES = (
    GNLAYOUT_OT_start_server,
    GNLAYOUT_OT_stop_server,
    GNLAYOUT_PT_panel,
)


def register():
    bpy.types.Scene.gnlayout_port = bpy.props.IntProperty(
        name="Port", default=9877, min=1024, max=65535,
    )
    bpy.types.Scene.gnlayout_host = bpy.props.StringProperty(
        name="Host", default="localhost",
    )
    for cls in _CLASSES:
        bpy.utils.register_class(cls)
    _ensure_timer()


def unregister():
    global _SERVER
    if _SERVER is not None:
        _SERVER.stop()
        _SERVER = None
    if bpy.app.timers.is_registered(_drain_queue):
        bpy.app.timers.unregister(_drain_queue)
    for cls in reversed(_CLASSES):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.gnlayout_port
    del bpy.types.Scene.gnlayout_host


if __name__ == "__main__":
    register()
