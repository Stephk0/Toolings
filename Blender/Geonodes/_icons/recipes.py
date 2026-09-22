"""Icon recipes - one entry per ST3E geonode modifier.

A recipe says what to build, how to prepare it so the modifier actually bites,
which parameters to push, and what visible effect to expect. `expect` is
enforced at build time: if the modifier produced no measurable change the icon
build FAILS instead of quietly emitting an unmodified Suzanne.

Keys
----
file      .blend under Blender/Geonodes/ holding the group (default: group + ".blend")
group     datablock name, when the recipe KEY differs (two groups share a name)
also_embed  extra .blend files holding an identical copy - same icon embedded
catalog   asset catalog, picks the frame tint: Deform|Generate|Modify|Scatter|Shading
short     short name burned over the lower part of the icon
emblem    no modifier at all - a shared tile for a reusable node group
shader    a SHADER node group: rendered as a material, gated against plain clay
output    (shader) which group output to show; into = base_color | emission
engine    "EEVEE" to opt out of Cycles (run last - headless EEVEE can crash)
base      base mesh: suzanne|grid|plane|cylinder|icosphere  (default suzanne)
base_args kwargs for the base builder
helpers   extra objects for Object/Collection sockets; reference as "@name"
outputs   {output socket name: attribute name} - store an anonymous output
promote   {bool attr: float attr} - freeze the result and bake a flag to a shadeable float
prep      ordered list of prep steps, each ("step_name", *args, {kwargs})
params    {socket NAME: value}; Menu sockets take the item NAME as a string
cage      draw the modifier's deformation preview cage (deformers only)
keep_base draw the prepared mesh again, unmodified, behind the result
wire_only hide the solid result and keep only its ghost_wire
two_sided render backfaces in a warning tint (Flip Faces)
ghost_wire  "removed" wireframes the geometry the modifier deleted
cage_resolution  cage density, default 10
material  "clay" | ("attribute", attr_name[, "color"|"fac"])
expect    deform | verts_up | verts_down | topology | any | attribute:<name>
"""

# Params every deformer wants off so the gizmo/preview overlays stay out of
# the icon. Only applied where the socket actually exists.
import os

NO_OVERLAY = {"Show Center Gizmo": False, "Show Deformation Preview": False}


RECIPES = {

    # -- class 1: no prep at all -------------------------------------------
    "GN_Twist": dict(
        short="Twist",
        catalog="Deform",
        base="suzanne",
        prep=[("subsurf", 1), "shade_smooth"],
        params=dict(Axis="Z", Angle=2.6, Symmetry=False, **NO_OVERLAY),
        cage=True,
        expect="deform",
    ),

    # -- class 2: needs material slots + per-face material_index -----------
    "GN_Delete": dict(
        short="Delete",
        catalog="Modify",
        base="suzanne",
        prep=[("subsurf", 1), "shade_smooth",
              ("material_slots", 2),
              ("material_index_by", "half")],
        params={"Selection Mode": "Material ID", "Material ID": 1,
                "Domain": "Face"},
        ghost_wire="removed",
        expect="verts_down",
    ),

    # -- class 3: no geometry change at all; needs a viz material ----------
    # Suzanne is a weak AO subject (mostly convex, so most of the surface is
    # fully open) - the remap below is pushed hard to make the occlusion read.
    # A concave base would show it better at the cost of family consistency.
    "GN_AmbientOcclusion": dict(
        short="AO",
        catalog="Modify",
        base="suzanne",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Write To": "Colour Attribute", "Domain": "Point",
                "Colour Attribute": "AO", "Samples": 48, "Distance": 1.6,
                "Spread": 1.0, "Auto Range": False, "Input Min": 0.88,
                "Input Max": 1.0, "Blur Iterations": 1},
        material=("attribute", "AO", "color", "emission"),
        expect="attribute:AO",
    ),
    # ---- Deform: pure deformers, cage on, no prep beyond a smoothing pass ----
    "GN_Bend": dict(
        short="Bend",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params=dict(Angle=1.9, **{"Bend Axis": "X", "Bend Direction": "Z"},
                    **NO_OVERLAY),
        cage=True,
        expect="deform",
    ),

    "GN_Taper": dict(
        short="Taper",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params=dict(Axis="Z", Factor=0.75, Symmetry=False, **NO_OVERLAY),
        cage=True,
        expect="deform",
    ),

    "GN_Wave": dict(
        short="Wave",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        # Ripple travels along X only, offset applied on Z only.
        params=dict(Amplitude=0.30, Wavelength=2.0,
                    **{"Displace Along": "Z",
                       "Ripple X": 1.0, "Ripple Y": 0.0, "Ripple Z": 0.0,
                       "Affect X": 0.0, "Affect Y": 0.0, "Affect Z": 1.0},
                    **NO_OVERLAY),
        cage=True,
        expect="deform",
    ),

    # ---- Generate ------------------------------------------------------------
    # No pre-subdivision here: the point of the icon is the coarse cage becoming
    # a smooth surface, so the base has to stay low-poly and the original wire
    # is drawn over the result.
    "GN_Subdivide": dict(
        short="Subdivide",
        catalog="Generate",
        prep=["shade_smooth"],
        params={"Level": 2, "Smooth": True},
        ghost_wire="all",
        expect="verts_up",
    ),

    "GN_Wireframe": dict(
        short="Wireframe",
        catalog="Generate",
        prep=["shade_smooth"],
        params={"Thickness": 0.03, "Resolution": 4, "Fill Caps": True},
        expect="topology",
    ),

    "GN_ConvexHull": dict(
        short="Convex Hull",
        catalog="Generate",
        prep=[("subsurf", 1), "shade_smooth"],
        params={},
        expect="topology",
    ),

    # Class 3: needs an external object bound to an Object socket. The cutter
    # is placed to bite the SILHOUETTE - a cutter buried in the mesh leaves an
    # interior cavity whose flat-shaded far wall reads as a bulge, not a hole.
    "GN_MeshBoolean": dict(
        short="Boolean",
        catalog="Generate",
        prep=[("subsurf", 1), "shade_smooth"],
        helpers=[dict(name="cutter", base="icosphere",
                      base_args={"subdiv": 3, "r": 0.85},
                      location=(0.85, -0.25, 0.75))],
        params={"Cutter Object": "@cutter", "Operation": "Difference"},
        expect="topology",
    ),

    # ---- Scatter -------------------------------------------------------------
    "GN_PointsToSpheres": dict(
        short="Pt Spheres",
        catalog="Scatter",
        prep=["shade_smooth"],
        params={"Radius": 0.055, "Subdivisions": 2},
        expect="verts_up",
    ),
    # ---- batch 3 -------------------------------------------------------------
    "GN_Inflate": dict(
        short="Inflate",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Amount": 0.12},
        expect="deform",
    ),

    "GN_Smooth": dict(
        short="Smooth",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Iterations": 20, "Factor": 1.0},
        expect="deform",
    ),

    # Cast to a BOX, not the default sphere - a sphere cast just rounds the
    # subject off and reads as a generic blob.
    "GN_Cast": dict(
        short="Cast",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params=dict(Shape="Box", Factor=0.6, Radius=1.0, Axis="Z",
                    **NO_OVERLAY),
        cage=True,
        expect="deform",
    ),

    "GN_ShearGeometry": dict(
        short="Shear",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        # One shear axis driven by one mask axis - the group exposes exactly
        # one of each, so this is a single-axis shear.
        params=dict(**{"Shear Factor": 0.45, "Shear Axis": "X",
                       "Mask Axis": "Z", "Symmetry": False,
                       "Center Offset": 0.0}, **NO_OVERLAY),
        cage=True,
        expect="deform",
    ),

    # The box alone is an anonymous cube. Draw Suzanne solid inside it and the
    # box as wireframe only, so the icon shows what is being bounded.
    "GN_BoundingBox": dict(
        short="Bound Box",
        catalog="Generate",
        prep=[("subsurf", 1), "shade_smooth"],
        params={},
        keep_base=True,
        ghost_wire="result",
        wire_only=True,
        expect="topology",
    ),

    # Flat shaded and un-subdivided: the point is the new edge flow, and the
    # result wireframe is what actually shows it.
    "GN_Triangulate": dict(
        short="Triangulate",
        catalog="Generate",
        prep=[],
        params={},
        ghost_wire="result",
        expect="topology",
    ),

    "GN_VoxelRemesh": dict(
        short="Voxel Remesh",
        catalog="Generate",
        prep=["shade_smooth"],
        params={"Voxel Size": 0.09, "Adaptivity": 0.0},
        expect="topology",
    ),

    "GN_DualMesh": dict(
        short="Dual Mesh",
        catalog="Generate",
        prep=[],
        params={"Keep Boundaries": True},
        ghost_wire="result",
        expect="topology",
    ),

    # Class 2 variant: here the material split IS the subject of the icon, so
    # the helper material is tinted rather than clay.
    "GN_SetMaterial": dict(
        short="Set Material",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth", ("material_slots", 1)],
        helpers=[dict(name="mat", kind="material", colour=(0.85, 0.34, 0.24, 1.0))],
        params={"Material": "@mat", "Selection": True},
        expect="material",
    ),

    "GN_Scatter": dict(
        short="Scatter",
        catalog="Scatter",
        prep=["shade_smooth"],
        helpers=[dict(name="proto", base="icosphere",
                      base_args={"subdiv": 2, "r": 0.08},
                      location=(0.0, 0.0, 6.0))],
        params={"Instance Object": "@proto", "Density": 60.0, "Seed": 3,
                "Scale Min": 0.7, "Scale Max": 1.3, "Align to Normal": True},
        keep_base=True,
        expect="instances_up",
    ),
    # ---- batch 4 -------------------------------------------------------------
    "GN_Displace": dict(
        short="Displace",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Strength": 0.35, "Midlevel": 0.5, "Scale": 2.5,
                "Detail": 3.0, "Direction": "Normal"},
        expect="deform",
    ),

    # Erosion carves vertically, so it needs a surface with room to carve -
    # on Suzanne it has nothing to bite.
    "GN_Erosion": dict(
        short="Erosion",
        catalog="Deform",
        base="grid",
        base_args={"x": 48, "y": 48, "size": 2.0},
        prep=["shade_smooth"],
        params={"Scale": 1.3, "Erosion Strength": 1.0, "Along Axis": "X",
                "Detail Scale": 2.0, "Exponent": 0.5, "Distortion": 0.45,
                "Masking Axis": (0.0, 0.0, 0.0)},
        expect="deform",
    ),

    # Class 4: the Boundary Edges socket wants a per-edge field, which only an
    # attribute binding can express.
    "GN_FlattenByBoundary": dict(
        short="Flatten",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth",
              ("bool_attribute", "boundary", 'EDGE', "bands", 3)],
        params={"Boundary Edges": ("attr", "boundary"), "Factor": 1.0},
        expect="deform",
    ),

    "GN_NoiseDisplace": dict(
        short="Noise Disp",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Noise Scale": 2.0, "Overall Strength": 0.35,
                "Displace Along": "Normal", "Detail": 2.0,
                "Distortion": 0.4},
        expect="deform",
    ),

    "GN_RandomizeMeshElements": dict(
        short="Randomize",
        catalog="Deform",
        prep=["shade_smooth"],
        params={"Group By": "Face", "Seed": 4, "Affect Chance": 1.0,
                "Position Amount": (0.06, 0.06, 0.06),
                "Rotation Amount": (0.25, 0.25, 0.25),
                "Uniform Scale": True, "Scale Min": 0.55, "Scale Max": 0.85,
                "Pivot Point": "Element Center"},
        expect="any",
    ),

    "GN_RandomizePosition": dict(
        short="Rnd Position",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Direction": "Free (XYZ)", "Noise Type": "Perlin",
                "Amount": (0.12, 0.12, 0.12), "Scale": 4.0, "Seed": 2},
        expect="deform",
    ),

    # keep_base is what makes this legible: the framing recentres on whatever
    # it is given, so a pure transform would otherwise look like nothing moved.
    "GN_SimpleTransformMesh": dict(
        short="Transform",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Translation": (0.0, 0.0, 0.9), "Rotation": (0.0, 0.0, 0.6),
                "Scale": (0.75, 0.75, 0.75)},
        keep_base=True,
        expect="deform",
    ),

    "GN_Stretch": dict(
        short="Stretch",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params=dict(Axis="Z", Factor=1.7, **NO_OVERLAY),
        cage=True,
        expect="deform",
    ),

    "GN_VoronoiDisplace": dict(
        short="Voronoi Disp",
        catalog="Deform",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Noise Scale": 2.0, "Overall Strength": 0.35,
                "Displace Along": "Normal", "Blocking": 0.5,
                "Distortion": 0.3},
        expect="deform",
    ),

    # ---- Generate ------------------------------------------------------------
    # Class 2: extrude only the faces on the crown, for a punk-hair silhouette.
    "GN_ExtrudeFace": dict(
        short="Extrude",
        catalog="Generate",
        prep=[("subsurf", 1), "shade_smooth", ("material_slots", 2),
              ("material_index_by", "region", {"freq": 0.52, "axis": "z"})],
        params={"Select by Material Index": True,
                "Selection Material Index": 1,
                "Height": 0.45, "Individual": True, "Outer Faces": True,
                "Edge Offset": -0.018},
        expect="verts_up",
    ),

    "GN_RadialArray": dict(
        short="Radial Array",
        catalog="Generate",
        prep=["shade_smooth"],
        params={"Count": 6, "Radius": 1.6, "Axis": "Z"},
        expect="verts_up",
    ),

    "GN_TileableMeshNoise": dict(
        short="Tile Noise",
        catalog="Generate",
        base="grid",
        base_args={"x": 2, "y": 2, "size": 2.0},
        prep=[],
        params={"Cell Type": "Voronoi", "Cells X": 6, "Cells Y": 6,
                "Distortion Type": "Perlin", "Distortion": 0.75,
                "Cell Gap": 0.28, "Isolate Cells": True, "Seed": 1},
        expect="topology",
    ),

    # ---- Modify --------------------------------------------------------------
    # Left flat-shaded on purpose: auto smooth changes shading only, so the
    # icon has to start from something visibly faceted.
    "GN_AutoSmooth": dict(
        short="Auto Smooth",
        catalog="Modify",
        prep=[],
        params={"Angle": 0.7},
        expect="shading",
    ),

    # A two-sided material is what makes this visible at all - a flipped face
    # renders identically to an unflipped one otherwise, and culling the
    # backfaces just gives an unlit black silhouette.
    "GN_FlipFaces": dict(
        short="Flip Faces",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Selection": True},
        hollow=True,
        expect="shading",
    ),

    "GN_MaterialOverride": dict(
        short="Mat Override",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth", ("material_slots", 1)],
        helpers=[dict(name="mat", kind="material",
                      colour=(0.30, 0.55, 0.82, 1.0))],
        params={"On": True, "Material Override": "@mat"},
        expect="material",
    ),

    "GN_NormalTransfer": dict(
        short="Nrm Transfer",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth"],
        helpers=[dict(name="src", base="icosphere",
                      base_args={"subdiv": 3, "r": 1.4},
                      location=(0.0, 0.0, 0.0))],
        params={"Source Object": "@src", "Masking Mode": "None"},
        expect="shading",
    ),

    "GN_SplitEdgeByAttribute": dict(
        short="Split Edges",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth",
              ("bool_attribute", "split_here", 'EDGE', "bands", 3)],
        params={"Attribute Preset": "Custom",
                "Custom Attribute": "split_here",
                "Boundary of Face Group": False},
        expect="verts_up",
    ),

    "GN_Weld": dict(
        short="Weld",
        catalog="Modify",
        prep=["shade_smooth"],
        params={"Mode": "All", "Distance": 0.16},
        expect="verts_down",
    ),

    # Class 5: writes a colour attribute and changes no geometry. It targets
    # the standard "Color" attribute via its default preset, so that is what
    # the viz material reads.
    "GN_SetAttribute": dict(
        short="Set Attribute",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Convex": True, "Convex Threshold": 0.4,
                "XYZ/RGB Write": True, "Fill": False,
                "XYZ/RGB Attribute Value to Set": (0.88, 0.28, 0.18)},
        material=("attribute", "Color", "color", "clay"),
        expect="attribute:Color",
    ),

    # ---- batch 5: the heavy generators --------------------------------------
    # Same masking trap as GN_Erosion: the default axis vector evaluates to
    # zero on an unvaried surface and nothing erodes.
    "GN_Erosion_3D": dict(
        short="Erosion 3D",
        catalog="Deform",
        # Two subdivision levels, not one: the erosion is a fine displacement
        # and a coarse cage cannot carry it.
        prep=[("subsurf", 2), "shade_smooth"],
        params={"Scale Min": 2.2, "Scale Max": 2.8, "Erosion Strength": 2.5,
                "Menu": "X", "Detail Scale": 3.0, "Iterations": 6,
                "Weight": 1.5, "Masking Axis": (0.0, 0.0, 0.0)},
        expect="deform",
    ),

    # NB "Seed" appears three times in this group, so it cannot be bound by
    # name - use Scatter Seed, which is unique.
    "GN_CellFrac": dict(
        short="Fracture",
        catalog="Generate",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Cut Iterations": 14, "Crater Mode": "Uniform",
                "Scatter Pieces": True, "Scatter Seed": 3,
                "Random Position": (0.05, 0.05, 0.05),
                "Push Pull": 0.09, "Output Instances": False},
        expect="topology",
    ),

    # On a box, not Suzanne: it chips edges sharper than its auto angle, and a
    # subdivided Suzanne has almost none, so the damage read as random lumps.
    "GN_EdgeDestruct": dict(
        short="Edge Destruct",
        catalog="Generate",
        base="cube",
        base_args={"size": 1.6},
        prep=[],
        params={"Max Damage": 1.0, "Min Damage": 0.2, "Cuts": 2,
                "Voronoi Scale": 3.0, "Noise Scale": 2.0,
                "Corner Damage": True},
        expect="topology",
    ),

    # Shatter mode over Suzanne, keeping the source mesh underneath, per the
    # settings dialled in by hand. Grid mode needs a bounded surface; Shatter
    # skins an arbitrary mesh, so Suzanne works and stays on-family.
    "GN_Mosaic": dict(
        short="Mosaic",
        catalog="Generate",
        # No subdivision: the tile sizes above are absolute, so the plates read
        # at the scale they were dialled in against the base Suzanne.
        prep=["shade_smooth"],
        params={"Tiling Mode": "Shatter",
                "Tile Size": 0.08, "Tile Size Max": 0.26,
                "Gap": 0.015, "Gap Max": 0.0,
                "Scale Variation": 0.12, "Seed": 0,
                "Triangle Ratio": 0.25, "Grid Rotation": 0.0,
                "Irregularity": 0.15, "Position Jitter": 0.4,
                "Rotation Jitter": 0.06, "Region Rotation": 0.0,
                "Adaptive Levels": 2, "Adaptive Threshold": 1.0,
                "Fit Mode": "Center Inside", "Edge Margin": 0.0,
                "Fit Tiles To Boundary": False,
                "Shatter Levels": 7, "Max Corners": 5, "Tileable": False,
                "Tile Bounds": (2.0, 2.0, 2.0),
                "Split Chance": 0.361, "Split Jitter": 1.0,
                "Shatter Position Jitter": 0.0,
                "Shatter Rotation Jitter": 0.0,
                "Shatter Scale Jitter": 0.0,
                "Boundary Edges": False, "Use Open Edges": False,
                "Contour Rows": 0, "Contour Spacing": 1.0,
                "Projection Axis": "Object", "Conform To Surface": False,
                "Surface Offset": 0.0, "Thickness": 0.02,
                "Keep Source Mesh": False},
        expect="topology",
    ),

    "GN_RandomDistribute": dict(
        short="Rnd Distribute",
        catalog="Scatter",
        prep=["shade_smooth"],
        helpers=[dict(name="spawn", base="cylinder",
                      base_args={"verts": 8, "r": 0.05, "depth": 0.3},
                      location=(0.0, 0.0, 8.0))],
        params={"Surface Type": "Self Surface", "Add / Keep Surface": True,
                "Spawn Object": "@spawn", "Density": 30.0,
                "Density Multiplier": 1.0, "Distribution Seed": 4,
                "Uniform Scale Min": 0.7, "Uniform Scale Max": 1.3},
        expect="any",
    ),
    # The node targets the "Color" attribute but writes zeros for every
    # parameter set tried (see ICONS.md), so the icon is representational: a
    # convexity map authored in prep, split on a screen-space diagonal with the
    # far half hue-shifted - the same attribute arriving somewhere else. The
    # gate asserts only what the node verifiably does, which is create Color.
    "GN_AttributeTransfer": dict(
        short="Attr Transfer",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth", ("convexity_colour", "src")],
        params={"To Attribute Presets": "Color",
                "To Attribute Domain Type": "Vertex Point",
                "To Attribute Data Type": "Color"},
        material=("split", "src", 0.45),
        expect="attribute_added:Color",
    ),

    # ---- batch 6: the last of them ------------------------------------------
    # Mirror on Z without deleting the far half, so the icon shows the doubling
    # rather than an unchanged Suzanne.
    "GN_MirrorGroup": dict(
        short="Mirror Group",
        catalog="Generate",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"X Axis": False, "Y Axis": False, "Z Axis": True,
                "Delete Selection over Z": False, "Merge Mesh": False,
                "Use Mirror Object": False},
        expect="verts_up",
    ),

    "GN_CollectionInstancerModel": dict(
        short="Instancer",
        catalog="Scatter",
        base="plane",
        base_args={"size": 2.0},
        prep=[],
        helpers=[dict(name="coll", kind="collection", items=[
            dict(base="icosphere", base_args={"subdiv": 2, "r": 0.3}),
            dict(base="cylinder", base_args={"verts": 12, "r": 0.24,
                                             "depth": 0.55}),
        ])],
        params={"Instance Type": "Collection", "Collection": "@coll",
                "Realize All": True, "AutoGrid": True,
                "Base Grid Size X": 0.8, "Base Grid Size Y": 0.8,
                "Grid Amount X": 3, "Grid Amount Y": 3, "Seed": 5,
                "Scale Uniform": 1.0},
        expect="any",
    ),

    # Class 5. Writes local position into an RGB colour channel set, which is
    # the clearest thing this node does that an icon can show.
    "GN_VertexDataComposer": dict(
        short="Vertex Data",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Col 1 Name": "Col", "Col 1 Domain": "Vertex",
                "Col 1 Data Type": "Float Color",
                "Col 1 R Write": True,
                "Col 1 R Source": "Position (Bounds 0-1)",
                "Col 1 R Component": "X / Red / U",
                "Col 1 G Write": True,
                "Col 1 G Source": "Position (Bounds 0-1)",
                "Col 1 G Component": "Y / Green / V",
                "Col 1 B Write": True,
                "Col 1 B Source": "Position (Bounds 0-1)",
                "Col 1 B Component": "Z / Blue"},
        material=("attribute", "Col", "color", "emission"),
        expect="attribute:Col",
    ),

    # Needs a hole to close, so the prep cuts the crown off Suzanne. The cap is
    # tinted via the modifier's own Cap output and only ITS edges are wired, so
    # the all-quad grid - the point of the node - is what reads.
    "GN_QuadCap": dict(
        short="Quad Cap",
        catalog="Generate",
        prep=["shade_smooth", ("mark_open_boundary", "z", 0.42)],
        params={"Relax Iterations": 4, "Dome": 0.18,
                "Merge With Mesh": True, "Cap Loose Edge Loops": False},
        outputs={"Cap": "cap"},
        # The Cap flag never reaches the shader from the live modifier, so the
        # result is frozen and the flag re-written as a float from Python.
        promote={"cap": "cap_f"},
        material=("mask", "cap_f"),
        ghost_wire="attr:cap",
        expect="topology",
    ),

    # Grows a seed selection; the output is a flag, not geometry. The prep
    # marks a small seed patch, the modifier's Selection output is stored as
    # "grown", and both are drawn: seed in the full Modify tint over the region
    # it grew into in a lighter one. Selection Domain's menu default is empty,
    # so it has to be set explicitly.
    "GN_GrowSelection": dict(
        short="Grow Sel",
        catalog="Modify",
        prep=[("subsurf", 1), "shade_smooth",
              ("bool_attribute", "seed", 'FACE', "spot",
               {"centre": (0.0, -0.85, 0.25), "radius": 0.18})],
        params={"Selection": ("attr", "seed"), "Grow Iterations": 4,
                "Selection Domain": "Face"},
        outputs={"Selection": "grown"},
        promote={"grown": "grown_f", "seed": "seed_f"},
        material=("mask2", "seed_f", "grown_f"),
        expect="attribute:grown",
    ),

    # ---- ST3E/Shading: shader node groups ------------------------------------
    # Not modifiers - Suzanne wears a material instancing the group, set up
    # like each file's own demo material (group Color -> Principled Base
    # Color). Ridge/Valley are pushed past the demo's 1.0 so the effect holds
    # at icon size. These live in Blender/Shading, hence the relative path.
    "SH_Cavity": dict(
        short="Cavity",
        catalog="Shading",
        file="../Shading/SH_Cavity.blend",
        shader=True,
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Base Color": (0.62, 0.63, 0.66, 1.0),
                "World Ridge": 1.6, "World Valley": 1.6,
                "World Distance": 0.2,
                "Screen Ridge": 1.6, "Screen Valley": 1.6,
                "Screen Distance": 0.05},
        output="Color",
        into="base_color",
    ),

    # EEVEE, not Cycles: its curvature comes from the Bump node's screen-space
    # derivative (GLSL dFdx/dFdy). Cycles evaluates Bump by ray differentials,
    # where the trick is identically zero - the render matched plain clay to
    # four decimal places.
    "SH_ScreenCavity": dict(
        short="Screen Cavity",
        catalog="Shading",
        file="../Shading/SH_ScreenCavity.blend",
        shader=True,
        engine="EEVEE",
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Base Color": (0.62, 0.63, 0.66, 1.0),
                "Ridge": 1.6, "Valley": 1.6,
                "Curvature Scale": 2.0, "Distance Scaling": 0.0},
        output="Color",
        into="base_color",
    ),

    # ---- ST3E/Group: reusable node groups, not modifiers ---------------------
    "GNG_AmbientOcclusion": dict(
        short="AO Core",
        catalog="Group",
        file="GN_AmbientOcclusion.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GNG_Mirror": dict(
        short="Mirror",
        catalog="Group",
        file="GN_Mirror_Groupable.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GNG_MixAlpha": dict(
        short="Mix Alpha",
        catalog="Group",
        file="GN_AttributeFunctions_4.5.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GNG_MixRGBXYZValues": dict(
        short="Mix RGB/XYZ",
        catalog="Group",
        file="GN_AttributeFunctions_4.5.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GNG_SetAttributename": dict(
        short="Attr Name",
        catalog="Group",
        file="GN_AttributeFunctions_4.5.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GNG_StoreAttributeOnDomain": dict(
        short="Store Attr",
        catalog="Group",
        file="GN_AttributeFunctions_4.5.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GNG_TileableNoiseCoords": dict(
        short="Tile Coords",
        catalog="Group",
        file="SHG_TileableNoise.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GNG_VertexChannel": dict(
        short="Vtx Channel",
        catalog="Group",
        file="GN_VertexDataComposer.blend",
        base="nodegraph",
        emblem=True,
    ),

    # ---- catalogued later: new modifiers and helpers --------------------------
    # Despite the name it adds no faces: it pulls OPEN-BORDER vertices inward
    # by Offset (on stock Suzanne that is only the 42 eye-socket rim verts).
    # So the crown is cut off to give it a border worth seeing, and the gate
    # is `deform` - topology never changes.
    "GN_InsetFaces": dict(
        short="Inset",
        catalog="Generate",
        file="GN_InsetFace.blend",
        prep=[("subsurf", 1), "shade_smooth",
              ("mark_open_boundary", "z", 0.35)],
        params={"Offset": 0.22, "Selection": True},
        expect="deform",
    ),

    # Solidify on a closed mesh builds its shell out of sight, inside. Cutting
    # the crown off leaves a rim where the new thickness shows.
    "GN_Solidify2": dict(
        short="Solidify",
        catalog="Generate",
        file="GN_Solidify2.blend",
        prep=["shade_smooth", ("mark_open_boundary", "z", 0.3)],
        params={"Thickness": 0.12, "Offset": 0.5},
        expect="topology",
    ),

    # Key is the PNG filename, so it must be filesystem-safe - the real group
    # name contains a "/".
    "GN_ExpandContractSelection": dict(
        group="Expand / Contract Selection",
        short="Expand Sel",
        catalog="Group",
        file="GN_ExtrudeSelection.blend",
        base="nodegraph",
        emblem=True,
    ),

    "GN_Smooth Position": dict(
        short="Smooth Pos",
        catalog="Group",
        file="GN_ExtrudeSelection.blend",
        base="nodegraph",
        emblem=True,
    ),

    # SHG_* are SHADER helpers - they output coordinates, which mean nothing
    # shown raw. Feeding them into a Noise Texture shows what they are FOR: a
    # noise pattern laid out through their mapping.
    "SHG_TwistedTorusUV": dict(
        short="Torus UV",
        catalog="Group",
        file="SHG_TileableNoise.blend",
        shader=True,
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Vector": ("texcoord", "Object")},
        output="Vector",
        into="noise",
    ),

    "SHG_TileableNoiseUV": dict(
        short="Tile Noise UV",
        catalog="Group",
        file="SHG_TileableNoise.blend",
        shader=True,
        prep=[("subsurf", 1), "shade_smooth"],
        params={"Position Vector": ("texcoord", "Object"),
                "Tile Scale": (2.0, 2.0, 2.0),
                "Position": "Geometry Position"},
        output="Vector",
        into="noise",
    ),
}


# Group name -> source .blend, where the file is not named after the group.
FILE_OVERRIDES = {
    "GN_SimpleTransformMesh": "GN_SimpleTransform.blend",
    "GN_SplitEdgeByAttribute": "GN_SplitByAttribute.blend",
    "GN_ExtrudeFace": "GN_ExtrudeSelection.blend",
    "GN_Mirror": "GN_Mirror_Groupable.blend",
    "GN_MirrorGroup": "GN_Mirror_Groupable.blend",
    "GN_MaterialOverride": "GN_CollectionInstancer.blend",
    "GN_CollectionInstancerModel": "GN_CollectionInstancer.blend",
    "GN_SetAttribute": "GN_AttributeFunctions_4.5.blend",
    "GN_AttributeTransfer": "GN_AttributeFunctions_4.5.blend",
    "GN_EdgeDestruct": "GN_EdgeDestruct_fixed.blend",
}


def source_file(group):
    return FILE_OVERRIDES.get(group, group + ".blend")


def group_of(key):
    """The node-group datablock a recipe renders; the key is only an icon id."""
    return RECIPES[key].get("group", key)


def files_of(key):
    """Every .blend this recipe's icon is embedded into."""
    rec = RECIPES[key]
    first = rec.get("file", source_file(group_of(key)))
    return [first] + list(rec.get("also_embed", []))


def covered():
    """{(group, file basename): recipe key} for everything that gets an icon."""
    return {(group_of(k), os.path.basename(f)): k
            for k in RECIPES for f in files_of(k)}
