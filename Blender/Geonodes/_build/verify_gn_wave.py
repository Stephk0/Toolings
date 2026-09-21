"""Verification matrix for GN_Wave: travel distance, Symmetry, Ripple/Affect Axes.

The wave is
    offset = dir * Amplitude * sin(2*pi/Wavelength * d + Phase) * (Ax,Ay,Az)
with the travel distance d measured from the Center as
    t  = perp * (Rx,Ry,Rz)                     perp = (pos-Center) minus its dir part
    d  = dot(t, normalize(R - dir*(R.dir)))    Symmetry OFF -- signed, continuous
    d  = length(t)                             Symmetry ON  -- mirrored around Center

Run:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup D:\\...\\GN_Wave.blend --python verify_gn_wave.py
"""
import bpy, sys, os, math

NAME = "GN_Wave"
ng = bpy.data.node_groups[NAME]
ID = {s.name: s.identifier for s in ng.interface.items_tree if s.item_type == 'SOCKET'}

PASS, FAIL = [], []
DEMO_OK = [o.name for o in bpy.data.objects
           if any(m.type == 'NODES' and m.node_group == ng for m in o.modifiers)]
DEMO_SYM = [m[ID["Symmetry"]] for o in bpy.data.objects for m in o.modifiers
            if m.type == 'NODES' and m.node_group == ng]


def ck(label, cond, extra=""):
    (PASS if cond else FAIL).append(label)
    print("[%s] %s%s" % (" OK " if cond else "FAIL", label,
                         ("  -- " + extra) if extra else ""), flush=True)


def fresh():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)


def evaluated(obj):
    obj.update_tag()
    bpy.context.view_layer.update()
    return obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).data


MENU_ITEMS = [s.name for s in ng.nodes["Menu Switch"].inputs
              if s.identifier.startswith("Item_")]


def add_wave(obj, direction=None, **kw):
    md = obj.modifiers.new("Wave", 'NODES')
    md.node_group = ng
    # every input explicit: a new socket backfills a modifier with type-zero
    md[ID["Amplitude"]] = 1.0
    md[ID["Wavelength"]] = 4.0
    md[ID["Phase"]] = 0.0
    md[ID["Symmetry"]] = False
    md[ID["Center"]] = (0.0, 0.0, 0.0)
    md[ID["Show Center Gizmo"]] = False
    md[ID["Show Deformation Preview"]] = False
    md[ID["Use Object As Center"]] = False
    md[ID["Selection"]] = True
    for a in "XYZ":
        md[ID["Ripple " + a]] = 1.0
        md[ID["Affect " + a]] = 1.0
    if direction is not None:
        try:
            md[ID["Displace Along"]] = direction
        except TypeError:
            md[ID["Displace Along"]] = MENU_ITEMS.index(direction)
    for k, v in kw.items():
        md[ID[k]] = v
    return md


def grid(size=8.0, subd=21):
    bpy.ops.mesh.primitive_grid_add(size=size, x_subdivisions=subd, y_subdivisions=subd)
    return bpy.context.object


def base_and_out(obj):
    return ([tuple(v.co) for v in obj.data.vertices],
            [tuple(v.co) for v in evaluated(obj).vertices])


def run(**kw):
    """Grid + wave with the given overrides -> (base, out)."""
    fresh()
    g = grid()
    add_wave(g, **kw)
    return base_and_out(g)


K = 2.0 * math.pi / 4.0


def mirrored_z(x, y, rx=1.0, ry=1.0, phase=0.0, cx=0.0):
    """Symmetry ON: |t|."""
    return math.sin(K * math.hypot((x - cx) * rx, y * ry) + phase)


def signed_z(x, y, rx=1.0, ry=1.0, phase=0.0, cx=0.0):
    """Symmetry OFF: dot(t, normalize(R in the perpendicular plane)); dir = Z."""
    n = math.hypot(rx, ry)
    if n < 1e-9:
        return math.sin(phase)
    return math.sin(K * ((x - cx) * rx * rx + y * ry * ry) / n + phase)


def maxerr(base, out, fn, **kw):
    return max(abs(o[2] - fn(b[0], b[1], **kw)) for b, o in zip(base, out))


def zmap(base, out):
    return dict(((round(b[0], 4), round(b[1], 4)), o[2]) for b, o in zip(base, out))


# ------------------------------------------------- A: default is signed & continuous
base, out = run()
ck("A defaults: vertex count unchanged", len(base) == len(out),
   "%d -> %d" % (len(base), len(out)))
ck("A defaults: signed diagonal wave matches analytic",
   maxerr(base, out, signed_z) < 1e-5, "max err %.2e" % maxerr(base, out, signed_z))
ck("A defaults: x/y untouched",
   max(max(abs(o[0] - b[0]), abs(o[1] - b[1])) for b, o in zip(base, out)) < 1e-6)
z = zmap(base, out)
odd = max(abs(z[(x, y)] + z[(-x, -y)])
          for (x, y) in z if (-x, -y) in z and (x, y) != (0.0, 0.0))
ck("A defaults: NO mirror about Center (odd function; sin is odd at Phase 0)",
   odd < 1e-5, "max |z(p) + z(-p)| = %.2e" % odd)

# ---------------------------------------------- B: Symmetry ON restores the ripple
base, out = run(Symmetry=True)
ck("B Symmetry ON: concentric ripple matches analytic",
   maxerr(base, out, mirrored_z) < 1e-5,
   "max err %.2e" % maxerr(base, out, mirrored_z))
z = zmap(base, out)
even = max(abs(z[(x, y)] - z[(-x, -y)]) for (x, y) in z if (-x, -y) in z)
ck("B Symmetry ON: mirrored about Center (even function)", even < 1e-6,
   "max |z(p) - z(-p)| = %.2e" % even)

# ------------------------------------- C: one ripple axis = plain continuous wave
base, out = run(**{"Ripple Y": 0.0})
err = max(abs(o[2] - math.sin(K * b[0])) for b, o in zip(base, out))
ck("C Ripple Y=0: continuous planar wave, z = sin(k*x) (signed, not |x|)",
   err < 1e-5, "max err %.2e" % err)
z = zmap(base, out)
ck("C Ripple Y=0: crests keep cycling past the Center (no crease)",
   max(abs(z[(x, y)] + z[(-x, y)]) for (x, y) in z if (-x, y) in z) < 1e-5)
cols = {}
for b, o in zip(base, out):
    cols.setdefault(round(b[0], 4), set()).add(round(o[2], 5))
ck("C Ripple Y=0: z constant along Y", all(len(v) == 1 for v in cols.values()))

base, out = run(Symmetry=True, **{"Ripple Y": 0.0})
err = max(abs(o[2] - math.sin(K * abs(b[0]))) for b, o in zip(base, out))
ck("C Ripple Y=0 + Symmetry: mirrored wave, z = sin(k*|x|)", err < 1e-5,
   "max err %.2e" % err)

base, out = run(**{"Ripple X": 0.0})
err = max(abs(o[2] - math.sin(K * b[1])) for b, o in zip(base, out))
ck("C Ripple X=0: continuous planar wave along Y", err < 1e-5, "max err %.2e" % err)

# ------------------------------------------------ D: partial weights still tunable
base, out = run(**{"Ripple Y": 0.5})
ck("D Ripple Y=0.5 (signed): matches analytic",
   maxerr(base, out, signed_z, ry=0.5) < 1e-5,
   "max err %.2e" % maxerr(base, out, signed_z, ry=0.5))
base, out = run(Symmetry=True, **{"Ripple Y": 0.5})
ck("D Ripple Y=0.5 + Symmetry: elliptical ripple matches analytic",
   maxerr(base, out, mirrored_z, ry=0.5) < 1e-5,
   "max err %.2e" % maxerr(base, out, mirrored_z, ry=0.5))

# ----------------------------------------------------------- E: Phase still cycles
base, out = run(Phase=1.0, **{"Ripple Y": 0.0})
err = max(abs(o[2] - math.sin(K * b[0] + 1.0)) for b, o in zip(base, out))
ck("E Phase shifts the continuous wave", err < 1e-5, "max err %.2e" % err)

# ----------------------------------------------------------- F: all-zero guards
ref = run()[1]
for mode in (False, True):
    base, out = run(Symmetry=mode,
                    **{"Ripple X": 0.0, "Ripple Y": 0.0, "Ripple Z": 0.0})
    r = run(Symmetry=mode)[1]
    err = max(abs(a[2] - b[2]) for a, b in zip(out, r))
    ck("F Ripple all 0 reads as all on (Symmetry %s)" % ("ON" if mode else "OFF"),
       err < 1e-6, "max err %.2e" % err)

base, out = run(**{"Affect X": 0.0, "Affect Y": 0.0, "Affect Z": 0.0})
ck("F Affect all 0 reads as all on",
   max(abs(a[2] - b[2]) for a, b in zip(out, ref)) < 1e-6)

# ----------------------------------------------------------------- G: Affect Axes
base, out = run(**{"Affect Z": 0.0})
ck("G Affect Z=0: Z-displacement fully locked",
   max(abs(o[2] - b[2]) for b, o in zip(base, out)) < 1e-6)
base, out = run(**{"Affect Z": 0.25})
err = max(abs(o[2] - 0.25 * signed_z(b[0], b[1])) for b, o in zip(base, out))
ck("G Affect Z=0.25: offset scaled to a quarter", err < 1e-5, "max err %.2e" % err)


# --------------------------------------- H: non-axis-aligned direction (cylinder)
def cylinder():
    bpy.ops.mesh.primitive_cylinder_add(radius=1.0, depth=4.0, vertices=32)
    return bpy.context.object


fresh()
c = cylinder()
add_wave(c, direction="Normal")
base, out = base_and_out(c)
dx = max(abs(o[0] - b[0]) for b, o in zip(base, out))
dy = max(abs(o[1] - b[1]) for b, o in zip(base, out))
ck("H Normal direction: X and Y both move by default", dx > 1e-3 and dy > 1e-3,
   "max dx %.4f  max dy %.4f" % (dx, dy))

fresh()
c = cylinder()
add_wave(c, direction="Normal")
c.modifiers[0][ID["Affect X"]] = 0.0
base, out = base_and_out(c)
dx = max(abs(o[0] - b[0]) for b, o in zip(base, out))
dy = max(abs(o[1] - b[1]) for b, o in zip(base, out))
ck("H Normal direction + Affect X=0: X pinned, Y still ripples",
   dx < 1e-6 and dy > 1e-3, "max dx %.2e  max dy %.4f" % (dx, dy))

# --------------------------------------------------- I: existing features unaffected
base, out = run(Center=(1.0, 0.0, 0.0), **{"Ripple Y": 0.0})
err = max(abs(o[2] - math.sin(K * (b[0] - 1.0))) for b, o in zip(base, out))
ck("I Center offset still honoured (wave origin moves with it)", err < 1e-5,
   "max err %.2e" % err)

fresh()
g = grid()
md = add_wave(g)
md[ID["Show Center Gizmo"]] = True
gz = len(evaluated(g).vertices)
md[ID["Show Center Gizmo"]] = False
md[ID["Show Deformation Preview"]] = True
pv = len(evaluated(g).vertices)
ck("I gizmo is overlay-only (adds 0 verts)", gz == len(g.data.vertices), str(gz))
ck("I preview cage still adds geometry", pv > len(g.data.vertices), str(pv))

# ------------------------------------------------------------------- J: interface
items = list(ng.interface.items_tree)
socks = [i for i in items if i.item_type == 'SOCKET']
ins = [s.name for s in socks if s.in_out == 'INPUT']
ck("J input socket names unique (R9)", len(ins) == len(set(ins)))
s = next(i for i in socks if i.name == "Symmetry")
ck("J Symmetry: bool, default OFF, in the Wave panel, tooltipped",
   s.socket_type == 'NodeSocketBool' and s.default_value is False
   and s.parent.name == "Wave" and bool(s.description),
   "default=%s parent=%s" % (s.default_value, s.parent.name))
wave_order = [i.name for i in items
              if i.item_type == 'SOCKET' and i.parent and i.parent.name == "Wave"]
ck("J Wave panel order matches the sibling deformers "
   "(Symmetry before Direction Object)",
   wave_order == ["Amplitude", "Wavelength", "Phase", "Displace Along", "Symmetry",
                  "Direction Object"], str(wave_order))
for a in "XYZ":
    for kind, panel in (("Ripple", "Ripple Axes"), ("Affect", "Affect Axes")):
        s = next(i for i in socks if i.name == "%s %s" % (kind, a))
        ok = (s.subtype == 'FACTOR' and abs(s.default_value - 1.0) < 1e-9
              and s.min_value == 0.0 and s.max_value == 1.0
              and s.description and s.parent.name == panel)
        ck("J %s %s: FACTOR 0..1 default 1, tooltipped, panel %r" % (kind, a, panel),
           ok, "subtype=%s default=%s parent=%s" % (s.subtype, s.default_value,
                                                    s.parent.name))
panels = [i.name for i in items if i.item_type == 'PANEL']
ck("J panel order: Wave -> Ripple Axes -> Affect Axes -> Center -> Preview",
   panels == ["Wave", "Ripple Axes", "Affect Axes", "Center", "Preview"], str(panels))
ck("J every input socket tooltipped",
   all(s.description for s in socks if s.in_out == 'INPUT'))

# ----------------------------------------------------------------- K: graph hygiene
unframed = [n.name for n in ng.nodes if n.parent is None and n.bl_idname not in
            ("NodeFrame", "NodeReroute", "NodeGroupInput", "NodeGroupOutput")]
ck("K every function node is framed (R8)", not unframed, str(unframed))
ck("K every frame labelled (R4)",
   all(n.label for n in ng.nodes if n.bl_idname == "NodeFrame"))
orphans = [n.name for n in ng.nodes
           if n.bl_idname == "NodeReroute" and not n.outputs[0].is_linked]
ck("K no orphaned reroutes left by the rewire", not orphans, str(orphans))

# -------------------------------------------------------------------- L: publishing
ad = ng.asset_data
ck("L marked as asset", ad is not None)
if ad:
    ck("L ST3E tag present", "ST3E" in [t.name for t in ad.tags],
       str([t.name for t in ad.tags]))
    ck("L catalog assigned",
       str(ad.catalog_id) != "00000000-0000-0000-0000-000000000000", str(ad.catalog_id))
ck("L is_modifier", ng.is_modifier)
ck("L demo object ships with the modifier attached", bool(DEMO_OK), str(DEMO_OK))
ck("L demo ships on the continuous default (Symmetry off)",
   DEMO_SYM == [False] * len(DEMO_SYM), str(DEMO_SYM))

print("\n%d passed, %d failed" % (len(PASS), len(FAIL)), flush=True)
for f in FAIL:
    print("  FAILED: " + f, flush=True)
sys.stdout.flush()
os._exit(1 if FAIL else 0)
