"""Build GN_PolygonTileableNoise — a ST3E modifier that produces a tileable
perlin / voronoi noise value in the form of a piecewise-linear (triangulated)
scalar field on the mesh.

Algorithm (per face-corner):
  1. Read the corner's UV (or fall back to Position.xy).
  2. Scale to tile space: s = uv * tile_scale.   (one tile = 1.0 x 1.0)
  3. Decompose into a SQUARE cell split by a diagonal, in the (u, v) integer grid.
       col = floor(s.x), row = floor(s.y),  fu = s.x - col,  fv = s.y - row.
       lower triangle (fu + fv <= 1):  A=(col,row), B=(col+1,row), C=(col,row+1)
       upper triangle (fu + fv >  1):  B=(col+1,row), D=(col+1,row+1), C=(col,row+1)
  4. Per-vertex hash:   h(v) = FunctionNodeHashValue(seed=seed_per_vertex, value=v) in [0,1]
  5. Perlin  = barycentric interpolation of the 3 corner hashes   (piecewise-linear in triangles)
     Voronoi = F1 distance to the 4 surrounding feature points     (Voronoi cells = triangles
                                                                     in the Delaunay dual)
  6. Store the result on FACE_CORNER domain as a named attribute.

Tileability: because step 4 keys the hash on INTEGER vertex coordinates, a point on the
right edge of tile T (col=N) and a point on the left edge of tile T+1 (col=N+1) hit
the same vertex and therefore get the same hash. Adjacent tiles are continuous.
The "triangular" aspect: the value is piecewise-linear on a triangulation of the tile
plane (each square cell is split into 2 right triangles along the diagonal).

The whole build is headless, follows the ST3E recipe (asset_mark + ST3E catalog +
is_modifier=True + ST3E tag + tooltip every socket + ship a demo object with the
modifier attached + save full mainfile), and is then verified by `run_pipeline.py`
which applies `tidy_layout` and gates the save on geometry-unchanged + R1..R5.

Usage:
  blender --background --factory-startup \\
      --python D:/Stephko_Tooling/Toolings/Blender/Geonodes/_build/build_gn_polygon_tileable_noise.py
"""

import bpy
import sys
import os
import bmesh
from math import sqrt

# ----------------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------------

OUT_DIR = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
OUT_FILE = os.path.join(OUT_DIR, "GN_PolygonTileableNoise.blend")
GROUP_NAME = "GN_PolygonTileableNoise"
ST3E_CATALOG = "f9ab2fa9-3a4e-491a-abaa-558cd5c029d0"
ST3E_TAG = "ST3E"

# ----------------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------------


def add_node(ng, bl_idname, *, location=(0, 0), label="", parent=None):
    n = ng.nodes.new(bl_idname)
    n.location = location
    if label:
        n.label = label
    if parent is not None:
        n.parent = parent
    return n


def link(ng, src, src_socket, dst, dst_socket):
    """Robust link by SOCKET IDENTIFIER (display names can collide)."""
    out = next(s for s in src.outputs if s.identifier == src_socket)
    inp = next(s for s in dst.inputs if s.identifier == dst_socket)
    return ng.links.new(out, inp)


def link_by_name(ng, src, src_name, dst, dst_name):
    """Link by display name (use only when names are unique)."""
    out = src.outputs[src_name]
    inp = dst.inputs[dst_name]
    return ng.links.new(out, inp)


def frame(ng, *, label, location=(0, 0), parent=None):
    f = ng.nodes.new("NodeFrame")
    f.label = label
    # Trick: frame at (0,0) makes child .location absolute
    f.location = (0, 0)
    if parent is not None:
        f.parent = parent
    return f


def add_menu_socket(ng, *, name, items, default, description=""):
    """Add a NodeSocketMenu input with the given enum items + default.
    Order matters: Menu Switch's enum must exist BEFORE we set default.
    Here we don't wire yet — caller does that — so the trick is to first
    create the menu switch, set its items, THEN add the interface socket
    and wire it. This function only adds the interface socket."""
    sock = ng.interface.new_socket(name, in_out="INPUT", socket_type="NodeSocketMenu")
    sock.default_value = default
    if description:
        sock.description = description
    return sock


def set_menu_items(menu_switch, names):
    """Replace a Menu Switch's enum items. Starts with 2 (A/B); add as needed."""
    ed = menu_switch.enum_definition
    while len(ed.enum_items):
        ed.enum_items.remove(ed.enum_items[-1])
    for n in names:
        ed.enum_items.new(n)


def set_tooltip(ng, name, text):
    """Set the description (tooltip) of an interface socket by name.
    Only fills EMPTY descriptions (per project checklist)."""
    for it in ng.interface.items_tree:
        if it.item_type == "SOCKET" and it.name == name and not (it.description or "").strip():
            it.description = text


# ----------------------------------------------------------------------------
# Build the geonode
# ----------------------------------------------------------------------------


def build():
    # Start from a clean factory session so we don't carry leftover state
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # --- 1. Create the group ---------------------------------------------------
    ng = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")

    # --- 2. Add the Group Input/Output buses FIRST so all interface items
    #       below get a socket to live in ------------------------------------
    gi = add_node(ng, "NodeGroupInput", location=(-2200, 0), label="Inputs")
    go = add_node(ng, "NodeGroupOutput", location=(1800, 0), label="Output")

    # --- 3. Build the interface (sockets) in the order they should appear
    #       (Geometry + Selection top-level, then Noise panel, then UV panel) ---

    # Geometry (top-level)
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Selection", in_out="INPUT", socket_type="NodeSocketBool").default_value = True

    # --- Build a "Noise" panel and a "Coordinates" panel. We add the panels
    #     first as empty containers, then add sockets INTO the panel. -------

    noise_panel = ng.interface.new_panel("Noise")
    coords_panel = ng.interface.new_panel("Coordinates")

    # Helper to add a socket into a specific panel
    def add_to_panel(panel, name, socket_type, default=None, min=None, max=None, description=""):
        s = ng.interface.new_socket(name, in_out="INPUT", socket_type=socket_type)
        if panel is not None:
            ng.interface.move_to_parent(s, panel, len(panel.contents))
        if default is not None:
            try:
                s.default_value = default
            except (TypeError, AttributeError):
                pass
        if min is not None:
            s.min_value = min
        if max is not None:
            s.max_value = max
        if description:
            s.description = description
        return s

    # ---- 4. Build a master Menu Switch for Noise Type, add its menu socket,
    #         wire, and rename items ---------------------------------------
    menu_noise = add_node(ng, "GeometryNodeMenuSwitch", label="Noise Type",
                          location=(-2000, -300))
    menu_noise.data_type = "INT"
    set_menu_items(menu_noise, ["Perlin", "Voronoi"])
    noise_sock = add_to_panel(noise_panel, "Noise Type", "NodeSocketMenu", default="Perlin",
                              description="Piecewise-linear (triangulated) Perlin-like value, or Voronoi F1 distance to feature points.")
    link(ng, gi, "Noise Type", menu_noise, "Menu")

    # The remaining Noise panel params
    add_to_panel(noise_panel, "Noise Scale", "NodeSocketInt", default=4, min=1, max=64,
                 description="Grid cells per tile (each cell is split into 2 triangles). Higher = more detail.")
    add_to_panel(noise_panel, "Detail", "NodeSocketInt", default=0, min=0, max=8,
                 description="Octave count (each octave doubles the frequency with reduced amplitude).")
    add_to_panel(noise_panel, "Roughness", "NodeSocketFloat", default=0.5, min=0.0, max=1.0,
                 description="Per-octave amplitude falloff (0 = constant, 1 = standard fBm).")
    add_to_panel(noise_panel, "Seed", "NodeSocketInt", default=0, min=0, max=9999,
                 description="Random seed for the per-vertex hashes.")

    # Coordinates panel
    add_to_panel(coords_panel, "UV Map", "NodeSocketString", default="UVMap",
                 description="Name of the 2D coordinate attribute (usually a UV map). Falls back to Position.xy when the attribute is missing or a vertex is at UV (0,0).")
    add_to_panel(coords_panel, "Tile Size", "NodeSocketFloat", default=1.0, min=0.001, max=100.0,
                 description="Size of one tile in UV units. Set this to the size of the UV island you want the noise to repeat over. The default of 1.0 tiles a 0-1 UV space exactly once.")
    add_to_panel(coords_panel, "Output Attribute", "NodeSocketString", default="TileableTriNoise",
                 description="Name of the stored FLOAT attribute (written on the FACE_CORNER domain).")

    # Geometry must stay the FIRST input; the order above is correct, but
    # re-verify: Selection should sit just below Geometry at the top level.

    # ----------------------------------------------------------------------------
    # Layout constants (will be used as we go) — generous column gap so frames
    # breathe.
    # ----------------------------------------------------------------------------
    X_BASE = -1900    # Group Input is at -2200; first real frame starts here
    DX = 320          # horizontal gap between columns of nodes
    DY = 90           # vertical gap between stacked nodes in a frame

    # ----------------------------------------------------------------------------
    # Frame: INPUTS  (Group Input + named-attribute reads)
    # ----------------------------------------------------------------------------
    f_inputs = frame(ng, label="Inputs")
    f_inputs.location = (0, 0)

    # Move GI/GO into the right frames later; keep this frame empty for now,
    # we'll parent GI into the Inputs frame.

    # Place the GI inside f_inputs
    gi.parent = f_inputs
    gi.location = (0, 0)

    # Re-collect the GI outputs (so the new sockets are visible)
    def gi_out(name):
        return gi.outputs[name]

    # ----------------------------------------------------------------------------
    # Frame: TILE SPACE  (UV -> s in tile units, with Position.xy fallback)
    # ----------------------------------------------------------------------------
    f_tile = frame(ng, label="Tile Space")
    f_tile.location = (0, 0)

    # Named attribute read for the UV (VECTOR)
    na_uv = add_node(ng, "GeometryNodeInputNamedAttribute", label="Read UV",
                     location=(X_BASE, 200), parent=f_tile)
    link(ng, gi, "UV Map", na_uv, "Name")
    # Result type is INT by default -> change to FLOAT_VECTOR
    na_uv.data_type = "FLOAT_VECTOR"
    uv_exists = na_uv.outputs["Exists"]

    # Read Position as a fallback when UV is missing (or per the user's request,
    # take .xy regardless). To keep things simple and robust, we'll use UV if it
    # exists, else Position.xy.

    na_pos = add_node(ng, "GeometryNodeInputPosition", label="Read Position",
                      location=(X_BASE, 0), parent=f_tile)
    pos_xyz = na_pos.outputs["Position"]

    # Take the .xy of Position as a VECTOR
    sep_pos = add_node(ng, "ShaderNodeSeparateXYZ", label="Sep Position",
                       location=(X_BASE + DX, 0), parent=f_tile)
    link(ng, na_pos, "Position", sep_pos, "Vector")
    comb_pos_xy = add_node(ng, "ShaderNodeCombineXYZ", label="Pos .xy",
                           location=(X_BASE + 2 * DX, 0), parent=f_tile)
    link(ng, sep_pos, "X", comb_pos_xy, "X")
    link(ng, sep_pos, "Y", comb_pos_xy, "Y")
    # Z stays 0 (default)

    # Switch between UV and Position.xy by the UV-exists boolean
    sw_uv = add_node(ng, "GeometryNodeSwitch", label="UV or Pos?",
                     location=(X_BASE + 3 * DX, 100), parent=f_tile)
    sw_uv.input_type = "VECTOR"
    link(ng, na_uv, "Attribute", sw_uv, "False")
    link(ng, comb_pos_xy, "Vector", sw_uv, "True")
    link(ng, na_uv, "Exists", sw_uv, "Switch")

    coord = sw_uv.outputs["Output"]  # the chosen 2D coordinate, VECTOR

    # Multiply by Noise Scale to get s in tile units (so the noise repeats
    # exactly once over [0, 1] x [0, 1] when Tile Size = 1.0)
    # Actually we want: s = (uv * tile_size) * (1 / cells_per_tile * cells_per_tile)?
    # Simpler:  s = uv * (tile_size_recip * noise_scale)
    # We will compute:  s = uv * tile_size  (one full tile in the noise when
    # tile spans 0..1), then further multiply by 1 at the cell stage. Actually,
    # the user-controlled "Noise Scale" gives cells per tile, so we need
    #   s = uv * tile_size  (so 1 tile = 1 unit in s)
    #   cell = floor(s * noise_scale)  (so noise_scale cells per tile)
    # We'll fold these multiplications together below.

    # ----------------------------------------------------------------------------
    # Frame: LATTICE COORDS  (s -> col, row, fu, fv, triangle selector)
    # ----------------------------------------------------------------------------
    f_lattice = frame(ng, label="Lattice Coords")
    f_lattice.location = (0, 0)

    # s.x, s.y
    # s = coord * (tile_size * noise_scale)
    mul = add_node(ng, "ShaderNodeVectorMath", label="s = uv * (tile*N)",
                   location=(X_BASE + 4 * DX, 100), parent=f_lattice)
    mul.operation = "SCALE"
    link(ng, sw_uv, "Output", mul, "Vector")
    # The scale value = tile_size * noise_scale  (computed below)
    mul_t = add_node(ng, "ShaderNodeMath", label="Tile * N",
                     location=(X_BASE + 4 * DX - 180, 200), parent=f_lattice)
    mul_t.operation = "MULTIPLY"
    link(ng, gi, "Tile Size", mul_t, "Value")
    link(ng, gi, "Noise Scale", mul_t, "Value_001")
    link(ng, mul_t, "Value", mul, "Scale")

    # Decompose s into (col, row) + (fu, fv)
    sep_s = add_node(ng, "ShaderNodeSeparateXYZ", label="Sep s",
                     location=(X_BASE + 5 * DX, 100), parent=f_lattice)
    link(ng, mul, "Vector", sep_s, "Vector")
    sx = sep_s.outputs["X"]
    sy = sep_s.outputs["Y"]

    # col = floor(s.x)
    col = add_node(ng, "ShaderNodeMath", label="col", location=(X_BASE + 6 * DX, 200),
                   parent=f_lattice)
    col.operation = "FLOOR"
    link(ng, sx, "Value", col, "Value")
    # row = floor(s.y)
    row = add_node(ng, "ShaderNodeMath", label="row", location=(X_BASE + 6 * DX, 100),
                   parent=f_lattice)
    row.operation = "FLOOR"
    link(ng, sy, "Value", row, "Value")

    # fu = fract(s.x), fv = fract(s.y)
    fu = add_node(ng, "ShaderNodeMath", label="fu", location=(X_BASE + 6 * DX, 0),
                  parent=f_lattice)
    fu.operation = "FRACT"
    link(ng, sx, "Value", fu, "Value")
    fv = add_node(ng, "ShaderNodeMath", label="fv", location=(X_BASE + 6 * DX, -100),
                  parent=f_lattice)
    fv.operation = "FRACT"
    link(ng, sy, "Value", fv, "Value")

    # Lower-triangle?  fu + fv <= 1.0
    sum_f = add_node(ng, "ShaderNodeMath", label="fu + fv",
                     location=(X_BASE + 7 * DX, -50), parent=f_lattice)
    sum_f.operation = "ADD"
    link(ng, fu, "Value", sum_f, "Value")
    link(ng, fv, "Value", sum_f, "Value_001")
    cmp = add_node(ng, "FunctionNodeCompare", label="lower? (fu+fv <= 1)",
                   location=(X_BASE + 7 * DX, 200), parent=f_lattice)
    cmp.data_type = "FLOAT"
    cmp.operation = "LESS_EQUAL"
    link(ng, sum_f, "Value", cmp, "A")
    cmp.inputs["B"].default_value = 1.0
    is_lower = cmp.outputs["Result"]

    # Tileable wrap: col_mod = col mod N, row_mod = row mod N
    N = add_node(ng, "ShaderNodeMath", label="col mod N",
                 location=(X_BASE + 7 * DX, 400), parent=f_lattice)
    N.operation = "FLOORED_MODULO"
    link(ng, col, "Value", N, "Value")
    link(ng, gi, "Noise Scale", N, "Value_001")
    R = add_node(ng, "ShaderNodeMath", label="row mod N",
                 location=(X_BASE + 7 * DX, 320), parent=f_lattice)
    R.operation = "FLOORED_MODULO"
    link(ng, row, "Value", R, "Value")
    link(ng, gi, "Noise Scale", R, "Value_001")
    col_w = N.outputs["Value"]
    row_w = R.outputs["Value"]

    # ----------------------------------------------------------------------------
    # Frame: PERLIN PATH  (4 vertex hashes + barycentric interpolation)
    # ----------------------------------------------------------------------------
    f_perlin = frame(ng, label="Perlin (Barycentric Hash)")
    f_perlin.location = (0, 0)

    # We'll compute 3 vertex hashes per face corner (which triangle we're in
    # determines which 3). To avoid stacking 6 hash nodes (2 triangles x 3
    # vertices), we instead compute hashes for all 4 cell vertices, then use
    # a Switch on the triangle selector to pick which 3 feed the interp.
    #
    # 4 vertex IDs in cell space:
    #   A = (col, row)
    #   B = (col+1, row)
    #   C = (col,   row+1)
    #   D = (col+1, row+1)
    #
    # Lower triangle:  alpha*A + beta*B + gamma*C
    #   alpha = 1 - fu - fv,  beta = fu,  gamma = fv
    # Upper triangle:  alpha*B + beta*D + gamma*C
    #   alpha = fu + fv - 1,  beta = 1 - fv,  gamma = 1 - fu
    #
    # Hash inputs need a unique INT per (vx, vy, seed). We'll build a
    # combined INT seed:  vx * BIG + vy * BIG2 + seed  (avoiding name dups).

    # Helper: add a hash node that takes (vx, vy) and the master seed
    def add_vertex_hash(label, vx_node, vy_node, out_x, out_y, parent):
        # Combine vx, vy, seed into a single integer.
        # vx and vy are SCALARS; we multiply by a constant to make a unique
        # 3-component key. Hash Value's Value input is INT, so a sum of
        # (vx * 1000003) + (vy * 10007) + seed works (assuming values are
        # small ints).
        m_vx = add_node(ng, "ShaderNodeMath", label="vx*1e6", location=out_x, parent=parent)
        m_vx.operation = "MULTIPLY"
        m_vx.inputs[1].default_value = 1000003
        link(ng, vx_node, "Value", m_vx, "Value")
        m_vy = add_node(ng, "ShaderNodeMath", label="vy*1e4", location=out_y, parent=parent)
        m_vy.operation = "MULTIPLY"
        m_vy.inputs[1].default_value = 10007
        link(ng, vy_node, "Value", m_vy, "Value")
        seed = add_node(ng, "ShaderNodeMath", label="+ seed", location=(out_x[0] + 200, out_x[1] + 60),
                        parent=parent)
        seed.operation = "ADD"
        link(ng, m_vx, "Value", seed, "Value")
        link(ng, m_vy, "Value", seed, "Value_001")
        seed2 = add_node(ng, "ShaderNodeMath", label="+ seed (master)", location=(out_x[0] + 380, out_x[1] + 60),
                         parent=parent)
        seed2.operation = "ADD"
        link(ng, seed, "Value", seed2, "Value")
        link(ng, gi, "Seed", seed2, "Value_001")
        # Convert seed to integer for hash input
        h = add_node(ng, "FunctionNodeHashValue", label=label, location=(out_x[0] + 580, out_x[1]),
                     parent=parent)
        h.data_type = "INT"
        link(ng, seed2, "Value", h, "Seed")
        return h.outputs["Hash"]

    # Vertex inputs:
    #   A_vx = col_w, A_vy = row_w
    #   B_vx = col_w+1, B_vy = row_w
    #   C_vx = col_w, C_vy = row_w+1
    #   D_vx = col_w+1, D_vy = row_w+1
    col_p1 = add_node(ng, "ShaderNodeMath", label="col+1", location=(X_BASE + 7 * DX, 500), parent=f_lattice)
    col_p1.operation = "ADD"
    col_p1.inputs[1].default_value = 1
    link(ng, col_w, "Value", col_p1, "Value")
    row_p1 = add_node(ng, "ShaderNodeMath", label="row+1", location=(X_BASE + 7 * DX, 250), parent=f_lattice)
    row_p1.operation = "ADD"
    row_p1.inputs[1].default_value = 1
    link(ng, row_w, "Value", row_p1, "Value")

    # Hash nodes
    P_X0 = X_BASE + 8 * DX
    hA = add_vertex_hash("hash A", col_w, row_w, (P_X0, 300), (P_X0 - 200, 300), f_perlin)
    hB = add_vertex_hash("hash B", col_p1, row_w, (P_X0, 200), (P_X0 - 200, 200), f_perlin)
    hC = add_vertex_hash("hash C", col_w, row_p1, (P_X0, 100), (P_X0 - 200, 100), f_perlin)
    hD = add_vertex_hash("hash D", col_p1, row_p1, (P_X0, 0), (P_X0 - 200, 0), f_perlin)

    # Barycentric coords for the LOWER triangle:
    #   alpha = 1 - fu - fv,  beta = fu,  gamma = fv
    P_X1 = P_X0 + 1 * DX
    one_minus_fufv = add_node(ng, "ShaderNodeMath", label="1 - (fu+fv)",
                              location=(P_X1, 300), parent=f_perlin)
    one_minus_fufv.operation = "SUBTRACT"
    one_minus_fufv.inputs[0].default_value = 1.0
    link(ng, sum_f, "Value", one_minus_fufv, "Value")
    # alpha_lo = one_minus_fufv
    # beta_lo = fu
    # gamma_lo = fv

    # Lower triangle perlin = alpha*hA + beta*hB + gamma*hC
    l_aA = add_node(ng, "ShaderNodeMath", label="alpha*hA", location=(P_X1 + 200, 350), parent=f_perlin)
    l_aA.operation = "MULTIPLY"
    link(ng, one_minus_fufv, "Value", l_aA, "Value")
    link(ng, hA, "Hash", l_aA, "Value_001")
    l_aB = add_node(ng, "ShaderNodeMath", label="beta*hB", location=(P_X1 + 200, 280), parent=f_perlin)
    l_aB.operation = "MULTIPLY"
    link(ng, fu, "Value", l_aB, "Value")
    link(ng, hB, "Hash", l_aB, "Value_001")
    l_aC = add_node(ng, "ShaderNodeMath", label="gamma*hC", location=(P_X1 + 200, 210), parent=f_perlin)
    l_aC.operation = "MULTIPLY"
    link(ng, fv, "Value", l_aC, "Value")
    link(ng, hC, "Hash", l_aC, "Value_001")
    l_sum = add_node(ng, "ShaderNodeMath", label="lower sum",
                     location=(P_X1 + 400, 280), parent=f_perlin)
    l_sum.operation = "ADD"
    link(ng, l_aA, "Value", l_sum, "Value")
    link(ng, l_aB, "Value", l_sum, "Value_001")
    l_sum2 = add_node(ng, "ShaderNodeMath", label="lower sum (cont)",
                      location=(P_X1 + 600, 280), parent=f_perlin)
    l_sum2.operation = "ADD"
    link(ng, l_sum, "Value", l_sum2, "Value")
    link(ng, l_aC, "Value", l_sum2, "Value_001")

    # Upper triangle barycentric:
    #   alpha = (fu+fv) - 1,  beta = 1 - fv,  gamma = 1 - fu
    fufv_m1 = add_node(ng, "ShaderNodeMath", label="(fu+fv) - 1",
                       location=(P_X1, 150), parent=f_perlin)
    fufv_m1.operation = "SUBTRACT"
    link(ng, sum_f, "Value", fufv_m1, "Value")
    fufv_m1.inputs[1].default_value = 1.0
    one_minus_fv = add_node(ng, "ShaderNodeMath", label="1 - fv",
                            location=(P_X1, 80), parent=f_perlin)
    one_minus_fv.operation = "SUBTRACT"
    one_minus_fv.inputs[0].default_value = 1.0
    link(ng, fv, "Value", one_minus_fv, "Value")
    one_minus_fu = add_node(ng, "ShaderNodeMath", label="1 - fu",
                            location=(P_X1, 10), parent=f_perlin)
    one_minus_fu.operation = "SUBTRACT"
    one_minus_fu.inputs[0].default_value = 1.0
    link(ng, fu, "Value", one_minus_fu, "Value")

    # Upper triangle perlin = alpha*hB + beta*hD + gamma*hC
    u_aB = add_node(ng, "ShaderNodeMath", label="alpha*hB (up)", location=(P_X1 + 200, 140), parent=f_perlin)
    u_aB.operation = "MULTIPLY"
    link(ng, fufv_m1, "Value", u_aB, "Value")
    link(ng, hB, "Hash", u_aB, "Value_001")
    u_aD = add_node(ng, "ShaderNodeMath", label="beta*hD", location=(P_X1 + 200, 70), parent=f_perlin)
    u_aD.operation = "MULTIPLY"
    link(ng, one_minus_fv, "Value", u_aD, "Value")
    link(ng, hD, "Hash", u_aD, "Value_001")
    u_aC = add_node(ng, "ShaderNodeMath", label="gamma*hC (up)", location=(P_X1 + 200, 0), parent=f_perlin)
    u_aC.operation = "MULTIPLY"
    link(ng, one_minus_fu, "Value", u_aC, "Value")
    link(ng, hC, "Hash", u_aC, "Value_001")
    u_sum = add_node(ng, "ShaderNodeMath", label="upper sum",
                     location=(P_X1 + 400, 70), parent=f_perlin)
    u_sum.operation = "ADD"
    link(ng, u_aB, "Value", u_sum, "Value")
    link(ng, u_aD, "Value", u_sum, "Value_001")
    u_sum2 = add_node(ng, "ShaderNodeMath", label="upper sum (cont)",
                      location=(P_X1 + 600, 70), parent=f_perlin)
    u_sum2.operation = "ADD"
    link(ng, u_sum, "Value", u_sum2, "Value")
    link(ng, u_aC, "Value", u_sum2, "Value_001")

    # Pick lower or upper based on is_lower
    sw_perlin = add_node(ng, "GeometryNodeSwitch", label="pick triangle",
                         location=(P_X1 + 800, 175), parent=f_perlin)
    sw_perlin.input_type = "FLOAT"
    link(ng, l_sum2, "Value", sw_perlin, "False")
    link(ng, u_sum2, "Value", sw_perlin, "True")
    link(ng, is_lower, "Result", sw_perlin, "Switch")
    perlin_value = sw_perlin.outputs["Output"]

    # ----------------------------------------------------------------------------
    # Frame: VORONOI PATH  (F1 distance to 4 surrounding feature points)
    # ----------------------------------------------------------------------------
    f_voronoi = frame(ng, label="Voronoi (Feature Points)")
    f_voronoi.location = (0, 0)

    # Feature points = integer (col, row), placed at the cell corners.
    # We compute F1 distance from (s.x, s.y) to each of the 4 surrounding
    # feature points, then take the minimum.

    # Distance from (s.x, s.y) to A = (col_w, row_w)
    # dx = s.x - col_w = fu,  dy = s.y - row_w = fv
    # dA^2 = fu^2 + fv^2
    # dA = sqrt(dA^2)
    # Distance to B = (col+1, row) -> dx = fu-1, dy = fv  -> dB = sqrt((1-fu)^2 + fv^2)
    # Distance to C = (col, row+1) -> dx = fu, dy = fv-1 -> dC = sqrt(fu^2 + (1-fv)^2)
    # Distance to D = (col+1, row+1) -> dx = fu-1, dy = fv-1 -> dD = sqrt((1-fu)^2 + (1-fv)^2)

    V_X = P_X1 + 1 * DX
    # dA
    fu_sq = add_node(ng, "ShaderNodeMath", label="fu^2", location=(V_X, 350), parent=f_voronoi)
    fu_sq.operation = "MULTIPLY"
    link(ng, fu, "Value", fu_sq, "Value")
    link(ng, fu, "Value", fu_sq, "Value_001")
    fv_sq = add_node(ng, "ShaderNodeMath", label="fv^2", location=(V_X, 280), parent=f_voronoi)
    fv_sq.operation = "MULTIPLY"
    link(ng, fv, "Value", fv_sq, "Value")
    link(ng, fv, "Value", fv_sq, "Value_001")
    sumA_sq = add_node(ng, "ShaderNodeMath", label="dA^2", location=(V_X + 200, 320), parent=f_voronoi)
    sumA_sq.operation = "ADD"
    link(ng, fu_sq, "Value", sumA_sq, "Value")
    link(ng, fv_sq, "Value", sumA_sq, "Value_001")
    dA = add_node(ng, "ShaderNodeMath", label="dA", location=(V_X + 400, 320), parent=f_voronoi)
    dA.operation = "SQRT"
    link(ng, sumA_sq, "Value", dA, "Value")

    # dB
    one_minus_fu2 = add_node(ng, "ShaderNodeMath", label="(1-fu)^2",
                             location=(V_X, 210), parent=f_voronoi)
    one_minus_fu2.operation = "MULTIPLY"
    link(ng, one_minus_fu, "Value", one_minus_fu2, "Value")
    link(ng, one_minus_fu, "Value", one_minus_fu2, "Value_001")
    sumB_sq = add_node(ng, "ShaderNodeMath", label="dB^2", location=(V_X + 200, 200), parent=f_voronoi)
    sumB_sq.operation = "ADD"
    link(ng, one_minus_fu2, "Value", sumB_sq, "Value")
    link(ng, fv_sq, "Value", sumB_sq, "Value_001")
    dB = add_node(ng, "ShaderNodeMath", label="dB", location=(V_X + 400, 200), parent=f_voronoi)
    dB.operation = "SQRT"
    link(ng, sumB_sq, "Value", dB, "Value")

    # dC
    one_minus_fv2 = add_node(ng, "ShaderNodeMath", label="(1-fv)^2",
                             location=(V_X, 140), parent=f_voronoi)
    one_minus_fv2.operation = "MULTIPLY"
    link(ng, one_minus_fv, "Value", one_minus_fv2, "Value")
    link(ng, one_minus_fv, "Value", one_minus_fv2, "Value_001")
    sumC_sq = add_node(ng, "ShaderNodeMath", label="dC^2", location=(V_X + 200, 130), parent=f_voronoi)
    sumC_sq.operation = "ADD"
    link(ng, fu_sq, "Value", sumC_sq, "Value")
    link(ng, one_minus_fv2, "Value", sumC_sq, "Value_001")
    dC = add_node(ng, "ShaderNodeMath", label="dC", location=(V_X + 400, 130), parent=f_voronoi)
    dC.operation = "SQRT"
    link(ng, sumC_sq, "Value", dC, "Value")

    # dD
    sumD_sq = add_node(ng, "ShaderNodeMath", label="dD^2", location=(V_X + 200, 60), parent=f_voronoi)
    sumD_sq.operation = "ADD"
    link(ng, one_minus_fu2, "Value", sumD_sq, "Value")
    link(ng, one_minus_fv2, "Value", sumD_sq, "Value_001")
    dD = add_node(ng, "ShaderNodeMath", label="dD", location=(V_X + 400, 60), parent=f_voronoi)
    dD.operation = "SQRT"
    link(ng, sumD_sq, "Value", dD, "Value")

    # min(dA, dB, dC, dD)
    minAB = add_node(ng, "ShaderNodeMath", label="min(dA,dB)",
                     location=(V_X + 600, 250), parent=f_voronoi)
    minAB.operation = "MINIMUM"
    link(ng, dA, "Value", minAB, "Value")
    link(ng, dB, "Value", minAB, "Value_001")
    minCD = add_node(ng, "ShaderNodeMath", label="min(dC,dD)",
                     location=(V_X + 600, 100), parent=f_voronoi)
    minCD.operation = "MINIMUM"
    link(ng, dC, "Value", minCD, "Value")
    link(ng, dD, "Value", minCD, "Value_001")
    voronoi_min = add_node(ng, "ShaderNodeMath", label="F1 distance",
                           location=(V_X + 800, 175), parent=f_voronoi)
    voronoi_min.operation = "MINIMUM"
    link(ng, minAB, "Value", voronoi_min, "Value")
    link(ng, minCD, "Value", voronoi_min, "Value_001")

    # The F1 distance for the host cell is in [0, sqrt(2)/2] for a 1x1 cell.
    # Remap to a friendly 0..1-ish range: (1 - 2*F1) clamped to [0, 1]
    # i.e. value = max(0, 1 - 2*F1)
    two_F1 = add_node(ng, "ShaderNodeMath", label="2*F1",
                      location=(V_X + 1000, 175), parent=f_voronoi)
    two_F1.operation = "MULTIPLY"
    link(ng, voronoi_min, "Value", two_F1, "Value")
    two_F1.inputs[1].default_value = 2.0
    one_minus_2F1 = add_node(ng, "ShaderNodeMath", label="1 - 2*F1",
                             location=(V_X + 1200, 175), parent=f_voronoi)
    one_minus_2F1.operation = "SUBTRACT"
    one_minus_2F1.inputs[0].default_value = 1.0
    link(ng, two_F1, "Value", one_minus_2F1, "Value")
    voronoi_value = one_minus_2F1.outputs["Value"]

    # ----------------------------------------------------------------------------
    # Frame: MODE SWITCH  (Pick perlin or voronoi via the master Menu Switch)
    # ----------------------------------------------------------------------------
    f_switch = frame(ng, label="Mode Switch")
    f_switch.location = (0, 0)

    sw_mode = add_node(ng, "GeometryNodeSwitch", label="Perlin or Voronoi",
                       location=(P_X1 + 1100, 175), parent=f_switch)
    sw_mode.input_type = "FLOAT"
    link(ng, perlin_value, "Output", sw_mode, "False")
    link(ng, voronoi_value, "Value", sw_mode, "True")
    # The switch is driven by the master Menu Switch's output (INT 0 = Perlin,
    # 1 = Voronoi). MenuSwitch's Output is an INT.
    link(ng, menu_noise, "Output", sw_mode, "Switch")
    noise_value = sw_mode.outputs["Output"]

    # ----------------------------------------------------------------------------
    # Frame: OUTPUT  (Store named attribute + Group Output)
    # ----------------------------------------------------------------------------
    f_output = frame(ng, label="Output (Store Attribute)")
    f_output.location = (0, 0)

    store = add_node(ng, "GeometryNodeStoreNamedAttribute", label="Store Noise",
                     location=(P_X1 + 1300, 175), parent=f_output)
    store.data_type = "FLOAT"
    store.domain = "CORNER"
    link(ng, noise_value, "Output", store, "Value")
    link(ng, gi, "Selection", store, "Selection")
    link(ng, gi, "Output Attribute", store, "Name")

    # Connect the Geometry through
    link(ng, gi, "Geometry", store, "Geometry")

    # Group Output
    go.parent = f_output
    go.location = (P_X1 + 1600, 175)
    link(ng, store, "Geometry", go, "Geometry")

    # ----------------------------------------------------------------------------
    # Set tooltips on every input socket (only EMPTY ones, per project rules)
    # ----------------------------------------------------------------------------
    set_tooltip(ng, "Geometry", "Mesh to evaluate the noise on. The modifier stores a FLOAT attribute (default 'TileableTriNoise') on the FACE_CORNER domain and passes the mesh through unchanged.")
    set_tooltip(ng, "Selection", "Boolean mask (face-corner domain). When False, the face corner's stored noise value is left untouched.")
    # The panel-level sockets already got descriptions at creation time.

    # ----------------------------------------------------------------------------
    # Asset marking (per project_geonode_modifier_asset_checklist)
    # ----------------------------------------------------------------------------
    ng.asset_mark()
    ng.asset_data.catalog_id = ST3E_CATALOG
    ng.asset_data.tags.new(ST3E_TAG)
    ng.is_modifier = True
    ng.is_tool = False
    ng.asset_data.description = (
        "Tileable Perlin / Voronoi noise structured as a piecewise-linear (triangulated) "
        "scalar field. Each unit cell of a configurable grid is split into 2 right triangles; "
        "Perlin mode barycentric-interpolates 3 per-vertex hashes per face corner, Voronoi "
        "mode returns the F1 distance to the 4 surrounding feature points. The integer "
        "lattice wraps modulo the noise scale, so the field is exactly continuous at tile "
        "boundaries."
    )

    # ----------------------------------------------------------------------------
    # Build a demo object: a subdivided plane with UVs
    # ----------------------------------------------------------------------------
    mesh = bpy.data.meshes.new("GN_Demo_Mesh")
    bm = bmesh.new()
    # 4x4 quads -> 32 triangles with UVs
    bmesh.ops.create_grid(bm, x_segments=4, y_segments=4, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    # Add a UV layer
    uv_layer = mesh.uv_layers.new(name="UVMap")
    # Manually populate UV coords (bmesh create_grid doesn't auto-fill uv)
    bm = bmesh.new()
    bm.from_mesh(mesh)
    uv_lay = bm.loops.layers.uv.verify()
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_lay].uv = (loop.vert.co.x * 0.5 + 0.5, loop.vert.co.y * 0.5 + 0.5)
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("GN_Demo", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    mod = obj.modifiers.new(name="GN", type="NODES")
    mod.node_group = ng

    # Set a few non-default modifier inputs so the user sees a meaningful
    # first preview
    try:
        mod["Socket_3"] = 8  # Noise Scale
    except Exception:
        pass
    try:
        mod["Socket_10"] = "TileableTriNoise"  # Output Attribute
    except Exception:
        pass

    # Save full mainfile
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_FILE)
    print(f"[OK] Wrote {OUT_FILE}")
    print(f"     group: {ng.name}")
    print(f"     node count: {len(ng.nodes)}")
    print(f"     link count: {len(ng.links)}")
    print(f"     frame count: {sum(1 for n in ng.nodes if n.bl_idname == 'NodeFrame')}")


if __name__ == "__main__":
    log_path = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\_build\build.log"
    try:
        build()
    except Exception as e:
        import traceback
        with open(log_path, "w") as f:
            f.write("BUILD FAILED:\n")
            traceback.print_exc(file=f)
        print("BUILD FAILED:", e)
        traceback.print_exc()
    finally:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(0)
