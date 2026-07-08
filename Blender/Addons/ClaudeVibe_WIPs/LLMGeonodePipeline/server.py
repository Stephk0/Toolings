"""Geometry-Nodes Layout MCP server.

A thin FastMCP process that forwards JSON commands over a TCP socket to the
Blender addon (``geonode_layout_addon``) and relays the responses.  The only
real work it does is downscaling the capture image with Pillow so the returned
payload stays cheap.

Tools
-----
* ``capture_graph``    -- annotated screenshot + node/link table (one response)
* ``apply_layout``     -- one batched write of node positions
* ``autolayout_pass``  -- deterministic layout, returns moves (does NOT apply)

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


def _send_command(ctype: str, params: dict) -> dict:
    """Send one command to the Blender addon and return its ``result`` dict.

    Protocol: connect, send the JSON command, half-close the write end so the
    addon can read to EOF, then read the full response to EOF and parse it.
    """
    payload = json.dumps({"type": ctype, "params": params}).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(SOCKET_TIMEOUT)
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


if __name__ == "__main__":
    mcp.run()
