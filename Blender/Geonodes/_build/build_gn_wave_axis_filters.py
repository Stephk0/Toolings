"""GN_Wave -- add the two per-axis filters (Ripple Axes + Affect Axes).

Ripple Axes weights the PERPENDICULAR vector before its length becomes the wave
radius, so zeroing an axis turns the concentric ripple into a planar wave
travelling along the remaining axis.  Affect Axes weights the final offset
vector, so an axis can be locked out of the deformation entirely (matters for
Displace Along = Normal / Object, whose offset is not axis-aligned).

Both triples are guarded: all three at 0 is read as all-on.  That is what makes
the change backward compatible -- a new interface input backfills EXISTING
modifiers with type-zero, not with the socket default
(memory: feedback_gn_new_socket_backfills_zero).

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup D:\\...\\GN_Wave.blend --python build_gn_wave_axis_filters.py
"""
import bpy, sys, os

PATH = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\GN_Wave.blend"
NAME = "GN_Wave"

ng = bpy.data.node_groups[NAME]
iface = ng.interface
nodes, links = ng.nodes, ng.links


def out_of(node, ident):
    return next(s for s in node.outputs if s.identifier == ident)


def inp_of(node, ident):
    return next(s for s in node.inputs if s.identifier == ident)


# ----------------------------------------------------------------- geometry snapshot
def demo_objects():
    return [o for o in bpy.data.objects
            if any(m.type == 'NODES' and m.node_group == ng for m in o.modifiers)]


def snapshot():
    dg = bpy.context.evaluated_depsgraph_get()
    out = {}
    for o in demo_objects():
        ev = o.evaluated_get(dg).data
        out[o.name] = [tuple(round(c, 6) for c in v.co) for v in ev.vertices]
    return out


bpy.context.view_layer.update()
BEFORE = snapshot()
print("BUILD: snapshot " + str([(k, len(v)) for k, v in BEFORE.items()]), flush=True)

# ------------------------------------------------------------------------ interface
def add_float(name, desc):
    s = iface.new_socket(name=name, in_out='INPUT', socket_type='NodeSocketFloat')
    s.description = desc
    s.subtype = 'FACTOR'
    s.min_value = 0.0
    s.max_value = 1.0
    s.default_value = 1.0
    return s


RIPPLE_DESC = ("How strongly the {ax} axis contributes to the wave's travel distance. "
               "Zero one axis to turn the concentric ripple into a planar wave running "
               "along the other. All three at 0 is read as all-on.")
AFFECT_DESC = ("How much of the offset is allowed on the {ax} axis. Zero locks {ax} in "
               "place. All three at 0 is read as all-on.")

p_ripple = iface.new_panel(
    "Ripple Axes", default_closed=True,
    description="Which axes the wave travels across (weights the radius measurement).")
p_affect = iface.new_panel(
    "Affect Axes", default_closed=True,
    description="Which axes the deformation is allowed to move.")

ripple_socks = [add_float("Ripple " + a, RIPPLE_DESC.format(ax=a)) for a in "XYZ"]
affect_socks = [add_float("Affect " + a, AFFECT_DESC.format(ax=a)) for a in "XYZ"]
for i, s in enumerate(ripple_socks):
    iface.move_to_parent(s, p_ripple, i)
for i, s in enumerate(affect_socks):
    iface.move_to_parent(s, p_affect, i)


def root_items():
    return [it for it in iface.items_tree if it.parent is None or it.parent.name == ""]


centre_idx = next(i for i, it in enumerate(root_items()) if it.name == "Center")
iface.move(p_ripple, centre_idx)
iface.move(p_affect, centre_idx + 1)

# the Displace Along tooltip now has a companion control worth naming
for it in iface.items_tree:
    if it.item_type == 'SOCKET' and it.name == "Displace Along":
        it.description = ("Direction the ripple pushes: an axis (X/Y/Z), the surface "
                          "Normal, or the Direction Object. Radius is measured in the "
                          "plane perpendicular to it, filtered by Ripple Axes.")

ID = {s.name: s.identifier for s in iface.items_tree if s.item_type == 'SOCKET'}


# --------------------------------------------------------------------------- helpers
def axis_weight_block(frame, x, y, sock_names, tag):
    """GroupInput -> CombineXYZ -> (all-zero? -> (1,1,1)) -> weight vector."""
    gi = nodes.new("NodeGroupInput")
    gi.parent = frame
    gi.label = "In: " + frame.label
    gi.location = (x, y - 300)
    keep = set(ID[n] for n in sock_names)
    for s in gi.outputs:
        s.hide = s.identifier not in keep

    comb = nodes.new("ShaderNodeCombineXYZ")
    comb.parent = frame
    comb.label = tag + " weights"
    comb.location = (x + 300, y)

    dot = nodes.new("ShaderNodeVectorMath")
    dot.parent = frame
    dot.operation = 'DOT_PRODUCT'
    dot.label = "sum of weights"
    dot.location = (x + 600, y - 60)
    dot.inputs[1].default_value = (1.0, 1.0, 1.0)

    cmp = nodes.new("FunctionNodeCompare")
    cmp.parent = frame
    cmp.data_type = 'FLOAT'
    cmp.operation = 'LESS_THAN'
    cmp.label = "all zero?"
    cmp.location = (x + 900, y - 60)
    inp_of(cmp, 'B').default_value = 1e-6

    sw = nodes.new("GeometryNodeSwitch")
    sw.parent = frame
    sw.input_type = 'VECTOR'
    sw.label = "all zero -> all on"
    sw.location = (x + 1200, y)
    inp_of(sw, 'True').default_value = (1.0, 1.0, 1.0)

    for i, n in enumerate(sock_names):
        links.new(out_of(gi, ID[n]), comb.inputs[i])
    links.new(out_of(comb, 'Vector'), inp_of(dot, 'Vector'))
    links.new(out_of(dot, 'Value'), inp_of(cmp, 'A'))
    links.new(out_of(comb, 'Vector'), inp_of(sw, 'False'))
    links.new(out_of(cmp, 'Result'), inp_of(sw, 'Switch'))

    mul = nodes.new("ShaderNodeVectorMath")
    mul.parent = frame
    mul.operation = 'MULTIPLY'
    mul.label = "apply " + tag
    mul.location = (x + 1500, y + 60)
    links.new(out_of(sw, 'Output'), inp_of(mul, 'Vector_001'))
    return mul


# ------------------------------------------------------- Ripple Axes (radius filter)
f_ripple = nodes.new("NodeFrame")
f_ripple.label = "Ripple Axes  (radius = |perpendicular x (Rx,Ry,Rz)|)"
f_ripple.location = (0, 0)
f_ripple.label_size = 26

mul_r = axis_weight_block(f_ripple, 3600, -4400,
                          ["Ripple X", "Ripple Y", "Ripple Z"], "ripple")

perp = nodes["Vector Math.004"]        # d - dir*(d.dir)
radius = nodes["Vector Math.005"]      # LENGTH
for l in [l for l in links if l.to_node == radius and l.to_socket.identifier == 'Vector']:
    links.remove(l)
links.new(out_of(perp, 'Vector'), inp_of(mul_r, 'Vector'))
links.new(out_of(mul_r, 'Vector'), inp_of(radius, 'Vector'))

# ------------------------------------------------------- Affect Axes (offset filter)
f_affect = nodes.new("NodeFrame")
f_affect.label = "Affect Axes  (offset x (Ax,Ay,Az))"
f_affect.location = (0, 0)
f_affect.label_size = 26

mul_a = axis_weight_block(f_affect, 3600, -5400,
                          ["Affect X", "Affect Y", "Affect Z"], "affect")

wave_offset = nodes["Vector Math.006"]  # dir * wave
consumers = [(l.to_node, l.to_socket.identifier)
             for l in links if l.from_node == wave_offset]
for l in [l for l in links if l.from_node == wave_offset]:
    links.remove(l)
links.new(out_of(wave_offset, 'Vector'), inp_of(mul_a, 'Vector'))
for node, sock_id in consumers:
    links.new(out_of(mul_a, 'Vector'), inp_of(node, sock_id))
print("BUILD: offset consumers rewired -> "
      + str([(n.name, s) for n, s in consumers]), flush=True)

# -------------------------------------------------- backfill the shipped demo modifier
for o in demo_objects():
    for m in o.modifiers:
        if m.type == 'NODES' and m.node_group == ng:
            for n in ("Ripple X", "Ripple Y", "Ripple Z",
                      "Affect X", "Affect Y", "Affect Z"):
                m[ID[n]] = 1.0
    o.update_tag()

# ------------------------------------------------------------------- geometry gate
bpy.context.view_layer.update()
AFTER = snapshot()
same = BEFORE == AFTER
if not same:
    for k in BEFORE:
        b, a = BEFORE[k], AFTER.get(k, [])
        diff = [(i, b[i], a[i]) for i in range(min(len(b), len(a))) if b[i] != a[i]][:5]
        if b != a:
            print("BUILD: MISMATCH on %s: %d -> %d verts, first %s"
                  % (k, len(b), len(a), diff), flush=True)
print("BUILD: geometry unchanged at defaults = " + str(same), flush=True)

print("BUILD: interface ---", flush=True)
for it in iface.items_tree:
    pad = "  " if (it.parent and it.parent.name) else ""
    kind = "[P] " if it.item_type == 'PANEL' else ""
    print("  " + pad + kind + it.name, flush=True)

if not same:
    print("BUILD: ABORT -- not saving", flush=True)
    sys.stdout.flush()
    os._exit(1)

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print("BUILD: saved " + PATH, flush=True)
sys.stdout.flush()
os._exit(0)
