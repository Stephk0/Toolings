"""Build GN_RandomizeMeshElements.blend -- a Geometry Nodes MODIFIER that gives every
mesh ELEMENT (island / face / material / attribute group) its own random rigid-ish
transform: position offset, rotation, scale and axis mirroring ("flip").

Per element, with a random value keyed on the element's group id:

    p' = pivot + Rot( (Scale * Flip) * (p - pivot) ) + Offset

Elements are separated first (edges split at the group borders) so that a vertex
shared by two groups cannot be asked to move two ways -- for Island grouping there
are no such borders, so that split is a no-op and topology is untouched.

Mirroring an element inverts its winding, so faces of elements with an odd number
of mirrored axes are flipped back (Flip Faces On Mirror) to keep normals outward.

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python build_gn_randomize_mesh_elements.py
"""
import bpy, bmesh, sys, os, math
from mathutils import Matrix

GEO  = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_RandomizeMeshElements"
PATH = os.path.join(GEO, NAME + ".blend")
CAT  = "bacd112a-8e87-47c2-afbc-818a11c75c08"   # ST3E/Deform (sibling of GN_RandomizePosition)

# ----------------------------------------------------------------------------- helpers
def _pick(sockets, key):
    """Resolve a socket by index, identifier or display name -- preferring the
    ENABLED variant (multi-type nodes keep disabled same-name sockets that no-op)."""
    if isinstance(key, int):
        return sockets[key]
    # enabled identifier -> enabled name -> any identifier -> any name.
    # (Multi-type nodes such as Random Value keep a DISABLED socket whose identifier
    #  is the plain name; linking it silently no-ops at evaluation time.)
    for test in (lambda s: s.enabled and s.identifier == key,
                 lambda s: s.enabled and s.name == key,
                 lambda s: s.identifier == key,
                 lambda s: s.name == key):
        for s in sockets:
            if test(s):
                return s
    raise KeyError(key)
def osock(node, key): return _pick(node.outputs, key)
def isock(node, key): return _pick(node.inputs,  key)

# ----------------------------------------------------------------------------- clean slate
for _ng in list(bpy.data.node_groups):
    if _ng.name == NAME:
        bpy.data.node_groups.remove(_ng)

ng = bpy.data.node_groups.new(NAME, "GeometryNodeTree")
n, links = ng.nodes, ng.links
def link(a, ai, b, bi): links.new(osock(a, ai), isock(b, bi))

# ============================================================================= INTERFACE
iface = ng.interface
def sock(name, in_out, stype, parent=None, default=None, mn=None, mx=None,
         subtype=None, desc=""):
    s = iface.new_socket(name, in_out=in_out, socket_type=stype,
                         parent=parent if parent else None)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    return s

# --- top level ---------------------------------------------------------------
sock("Geometry", 'INPUT', 'NodeSocketGeometry',
     desc="Mesh whose elements are randomized.")
sock("Selection", 'INPUT', 'NodeSocketBool', default=True,
     desc="Vertices that are allowed to move. Leave on to randomize the whole mesh; "
          "drive it with an attribute/field to protect regions. Note the random values "
          "themselves are always computed per whole element, so a partly selected "
          "element gets torn -- select whole elements if you want them to stay rigid.")

# --- Elements ----------------------------------------------------------------
p_el = iface.new_panel("Elements")
sk_gby = sock("Group By", 'INPUT', 'NodeSocketMenu', parent=p_el,
     desc="What counts as one element. Island = a connected piece of mesh (the usual "
          "'element'), Face = every face on its own, Material = faces sharing a material "
          "slot, Attribute = faces sharing the value of an integer attribute. Except for "
          "Island, the mesh is split along the group borders so each element can move "
          "freely -- Island grouping leaves the topology untouched.")
sock("Group Attribute", 'INPUT', 'NodeSocketString', parent=p_el, default="group_id",
     desc="Name of the INTEGER attribute that identifies the elements when Group By is "
          "set to Attribute. Faces sharing a value form one element.")
sock("Seed", 'INPUT', 'NodeSocketInt', parent=p_el, default=0,
     desc="Changes the whole random pattern. Same seed + same mesh = same result.")
sock("Affect Chance", 'INPUT', 'NodeSocketFloat', parent=p_el, default=1.0,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Fraction of the elements that get randomized at all. 1 = every element, "
          "0.3 = roughly a third; the rest stay exactly where they are.")

# --- Position ----------------------------------------------------------------
p_pos = iface.new_panel("Position")
sock("Position Amount", 'INPUT', 'NodeSocketVector', parent=p_pos,
     default=(0.1, 0.1, 0.1), subtype='TRANSLATION',
     desc="Maximum random move per axis, in object units. Each element is offset by a "
          "random amount between minus and plus this vector.")

# --- Rotation ----------------------------------------------------------------
p_rot = iface.new_panel("Rotation")
sock("Rotation Amount", 'INPUT', 'NodeSocketVector', parent=p_rot,
     default=(0.0, 0.0, math.radians(15.0)), subtype='EULER',
     desc="Maximum random rotation per axis. Each element is rotated about its pivot by "
          "a random angle between minus and plus these values (XYZ Euler).")

# --- Scale -------------------------------------------------------------------
p_scl = iface.new_panel("Scale")
sock("Uniform Scale", 'INPUT', 'NodeSocketBool', parent=p_scl, default=True,
     desc="On: one random factor scales the element on all three axes, so its shape is "
          "kept. Off: each axis gets its own random factor (stretched elements).")
sock("Scale Min", 'INPUT', 'NodeSocketFloat', parent=p_scl, default=0.9, mn=0.0,
     desc="Smallest random scale factor. 1 = original size.")
sock("Scale Max", 'INPUT', 'NodeSocketFloat', parent=p_scl, default=1.1, mn=0.0,
     desc="Largest random scale factor. Set both Min and Max to 1 to disable scaling.")

# --- Flip --------------------------------------------------------------------
p_flp = iface.new_panel("Flip")
sock("Flip X Chance", 'INPUT', 'NodeSocketFloat', parent=p_flp, default=0.0,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Chance that an element is mirrored on X about its pivot. 0.5 = about half of "
          "them. Useful to break up repeated modular pieces.")
sock("Flip Y Chance", 'INPUT', 'NodeSocketFloat', parent=p_flp, default=0.0,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Chance that an element is mirrored on Y about its pivot.")
sock("Flip Z Chance", 'INPUT', 'NodeSocketFloat', parent=p_flp, default=0.0,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Chance that an element is mirrored on Z about its pivot.")
sock("Flip Faces On Mirror", 'INPUT', 'NodeSocketBool', parent=p_flp, default=True,
     desc="Mirroring turns an element inside out. With this on, the faces of elements "
          "mirrored on an odd number of axes are flipped back so the normals keep "
          "pointing outward. Turn off to see (or keep) the inverted shading.")

# --- Pivot -------------------------------------------------------------------
p_piv = iface.new_panel("Pivot")
sk_piv = sock("Pivot Point", 'INPUT', 'NodeSocketMenu', parent=p_piv,
     desc="What the rotation, scaling and mirroring of an element happen around. "
          "Element Center = the average of the element's own vertices (each piece turns "
          "in place). Object Origin = the object's origin, so elements swing around the "
          "object centre like a fan.")

sock("Geometry", 'OUTPUT', 'NodeSocketGeometry',
     desc="Mesh with every element randomly transformed.")

# socket name constants (used for Group Input routing)
S_GEO, S_SEL   = "Geometry", "Selection"
S_GBY, S_GATTR = "Group By", "Group Attribute"
S_SEED, S_CHN  = "Seed", "Affect Chance"
S_POS          = "Position Amount"
S_ROT          = "Rotation Amount"
S_UNI, S_SMIN, S_SMAX = "Uniform Scale", "Scale Min", "Scale Max"
S_FX, S_FY, S_FZ, S_FF = ("Flip X Chance", "Flip Y Chance", "Flip Z Chance",
                          "Flip Faces On Mirror")
S_PIV          = "Pivot Point"

gin  = n.new("NodeGroupInput")
gout = n.new("NodeGroupOutput")

# ============================================================================= FRAMES
def frame(label):
    f = n.new("NodeFrame"); f.label = label; f.location = (0, 0)
    f.use_custom_color = True; f.color = (0.18, 0.20, 0.26)
    return f
F_grp = frame("Element Grouping  (Group By -> group id)")
F_sep = frame("Separate Elements  (split edges at group borders)")
F_rnd = frame("Per-Element Randoms  (ID = group id)")
F_piv = frame("Pivot  (element centre / object origin)")
F_scl = frame("Scale & Flip Vector")
F_xf  = frame("Element Transform  (flip -> scale -> rotate -> offset)")
F_out = frame("Apply  (Set Position + Flip mirrored faces)")

def mk(idname, parent=None, loc=(0, 0), **props):
    node = n.new(idname)
    for k, v in props.items(): setattr(node, k, v)
    if parent: node.parent = parent
    node.location = loc
    return node

def math_(op, parent, loc):  return mk("ShaderNodeMath", parent, loc, operation=op)
def vmath(op, parent, loc):  return mk("ShaderNodeVectorMath", parent, loc, operation=op)
def cmp(op, dtype, parent, loc):
    return mk("FunctionNodeCompare", parent, loc, data_type=dtype, operation=op)
def boolmath(op, parent, loc):
    return mk("FunctionNodeBooleanMath", parent, loc, operation=op)
def rnd(dtype, parent, loc):
    return mk("FunctionNodeRandomValue", parent, loc, data_type=dtype)
def comb(parent, loc): return mk("ShaderNodeCombineXYZ", parent, loc)
def sep(parent, loc):  return mk("ShaderNodeSeparateXYZ", parent, loc)

# ============================================================================= 1. GROUPING
# One integer key per FACE identifies the element. Reading it back on the POINT
# domain is exact once the mesh is split along the group borders (below), because
# then every vertex only touches faces of a single group.
isl  = mk("GeometryNodeInputMeshIsland",    F_grp, (-2400,  460))
idx  = mk("GeometryNodeInputIndex",         F_grp, (-2400,  300))
mat  = mk("GeometryNodeInputMaterialIndex", F_grp, (-2400,  160))
attr = mk("GeometryNodeInputNamedAttribute", F_grp, (-2400, -20), data_type='INT')
link(gin, S_GATTR, attr, "Name")

gMenu = mk("GeometryNodeMenuSwitch", F_grp, (-2160, 520), data_type='INT')
_gi = gMenu.enum_definition.enum_items
_gi[0].name = "Island"; _gi[1].name = "Face"
for _nm in ("Material", "Attribute"): _gi.new(_nm)
for _i in range(4): isock(gMenu, f"Item_{_i}").default_value = _i
link(gin, S_GBY, gMenu, "Menu")

gPick = mk("GeometryNodeIndexSwitch", F_grp, (-1940, 300), data_type='INT')
for _ in range(2): gPick.index_switch_items.new()          # 2 stock + 2 = 4 items
link(gMenu, "Output", gPick, "Index")
link(isl,  "Island Index",   gPick, "Item_0")
link(idx,  "Index",          gPick, "Item_1")
link(mat,  "Material Index", gPick, "Item_2")
link(attr, "Attribute",      gPick, "Item_3")

# the key, evaluated on FACE domain -> one value per face, shared by its corners
gid = mk("GeometryNodeFieldOnDomain", F_grp, (-1740, 300),
         data_type='INT', domain='FACE')
gid.label = "Group ID (per face)"
link(gPick, "Output", gid, "Value")

# ============================================================================= 2. SEPARATE
# Edges between two different groups are split so each element becomes its own
# island and its vertices can be moved independently. No border -> no-op.
bnd = mk("GeometryNodeMeshFaceSetBoundaries", F_sep, (-1500, 140))
link(gid, "Value", bnd, "Face Set")
split = mk("GeometryNodeSplitEdges", F_sep, (-1300, 300))
link(gin, S_GEO, split, "Mesh")
link(bnd, "Boundary Edges", split, "Selection")

# ============================================================================= 3. RANDOMS
# Every channel gets its own seed offset so position, rotation, scale, flip and the
# affect-chance draw are independent.
def seeded(offset, loc):
    m = math_('ADD', F_rnd, loc); m.label = f"Seed +{offset}"
    link(gin, S_SEED, m, 0); isock(m, "Value_001").default_value = float(offset)
    return m
sPos = seeded(0,       (-1120,  660))
sRot = seeded(7919,    (-1120,  380))
sScl = seeded(31337,   (-1120,  100))
sFlp = seeded(104729,  (-1120, -180))
sChn = seeded(1299709, (-1120, -460))

# --- position: random vector in [-Position Amount, +Position Amount]
posNeg = vmath('SCALE', F_rnd, (-900, 800)); link(gin, S_POS, posNeg, "Vector")
isock(posNeg, "Scale").default_value = -1.0
rPos = rnd('FLOAT_VECTOR', F_rnd, (-700, 760))
link(posNeg, "Vector", rPos, "Min"); link(gin, S_POS, rPos, "Max")
link(gid, "Value", rPos, "ID");      link(sPos, "Value", rPos, "Seed")

# --- rotation: random Euler in [-Rotation Amount, +Rotation Amount]
rotNeg = vmath('SCALE', F_rnd, (-900, 500)); link(gin, S_ROT, rotNeg, "Vector")
isock(rotNeg, "Scale").default_value = -1.0
rRot = rnd('FLOAT_VECTOR', F_rnd, (-700, 460))
link(rotNeg, "Vector", rRot, "Min"); link(gin, S_ROT, rRot, "Max")
link(gid, "Value", rRot, "ID");      link(sRot, "Value", rRot, "Seed")

# --- scale: one factor for all axes (uniform) or one per axis
rSclU = rnd('FLOAT', F_rnd, (-700, 180))
link(gin, S_SMIN, rSclU, "Min"); link(gin, S_SMAX, rSclU, "Max")
link(gid, "Value", rSclU, "ID"); link(sScl, "Value", rSclU, "Seed")
sMinV = comb(F_rnd, (-900, -20)); sMaxV = comb(F_rnd, (-900, -180))
for _c in range(3):
    link(gin, S_SMIN, sMinV, _c); link(gin, S_SMAX, sMaxV, _c)
rSclV = rnd('FLOAT_VECTOR', F_rnd, (-700, -100))
link(sMinV, "Vector", rSclV, "Min"); link(sMaxV, "Vector", rSclV, "Max")
link(gid, "Value", rSclV, "ID");     link(sScl, "Value", rSclV, "Seed")

# --- flip: one draw per axis in [0,1), compared against the per-axis chance
rFlp = rnd('FLOAT_VECTOR', F_rnd, (-700, -420))
isock(rFlp, "Min").default_value = (0.0, 0.0, 0.0)
isock(rFlp, "Max").default_value = (1.0, 1.0, 1.0)
link(gid, "Value", rFlp, "ID"); link(sFlp, "Value", rFlp, "Seed")

# --- affect chance: element participates at all?
rChn = rnd('FLOAT', F_rnd, (-700, -700))
isock(rChn, "Min").default_value = 0.0; isock(rChn, "Max").default_value = 1.0
link(gid, "Value", rChn, "ID"); link(sChn, "Value", rChn, "Seed")
chnLt = cmp('LESS_THAN', 'FLOAT', F_rnd, (-500, -700))
link(rChn, "Value", chnLt, "A"); link(gin, S_CHN, chnLt, "B")
chnAll = cmp('GREATER_EQUAL', 'FLOAT', F_rnd, (-500, -860))   # Chance 1 = always, exactly
link(gin, S_CHN, chnAll, "A"); isock(chnAll, "B").default_value = 1.0
affect = boolmath('OR', F_rnd, (-320, -780)); affect.label = "Element affected"
link(chnLt, "Result", affect, 0); link(chnAll, "Result", affect, 1)

# ============================================================================= 4. PIVOT
pos  = mk("GeometryNodeInputPosition", F_piv, (-1120, -1080))
accP = mk("GeometryNodeAccumulateField", F_piv, (-900, -1040),
          data_type='FLOAT_VECTOR', domain='POINT')
link(pos, "Position", accP, "Value"); link(gid, "Value", accP, "Group Index")
accN = mk("GeometryNodeAccumulateField", F_piv, (-900, -1240),
          data_type='FLOAT', domain='POINT')
isock(accN, "Value").default_value = 1.0
link(gid, "Value", accN, "Group Index")
cntV = comb(F_piv, (-700, -1240))
for _c in range(3): link(accN, "Total", cntV, _c)
centre = vmath('DIVIDE', F_piv, (-520, -1100)); centre.label = "Element centre"
link(accP, "Total", centre, 0); link(cntV, "Vector", centre, 1)

pMenu = mk("GeometryNodeMenuSwitch", F_piv, (-520, -1320), data_type='INT')
_pi = pMenu.enum_definition.enum_items
_pi[0].name = "Element Center"; _pi[1].name = "Object Origin"
for _i in range(2): isock(pMenu, f"Item_{_i}").default_value = _i
link(gin, S_PIV, pMenu, "Menu")
pivot = mk("GeometryNodeIndexSwitch", F_piv, (-320, -1160), data_type='VECTOR')
link(pMenu, "Output", pivot, "Index")
link(centre, "Vector", pivot, "Item_0")
isock(pivot, "Item_1").default_value = (0.0, 0.0, 0.0)

# ============================================================================= 5. SCALE+FLIP
# Flip sign per axis: +1 where the draw missed the chance, -1 where it hit.
# (Vector Math has no component-wise comparison in Blender 5, so this is per axis.)
flpXYZ = sep(F_scl, (-500, -420)); link(rFlp, "Value", flpXYZ, "Vector")
_flpsgn = []
for _ax, _chn, _y in (("X", S_FX, -300), ("Y", S_FY, -440), ("Z", S_FZ, -580)):
    c = cmp('LESS_THAN', 'FLOAT', F_scl, (-320, _y))
    link(flpXYZ, _ax, c, "A"); link(gin, _chn, c, "B")
    s = math_('MULTIPLY_ADD', F_scl, (-140, _y)); s.label = f"Flip sign {_ax}"
    link(c, "Result", s, 0)
    isock(s, "Value_001").default_value = -2.0     # 1 - 2*hit  ->  +1 / -1
    isock(s, "Value_002").default_value = 1.0
    _flpsgn.append(s)
flpSgn = comb(F_scl, (40, -440)); flpSgn.label = "Flip sign (+1 / -1)"
for _c, _s in enumerate(_flpsgn): link(_s, "Value", flpSgn, _c)

uniV = comb(F_scl, (-320, 60)); uniV.label = "Uniform scale"
for _c in range(3): link(rSclU, "Value", uniV, _c)
sclSw = mk("GeometryNodeSwitch", F_scl, (-140, -20), input_type='VECTOR')
link(gin, S_UNI, sclSw, "Switch")
link(rSclV, "Value", sclSw, "False"); link(uniV, "Vector", sclSw, "True")
sclVec = vmath('MULTIPLY', F_scl, (40, -140)); sclVec.label = "Scale * flip"
link(sclSw, "Output", sclVec, 0); link(flpSgn, "Vector", sclVec, 1)

# ============================================================================= 6. TRANSFORM
d0 = vmath('SUBTRACT', F_xf, (260, -620)); d0.label = "p - pivot"
link(pos, "Position", d0, 0); link(pivot, "Output", d0, 1)
d1 = vmath('MULTIPLY', F_xf, (440, -620)); d1.label = "scaled / mirrored"
link(d0, "Vector", d1, 0); link(sclVec, "Vector", d1, 1)
d2 = mk("ShaderNodeVectorRotate", F_xf, (620, -620), rotation_type='EULER_XYZ')
d2.label = "rotated"
link(d1, "Vector", d2, "Vector"); link(rRot, "Value", d2, "Rotation")
isock(d2, "Center").default_value = (0.0, 0.0, 0.0)
back = vmath('ADD', F_xf, (800, -620)); back.label = "back to pivot"
link(d2, "Vector", back, 0); link(pivot, "Output", back, 1)
moved = vmath('ADD', F_xf, (980, -620)); moved.label = "+ random offset"
link(back, "Vector", moved, 0); link(rPos, "Value", moved, 1)
delta = vmath('SUBTRACT', F_xf, (1160, -620)); delta.label = "offset from original"
link(moved, "Vector", delta, 0); link(pos, "Position", delta, 1)
gate = vmath('SCALE', F_xf, (1340, -620)); gate.label = "gate by Affect Chance"
link(delta, "Vector", gate, "Vector"); link(affect, "Boolean", gate, "Scale")

# ============================================================================= 7. APPLY
setp = mk("GeometryNodeSetPosition", F_out, (1560, 300))
link(split, "Mesh", setp, "Geometry")
link(gin, S_SEL, setp, "Selection")
link(gate, "Vector", setp, "Offset")

# an odd number of mirrored axes inverts the winding -> flip those faces back
sgnXYZ = sep(F_out, (1560, -140)); link(flpSgn, "Vector", sgnXYZ, "Vector")
mXY = math_('MULTIPLY', F_out, (1740, -140))
link(sgnXYZ, "X", mXY, 0); link(sgnXYZ, "Y", mXY, 1)
det = math_('MULTIPLY', F_out, (1900, -140)); det.label = "sign determinant"
link(mXY, "Value", det, 0); link(sgnXYZ, "Z", det, 1)
inv = cmp('LESS_THAN', 'FLOAT', F_out, (2060, -140))
link(det, "Value", inv, "A"); isock(inv, "B").default_value = 0.0
invA = boolmath('AND', F_out, (2220, -140))
link(inv, "Result", invA, 0); link(affect, "Boolean", invA, 1)
invB = boolmath('AND', F_out, (2380, -140))
link(invA, "Boolean", invB, 0); link(gin, S_FF, invB, 1)
invC = boolmath('AND', F_out, (2540, -140)); invC.label = "mirrored & selected"
link(invB, "Boolean", invC, 0); link(gin, S_SEL, invC, 1)

flip = mk("GeometryNodeFlipFaces", F_out, (2720, 300))
link(setp, "Geometry", flip, "Mesh")
link(invC, "Boolean", flip, "Selection")
link(flip, "Mesh", gout, S_GEO)

gin.location  = (-2800, 0)
gout.location = (2960, 0)

# menu interface defaults must be set AFTER the Menu Switches exist (they define the items)
sk_gby.default_value = "Island"
sk_piv.default_value = "Element Center"

# ============================================================================= DEMO OBJECT
# a grid of separate cubes: 16 islands, so the default settings visibly jitter,
# turn and resize each piece on its own.
for _o in list(bpy.data.objects):          # drop the factory-startup cube
    if _o.type == 'MESH':
        bpy.data.objects.remove(_o, do_unlink=True)
me = bpy.data.meshes.new("GN_Demo")
bm = bmesh.new()
for iy in range(4):
    for ix in range(4):
        bmesh.ops.create_cube(bm, size=0.6,
                              matrix=Matrix.Translation((ix - 1.5, iy - 1.5, 0.0)))
bm.to_mesh(me); bm.free()
obj = bpy.data.objects.new("GN_Demo", me)
bpy.context.scene.collection.objects.link(obj)
md = obj.modifiers.new(NAME, "NODES"); md.node_group = ng
obj.select_set(True); bpy.context.view_layer.objects.active = obj

# ============================================================================= PUBLISH
ng.asset_mark()
ng.asset_data.catalog_id = CAT
ng.asset_data.tags.new("ST3E")
ng.asset_data.description = (
    "Randomizes each mesh element on its own: per-element position offset, rotation, "
    "scale and axis mirroring, grouped by island, face, material or an integer "
    "attribute. Elements are separated at their borders, mirrored pieces get their "
    "faces flipped back, and Affect Chance leaves a share of them untouched.")
ng.is_modifier = True
ng.is_tool = False

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print("SAVED", PATH, "nodes:", len(ng.nodes))
sys.stdout.flush()
os._exit(0)
