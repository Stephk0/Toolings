"""GN_Wave -- make the wave continuous by default, keep the mirror as `Symmetry`.

The travel distance used to be `|perp * R|`, an EVEN function of position: the
wave mirrored around the Center and creased there, so an object straddling the
Center never cycled through a continuous wave.

Now the distance is a SIGNED projection by default:

    t  = perp * (Rx,Ry,Rz)                     weighted perpendicular offset
    Rp = R - dir*(R.dir)                       weight vector in the perp plane
    d  = dot(t, normalize(Rp))                 Symmetry OFF -- continuous
    d  = length(t)                             Symmetry ON  -- mirrored ripple

Symmetry ON reproduces the old output bit-for-bit (verified in this script).
A new bool socket backfills existing modifiers with False, which is the new
default, so legacy files pick up the continuous wave too -- intended.

The radius chain also moves into its own frame ("Travel Distance") so the graph
keeps flowing left-to-right: Displace Direction -> Travel Distance -> Wave.

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup D:\\...\\GN_Wave.blend --python build_gn_wave_symmetry.py
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


def by_label(label):
    return next(n for n in nodes if n.label == label)


def unlink_input(node, ident):
    """Drop the link into a socket, pruning any reroute chain left orphaned."""
    for l in [l for l in links if l.to_node == node and l.to_socket.identifier == ident]:
        src = l.from_node
        links.remove(l)
        while src is not None and src.bl_idname == "NodeReroute" \
                and not src.outputs[0].is_linked:
            feeders = [ll.from_node for ll in links if ll.to_node == src]
            for ll in [ll for ll in links if ll.to_node == src]:
                links.remove(ll)
            nodes.remove(src)
            src = feeders[0] if feeders else None


def demo_objects():
    return [o for o in bpy.data.objects
            if any(m.type == 'NODES' and m.node_group == ng for m in o.modifiers)]


def snapshot():
    dg = bpy.context.evaluated_depsgraph_get()
    return {o.name: [tuple(round(c, 6) for c in v.co)
                     for v in o.evaluated_get(dg).data.vertices]
            for o in demo_objects()}


bpy.context.view_layer.update()
BEFORE = snapshot()
print("BUILD: snapshot " + str([(k, len(v)) for k, v in BEFORE.items()]), flush=True)

# ------------------------------------------------------------------------ interface
sym = iface.new_socket(name="Symmetry", in_out='INPUT', socket_type='NodeSocketBool')
sym.default_value = False
sym.description = ("Mirror the wave around the Center: the travel distance becomes an "
                   "absolute distance, giving a concentric ripple with a crease at the "
                   "Center. Off (default) measures a signed distance, so the wave "
                   "cycles continuously across the whole object.")
wave_panel = next(i for i in iface.items_tree
                  if i.item_type == 'PANEL' and i.name == "Wave")
order = [i.name for i in iface.items_tree
         if i.item_type == 'SOCKET' and i.parent and i.parent.name == "Wave"]
iface.move_to_parent(sym, wave_panel, order.index("Direction Object"))

ID = {s.name: s.identifier for s in iface.items_tree if s.item_type == 'SOCKET'}

for it in iface.items_tree:
    if it.item_type == 'SOCKET' and it.name.startswith("Ripple "):
        ax = it.name[-1]
        it.description = (
            "How strongly the %s axis contributes to the wave's travel distance. "
            "Zero one axis to get a plain planar wave running along the other. "
            "With Symmetry off the weights also set the direction the wave travels. "
            "All three at 0 is read as all-on." % ax)

# ------------------------------------------------------ regroup: Travel Distance frame
f_travel = next(n for n in nodes
                if n.bl_idname == "NodeFrame" and n.label.startswith("Ripple Axes"))
f_travel.label = "Travel Distance  (Ripple Axes weights; Symmetry = |d| vs signed d)"

for lab in ("pos - Center", "d . dir", "dir x dot", "perpendicular", "radius",
            "apply ripple"):
    by_label(lab).parent = f_travel
for n in nodes:
    if n.bl_idname == "GeometryNodeInputPosition":
        n.parent = f_travel

weight_vec = by_label("all zero -> all on")      # guarded (Rx,Ry,Rz)
t_vec = by_label("apply ripple")                 # perp * R
length = by_label("radius")                      # |t|
direction = by_label("Displace Dir")             # unit direction vector
kr = by_label("k x r")                           # consumer of the travel distance

X, Y = t_vec.location.x, t_vec.location.y - 520

# Rp = R - dir*(R.dir), the weight vector projected into the perpendicular plane
d_rd = nodes.new("ShaderNodeVectorMath")
d_rd.parent, d_rd.operation, d_rd.label = f_travel, 'DOT_PRODUCT', "R . dir"
d_rd.location = (X, Y)

scl = nodes.new("ShaderNodeVectorMath")
scl.parent, scl.operation, scl.label = f_travel, 'SCALE', "dir x (R . dir)"
scl.location = (X + 300, Y)

rp = nodes.new("ShaderNodeVectorMath")
rp.parent, rp.operation, rp.label = f_travel, 'SUBTRACT', "R in perp plane"
rp.location = (X + 600, Y)

uhat = nodes.new("ShaderNodeVectorMath")
uhat.parent, uhat.operation, uhat.label = f_travel, 'NORMALIZE', "travel direction"
uhat.location = (X + 900, Y)

signed = nodes.new("ShaderNodeVectorMath")
signed.parent, signed.operation, signed.label = f_travel, 'DOT_PRODUCT', "signed distance"
signed.location = (X + 1200, Y)

sym_sw = nodes.new("GeometryNodeSwitch")
sym_sw.parent, sym_sw.input_type = f_travel, 'FLOAT'
sym_sw.label = "Symmetry? mirrored : continuous"
sym_sw.location = (X + 1500, Y + 200)

gi = nodes.new("NodeGroupInput")
gi.parent, gi.label = f_travel, "In: Symmetry"
gi.location = (X + 1200, Y - 300)
for s in gi.outputs:
    s.hide = s.identifier != ID["Symmetry"]

links.new(out_of(weight_vec, 'Output'), inp_of(d_rd, 'Vector'))
links.new(out_of(direction, 'Output'), inp_of(d_rd, 'Vector_001'))
links.new(out_of(direction, 'Output'), inp_of(scl, 'Vector'))
links.new(out_of(d_rd, 'Value'), inp_of(scl, 'Scale'))
links.new(out_of(weight_vec, 'Output'), inp_of(rp, 'Vector'))
links.new(out_of(scl, 'Vector'), inp_of(rp, 'Vector_001'))
links.new(out_of(rp, 'Vector'), inp_of(uhat, 'Vector'))
links.new(out_of(t_vec, 'Vector'), inp_of(signed, 'Vector'))
links.new(out_of(uhat, 'Vector'), inp_of(signed, 'Vector_001'))

links.new(out_of(signed, 'Value'), inp_of(sym_sw, 'False'))
links.new(out_of(length, 'Value'), inp_of(sym_sw, 'True'))
links.new(out_of(gi, ID["Symmetry"]), inp_of(sym_sw, 'Switch'))

unlink_input(kr, 'Value_001')
links.new(out_of(sym_sw, 'Output'), inp_of(kr, 'Value_001'))
print("BUILD: travel distance rewired into %r" % kr.label, flush=True)

# --------------------------------------------- Symmetry ON must reproduce the old wave
for o in demo_objects():
    for m in o.modifiers:
        if m.type == 'NODES' and m.node_group == ng:
            m[ID["Symmetry"]] = True
    o.update_tag()
bpy.context.view_layer.update()
MIRRORED = snapshot()
same = BEFORE == MIRRORED
print("BUILD: Symmetry ON reproduces the previous output = " + str(same), flush=True)
if not same:
    for k in BEFORE:
        b, a = BEFORE[k], MIRRORED.get(k, [])
        diff = [(i, b[i], a[i]) for i in range(min(len(b), len(a))) if b[i] != a[i]][:5]
        if diff:
            print("BUILD: MISMATCH %s -> %s" % (k, diff), flush=True)

# ship the demo on the new default
for o in demo_objects():
    for m in o.modifiers:
        if m.type == 'NODES' and m.node_group == ng:
            m[ID["Symmetry"]] = False
    o.update_tag()
bpy.context.view_layer.update()
CONT = snapshot()
delta = max(abs(a[2] - b[2])
            for k in BEFORE for a, b in zip(CONT[k], BEFORE[k]))
print("BUILD: continuous default differs from mirrored by max dz %.4f" % delta,
      flush=True)

if not same:
    print("BUILD: ABORT -- not saving", flush=True)
    sys.stdout.flush()
    os._exit(1)

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print("BUILD: saved " + PATH, flush=True)
sys.stdout.flush()
os._exit(0)
