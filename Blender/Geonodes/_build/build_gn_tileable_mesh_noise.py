"""Build GN_TileableMeshNoise v2 — tileable cell-mesh generator with noise
PASSES, input-mesh cells, per-cell pass probability, and cell isolation.

v1 concept (kept): the input mesh's XY bounding box is the TILE; the output is
a cell mesh that repeats seamlessly every tile. "Cell Type" menu:
  Perlin Grid (0): quad cells warped by a smooth tileable value-noise field
  Voronoi (1): jittered lattice -> Triangulate -> Dual Mesh cell polygons
  Input Mesh (2, NEW): the input mesh itself becomes the base cells (one cell
    per input face, cell_id = face index); "Cell Subdivision" doubles as the
    tessellation parameter before the first deform.

v2 additions (user brief 2026-07-18):
  - Passes (1..4): a Repeat Zone runs after the base cells. Each extra pass
    subdivides the mesh once (sub-cells), DOUBLES the noise lattice frequency,
    scales amplitude by Pass Falloff^pass, reseeds, warps, and re-stores
    cell_id/cell_random on the finer lattice.
  - Pass Probability: per PARENT cell, hash01(parent_id, pass seed) < P gates
    the pass. Gated-off cells keep their parent id/random (they stay ONE cell
    logically) and get zero sub-deformation (their sub-verts stay put; the
    face->point mean of the gate softly blends at cell borders).
  - Isolate Cells + Cell Gap: Face Group Boundaries(cell_id) -> Split Edges ->
    Scale Elements(FACE, 1 - gap) shrinks every cell island around its own
    center, so cells become separate mesh islands with a visible gap.

Float32 discipline: hash keys = c*4096 + r + 999331; with Cells X/Y <= 128 and
4 passes the lattice tops out at 2048 -> keys < 2^24, cell ids < 2^22 — all
exact in float32. Channel/pass separation goes through the Hash node's SEED
input, never the key.

Usage:
  blender --background --factory-startup \
      --python D:/Stephko_Tooling/Toolings/Blender/Geonodes/_build/build_gn_tileable_mesh_noise.py
"""

import bpy
import sys
import os
import bmesh

OUT_DIR = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
OUT_FILE = os.path.join(OUT_DIR, "GN_TileableMeshNoise.blend")
GROUP_NAME = "GN_TileableMeshNoise"
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


def _resolve_socket(node_or_socket, key, io):
    """ENABLED sockets take priority even over identifier matches: multi-type
    nodes (Compare!) keep a disabled socket whose identifier is the plain name
    ("A") while the enabled one is suffixed ("A_INT") — linking the disabled
    socket silently no-ops at evaluation time. Bit us on the border-pin chain."""
    if isinstance(node_or_socket, bpy.types.NodeSocket):
        return node_or_socket
    socks = getattr(node_or_socket, io)
    for s in socks:
        if s.enabled and s.identifier == key:
            return s
    for s in socks:
        if s.enabled and s.name == key:
            return s
    for s in socks:
        if s.identifier == key:
            return s
    for s in socks:
        if s.name == key:
            return s
    raise KeyError(f"no {io} socket '{key}' on {node_or_socket.name}")


def frame(ng, *, label):
    f = ng.nodes.new("NodeFrame")
    f.label = label
    f.location = (0, 0)  # frame at (0,0) keeps child .location absolute
    return f


def set_menu_items(menu_switch, names):
    """RENAME stock items in place (IDs stay 0,1,...) — item IDs are
    ever-increasing and the modifier menu override int is the item ID."""
    ed = menu_switch.enum_definition
    while len(ed.enum_items) > len(names):
        ed.enum_items.remove(ed.enum_items[-1])
    for i, n in enumerate(names):
        if i < len(ed.enum_items):
            ed.enum_items[i].name = n
        else:
            ed.enum_items.new(n)


def float_out(n):
    """First enabled scalar output — Math has 'Value', Mix/MapRange 'Result',
    Hash 'Hash'. Sockets pass through unchanged."""
    if isinstance(n, bpy.types.NodeSocket):
        return n
    for cand in ("Value", "Result", "Hash"):
        for s in n.outputs:
            if s.enabled and s.name == cand:
                return s
    return n.outputs[0]


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ng = bpy.data.node_groups.new(GROUP_NAME, "GeometryNodeTree")

    def link(src, src_socket, dst, dst_socket):
        out = _resolve_socket(src, src_socket, "outputs")
        inp = _resolve_socket(dst, dst_socket, "inputs")
        return ng.links.new(out, inp)

    def math(op, label, loc, parent, *, c0=None, c1=None, c2=None):
        n = add_node(ng, "ShaderNodeMath", location=loc, label=label, parent=parent)
        n.operation = op
        if c0 is not None:
            n.inputs[0].default_value = c0
        if c1 is not None:
            n.inputs[1].default_value = c1
        if c2 is not None:
            n.inputs[2].default_value = c2
        return n

    gi = add_node(ng, "NodeGroupInput", location=(-3600, 0), label="Inputs")
    go = add_node(ng, "NodeGroupOutput", location=(4200, 0), label="Output")

    def gis(name):
        return _resolve_socket(gi, name, "outputs")

    # --- Interface -----------------------------------------------------------
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    cells_panel = ng.interface.new_panel("Cells")
    dist_panel = ng.interface.new_panel("Distortion")
    pass_panel = ng.interface.new_panel("Passes")
    iso_panel = ng.interface.new_panel("Isolation")
    attr_panel = ng.interface.new_panel("Output Attributes")

    def add_sock(panel, name, socket_type, default=None, min=None, max=None, description=""):
        s = ng.interface.new_socket(name, in_out="INPUT", socket_type=socket_type,
                                    parent=panel)
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

    menu_sock = add_sock(cells_panel, "Cell Type", "NodeSocketMenu",
                         description="Base cells: Perlin Grid = noise-warped quad grid (4-sided); Voronoi = irregular cell polygons (~6-sided, dual mesh); Input Mesh = the input mesh's own faces become the cells; Triangles = 3-sided cells; Pentagons = 5-sided cells (prismatic tiling, best with even Cells Y); Octagons = 8-sided cells with small square fillers (truncated-square tiling, best with even Cells X/Y — a flat tiling of pure 8-gons is geometrically impossible).")
    add_sock(cells_panel, "Bounds Size", "NodeSocketVector", default=(0.0, 0.0, 0.0),
             min=0.0,
             description="Tile bounds in meters. 0 = automatic (each axis sized from the input mesh's bounding box). Set X and/or Y to force that tile dimension — the pattern then repeats seamlessly every X/Y meters. Z is ignored.")
    add_sock(cells_panel, "Cells X", "NodeSocketInt", default=8, min=1, max=128,
             description="Cells along X inside one tile (the tile width — Bounds Size X, or the input's bounding-box width when Bounds Size is 0). Capped at 128 so 4 passes of refinement stay numerically exact.")
    add_sock(cells_panel, "Cells Y", "NodeSocketInt", default=8, min=1, max=128,
             description="Cells along Y inside one tile (the tile depth — Bounds Size Y, or the input's bounding-box depth when Bounds Size is 0).")
    add_sock(cells_panel, "Cell Subdivision", "NodeSocketInt", default=0, min=0, max=4,
             description="Subdivide the base cells before the first deform so cell interiors can bend. In Input Mesh mode this is the tessellation applied to the input mesh.")
    dist_menu_sock = add_sock(dist_panel, "Distortion Type", "NodeSocketMenu",
                              description="Distortion algorithm: Perlin = smooth value-noise offsets; Voronoi = pull geometry toward the nearest jittered feature point (cellular pucker); Swirl = a random vortex inside every lattice cell (fades to zero at the cell border — needs Cell Subdivision or Passes to show on a plain grid).")
    add_sock(dist_panel, "Distortion", "NodeSocketFloat", default=0.75, min=0.0, max=1.0,
             description="Distortion strength. Perlin: vertex wander up to 45% of a cell (flip-free); Voronoi: pull fraction toward the nearest feature; Swirl: vortex angle up to a half turn.")
    add_sock(dist_panel, "Seed", "NodeSocketInt", default=0, min=0, max=99999,
             description="Random seed for the tileable hash lattice. Every pass derives its own seed from this.")
    add_sock(pass_panel, "Passes", "NodeSocketInt", default=1, min=1, max=4,
             description="Noise passes. Pass 1 deforms the base cells; every further pass subdivides the cells once, doubles the noise frequency, and deforms the resulting sub-cells (fresh cell ids on the finer lattice).")
    add_sock(pass_panel, "Pass Falloff", "NodeSocketFloat", default=0.5, min=0.0, max=1.0,
             description="Amplitude multiplier per extra pass (0.5 = each pass distorts half as much as the previous one).")
    add_sock(pass_panel, "Pass Probability", "NodeSocketFloat", default=1.0, min=0.0, max=1.0,
             description="Chance per PARENT cell that a pass refines it. Skipped cells keep their parent cell id/random and receive no sub-deformation, so they remain one coarse cell.")
    add_sock(iso_panel, "Isolate Cells", "NodeSocketBool", default=False,
             description="Split the mesh along every cell boundary so each cell becomes its own island (cells stay in one mesh but share no vertices).")
    add_sock(iso_panel, "Preserve Tile Border", "NodeSocketBool", default=True,
             description="Pin the tile's outer-boundary vertices during the gap shrink so tiled instances stay continuous — border cells keep their outer edge on the tile bounds and only their inner walls open a gap.")
    add_sock(iso_panel, "Cell Gap", "NodeSocketFloat", default=0.1, min=0.0, max=0.95,
             description="With Isolate Cells: shrink every cell island toward its own center by this fraction, opening a visible gap between neighboring cells.")
    add_sock(attr_panel, "Cell ID Attribute", "NodeSocketString", default="cell_id",
             description="Name of the INT face attribute holding each cell's tile-stable index (cells split by the tile border share one id).")
    add_sock(attr_panel, "Cell Random Attribute", "NodeSocketString", default="cell_random",
             description="Name of the FLOAT face attribute holding a per-cell random value in 0..1 (for shading variation).")
    add_sock(attr_panel, "Cell Color Attribute", "NodeSocketString", default="cell_color",
             description="Name of the COLOR (face-corner) attribute holding a random debug color per cell — view it via Viewport Shading > Attribute or in Vertex Paint to inspect the cells at a glance.")

    # ------------------------------------------------------------------------
    # Frame: BOUNDS & LATTICE
    # ------------------------------------------------------------------------
    f_bounds = frame(ng, label="Bounds & Lattice")
    X = -3300
    bb = add_node(ng, "GeometryNodeBoundBox", label="Input Bounds",
                  location=(X, 400), parent=f_bounds)
    link(gi, "Geometry", bb, "Geometry")
    sep_min = add_node(ng, "ShaderNodeSeparateXYZ", label="Min",
                       location=(X + 300, 500), parent=f_bounds)
    link(bb, "Min", sep_min, "Vector")
    sep_max = add_node(ng, "ShaderNodeSeparateXYZ", label="Max",
                       location=(X + 300, 300), parent=f_bounds)
    link(bb, "Max", sep_max, "Vector")

    w_raw = math("SUBTRACT", "max.x - min.x", (X + 600, 500), f_bounds)
    link(sep_max, "X", w_raw, "Value")
    link(sep_min, "X", w_raw, "Value_001")
    autoW = math("MAXIMUM", "Auto W", (X + 800, 500), f_bounds, c1=0.001)
    link(w_raw, "Value", autoW, "Value")

    h_raw = math("SUBTRACT", "max.y - min.y", (X + 600, 300), f_bounds)
    link(sep_max, "Y", h_raw, "Value")
    link(sep_min, "Y", h_raw, "Value_001")
    autoH = math("MAXIMUM", "Auto H", (X + 800, 300), f_bounds, c1=0.001)
    link(h_raw, "Value", autoH, "Value")

    # Bounds Size override: any positive component replaces the auto bounds on
    # that axis. Pure-Math blend (final = auto + (custom - auto) * (custom > 0))
    # keeps the output socket named "Value" so every downstream link() keys on
    # the same socket name as a plain Math node.
    sep_bs = add_node(ng, "ShaderNodeSeparateXYZ", label="Bounds Size",
                      location=(X + 600, 750), parent=f_bounds)
    link(gi, "Bounds Size", sep_bs, "Vector")

    def bounds_override(axis, auto_node, y):
        gt = math("GREATER_THAN", f"custom {axis} set?", (X + 800, y), f_bounds,
                  c1=0.0)
        link(sep_bs, axis.upper(), gt, "Value")
        diff = math("SUBTRACT", f"custom - auto {axis}", (X + 1000, y), f_bounds)
        link(sep_bs, axis.upper(), diff, "Value")
        link(auto_node, "Value", diff, "Value_001")
        final = math("MULTIPLY_ADD", f"Tile {axis.upper()}", (X + 1200, y),
                     f_bounds)
        link(diff, "Value", final, "Value")
        link(gt, "Value", final, "Value_001")
        link(auto_node, "Value", final, "Value_002")
        return final

    W = bounds_override("x", autoW, 750)
    H = bounds_override("y", autoH, 650)

    center_sum = add_node(ng, "ShaderNodeVectorMath", label="min + max",
                          location=(X + 600, 100), parent=f_bounds)
    center_sum.operation = "ADD"
    link(bb, "Min", center_sum, "Vector")
    link(bb, "Max", center_sum, "Vector_001")
    center = add_node(ng, "ShaderNodeVectorMath", label="Bounds Center",
                      location=(X + 800, 100), parent=f_bounds)
    center.operation = "SCALE"
    center.inputs["Scale"].default_value = 0.5
    link(center_sum, "Vector", center, "Vector")
    neg_center = add_node(ng, "ShaderNodeVectorMath", label="-Center",
                          location=(X + 1000, 100), parent=f_bounds)
    neg_center.operation = "SCALE"
    neg_center.inputs["Scale"].default_value = -1.0
    link(center, "Vector", neg_center, "Vector")

    cellW = math("DIVIDE", "Cell W", (X + 1000, 500), f_bounds)
    link(W, "Value", cellW, "Value")
    link(gi, "Cells X", cellW, "Value_001")
    cellH = math("DIVIDE", "Cell H", (X + 1000, 300), f_bounds)
    link(H, "Value", cellH, "Value")
    link(gi, "Cells Y", cellH, "Value_001")

    # master Distortion-Type menu: ONE MenuSwitch(INT), fanned to the
    # IndexSwitch(VECTOR) inside each noise block (menu -> index pattern)
    f_dmenu = frame(ng, label="Distortion Type")
    dist_menu = add_node(ng, "GeometryNodeMenuSwitch", label="Distortion Type",
                         location=(X + 1300, 150), parent=f_dmenu)
    dist_menu.data_type = "INT"
    set_menu_items(dist_menu, ["Perlin", "Voronoi", "Swirl"])
    dist_menu.inputs["Perlin"].default_value = 0
    dist_menu.inputs["Voronoi"].default_value = 1
    dist_menu.inputs["Swirl"].default_value = 2
    link(gi, "Distortion Type", dist_menu, "Menu")
    dist_menu_sock.default_value = "Perlin"  # AFTER wiring, once the enum exists

    # ------------------------------------------------------------------------
    # Reusable builders (parametric so the Repeat Zone gets its own finer copy)
    # ------------------------------------------------------------------------

    def hash01(c_src, r_src, seed_src, label, loc, parent):
        """hash01(c, r) in [0,1). Key = c*4096 + r + 999331 (< 2^24, float32-
        exact); pass/channel separation goes through the Seed input. Modulo a
        PRIME (46337) — power-of-two moduli showed low-bit collision clusters."""
        k1 = math("MULTIPLY_ADD", label + " key", loc, parent, c1=4096)
        link(float_out(c_src), "", k1, "Value")
        link(float_out(r_src), "", k1, "Value_002")
        k2 = math("ADD", label + " +c", (loc[0] + 180, loc[1]), parent, c1=999331)
        link(k1, "Value", k2, "Value")
        h = add_node(ng, "FunctionNodeHashValue", label=label,
                     location=(loc[0] + 360, loc[1]), parent=parent)
        h.data_type = "INT"
        link(k2, "Value", h, "Value")
        link(float_out(seed_src), "", h, "Seed")
        hm = math("FLOORED_MODULO", label + " mod", (loc[0] + 540, loc[1]),
                  parent, c1=46337)
        link(h, "Hash", hm, "Value")
        hd = math("DIVIDE", label + " 0..1", (loc[0] + 720, loc[1]),
                  parent, c1=46337.0)
        link(hm, "Value", hd, "Value")
        return hd

    def noise_block(tag, parent, X0, nx_src, ny_src, seed_src, strength_src,
                    cellw_src, cellh_src):
        """Tileable XY offset field with three switchable algorithms:
          0 Perlin = smoothstep-bilinear value noise
          1 Voronoi = pull toward the nearest jittered corner feature (the same
            jittered lattice points that seed the Voronoi cell mode)
          2 Swirl = per-cell vortex, fading to zero at the cell border
        Selected by the master Distortion Type menu via an IndexSwitch(VECTOR).
        Returns dict with the offset socket + lattice sub-results for cell ids."""
        pos = add_node(ng, "GeometryNodeInputPosition", label=f"{tag} Position",
                       location=(X0, 200), parent=parent)
        sep = add_node(ng, "ShaderNodeSeparateXYZ", label=f"{tag} Sep Pos",
                       location=(X0 + 200, 200), parent=parent)
        link(pos, "Position", sep, "Vector")

        def s_chain(axis, ext_src, n_src, y):
            d = math("DIVIDE", f"{tag} {axis}/ext", (X0 + 400, y), parent)
            link(sep, axis.upper(), d, "Value")
            link(float_out(ext_src), "", d, "Value_001")
            a = math("ADD", f"{tag} +0.5", (X0 + 600, y), parent, c1=0.5)
            link(d, "Value", a, "Value")
            m = math("MULTIPLY", f"{tag} s.{axis}", (X0 + 800, y), parent)
            link(a, "Value", m, "Value")
            link(float_out(n_src), "", m, "Value_001")
            return m

        sx = s_chain("x", W, nx_src, 300)
        sy = s_chain("y", H, ny_src, 100)

        cx = math("FLOOR", f"{tag} col", (X0 + 1000, 400), parent)
        link(sx, "Value", cx, "Value")
        fx = math("FRACT", f"{tag} fu", (X0 + 1000, 300), parent)
        link(sx, "Value", fx, "Value")
        cy = math("FLOOR", f"{tag} row", (X0 + 1000, 100), parent)
        link(sy, "Value", cy, "Value")
        fy = math("FRACT", f"{tag} fv", (X0 + 1000, 0), parent)
        link(sy, "Value", fy, "Value")

        def wrap(v_node, n_src, label, loc):
            m = math("FLOORED_MODULO", label, loc, parent)
            link(v_node, "Value", m, "Value")
            link(float_out(n_src), "", m, "Value_001")
            return m

        cx0 = wrap(cx, nx_src, f"{tag} col mod", (X0 + 1250, 450))
        cy0 = wrap(cy, ny_src, f"{tag} row mod", (X0 + 1250, 150))
        cx1_raw = math("ADD", f"{tag} col+1", (X0 + 1250, 350), parent, c1=1)
        link(cx, "Value", cx1_raw, "Value")
        cx1 = wrap(cx1_raw, nx_src, f"{tag} (col+1) mod", (X0 + 1450, 350))
        cy1_raw = math("ADD", f"{tag} row+1", (X0 + 1250, 50), parent, c1=1)
        link(cy, "Value", cy1_raw, "Value")
        cy1 = wrap(cy1_raw, ny_src, f"{tag} (row+1) mod", (X0 + 1450, 50))

        u_ss = add_node(ng, "ShaderNodeMapRange", label=f"{tag} smoothstep(fu)",
                        location=(X0 + 1450, 650), parent=parent)
        u_ss.interpolation_type = "SMOOTHSTEP"
        link(fx, "Value", u_ss, "Value")
        v_ss = add_node(ng, "ShaderNodeMapRange", label=f"{tag} smoothstep(fv)",
                        location=(X0 + 1450, 500), parent=parent)
        v_ss.interpolation_type = "SMOOTHSTEP"
        link(fy, "Value", v_ss, "Value")

        def mixf(a, b, fac, label, loc):
            m = add_node(ng, "ShaderNodeMix", label=label, location=loc, parent=parent)
            m.data_type = "FLOAT"
            link(float_out(fac), "", m, "Factor")
            link(float_out(a), "", m, "A")
            link(float_out(b), "", m, "B")
            return m

        # amplitudes from strength (0.9 cap keeps Perlin flip-free)
        amp09 = math("MULTIPLY", f"{tag} strength*0.9", (X0 + 1450, -500), parent, c1=0.9)
        link(float_out(strength_src), "", amp09, "Value")
        ampx = math("MULTIPLY", f"{tag} amp X", (X0 + 1650, -450), parent)
        link(amp09, "Value", ampx, "Value")
        link(float_out(cellw_src), "", ampx, "Value_001")
        ampy = math("MULTIPLY", f"{tag} amp Y", (X0 + 1650, -550), parent)
        link(amp09, "Value", ampy, "Value")
        link(float_out(cellh_src), "", ampy, "Value_001")
        neg_w2 = math("MULTIPLY", f"{tag} -W/2", (X0 + 1650, -650), parent, c1=-0.5)
        link(W, "Value", neg_w2, "Value")
        neg_h2 = math("MULTIPLY", f"{tag} -H/2", (X0 + 1650, -730), parent, c1=-0.5)
        link(H, "Value", neg_h2, "Value")

        def channel(seed_add, ch, y0):
            seed = math("ADD", f"{tag} {ch} seed", (X0 + 1450, y0 + 90), parent,
                        c1=seed_add)
            link(float_out(seed_src), "", seed, "Value")
            hA = hash01(cx0, cy0, seed, f"{tag} h{ch}A", (X0 + 1700, y0), parent)
            hB = hash01(cx1, cy0, seed, f"{tag} h{ch}B", (X0 + 1700, y0 - 90), parent)
            hC = hash01(cx0, cy1, seed, f"{tag} h{ch}C", (X0 + 1700, y0 - 180), parent)
            hD = hash01(cx1, cy1, seed, f"{tag} h{ch}D", (X0 + 1700, y0 - 270), parent)
            m1 = mixf(hA, hB, u_ss, f"{tag} {ch} mix bottom", (X0 + 2650, y0 - 40))
            m2 = mixf(hC, hD, u_ss, f"{tag} {ch} mix top", (X0 + 2650, y0 - 220))
            mv = mixf(m1, m2, v_ss, f"{tag} {ch} bilinear", (X0 + 2850, y0 - 130))
            return mv, {"A": hA, "B": hB, "C": hC, "D": hD}

        ch_x, hx = channel(0, "X", 350)
        ch_y, hy = channel(7919, "Y", -100)

        # ---- 0: PERLIN offset ------------------------------------------------
        def offset_axis(ch, amp_node, label, y):
            c = math("SUBTRACT", f"{tag} {label}-0.5", (X0 + 3100, y), parent, c1=0.5)
            link(float_out(ch), "", c, "Value")
            o = math("MULTIPLY", f"{tag} offset {label}", (X0 + 3300, y), parent)
            link(c, "Value", o, "Value")
            link(amp_node, "Value", o, "Value_001")
            return o

        ox = offset_axis(ch_x, ampx, "X", -100)
        oy = offset_axis(ch_y, ampy, "Y", -250)
        off_perlin = add_node(ng, "ShaderNodeCombineXYZ", label=f"{tag} Perlin Offset",
                              location=(X0 + 3500, -175), parent=parent)
        link(ox, "Value", off_perlin, "X")
        link(oy, "Value", off_perlin, "Y")

        # ---- 1: VORONOI pull (toward nearest jittered corner feature) --------
        # corner features reuse the SAME per-corner hashes as the Perlin
        # channels, so they coincide with the Voronoi cell-mode seed points.
        corners = {
            "A": (cx, cy), "B": (cx1_raw, cy), "C": (cx, cy1_raw), "D": (cx1_raw, cy1_raw),
        }

        def corner_pull(kname, i, ycor):
            ic, jc = corners[kname]
            fx = math("MULTIPLY_ADD", f"{tag} f{kname}.x", (X0 + 3100, ycor), parent)
            link(float_out(ic), "", fx, "Value")
            link(float_out(cellw_src), "", fx, "Value_001")
            link(neg_w2, "Value", fx, "Value_002")
            jxa = math("SUBTRACT", f"{tag} f{kname} jx", (X0 + 3100, ycor - 60), parent, c1=0.5)
            link(float_out(hx[kname]), "", jxa, "Value")
            jxm = math("MULTIPLY", f"{tag} f{kname} jx*a", (X0 + 3280, ycor - 60), parent)
            link(jxa, "Value", jxm, "Value")
            link(ampx, "Value", jxm, "Value_001")
            fxj = math("ADD", f"{tag} f{kname}.xj", (X0 + 3460, ycor), parent)
            link(fx, "Value", fxj, "Value")
            link(jxm, "Value", fxj, "Value_001")
            fy = math("MULTIPLY_ADD", f"{tag} f{kname}.y", (X0 + 3100, ycor - 120), parent)
            link(float_out(jc), "", fy, "Value")
            link(float_out(cellh_src), "", fy, "Value_001")
            link(neg_h2, "Value", fy, "Value_002")
            jya = math("SUBTRACT", f"{tag} f{kname} jy", (X0 + 3100, ycor - 180), parent, c1=0.5)
            link(float_out(hy[kname]), "", jya, "Value")
            jym = math("MULTIPLY", f"{tag} f{kname} jy*a", (X0 + 3280, ycor - 180), parent)
            link(jya, "Value", jym, "Value")
            link(ampy, "Value", jym, "Value_001")
            fyj = math("ADD", f"{tag} f{kname}.yj", (X0 + 3460, ycor - 120), parent)
            link(fy, "Value", fyj, "Value")
            link(jym, "Value", fyj, "Value_001")
            # pull vector = feature - p, and its squared length
            dx = math("SUBTRACT", f"{tag} {kname} dx", (X0 + 3640, ycor), parent)
            link(fxj, "Value", dx, "Value")
            link(sep, "X", dx, "Value_001")
            dy = math("SUBTRACT", f"{tag} {kname} dy", (X0 + 3640, ycor - 120), parent)
            link(fyj, "Value", dy, "Value")
            link(sep, "Y", dy, "Value_001")
            dxx = math("MULTIPLY", f"{tag} {kname} dx2", (X0 + 3820, ycor), parent)
            link(dx, "Value", dxx, "Value")
            link(dx, "Value", dxx, "Value_001")
            d2 = math("MULTIPLY_ADD", f"{tag} {kname} d^2", (X0 + 3820, ycor - 120), parent)
            link(dy, "Value", d2, "Value")
            link(dy, "Value", d2, "Value_001")
            link(dxx, "Value", d2, "Value_002")
            vec = add_node(ng, "ShaderNodeCombineXYZ", label=f"{tag} {kname} pull",
                           location=(X0 + 4000, ycor - 60), parent=parent)
            link(dx, "Value", vec, "X")
            link(dy, "Value", vec, "Y")
            return d2, vec

        pulls = {k: corner_pull(k, i, -700 - i * 260) for i, k in enumerate("ABCD")}

        def nearer(p1, p2, label, x, y):
            (d1, v1), (d2, v2) = p1, p2
            cmp = add_node(ng, "FunctionNodeCompare", label=f"{tag} {label} nearer?",
                           location=(x, y), parent=parent)
            cmp.data_type = "FLOAT"
            cmp.operation = "LESS_THAN"
            link(float_out(d1), "", cmp, "A")
            link(float_out(d2), "", cmp, "B")
            swd = add_node(ng, "GeometryNodeSwitch", label=f"{tag} {label} d",
                           location=(x + 180, y), parent=parent)
            swd.input_type = "FLOAT"
            link(float_out(d2), "", swd, "False")
            link(float_out(d1), "", swd, "True")
            link(cmp, "Result", swd, "Switch")
            swv = add_node(ng, "GeometryNodeSwitch", label=f"{tag} {label} v",
                           location=(x + 180, y - 120), parent=parent)
            swv.input_type = "VECTOR"
            link(_resolve_socket(v2, "Vector", "outputs") if not isinstance(v2, bpy.types.NodeSocket) else v2, "", swv, "False")
            link(_resolve_socket(v1, "Vector", "outputs") if not isinstance(v1, bpy.types.NodeSocket) else v1, "", swv, "True")
            link(cmp, "Result", swv, "Switch")
            return swd.outputs["Output"], swv.outputs["Output"]

        nAB = nearer(pulls["A"], pulls["B"], "AB", X0 + 4250, -750)
        nCD = nearer(pulls["C"], pulls["D"], "CD", X0 + 4250, -1150)
        n_d, n_v = nearer(nAB, nCD, "F1", X0 + 4650, -950)
        pull_amt = math("MULTIPLY", f"{tag} pull amount", (X0 + 4650, -700), parent, c1=0.75)
        link(float_out(strength_src), "", pull_amt, "Value")
        off_vor_s = add_node(ng, "ShaderNodeVectorMath", label=f"{tag} Voronoi Offset",
                             location=(X0 + 4900, -950), parent=parent)
        off_vor_s.operation = "SCALE"
        link(n_v, "Output", off_vor_s, "Vector")
        link(pull_amt, "Value", off_vor_s, "Scale")
        # keep the pull strictly in-plane (input meshes may have Z)
        off_vor = add_node(ng, "ShaderNodeVectorMath", label=f"{tag} pull XY only",
                           location=(X0 + 5100, -950), parent=parent)
        off_vor.operation = "MULTIPLY"
        off_vor.inputs[1].default_value = (1.0, 1.0, 0.0)
        link(off_vor_s, "Vector", off_vor, "Vector")

        # ---- 2: SWIRL (per-cell vortex, zero at the cell border) -------------
        # The swirl gets its OWN half-frequency lattice: a full-frequency one
        # is resonant with the mesh (grid/pass verts sit exactly on cell
        # corners, where the falloff is zero, so nothing would ever move).
        def swirl_axis_lattice(n_src, ext_node, axis, y):
            half = math("MULTIPLY", f"{tag} sw N{axis}/2", (X0 + 2500, y), parent, c1=0.5)
            link(float_out(n_src), "", half, "Value")
            fl = math("FLOOR", f"{tag} sw floor", (X0 + 2680, y), parent)
            link(half, "Value", fl, "Value")
            n = math("MAXIMUM", f"{tag} sw N{axis}", (X0 + 2860, y), parent, c1=1.0)
            link(fl, "Value", n, "Value")
            csize = math("DIVIDE", f"{tag} sw cell {axis}", (X0 + 3040, y), parent)
            link(ext_node, "Value", csize, "Value")
            link(n, "Value", csize, "Value_001")
            d = math("DIVIDE", f"{tag} sw {axis}/ext", (X0 + 2500, y - 90), parent)
            link(sep, axis.upper(), d, "Value")
            link(ext_node, "Value", d, "Value_001")
            a = math("ADD", f"{tag} sw +0.5", (X0 + 2680, y - 90), parent, c1=0.5)
            link(d, "Value", a, "Value")
            s = math("MULTIPLY", f"{tag} sw s.{axis}", (X0 + 2860, y - 90), parent)
            link(a, "Value", s, "Value")
            link(n, "Value", s, "Value_001")
            c = math("FLOOR", f"{tag} sw c{axis}", (X0 + 3040, y - 90), parent)
            link(s, "Value", c, "Value")
            cw = math("FLOORED_MODULO", f"{tag} sw c{axis} mod", (X0 + 3220, y - 90), parent)
            link(c, "Value", cw, "Value")
            link(n, "Value", cw, "Value_001")
            return c, cw, csize

        scx, scx0, swcw = swirl_axis_lattice(nx_src, W, "x", -1650)
        scy, scy0, swch = swirl_axis_lattice(ny_src, H, "y", -1830)

        ccx = math("ADD", f"{tag} cell cx", (X0 + 3400, -1900), parent, c1=0.5)
        link(scx, "Value", ccx, "Value")
        cwx = math("MULTIPLY_ADD", f"{tag} center x", (X0 + 3580, -1900), parent)
        link(ccx, "Value", cwx, "Value")
        link(swcw, "Value", cwx, "Value_001")
        link(neg_w2, "Value", cwx, "Value_002")
        ccy = math("ADD", f"{tag} cell cy", (X0 + 3400, -2020), parent, c1=0.5)
        link(scy, "Value", ccy, "Value")
        cwy = math("MULTIPLY_ADD", f"{tag} center y", (X0 + 3580, -2020), parent)
        link(ccy, "Value", cwy, "Value")
        link(swch, "Value", cwy, "Value_001")
        link(neg_h2, "Value", cwy, "Value_002")
        # jitter the vortex center (±20% of a swirl cell): an unjittered center
        # is resonant with regular meshes — verts land at r=0 (rotation is a
        # no-op there) or exactly at the falloff radius, so nothing moves
        jx_seed = math("ADD", f"{tag} swjx seed", (X0 + 3400, -2450), parent, c1=666)
        link(float_out(seed_src), "", jx_seed, "Value")
        jx_h = hash01(scx0, scy0, jx_seed, f"{tag} swjx", (X0 + 3580, -2450), parent)
        jy_seed = math("ADD", f"{tag} swjy seed", (X0 + 3400, -2540), parent, c1=777)
        link(float_out(seed_src), "", jy_seed, "Value")
        jy_h = hash01(scx0, scy0, jy_seed, f"{tag} swjy", (X0 + 3580, -2540), parent)
        jx_c = math("SUBTRACT", f"{tag} swjx-0.5", (X0 + 4340, -2450), parent, c1=0.5)
        link(jx_h, "Value", jx_c, "Value")
        jx_a = math("MULTIPLY", f"{tag} swjx amp", (X0 + 4520, -2450), parent, c1=0.4)
        link(swcw, "Value", jx_a, "Value")
        jx = math("MULTIPLY", f"{tag} swirl jx", (X0 + 4700, -2450), parent)
        link(jx_c, "Value", jx, "Value")
        link(jx_a, "Value", jx, "Value_001")
        jy_c = math("SUBTRACT", f"{tag} swjy-0.5", (X0 + 4340, -2540), parent, c1=0.5)
        link(jy_h, "Value", jy_c, "Value")
        jy_a = math("MULTIPLY", f"{tag} swjy amp", (X0 + 4520, -2540), parent, c1=0.4)
        link(swch, "Value", jy_a, "Value")
        jy = math("MULTIPLY", f"{tag} swirl jy", (X0 + 4700, -2540), parent)
        link(jy_c, "Value", jy, "Value")
        link(jy_a, "Value", jy, "Value_001")
        cwx_j = math("ADD", f"{tag} center x jit", (X0 + 3760, -1900), parent)
        link(cwx, "Value", cwx_j, "Value")
        link(jx, "Value", cwx_j, "Value_001")
        cwy_j = math("ADD", f"{tag} center y jit", (X0 + 3760, -2020), parent)
        link(cwy, "Value", cwy_j, "Value")
        link(jy, "Value", cwy_j, "Value_001")
        sdx = math("SUBTRACT", f"{tag} swirl dx", (X0 + 3940, -1900), parent)
        link(sep, "X", sdx, "Value")
        link(cwx_j, "Value", sdx, "Value_001")
        sdy = math("SUBTRACT", f"{tag} swirl dy", (X0 + 3940, -2020), parent)
        link(sep, "Y", sdy, "Value")
        link(cwy_j, "Value", sdy, "Value_001")
        sdx2 = math("MULTIPLY", f"{tag} dx^2", (X0 + 3640, -1900), parent)
        link(sdx, "Value", sdx2, "Value")
        link(sdx, "Value", sdx2, "Value_001")
        sr2 = math("MULTIPLY_ADD", f"{tag} r^2", (X0 + 3640, -2020), parent)
        link(sdy, "Value", sr2, "Value")
        link(sdy, "Value", sr2, "Value_001")
        link(sdx2, "Value", sr2, "Value_002")
        sr = math("SQRT", f"{tag} r", (X0 + 3820, -1960), parent)
        link(sr2, "Value", sr, "Value")
        cell_min = math("MINIMUM", f"{tag} min cell", (X0 + 3640, -2140), parent)
        link(swcw, "Value", cell_min, "Value")
        link(swch, "Value", cell_min, "Value_001")
        # falloff radius 0.3 cell: with ±0.2-cell center jitter the vortex
        # still dies out before the cell border, keeping the field continuous
        rmax = math("MULTIPLY", f"{tag} r max", (X0 + 3820, -2140), parent, c1=0.3)
        link(cell_min, "Value", rmax, "Value")
        rn = math("DIVIDE", f"{tag} r/rmax", (X0 + 4000, -1960), parent)
        link(sr, "Value", rn, "Value")
        link(rmax, "Value", rn, "Value_001")
        tt = math("SUBTRACT", f"{tag} 1-rn", (X0 + 4180, -1960), parent, c0=1.0)
        link(rn, "Value", tt, "Value_001")
        tc = math("MAXIMUM", f"{tag} clamp t", (X0 + 4360, -1960), parent, c1=0.0)
        link(tt, "Value", tc, "Value")
        t2 = math("MULTIPLY", f"{tag} t^2", (X0 + 4540, -1960), parent)
        link(tc, "Value", t2, "Value")
        link(tc, "Value", t2, "Value_001")
        sw_seed = math("ADD", f"{tag} swirl seed", (X0 + 3100, -2260), parent, c1=555)
        link(float_out(seed_src), "", sw_seed, "Value")
        sw_h = hash01(scx0, scy0, sw_seed, f"{tag} swirl h", (X0 + 3280, -2260), parent)
        sw_dir = math("MULTIPLY_ADD", f"{tag} h*2-1", (X0 + 4180, -2260), parent,
                      c1=2.0, c2=-1.0)
        link(sw_h, "Value", sw_dir, "Value")
        sw_str = math("MULTIPLY", f"{tag} strength*2pi", (X0 + 4180, -2380), parent,
                      c1=6.28319)
        link(float_out(strength_src), "", sw_str, "Value")
        th_max = math("MULTIPLY", f"{tag} theta max", (X0 + 4360, -2300), parent)
        link(sw_dir, "Value", th_max, "Value")
        link(sw_str, "Value", th_max, "Value_001")
        theta = math("MULTIPLY", f"{tag} theta", (X0 + 4540, -2200), parent)
        link(th_max, "Value", theta, "Value")
        link(t2, "Value", theta, "Value_001")
        cth = math("COSINE", f"{tag} cos", (X0 + 4720, -2140), parent)
        link(theta, "Value", cth, "Value")
        sth = math("SINE", f"{tag} sin", (X0 + 4720, -2260), parent)
        link(theta, "Value", sth, "Value")
        rx1 = math("MULTIPLY", f"{tag} dx*cos", (X0 + 4900, -2080), parent)
        link(sdx, "Value", rx1, "Value")
        link(cth, "Value", rx1, "Value_001")
        rx2 = math("MULTIPLY", f"{tag} dy*sin", (X0 + 4900, -2200), parent)
        link(sdy, "Value", rx2, "Value")
        link(sth, "Value", rx2, "Value_001")
        rx = math("SUBTRACT", f"{tag} rot x", (X0 + 5080, -2140), parent)
        link(rx1, "Value", rx, "Value")
        link(rx2, "Value", rx, "Value_001")
        ry1 = math("MULTIPLY", f"{tag} dx*sin", (X0 + 4900, -2320), parent)
        link(sdx, "Value", ry1, "Value")
        link(sth, "Value", ry1, "Value_001")
        ry2 = math("MULTIPLY", f"{tag} dy*cos", (X0 + 4900, -2440), parent)
        link(sdy, "Value", ry2, "Value")
        link(cth, "Value", ry2, "Value_001")
        ry = math("ADD", f"{tag} rot y", (X0 + 5080, -2380), parent)
        link(ry1, "Value", ry, "Value")
        link(ry2, "Value", ry, "Value_001")
        sox = math("SUBTRACT", f"{tag} swirl off x", (X0 + 5260, -2140), parent)
        link(rx, "Value", sox, "Value")
        link(sdx, "Value", sox, "Value_001")
        soy = math("SUBTRACT", f"{tag} swirl off y", (X0 + 5260, -2380), parent)
        link(ry, "Value", soy, "Value")
        link(sdy, "Value", soy, "Value_001")
        off_swirl = add_node(ng, "ShaderNodeCombineXYZ", label=f"{tag} Swirl Offset",
                             location=(X0 + 5440, -2260), parent=parent)
        link(sox, "Value", off_swirl, "X")
        link(soy, "Value", off_swirl, "Y")

        # ---- select by the master Distortion Type menu -----------------------
        isw_d = add_node(ng, "GeometryNodeIndexSwitch", label=f"{tag} Pick Distortion",
                         location=(X0 + 5650, -1000), parent=parent)
        isw_d.data_type = "VECTOR"
        while len(isw_d.index_switch_items) < 3:
            isw_d.index_switch_items.new()
        link(dist_menu, "Output", isw_d, "Index")
        link(off_perlin, "Vector", isw_d, "Item_0")
        link(off_vor, "Vector", isw_d, "Item_1")
        link(off_swirl, "Vector", isw_d, "Item_2")
        return {"offset": isw_d.outputs[0], "sx": sx, "sy": sy, "cx": cx, "cy": cy}

    def cell_id_chain(col_src, row_src, nx_src, ny_src, tag, parent, x0, y0):
        col_w = math("FLOORED_MODULO", f"{tag} col mod", (x0, y0), parent)
        link(float_out(col_src), "", col_w, "Value")
        link(float_out(nx_src), "", col_w, "Value_001")
        row_w = math("FLOORED_MODULO", f"{tag} row mod", (x0, y0 - 90), parent)
        link(float_out(row_src), "", row_w, "Value")
        link(float_out(ny_src), "", row_w, "Value_001")
        cid = math("MULTIPLY_ADD", f"{tag} cell id", (x0 + 200, y0 - 45), parent)
        link(row_w, "Value", cid, "Value")
        link(float_out(nx_src), "", cid, "Value_001")
        link(col_w, "Value", cid, "Value_002")
        return cid

    def cell_random_chain(cid, seed_src, tag, parent, x0, y0):
        seed = math("ADD", f"{tag} rnd seed", (x0, y0 - 60), parent, c1=31337)
        link(float_out(seed_src), "", seed, "Value")
        h = add_node(ng, "FunctionNodeHashValue", label=f"{tag} rnd hash",
                     location=(x0 + 180, y0), parent=parent)
        h.data_type = "INT"
        link(float_out(cid), "", h, "Value")
        link(seed, "Value", h, "Seed")
        hm = math("FLOORED_MODULO", f"{tag} rnd mod", (x0 + 360, y0), parent, c1=46337)
        link(h, "Hash", hm, "Value")
        hd = math("DIVIDE", f"{tag} rnd 0..1", (x0 + 540, y0), parent, c1=46337.0)
        link(hm, "Value", hd, "Value")
        return hd

    def store_pair(geo_src, geo_out_sock, domain, cid, crnd, tag, parent, x0, y0,
                   selection=None):
        """cell_random FIRST, cell_id LAST — pass gates read the OLD cell_id,
        so it must be overwritten only in the final store."""
        s1 = add_node(ng, "GeometryNodeStoreNamedAttribute",
                      label=f"{tag} store cell_random", location=(x0, y0), parent=parent)
        s1.data_type = "FLOAT"
        s1.domain = domain
        link(geo_src, geo_out_sock, s1, "Geometry")
        link(gi, "Cell Random Attribute", s1, "Name")
        link(float_out(crnd), "", s1, "Value")
        if selection is not None:
            link(float_out(selection), "", s1, "Selection")
        s2 = add_node(ng, "GeometryNodeStoreNamedAttribute",
                      label=f"{tag} store cell_id", location=(x0 + 250, y0),
                      parent=parent)
        s2.data_type = "INT"
        s2.domain = domain
        link(s1, "Geometry", s2, "Geometry")
        link(gi, "Cell ID Attribute", s2, "Name")
        link(float_out(cid), "", s2, "Value")
        if selection is not None:
            link(float_out(selection), "", s2, "Selection")
        return s2

    # ------------------------------------------------------------------------
    # Frame: PASS-1 NOISE FIELD (base lattice)
    # ------------------------------------------------------------------------
    f_field = frame(ng, label="Pass 1 Noise Field")
    nb1 = noise_block("P1", f_field, -2000, gis("Cells X"), gis("Cells Y"),
                      gis("Seed"), gis("Distortion"), cellW, cellH)

    # ------------------------------------------------------------------------
    # Frame: BASE GRID
    # ------------------------------------------------------------------------
    f_grid = frame(ng, label="Base Grid")
    GX = -2600
    vx = math("ADD", "Cells X + 1", (GX, -700), f_grid, c1=1)
    link(gi, "Cells X", vx, "Value")
    vy = math("ADD", "Cells Y + 1", (GX, -850), f_grid, c1=1)
    link(gi, "Cells Y", vy, "Value")
    grid = add_node(ng, "GeometryNodeMeshGrid", label="Cell Grid",
                    location=(GX + 300, -750), parent=f_grid)
    link(W, "Value", grid, "Size X")
    link(H, "Value", grid, "Size Y")
    link(vx, "Value", grid, "Vertices X")
    link(vy, "Value", grid, "Vertices Y")

    # ------------------------------------------------------------------------
    # Frame: PERLIN GRID CELLS
    # ------------------------------------------------------------------------
    f_quad = frame(ng, label="Perlin Grid Cells")
    QX = 1600
    q_cid = cell_id_chain(nb1["cx"], nb1["cy"], gis("Cells X"), gis("Cells Y"),
                          "Q", f_quad, QX, 700)
    q_rnd = cell_random_chain(q_cid, gis("Seed"), "Q", f_quad, QX + 450, 700)
    q_store = store_pair(grid, "Mesh", "FACE", q_cid, q_rnd, "Q", f_quad,
                         QX + 1150, 600)
    q_subdiv = add_node(ng, "GeometryNodeSubdivideMesh", label="Subdivide Cells",
                        location=(QX + 1500, 600), parent=f_quad)
    link(q_store, "Geometry", q_subdiv, "Mesh")
    link(gi, "Cell Subdivision", q_subdiv, "Level")
    q_warp = add_node(ng, "GeometryNodeSetPosition", label="Warp by Field",
                      location=(QX + 1750, 600), parent=f_quad)
    link(q_subdiv, "Mesh", q_warp, "Geometry")
    link(nb1["offset"], "Vector", q_warp, "Offset")

    # ------------------------------------------------------------------------
    # Frame: VORONOI CELLS
    # ------------------------------------------------------------------------
    f_vor = frame(ng, label="Voronoi Cells")
    VX = 1600
    v_col = math("ROUND", "V vert col", (VX, -100), f_vor)
    link(nb1["sx"], "Value", v_col, "Value")
    v_row = math("ROUND", "V vert row", (VX, -190), f_vor)
    link(nb1["sy"], "Value", v_row, "Value")
    v_cid = cell_id_chain(v_col, v_row, gis("Cells X"), gis("Cells Y"),
                          "V", f_vor, VX + 220, -100)
    v_rnd = cell_random_chain(v_cid, gis("Seed"), "V", f_vor, VX + 670, -100)
    v_store = store_pair(grid, "Mesh", "POINT", v_cid, v_rnd, "V", f_vor,
                         VX + 1350, -200)
    v_jitter = add_node(ng, "GeometryNodeSetPosition", label="Jitter Points",
                        location=(VX + 1700, -200), parent=f_vor)
    link(v_store, "Geometry", v_jitter, "Geometry")
    link(nb1["offset"], "Vector", v_jitter, "Offset")
    v_tri = add_node(ng, "GeometryNodeTriangulate", label="Triangulate",
                     location=(VX + 1950, -200), parent=f_vor)
    link(v_jitter, "Geometry", v_tri, "Mesh")
    v_dual = add_node(ng, "GeometryNodeDualMesh", label="Dual Mesh (cells)",
                      location=(VX + 2200, -200), parent=f_vor)
    link(v_tri, "Mesh", v_dual, "Mesh")
    v_dual.inputs["Keep Boundaries"].default_value = True
    v_subdiv = add_node(ng, "GeometryNodeSubdivideMesh", label="Subdivide Cells",
                        location=(VX + 2450, -200), parent=f_vor)
    link(v_dual, "Dual Mesh", v_subdiv, "Mesh")
    link(gi, "Cell Subdivision", v_subdiv, "Level")

    # -- Pentagons: triangulate only every OTHER row -> every vertex reaches
    #    valence 5 -> the dual is the prismatic pentagonal tiling
    p5_rowm = math("FLOORED_MODULO", "P5 row mod Ny", (VX + 1900, -550), f_vor)
    link(nb1["cy"], "Value", p5_rowm, "Value")
    link(gi, "Cells Y", p5_rowm, "Value_001")
    p5_row2 = math("FLOORED_MODULO", "P5 row parity", (VX + 2080, -550), f_vor, c1=2)
    link(p5_rowm, "Value", p5_row2, "Value")
    p5_odd = add_node(ng, "FunctionNodeCompare", label="P5 odd row?",
                      location=(VX + 2260, -550), parent=f_vor)
    p5_odd.data_type = "FLOAT"
    p5_odd.operation = "GREATER_THAN"
    link(p5_row2, "Value", p5_odd, "A")
    _resolve_socket(p5_odd, "B", "inputs").default_value = 0.5
    p5_tri = add_node(ng, "GeometryNodeTriangulate", label="P5 Triangulate Odd Rows",
                      location=(VX + 2450, -550), parent=f_vor)
    p5_tri.inputs["Quad Method"].default_value = "Fixed"
    link(v_jitter, "Geometry", p5_tri, "Mesh")
    link(p5_odd, "Result", p5_tri, "Selection")
    p5_dual = add_node(ng, "GeometryNodeDualMesh", label="P5 Dual (pentagons)",
                       location=(VX + 2700, -550), parent=f_vor)
    link(p5_tri, "Mesh", p5_dual, "Mesh")
    p5_dual.inputs["Keep Boundaries"].default_value = True
    p5_subdiv = add_node(ng, "GeometryNodeSubdivideMesh", label="P5 Subdivide",
                         location=(VX + 2950, -550), parent=f_vor)
    link(p5_dual, "Dual Mesh", p5_subdiv, "Mesh")
    link(gi, "Cell Subdivision", p5_subdiv, "Level")

    # -- Octagons & squares: CHECKERBOARD diagonals -> valence 8 / 4 verts ->
    #    dual is the truncated-square tiling. Blender's "Fixed Alternate" is
    #    NOT per-face alternation (it is just the other fixed diagonal), so
    #    checkerboard = two selective Triangulate passes, one per parity.
    o8_colw = math("FLOORED_MODULO", "O8 col mod", (VX + 1700, -900), f_vor)
    link(nb1["cx"], "Value", o8_colw, "Value")
    link(gi, "Cells X", o8_colw, "Value_001")
    o8_roww = math("FLOORED_MODULO", "O8 row mod", (VX + 1700, -980), f_vor)
    link(nb1["cy"], "Value", o8_roww, "Value")
    link(gi, "Cells Y", o8_roww, "Value_001")
    o8_sum = math("ADD", "O8 col+row", (VX + 1880, -940), f_vor)
    link(o8_colw, "Value", o8_sum, "Value")
    link(o8_roww, "Value", o8_sum, "Value_001")
    o8_par = math("FLOORED_MODULO", "O8 parity", (VX + 2060, -940), f_vor, c1=2)
    link(o8_sum, "Value", o8_par, "Value")
    o8_even = add_node(ng, "FunctionNodeCompare", label="O8 even?",
                       location=(VX + 2240, -900), parent=f_vor)
    o8_even.data_type = "FLOAT"
    o8_even.operation = "LESS_THAN"
    link(o8_par, "Value", o8_even, "A")
    _resolve_socket(o8_even, "B", "inputs").default_value = 0.5
    o8_odd = add_node(ng, "FunctionNodeCompare", label="O8 odd?",
                      location=(VX + 2240, -1020), parent=f_vor)
    o8_odd.data_type = "FLOAT"
    o8_odd.operation = "GREATER_THAN"
    link(o8_par, "Value", o8_odd, "A")
    _resolve_socket(o8_odd, "B", "inputs").default_value = 0.5
    o8_tri1 = add_node(ng, "GeometryNodeTriangulate", label="O8 Tri Even (0-2)",
                       location=(VX + 2450, -900), parent=f_vor)
    o8_tri1.inputs["Quad Method"].default_value = "Fixed"
    link(v_jitter, "Geometry", o8_tri1, "Mesh")
    link(o8_even, "Result", o8_tri1, "Selection")
    o8_tri = add_node(ng, "GeometryNodeTriangulate", label="O8 Tri Odd (1-3)",
                      location=(VX + 2700, -900), parent=f_vor)
    o8_tri.inputs["Quad Method"].default_value = "Fixed Alternate"
    link(o8_tri1, "Mesh", o8_tri, "Mesh")
    link(o8_odd, "Result", o8_tri, "Selection")
    o8_dual = add_node(ng, "GeometryNodeDualMesh", label="O8 Dual (octagons)",
                       location=(VX + 2950, -900), parent=f_vor)
    link(o8_tri, "Mesh", o8_dual, "Mesh")
    o8_dual.inputs["Keep Boundaries"].default_value = True
    o8_subdiv = add_node(ng, "GeometryNodeSubdivideMesh", label="O8 Subdivide",
                         location=(VX + 2950, -900), parent=f_vor)
    link(o8_dual, "Dual Mesh", o8_subdiv, "Mesh")
    link(gi, "Cell Subdivision", o8_subdiv, "Level")

    # ------------------------------------------------------------------------
    # Frame: TRIANGLE CELLS (3-sided: triangulated grid, cells = triangles)
    # ------------------------------------------------------------------------
    f_t3 = frame(ng, label="Triangle Cells")
    TX = 1600
    t3_tri = add_node(ng, "GeometryNodeTriangulate", label="T3 Triangulate",
                      location=(TX, -1700), parent=f_t3)
    t3_tri.inputs["Quad Method"].default_value = "Fixed"
    link(grid, "Mesh", t3_tri, "Mesh")
    # cell id = quad id * 2 + (upper triangle?) — FIXED splits every quad the
    # same way, so fu+fv of the face center decides lower/upper (1/3+1/3 vs 2/3+2/3)
    t3_fu = math("SUBTRACT", "T3 fu", (TX, -1950), f_t3)
    link(nb1["sx"], "Value", t3_fu, "Value")
    link(nb1["cx"], "Value", t3_fu, "Value_001")
    t3_fv = math("SUBTRACT", "T3 fv", (TX, -2030), f_t3)
    link(nb1["sy"], "Value", t3_fv, "Value")
    link(nb1["cy"], "Value", t3_fv, "Value_001")
    # "Fixed" splits along the LL-UR diagonal, so BOTH triangle centers have
    # fu+fv = exactly 1.0 — a sum test is knife-edge unstable. The diagonal
    # separates fu > fv (lower-right) from fu < fv (upper-left): robust.
    t3_upper = add_node(ng, "FunctionNodeCompare", label="T3 right of diag?",
                        location=(TX + 360, -1990), parent=f_t3)
    t3_upper.data_type = "FLOAT"
    t3_upper.operation = "GREATER_THAN"
    link(t3_fu, "Value", t3_upper, "A")
    link(t3_fv, "Value", t3_upper, "B")
    t3_base = cell_id_chain(nb1["cx"], nb1["cy"], gis("Cells X"), gis("Cells Y"),
                            "T3", f_t3, TX + 560, -1950)
    t3_cid = math("MULTIPLY_ADD", "T3 cell id", (TX + 960, -1990), f_t3, c1=2)
    link(t3_base, "Value", t3_cid, "Value")
    link(t3_upper, "Result", t3_cid, "Value_002")
    t3_rnd = cell_random_chain(t3_cid, gis("Seed"), "T3", f_t3, TX + 1160, -1950)
    t3_store = store_pair(t3_tri, "Mesh", "FACE", t3_cid, t3_rnd, "T3", f_t3,
                          TX + 1800, -1800)
    t3_subdiv = add_node(ng, "GeometryNodeSubdivideMesh", label="T3 Subdivide",
                         location=(TX + 2150, -1800), parent=f_t3)
    link(t3_store, "Geometry", t3_subdiv, "Mesh")
    link(gi, "Cell Subdivision", t3_subdiv, "Level")
    t3_warp = add_node(ng, "GeometryNodeSetPosition", label="T3 Warp by Field",
                       location=(TX + 2400, -1800), parent=f_t3)
    link(t3_subdiv, "Mesh", t3_warp, "Geometry")
    link(nb1["offset"], "Vector", t3_warp, "Offset")

    # ------------------------------------------------------------------------
    # Frame: INPUT MESH CELLS (one cell per input face; origin-local)
    # ------------------------------------------------------------------------
    f_inp = frame(ng, label="Input Mesh Cells")
    IX = 1600
    # work origin-local like the generated branches; moved back at the end
    i_local = add_node(ng, "GeometryNodeTransform", label="To Origin",
                       location=(IX, -1000), parent=f_inp)
    link(gi, "Geometry", i_local, "Geometry")
    link(neg_center, "Vector", i_local, "Translation")
    i_idx = add_node(ng, "GeometryNodeInputIndex", label="Face Index",
                     location=(IX, -1250), parent=f_inp)
    i_rnd = cell_random_chain(i_idx, gis("Seed"), "I", f_inp, IX + 250, -1250)
    i_store = store_pair(i_local, "Geometry", "FACE", i_idx, i_rnd, "I", f_inp,
                         IX + 900, -1100)
    i_subdiv = add_node(ng, "GeometryNodeSubdivideMesh", label="Tessellate Input",
                        location=(IX + 1250, -1100), parent=f_inp)
    link(i_store, "Geometry", i_subdiv, "Mesh")
    link(gi, "Cell Subdivision", i_subdiv, "Level")
    i_warp = add_node(ng, "GeometryNodeSetPosition", label="Warp by Field",
                      location=(IX + 1500, -1100), parent=f_inp)
    link(i_subdiv, "Mesh", i_warp, "Geometry")
    link(nb1["offset"], "Vector", i_warp, "Offset")

    # ------------------------------------------------------------------------
    # Frame: MODE SWITCH (master menu -> Index Switch, extensible)
    # ------------------------------------------------------------------------
    f_mode = frame(ng, label="Mode Switch")
    MX = 5600
    menu = add_node(ng, "GeometryNodeMenuSwitch", label="Cell Type",
                    location=(MX, 400), parent=f_mode)
    menu.data_type = "INT"
    set_menu_items(menu, ["Perlin Grid", "Voronoi", "Input Mesh",
                          "Triangles", "Pentagons", "Octagons"])
    for i, nm in enumerate(["Perlin Grid", "Voronoi", "Input Mesh",
                            "Triangles", "Pentagons", "Octagons"]):
        menu.inputs[nm].default_value = i
    link(gi, "Cell Type", menu, "Menu")
    menu_sock.default_value = "Voronoi"  # AFTER wiring, once the enum exists

    isw = add_node(ng, "GeometryNodeIndexSwitch", label="Pick Cell Mesh",
                   location=(MX + 300, 150), parent=f_mode)
    isw.data_type = "GEOMETRY"
    while len(isw.index_switch_items) < 6:
        isw.index_switch_items.new()
    link(menu, "Output", isw, "Index")
    link(q_warp, "Geometry", isw, "Item_0")
    link(v_subdiv, "Mesh", isw, "Item_1")
    link(i_warp, "Geometry", isw, "Item_2")
    link(t3_warp, "Geometry", isw, "Item_3")
    link(p5_subdiv, "Mesh", isw, "Item_4")
    link(o8_subdiv, "Mesh", isw, "Item_5")

    # ------------------------------------------------------------------------
    # Frame: NOISE PASSES (Repeat Zone; pass k: subdivide + finer field)
    # ------------------------------------------------------------------------
    f_pass = frame(ng, label="Noise Passes (Repeat Zone)")
    PX = 6400
    rout = add_node(ng, "GeometryNodeRepeatOutput", label="Passes End",
                    location=(PX + 5600, 100), parent=f_pass)
    rin = add_node(ng, "GeometryNodeRepeatInput", label="Passes Start",
                   location=(PX, 100), parent=f_pass)
    rin.pair_with_output(rout)
    # ensure exactly one Geometry state item
    items = rout.repeat_items
    while len(items) > 1:
        items.remove(items[-1])
    if len(items) == 0:
        items.new("GEOMETRY", "Geometry")
    elif items[0].socket_type != "GEOMETRY":
        items.remove(items[0])
        items.new("GEOMETRY", "Geometry")

    iters = math("SUBTRACT", "Passes - 1", (PX - 300, 250), f_pass, c1=1)
    link(gi, "Passes", iters, "Value")
    link(iters, "Value", rin, "Iterations")
    link(isw, "Output", rin, "Geometry")

    # pass index k = Iteration + 1 (1-based extra pass)
    k = math("ADD", "pass k", (PX + 300, 500), f_pass, c1=1)
    link(rin, "Iteration", k, "Value")
    mult = math("POWER", "2^k", (PX + 500, 500), f_pass, c0=2)
    link(k, "Value", mult, "Value_001")
    nk_x = math("MULTIPLY", "Nx * 2^k", (PX + 700, 550), f_pass)
    link(gi, "Cells X", nk_x, "Value")
    link(mult, "Value", nk_x, "Value_001")
    nk_y = math("MULTIPLY", "Ny * 2^k", (PX + 700, 450), f_pass)
    link(gi, "Cells Y", nk_y, "Value")
    link(mult, "Value", nk_y, "Value_001")
    cellk_w = math("DIVIDE", "cell W / 2^k", (PX + 900, 550), f_pass)
    link(cellW, "Value", cellk_w, "Value")
    link(mult, "Value", cellk_w, "Value_001")
    cellk_h = math("DIVIDE", "cell H / 2^k", (PX + 900, 450), f_pass)
    link(cellH, "Value", cellk_h, "Value")
    link(mult, "Value", cellk_h, "Value_001")
    falloff_k = math("POWER", "Falloff^k", (PX + 700, 350), f_pass)
    link(gi, "Pass Falloff", falloff_k, "Value")
    link(k, "Value", falloff_k, "Value_001")
    seed_k = math("MULTIPLY_ADD", "pass seed", (PX + 700, 250), f_pass, c1=7691)
    link(k, "Value", seed_k, "Value")
    link(gi, "Seed", seed_k, "Value_002")
    strength_k = math("MULTIPLY", "strength * falloff^k", (PX + 900, 350), f_pass)
    link(gi, "Distortion", strength_k, "Value")
    link(falloff_k, "Value", strength_k, "Value_001")

    # subdivide the current cells -> sub-cell candidates
    p_subdiv = add_node(ng, "GeometryNodeSubdivideMesh", label="Tessellate Pass",
                        location=(PX + 300, 100), parent=f_pass)
    link(rin, "Geometry", p_subdiv, "Mesh")
    p_subdiv.inputs["Level"].default_value = 1

    # per-PARENT-cell probability gate (parent id survived the subdivide)
    parent_id = add_node(ng, "GeometryNodeInputNamedAttribute",
                         label="parent cell id", location=(PX + 1400, 700),
                         parent=f_pass)
    parent_id.data_type = "INT"
    link(gi, "Cell ID Attribute", parent_id, "Name")
    gate_seed = math("ADD", "gate seed", (PX + 1400, 550), f_pass, c1=4409)
    link(seed_k, "Value", gate_seed, "Value")
    gate_h = add_node(ng, "FunctionNodeHashValue", label="gate hash",
                      location=(PX + 1600, 650), parent=f_pass)
    gate_h.data_type = "INT"
    link(parent_id, "Attribute", gate_h, "Value")
    link(gate_seed, "Value", gate_h, "Seed")
    gate_m = math("FLOORED_MODULO", "gate mod", (PX + 1800, 650), f_pass, c1=46337)
    link(gate_h, "Hash", gate_m, "Value")
    gate_d = math("DIVIDE", "gate 0..1", (PX + 2000, 650), f_pass, c1=46337.0)
    link(gate_m, "Value", gate_d, "Value")
    gate = add_node(ng, "FunctionNodeCompare", label="gate < probability",
                    location=(PX + 2200, 650), parent=f_pass)
    gate.data_type = "FLOAT"
    gate.operation = "LESS_THAN"
    link(gate_d, "Value", gate, "A")
    link(gi, "Pass Probability", gate, "B")
    # face->point mean of the gate = smooth deform multiplier at cell borders
    gate_face = add_node(ng, "GeometryNodeFieldOnDomain", label="gate on faces",
                         location=(PX + 2400, 650), parent=f_pass)
    gate_face.data_type = "FLOAT"
    gate_face.domain = "FACE"
    link(gate, "Result", gate_face, "Value")

    nbk = noise_block("Pk", f_pass, PX + 1400, nk_x, nk_y, seed_k, strength_k,
                      cellk_w, cellk_h)
    gated_offset = add_node(ng, "ShaderNodeVectorMath", label="offset * gate",
                            location=(PX + 5000, 300), parent=f_pass)
    gated_offset.operation = "SCALE"
    link(nbk["offset"], "Vector", gated_offset, "Vector")
    link(gate_face, "Value", gated_offset, "Scale")
    p_warp = add_node(ng, "GeometryNodeSetPosition", label="Warp Sub-Cells",
                      location=(PX + 5200, 100), parent=f_pass)
    link(p_subdiv, "Mesh", p_warp, "Geometry")
    link(gated_offset, "Vector", p_warp, "Offset")

    # refreshed sub-cell attributes, only where the gate passed
    pk_cid = cell_id_chain(nbk["cx"], nbk["cy"], nk_x, nk_y, "Pk", f_pass,
                           PX + 4600, 700)
    pk_rnd = cell_random_chain(pk_cid, seed_k, "Pk", f_pass, PX + 5050, 700)
    p_store = store_pair(p_warp, "Geometry", "FACE", pk_cid, pk_rnd, "Pk", f_pass,
                         PX + 5450, 600, selection=gate)
    link(p_store, "Geometry", rout, "Geometry")

    # ------------------------------------------------------------------------
    # Frame: CELL DEBUG COLOR (random RGB per cell, corner color attribute)
    # ------------------------------------------------------------------------
    f_color = frame(ng, label="Cell Debug Color")
    CX = PX + 6200
    color_id = add_node(ng, "GeometryNodeInputNamedAttribute",
                        label="cell id (color)", location=(CX, 700), parent=f_color)
    color_id.data_type = "INT"
    link(gi, "Cell ID Attribute", color_id, "Name")

    def color_chan(off, label, y):
        seed = math("ADD", f"col {label} seed", (CX + 200, y - 60), f_color, c1=off)
        link(gi, "Seed", seed, "Value")
        h = add_node(ng, "FunctionNodeHashValue", label=f"col {label} hash",
                     location=(CX + 380, y), parent=f_color)
        h.data_type = "INT"
        link(color_id, "Attribute", h, "Value")
        link(seed, "Value", h, "Seed")
        hm = math("FLOORED_MODULO", f"col {label} mod", (CX + 560, y), f_color, c1=46337)
        link(h, "Hash", hm, "Value")
        hd = math("DIVIDE", f"col {label} 0..1", (CX + 740, y), f_color, c1=46337.0)
        link(hm, "Value", hd, "Value")
        return hd

    col_r = color_chan(911, "R", 700)
    col_g = color_chan(922, "G", 560)
    col_b = color_chan(933, "B", 420)
    combine_col = add_node(ng, "FunctionNodeCombineColor", label="Cell Color",
                           location=(CX + 940, 560), parent=f_color)
    link(col_r, "Value", combine_col, "Red")
    link(col_g, "Value", combine_col, "Green")
    link(col_b, "Value", combine_col, "Blue")
    combine_col.inputs["Alpha"].default_value = 1.0
    store_col = add_node(ng, "GeometryNodeStoreNamedAttribute",
                         label="store cell_color", location=(CX + 1140, 300),
                         parent=f_color)
    store_col.data_type = "FLOAT_COLOR"
    store_col.domain = "CORNER"
    link(rout, "Geometry", store_col, "Geometry")
    link(gi, "Cell Color Attribute", store_col, "Name")
    link(combine_col, "Color", store_col, "Value")

    # ------------------------------------------------------------------------
    # Frame: CELL ISOLATION (split walls + shrink islands toward their center,
    # optionally pinning the tile's outer-boundary verts for tile continuity)
    # ------------------------------------------------------------------------
    f_iso = frame(ng, label="Cell Isolation")
    SX = CX + 1500
    final_id = add_node(ng, "GeometryNodeInputNamedAttribute",
                        label="final cell id", location=(SX, 400), parent=f_iso)
    final_id.data_type = "INT"
    link(gi, "Cell ID Attribute", final_id, "Name")
    fgb = add_node(ng, "GeometryNodeMeshFaceSetBoundaries", label="Cell Walls",
                   location=(SX + 250, 400), parent=f_iso)
    link(final_id, "Attribute", fgb, "Face Set")

    # tile-border verts, detected TOPOLOGICALLY on the POINT domain (boundary
    # vert: adjacent faces < adjacent edges) and captured BEFORE the split —
    # afterwards every cell wall is a boundary too. NB: an edge-domain field
    # captured on POINT reads 0 (no edge->point interpolation) — bit us.
    vert_nb = add_node(ng, "GeometryNodeInputMeshVertexNeighbors",
                       label="Vertex Neighbors", location=(SX, 700), parent=f_iso)
    is_border_v = add_node(ng, "FunctionNodeCompare", label="border vert?",
                           location=(SX + 200, 700), parent=f_iso)
    is_border_v.data_type = "INT"
    is_border_v.operation = "LESS_THAN"
    link(vert_nb, "Face Count", is_border_v, "A")
    link(vert_nb, "Vertex Count", is_border_v, "B")
    cap_border = add_node(ng, "GeometryNodeCaptureAttribute", label="capture border",
                          location=(SX + 450, 550), parent=f_iso)
    cap_border.domain = "POINT"
    cap_border.capture_items.new("FLOAT", "Border")
    link(store_col, "Geometry", cap_border, "Geometry")
    link(is_border_v, "Result", cap_border, "Border")

    split = add_node(ng, "GeometryNodeSplitEdges", label="Split Cell Walls",
                     location=(SX + 700, 200), parent=f_iso)
    link(cap_border, "Geometry", split, "Mesh")
    link(fgb, "Boundary Edges", split, "Selection")

    # per-island (= per split cell) centroid via Accumulate Field
    island = add_node(ng, "GeometryNodeInputMeshIsland", label="Cell Island",
                      location=(SX + 700, 700), parent=f_iso)
    iso_pos = add_node(ng, "GeometryNodeInputPosition", label="Position",
                       location=(SX + 700, 550), parent=f_iso)
    acc_p = add_node(ng, "GeometryNodeAccumulateField", label="sum positions",
                     location=(SX + 950, 700), parent=f_iso)
    acc_p.data_type = "FLOAT_VECTOR"
    acc_p.domain = "POINT"
    link(iso_pos, "Position", acc_p, "Value")
    link(island, "Island Index", acc_p, "Group Index")
    acc_n = add_node(ng, "GeometryNodeAccumulateField", label="count verts",
                     location=(SX + 950, 500), parent=f_iso)
    acc_n.data_type = "FLOAT"
    acc_n.domain = "POINT"
    _resolve_socket(acc_n, "Value", "inputs").default_value = 1.0
    link(island, "Island Index", acc_n, "Group Index")
    inv_n = math("DIVIDE", "1 / count", (SX + 1200, 500), f_iso, c0=1.0)
    link(acc_n, "Total", inv_n, "Value_001")
    centroid = add_node(ng, "ShaderNodeVectorMath", label="island centroid",
                        location=(SX + 1400, 650), parent=f_iso)
    centroid.operation = "SCALE"
    link(acc_p, "Total", centroid, "Vector")
    link(inv_n, "Value", centroid, "Scale")
    to_center = add_node(ng, "ShaderNodeVectorMath", label="to centroid",
                         location=(SX + 1600, 650), parent=f_iso)
    to_center.operation = "SUBTRACT"
    link(centroid, "Vector", to_center, "Vector")
    link(iso_pos, "Position", to_center, "Vector_001")

    # full shrink toward the island centroid (interior verts / preserve OFF)
    base_off = add_node(ng, "ShaderNodeVectorMath", label="shrink offset",
                        location=(SX + 1800, 550), parent=f_iso)
    base_off.operation = "SCALE"
    link(to_center, "Vector", base_off, "Vector")
    link(gi, "Cell Gap", base_off, "Scale")

    # --- Preserve Tile Border: border verts SLIDE ALONG the border axis -----
    # Fully pinning them pinches wall gaps closed at the seam; per-centroid
    # sliding breaks vertex mating across tiles. So: slide by a CONSTANT
    # magnitude (Gap * 0.25 * min cell) with only the SIGN taken from the cell
    # centroid — both tiles compute the identical slide, wall gaps stay open
    # at the border, and opposite-edge verts still weld. Corners stay pinned.
    pin = add_node(ng, "FunctionNodeCompare", label="pinned?",
                   location=(SX + 1200, 350), parent=f_iso)
    pin.data_type = "FLOAT"
    pin.operation = "GREATER_THAN"
    link(cap_border, "Border", pin, "A")
    _resolve_socket(pin, "B", "inputs").default_value = 0.0
    sepB = add_node(ng, "ShaderNodeSeparateXYZ", label="border pos",
                    location=(SX + 1200, 120), parent=f_iso)
    link(iso_pos, "Position", sepB, "Vector")
    w2 = math("MULTIPLY", "W/2", (SX + 1200, -50), f_iso, c1=0.5)
    link(W, "Value", w2, "Value")
    h2 = math("MULTIPLY", "H/2", (SX + 1200, -130), f_iso, c1=0.5)
    link(H, "Value", h2, "Value")

    def edge_dist(comp, half_node, label, y):
        d1 = math("SUBTRACT", f"{label} - e", (SX + 1400, y), f_iso)
        link(sepB, comp, d1, "Value")
        link(half_node, "Value", d1, "Value_001")
        a1 = math("ABSOLUTE", f"|{label} - e|", (SX + 1580, y), f_iso)
        link(d1, "Value", a1, "Value")
        d2 = math("ADD", f"{label} + e", (SX + 1400, y - 80), f_iso)
        link(sepB, comp, d2, "Value")
        link(half_node, "Value", d2, "Value_001")
        a2 = math("ABSOLUTE", f"|{label} + e|", (SX + 1580, y - 80), f_iso)
        link(d2, "Value", a2, "Value")
        m = math("MINIMUM", f"dist {label} border", (SX + 1760, y - 40), f_iso)
        link(a1, "Value", m, "Value")
        link(a2, "Value", m, "Value_001")
        return m

    dvx = edge_dist("X", w2, "x", 120)
    dvy = edge_dist("Y", h2, "y", -60)
    axis_vert = add_node(ng, "FunctionNodeCompare", label="on L/R border?",
                         location=(SX + 1960, 40), parent=f_iso)
    axis_vert.data_type = "FLOAT"
    axis_vert.operation = "LESS_THAN"
    link(dvx, "Value", axis_vert, "A")
    link(dvy, "Value", axis_vert, "B")

    cth_x = math("MULTIPLY", "0.45 cell W", (SX + 1760, -220), f_iso, c1=0.45)
    link(cellW, "Value", cth_x, "Value")
    cth_y = math("MULTIPLY", "0.45 cell H", (SX + 1760, -300), f_iso, c1=0.45)
    link(cellH, "Value", cth_y, "Value")
    near_x = add_node(ng, "FunctionNodeCompare", label="near L/R?",
                      location=(SX + 1960, -220), parent=f_iso)
    near_x.data_type = "FLOAT"
    near_x.operation = "LESS_THAN"
    link(dvx, "Value", near_x, "A")
    link(cth_x, "Value", near_x, "B")
    near_y = add_node(ng, "FunctionNodeCompare", label="near T/B?",
                      location=(SX + 1960, -300), parent=f_iso)
    near_y.data_type = "FLOAT"
    near_y.operation = "LESS_THAN"
    link(dvy, "Value", near_y, "A")
    link(cth_y, "Value", near_y, "B")
    corner = add_node(ng, "FunctionNodeBooleanMath", label="tile corner?",
                      location=(SX + 2140, -260), parent=f_iso)
    corner.operation = "AND"
    link(near_x, "Result", corner, "Boolean")
    link(near_y, "Result", corner, "Boolean_001")
    not_corner = add_node(ng, "FunctionNodeBooleanMath", label="not corner",
                          location=(SX + 2320, -260), parent=f_iso)
    not_corner.operation = "NOT"
    link(corner, "Boolean", not_corner, "Boolean")

    # tangential centroid of the UNITED cell, accumulated by CELL_ID: both
    # halves of a border-straddling cell live in ONE tile (same wrapped id at
    # opposite edges), so the mean is identical on every tile — the halves
    # slide in lockstep and opposite-tile vert copies keep mating exactly.
    # (Per-island centroids disagree between halves — sign flips mid-cell
    # produced sliver cracks along the seams.)
    pid = add_node(ng, "GeometryNodeInputNamedAttribute", label="cell id (pin)",
                   location=(SX + 1960, 620), parent=f_iso)
    pid.data_type = "INT"
    link(gi, "Cell ID Attribute", pid, "Name")

    def acc_by_cell(value_src, label, y):
        a = add_node(ng, "GeometryNodeAccumulateField", label=label,
                     location=(SX + 2320, y), parent=f_iso)
        a.data_type = "FLOAT"
        a.domain = "POINT"
        if value_src is not None:
            link(float_out(value_src), "", a, "Value")
        else:
            _resolve_socket(a, "Value", "inputs").default_value = 1.0
        link(pid, "Attribute", a, "Group Index")
        return a

    x2 = math("MULTIPLY", "x^2", (SX + 2140, 900), f_iso)
    link(sepB, "X", x2, "Value")
    link(sepB, "X", x2, "Value_001")
    y2 = math("MULTIPLY", "y^2", (SX + 2140, 820), f_iso)
    link(sepB, "Y", y2, "Value")
    link(sepB, "Y", y2, "Value_001")
    acc_cnt = acc_by_cell(None, "cell count", 620)
    acc_x = acc_by_cell(sepB.outputs["X"], "sum x", 900)
    acc_y = acc_by_cell(sepB.outputs["Y"], "sum y", 760)
    acc_x2 = acc_by_cell(x2, "sum x^2", 480)
    acc_y2 = acc_by_cell(y2, "sum y^2", 340)
    inv_cnt = math("DIVIDE", "1/cell count", (SX + 2560, 620), f_iso, c0=1.0)
    link(acc_cnt, "Total", inv_cnt, "Value_001")

    def mean_of(acc, label, y):
        m = math("MULTIPLY", label, (SX + 2740, y), f_iso)
        link(acc, "Total", m, "Value")
        link(inv_cnt, "Value", m, "Value_001")
        return m

    mean_x = mean_of(acc_x, "mean x", 900)
    mean_y = mean_of(acc_y, "mean y", 760)
    mean_x2 = mean_of(acc_x2, "mean x^2", 480)
    mean_y2 = mean_of(acc_y2, "mean y^2", 340)

    def var_of(mean_sq, mean, label, y):
        msq = math("MULTIPLY", label + " m^2", (SX + 2920, y), f_iso)
        link(mean, "Value", msq, "Value")
        link(mean, "Value", msq, "Value_001")
        v = math("SUBTRACT", label, (SX + 3100, y), f_iso)
        link(mean_sq, "Value", v, "Value")
        link(msq, "Value", v, "Value_001")
        return v

    var_x = var_of(mean_x2, mean_x, "var x", 480)
    var_y = var_of(mean_y2, mean_y, "var y", 340)

    # --- corner-straddling cells: shrink toward the JUNCTION-ASSEMBLED cell -
    # Their 4 quadrant pieces sit at the 4 tile corners, so plain means are
    # nonsense. Taking positions relative to each vert's NEAREST tile corner
    # (q = p - sign(p)*halfbounds) makes the pieces congruent: the mean of q by
    # cell_id IS the assembled cell's centroid relative to the junction — the
    # same value in every tile, so all four pieces shrink in lockstep and a
    # proper gap forms around the corner junction.
    sgn_x = math("SIGN", "sign x", (SX + 2140, 1120), f_iso)
    link(sepB, "X", sgn_x, "Value")
    sgn_y = math("SIGN", "sign y", (SX + 2140, 1040), f_iso)
    link(sepB, "Y", sgn_y, "Value")
    qx_off = math("MULTIPLY", "sgn * W/2", (SX + 2320, 1120), f_iso)
    link(sgn_x, "Value", qx_off, "Value")
    link(w2, "Value", qx_off, "Value_001")
    qx = math("SUBTRACT", "q.x", (SX + 2500, 1120), f_iso)
    link(sepB, "X", qx, "Value")
    link(qx_off, "Value", qx, "Value_001")
    qy_off = math("MULTIPLY", "sgn * H/2", (SX + 2320, 1040), f_iso)
    link(sgn_y, "Value", qy_off, "Value")
    link(h2, "Value", qy_off, "Value_001")
    qy = math("SUBTRACT", "q.y", (SX + 2500, 1040), f_iso)
    link(sepB, "Y", qy, "Value")
    link(qy_off, "Value", qy, "Value_001")
    acc_qx = acc_by_cell(qx, "sum q.x", 1200)
    acc_qy = acc_by_cell(qy, "sum q.y", 1060)
    mean_qx = mean_of(acc_qx, "mean q.x", 1200)
    mean_qy = mean_of(acc_qy, "mean q.y", 1060)
    coffx0 = math("SUBTRACT", "q centroid - q.x", (SX + 2920, 1200), f_iso)
    link(mean_qx, "Value", coffx0, "Value")
    link(qx, "Value", coffx0, "Value_001")
    coffx = math("MULTIPLY", "corner off x", (SX + 3100, 1200), f_iso)
    link(coffx0, "Value", coffx, "Value")
    link(gi, "Cell Gap", coffx, "Value_001")
    coffy0 = math("SUBTRACT", "q centroid - q.y", (SX + 2920, 1060), f_iso)
    link(mean_qy, "Value", coffy0, "Value")
    link(qy, "Value", coffy0, "Value_001")
    coffy = math("MULTIPLY", "corner off y", (SX + 3100, 1060), f_iso)
    link(coffy0, "Value", coffy, "Value")
    link(gi, "Cell Gap", coffy, "Value_001")
    corner_off = add_node(ng, "ShaderNodeCombineXYZ", label="corner cell offset",
                          location=(SX + 3280, 1130), parent=f_iso)
    link(coffx, "Value", corner_off, "X")
    link(coffy, "Value", corner_off, "Y")

    def axis_pick(a_false, a_true, label, x, y):
        sw = add_node(ng, "GeometryNodeSwitch", label=label, location=(x, y),
                      parent=f_iso)
        sw.input_type = "FLOAT"
        link(float_out(a_false), "", sw, "False")
        link(float_out(a_true), "", sw, "True")
        link(axis_vert, "Result", sw, "Switch")
        return sw

    t_mean = axis_pick(mean_x, mean_y, "tangent mean", SX + 3280, 760)
    p_t = axis_pick(sepB.outputs["X"], sepB.outputs["Y"], "tangent pos", SX + 3280, 620)
    var_t = axis_pick(var_x, var_y, "tangent var", SX + 3280, 480)

    # corner-straddling cells (4 pieces share one id) have a nonsense mean —
    # their tangential variance is huge (pieces cluster at both tile ends)
    cell_min_b = math("MINIMUM", "min cell", (SX + 3280, 340), f_iso)
    link(cellW, "Value", cell_min_b, "Value")
    link(cellH, "Value", cell_min_b, "Value_001")
    var_th0 = math("MULTIPLY", "1.5 min cell", (SX + 3460, 340), f_iso, c1=1.5)
    link(cell_min_b, "Value", var_th0, "Value")
    var_th = math("MULTIPLY", "var threshold", (SX + 3640, 340), f_iso)
    link(var_th0, "Value", var_th, "Value")
    link(var_th0, "Value", var_th, "Value_001")
    sane_mean = add_node(ng, "FunctionNodeCompare", label="mean usable?",
                         location=(SX + 3820, 400), parent=f_iso)
    sane_mean.data_type = "FLOAT"
    sane_mean.operation = "LESS_THAN"
    link(var_t, "Output", sane_mean, "A")
    link(var_th, "Value", sane_mean, "B")
    # a corner-straddling cell has HUGE variance on BOTH axes (its pieces
    # cluster at all four tile corners)
    big_var_x = add_node(ng, "FunctionNodeCompare", label="var x big?",
                         location=(SX + 3820, 250), parent=f_iso)
    big_var_x.data_type = "FLOAT"
    big_var_x.operation = "GREATER_THAN"
    link(var_x, "Value", big_var_x, "A")
    link(var_th, "Value", big_var_x, "B")
    big_var_y = add_node(ng, "FunctionNodeCompare", label="var y big?",
                         location=(SX + 3820, 150), parent=f_iso)
    big_var_y.data_type = "FLOAT"
    big_var_y.operation = "GREATER_THAN"
    link(var_y, "Value", big_var_y, "A")
    link(var_th, "Value", big_var_y, "B")
    is_corner_cell = add_node(ng, "FunctionNodeBooleanMath", label="corner cell?",
                              location=(SX + 4000, 200), parent=f_iso)
    is_corner_cell.operation = "AND"
    link(big_var_x, "Result", is_corner_cell, "Boolean")
    link(big_var_y, "Result", is_corner_cell, "Boolean_001")

    slide_raw = math("SUBTRACT", "t centroid - t", (SX + 3460, 700), f_iso)
    link(t_mean, "Output", slide_raw, "Value")
    link(p_t, "Output", slide_raw, "Value_001")
    slide_g = math("MULTIPLY", "* Gap", (SX + 3640, 700), f_iso)
    link(slide_raw, "Value", slide_g, "Value")
    link(gi, "Cell Gap", slide_g, "Value_001")
    slide_c = math("MULTIPLY", "no corners", (SX + 3820, 700), f_iso)
    link(slide_g, "Value", slide_c, "Value")
    link(not_corner, "Boolean", slide_c, "Value_001")
    slide = math("MULTIPLY", "slide amount", (SX + 4000, 700), f_iso)
    link(slide_c, "Value", slide, "Value")
    link(sane_mean, "Result", slide, "Value_001")
    slide_x = add_node(ng, "ShaderNodeCombineXYZ", label="slide along X",
                       location=(SX + 2860, 380), parent=f_iso)
    link(slide, "Value", slide_x, "X")
    slide_y = add_node(ng, "ShaderNodeCombineXYZ", label="slide along Y",
                       location=(SX + 2860, 260), parent=f_iso)
    link(slide, "Value", slide_y, "Y")
    border_off = add_node(ng, "GeometryNodeSwitch", label="border slide",
                          location=(SX + 3040, 320), parent=f_iso)
    border_off.input_type = "VECTOR"
    link(slide_x, "Vector", border_off, "False")
    link(slide_y, "Vector", border_off, "True")
    link(axis_vert, "Result", border_off, "Switch")

    # per-vert offset: preserve OFF -> plain island shrink; preserve ON ->
    # corner cells shrink toward their junction-assembled centroid (ALL their
    # verts, for piece coherence), border verts of other cells slide
    # tangentially, everything else island-shrinks.
    sw_bord = add_node(ng, "GeometryNodeSwitch", label="border vert offset",
                       location=(SX + 3400, 500), parent=f_iso)
    sw_bord.input_type = "VECTOR"
    link(base_off, "Vector", sw_bord, "False")
    link(border_off, "Output", sw_bord, "True")
    link(pin, "Result", sw_bord, "Switch")
    sw_cell = add_node(ng, "GeometryNodeSwitch", label="corner cell offset?",
                       location=(SX + 3600, 500), parent=f_iso)
    sw_cell.input_type = "VECTOR"
    link(sw_bord, "Output", sw_cell, "False")
    link(corner_off, "Vector", sw_cell, "True")
    link(is_corner_cell, "Boolean", sw_cell, "Switch")
    final_off = add_node(ng, "GeometryNodeSwitch", label="pick offset",
                         location=(SX + 3800, 500), parent=f_iso)
    final_off.input_type = "VECTOR"
    link(base_off, "Vector", final_off, "False")
    link(sw_cell, "Output", final_off, "True")
    link(gi, "Preserve Tile Border", final_off, "Switch")

    shrink_sp = add_node(ng, "GeometryNodeSetPosition", label="Shrink Cells",
                         location=(SX + 3400, 200), parent=f_iso)
    link(split, "Mesh", shrink_sp, "Geometry")
    link(final_off, "Output", shrink_sp, "Offset")

    iso_sw = add_node(ng, "GeometryNodeSwitch", label="Isolate?",
                      location=(SX + 2250, 100), parent=f_iso)
    iso_sw.input_type = "GEOMETRY"
    link(store_col, "Geometry", iso_sw, "False")
    link(shrink_sp, "Geometry", iso_sw, "True")
    link(gi, "Isolate Cells", iso_sw, "Switch")

    # ------------------------------------------------------------------------
    # Frame: OUTPUT
    # ------------------------------------------------------------------------
    f_out = frame(ng, label="Output (place at input bounds)")
    xform = add_node(ng, "GeometryNodeTransform", label="Move to Bounds Center",
                     location=(SX + 1300, 100), parent=f_out)
    link(iso_sw, "Output", xform, "Geometry")
    link(center, "Vector", xform, "Translation")
    go.parent = f_out
    go.location = (SX + 1600, 100)
    link(xform, "Geometry", go, "Geometry")

    # Geometry tooltip
    for it in ng.interface.items_tree:
        if it.item_type == "SOCKET" and it.name == "Geometry" and not (it.description or "").strip():
            it.description = ("Input mesh. Perlin Grid / Voronoi modes only use its XY bounding "
                              "box (tile size + placement) and replace it; Input Mesh mode uses "
                              "the mesh itself as the base cells. Output repeats seamlessly every "
                              "bounding-box width/depth.")

    # --- Asset publishing ----------------------------------------------------
    ng.asset_mark()
    ng.asset_data.catalog_id = ST3E_CATALOG
    ng.asset_data.tags.new(ST3E_TAG)
    ng.is_modifier = True
    ng.is_tool = False
    ng.asset_data.description = (
        "Replace a mesh with a TILEABLE cell mesh whose topology follows a noise "
        "pattern (tile = the input's XY bounding box; instances one tile apart mate "
        "vertex-for-vertex). Cell types: noise-warped quad grid, Voronoi cell "
        "polygons (a mesh edge between every cell), or the input mesh's own faces. "
        "Multiple noise passes tessellate and deform nested sub-cells (per-parent-"
        "cell probability), and cells can be split apart with a gap. Per-cell INT "
        "id + FLOAT random face attributes for shading."
    )

    # --- Demo object: a 2x2m plane ------------------------------------------
    mesh = bpy.data.meshes.new("GN_Demo_Mesh")
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1.0)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new("GN_Demo", mesh)
    bpy.context.scene.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new(name="GN", type="NODES")
    mod.node_group = ng

    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=OUT_FILE)
    print(f"[OK] Wrote {OUT_FILE}")
    print(f"     group: {ng.name}")
    print(f"     node count: {len(ng.nodes)}")
    print(f"     link count: {len(ng.links)}")
    print(f"     frame count: {sum(1 for n in ng.nodes if n.bl_idname == 'NodeFrame')}")


if __name__ == "__main__":
    log_path = os.path.join(OUT_DIR, "_build", "build.log")
    ok = False
    try:
        build()
        ok = True
        with open(log_path, "w") as f:
            f.write("BUILD OK (GN_TileableMeshNoise v2)\n")
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
        os._exit(0 if ok else 1)
