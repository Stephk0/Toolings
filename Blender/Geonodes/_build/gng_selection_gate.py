"""GNG_SelectionGate -- the shared ST3E selection gate.

One field-only helper group that every ST3E modifier routes its Selection through,
so selection features are added in one place instead of per tool.

    Selection, Invert, Grow / Shrink,
    Use Material ID, Material ID, Material Mode  ->  Selection

Order of operations: combine with material -> invert -> grow / shrink.

v1:
  * Invert         Selection XOR Invert (off = exact passthrough).
  * Grow / Shrink  signed ring count. +N grows the selection N rings, -N shrinks it
                   N rings (shrink = grow the complement). 0 = exact passthrough.
                   Rings are counted in the domain the consumer evaluates the field
                   on (vertices via edges, faces via shared edges, curve points along
                   the curve) -- the neighbourhood Blur Attribute uses. Point clouds and
                   instances have no topology, so Grow / Shrink leaves them unchanged.
v2:
  * Material ID    faces whose material index equals Material ID, evaluated on the FACE
                   domain and spread to the consumer's domain (a vertex/edge counts when
                   ANY adjacent face matches, so deformers move whole material regions).
                   Combined with Selection by Material Mode:
                     Add                       Selection OR Material
                     Subtract                  Selection AND NOT Material
                     Intersect                 Selection AND Material
                     Material Minus Selection  Material AND NOT Selection
                   Use Material ID off = exact passthrough.

Grow is ONE Blur Attribute step + `> 0` per repeat iteration, so it is exact for any
ring count (a single N-iteration blur thresholded once underflows float32 past ~40
rings).

The group has no Geometry input on purpose: it is a pure field, evaluated wherever
its output is plugged in, exactly like the XOR node it replaces.

Usage (inside a headless Blender script):
    sys.path.append(r"...\\Blender\\Geonodes\\_build")
    import gng_selection_gate as gate
    ng = gate.ensure()          # builds or upgrades the group in the current file
"""
import bpy

NAME = "GNG_SelectionGate"
VERSION = 3   # v3: Material Mode item identifiers start at 0 (backfilled 0 = Add)
VERSION_KEY = "st3e_version"

SEL, INV, GROW = "Selection", "Invert", "Grow / Shrink"
USE_MAT, MAT_ID, MAT_MODE = "Use Material ID", "Material ID", "Material Mode"
MODES = ("Add", "Subtract", "Intersect", "Material Minus Selection")
MODE_DESC = {
    "Add": "Selection plus every face with the Material ID",
    "Subtract": "Selection minus the faces with the Material ID",
    "Intersect": "Only the part of the Selection that has the Material ID",
    "Material Minus Selection": "Faces with the Material ID, minus the Selection",
}

DESC = {
    SEL: "Selection to pass through the gate",
    INV: "Use the complement of the (material-combined) selection",
    GROW: ("Grow the selection by this many rings of neighbours; negative values "
           "shrink it. 0 leaves it unchanged"),
    USE_MAT: "Combine the Selection with the faces that use Material ID",
    MAT_ID: "Material slot index (0 = first slot) whose faces take part",
    MAT_MODE: "How the Material ID faces combine with the Selection",
}
GROUP_DESC = ("ST3E selection gate: Selection combined with a Material ID (Add / Subtract / "
              "Intersect / Material Minus Selection), then inverted, then grown (+) or "
              "shrunk (-) by whole rings in the evaluating domain. Shared by every ST3E "
              "modifier")


def _socket(iface, name, in_out, stype):
    for it in iface.items_tree:
        if it.item_type == 'SOCKET' and it.in_out == in_out and it.name == name:
            return it
    return iface.new_socket(name, in_out=in_out, socket_type=stype)


def _single(it):
    # Per-group settings, not per-element values: plain number boxes on the modifier.
    if hasattr(it, "structure_type"):
        it.structure_type = 'SINGLE'


def _interface(ng):
    iface = ng.interface
    # On upgrade, sockets are matched by name and new ones are appended, so the
    # identifiers of existing ones never move.
    o = _socket(iface, SEL, 'OUTPUT', 'NodeSocketBool')
    o.description = "The gated selection"
    s = _socket(iface, SEL, 'INPUT', 'NodeSocketBool')
    s.default_value = True
    i = _socket(iface, INV, 'INPUT', 'NodeSocketBool')
    i.default_value = False
    g = _socket(iface, GROW, 'INPUT', 'NodeSocketInt')
    g.default_value = 0
    g.min_value, g.max_value = -10000, 10000
    _single(g)
    u = _socket(iface, USE_MAT, 'INPUT', 'NodeSocketBool')
    u.default_value = False
    _single(u)
    m = _socket(iface, MAT_ID, 'INPUT', 'NodeSocketInt')
    m.default_value = 0
    m.min_value, m.max_value = 0, 32767
    _single(m)
    _socket(iface, MAT_MODE, 'INPUT', 'NodeSocketMenu')
    for it in (s, i, g, u, m, _socket(iface, MAT_MODE, 'INPUT', 'NodeSocketMenu')):
        it.description = DESC[it.name]


def _frame(nodes, label):
    f = nodes.new("NodeFrame")
    f.label = label
    f.label_size = 16
    f.location = (0, 0)   # child .location stays absolute
    return f


def _build_nodes(ng):
    nodes, links = ng.nodes, ng.links
    nodes.clear()

    # ---- frames, created in signal order (one frame = one layout band) ----------
    f_mat = _frame(nodes, "Material ID  (faces with the index, spread to their corners)")
    f_comb = _frame(nodes, "Combine with Material  (Add / Subtract / Intersect / Material Minus Selection)")
    f_inv = _frame(nodes, "Invert  (combined XOR Invert)")
    f_mode = _frame(nodes, "Grow or Shrink  (sign = mode, |value| = rings)")
    f_in = _frame(nodes, "Flip for Shrink  (shrink = grow the complement)")
    f_rin = _frame(nodes, "Ring Loop In")
    f_body = _frame(nodes, "Grow One Ring  (blur 1 step, any neighbour selected)")
    f_rout = _frame(nodes, "Ring Loop Out")
    f_out = _frame(nodes, "Flip Back")

    def node(kind, frame, x, y, label=None, name=None):
        n = nodes.new(kind)
        n.parent = frame
        n.location = (x, y)
        if label:
            n.label = label
        if name:
            n.name = name
        return n

    def bmath(op, frame, x, y, label):
        n = node("FunctionNodeBooleanMath", frame, x, y, label=label, name=label)
        n.operation = op
        return n

    # ---- Selection in (GI bus, exempt from framing) ------------------------------
    gi_sel = node("NodeGroupInput", None, -2000, 340, label="In: Selection")

    # ---- Material ID --------------------------------------------------------------
    gi_mat = node("NodeGroupInput", f_mat, -2000, -380, label="In: Material ID")
    mat_idx = node("GeometryNodeInputMaterialIndex", f_mat, -2000, -560)
    is_mat = node("FunctionNodeCompare", f_mat, -1760, -420,
                  label="Material Index == ID", name="Is Material")
    is_mat.data_type, is_mat.operation = 'INT', 'EQUAL'
    on_face = node("GeometryNodeFieldOnDomain", f_mat, -1540, -420,
                   label="On Faces", name="Material On Faces")
    on_face.domain, on_face.data_type = 'FACE', 'BOOLEAN'

    # ---- Combine ------------------------------------------------------------------
    b_add = bmath('OR', f_comb, -1300, 340, "Add")
    b_sub = bmath('NIMPLY', f_comb, -1300, 140, "Subtract")
    b_int = bmath('AND', f_comb, -1300, -60, "Intersect")
    b_msub = bmath('NIMPLY', f_comb, -1300, -260, "Material Minus Selection")
    mode = node("GeometryNodeMenuSwitch", f_comb, -1080, 140, label="Material Mode",
                name="Material Mode")
    mode.data_type = 'BOOLEAN'
    # A modifier stores a menu override as the item's IDENTIFIER, and a new input on an
    # existing modifier is backfilled with 0. Rename the two default items (identifiers
    # 0 and 1) instead of clearing them, so 0 = Add; clearing would start at 2.
    items = mode.enum_items
    while len(items) > 2:
        items.remove(items[-1])
    for k, name in enumerate(MODES):
        it = items[k] if k < len(items) else items.new(name)
        it.name = name
        it.description = MODE_DESC[name]
    use = node("GeometryNodeSwitch", f_comb, -860, 140, label="Use Material ID?",
               name="Use Material")
    use.input_type = 'BOOLEAN'

    # ---- Invert ---------------------------------------------------------------------
    gi_inv = node("NodeGroupInput", f_inv, -640, 340, label="In: Invert")
    xor_inv = node("FunctionNodeBooleanMath", f_inv, -420, 140,
                   label="Combined XOR Invert", name="Invert XOR")
    xor_inv.operation = 'XOR'

    # ---- Mode -------------------------------------------------------------------
    gi_grow = node("NodeGroupInput", f_mode, -640, -640, label="In: Grow / Shrink")
    is_shrink = node("FunctionNodeCompare", f_mode, -420, -580,
                     label="Shrinking?  (value < 0)", name="Is Shrink")
    is_shrink.data_type, is_shrink.operation = 'INT', 'LESS_THAN'
    is_shrink.inputs[3].default_value = 0          # B (int)
    rings = node("FunctionNodeIntegerMath", f_mode, -420, -780,
                 label="Rings  |value|", name="Ring Count")
    rings.operation = 'ABSOLUTE'

    # ---- Flip in ----------------------------------------------------------------
    flip_in = node("FunctionNodeBooleanMath", f_in, -180, 140,
                   label="Complement if Shrinking", name="Flip In")
    flip_in.operation = 'XOR'

    # ---- Repeat zone ------------------------------------------------------------
    r_in = node("GeometryNodeRepeatInput", f_rin, 60, 80, name="Ring Loop In")
    r_out = node("GeometryNodeRepeatOutput", f_rout, 740, 80, name="Ring Loop Out")
    r_in.pair_with_output(r_out)
    r_out.repeat_items.clear()
    r_out.repeat_items.new('BOOLEAN', "Selection")

    blur = node("GeometryNodeBlurAttribute", f_body, 280, 140, label="Blur 1 Ring",
                name="Blur 1 Ring")
    blur.data_type = 'FLOAT'
    blur.inputs["Iterations"].default_value = 1
    blur.inputs["Weight"].default_value = 1.0
    touched = node("FunctionNodeCompare", f_body, 500, 140,
                   label="Any Neighbour Selected  (> 0)", name="Touched")
    touched.data_type, touched.operation = 'FLOAT', 'GREATER_THAN'
    touched.inputs[1].default_value = 0.0          # B (float)

    # ---- Flip out ---------------------------------------------------------------
    flip_out = node("FunctionNodeBooleanMath", f_out, 980, 140,
                    label="Undo Complement", name="Flip Out")
    flip_out.operation = 'XOR'
    go = node("NodeGroupOutput", f_out, 1200, 140)

    # ---- links ------------------------------------------------------------------
    S = gi_sel.outputs[SEL]
    links.new(mat_idx.outputs[0], is_mat.inputs[2])           # A (int)
    links.new(gi_mat.outputs[MAT_ID], is_mat.inputs[3])        # B (int)
    links.new(is_mat.outputs[0], on_face.inputs[0])
    M = on_face.outputs[0]
    for b, (a0, a1) in ((b_add, (S, M)), (b_sub, (S, M)), (b_int, (S, M)), (b_msub, (M, S))):
        links.new(a0, b.inputs[0])
        links.new(a1, b.inputs[1])
    links.new(gi_mat.outputs[MAT_MODE], mode.inputs[0])
    for k, b in enumerate((b_add, b_sub, b_int, b_msub)):
        links.new(b.outputs[0], mode.inputs[k + 1])
    links.new(gi_mat.outputs[USE_MAT], use.inputs[0])          # Switch
    links.new(S, use.inputs[1])                                # False: plain Selection
    links.new(mode.outputs[0], use.inputs[2])                  # True: combined

    links.new(use.outputs[0], xor_inv.inputs[0])
    links.new(gi_inv.outputs[INV], xor_inv.inputs[1])
    links.new(gi_grow.outputs[GROW], is_shrink.inputs[2])      # A (int)
    links.new(gi_grow.outputs[GROW], rings.inputs[0])
    links.new(xor_inv.outputs[0], flip_in.inputs[0])
    links.new(is_shrink.outputs[0], flip_in.inputs[1])
    links.new(rings.outputs[0], r_in.inputs["Iterations"])
    links.new(flip_in.outputs[0], r_in.inputs["Selection"])
    links.new(r_in.outputs["Selection"], blur.inputs["Value"])
    links.new(blur.outputs["Value"], touched.inputs[0])        # A (float)
    links.new(touched.outputs[0], r_out.inputs["Selection"])
    links.new(r_out.outputs["Selection"], flip_out.inputs[0])
    links.new(is_shrink.outputs[0], flip_out.inputs[1])
    links.new(flip_out.outputs[0], go.inputs[SEL])

    for gi, keep in ((gi_sel, (SEL,)), (gi_inv, (INV,)), (gi_grow, (GROW,)),
                     (gi_mat, (USE_MAT, MAT_ID, MAT_MODE))):
        for o in gi.outputs:
            o.hide = o.name not in keep


def ensure(force=False):
    """Return the file's GNG_SelectionGate, building or upgrading it in place.

    Upgrading keeps the datablock (so every group node using it stays linked) and
    keeps socket identifiers (matched by name, new ones appended)."""
    ng = bpy.data.node_groups.get(NAME)
    if ng is not None and ng.library is None and not force \
            and ng.get(VERSION_KEY, 0) >= VERSION:
        return ng
    if ng is None or ng.library is not None:
        ng = bpy.data.node_groups.new(NAME, "GeometryNodeTree")
    _interface(ng)
    _build_nodes(ng)
    # A menu socket's default is the item NAME and only resolves once it is linked
    # to the Menu Switch -- set it after the nodes exist.
    _socket(ng.interface, MAT_MODE, 'INPUT', 'NodeSocketMenu').default_value = MODES[0]
    ng.description = GROUP_DESC
    if hasattr(ng, "color_tag"):
        ng.color_tag = 'INPUT'
    ng[VERSION_KEY] = VERSION
    return ng
