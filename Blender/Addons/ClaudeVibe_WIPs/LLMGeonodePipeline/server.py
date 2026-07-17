"""Geometry-Nodes Layout MCP server.

A thin FastMCP process that forwards JSON commands over a TCP socket to the
Blender addon (``geonode_layout_addon``) and relays the responses.  The only
real work it does is downscaling the capture image with Pillow so the returned
payload stays cheap.

Tools
-----
* ``capture_graph``           -- annotated screenshot + node/link table (one response)
* ``apply_layout``            -- one batched write of node positions
* ``autolayout_pass``         -- deterministic layout, returns moves (does NOT apply)
* ``execute_blender_code``    -- run Python in the live Blender (stdout relayed)
* ``get_scene_info``          -- scene/object summary + geometry node groups
* ``get_object_info``         -- one object in depth (incl. evaluated mesh counts)
* ``get_viewport_screenshot`` -- capture the 3D viewport as an image

The last four are ports of the blender-mcp tools the geonode pipeline used to
depend on -- with them the pipeline runs autonomously against this one bridge.

Run:  ``python server.py``  (or via your MCP client config -- see README).
"""

import io
import os
import json
import socket
import base64

from mcp.server.fastmcp import FastMCP, Image

try:
    from PIL import Image as PILImage
except ImportError:  # Pillow only used for downscaling; degrade gracefully.
    PILImage = None

BLENDER_HOST = os.environ.get("GNLAYOUT_HOST", "localhost")
BLENDER_PORT = int(os.environ.get("GNLAYOUT_PORT", "9877"))
SOCKET_TIMEOUT = float(os.environ.get("GNLAYOUT_TIMEOUT", "60"))

mcp = FastMCP("blender-geonode-layout")


def _send_command(ctype: str, params: dict, timeout: float | None = None) -> dict:
    """Send one command to the Blender addon and return its ``result`` dict.

    Protocol: connect, send the JSON command, half-close the write end so the
    addon can read to EOF, then read the full response to EOF and parse it.
    ``timeout`` overrides the default socket timeout for long-running commands
    (keep it above the addon-side handler budget so slow work isn't cut off).
    """
    payload = json.dumps({"type": ctype, "params": params}).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout if timeout is not None else SOCKET_TIMEOUT)
    try:
        sock.connect((BLENDER_HOST, BLENDER_PORT))
        sock.sendall(payload)
        sock.shutdown(socket.SHUT_WR)  # signal end-of-request
        chunks = []
        while True:
            try:
                data = sock.recv(65536)
            except socket.timeout:
                break
            if not data:
                break
            chunks.append(data)
    finally:
        sock.close()

    raw = b"".join(chunks)
    if not raw:
        raise RuntimeError(
            "no response from Blender -- is the addon's server started "
            f"(port {BLENDER_PORT})?"
        )
    response = json.loads(raw.decode("utf-8"))
    if response.get("status") == "error":
        raise RuntimeError(f"Blender error: {response.get('message')}")
    return response["result"]


def _downscale_png(raw: bytes, max_px: int) -> bytes:
    """Cap the longest edge of a PNG at ``max_px`` (Pillow). No-op without PIL."""
    if PILImage is None or max_px <= 0:
        return raw
    img = PILImage.open(io.BytesIO(raw))
    w, h = img.size
    longest = max(w, h)
    if longest > max_px:
        ratio = max_px / float(longest)
        img = img.resize((max(1, int(w * ratio)), max(1, int(h * ratio))),
                         PILImage.LANCZOS)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


@mcp.tool()
def capture_graph(tree: str = "active", annotate: bool = True,
                  scale: float = 1.0, max_px: int = 1600):
    """Capture a Geometry Nodes graph as an annotated image PLUS structured data.

    Returns, in ONE response, both:
      * an image where each node is stamped with its integer index, and
      * a JSON table of ``nodes`` (index/name/type/loc/abs_loc/dim/parent) and
        ``links`` (from_node/from_socket/to_node/to_socket, by index).

    The stamped index is the identity key: use it to refer to a specific node in
    ``apply_layout``.  Reason over the whole image, then emit the entire new
    layout at once -- do not re-capture between writes.

    Args:
        tree:     "active" (active object's active GN modifier) or a node-group name.
        annotate: stamp integer indices on the nodes (default True).
        scale:    reserved render-scale hint (passed through).
        max_px:   longest-edge cap for the returned image (default 1600).
    """
    result = _send_command("capture_graph", {
        "tree": tree, "annotate": annotate, "scale": scale,
    })
    img_b64 = result.pop("image_png_base64", None)

    table = json.dumps(result, indent=2)
    if img_b64 is None:
        return table

    raw = base64.b64decode(img_b64)
    raw = _downscale_png(raw, max_px)
    return [Image(data=raw, format="png"), table]


@mcp.tool()
def apply_layout(moves: list, tree: str = "active"):
    """Write node positions in ONE batched pass.

    Args:
        moves: list of ``{"index": int, "x": float, "y": float}`` -- absolute
               node-space top-left coordinates (same space as ``abs_loc`` from
               capture_graph). Indices are the stamped capture indices.
        tree:  "active" or a node-group name (must match the captured tree).

    Returns how many nodes were moved and which indices were skipped.
    """
    result = _send_command("apply_layout", {"tree": tree, "moves": moves})
    return json.dumps(result, indent=2)


@mcp.tool()
def autolayout_pass(tree: str = "active", x_gap: float = 80.0, y_gap: float = 40.0):
    """Compute a deterministic left-to-right layered layout.

    Returns ``moves`` (absolute node-space coords) WITHOUT applying them, so you
    can review/adjust and then hand them to ``apply_layout``.  Frame nodes are
    omitted (they shrink-wrap their children automatically).

    Args:
        tree:  "active" or a node-group name.
        x_gap: horizontal spacing between columns (node-space units).
        y_gap: vertical spacing between stacked nodes (node-space units).
    """
    result = _send_command("autolayout_pass", {
        "tree": tree, "x_gap": x_gap, "y_gap": y_gap,
    })
    return json.dumps(result, indent=2)


@mcp.tool()
def execute_blender_code(code: str):
    """Run arbitrary Python inside the live Blender session (``bpy`` in scope).

    This is the pipeline's general-purpose escape hatch -- use it for everything
    the dedicated tools don't cover: bootstrapping an editor with
    ``prepare_capture.prepare(...)``, creating/parenting frames, rewiring links
    (always by socket IDENTIFIER, never display name), renaming interface
    sockets, saving the file, etc.

    ``print()`` output is captured and returned (truncated past ~60k chars),
    so print what you need to see. Runs on Blender's main thread with a 120 s
    budget. The code operates on the live .blend -- verify evaluated geometry
    before saving anything.

    Args:
        code: Python source to execute.
    """
    result = _send_command("execute_code", {"code": code}, timeout=130.0)
    return json.dumps(result, indent=2)


@mcp.tool()
def get_scene_info(max_objects: int = 50):
    """Summarize the current Blender scene.

    Returns the scene name, .blend filepath, object list (name/type/location,
    plus each object's Geometry Nodes groups), the active object, and the names
    of ALL GeometryNodeTree groups in the file -- the quickest way to find the
    tree you want to capture or tidy.

    Args:
        max_objects: cap on listed objects (``objects_truncated`` flags overflow).
    """
    result = _send_command("get_scene_info", {"max_objects": max_objects})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_object_info(name: str):
    """Inspect one object in depth.

    Returns transform, visibility, collections, modifier stack (with node-group
    names for GN modifiers), materials, world bounding box, and for meshes BOTH
    base and evaluated (post-modifier) vertex/edge/polygon counts -- the
    evaluated counts are the pipeline's geometry-unchanged gate: snapshot them
    before editing a graph and compare after, never save on a mismatch.

    Args:
        name: object name in ``bpy.data.objects``.
    """
    result = _send_command("get_object_info", {"name": name})
    return json.dumps(result, indent=2)


@mcp.tool()
def get_viewport_screenshot(max_px: int = 800):
    """Capture the 3D viewport as a PNG image.

    Grabs the first open VIEW_3D area (overlays included) -- use it to eyeball
    a modifier's visual result after graph edits. Fails if no 3D viewport is
    open.

    Args:
        max_px: longest-edge cap for the returned image (default 800).
    """
    result = _send_command("get_viewport_screenshot", {})
    raw = base64.b64decode(result.pop("image_png_base64"))
    raw = _downscale_png(raw, max_px)
    return Image(data=raw, format="png")


if __name__ == "__main__":
    mcp.run()
