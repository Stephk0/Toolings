"""Build GN_Mosaic.blend -- a Geometry Nodes MODIFIER that fills the areas of a mesh
with mosaic tesserae (square + triangular tiles), bounded by edge loops.

The user paints/marks edges (`Boundary Edges`, attribute-bindable) and/or lets the
mesh's own OPEN edges act as walls. Those walls cut the surface into REGIONS
(connected components); every region is packed with tiles that stop at its outline,
however organic that outline is.

Pipeline (one frame per stage in the node tree):

  Selection  -> fillable surface (Separate Geometry, FACE)
  Boundary   -> marked edges  OR  open edges (Edge Neighbors.Face Count < 2)
  Regions    -> Split Edges by boundary -> Mesh Island -> Sample Index back onto the
                ORIGINAL faces = per-face region id, stored on the raycast "canvas"
  Frame      -> projection axis (Auto avg-normal / X / Y / Z / Object empty) + grid
                rotation -> an orthonormal (T, B, N) basis
  Domain     -> extent of the surface measured along T and B -> grid size & counts
  Lattice    -> Grid mesh, vertices warped by `Irregularity` -> organic quad cells
  Shapes     -> a `Triangle Ratio` fraction of cells is triangulated (two passes with
                opposite diagonals so the split direction varies)
  Variation  -> every tile is separated (Split Edges), then scaled to leave the grout
                `Gap`, size/rotation-jittered and nudged inside its cell
  Fit        -> a raycast down the projection axis tests each tile vertex AND the tile
                centre against the surface; `Fit Mode` picks centre-inside /
                fully-inside / any-overlap, `Edge Margin` pushes tiles off the outline
  Contour    -> boundary edges -> curve -> resampled by tile pitch -> N rows of tiles
                following the outline (opus vermiculatum); the grid fill is culled out
                of that band automatically
  ShVariation-> the shattered tiles get the same per-island wobble the grid tiles do
                (turn / shrink / slide about their own centroid), opt-in and scaled by
                the grout so the exact partition survives; seam tiles sit it out
  Cut        -> optional: vertices hanging outside the region are snapped onto the
                nearest boundary point, so border tiles read as cut stone
  Conform    -> tiles are dropped onto the real surface (curved geometry supported)
  Attributes -> tile_id (unique INT per tile), region_id, tile_random, tile_color

Run headless:
  "C:\\Program Files\\Blender Foundation\\Blender 5.0\\blender.exe" --background \
      --factory-startup --python build_gn_mosaic.py
"""
import bpy, bmesh, sys, os, math
from mathutils import Vector

GEO  = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes"
NAME = "GN_Mosaic"
PATH = os.path.join(GEO, NAME + ".blend")
CAT  = "8872522f-45b7-4541-a557-5b69bcbfcee2"          # ST3E/Generate catalog
                                                       # (the flat ST3E root holds no
                                                       #  direct assets since the
                                                       #  2026-07-20 sub-catalog split)

# internal (non user-facing) attribute names used to carry data between stages
A_REGION = "__mos_region"      # FACE  INT   on the canvas: which region a face belongs to
A_TRI    = "__mos_tri"         # FACE  FLOAT per-cell random deciding square vs triangle
A_DIAG   = "__mos_diag"        # FACE  FLOAT per-cell random deciding the triangle diagonal
A_TILE   = "__mos_tile"        # FACE  FLOAT per-tile id, read back per-vertex after splitting
A_V  = ["__mos_v%d" % k for k in range(6)]   # shatter tile corners, up to six
A_T  = ["__mos_t%d" % k for k in range(6)]   # scratch copy while corners are rewritten
A_NC = "__mos_nc"                            # how many of them are real
A_MI, A_MJ = "__mos_mi", "__mos_mj"
A_N1, A_N2 = "__mos_n1", "__mos_n2"          # corner count of each child          # the two cut points
A_BI, A_BD = "__mos_bi", "__mos_bd"          # cut edge index, and how far round to the second
A_SS = "__mos_ss"                            # split decision
A_SEAM = "__mos_seam"          # POINT FLOAT 1 where a tile corner sits on the bounds box
A_ROW    = "__mos_row"         # POINT FLOAT contour row distance, carried across the resample
A_TAN    = "__mos_tangent"     # POINT VEC   outline tangent, kept across Duplicate Elements

# ----------------------------------------------------------------------------- helpers
def _pick(sockets, key):
    """Socket by index / identifier / display name, preferring the ENABLED variant.
    Multi-type nodes keep disabled same-name sockets whose links silently no-op."""
    if isinstance(key, int):
        return sockets[key]
    # ENABLED first, both by identifier AND by name, before ever looking at a
    # disabled socket: Random Value keeps a disabled 'Min'/'Value' for every data
    # type it is not set to, and linking one of those no-ops silently at eval time.
    for pred in (lambda s: s.enabled and s.identifier == key,
                 lambda s: s.enabled and s.name == key,
                 lambda s: s.identifier == key,
                 lambda s: s.name == key):
        for s in sockets:
            if pred(s):
                return s
    raise KeyError(key)
def osock(node, key): return _pick(node.outputs, key)
def isock(node, key): return _pick(node.inputs,  key)

# ----------------------------------------------------------------------------- clean slate
for grp in list(bpy.data.node_groups):
    if grp.name == NAME:
        bpy.data.node_groups.remove(grp)

ng = bpy.data.node_groups.new(NAME, "GeometryNodeTree")
nodes, links = ng.nodes, ng.links
def link(a, ai, b, bi): links.new(osock(a, ai), isock(b, bi))

# ============================================================================= INTERFACE
iface = ng.interface
def sock(name, in_out, stype, parent=None, default=None, mn=None, mx=None,
         subtype=None, desc=""):
    s = iface.new_socket(name, in_out=in_out, socket_type=stype, parent=parent)
    if default is not None: s.default_value = default
    if mn is not None:      s.min_value = mn
    if mx is not None:      s.max_value = mx
    if subtype:             s.subtype = subtype
    s.description = desc
    return s

sock("Geometry", 'INPUT', 'NodeSocketGeometry',
     desc="Surface to tile. Needs FACES -- the faces are the canvas the tiles are "
          "fitted onto; the edges you mark are the walls that bound them.")

sock("Selection", 'INPUT', 'NodeSocketBool', default=True,
     desc="Faces eligible for tiling. The border of this selection also acts as a "
          "boundary, so you can tile part of a surface without marking any edge.")


p_tile = iface.new_panel("Tiles")
sock("Tiling Mode", 'INPUT', 'NodeSocketMenu', parent=p_tile,
     desc="How the tiles are generated. Grid lays a rotated lattice over the surface "
          "and keeps the cells that fit -- regular courses of tesserae. Shatter instead "
          "SUBDIVIDES each bounded region itself, splitting it again and again along its "
          "longest edge, so the tiles partition the shape exactly: every outline, corner "
          "and hole is formed by real tile edges, with no strip left over and nothing "
          "clipped. Shatter produces triangles only, in mixed sizes.")
sock("Tile Size", 'INPUT', 'NodeSocketFloat', parent=p_tile, default=0.1, mn=0.0001,
     subtype='DISTANCE',
     desc="Width of one tessera. Together with Gap this sets the grid pitch, so it "
          "also decides how many tiles are generated.")
sock("Gap", 'INPUT', 'NodeSocketFloat', parent=p_tile, default=0.015, mn=0.0,
     subtype='DISTANCE',
     desc="Grout width between neighbouring tiles. In Grid mode tiles are shrunk inside "
          "their cell by this amount, so the pitch stays Tile Size + Gap. In Shatter "
          "mode each tile is inset by half of it, making every joint exactly this wide. "
          "Keep it well below Tile Size there -- a tile with no room left for its own "
          "grout is nothing but grout, and is dropped rather than folded inside out.")
sock("Scale Variation", 'INPUT', 'NodeSocketFloat', parent=p_tile, default=0.12,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Random size difference between tiles, as a fraction of Tile Size.")
sock("Seed", 'INPUT', 'NodeSocketInt', parent=p_tile, default=0,
     desc="Randomisation seed. Drives every random in the tool -- cell shapes, "
          "triangle choice, jitter and the per-tile colour.")

p_grid = iface.new_panel("Grid")
sock("Triangle Ratio", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=0.25,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Fraction of cells split into two TRIANGULAR tiles instead of staying a "
          "square. 0 = all squares, 1 = all triangles. The diagonal alternates "
          "randomly so the split direction is not uniform.")
sock("Grid Rotation", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=0.0,
     subtype='ANGLE',
     desc="Rotates the whole tile grid around the projection axis -- the direction the "
          "courses of tiles run in.")
sock("Irregularity", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=0.15,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Warps the lattice corners before the tiles are cut, so cells become "
          "irregular quads/triangles instead of a perfect grid. Capped at 45% of a "
          "cell, so cells can never fold over each other.")
sock("Position Jitter", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=0.4,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Nudges each tile inside its own cell. Scaled by the Gap, so tiles can "
          "never collide however high you push it.")
sock("Rotation Jitter", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=0.06,
     subtype='ANGLE',
     desc="Random rotation of each tile about the projection axis, plus/minus this "
          "angle. A few degrees is enough to kill the machine-made look.")
sock("Region Rotation", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=0.0,
     subtype='ANGLE',
     desc="Extra random rotation shared by every tile of the SAME region, up to this "
          "angle. Makes each bounded shape read as its own patch of stonework. Note "
          "it turns the tiles in place; the underlying grid stays global.")
sock("Adaptive Levels", 'INPUT', 'NodeSocketInt', parent=p_grid, default=2, mn=0, mx=4,
     desc="Lets the tiles change size to suit the room they have: any cell that is too "
          "big for the space left between the walls is split into four, up to this many "
          "times. Tile Size then reads as the LARGEST tile -- open ground keeps it, "
          "narrow necks and tight corners get halves, quarters and so on, which is how "
          "a real mosaic negotiates an awkward shape. 0 = one uniform size everywhere.")
sock("Adaptive Threshold", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=1.0,
     mn=0.0, mx=4.0,
     desc="How eagerly cells split. A cell splits when the nearest wall is closer than "
          "this many cell-widths, so higher values shrink tiles over a wider band around "
          "every boundary. 0 disables splitting even with Adaptive Levels set.")
sock("Fit Mode", 'INPUT', 'NodeSocketMenu', parent=p_grid,
     desc="How a tile straddling a wall is judged. Center Inside keeps it when its "
          "centre is in the region, so tiles may overhang by up to half a tile. Fully "
          "Inside keeps only tiles lying entirely within ONE region -- whole tiles "
          "only, which by definition leaves a tile-wide strip along every wall "
          "unfilled; fill that strip with Contour Rows, or use Any Overlap together "
          "with Cut Tiles At Boundary. Any Overlap keeps anything touching the region. "
          "Note the three agree once Contour Rows is 1 or more, because the reserved "
          "band already guarantees a whole tile fits.")
sock("Edge Margin", 'INPUT', 'NodeSocketFloat', parent=p_grid, default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="Keeps tiles this far away from the boundary walls, widening the grout line "
          "that runs along the outline.")
sock("Fit Tiles To Boundary", 'INPUT', 'NodeSocketBool', parent=p_grid, default=False,
     desc="Reshapes the tiles that meet a wall so their edge follows the outline "
          "instead of crossing it: any corner lying outside its region -- or closer to "
          "the wall than Boundary Gap -- is moved onto the Boundary Gap line, measured "
          "from the real boundary, so even an organic curve comes out cleanly cut. "
          "Works on interior walls as well as the silhouette. Pair with Fit Mode = Any "
          "Overlap for a mosaic that reaches the edge of the shape.")

p_sh = iface.new_panel("Shatter")
sock("Shatter Levels", 'INPUT', 'NodeSocketInt', parent=p_sh, default=7, mn=0, mx=12,
     desc="How many times a region may be split in Shatter mode. Splitting stops on its "
          "own once a tile reaches Tile Size, so this is a safety ceiling rather than a "
          "dial -- raise it if large shapes stay coarse, lower it to cap the tile count.")
sock("Max Corners", 'INPUT', 'NodeSocketInt', parent=p_sh, default=4, mn=3, mx=6,
     desc="Largest number of sides a shattered tile may have. 3 keeps the classic "
          "all-triangle break-up; 4 lets a cut run between opposite edges so quads "
          "survive as quads and triangles turn into a triangle plus a quad; 5 and 6 "
          "allow pentagons and hexagons, giving the loose polygonal paving of opus "
          "palladianum. Input faces with more corners than this are triangulated first.")
sock("Tileable", 'INPUT', 'NodeSocketBool', parent=p_sh, default=False,
     desc="Makes the break-up repeat seamlessly across a box of Tile Bounds. Any tile "
          "edge lying on a face of that box is treated as a seam and keeps HALF the "
          "ordinary Gap instead of the Boundary Gap, so two copies laid side by side "
          "meet with exactly one Gap between them, indistinguishable from every other "
          "joint. A cut may also START or END on a seam vertex but never introduces a "
          "NEW one, so the seam keeps exactly the subdivision your input mesh gave it -- "
          "which is what holds the two faces together at any Split Jitter. The spacing "
          "of tiles ALONG a seam therefore comes from the input mesh: subdivide it more "
          "finely for a finer border. Tiles touching a seam also sit out the Shatter "
          "jitter below, since the tile on the far face is a different shape and no "
          "rigid nudge could keep both in register. Your mesh must fill the box for any "
          "of this to mean anything.")
sock("Tile Bounds", 'INPUT', 'NodeSocketVector', parent=p_sh, default=(2.0, 2.0, 2.0),
     subtype='TRANSLATION',
     desc="Size of the repeating box, centred on the object origin -- 2,2,2 means one "
          "metre out to each side. Only used while Tileable is on.")
sock("Split Chance", 'INPUT', 'NodeSocketFloat', parent=p_sh, default=0.75,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Chance that an oversized tile actually splits on any given pass. At 1 every "
          "tile is worked down to Tile Size and the result is fairly even; lower it and "
          "some pieces are left large while their neighbours keep breaking up, which is "
          "what gives real cut stonework its mix of big slabs and small fragments.")
sock("Split Jitter", 'INPUT', 'NodeSocketFloat', parent=p_sh, default=0.5,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="How far off centre each cut lands on the edge it splits. 0 halves every tile "
          "exactly and the result looks mechanical; higher values give the uneven, "
          "hand-broken shapes of real cut stone.")

p_bnd = iface.new_panel("Boundary")
sock("Boundary Edges", 'INPUT', 'NodeSocketBool', parent=p_bnd, default=False,
     desc="Edge selection marking the walls of the mosaic areas. Bind it to an edge "
          "attribute (the dot next to the field) and mark the loops in Edit Mode. "
          "Each closed loop carves the surface into its own region with its own "
          "region id -- loops may be organic, of any size, and nested.")
sock("Use Open Edges", 'INPUT', 'NodeSocketBool', parent=p_bnd, default=True,
     desc="Also treat the mesh's own open (unshared) edges as boundary walls -- the "
          "outline of a flat shape and the rim of any hole in it. Lets a cut-out "
          "silhouette be tiled without marking a single edge.")
sock("Boundary Gap", 'INPUT', 'NodeSocketFloat', parent=p_bnd, default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="Grout width left along the boundary walls themselves, as opposed to the Gap "
          "between neighbouring tiles. In Grid mode the contour rows start this far in "
          "and tiles fitted to the boundary stop on this line. In Shatter mode the tiles "
          "meeting a wall are inset from it by exactly this much, while their shared "
          "edges keep the ordinary Gap. Keep it well under Tile Size: a gap approaching "
          "the size of the tiles simply eats the ones along the edge, and those are "
          "dropped rather than folded inside out.")

p_con = iface.new_panel("Contour Rows")
sock("Contour Rows", 'INPUT', 'NodeSocketInt', parent=p_con, default=1, mn=0, mx=8,
     desc="Rows of tiles that FOLLOW the walls instead of the grid (opus vermiculatum "
          "-- the band that makes a mosaic read as hand-laid). They run along the "
          "outline of every region, so they are also what fills the strip the grid "
          "cannot reach; the grid is culled out of the band they occupy, and the two "
          "never overlap. 0 = off.")
sock("Contour Spacing", 'INPUT', 'NodeSocketFloat', parent=p_con, default=1.0,
     mn=0.1, mx=4.0,
     desc="Stretches the spacing of the contour tiles along the wall without changing "
          "their size: 1 lays them end to end with the Gap between, above 1 opens the "
          "joints up, below 1 crowds them together.")
sock("Contour Length", 'INPUT', 'NodeSocketFloat', parent=p_con, default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="Length of a contour tile measured ALONG the wall. 0 follows Tile Size; raise "
          "it for long brick-like tesserae running with the outline.")
sock("Contour Width", 'INPUT', 'NodeSocketFloat', parent=p_con, default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="Width of a contour tile measured ACROSS the wall -- also the spacing between "
          "one contour row and the next. 0 follows Tile Size; lower it for a fine border "
          "of thin tesserae around a coarser field.")
sock("Contour Triangle Ratio", 'INPUT', 'NodeSocketFloat', parent=p_con, default=0.0,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Fraction of contour tiles split into two triangles, the same way Triangle "
          "Ratio works on the grid fill. 0 keeps the border purely rectangular, which "
          "is the traditional look.")

p_prj = iface.new_panel("Projection")
sock("Projection Axis", 'INPUT', 'NodeSocketMenu', parent=p_prj,
     desc="Axis the tile grid is projected along -- the 'up' of the mosaic plane. "
          "Auto uses the surface's own area-weighted average normal, so a tilted or "
          "curved patch just works. Object takes the local +Z of an empty.")
sock("Direction Object", 'INPUT', 'NodeSocketObject', parent=p_prj,
     desc="Empty whose local +Z gives the projection axis when Projection Axis is set "
          "to Object.")
sock("Conform To Surface", 'INPUT', 'NodeSocketBool', parent=p_prj, default=True,
     desc="Drops every tile vertex onto the real surface along the projection axis, so "
          "the mosaic follows curved geometry. Off = all tiles stay on one flat plane.")
sock("Surface Offset", 'INPUT', 'NodeSocketFloat', parent=p_prj, default=0.0,
     subtype='DISTANCE',
     desc="Lifts the tiles off the surface along its normal. Use a small value to stop "
          "z-fighting when the source mesh is kept.")

p_out = iface.new_panel("Output")
sock("Material", 'INPUT', 'NodeSocketMaterial', parent=p_out,
     desc="Material assigned to the tiles. Geometry built by a node tree carries no "
          "material of its own, so without this the tesserae render with Blender's "
          "default grey -- set it here and read the tile attributes inside it.")
sock("Thickness", 'INPUT', 'NodeSocketFloat', parent=p_out, default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="Extrudes every tile into a solid slab of this height. 0 keeps them flat "
          "(cheapest).")
sock("Keep Source Mesh", 'INPUT', 'NodeSocketBool', parent=p_out, default=False,
     desc="Outputs the original surface underneath the tiles as a backing/grout layer "
          "instead of replacing it.")
sock("Tile ID Attribute", 'INPUT', 'NodeSocketString', parent=p_out, default="tile_id",
     desc="Name of the INT face attribute holding each tile's UNIQUE id. Read it in a "
          "material (Attribute node) to colour every tessera individually.")
sock("Region ID Attribute", 'INPUT', 'NodeSocketString', parent=p_out,
     default="region_id",
     desc="Name of the INT face attribute holding the id of the bounded region a tile "
          "sits in -- use it to give each shape its own palette.")
sock("Tile Random Attribute", 'INPUT', 'NodeSocketString', parent=p_out,
     default="tile_random",
     desc="Name of the FLOAT face attribute holding a stable random 0..1 per tile. The "
          "quickest hook for colour/roughness variation in a material.")
sock("Tile Color Attribute", 'INPUT', 'NodeSocketString', parent=p_out,
     default="tile_color",
     desc="Name of the COLOR face attribute holding a random RGB per tile, ready to "
          "plug straight into a shader or to remap through a colour ramp.")

sock("Geometry", 'OUTPUT', 'NodeSocketGeometry',
     desc="The mosaic tiles. Every tile is a separate face island carrying its own "
          "tile_id / region_id / tile_random / tile_color.")

# --- Shatter per-tile variation ------------------------------------------------------
# Declared AFTER the output on purpose. Interface identifiers are handed out in creation
# order (Socket_0, Socket_1, ...), so inserting these in the middle of the Shatter panel
# would renumber every socket below them and silently re-point the overrides already
# saved on existing modifiers. Created last, they get fresh numbers; the move_to_parent
# calls underneath put them where they belong in the UI without touching identifiers.
sock("Shatter Position Jitter", 'INPUT', 'NodeSocketFloat', default=0.0,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Nudges each shattered tessera off the exact partition, the way Position "
          "Jitter loosens the grid. The room it has to move in is the grout it just "
          "opened, so the offset is scaled by the Gap and tiles can never collide "
          "however high you push it -- and at Gap 0 there is nowhere to go, which is "
          "what keeps the exact-coverage partition intact. Tiles meeting a wall can "
          "drift across it, so give Boundary Gap some room if that matters. 0.3-0.5 "
          "reads as hand-laid.")
sock("Shatter Rotation Jitter", 'INPUT', 'NodeSocketFloat', default=0.0, mn=0.0,
     subtype='ANGLE',
     desc="Turns each shattered tessera in place about its own centre, plus/minus this "
          "angle. You get exactly the angle you ask for, at any Gap. Note that a tile "
          "turning in place needs more room than one sliding does, and Shatter mixes "
          "tile sizes on purpose, so past a few degrees the bigger tesserae will start "
          "to overlap their neighbours -- widen the Gap to buy room, or keep the angle "
          "small. A couple of degrees already kills the machine-cut look.")
sock("Tile Size Max", 'INPUT', 'NodeSocketFloat', default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="Upper end of a tile SIZE RANGE. Leave at 0 (or anything at or below Tile "
          "Size) and every tessera targets Tile Size as before; raise it above Tile "
          "Size and each one draws its own target somewhere between the two, which is "
          "what stops a mosaic reading as a manufactured sheet. Grid mode spaces the "
          "lattice for the LARGEST tile and shrinks each tessera to its own size inside "
          "that cell, so the smaller ones simply sit in more grout; Shatter splits each "
          "piece down to its own target, so the range changes the break-up itself. "
          "Scale Variation still applies on top as a percentage wobble.")
sock("Gap Max", 'INPUT', 'NodeSocketFloat', default=0.0, mn=0.0, subtype='DISTANCE',
     desc="Upper end of a GROUT RANGE. At 0 (or anything at or below Gap) every joint "
          "is exactly Gap wide as before; above it, each joint draws its own width "
          "between the two. In Shatter the draw is per EDGE and both tiles sharing it "
          "agree, so the joint stays even along its length -- and it stays in register "
          "across a Tileable seam. In Grid the draw is per TILE.")
sock("Boundary Gap Max", 'INPUT', 'NodeSocketFloat', default=0.0, mn=0.0,
     subtype='DISTANCE',
     desc="Upper end of a range for the grout along the WALLS, exactly as Gap Max is "
          "for the grout between tiles -- a ragged, hand-cut edge instead of a machined "
          "setback. Shatter only: in Grid the Boundary Gap is a single setback line that "
          "the fit test and the contour band are both measured against, so it has to "
          "stay one number there.")
sock("Shatter Scale Jitter", 'INPUT', 'NodeSocketFloat', default=0.0,
     mn=0.0, mx=1.0, subtype='FACTOR',
     desc="Shrinks each shattered tessera by a random fraction of its own size, up to "
          "this much, so some pieces sit looser in their grout than others -- stone cut "
          "slightly small rather than machined to fit. Unlike the other two this is NOT "
          "tied to the Gap, so any value above 0 gives up the exact-coverage partition "
          "by design.")

# ...and now file them under Shatter, after Split Jitter. Purely a UI move: the
# identifiers minted above travel with the sockets.
_by_name = {i.name: i for i in iface.items_tree if i.item_type == 'SOCKET'}
for _pos, _nm in enumerate(("Shatter Position Jitter", "Shatter Rotation Jitter",
                            "Shatter Scale Jitter")):
    iface.move_to_parent(_by_name[_nm], p_sh, 6 + _pos)
# the size/grout ranges sit next to the values they cap
iface.move_to_parent(_by_name["Tile Size Max"], p_tile, 2)   # after Tile Size
iface.move_to_parent(_by_name["Gap Max"], p_tile, 4)         # after Gap, which the
                                                             # previous move pushed down
iface.move_to_parent(_by_name["Boundary Gap Max"], p_bnd, 3)  # after Boundary Gap

# socket name constants (interface display names -- Group Input output identifiers)
S_GEO, S_SEL      = "Geometry", "Selection"
S_BND, S_OPEN     = "Boundary Edges", "Use Open Edges"
S_TSZ, S_GAP      = "Tile Size", "Gap"
S_TSZM, S_GAPM    = "Tile Size Max", "Gap Max"
S_BGAPM           = "Boundary Gap Max"
S_TRI, S_SEED     = "Triangle Ratio", "Seed"
S_GROT, S_IRR     = "Grid Rotation", "Irregularity"
S_PJIT, S_RJIT    = "Position Jitter", "Rotation Jitter"
S_SVAR, S_RROT    = "Scale Variation", "Region Rotation"
S_FIT, S_MARG     = "Fit Mode", "Edge Margin"
S_BGAP, S_CUT     = "Boundary Gap", "Fit Tiles To Boundary"
S_ROWS, S_CSPC    = "Contour Rows", "Contour Spacing"
S_CLEN, S_CWID    = "Contour Length", "Contour Width"
S_CTRI            = "Contour Triangle Ratio"
S_ALVL, S_ATHR    = "Adaptive Levels", "Adaptive Threshold"
S_TMODE           = "Tiling Mode"
S_SLVL, S_SJIT    = "Shatter Levels", "Split Jitter"
S_MAXC            = "Max Corners"
S_SPJ, S_SRJ      = "Shatter Position Jitter", "Shatter Rotation Jitter"
S_SSJ             = "Shatter Scale Jitter"
S_TILE, S_TBND    = "Tileable", "Tile Bounds"
S_SCHN            = "Split Chance"
S_AXIS, S_DOBJ    = "Projection Axis", "Direction Object"
S_CONF, S_SOFF    = "Conform To Surface", "Surface Offset"
S_MAT             = "Material"
S_THK, S_KEEP     = "Thickness", "Keep Source Mesh"
S_NTID, S_NREG    = "Tile ID Attribute", "Region ID Attribute"
S_NRND, S_NCOL    = "Tile Random Attribute", "Tile Color Attribute"

gin  = nodes.new("NodeGroupInput");  gin.location  = (-3600, 0)
gout = nodes.new("NodeGroupOutput"); gout.location = (5200, 0)

# ============================================================================= FRAMES
def frame(label, color=(0.18, 0.20, 0.26)):
    f = nodes.new("NodeFrame"); f.label = label; f.location = (0, 0)
    f.use_custom_color = True; f.color = color
    return f

F_surf = frame("Fillable Surface")
F_bnd  = frame("Boundary Walls  (marked edges OR open edges)")
F_reg  = frame("Regions  (split by walls -> per-face region id)")
F_axis = frame("Projection Axis")
F_frm  = frame("Plane Basis  (T / B / N + grid rotation)")
F_dom  = frame("Grid Domain  (surface extent in the plane)")
F_lat  = frame("Tile Lattice  (grid + irregularity)")
F_adapt = frame("Adaptive Tile Size  (split cells that crowd a wall)")
F_shp  = frame("Square / Triangle Tiles")
F_var  = frame("Per-Tile Variation  (gap, scale, rotation, jitter)")
F_fitm = frame("Fit Test  (raycast containment + margin)")
F_cull = frame("Cull Tiles By Fit Mode")
F_seed = frame("Shatter Seed  (region triangles -> one point per tile)")
F_splt = frame("Shatter Split  (recursive longest-edge bisection)")
F_bld  = frame("Shatter Build  (points -> triangles + uniform grout)")
F_shvar = frame("Shatter Variation  (per-tile scale / rotation / jitter)")
F_cont = frame("Contour Rows  (tiles following the outline)")
F_cut  = frame("Cut Tiles At Boundary")
F_cnf  = frame("Conform To Surface")
F_attr = frame("Tile Attributes  (id / region / random / colour)")
F_fin  = frame("Thickness + Output")

def seam_edge(pa, pak, pb, pbk, parent, x, y):
    """True when both ends of an edge sit on the SAME face of the tile-bounds box.
    Those edges are the seams: they carry the interior grout instead of the boundary
    one, and any cut on them is placed from the wrapped coordinate so the opposite
    face gets the identical split."""
    half = vmath('SCALE', parent, (x, y + 260))
    link(gin, S_TBND, half, "Vector"); isock(half, "Scale").default_value = 0.5
    hs = mk("ShaderNodeSeparateXYZ", parent, (x + 180, y + 260)); link(half, "Vector", hs, "Vector")
    sa = mk("ShaderNodeSeparateXYZ", parent, (x, y + 130)); link(pa, pak, sa, "Vector")
    sb = mk("ShaderNodeSeparateXYZ", parent, (x, y)); link(pb, pbk, sb, "Vector")
    axes = []
    for i, k in enumerate("XYZ"):
        yy = y - i * 150
        lim = mth('SUBTRACT', parent, (x + 360, yy), v2=1e-4); link(hs, k, lim, "Value")
        aa = mth('ABSOLUTE', parent, (x + 360, yy - 60)); link(sa, k, aa, "Value")
        ab = mth('ABSOLUTE', parent, (x + 360, yy - 120)); link(sb, k, ab, "Value")
        oa = cmp('GREATER_THAN', 'FLOAT', parent, (x + 540, yy))
        link(aa, "Value", oa, "A"); link(lim, "Value", oa, "B")
        ob = cmp('GREATER_THAN', 'FLOAT', parent, (x + 540, yy - 70))
        link(ab, "Value", ob, "A"); link(lim, "Value", ob, "B")
        both = boolm('AND', parent, (x + 720, yy))
        link(oa, "Result", both, 0); link(ob, "Result", both, 1)
        prod = mth('MULTIPLY', parent, (x + 540, yy - 140)); link(sa, k, prod, "Value"); link(sb, k, prod, "Value_001")
        same = cmp('GREATER_THAN', 'FLOAT', parent, (x + 720, yy - 140))
        link(prod, "Value", same, "A"); isock(same, "B").default_value = 0.0
        ax = boolm('AND', parent, (x + 900, yy))
        link(both, "Boolean", ax, 0); link(same, "Result", ax, 1)
        axes.append(ax)
    o1 = boolm('OR', parent, (x + 1080, y))
    link(axes[0], "Boolean", o1, 0); link(axes[1], "Boolean", o1, 1)
    o2 = boolm('OR', parent, (x + 1260, y))
    link(o1, "Boolean", o2, 0); link(axes[2], "Boolean", o2, 1)
    on = boolm('AND', parent, (x + 1440, y))
    link(o2, "Boolean", on, 0); link(gin, S_TILE, on, 1)
    return on

def range_hi(base_key, max_key, parent, loc):
    """Upper end of a `value .. value Max` range. A Max at or below the base collapses
    the range to the base, so 0 means 'no range' for every one of these sockets and the
    tool behaves exactly as it did before the range existed."""
    hi = mth('MAXIMUM', parent, loc)
    link(gin, base_key, hi, "Value"); link(gin, max_key, hi, "Value_001")
    return hi


def range_pick(base_key, hi, idnode, idkey, seed_off, parent, loc):
    """One draw from `base .. hi`, keyed on a per-element id so it is stable."""
    x, y = loc
    sd = mth('ADD', parent, (x, y - 120), v2=float(seed_off))
    link(gin, S_SEED, sd, "Value")
    r = rnd('FLOAT', parent, (x + 180, y))
    link(idnode, idkey, r, "ID"); link(sd, "Value", r, "Seed")
    link(gin, base_key, r, "Min"); link(hi, "Value", r, "Max")
    return r


def range_pick_at(base_key, hi, vnode, vkey, offset, parent, loc):
    """Same draw, but keyed on a POSITION instead of an id -- White Noise makes it a pure
    function of the point, so two tiles asking about the same shared edge get the same
    answer and the joint stays even along its length."""
    x, y = loc
    off = vmath('ADD', parent, (x, y), v2=offset); link(vnode, vkey, off, "Vector")
    wn = mk("ShaderNodeTexWhiteNoise", parent, (x + 180, y), noise_dimensions='3D')
    link(off, "Vector", wn, "Vector")
    span = mth('SUBTRACT', parent, (x + 180, y - 160))
    link(hi, "Value", span, "Value"); link(gin, base_key, span, "Value_001")
    scaled = mth('MULTIPLY', parent, (x + 360, y - 160))
    link(wn, "Value", scaled, "Value"); link(span, "Value", scaled, "Value_001")
    out = mth('ADD', parent, (x + 540, y - 80))
    link(gin, base_key, out, "Value"); link(scaled, "Value", out, "Value_001")
    return out


def seam_vert(pnode, pkey, parent, x, y):
    """True when a single vertex sits on a face of the tile-bounds box (Tileable only).
    seam_edge() answers the same question for an edge; this is the per-vertex form, and
    it is what stops the variation stage from dragging a seam out of register."""
    half = vmath('SCALE', parent, (x, y + 200))
    link(gin, S_TBND, half, "Vector"); isock(half, "Scale").default_value = 0.5
    hs = mk("ShaderNodeSeparateXYZ", parent, (x + 180, y + 200)); link(half, "Vector", hs, "Vector")
    sp = mk("ShaderNodeSeparateXYZ", parent, (x + 180, y)); link(pnode, pkey, sp, "Vector")
    axes = []
    for i, k in enumerate("XYZ"):
        yy = y - i * 130
        lim = mth('SUBTRACT', parent, (x + 360, yy), v2=1e-4); link(hs, k, lim, "Value")
        av = mth('ABSOLUTE', parent, (x + 360, yy - 60)); link(sp, k, av, "Value")
        hit = cmp('GREATER_THAN', 'FLOAT', parent, (x + 540, yy))
        link(av, "Value", hit, "A"); link(lim, "Value", hit, "B")
        axes.append(hit)
    o1 = boolm('OR', parent, (x + 720, y))
    link(axes[0], "Result", o1, 0); link(axes[1], "Result", o1, 1)
    o2 = boolm('OR', parent, (x + 900, y))
    link(o1, "Boolean", o2, 0); link(axes[2], "Result", o2, 1)
    on = boolm('AND', parent, (x + 1080, y))
    link(o2, "Boolean", on, 0); link(gin, S_TILE, on, 1)
    return on


def wrapped_mid(pa, pak, pb, pbk, parent, x, y):
    """midpoint of an edge folded into the bounds box -- opposite faces land together"""
    add = vmath('ADD', parent, (x, y)); link(pa, pak, add, "Vector"); link(pb, pbk, add, "Vector_001")
    mid = vmath('SCALE', parent, (x + 180, y)); link(add, "Vector", mid, "Vector")
    isock(mid, "Scale").default_value = 0.5
    ms = mk("ShaderNodeSeparateXYZ", parent, (x + 360, y)); link(mid, "Vector", ms, "Vector")
    half = vmath('SCALE', parent, (x + 180, y - 200))
    link(gin, S_TBND, half, "Vector"); isock(half, "Scale").default_value = 0.5
    hs = mk("ShaderNodeSeparateXYZ", parent, (x + 360, y - 200)); link(half, "Vector", hs, "Vector")
    comb = mk("ShaderNodeCombineXYZ", parent, (x + 900, y))
    for i, k in enumerate("XYZ"):
        neg = mth('MULTIPLY', parent, (x + 540, y - 260 - i * 90), v2=-1.0); link(hs, k, neg, "Value")
        w = mth('WRAP', parent, (x + 720, y - i * 90))
        link(ms, k, w, "Value"); link(hs, k, w, "Value_001"); link(neg, "Value", w, "Value_002")
        link(w, "Value", comb, k)
    return comb

def mk(idname, parent=None, loc=(0, 0), **props):
    nd = nodes.new(idname)
    for k, v in props.items(): setattr(nd, k, v)
    if parent: nd.parent = parent
    nd.location = loc
    return nd

# small builders --------------------------------------------------------------
def mth(op, parent, loc, v1=None, v2=None):
    nd = mk("ShaderNodeMath", parent, loc, operation=op)
    if v1 is not None: isock(nd, "Value").default_value = v1
    if v2 is not None: isock(nd, "Value_001").default_value = v2
    return nd
def vmath(op, parent, loc, v2=None):
    nd = mk("ShaderNodeVectorMath", parent, loc, operation=op)
    if v2 is not None: isock(nd, "Vector_001").default_value = v2
    return nd
def cmp(op, dtype, parent, loc):
    return mk("FunctionNodeCompare", parent, loc, data_type=dtype, operation=op)
def boolm(op, parent, loc):
    return mk("FunctionNodeBooleanMath", parent, loc, operation=op)
def switch(dtype, parent, loc):
    return mk("GeometryNodeSwitch", parent, loc, input_type=dtype)
def named(dtype, parent, loc, name):
    nd = mk("GeometryNodeInputNamedAttribute", parent, loc, data_type=dtype)
    isock(nd, "Name").default_value = name
    return nd
def store(geo_from, geo_key, dtype, domain, parent, loc, name=None):
    nd = mk("GeometryNodeStoreNamedAttribute", parent, loc,
            data_type=dtype, domain=domain)
    link(geo_from, geo_key, nd, "Geometry")
    if name is not None: isock(nd, "Name").default_value = name
    return nd
def rnd(dtype, parent, loc):
    return mk("FunctionNodeRandomValue", parent, loc, data_type=dtype)
def vrot(parent, loc):
    return mk("ShaderNodeVectorRotate", parent, loc, rotation_type='AXIS_ANGLE')
def pos_node(parent, loc): return mk("GeometryNodeInputPosition", parent, loc)
def idx_node(parent, loc): return mk("GeometryNodeInputIndex", parent, loc)

# ============================================================================= 1. SURFACE
# The Selection border doubles as a wall: separating first means the open-edge test
# below automatically picks up the rim of whatever the user selected.
sep = mk("GeometryNodeSeparateGeometry", F_surf, (-3300, 300), domain='FACE')
link(gin, S_GEO, sep, "Geometry"); link(gin, S_SEL, sep, "Selection")

# ============================================================================= 2. BOUNDARY
en    = mk("GeometryNodeInputMeshEdgeNeighbors", F_bnd, (-3300, 0))
isOpen = cmp('LESS_THAN', 'INT', F_bnd, (-3120, 20))
link(en, "Face Count", isOpen, "A_INT"); isock(isOpen, "B_INT").default_value = 2
openOn = boolm('AND', F_bnd, (-2940, 20))
link(isOpen, "Result", openOn, 0); link(gin, S_OPEN, openOn, 1)
wall   = boolm('OR', F_bnd, (-2760, 20))
link(openOn, "Boolean", wall, 0); link(gin, S_BND, wall, 1)

# ============================================================================= 3. REGIONS
# Splitting the walls turns every bounded area into its own connected component.
# Face indices survive Split Edges, so sampling the island index BY FACE INDEX carries
# the region id back onto the unsplit surface without keeping the split copy.
splt = mk("GeometryNodeSplitEdges", F_reg, (-2560, 200))
link(sep, "Selection", splt, "Mesh"); link(wall, "Boolean", splt, "Selection")
isl  = mk("GeometryNodeInputMeshIsland", F_reg, (-2560, 40))
fidx = idx_node(F_reg, (-2560, -80))
regId = mk("GeometryNodeSampleIndex", F_reg, (-2360, 120),
           data_type='INT', domain='FACE')
link(splt, "Mesh", regId, "Geometry")
link(isl, "Island Index", regId, "Value"); link(fidx, "Index", regId, "Index")
# the raycast target: the fillable surface carrying its region ids
canvas = store(sep, "Selection", 'INT', 'FACE', F_reg, (-2160, 200), A_REGION)
link(regId, "Value", canvas, "Value")
# boundary walls as standalone edge geometry -- used for every distance-to-outline test
bndGeo = mk("GeometryNodeSeparateGeometry", F_reg, (-2160, -60), domain='EDGE')
link(sep, "Selection", bndGeo, "Geometry"); link(wall, "Boolean", bndGeo, "Selection")

# ============================================================================= 4. AXIS
# Auto = area-weighted average face normal of the fillable surface.
nrm  = mk("GeometryNodeInputNormal", F_axis, (-3300, -520))
area = mk("GeometryNodeInputMeshFaceArea", F_axis, (-3300, -660))
nw   = vmath('SCALE', F_axis, (-3120, -560))
link(nrm, "True Normal", nw, "Vector"); link(area, "Area", nw, "Scale")
nstat = mk("GeometryNodeAttributeStatistic", F_axis, (-2940, -560),
           data_type='FLOAT_VECTOR', domain='FACE')
link(sep, "Selection", nstat, "Geometry"); link(nw, "Vector", nstat, "Attribute")
autoN = vmath('NORMALIZE', F_axis, (-2740, -560))
link(nstat, "Sum", autoN, "Vector")

# Object = the empty's local +Z
oinfo = mk("GeometryNodeObjectInfo", F_axis, (-2940, -860), transform_space='RELATIVE')
link(gin, S_DOBJ, oinfo, "Object")
objN  = mk("FunctionNodeRotateVector", F_axis, (-2740, -860))
isock(objN, "Vector").default_value = (0.0, 0.0, 1.0)
link(oinfo, "Rotation", objN, "Rotation")

axMenu = mk("GeometryNodeMenuSwitch", F_axis, (-2540, -420), data_type='INT')
_it = axMenu.enum_definition.enum_items
_it[0].name = "Auto"; _it[1].name = "X"
for nm in ("Y", "Z", "Object"): _it.new(nm)
for i in range(5): isock(axMenu, f"Item_{i}").default_value = i
link(gin, S_AXIS, axMenu, "Menu")

axPick = mk("GeometryNodeIndexSwitch", F_axis, (-2360, -560), data_type='VECTOR')
for _ in range(3): axPick.index_switch_items.new()          # 2 stock + 3 = 5 items
link(axMenu, "Output", axPick, "Index")
link(autoN, "Vector", axPick, "Item_0")
isock(axPick, "Item_1").default_value = (1.0, 0.0, 0.0)
isock(axPick, "Item_2").default_value = (0.0, 1.0, 0.0)
isock(axPick, "Item_3").default_value = (0.0, 0.0, 1.0)
link(objN, "Vector", axPick, "Item_4")

# ============================================================================= 5. BASIS
# N (plane normal), then T rotated around N by Grid Rotation, then B = N x T.
axLen = vmath('LENGTH', F_frm, (-2160, -560))
link(axPick, "Output", axLen, "Vector")
axOk  = cmp('GREATER_THAN', 'FLOAT', F_frm, (-1990, -560))
link(axLen, "Value", axOk, "A"); isock(axOk, "B").default_value = 1e-5
axSafe = switch('VECTOR', F_frm, (-1810, -560))            # degenerate axis -> world Z
link(axOk, "Result", axSafe, "Switch")
isock(axSafe, "False").default_value = (0.0, 0.0, 1.0)
link(axPick, "Output", axSafe, "True")
N = vmath('NORMALIZE', F_frm, (-1630, -560))
link(axSafe, "Output", N, "Vector")

nsep = mk("ShaderNodeSeparateXYZ", F_frm, (-1450, -700))
link(N, "Vector", nsep, "Vector")
nzAbs = mth('ABSOLUTE', F_frm, (-1280, -700)); link(nsep, "Z", nzAbs, "Value")
nzUp  = cmp('GREATER_THAN', 'FLOAT', F_frm, (-1110, -700))
link(nzAbs, "Value", nzUp, "A"); isock(nzUp, "B").default_value = 0.9
ref   = switch('VECTOR', F_frm, (-930, -700))              # reference not parallel to N
link(nzUp, "Result", ref, "Switch")
isock(ref, "False").default_value = (0.0, 0.0, 1.0)
isock(ref, "True").default_value  = (1.0, 0.0, 0.0)

T0 = vmath('CROSS_PRODUCT', F_frm, (-750, -640))
link(ref, "Output", T0, "Vector"); link(N, "Vector", T0, "Vector_001")
T0n = vmath('NORMALIZE', F_frm, (-570, -640)); link(T0, "Vector", T0n, "Vector")
Trot = vrot(F_frm, (-390, -640))
link(T0n, "Vector", Trot, "Vector"); link(N, "Vector", Trot, "Axis")
link(gin, S_GROT, Trot, "Angle")
T = vmath('NORMALIZE', F_frm, (-210, -640)); link(Trot, "Vector", T, "Vector")
B = vmath('CROSS_PRODUCT', F_frm, (-210, -800))
link(N, "Vector", B, "Vector"); link(T, "Vector", B, "Vector_001")
# the shared "cast straight down onto the surface" direction, used by every raycast
down = vmath('SCALE', F_frm, (-210, -960))
link(N, "Vector", down, "Vector"); isock(down, "Scale").default_value = -1.0

# rotation that maps the local grid plane (XY) onto the world plane
planeRot = mk("FunctionNodeAxesToRotation", F_frm, (-30, -700),
              primary_axis='Z', secondary_axis='X')
link(N, "Vector", planeRot, "Primary Axis"); link(T, "Vector", planeRot, "Secondary Axis")

# ============================================================================= 6. DOMAIN
bb = mk("GeometryNodeBoundBox", F_dom, (-2160, 620))
link(sep, "Selection", bb, "Geometry")
bbSum = vmath('ADD', F_dom, (-1980, 660))
link(bb, "Min", bbSum, "Vector"); link(bb, "Max", bbSum, "Vector_001")
center = vmath('SCALE', F_dom, (-1800, 660))
link(bbSum, "Vector", center, "Vector"); isock(center, "Scale").default_value = 0.5
bbDiag = vmath('SUBTRACT', F_dom, (-1980, 500))
link(bb, "Max", bbDiag, "Vector"); link(bb, "Min", bbDiag, "Vector_001")
diagLen = vmath('LENGTH', F_dom, (-1800, 500)); link(bbDiag, "Vector", diagLen, "Vector")
rayLen = mth('ADD', F_dom, (-1620, 500), v2=1.0)          # ray start height above the plane
link(diagLen, "Value", rayLen, "Value")
rayLen2 = mth('MULTIPLY', F_dom, (-1450, 500), v2=2.0)    # ray length (down through it)
link(rayLen, "Value", rayLen2, "Value")

# cell pitch = biggest tile the size range allows + Gap  (clamped so it can never be
# zero). The lattice has to hold the LARGEST tessera; the smaller draws then shrink
# inside their own cell and sit in correspondingly more grout, which is how a real
# mosaic mixes sizes without leaving a hole.
tszHi = range_hi(S_TSZ, S_TSZM, F_dom, (-1800, 1040))
pitch0 = mth('ADD', F_dom, (-1620, 900))
link(tszHi, "Value", pitch0, "Value"); link(gin, S_GAP, pitch0, "Value_001")
cell = mth('MAXIMUM', F_dom, (-1450, 900), v2=1e-4)
link(pitch0, "Value", cell, "Value")

# contour tiles carry their own size; 0 on either socket falls back to Tile Size
cwOn = cmp('GREATER_THAN', 'FLOAT', F_cont, (5260, 620))
link(gin, S_CWID, cwOn, "A"); isock(cwOn, "B").default_value = 1e-6
cw = switch('FLOAT', F_cont, (5440, 620))                 # width ACROSS the wall
link(cwOn, "Result", cw, "Switch")
link(gin, S_TSZ, cw, "False"); link(gin, S_CWID, cw, "True")
clOn = cmp('GREATER_THAN', 'FLOAT', F_cont, (5260, 440))
link(gin, S_CLEN, clOn, "A"); isock(clOn, "B").default_value = 1e-6
cl = switch('FLOAT', F_cont, (5440, 440))                 # length ALONG the wall
link(clOn, "Result", cl, "Switch")
link(gin, S_TSZ, cl, "False"); link(gin, S_CLEN, cl, "True")
# pitch along the wall: tile length plus grout, stretched by Contour Spacing
pitchC0 = mth('ADD', F_cont, (5620, 440))
link(cl, "Output", pitchC0, "Value"); link(gin, S_GAP, pitchC0, "Value_001")
pitchC = mth('MULTIPLY', F_cont, (5620, 700))
link(pitchC0, "Value", pitchC, "Value"); link(gin, S_CSPC, pitchC, "Value_001")
pitchC2 = mth('MAXIMUM', F_cont, (5800, 700), v2=1e-4)
link(pitchC, "Value", pitchC2, "Value")
# spacing from one row to the next
rowPitch0 = mth('ADD', F_cont, (5620, 260))
link(cw, "Output", rowPitch0, "Value"); link(gin, S_GAP, rowPitch0, "Value_001")
rowPitch = mth('MAXIMUM', F_cont, (5800, 260), v2=1e-5)
link(rowPitch0, "Value", rowPitch, "Value")

# surface extent measured along T and along B
posD = pos_node(F_dom, (-1620, 260))
dVec = vmath('SUBTRACT', F_dom, (-1450, 300))
link(posD, "Position", dVec, "Vector"); link(center, "Vector", dVec, "Vector_001")
uDot = vmath('DOT_PRODUCT', F_dom, (-1270, 340))
link(dVec, "Vector", uDot, "Vector"); link(T, "Vector", uDot, "Vector_001")
vDot = vmath('DOT_PRODUCT', F_dom, (-1270, 180))
link(dVec, "Vector", vDot, "Vector"); link(B, "Vector", vDot, "Vector_001")
uStat = mk("GeometryNodeAttributeStatistic", F_dom, (-1090, 380),
           data_type='FLOAT', domain='POINT')
link(sep, "Selection", uStat, "Geometry"); link(uDot, "Value", uStat, "Attribute")
vStat = mk("GeometryNodeAttributeStatistic", F_dom, (-1090, 120),
           data_type='FLOAT', domain='POINT')
link(sep, "Selection", vStat, "Geometry"); link(vDot, "Value", vStat, "Attribute")

def grid_axis(stat, y):
    """size (extent + 2 cells of headroom) and vertex count for one grid axis"""
    size = mth('ADD', F_dom, (-880, y))
    link(stat, "Range", size, "Value")
    pad = mth('MULTIPLY', F_dom, (-880, y - 130), v2=2.0)
    link(cell, "Value", pad, "Value")
    link(pad, "Value", size, "Value_001")
    cnt0 = mth('DIVIDE', F_dom, (-700, y))
    link(size, "Value", cnt0, "Value"); link(cell, "Value", cnt0, "Value_001")
    cnt1 = mth('CEIL', F_dom, (-540, y)); link(cnt0, "Value", cnt1, "Value")
    cnt2 = mth('ADD', F_dom, (-380, y), v2=1.0); link(cnt1, "Value", cnt2, "Value")
    cnt3 = mth('MINIMUM', F_dom, (-220, y), v2=400.0)     # hard ceiling: 400x400 cells
    link(cnt2, "Value", cnt3, "Value")
    cnt4 = mth('MAXIMUM', F_dom, (-60, y), v2=2.0)
    link(cnt3, "Value", cnt4, "Value")
    # centre of the extent along this axis, so the grid sits over the surface
    mid0 = mth('ADD', F_dom, (-880, y - 260))
    link(stat, "Min", mid0, "Value"); link(stat, "Max", mid0, "Value_001")
    mid = mth('MULTIPLY', F_dom, (-700, y - 260), v2=0.5)
    link(mid0, "Value", mid, "Value")
    return size, cnt4, mid

uSize, uCnt, uMid = grid_axis(uStat, 420)
vSize, vCnt, vMid = grid_axis(vStat, -120)

# grid origin in world space = bbox centre shifted to the middle of the measured extent
offU = vmath('SCALE', F_dom, (120, 380))
link(T, "Vector", offU, "Vector"); link(uMid, "Value", offU, "Scale")
offV = vmath('SCALE', F_dom, (120, 220))
link(B, "Vector", offV, "Vector"); link(vMid, "Value", offV, "Scale")
gridOrg0 = vmath('ADD', F_dom, (300, 300))
link(center, "Vector", gridOrg0, "Vector"); link(offU, "Vector", gridOrg0, "Vector_001")
gridOrg = vmath('ADD', F_dom, (480, 300))
link(gridOrg0, "Vector", gridOrg, "Vector"); link(offV, "Vector", gridOrg, "Vector_001")

# ============================================================================= 7. LATTICE
grid = mk("GeometryNodeMeshGrid", F_lat, (700, 700))
link(uSize, "Value", grid, "Size X"); link(vSize, "Value", grid, "Size Y")
link(uCnt, "Value", grid, "Vertices X"); link(vCnt, "Value", grid, "Vertices Y")

# warp the lattice corners -> organic cells (capped at 45% of a cell = fold-free)
vIdx = idx_node(F_lat, (700, 460))
warpR = rnd('FLOAT_VECTOR', F_lat, (880, 500))
isock(warpR, "Min").default_value = (-1.0, -1.0, 0.0)
isock(warpR, "Max").default_value = (1.0, 1.0, 0.0)
link(vIdx, "Index", warpR, "ID"); link(gin, S_SEED, warpR, "Seed")
warpA0 = mth('MULTIPLY', F_lat, (880, 300), v2=0.45)
link(cell, "Value", warpA0, "Value")
warpA = mth('MULTIPLY', F_lat, (1050, 300))
link(warpA0, "Value", warpA, "Value"); link(gin, S_IRR, warpA, "Value_001")
warpV = vmath('SCALE', F_lat, (1220, 460))
link(warpR, "Value", warpV, "Vector"); link(warpA, "Value", warpV, "Scale")
warped = mk("GeometryNodeSetPosition", F_lat, (1400, 640))
link(grid, "Mesh", warped, "Geometry"); link(warpV, "Vector", warped, "Offset")

# --- adaptive sizing ---------------------------------------------------------
# Tiles earn their size from the room they have. Each pass splits every cell that is
# still too big for the space between it and the nearest wall into four, so open ground
# keeps full-size tesserae while necks, corners and thin slivers get progressively
# smaller ones -- the way a real mosaic negotiates an awkward shape. The randoms below
# are stored AFTER this, keyed on the final face index, so every sub-cell gets its own
# triangle/diagonal draw rather than inheriting its parent's.
rin = mk("GeometryNodeRepeatInput", F_adapt, (1500, 900))
rout = mk("GeometryNodeRepeatOutput", F_adapt, (2560, 900))
rin.pair_with_output(rout)
link(warped, "Geometry", rin, "Geometry")
link(gin, S_ALVL, rin, "Iterations")

aArea = mk("GeometryNodeInputMeshFaceArea", F_adapt, (1500, 620))
aCell = mth('SQRT', F_adapt, (1680, 620)); link(aArea, "Area", aCell, "Value")
aThr = mth('MULTIPLY', F_adapt, (2040, 700))
link(aCell, "Value", aThr, "Value"); link(gin, S_ATHR, aThr, "Value_001")
aPos = pos_node(F_adapt, (1500, 420))                   # FACE context -> cell centre
# the lattice is still in its own flat space here -- the walls are not, so the cell
# centre has to be carried onto the world plane before anything is measured against them
aRot = mk("FunctionNodeRotateVector", F_adapt, (1500, 260))
link(aPos, "Position", aRot, "Vector"); link(planeRot, "Rotation", aRot, "Rotation")
aWorld = vmath('ADD', F_adapt, (1680, 260))
link(aRot, "Vector", aWorld, "Vector"); link(gridOrg, "Vector", aWorld, "Vector_001")
aProx = mk("GeometryNodeProximity", F_adapt, (1860, 420), target_element='EDGES')
link(bndGeo, "Selection", aProx, "Target"); link(aWorld, "Vector", aProx, "Source Position")
aTight = cmp('LESS_THAN', 'FLOAT', F_adapt, (2040, 520))
link(aProx, "Distance", aTight, "A"); link(aThr, "Value", aTight, "B")
aWall = boolm('AND', F_adapt, (2220, 520))              # no walls -> nothing to adapt to
link(aTight, "Result", aWall, 0); link(aProx, "Is Valid", aWall, 1)
aUp = vmath('SCALE', F_adapt, (1680, 220))
link(N, "Vector", aUp, "Vector"); link(rayLen, "Value", aUp, "Scale")
aSrc = vmath('ADD', F_adapt, (1860, 100))
link(aWorld, "Vector", aSrc, "Vector"); link(aUp, "Vector", aSrc, "Vector_001")
aRc = mk("GeometryNodeRaycast", F_adapt, (2040, 260))   # don't refine cells off the mesh
link(canvas, "Geometry", aRc, "Target Geometry")
link(aSrc, "Vector", aRc, "Source Position")
link(down, "Vector", aRc, "Ray Direction")
link(rayLen2, "Value", aRc, "Ray Length")
aRefine = boolm('AND', F_adapt, (2220, 340))
link(aWall, "Boolean", aRefine, 0); link(aRc, "Is Hit", aRefine, 1)

aSep = mk("GeometryNodeSeparateGeometry", F_adapt, (2040, 900), domain='FACE')
link(rin, "Geometry", aSep, "Geometry"); link(aRefine, "Boolean", aSep, "Selection")
aSub = mk("GeometryNodeSubdivideMesh", F_adapt, (2220, 980))
link(aSep, "Selection", aSub, "Mesh"); isock(aSub, "Level").default_value = 1
aJoin = mk("GeometryNodeJoinGeometry", F_adapt, (2400, 900))
link(aSub, "Mesh", aJoin, "Geometry"); link(aSep, "Inverted", aJoin, "Geometry")
link(aJoin, "Geometry", rout, "Geometry")

# per-cell randoms, stored BEFORE triangulation so both halves of a split cell keep them
cIdx = idx_node(F_lat, (1400, 340))
triR = rnd('FLOAT', F_lat, (1580, 400))
link(cIdx, "Index", triR, "ID")
seedTri = mth('ADD', F_lat, (1400, 200), v2=11.0); link(gin, S_SEED, seedTri, "Value")
link(seedTri, "Value", triR, "Seed")
diagR = rnd('FLOAT', F_lat, (1580, 180))
link(cIdx, "Index", diagR, "ID")
seedDiag = mth('ADD', F_lat, (1400, 40), v2=23.0); link(gin, S_SEED, seedDiag, "Value")
link(seedDiag, "Value", diagR, "Seed")
stTri = store(rout, "Geometry", 'FLOAT', 'FACE', F_lat, (2760, 640), A_TRI)
link(triR, "Value", stTri, "Value")
stDiag = store(stTri, "Geometry", 'FLOAT', 'FACE', F_lat, (1960, 640), A_DIAG)
link(diagR, "Value", stDiag, "Value")

# ============================================================================= 8. SHAPES
# Two Triangulate passes with opposite fixed diagonals -> the split direction varies.
aTri  = named('FLOAT', F_shp, (2140, 400), A_TRI)
aDiag = named('FLOAT', F_shp, (2140, 260), A_DIAG)
isTri = cmp('LESS_THAN', 'FLOAT', F_shp, (2320, 400))
link(aTri, "Attribute", isTri, "A"); link(gin, S_TRI, isTri, "B")
dLow  = cmp('LESS_THAN', 'FLOAT', F_shp, (2320, 240))
link(aDiag, "Attribute", dLow, "A"); isock(dLow, "B").default_value = 0.5
notD = boolm('NOT', F_shp, (2500, 100)); link(dLow, "Result", notD, 0)
selA = boolm('AND', F_shp, (2680, 400))       # triangulate, diagonal one way ...
link(isTri, "Result", selA, 0); link(dLow, "Result", selA, 1)
selB = boolm('AND', F_shp, (2680, 200))       # ... and the other
link(isTri, "Result", selB, 0); link(notD, "Boolean", selB, 1)

triA = mk("GeometryNodeTriangulate", F_shp, (2880, 640))
link(stDiag, "Geometry", triA, "Mesh"); link(selA, "Boolean", triA, "Selection")
isock(triA, "Quad Method").default_value = "Fixed"
triB = mk("GeometryNodeTriangulate", F_shp, (2900, 640))
link(triA, "Mesh", triB, "Mesh"); link(selB, "Boolean", triB, "Selection")
isock(triB, "Quad Method").default_value = "Fixed Alternate"

# every tile becomes its own island so it can be transformed on its own
loose = mk("GeometryNodeSplitEdges", F_shp, (3100, 640))
link(triB, "Mesh", loose, "Mesh")
tIdx = idx_node(F_shp, (3100, 420))
stTile = store(loose, "Mesh", 'FLOAT', 'FACE', F_shp, (3280, 640), A_TILE)
link(tIdx, "Index", stTile, "Value")

# place the lattice onto the world plane
placed = mk("GeometryNodeTransform", F_shp, (3460, 640))
link(stTile, "Geometry", placed, "Geometry")
link(gridOrg, "Vector", placed, "Translation")
link(planeRot, "Rotation", placed, "Rotation")

# ============================================================================= 9. VARIATION
# per-tile centroid: each tile is an island, so accumulate position by island index
islV = mk("GeometryNodeInputMeshIsland", F_var, (3460, 200))
posV = pos_node(F_var, (3460, 60))
accC = mk("GeometryNodeAccumulateField", F_var, (3640, 220),
          data_type='FLOAT', domain='POINT')
isock(accC, "Value").default_value = 1.0
link(islV, "Island Index", accC, "Group Index")
accP = mk("GeometryNodeAccumulateField", F_var, (3640, 60),
          data_type='FLOAT_VECTOR', domain='POINT')
link(posV, "Position", accP, "Value"); link(islV, "Island Index", accP, "Group Index")
cntV = mk("ShaderNodeCombineXYZ", F_var, (3820, 220))
for k in ("X", "Y", "Z"): link(accC, "Total", cntV, k)
centroid = vmath('DIVIDE', F_var, (4000, 120))
link(accP, "Total", centroid, "Vector"); link(cntV, "Vector", centroid, "Vector_001")

tileId = named('FLOAT', F_var, (3460, -80), A_TILE)          # exact per-vertex (1 face/vert)

# region under the tile centre -- also drives the per-region rotation
upC = vmath('SCALE', F_var, (3640, -220))
link(N, "Vector", upC, "Vector"); link(rayLen, "Value", upC, "Scale")
srcC = vmath('ADD', F_var, (3820, -160))
link(centroid, "Vector", srcC, "Vector"); link(upC, "Vector", srcC, "Vector_001")
regAttr = named('INT', F_var, (3820, -420), A_REGION)
rcC = mk("GeometryNodeRaycast", F_var, (4000, -260), data_type='INT')
isock(rcC, "Interpolation").default_value = "Nearest"
link(canvas, "Geometry", rcC, "Target Geometry")
link(regAttr, "Attribute", rcC, "Attribute")
link(srcC, "Vector", rcC, "Source Position")
link(down, "Vector", rcC, "Ray Direction")
link(rayLen2, "Value", rcC, "Ray Length")

# random rotation / scale / offset, all keyed on the tile id (stable under reseeding)
sdRot = mth('ADD', F_var, (4180, 520), v2=53.0); link(gin, S_SEED, sdRot, "Value")
rRot  = rnd('FLOAT', F_var, (4360, 560))
link(tileId, "Attribute", rRot, "ID"); link(sdRot, "Value", rRot, "Seed")
rjNeg = mth('MULTIPLY', F_var, (4180, 680), v2=-1.0); link(gin, S_RJIT, rjNeg, "Value")
link(rjNeg, "Value", rRot, "Min"); link(gin, S_RJIT, rRot, "Max")

sdReg = mth('ADD', F_var, (4180, 380), v2=97.0); link(gin, S_SEED, sdReg, "Value")
rReg  = rnd('FLOAT', F_var, (4360, 400))
link(rcC, "Attribute", rReg, "ID"); link(sdReg, "Value", rReg, "Seed")
rrNeg = mth('MULTIPLY', F_var, (4180, 240), v2=-1.0); link(gin, S_RROT, rrNeg, "Value")
link(rrNeg, "Value", rReg, "Min"); link(gin, S_RROT, rReg, "Max")
angle = mth('ADD', F_var, (4540, 480))
link(rRot, "Value", angle, "Value"); link(rReg, "Value", angle, "Value_001")

sdScl = mth('ADD', F_var, (4180, 100), v2=37.0); link(gin, S_SEED, sdScl, "Value")
rScl  = rnd('FLOAT', F_var, (4360, 120))
link(tileId, "Attribute", rScl, "ID"); link(sdScl, "Value", rScl, "Seed")
sMin = mth('SUBTRACT', F_var, (4180, -40), v1=1.0); link(gin, S_SVAR, sMin, "Value_001")
sMax = mth('ADD', F_var, (4180, -180), v1=1.0);      link(gin, S_SVAR, sMax, "Value_001")
link(sMin, "Value", rScl, "Min"); link(sMax, "Value", rScl, "Max")
# Shrink so the grout Gap is left open. Once cells come in several sizes a single
# global factor is wrong -- a quarter-size tile would lose a quarter of the grout -- so
# measure each tile: rms distance from its own centroid, which for a square of side s is
# s/sqrt(2), then take back an absolute Gap from that.
dCen = vmath('SUBTRACT', F_var, (3820, -60))
link(posV, "Position", dCen, "Vector"); link(centroid, "Vector", dCen, "Vector_001")
dSq = vmath('DOT_PRODUCT', F_var, (4000, -60))
link(dCen, "Vector", dSq, "Vector"); link(dCen, "Vector", dSq, "Vector_001")
accD = mk("GeometryNodeAccumulateField", F_var, (4180, -60),
          data_type='FLOAT', domain='POINT')
link(dSq, "Value", accD, "Value"); link(islV, "Island Index", accD, "Group Index")
meanSq = mth('DIVIDE', F_var, (4360, -60))
link(accD, "Total", meanSq, "Value"); link(accC, "Total", meanSq, "Value_001")
rms = mth('SQRT', F_var, (4540, -60)); link(meanSq, "Value", rms, "Value")
tileEst = mth('MULTIPLY', F_var, (4720, -60), v2=1.41421356)   # rms -> side of a square
link(rms, "Value", tileEst, "Value")
tileEstS = mth('MAXIMUM', F_var, (4900, -60), v2=1e-6)
link(tileEst, "Value", tileEstS, "Value")
# this tile's own grout, drawn once from Gap .. Gap Max (identical for every tile while
# Gap Max is 0, which is the default)
gapHiG = range_hi(S_GAP, S_GAPM, F_var, (4180, -600))
gGap = range_pick(S_GAP, gapHiG, tileId, "Attribute", 211, F_var, (4360, -600))
gapS0 = mth('SUBTRACT', F_var, (5080, -60))
link(tileEstS, "Value", gapS0, "Value"); link(gGap, "Value", gapS0, "Value_001")
gapS1 = mth('DIVIDE', F_var, (5260, -60))
link(gapS0, "Value", gapS1, "Value"); link(tileEstS, "Value", gapS1, "Value_001")
gapS = mth('MAXIMUM', F_var, (5440, -60), v2=0.4)              # never collapse a tile
link(gapS1, "Value", gapS, "Value")
# ...and its own size, drawn from Tile Size .. Tile Size Max. The cell was spaced for the
# largest, so this is the fraction of its cell the tessera actually claims.
tszHiG = range_hi(S_TSZ, S_TSZM, F_var, (4180, -760))
gSize = range_pick(S_TSZ, tszHiG, tileId, "Attribute", 233, F_var, (4360, -760))
sizeF = mth('DIVIDE', F_var, (4900, -760))
link(gSize, "Value", sizeF, "Value"); link(tszHiG, "Value", sizeF, "Value_001")
scale0 = mth('MULTIPLY', F_var, (5620, -60))
link(rScl, "Value", scale0, "Value"); link(gapS, "Value", scale0, "Value_001")
scale = mth('MULTIPLY', F_var, (5800, -60))
link(scale0, "Value", scale, "Value"); link(sizeF, "Value", scale, "Value_001")

# in-cell nudge, capped by the Gap so tiles can never touch
sdJit = mth('ADD', F_var, (4180, -340), v2=71.0); link(gin, S_SEED, sdJit, "Value")
rJit  = rnd('FLOAT_VECTOR', F_var, (4360, -320))
isock(rJit, "Min").default_value = (-1.0, -1.0, 0.0)
isock(rJit, "Max").default_value = (1.0, 1.0, 0.0)
link(tileId, "Attribute", rJit, "ID"); link(sdJit, "Value", rJit, "Seed")
jitAmp = mth('MULTIPLY', F_var, (4360, -500), v2=0.5)
link(gGap, "Value", jitAmp, "Value")   # this tile's own grout, not the global one
jitAmp2 = mth('MULTIPLY', F_var, (4540, -500))
link(jitAmp, "Value", jitAmp2, "Value"); link(gin, S_PJIT, jitAmp2, "Value_001")
jsep = mk("ShaderNodeSeparateXYZ", F_var, (4540, -320)); link(rJit, "Value", jsep, "Vector")
jU = vmath('SCALE', F_var, (4720, -260)); link(T, "Vector", jU, "Vector")
jUs = mth('MULTIPLY', F_var, (4720, -420))
link(jsep, "X", jUs, "Value"); link(jitAmp2, "Value", jUs, "Value_001")
link(jUs, "Value", jU, "Scale")
jV = vmath('SCALE', F_var, (4900, -260)); link(B, "Vector", jV, "Vector")
jVs = mth('MULTIPLY', F_var, (4900, -420))
link(jsep, "Y", jVs, "Value"); link(jitAmp2, "Value", jVs, "Value_001")
link(jVs, "Value", jV, "Scale")
jit = vmath('ADD', F_var, (5080, -300))
link(jU, "Vector", jit, "Vector"); link(jV, "Vector", jit, "Vector_001")

# newPos = centroid + rot(pos - centroid) * scale + jitter
loc0 = vmath('SUBTRACT', F_var, (4720, 60))
link(posV, "Position", loc0, "Vector"); link(centroid, "Vector", loc0, "Vector_001")
locR = vrot(F_var, (4900, 60))
link(loc0, "Vector", locR, "Vector"); link(N, "Vector", locR, "Axis")
link(angle, "Value", locR, "Angle")
locS = vmath('SCALE', F_var, (5080, 60))
link(locR, "Vector", locS, "Vector"); link(scale, "Value", locS, "Scale")
np0 = vmath('ADD', F_var, (5260, 120))
link(centroid, "Vector", np0, "Vector"); link(locS, "Vector", np0, "Vector_001")
np1 = vmath('ADD', F_var, (5440, 120))
link(np0, "Vector", np1, "Vector"); link(jit, "Vector", np1, "Vector_001")
varied = mk("GeometryNodeSetPosition", F_var, (5620, 300))
link(placed, "Geometry", varied, "Geometry"); link(np1, "Vector", varied, "Position")

# ============================================================================= 10. FIT TEST
# effective margin = user margin + the band reserved for the contour rows
band0 = mth('MULTIPLY', F_fitm, (5620, -520))
link(gin, S_ROWS, band0, "Value"); link(rowPitch, "Value", band0, "Value_001")
band = mth('ADD', F_fitm, (5800, -520))
link(band0, "Value", band, "Value"); link(gin, S_BGAP, band, "Value_001")
effMarg = mth('ADD', F_fitm, (5980, -520))
link(gin, S_MARG, effMarg, "Value"); link(band, "Value", effMarg, "Value_001")
# vertices of a grid tile answer to the user's margin plus the boundary grout
vertMarg = mth('ADD', F_fitm, (5800, -680))
link(gin, S_MARG, vertMarg, "Value"); link(gin, S_BGAP, vertMarg, "Value_001")

# --- per-vertex containment
posF = pos_node(F_fitm, (5620, -60))
upV = vmath('SCALE', F_fitm, (5620, -200))
link(N, "Vector", upV, "Vector"); link(rayLen, "Value", upV, "Scale")
srcV = vmath('ADD', F_fitm, (5800, -120))
link(posF, "Position", srcV, "Vector"); link(upV, "Vector", srcV, "Vector_001")
regAttrV = named('INT', F_fitm, (5800, -300), A_REGION)
rcV = mk("GeometryNodeRaycast", F_fitm, (5980, -160), data_type='INT')
isock(rcV, "Interpolation").default_value = "Nearest"
link(canvas, "Geometry", rcV, "Target Geometry")
link(regAttrV, "Attribute", rcV, "Attribute")
link(srcV, "Vector", rcV, "Source Position")
link(down, "Vector", rcV, "Ray Direction")
link(rayLen2, "Value", rcV, "Ray Length")

proxV = mk("GeometryNodeProximity", F_fitm, (5980, -420), target_element='EDGES')
link(bndGeo, "Selection", proxV, "Target"); link(posF, "Position", proxV, "Source Position")
# Per-VERTEX only the user's Edge Margin applies. The contour band is a whole-tile
# reservation and is tested once, on the centre (bandOk below) -- charging it to every
# vertex as well cost an extra tile-width of fill everywhere in Fully Inside mode.
farV = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6160, -420))
link(proxV, "Distance", farV, "A"); link(vertMarg, "Value", farV, "B")
# with NO walls at all the proximity target is empty and reports distance 0 -- that
# must not read as "hard against the boundary", or nothing would ever be kept.
noWallV = boolm('NOT', F_fitm, (6160, -560)); link(proxV, "Is Valid", noWallV, 0)
clearV = boolm('OR', F_fitm, (6340, -480))
link(farV, "Result", clearV, 0); link(noWallV, "Boolean", clearV, 1)
sameReg = cmp('EQUAL', 'INT', F_fitm, (6160, -260))
link(rcV, "Attribute", sameReg, "A_INT"); link(rcC, "Attribute", sameReg, "B_INT")
vOk0 = boolm('AND', F_fitm, (6340, -160))
link(rcV, "Is Hit", vOk0, 0); link(clearV, "Boolean", vOk0, 1)
vOk = boolm('AND', F_fitm, (6520, -160))
link(vOk0, "Boolean", vOk, 0); link(sameReg, "Result", vOk, 1)

# --- tile-centre containment (same field for every vertex of a tile)
proxC = mk("GeometryNodeProximity", F_fitm, (5980, -640), target_element='EDGES')
link(bndGeo, "Selection", proxC, "Target"); link(centroid, "Vector", proxC, "Source Position")
farC = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6160, -640))
link(proxC, "Distance", farC, "A"); link(effMarg, "Value", farC, "B")
noWallC = boolm('NOT', F_fitm, (6160, -780)); link(proxC, "Is Valid", noWallC, 0)
clearC = boolm('OR', F_fitm, (6340, -760))
link(farC, "Result", clearC, 0); link(noWallC, "Boolean", clearC, 1)
cOk = boolm('AND', F_fitm, (6520, -640))
link(rcC, "Is Hit", cOk, 0); link(clearC, "Boolean", cOk, 1)

# Band reservation: the strip the contour rows occupy belongs to them alone, so NO
# PART of a grid tile may enter it -- testing only the tile centre let tiles poke half
# their width into the last row and overlap it. Unsigned proximity means that at band 0
# this is trivially true, so the rows-off behaviour is untouched.
farB = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6160, -900))
link(proxV, "Distance", farB, "A"); link(band, "Value", farB, "B")
clearB = boolm('OR', F_fitm, (6340, -900))
link(farB, "Result", clearB, 0); link(noWallV, "Boolean", clearB, 1)

# --- tile-centre containment (same field for every vertex of a tile)
proxC = mk("GeometryNodeProximity", F_fitm, (5980, -640), target_element='EDGES')
link(bndGeo, "Selection", proxC, "Target"); link(centroid, "Vector", proxC, "Source Position")
farC = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6160, -640))
link(proxC, "Distance", farC, "A"); link(effMarg, "Value", farC, "B")
noWallC = boolm('NOT', F_fitm, (6160, -780)); link(proxC, "Is Valid", noWallC, 0)
clearC = boolm('OR', F_fitm, (6340, -760))
link(farC, "Result", clearC, 0); link(noWallC, "Boolean", clearC, 1)
cOk = boolm('AND', F_fitm, (6520, -640))
link(rcC, "Is Hit", cOk, 0); link(clearC, "Boolean", cOk, 1)

# band reservation: whatever the fit mode, a grid tile's centre must clear the strip
# the contour rows occupy, so the two never fight over the same ground.
farB = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6160, -900))
link(proxC, "Distance", farB, "A"); link(band, "Value", farB, "B")
clearB = boolm('OR', F_fitm, (6340, -900))
link(farB, "Result", clearB, 0); link(noWallC, "Boolean", clearB, 1)
bOk = boolm('AND', F_fitm, (6520, -900))
link(rcC, "Is Hit", bOk, 0); link(clearB, "Boolean", bOk, 1)

# --- lift the POINT tests onto the FACE domain.  A boolean read across domains is
#     ANDed, so materialise as FLOAT and threshold: mean 1 = all corners, >0 = any.
fVert = mk("GeometryNodeFieldOnDomain", F_fitm, (6700, -160),
           domain='POINT', data_type='FLOAT')
link(vOk, "Boolean", fVert, "Value")
fCent = mk("GeometryNodeFieldOnDomain", F_fitm, (6700, -640),
           domain='POINT', data_type='FLOAT')
link(cOk, "Boolean", fCent, "Value")
fBand = mk("GeometryNodeFieldOnDomain", F_fitm, (6700, -900),
           domain='POINT', data_type='FLOAT')
link(clearB, "Boolean", fBand, "Value")
bandOk = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6880, -900))
link(fBand, "Value", bandOk, "A"); isock(bandOk, "B").default_value = 0.999

allIn = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6880, -100))
link(fVert, "Value", allIn, "A"); isock(allIn, "B").default_value = 0.999
anyIn = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6880, -260))
link(fVert, "Value", anyIn, "A"); isock(anyIn, "B").default_value = 0.001
keepAll = boolm('AND', F_fitm, (7060, -100))
link(allIn, "Result", keepAll, 0); link(bandOk, "Result", keepAll, 1)
keepAny = boolm('AND', F_fitm, (7060, -260))
link(anyIn, "Result", keepAny, 0); link(bandOk, "Result", keepAny, 1)
keepCtr0 = cmp('GREATER_THAN', 'FLOAT', F_fitm, (6880, -640))
link(fCent, "Value", keepCtr0, "A"); isock(keepCtr0, "B").default_value = 0.5
keepCtr = boolm('AND', F_fitm, (7060, -640))
link(keepCtr0, "Result", keepCtr, 0); link(bandOk, "Result", keepCtr, 1)

# ============================================================================= 11. CULL
fitMenu = mk("GeometryNodeMenuSwitch", F_cull, (7060, -420), data_type='INT')
_fi = fitMenu.enum_definition.enum_items
_fi[0].name = "Center Inside"; _fi[1].name = "Fully Inside"; _fi.new("Any Overlap")
for i in range(3): isock(fitMenu, f"Item_{i}").default_value = i
link(gin, S_FIT, fitMenu, "Menu")
keepPick = mk("GeometryNodeIndexSwitch", F_cull, (7240, -300), data_type='BOOLEAN')
keepPick.index_switch_items.new()
link(fitMenu, "Output", keepPick, "Index")
link(keepCtr, "Boolean", keepPick, "Item_0")
link(keepAll, "Boolean", keepPick, "Item_1")
link(keepAny, "Boolean", keepPick, "Item_2")
drop = boolm('NOT', F_cull, (7420, -300)); link(keepPick, "Output", drop, 0)
culled = mk("GeometryNodeDeleteGeometry", F_cull, (7600, 200), domain='FACE', mode='ALL')
link(varied, "Geometry", culled, "Geometry"); link(drop, "Boolean", culled, "Selection")


# ============================================================================= 11b. SHATTER
# An exact partition instead of a clipped grid. Every tile descends from the region's own
# faces, so the union of the tiles IS the region -- outlines, corners and holes come out
# exact for free, which is the one thing a grid intersected with a shape can never do.
#
# A tile is a convex polygon of up to six corners. One split cuts edge i and edge j,
# j = i + d round the ring, giving children of d+2 and n-d+2 corners; with d = floor(n/2)
# that stays inside six for anything that starts inside six. Set Max Corners to 3 and the
# second cut lands ON a vertex instead, which is the classic all-triangle bisection.

# --- Stage 0: seed -- one point per region face, carrying up to six corners -----------
shSrcI = idx_node(F_seed, (7420, 2100))
shSrcC = mk("GeometryNodeCornersOfFace", F_seed, (7600, 2100))
link(shSrcI, "Index", shSrcC, "Face Index")
shTooMany = cmp('GREATER_THAN', 'INT', F_seed, (7780, 2100))
link(shSrcC, "Total", shTooMany, "A_INT"); link(gin, S_MAXC, shTooMany, "B_INT")
shTri = mk("GeometryNodeTriangulate", F_seed, (7960, 2100))
link(sep, "Selection", shTri, "Mesh"); link(shTooMany, "Result", shTri, "Selection")

shFIdx = idx_node(F_seed, (7960, 1900))
shCnt = mk("GeometryNodeCornersOfFace", F_seed, (8140, 1900))
link(shFIdx, "Index", shCnt, "Face Index")
shLast = mth('SUBTRACT', F_seed, (8320, 1900), v2=1.0); link(shCnt, "Total", shLast, "Value")
def _corner(k, y):
    """position of corner k, clamped to the last real corner for short faces"""
    kk = mth('MINIMUM', F_seed, (8500, y), v1=float(k))
    link(shLast, "Value", kk, "Value_001")
    cof = mk("GeometryNodeCornersOfFace", F_seed, (8680, y))
    link(shFIdx, "Index", cof, "Face Index"); link(kk, "Value", cof, "Sort Index")
    voc = mk("GeometryNodeVertexOfCorner", F_seed, (8860, y))
    link(cof, "Corner Index", voc, "Corner Index")
    pp = pos_node(F_seed, (8680, y - 130))
    si = mk("GeometryNodeSampleIndex", F_seed, (9040, y),
            data_type='FLOAT_VECTOR', domain='POINT')
    link(shTri, "Mesh", si, "Geometry"); link(pp, "Position", si, "Value")
    link(voc, "Vertex Index", si, "Index")
    return si
seedChain = shTri
seedKey = "Mesh"
for k in range(6):
    c = _corner(k, 1700 - k * 320)
    st = store(seedChain, seedKey, 'FLOAT_VECTOR', 'FACE', F_seed, (9220 + k * 180, 2100), A_V[k])
    link(c, "Value", st, "Value")
    seedChain, seedKey = st, "Geometry"
stNC = store(seedChain, seedKey, 'FLOAT', 'FACE', F_seed, (10300, 2100), A_NC)
link(shCnt, "Total", stNC, "Value")
seedPts = mk("GeometryNodeMeshToPoints", F_seed, (10480, 2100), mode='FACES')
link(stNC, "Geometry", seedPts, "Mesh")

# --- Stage 1: recursive splitting ----------------------------------------------------
# Tiles are separated by grout anyway, so they need no shared topology -- which is what
# makes this possible at all, since Geometry Nodes cannot cut a face along a line. Each
# tile travels as ONE POINT carrying its corners, and a tile that splits simply becomes
# two points (Duplicate Elements takes a per-element Amount).
shIn = mk("GeometryNodeRepeatInput", F_splt, (10660, 2100))
shOut = mk("GeometryNodeRepeatOutput", F_splt, (14600, 2100))
shIn.pair_with_output(shOut)
shOut.repeat_items.new('INT', 'Pass')
link(seedPts, "Points", shIn, "Geometry")
link(gin, S_SLVL, shIn, "Iterations")
isock(shIn, "Pass").default_value = 0
# The zone needs to know which pass it is on. Without it every random here keys on the
# element index alone, which for a region that is still ONE tile is 0 on every pass --
# so a tile that failed its split roll once failed it forever.
passNext = mth('ADD', F_splt, (14400, 2300), v2=1.0)
link(shIn, "Pass", passNext, "Value")
link(passNext, "Value", shOut, "Pass")
passSeed = mth('MULTIPLY', F_splt, (10840, 1500), v2=7919.0)
link(shIn, "Pass", passSeed, "Value")
shSeed = mth('ADD', F_splt, (11020, 1500))
link(gin, S_SEED, shSeed, "Value"); link(passSeed, "Value", shSeed, "Value_001")
shIdx = idx_node(F_splt, (10840, 1380))

rV = [named('FLOAT_VECTOR', F_splt, (10660, 1800 - k * 120), A_V[k]) for k in range(6)]
rN = named('FLOAT', F_splt, (10660, 1060), A_NC)

def _vpick(idx_out, idx_key, y, x=11380):
    """the corner at a computed ring index"""
    sw = mk("GeometryNodeIndexSwitch", F_splt, (x, y), data_type='VECTOR')
    for _ in range(4): sw.index_switch_items.new()
    link(idx_out, idx_key, sw, "Index")
    for k in range(6): link(rV[k], "Attribute", sw, f"Item_{k}")
    return sw
def _mod(av, ak, bv, bk, y, x=11200):
    m = mth('MODULO', F_splt, (x, y)); link(av, ak, m, "Value"); link(bv, bk, m, "Value_001")
    return m

# --- longest edge.  Edges 0..4 join consecutive stored corners; the closing edge runs
#     from corner n-1 back to corner 0, so only that one needs a lookup.
nMinus1 = mth('SUBTRACT', F_splt, (10840, 1060), v2=1.0); link(rN, "Attribute", nMinus1, "Value")
vLast = _vpick(nMinus1, "Value", 1060, x=11020)
cands = []
for e in range(5):
    d = vmath('SUBTRACT', F_splt, (11020, 1800 - e * 120))
    link(rV[e + 1], "Attribute", d, "Vector"); link(rV[e], "Attribute", d, "Vector_001")
    L = vmath('LENGTH', F_splt, (11200, 1800 - e * 120)); link(d, "Vector", L, "Vector")
    ok = cmp('LESS_THAN', 'FLOAT', F_splt, (11020, 1740 - e * 120))
    isock(ok, "A").default_value = float(e + 1)
    link(rN, "Attribute", ok, "B")                       # edge e exists while e+1 < n
    Lv = switch('FLOAT', F_splt, (11380, 1800 - e * 120))
    link(ok, "Result", Lv, "Switch")
    isock(Lv, "False").default_value = -1.0
    link(L, "Value", Lv, "True")
    cands.append((Lv, "Output", float(e), None))
dC = vmath('SUBTRACT', F_splt, (11200, 940))
link(rV[0], "Attribute", dC, "Vector"); link(vLast, "Output", dC, "Vector_001")
LC = vmath('LENGTH', F_splt, (11380, 940)); link(dC, "Vector", LC, "Vector")
cands.append((LC, "Value", None, nMinus1))

bestL, bestLk = cands[0][0], cands[0][1]
bestI = mth('ADD', F_splt, (11560, 1800), v1=0.0, v2=0.0)      # constant 0
bestIk = "Value"
for n_i, (Lv, Lk, const_i, node_i) in enumerate(cands[1:], start=1):
    better = cmp('GREATER_THAN', 'FLOAT', F_splt, (11740, 1800 - n_i * 120))
    link(Lv, Lk, better, "A"); link(bestL, bestLk, better, "B")
    nl = switch('FLOAT', F_splt, (11920, 1800 - n_i * 120))
    link(better, "Result", nl, "Switch"); link(bestL, bestLk, nl, "False"); link(Lv, Lk, nl, "True")
    ni = switch('FLOAT', F_splt, (11920, 1740 - n_i * 120))
    link(better, "Result", ni, "Switch"); link(bestI, bestIk, ni, "False")
    if node_i is None: isock(ni, "True").default_value = const_i
    else:              link(node_i, "Value", ni, "True")
    bestL, bestLk, bestI, bestIk = nl, "Output", ni, "Output"

# --- how far round to the second cut
vtxCut = cmp('LESS_EQUAL', 'INT', F_splt, (10840, 820))
link(gin, S_MAXC, vtxCut, "A_INT"); isock(vtxCut, "B_INT").default_value = 3
# Children come out with d+2 and n-d+2 corners. Always halving would park every tile at
# four corners for ever, so draw d from the range that keeps BOTH children within Max
# Corners: d from max(1, n+2-M) to min(n-1, M-2). That is what lets pentagons and
# hexagons appear at all.
mSub2 = mth('SUBTRACT', F_splt, (10840, 940), v2=2.0); link(gin, S_MAXC, mSub2, "Value")
dLo0 = mth('ADD', F_splt, (11020, 1000), v2=2.0); link(rN, "Attribute", dLo0, "Value")
dLo1 = mth('SUBTRACT', F_splt, (11200, 1000)); link(dLo0, "Value", dLo1, "Value"); link(gin, S_MAXC, dLo1, "Value_001")
dLo = mth('MAXIMUM', F_splt, (11380, 1000), v2=1.0); link(dLo1, "Value", dLo, "Value")
dHi0 = mth('MINIMUM', F_splt, (11020, 880)); link(nMinus1, "Value", dHi0, "Value"); link(mSub2, "Value", dHi0, "Value_001")
dHi = mth('MAXIMUM', F_splt, (11200, 880)); link(dHi0, "Value", dHi, "Value"); link(dLo, "Value", dHi, "Value_001")
sdD = mth('ADD', F_splt, (11020, 760), v2=457.0); link(shSeed, "Value", sdD, "Value")
dRnd = rnd('FLOAT', F_splt, (11200, 760))
link(shIdx, "Index", dRnd, "ID"); link(sdD, "Value", dRnd, "Seed")
dSpan0 = mth('SUBTRACT', F_splt, (11380, 880)); link(dHi, "Value", dSpan0, "Value"); link(dLo, "Value", dSpan0, "Value_001")
dSpan = mth('ADD', F_splt, (11560, 880), v2=1.0); link(dSpan0, "Value", dSpan, "Value")
dOff = mth('MULTIPLY', F_splt, (11560, 760)); link(dRnd, "Value", dOff, "Value"); link(dSpan, "Value", dOff, "Value_001")
dSum = mth('ADD', F_splt, (11740, 880)); link(dLo, "Value", dSum, "Value"); link(dOff, "Value", dSum, "Value_001")
dFlr = mth('FLOOR', F_splt, (11920, 880)); link(dSum, "Value", dFlr, "Value")
dPick = mth('MINIMUM', F_splt, (12100, 880)); link(dFlr, "Value", dPick, "Value"); link(dHi, "Value", dPick, "Value_001")
shD = switch('FLOAT', F_splt, (12280, 940))
link(vtxCut, "Result", shD, "Switch")
link(dPick, "Value", shD, "False"); link(nMinus1, "Value", shD, "True")
jRaw = mth('ADD', F_splt, (12100, 820)); link(bestI, bestIk, jRaw, "Value"); link(shD, "Output", jRaw, "Value_001")
shJ = _mod(jRaw, "Value", rN, "Attribute", 820, x=12280)

# --- the two cut points
i1Raw = mth('ADD', F_splt, (12100, 700), v2=1.0); link(bestI, bestIk, i1Raw, "Value")
i1 = _mod(i1Raw, "Value", rN, "Attribute", 700, x=12280)
j1Raw = mth('ADD', F_splt, (12100, 580), v2=1.0); link(shJ, "Value", j1Raw, "Value")
j1 = _mod(j1Raw, "Value", rN, "Attribute", 580, x=12280)
Vi = _vpick(bestI, bestIk, 1800, x=12460); Vi1 = _vpick(i1, "Value", 1680, x=12460)
Vj = _vpick(shJ, "Value", 1560, x=12460);  Vj1 = _vpick(j1, "Value", 1440, x=12460)

jHalf = mth('MULTIPLY', F_splt, (10840, 700), v2=0.25); link(gin, S_SJIT, jHalf, "Value")
tMin = mth('SUBTRACT', F_splt, (11020, 700), v1=0.5); link(jHalf, "Value", tMin, "Value_001")
tMax = mth('ADD', F_splt, (11020, 580), v1=0.5); link(jHalf, "Value", tMax, "Value_001")
def _cut(Va, Vb, seed_off, y):
    sd = mth('ADD', F_splt, (12640, y - 120), v2=seed_off); link(shSeed, "Value", sd, "Value")
    r = rnd('FLOAT', F_splt, (12820, y - 120))
    link(shIdx, "Index", r, "ID"); link(sd, "Value", r, "Seed")
    link(tMin, "Value", r, "Min"); link(tMax, "Value", r, "Max")
    _rk = "Value"
    d = vmath('SUBTRACT', F_splt, (12820, y))
    link(Vb, "Output", d, "Vector"); link(Va, "Output", d, "Vector_001")
    sc = vmath('SCALE', F_splt, (13000, y)); link(d, "Vector", sc, "Vector"); link(r, _rk, sc, "Scale")
    m = vmath('ADD', F_splt, (13180, y)); link(Va, "Output", m, "Vector"); link(sc, "Vector", m, "Vector_001")
    return m
shMiE = _cut(Vi, Vi1, 401.0, 1800)
shMjE = _cut(Vj, Vj1, 409.0, 1560)
# seam_edge already folds in the Tileable toggle
seamI = seam_edge(Vi, "Output", Vi1, "Output", F_splt, 12640, 60)
seamJ = seam_edge(Vj, "Output", Vj1, "Output", F_splt, 12640, -900)
shMi = switch('VECTOR', F_splt, (13540, 1800))
link(seamI, "Boolean", shMi, "Switch")
link(shMiE, "Vector", shMi, "False"); link(Vi, "Output", shMi, "True")
lockJ = boolm('OR', F_splt, (13360, 1440))              # Max Corners 3 also cuts to a vertex
link(vtxCut, "Result", lockJ, 0); link(seamJ, "Boolean", lockJ, 1)
shMj = switch('VECTOR', F_splt, (13540, 1560))
link(lockJ, "Boolean", shMj, "Switch")
link(shMjE, "Vector", shMj, "False"); link(Vj, "Output", shMj, "True")
# a cut landing on an existing vertex costs its child one corner
addJ = switch('FLOAT', F_splt, (13720, 1440))
link(lockJ, "Boolean", addJ, "Switch")
isock(addJ, "False").default_value = 2.0; isock(addJ, "True").default_value = 1.0
addI = switch('FLOAT', F_splt, (13720, 1320))
link(seamI, "Boolean", addI, "Switch")
isock(addI, "False").default_value = 2.0; isock(addI, "True").default_value = 1.0
nFirstV = mth('ADD', F_splt, (13900, 1440)); link(shD, "Output", nFirstV, "Value"); link(addJ, "Output", nFirstV, "Value_001")
nMinusDv = mth('SUBTRACT', F_splt, (13900, 1200)); link(rN, "Attribute", nMinusDv, "Value"); link(shD, "Output", nMinusDv, "Value_001")
nSecondV = mth('ADD', F_splt, (14080, 1200)); link(nMinusDv, "Value", nSecondV, "Value"); link(addI, "Output", nSecondV, "Value_001")
# both ends on existing vertices is a plain diagonal -- it needs at least two corners
# either side of it, or the "child" would be a degenerate two-corner sliver
bothV = boolm('AND', F_splt, (13900, 1080)); link(seamI, "Boolean", bothV, 0); link(lockJ, "Boolean", bothV, 1)
dLow2 = cmp('LESS_THAN', 'FLOAT', F_splt, (13900, 960))
link(shD, "Output", dLow2, "A"); isock(dLow2, "B").default_value = 2.0
dHigh2 = cmp('LESS_THAN', 'FLOAT', F_splt, (13900, 840))
link(nMinusDv, "Value", dHigh2, "A"); isock(dHigh2, "B").default_value = 2.0
tooTight = boolm('OR', F_splt, (14080, 900)); link(dLow2, "Result", tooTight, 0); link(dHigh2, "Result", tooTight, 1)
noRoom = boolm('AND', F_splt, (14260, 900)); link(bothV, "Boolean", noRoom, 0); link(tooTight, "Boolean", noRoom, 1)
hasRoom = boolm('NOT', F_splt, (14440, 900)); link(noRoom, "Boolean", hasRoom, 0)

# --- split decision: too big for its own target, or too much of a sliver
sdS = mth('ADD', F_splt, (10840, 460), v2=419.0); link(shSeed, "Value", sdS, "Value")
svMin = mth('SUBTRACT', F_splt, (11020, 460), v1=1.0); link(gin, S_SVAR, svMin, "Value_001")
svMax = mth('ADD', F_splt, (11020, 340), v1=1.0); link(gin, S_SVAR, svMax, "Value_001")
sRnd = rnd('FLOAT', F_splt, (11200, 400))
link(shIdx, "Index", sRnd, "ID"); link(sdS, "Value", sRnd, "Seed")
link(svMin, "Value", sRnd, "Min"); link(svMax, "Value", sRnd, "Max")
# this piece's own target size, drawn from Tile Size .. Tile Size Max before Scale
# Variation wobbles it -- the range changes how far each piece is broken down, so it
# shows up in the break-up itself rather than as a shrink afterwards
tszHiS = range_hi(S_TSZ, S_TSZM, F_splt, (10840, 620))
shBase = range_pick(S_TSZ, tszHiS, shIdx, "Index", 233, F_splt, (11020, 620))
shTarget = mth('MULTIPLY', F_splt, (11380, 400))
link(shBase, "Value", shTarget, "Value"); link(sRnd, "Value", shTarget, "Value_001")
shPos = pos_node(F_splt, (10660, 220))
shProx = mk("GeometryNodeProximity", F_splt, (10840, 220), target_element='EDGES')
link(bndGeo, "Selection", shProx, "Target"); link(shPos, "Position", shProx, "Source Position")
shThr = mth('MULTIPLY', F_splt, (11560, 300))
link(shTarget, "Value", shThr, "Value"); link(gin, S_ATHR, shThr, "Value_001")
shNear0 = cmp('LESS_THAN', 'FLOAT', F_splt, (11740, 220))
link(shProx, "Distance", shNear0, "A"); link(shThr, "Value", shNear0, "B")
shNear = boolm('AND', F_splt, (11920, 220))
link(shNear0, "Result", shNear, 0); link(shProx, "Is Valid", shNear, 1)
shHalfT = mth('MULTIPLY', F_splt, (11740, 400), v2=0.5); link(shTarget, "Value", shHalfT, "Value")
shEff = switch('FLOAT', F_splt, (12100, 300))
link(shNear, "Boolean", shEff, "Switch")
link(shTarget, "Value", shEff, "False"); link(shHalfT, "Value", shEff, "True")
shBig0 = cmp('GREATER_THAN', 'FLOAT', F_splt, (13540, 1180))
link(bestL, bestLk, shBig0, "A"); link(shEff, "Output", shBig0, "B")

# polygon area as a fan from corner 0, so slivers can be spotted whatever the corner count
areaTerms = []
for k in range(1, 5):
    e1 = vmath('SUBTRACT', F_splt, (12460, 1180 - k * 110))
    link(rV[k], "Attribute", e1, "Vector"); link(rV[0], "Attribute", e1, "Vector_001")
    e2 = vmath('SUBTRACT', F_splt, (12640, 1180 - k * 110))
    link(rV[k + 1], "Attribute", e2, "Vector"); link(rV[0], "Attribute", e2, "Vector_001")
    cr = vmath('CROSS_PRODUCT', F_splt, (12820, 1180 - k * 110))
    link(e1, "Vector", cr, "Vector"); link(e2, "Vector", cr, "Vector_001")
    ln = vmath('LENGTH', F_splt, (13000, 1180 - k * 110)); link(cr, "Vector", ln, "Vector")
    ok = cmp('LESS_THAN', 'FLOAT', F_splt, (12820, 1120 - k * 110))
    isock(ok, "A").default_value = float(k + 1)
    link(rN, "Attribute", ok, "B")
    t = switch('FLOAT', F_splt, (13180, 1180 - k * 110))
    link(ok, "Result", t, "Switch"); isock(t, "False").default_value = 0.0
    link(ln, "Value", t, "True")
    areaTerms.append(t)
aSum = areaTerms[0]; aKey = "Output"
for k, t in enumerate(areaTerms[1:], start=1):
    ad = mth('ADD', F_splt, (13360, 1180 - k * 110))
    link(aSum, aKey, ad, "Value"); link(t, "Output", ad, "Value_001")
    aSum, aKey = ad, "Value"
shArea = mth('MAXIMUM', F_splt, (13540, 900), v2=1e-12); link(aSum, aKey, shArea, "Value")
shLen2 = mth('MULTIPLY', F_splt, (13540, 780)); link(bestL, bestLk, shLen2, "Value"); link(bestL, bestLk, shLen2, "Value_001")
shAsp = mth('DIVIDE', F_splt, (13720, 840)); link(shLen2, "Value", shAsp, "Value"); link(shArea, "Value", shAsp, "Value_001")
shThin = cmp('GREATER_THAN', 'FLOAT', F_splt, (13900, 840))
link(shAsp, "Value", shThin, "A"); isock(shThin, "B").default_value = 6.0
shFloor = mth('MULTIPLY', F_splt, (12280, 300), v2=0.3); link(shEff, "Output", shFloor, "Value")
shWorth = cmp('GREATER_THAN', 'FLOAT', F_splt, (13720, 700))
link(bestL, bestLk, shWorth, "A"); link(shFloor, "Value", shWorth, "B")
shThin2 = boolm('AND', F_splt, (14080, 780))
link(shThin, "Result", shThin2, 0); link(shWorth, "Result", shThin2, 1)
shBig = boolm('OR', F_splt, (14260, 1080))
link(shBig0, "Result", shBig, 0); link(shThin2, "Boolean", shBig, 1)
sdCh = mth('ADD', F_splt, (12460, 220), v2=433.0); link(shSeed, "Value", sdCh, "Value")
chRnd = rnd('FLOAT', F_splt, (12640, 220))
link(shIdx, "Index", chRnd, "ID"); link(sdCh, "Value", chRnd, "Seed")
chOk = cmp('LESS_THAN', 'FLOAT', F_splt, (12820, 220))
link(chRnd, "Value", chOk, "A"); link(gin, S_SCHN, chOk, "B")
shDo0 = boolm('AND', F_splt, (14620, 980))
link(shBig, "Boolean", shDo0, 0); link(chOk, "Result", shDo0, 1)
shDo = boolm('AND', F_splt, (14800, 980))
link(shDo0, "Boolean", shDo, 0); link(hasRoom, "Boolean", shDo, 1)
shAmt = switch('INT', F_splt, (14620, 980))
link(shDo, "Boolean", shAmt, "Switch")
isock(shAmt, "False").default_value = 1
isock(shAmt, "True").default_value = 2

# park everything the two children must agree on BEFORE the duplicate -- re-rolling the
# random cut per child would tear the two halves apart
wChain, wKey = shIn, "Geometry"
for nm, srcv, srck, dt in ((A_MI, shMi, "Output", 'FLOAT_VECTOR'),
                           (A_MJ, shMj, "Output", 'FLOAT_VECTOR'),
                           (A_BI, bestI, bestIk, 'FLOAT'),
                           (A_BD, shD, "Output", 'FLOAT'),
                           (A_SS, shDo, "Boolean", 'FLOAT'),
                           (A_N1, nFirstV, "Value", 'FLOAT'),
                           (A_N2, nSecondV, "Value", 'FLOAT')):
    st = store(wChain, wKey, dt, 'POINT', F_splt, (14800 + len(nm), 2100), nm)
    link(srcv, srck, st, "Value")
    wChain, wKey = st, "Geometry"
shDup = mk("GeometryNodeDuplicateElements", F_splt, (15400, 2100), domain='POINT')
link(wChain, wKey, shDup, "Geometry"); link(shAmt, "Output", shDup, "Amount")

# --- assemble the two children
dV = [named('FLOAT_VECTOR', F_splt, (15400, 1800 - k * 110), A_V[k]) for k in range(6)]
dN = named('FLOAT', F_splt, (15400, 1140), A_NC)
dMi = named('FLOAT_VECTOR', F_splt, (15400, 1030), A_MI)
dMj = named('FLOAT_VECTOR', F_splt, (15400, 920), A_MJ)
dI = named('FLOAT', F_splt, (15400, 810), A_BI)
dD = named('FLOAT', F_splt, (15400, 700), A_BD)
dS = named('FLOAT', F_splt, (15400, 590), A_SS)
wasSplit = cmp('GREATER_THAN', 'FLOAT', F_splt, (15580, 590))
link(dS, "Attribute", wasSplit, "A"); isock(wasSplit, "B").default_value = 0.5
firstHalf = cmp('EQUAL', 'INT', F_splt, (15580, 480))
link(shDup, "Duplicate Index", firstHalf, "A_INT"); isock(firstHalf, "B_INT").default_value = 0
dJraw = mth('ADD', F_splt, (15580, 700)); link(dI, "Attribute", dJraw, "Value"); link(dD, "Attribute", dJraw, "Value_001")
dJ = mth('MODULO', F_splt, (15760, 700)); link(dJraw, "Value", dJ, "Value"); link(dN, "Attribute", dJ, "Value_001")
# child 0 walks from i to j starting at Mi; child 1 walks from j back to i starting at Mj
startV = switch('VECTOR', F_splt, (15940, 1030))
link(firstHalf, "Result", startV, "Switch")
link(dMj, "Attribute", startV, "False"); link(dMi, "Attribute", startV, "True")
endV = switch('VECTOR', F_splt, (15940, 920))
link(firstHalf, "Result", endV, "Switch")
link(dMi, "Attribute", endV, "False"); link(dMj, "Attribute", endV, "True")
baseI = switch('FLOAT', F_splt, (15940, 810))
link(firstHalf, "Result", baseI, "Switch")
link(dJ, "Value", baseI, "False"); link(dI, "Attribute", baseI, "True")
nMinusD = mth('SUBTRACT', F_splt, (15760, 590)); link(dN, "Attribute", nMinusD, "Value"); link(dD, "Attribute", nMinusD, "Value_001")
limK = switch('FLOAT', F_splt, (15940, 700))
link(firstHalf, "Result", limK, "Switch")
link(nMinusD, "Value", limK, "False"); link(dD, "Attribute", limK, "True")

newV = []
for k in range(6):
    y = 1800 - k * 130
    if k == 0:
        val, valk = startV, "Output"
    else:
        idxRaw = mth('ADD', F_splt, (16120, y), v2=float(k)); link(baseI, "Output", idxRaw, "Value")
        idxM = mth('MODULO', F_splt, (16300, y)); link(idxRaw, "Value", idxM, "Value"); link(dN, "Attribute", idxM, "Value_001")
        pick = mk("GeometryNodeIndexSwitch", F_splt, (16480, y), data_type='VECTOR')
        for _ in range(4): pick.index_switch_items.new()
        link(idxM, "Value", pick, "Index")
        for q in range(6): link(dV[q], "Attribute", pick, f"Item_{q}")
        inMid = cmp('LESS_EQUAL', 'FLOAT', F_splt, (16300, y - 60))
        isock(inMid, "A").default_value = float(k)
        link(limK, "Output", inMid, "B")
        sw = switch('VECTOR', F_splt, (16660, y))
        link(inMid, "Result", sw, "Switch")
        link(endV, "Output", sw, "False"); link(pick, "Output", sw, "True")
        val, valk = sw, "Output"
    keep = switch('VECTOR', F_splt, (16840, y))
    link(wasSplit, "Result", keep, "Switch")
    link(dV[k], "Attribute", keep, "False"); link(val, valk, keep, "True")
    newV.append(keep)

# corner counts: d+2 and n-d+2, except a cut that landed on a vertex saves the first one
# a corner
nFirst = named('FLOAT', F_splt, (16300, 480), A_N1)
nSecond = named('FLOAT', F_splt, (16300, 360), A_N2)
nChild = switch('FLOAT', F_splt, (16480, 420))
link(firstHalf, "Result", nChild, "Switch")
link(nSecond, "Attribute", nChild, "False"); link(nFirst, "Attribute", nChild, "True")
newN = switch('FLOAT', F_splt, (16660, 420))
link(wasSplit, "Result", newN, "Switch")
link(dN, "Attribute", newN, "False"); link(nChild, "Output", newN, "True")

# Write through scratch attributes first. Each new corner is looked up out of ALL SIX
# old ones, so overwriting A_V[0] before A_V[1] is computed feeds the fresh value back
# into the next lookup -- which silently collapsed every second child onto one corner.
uChain, uKey = shDup, "Geometry"
for k in range(6):
    st = store(uChain, uKey, 'FLOAT_VECTOR', 'POINT', F_splt, (17020 + k * 180, 2100), A_T[k])
    link(newV[k], "Output", st, "Value")
    uChain, uKey = st, "Geometry"
for k in range(6):
    tmp = named('FLOAT_VECTOR', F_splt, (17020 + k * 180, 1700), A_T[k])
    st = store(uChain, uKey, 'FLOAT_VECTOR', 'POINT', F_splt, (17020 + k * 180, 1400), A_V[k])
    link(tmp, "Attribute", st, "Value")
    uChain, uKey = st, "Geometry"
stN2 = store(uChain, uKey, 'FLOAT', 'POINT', F_splt, (18100, 2100), A_NC)
link(newN, "Output", stN2, "Value")
# the point only carries the tile; putting it inside the polygon is enough for the
# distance-to-wall test next pass
fV = [named('FLOAT_VECTOR', F_splt, (18100, 1800 - k * 110), A_V[k]) for k in range(3)]
cen0 = vmath('ADD', F_splt, (18280, 1720))
link(fV[0], "Attribute", cen0, "Vector"); link(fV[1], "Attribute", cen0, "Vector_001")
cen1 = vmath('ADD', F_splt, (18460, 1720))
link(cen0, "Vector", cen1, "Vector"); link(fV[2], "Attribute", cen1, "Vector_001")
shCen = vmath('SCALE', F_splt, (18640, 1720))
link(cen1, "Vector", shCen, "Vector"); isock(shCen, "Scale").default_value = 1.0 / 3.0
shMove = mk("GeometryNodeSetPosition", F_splt, (18280, 2100))
link(stN2, "Geometry", shMove, "Geometry"); link(shCen, "Vector", shMove, "Position")
link(shMove, "Geometry", shOut, "Geometry")

# --- Stage 2: build the polygons -----------------------------------------------------
# one pass per corner count, so every tile gets a prototype with exactly its own number
# of vertices -- no degenerate doubled corners to clean up afterwards
bN = named('FLOAT', F_bld, (18820, 1700), A_NC)
shParts = []
for c in (3, 4, 5, 6):
    selc = cmp('EQUAL', 'INT', F_bld, (19000, 1900 - (c - 3) * 150))
    link(bN, "Attribute", selc, "A_INT"); isock(selc, "B_INT").default_value = c
    proto = mk("GeometryNodeMeshCircle", F_bld, (19000, 1000 - (c - 3) * 150), fill_type='NGON')
    isock(proto, "Vertices").default_value = c
    inst = mk("GeometryNodeInstanceOnPoints", F_bld, (19180, 1900 - (c - 3) * 150))
    link(shOut, "Geometry", inst, "Points"); link(selc, "Result", inst, "Selection")
    link(proto, "Mesh", inst, "Instance")
    rl = mk("GeometryNodeRealizeInstances", F_bld, (19360, 1900 - (c - 3) * 150))
    link(inst, "Instances", rl, "Geometry")
    shParts.append(rl)
shJoin = mk("GeometryNodeJoinGeometry", F_bld, (19540, 1700))
for rl in shParts: link(rl, "Geometry", shJoin, "Geometry")

# --- Stage 3: place the corners and open the grout -----------------------------------
cIdxN = idx_node(F_bld, (19540, 1300))
foc = mk("GeometryNodeFaceOfCorner", F_bld, (19720, 1300))
link(cIdxN, "Index", foc, "Corner Index")
kIn = foc                       # "Index in Face" -- which corner of its tile this is
oV = [named('FLOAT_VECTOR', F_bld, (19540, 1150 - k * 110), A_V[k]) for k in range(6)]
oN = named('FLOAT', F_bld, (19540, 480), A_NC)
def _opick(idx_out, idx_key, y):
    sw = mk("GeometryNodeIndexSwitch", F_bld, (20080, y), data_type='VECTOR')
    for _ in range(4): sw.index_switch_items.new()
    link(idx_out, idx_key, sw, "Index")
    for q in range(6): link(oV[q], "Attribute", sw, f"Item_{q}")
    return sw
kNext0 = mth('ADD', F_bld, (19900, 1300), v2=1.0); link(kIn, "Index in Face", kNext0, "Value")
kNext = mth('MODULO', F_bld, (20080, 1300)); link(kNext0, "Value", kNext, "Value"); link(oN, "Attribute", kNext, "Value_001")
kPrev0 = mth('SUBTRACT', F_bld, (19900, 1180)); link(kIn, "Index in Face", kPrev0, "Value"); isock(kPrev0, "Value_001").default_value = 1.0
kPrev1 = mth('ADD', F_bld, (20080, 1180)); link(kPrev0, "Value", kPrev1, "Value"); link(oN, "Attribute", kPrev1, "Value_001")
kPrev = mth('MODULO', F_bld, (20260, 1180)); link(kPrev1, "Value", kPrev, "Value"); link(oN, "Attribute", kPrev, "Value_001")
cV = _opick(kIn, "Index in Face", 1420)
cU = _opick(kNext, "Value", 1300)
cW = _opick(kPrev, "Value", 1180)

# a boundary edge is one lying ON a wall: the tiles partition the region exactly, so its
# midpoint sits at distance ~0 from the wall geometry
eps = mth('MULTIPLY', F_bld, (19900, 360), v2=0.005); link(gin, S_TSZ, eps, "Value")
eps2 = mth('MAXIMUM', F_bld, (20080, 360), v2=1e-6); link(eps, "Value", eps2, "Value")
gapHiB = range_hi(S_GAP, S_GAPM, F_bld, (19540, 120))
bgapHiB = range_hi(S_BGAP, S_BGAPM, F_bld, (19540, 40))
def _edge_gap(pa, pb, y):
    mid0 = vmath('ADD', F_bld, (20440, y)); link(pa, "Output", mid0, "Vector"); link(pb, "Output", mid0, "Vector_001")
    mid = vmath('SCALE', F_bld, (20620, y)); link(mid0, "Vector", mid, "Vector"); isock(mid, "Scale").default_value = 0.5
    # Draw both grout widths from the edge MIDPOINT rather than from a tile id: the two
    # tiles sharing this edge each compute the same midpoint, so they agree on the width
    # and the joint stays even. Under Tileable the midpoint is folded into the bounds
    # box first, so an edge on the +face and its partner on the -face agree too.
    wmid = wrapped_mid(pa, "Output", pb, "Output", F_bld, 20440, y - 1800)
    ncoord = switch('VECTOR', F_bld, (21520, y - 1800))
    link(gin, S_TILE, ncoord, "Switch")
    link(mid, "Vector", ncoord, "False"); link(wmid, "Vector", ncoord, "True")
    eGap = range_pick_at(S_GAP, gapHiB, ncoord, "Output", (0.0, 0.0, 0.0),
                         F_bld, (21700, y - 1800))
    eBGap = range_pick_at(S_BGAP, bgapHiB, ncoord, "Output", (13.7, 5.1, 2.3),
                          F_bld, (21700, y - 2100))
    gapHalf = mth('MULTIPLY', F_bld, (22420, y - 1800), v2=0.5)
    link(eGap, "Value", gapHalf, "Value")
    pr = mk("GeometryNodeProximity", F_bld, (20800, y), target_element='EDGES')
    link(bndGeo, "Selection", pr, "Target"); link(mid, "Vector", pr, "Source Position")
    on0 = cmp('LESS_THAN', 'FLOAT', F_bld, (20980, y))
    link(pr, "Distance", on0, "A"); link(eps2, "Value", on0, "B")
    on = boolm('AND', F_bld, (21160, y)); link(on0, "Result", on, 0); link(pr, "Is Valid", on, 1)
    # A seam is a wall, but it must NOT take the boundary grout: two copies laid side by
    # side would then show 2x Boundary Gap where every other joint shows one Gap.
    sm = seam_edge(pa, "Output", pb, "Output", F_bld, 20440, y - 900)
    notSeam = boolm('NOT', F_bld, (21900, y - 60)); link(sm, "Boolean", notSeam, 0)
    useB = boolm('AND', F_bld, (22080, y - 60))
    link(on, "Boolean", useB, 0); link(notSeam, "Boolean", useB, 1)
    d = switch('FLOAT', F_bld, (21340, y))
    link(useB, "Boolean", d, "Switch")
    link(gapHalf, "Value", d, "False"); link(eBGap, "Value", d, "True")
    return d
gd1 = _edge_gap(cV, cU, 900)          # the edge leaving this corner
gd2 = _edge_gap(cW, cV, 700)          # the edge arriving at it

# inward normals of those two edges, then the point that is gd1 from one and gd2 from the
# other -- with gd1 == gd2 this is the angle bisector, and it stays correct when the two
# differ, which is what lets the boundary carry its own gap
e1 = vmath('SUBTRACT', F_bld, (21520, 1420)); link(cU, "Output", e1, "Vector"); link(cV, "Output", e1, "Vector_001")
e2 = vmath('SUBTRACT', F_bld, (21520, 1300)); link(cW, "Output", e2, "Vector"); link(cV, "Output", e2, "Vector_001")
def _inward(ea, eb, y):
    d1 = vmath('DOT_PRODUCT', F_bld, (21700, y)); link(eb, "Vector", d1, "Vector"); link(ea, "Vector", d1, "Vector_001")
    d2 = vmath('DOT_PRODUCT', F_bld, (21700, y - 60)); link(ea, "Vector", d2, "Vector"); link(ea, "Vector", d2, "Vector_001")
    d2s = mth('MAXIMUM', F_bld, (21880, y - 60), v2=1e-12); link(d2, "Value", d2s, "Value")
    f = mth('DIVIDE', F_bld, (22060, y - 60)); link(d1, "Value", f, "Value"); link(d2s, "Value", f, "Value_001")
    pr = vmath('SCALE', F_bld, (22240, y)); link(ea, "Vector", pr, "Vector"); link(f, "Value", pr, "Scale")
    sub = vmath('SUBTRACT', F_bld, (22420, y)); link(eb, "Vector", sub, "Vector"); link(pr, "Vector", sub, "Vector_001")
    return vmath('NORMALIZE', F_bld, (22600, y)) , sub
n1, n1s = _inward(e1, e2, 1420); link(n1s, "Vector", n1, "Vector")
n2, n2s = _inward(e2, e1, 1180); link(n2s, "Vector", n2, "Vector")
cc = vmath('DOT_PRODUCT', F_bld, (22780, 1300)); link(n1, "Vector", cc, "Vector"); link(n2, "Vector", cc, "Vector_001")
cc2 = mth('MULTIPLY', F_bld, (22960, 1300)); link(cc, "Value", cc2, "Value"); link(cc, "Value", cc2, "Value_001")
den0 = mth('SUBTRACT', F_bld, (23140, 1300), v1=1.0); link(cc2, "Value", den0, "Value_001")
den = mth('MAXIMUM', F_bld, (23320, 1300), v2=1e-4); link(den0, "Value", den, "Value")
cd2 = mth('MULTIPLY', F_bld, (22960, 900)); link(cc, "Value", cd2, "Value"); link(gd2, "Output", cd2, "Value_001")
cd1 = mth('MULTIPLY', F_bld, (22960, 700)); link(cc, "Value", cd1, "Value"); link(gd1, "Output", cd1, "Value_001")
al0 = mth('SUBTRACT', F_bld, (23140, 900)); link(gd1, "Output", al0, "Value"); link(cd2, "Value", al0, "Value_001")
be0 = mth('SUBTRACT', F_bld, (23140, 700)); link(gd2, "Output", be0, "Value"); link(cd1, "Value", be0, "Value_001")
al = mth('DIVIDE', F_bld, (23500, 900)); link(al0, "Value", al, "Value"); link(den, "Value", al, "Value_001")
be = mth('DIVIDE', F_bld, (23500, 700)); link(be0, "Value", be, "Value"); link(den, "Value", be, "Value_001")
o1 = vmath('SCALE', F_bld, (23680, 1420)); link(n1, "Vector", o1, "Vector"); link(al, "Value", o1, "Scale")
o2 = vmath('SCALE', F_bld, (23680, 1180)); link(n2, "Vector", o2, "Vector"); link(be, "Value", o2, "Scale")
off0 = vmath('ADD', F_bld, (23860, 1300)); link(o1, "Vector", off0, "Vector"); link(o2, "Vector", off0, "Vector_001")
# never let a small tile turn itself inside out
l1 = vmath('LENGTH', F_bld, (21700, 1000)); link(e1, "Vector", l1, "Vector")
l2 = vmath('LENGTH', F_bld, (21700, 880)); link(e2, "Vector", l2, "Vector")
lmin = mth('MINIMUM', F_bld, (21880, 940)); link(l1, "Value", lmin, "Value"); link(l2, "Value", lmin, "Value_001")
lcap = mth('MULTIPLY', F_bld, (22060, 940), v2=0.45); link(lmin, "Value", lcap, "Value")
olen = vmath('LENGTH', F_bld, (24040, 1180)); link(off0, "Vector", olen, "Vector")
olen2 = mth('MAXIMUM', F_bld, (24220, 1180), v2=1e-9); link(olen, "Value", olen2, "Value")
oscl0 = mth('DIVIDE', F_bld, (24400, 1180)); link(lcap, "Value", oscl0, "Value"); link(olen2, "Value", oscl0, "Value_001")
oscl = mth('MINIMUM', F_bld, (24580, 1180), v2=1.0); link(oscl0, "Value", oscl, "Value")
# Use the exact solve, uncapped. Capping the step to stop a small tile inverting is
# what left corners short of the grout they were asked for, and no amount of pushing
# afterwards fixes it: at a sharp corner, moving away from one wall moves TOWARDS the
# other. A tile too small to hold its own grout is simply all grout -- drop it instead.
cornerPos = vmath('ADD', F_bld, (24940, 1300))
link(cV, "Output", cornerPos, "Vector"); link(off0, "Vector", cornerPos, "Vector_001")
capBind = cmp('GREATER_THAN', 'FLOAT', F_bld, (24940, 1000))
link(olen, "Value", capBind, "A"); link(lcap, "Value", capBind, "B")
capF = mk("GeometryNodeFieldOnDomain", F_bld, (25120, 1000),
          domain='CORNER', data_type='FLOAT')
link(capBind, "Result", capF, "Value")
capDrop = cmp('GREATER_THAN', 'FLOAT', F_bld, (25300, 1000))
link(capF, "Value", capDrop, "A"); isock(capDrop, "B").default_value = 0.001

# that was all built per CORNER; each tile owns its vertices outright, so reading it back
# on the point domain is exact
cornerToPoint = mk("GeometryNodeFieldOnDomain", F_bld, (25120, 1300),
                   domain='CORNER', data_type='FLOAT_VECTOR')
link(cornerPos, "Vector", cornerToPoint, "Value")
shSet = mk("GeometryNodeSetPosition", F_bld, (25300, 1700))
link(shJoin, "Geometry", shSet, "Geometry"); link(cornerToPoint, "Value", shSet, "Position")

# Flag the corners that sit on the bounds box, and do it on the corner BEFORE the grout
# inset moved it -- by the time the position is set, a seam vertex has been pulled Gap/2
# off the box face and no longer answers the seam test. Stored as an attribute because
# the variation stage downstream is on the far side of a Delete Geometry.
cSeam = seam_vert(cV, "Output", F_bld, 25300, -700)
cSeamN = switch('FLOAT', F_bld, (26560, -700))
link(cSeam, "Boolean", cSeamN, "Switch")
isock(cSeamN, "False").default_value = 0.0
isock(cSeamN, "True").default_value = 1.0
cSeamPt = mk("GeometryNodeFieldOnDomain", F_bld, (26740, -700),
             domain='CORNER', data_type='FLOAT')
link(cSeamN, "Output", cSeamPt, "Value")
shSeam = store(shSet, "Geometry", 'FLOAT', 'POINT', F_bld, (25480, 1700), A_SEAM)
link(cSeamPt, "Value", shSeam, "Value")

# the contour rows own their band in either mode, so keep the partition out of it
# Only the contour-row band applies here: in Shatter the Boundary Gap is opened by the
# inset, so folding it into the cull as well deleted every tile that touched a wall.
# nudge the threshold: a shatter tile sits exactly ON the wall, so a strict "distance
# greater than zero" would delete every one of them when there are no contour rows
shBandEps = mth('SUBTRACT', F_bld, (24940, 1180), v2=1e-5); link(band0, "Value", shBandEps, "Value")
shBandOk0 = cmp('GREATER_THAN', 'FLOAT', F_bld, (25120, 1180))
link(proxV, "Distance", shBandOk0, "A"); link(shBandEps, "Value", shBandOk0, "B")
shBandClear = boolm('OR', F_bld, (25300, 1180))
link(shBandOk0, "Result", shBandClear, 0); link(noWallV, "Boolean", shBandClear, 1)
shBandF = mk("GeometryNodeFieldOnDomain", F_bld, (25480, 1180),
             domain='POINT', data_type='FLOAT')
link(shBandClear, "Boolean", shBandF, "Value")
shBandAll = cmp('GREATER_THAN', 'FLOAT', F_bld, (25660, 1180))
link(shBandF, "Value", shBandAll, "A"); isock(shBandAll, "B").default_value = 0.999
shBandDrop = boolm('NOT', F_bld, (25840, 1300)); link(shBandAll, "Result", shBandDrop, 0)
shDrop = boolm('OR', F_bld, (25660, 1300))
link(shBandDrop, "Boolean", shDrop, 0); link(capDrop, "Result", shDrop, 1)
shCulled = mk("GeometryNodeDeleteGeometry", F_bld, (25840, 1700), domain='FACE', mode='ALL')
link(shSeam, "Geometry", shCulled, "Geometry"); link(shDrop, "Boolean", shCulled, "Selection")

# ==================================================== 11b. SHATTER PER-TILE VARIATION
# Same treatment the grid gets, on the shattered tiles: each one is its own island, so
# accumulate by island index for a centroid and turn/shrink/slide the tile about it.
#
# It runs AFTER the cull so the fit and grout tests still see the untouched partition,
# and it defaults to nothing at all: the whole point of Shatter is that the tiles cover
# the shape exactly, so the wobble is opt-in. Position and rotation are both scaled by
# the grout the tile just opened, which means at Gap 0 they are identically zero and the
# exact partition survives whatever the user dials in. Scale Jitter is not -- it is the
# one that deliberately gives coverage up.
islS = mk("GeometryNodeInputMeshIsland", F_shvar, (26020, 1700))
posS = pos_node(F_shvar, (26020, 1560))
accCS = mk("GeometryNodeAccumulateField", F_shvar, (26200, 1700),
           data_type='FLOAT', domain='POINT')
isock(accCS, "Value").default_value = 1.0
link(islS, "Island Index", accCS, "Group Index")
accPS = mk("GeometryNodeAccumulateField", F_shvar, (26200, 1560),
           data_type='FLOAT_VECTOR', domain='POINT')
link(posS, "Position", accPS, "Value"); link(islS, "Island Index", accPS, "Group Index")
cntS = mk("ShaderNodeCombineXYZ", F_shvar, (26380, 1700))
for _k in ("X", "Y", "Z"): link(accCS, "Total", cntS, _k)
cenS = vmath('DIVIDE', F_shvar, (26560, 1620))
link(accPS, "Total", cenS, "Vector"); link(cntS, "Vector", cenS, "Vector_001")

# the tile's own local frame: everything below turns and scales about its centroid
dCenS = vmath('SUBTRACT', F_shvar, (26740, 1440))
link(posS, "Position", dCenS, "Vector"); link(cenS, "Vector", dCenS, "Vector_001")

# rotation: the angle the user asked for, full stop.
# An earlier version limited this per tile to what the tile's own grout could absorb, on
# the reasoning that Shatter mixes tile sizes and a big tessera sweeps its corners much
# further than a small one for the same angle. It was the wrong call: the limit made the
# control silently stop responding past a few degrees on coarse break-ups, and at Gap 0
# it zeroed the control outright -- the knob simply did nothing. The grid's own Rotation
# Jitter does not cap either. Tiles CAN overlap at large angles; that is the user's call
# to make, and it is what the tooltip says.
sdSR = mth('ADD', F_shvar, (26740, 1180), v2=131.0); link(gin, S_SEED, sdSR, "Value")
angS = rnd('FLOAT', F_shvar, (26920, 1180))
link(islS, "Island Index", angS, "ID"); link(sdSR, "Value", angS, "Seed")
srNeg = mth('MULTIPLY', F_shvar, (26740, 1060), v2=-1.0); link(gin, S_SRJ, srNeg, "Value")
link(srNeg, "Value", angS, "Min"); link(gin, S_SRJ, angS, "Max")

# one-sided shrink -- growing a tile would eat the grout it was just given
sdSS = mth('ADD', F_shvar, (26740, 900), v2=173.0); link(gin, S_SEED, sdSS, "Value")
rSS = rnd('FLOAT', F_shvar, (26920, 900))
link(islS, "Island Index", rSS, "ID"); link(sdSS, "Value", rSS, "Seed")
isock(rSS, "Min").default_value = 0.0; isock(rSS, "Max").default_value = 1.0
shrink0 = mth('MULTIPLY', F_shvar, (27100, 900))
link(rSS, "Value", shrink0, "Value"); link(gin, S_SSJ, shrink0, "Value_001")
shrink = mth('SUBTRACT', F_shvar, (27280, 900), v1=1.0)
link(shrink0, "Value", shrink, "Value_001")

# slide, in the tile plane, capped by the Gap exactly as the grid's own jitter is
sdSP = mth('ADD', F_shvar, (26740, 660), v2=197.0); link(gin, S_SEED, sdSP, "Value")
rSP = rnd('FLOAT_VECTOR', F_shvar, (26920, 660))
isock(rSP, "Min").default_value = (-1.0, -1.0, 0.0)
isock(rSP, "Max").default_value = (1.0, 1.0, 0.0)
link(islS, "Island Index", rSP, "ID"); link(sdSP, "Value", rSP, "Seed")
ampS0 = mth('MULTIPLY', F_shvar, (26920, 520), v2=0.5); link(gin, S_GAP, ampS0, "Value")
ampS = mth('MULTIPLY', F_shvar, (27100, 520))
link(ampS0, "Value", ampS, "Value"); link(gin, S_SPJ, ampS, "Value_001")
sepS = mk("ShaderNodeSeparateXYZ", F_shvar, (27100, 660)); link(rSP, "Value", sepS, "Vector")
sUs = mth('MULTIPLY', F_shvar, (27280, 600))
link(sepS, "X", sUs, "Value"); link(ampS, "Value", sUs, "Value_001")
sU = vmath('SCALE', F_shvar, (27460, 700)); link(T, "Vector", sU, "Vector")
link(sUs, "Value", sU, "Scale")
sVs = mth('MULTIPLY', F_shvar, (27280, 460))
link(sepS, "Y", sVs, "Value"); link(ampS, "Value", sVs, "Value_001")
sV = vmath('SCALE', F_shvar, (27460, 560)); link(B, "Vector", sV, "Vector")
link(sVs, "Value", sV, "Scale")
sJit = vmath('ADD', F_shvar, (27640, 640))
link(sU, "Vector", sJit, "Vector"); link(sV, "Vector", sJit, "Vector_001")

# newPos = centroid + rot(pos - centroid) * shrink + slide
sLocR = vrot(F_shvar, (27820, 1620))
link(dCenS, "Vector", sLocR, "Vector"); link(N, "Vector", sLocR, "Axis")
link(angS, "Value", sLocR, "Angle")
sLocS = vmath('SCALE', F_shvar, (28360, 1620))
link(sLocR, "Vector", sLocS, "Vector"); link(shrink, "Value", sLocS, "Scale")
sNp0 = vmath('ADD', F_shvar, (28540, 1620))
link(cenS, "Vector", sNp0, "Vector"); link(sLocS, "Vector", sNp0, "Vector_001")
sNp = vmath('ADD', F_shvar, (28720, 1620))
link(sNp0, "Vector", sNp, "Vector"); link(sJit, "Vector", sNp, "Vector_001")

# A seam has to stay exactly where the input mesh put it: the tile on the far face of
# the box is a DIFFERENT tile with a different shape, so there is no rigid motion the
# two could share. Any tile with a vertex on a bounds face therefore sits this one out,
# leaving the two copies mating as before. Costs a ring of unwobbled tiles around the
# repeat, and only when Tileable is on.
sSeamA = named('FLOAT', F_shvar, (27280, 200), A_SEAM)
accSeam = mk("GeometryNodeAccumulateField", F_shvar, (27460, 200),
             data_type='FLOAT', domain='POINT')
link(sSeamA, "Attribute", accSeam, "Value"); link(islS, "Island Index", accSeam, "Group Index")
sPinned = cmp('GREATER_THAN', 'FLOAT', F_shvar, (27640, 200))
link(accSeam, "Total", sPinned, "A"); isock(sPinned, "B").default_value = 0.5
sFinal = switch('VECTOR', F_shvar, (28900, 1620))
link(sPinned, "Result", sFinal, "Switch")
link(sNp, "Vector", sFinal, "False"); link(posS, "Position", sFinal, "True")
shVaried = mk("GeometryNodeSetPosition", F_shvar, (29080, 1700))
link(shCulled, "Geometry", shVaried, "Geometry"); link(sFinal, "Output", shVaried, "Position")

# --- pick the generator --------------------------------------------------------------
modeMenu = mk("GeometryNodeMenuSwitch", F_bld, (25660, 1400), data_type='INT')
_mi = modeMenu.enum_definition.enum_items
_mi[0].name = "Grid"; _mi[1].name = "Shatter"
for i in range(2): isock(modeMenu, f"Item_{i}").default_value = i
link(gin, S_TMODE, modeMenu, "Menu")
tilesPick = mk("GeometryNodeIndexSwitch", F_bld, (25840, 1700), data_type='GEOMETRY')
link(modeMenu, "Output", tilesPick, "Index")
link(culled, "Geometry", tilesPick, "Item_0")
link(shVaried, "Geometry", tilesPick, "Item_1")

# ============================================================================= 12. CONTOUR
# Walls -> points spaced by the tile pitch -> one copy per row, each pushed inward.
# Everything after the first sampling happens on a POINT CLOUD: Mesh to Curve splits
# into open splines wherever an interior wall meets the outline, and offsetting those
# as curves doubled the rows around every such T-junction.
cCurve = mk("GeometryNodeMeshToCurve", F_cont, (5620, 900))
link(bndGeo, "Selection", cCurve, "Mesh")
# Densify FIRST. On a poly spline the tangent at a control point is the bisector of its
# two segments, and the field between control points interpolates those -- so on a
# coarse outline (a square is four control points) the corner rotation is smeared right
# along every straight run and the bricks sit visibly skewed. With control points a
# fraction of a tile apart the bisector IS the segment direction.
fineL0 = mth('MULTIPLY', F_cont, (5620, 520), v2=0.15)
link(cl, "Output", fineL0, "Value")
fineL = mth('MAXIMUM', F_cont, (5800, 520), v2=1e-5); link(fineL0, "Value", fineL, "Value")
cFine = mk("GeometryNodeResampleCurve", F_cont, (5980, 700))
link(cCurve, "Curve", cFine, "Curve")
isock(cFine, "Mode").default_value = "Length"
link(fineL, "Value", cFine, "Length")
cPts = mk("GeometryNodeCurveToPoints", F_cont, (6160, 900), mode='LENGTH')
link(cFine, "Curve", cPts, "Curve"); link(pitchC2, "Value", cPts, "Length")
stTan = store(cPts, "Points", 'FLOAT_VECTOR', 'POINT', F_cont, (6160, 900), A_TAN)
link(cPts, "Tangent", stTan, "Value")
cDup = mk("GeometryNodeDuplicateElements", F_cont, (6340, 900), domain='POINT')
link(stTan, "Geometry", cDup, "Geometry"); link(gin, S_ROWS, cDup, "Amount")

# tangent projected into the plane -> the inward normal of the outline
tanA = named('FLOAT_VECTOR', F_cont, (6340, 620), A_TAN)
tanDot = vmath('DOT_PRODUCT', F_cont, (6520, 560))
link(tanA, "Attribute", tanDot, "Vector"); link(N, "Vector", tanDot, "Vector_001")
tanN = vmath('SCALE', F_cont, (6700, 480))
link(N, "Vector", tanN, "Vector"); link(tanDot, "Value", tanN, "Scale")
tanP = vmath('SUBTRACT', F_cont, (6880, 560))
link(tanA, "Attribute", tanP, "Vector"); link(tanN, "Vector", tanP, "Vector_001")
tanU = vmath('NORMALIZE', F_cont, (7060, 560)); link(tanP, "Vector", tanU, "Vector")
inw0 = vmath('CROSS_PRODUCT', F_cont, (7240, 480))
link(N, "Vector", inw0, "Vector"); link(tanU, "Vector", inw0, "Vector_001")
inwN = vmath('NORMALIZE', F_cont, (7420, 480)); link(inw0, "Vector", inwN, "Vector")

# which side is "in"?  probe a short step along the candidate inward direction
posC = pos_node(F_cont, (6340, 380))
probeStep = mth('MULTIPLY', F_cont, (7240, 300), v2=0.35)
link(cell, "Value", probeStep, "Value")
probeV = vmath('SCALE', F_cont, (7420, 320))
link(inwN, "Vector", probeV, "Vector"); link(probeStep, "Value", probeV, "Scale")
probeP = vmath('ADD', F_cont, (7600, 380))
link(posC, "Position", probeP, "Vector"); link(probeV, "Vector", probeP, "Vector_001")
upP = vmath('SCALE', F_cont, (7600, 200))
link(N, "Vector", upP, "Vector"); link(rayLen, "Value", upP, "Scale")
probeS = vmath('ADD', F_cont, (7780, 300))
link(probeP, "Vector", probeS, "Vector"); link(upP, "Vector", probeS, "Vector_001")
rcP = mk("GeometryNodeRaycast", F_cont, (7960, 300))
link(canvas, "Geometry", rcP, "Target Geometry")
link(probeS, "Vector", rcP, "Source Position")
link(down, "Vector", rcP, "Ray Direction")
link(rayLen2, "Value", rcP, "Ray Length")
sign = switch('FLOAT', F_cont, (8140, 300))
link(rcP, "Is Hit", sign, "Switch")
isock(sign, "False").default_value = -1.0
isock(sign, "True").default_value  = 1.0
inward = vmath('SCALE', F_cont, (8320, 420))
link(inwN, "Vector", inward, "Vector"); link(sign, "Output", inward, "Scale")

# offset row k inward by (k + 0.5) * pitch + Edge Margin
rowD0 = mth('MULTIPLY', F_cont, (6700, 900))
link(cDup, "Duplicate Index", rowD0, "Value"); link(rowPitch, "Value", rowD0, "Value_001")
halfW = mth('MULTIPLY', F_cont, (6700, 740), v2=0.5); link(cw, "Output", halfW, "Value")
rowD1 = mth('ADD', F_cont, (6880, 900))                   # row 0 sits half a tile in ...
link(rowD0, "Value", rowD1, "Value"); link(halfW, "Value", rowD1, "Value_001")
rowD = mth('ADD', F_cont, (7060, 900))                    # ... plus the boundary grout
link(rowD1, "Value", rowD, "Value"); link(gin, S_BGAP, rowD, "Value_001")
# keep the row's target distance on the points: Duplicate Index does not survive the
# merge below, and the cull needs to know which row a point belongs to
stRow = store(cDup, "Geometry", 'FLOAT', 'POINT', F_cont, (7060, 900), A_ROW)
link(rowD, "Value", stRow, "Value")
rowV = vmath('SCALE', F_cont, (8500, 420))
link(inward, "Vector", rowV, "Vector"); link(rowD, "Value", rowV, "Scale")
cPos = mk("GeometryNodeSetPosition", F_cont, (8680, 900))
link(stRow, "Geometry", cPos, "Geometry"); link(rowV, "Vector", cPos, "Offset")

# --- relax onto the true offset distance -------------------------------------
# Stepping along the averaged inward normal undershoots at a convex corner: the wall
# bends away, so the point lands ~0.7*row from it and the tile hangs outside. Measure
# the ACTUAL distance and push the remainder along the proximity gradient. Dividing the
# target by how well that gradient still agrees with the inward normal is exactly the
# 1/cos(theta) extra clearance a square tile needs to get round a corner.
posR = pos_node(F_cont, (8860, 1120))
proxR = mk("GeometryNodeProximity", F_cont, (9040, 1120), target_element='EDGES')
link(bndGeo, "Selection", proxR, "Target"); link(posR, "Position", proxR, "Source Position")
gradR0 = vmath('SUBTRACT', F_cont, (9220, 1180))
link(posR, "Position", gradR0, "Vector"); link(proxR, "Position", gradR0, "Vector_001")
gradR1 = vmath('NORMALIZE', F_cont, (9400, 1180)); link(gradR0, "Vector", gradR1, "Vector")
# the gradient only points inward while the point IS inside -- sign it, and work in
# signed distance, so a point that escaped around a corner is pulled back across
upR = vmath('SCALE', F_cont, (8860, 1300))
link(N, "Vector", upR, "Vector"); link(rayLen, "Value", upR, "Scale")
srcR = vmath('ADD', F_cont, (9040, 1420))
link(posR, "Position", srcR, "Vector"); link(upR, "Vector", srcR, "Vector_001")
rcR = mk("GeometryNodeRaycast", F_cont, (9220, 1420))
link(canvas, "Geometry", rcR, "Target Geometry")
link(srcR, "Vector", rcR, "Source Position")
link(down, "Vector", rcR, "Ray Direction")
link(rayLen2, "Value", rcR, "Ray Length")
sgnR = switch('FLOAT', F_cont, (9400, 1420))
link(rcR, "Is Hit", sgnR, "Switch")
isock(sgnR, "False").default_value = -1.0
isock(sgnR, "True").default_value = 1.0
gradR = vmath('SCALE', F_cont, (9580, 1180))
link(gradR1, "Vector", gradR, "Vector"); link(sgnR, "Output", gradR, "Scale")
signedD = mth('MULTIPLY', F_cont, (9580, 1560))
link(proxR, "Distance", signedD, "Value"); link(sgnR, "Output", signedD, "Value_001")
rowR = named('FLOAT', F_cont, (8860, 1720), A_ROW)
# Rescue only. Pushing every point out to its full row distance sounds right but
# ROUNDS OFF corners -- a point that stepped into a 90-degree corner sits at 0.7*row
# and moving it to a full row walks it diagonally inward, so a square outline comes out
# blobby. Leave points that are already comfortably inside exactly where they are; only
# lift the ones that are outside, or too close for their own tile to fit.
targetR0 = mth('MULTIPLY', F_cont, (9760, 1720), v2=0.5)
link(cw, "Output", targetR0, "Value")
targetR = mth('ADD', F_cont, (9940, 1720))
link(targetR0, "Value", targetR, "Value"); link(gin, S_BGAP, targetR, "Value_001")
deficit0 = mth('SUBTRACT', F_cont, (10120, 1560))
link(targetR, "Value", deficit0, "Value"); link(signedD, "Value", deficit0, "Value_001")
deficit1a = mth('MAXIMUM', F_cont, (10300, 1560), v2=0.0)
link(deficit0, "Value", deficit1a, "Value")
# cap the push at one row: without it a point in the crease between two walls gets
# flung across the shape
deficit1 = mth('MINIMUM', F_cont, (10300, 1700))
link(deficit1a, "Value", deficit1, "Value"); link(rowR, "Attribute", deficit1, "Value_001")
deficit = switch('FLOAT', F_cont, (10480, 1560))           # no wall -> no relaxation
link(proxR, "Is Valid", deficit, "Switch")
isock(deficit, "False").default_value = 0.0
link(deficit1, "Value", deficit, "True")
relaxV = vmath('SCALE', F_cont, (10660, 1180))
link(gradR, "Vector", relaxV, "Vector"); link(deficit, "Output", relaxV, "Scale")
cRelax = mk("GeometryNodeSetPosition", F_cont, (10840, 1120))
link(cPos, "Geometry", cRelax, "Geometry"); link(relaxV, "Vector", cRelax, "Offset")

# A convex corner shortens the offset outline, so the points that were evenly spaced on
# the original wall arrive on top of each other. Collapse those into one tile.
# Keyed to the TILE, not to the spacing along the wall: at Contour Spacing > 1 a
# spacing-relative radius swallowed legitimate neighbours and averaged their tangents,
# which tilted the bricks off the wall they are supposed to run along.
mergeD0 = mth('MULTIPLY', F_cont, (10660, 980), v2=0.7)
link(cl, "Output", mergeD0, "Value")
# ...but never wide enough to swallow the NEXT row, which sits one rowPitch away
mergeCap = mth('MULTIPLY', F_cont, (10660, 820), v2=0.45)
link(rowPitch, "Value", mergeCap, "Value")
mergeD = mth('MINIMUM', F_cont, (10840, 900))
link(mergeD0, "Value", mergeD, "Value"); link(mergeCap, "Value", mergeD, "Value_001")
cMerge = mk("GeometryNodeMergeByDistance", F_cont, (11020, 900))
link(cRelax, "Geometry", cMerge, "Geometry"); link(mergeD, "Value", cMerge, "Distance")

# drop contour points that fell outside the region (narrow spots, concave corners)
posC2 = pos_node(F_cont, (8680, 660))
upC2 = vmath('SCALE', F_cont, (8680, 520))
link(N, "Vector", upC2, "Vector"); link(rayLen, "Value", upC2, "Scale")
srcC2 = vmath('ADD', F_cont, (8860, 600))
link(posC2, "Position", srcC2, "Vector"); link(upC2, "Vector", srcC2, "Vector_001")
rcC2 = mk("GeometryNodeRaycast", F_cont, (9040, 600))
link(canvas, "Geometry", rcC2, "Target Geometry")
link(srcC2, "Vector", rcC2, "Source Position")
link(down, "Vector", rcC2, "Ray Direction")
link(rayLen2, "Value", rcC2, "Ray Length")
proxC2 = mk("GeometryNodeProximity", F_cont, (9040, 400), target_element='EDGES')
link(bndGeo, "Selection", proxC2, "Target")
link(posC2, "Position", proxC2, "Source Position")
minD = mth('MULTIPLY', F_cont, (9040, 240), v2=0.25); link(cw, "Output", minD, "Value")
farC2 = cmp('GREATER_THAN', 'FLOAT', F_cont, (9220, 400))
link(proxC2, "Distance", farC2, "A"); link(minD, "Value", farC2, "B")
# a point nowhere near its row's distance came from a folded stretch -- drop it rather
# than stack a tile on one already there
rowA = named('FLOAT', F_cont, (9040, 60), A_ROW)
devi0 = mth('SUBTRACT', F_cont, (9220, 60))
link(proxC2, "Distance", devi0, "Value"); link(rowA, "Attribute", devi0, "Value_001")
devi = mth('ABSOLUTE', F_cont, (9400, 60)); link(devi0, "Value", devi, "Value")
tolR = mth('MULTIPLY', F_cont, (9220, -80), v2=0.75); link(rowPitch, "Value", tolR, "Value")
onRow = cmp('LESS_THAN', 'FLOAT', F_cont, (9580, 60))
link(devi, "Value", onRow, "A"); link(tolR, "Value", onRow, "B")
okC2a = boolm('AND', F_cont, (9400, 500))
link(rcC2, "Is Hit", okC2a, 0); link(farC2, "Result", okC2a, 1)
okC2 = boolm('AND', F_cont, (9760, 500))
link(okC2a, "Boolean", okC2, 0); link(onRow, "Result", okC2, 1)
dropC2 = boolm('NOT', F_cont, (9940, 500)); link(okC2, "Boolean", dropC2, 0)
cClean = mk("GeometryNodeDeleteGeometry", F_cont, (11200, 900), domain='POINT', mode='ALL')
link(cMerge, "Geometry", cClean, "Geometry"); link(dropC2, "Boolean", cClean, "Selection")


# one quad per contour point, running along the outline
cQuad = mk("GeometryNodeMeshGrid", F_cont, (10120, 700))
link(cl, "Output", cQuad, "Size X"); link(cw, "Output", cQuad, "Size Y")
isock(cQuad, "Vertices X").default_value = 2
isock(cQuad, "Vertices Y").default_value = 2

cIdx2 = idx_node(F_cont, (9760, 200))
sdCR = mth('ADD', F_cont, (9760, 60), v2=151.0); link(gin, S_SEED, sdCR, "Value")
cRotR = rnd('FLOAT', F_cont, (9940, 200))
link(cIdx2, "Index", cRotR, "ID"); link(sdCR, "Value", cRotR, "Seed")
cRotN = mth('MULTIPLY', F_cont, (9760, -80), v2=-1.0); link(gin, S_RJIT, cRotN, "Value")
link(cRotN, "Value", cRotR, "Min"); link(gin, S_RJIT, cRotR, "Max")
cTanR = vrot(F_cont, (10120, 200))
link(tanU, "Vector", cTanR, "Vector"); link(N, "Vector", cTanR, "Axis")
link(cRotR, "Value", cTanR, "Angle")
cRot = mk("FunctionNodeAxesToRotation", F_cont, (10300, 200),
          primary_axis='Z', secondary_axis='X')
link(N, "Vector", cRot, "Primary Axis"); link(cTanR, "Vector", cRot, "Secondary Axis")

sdCS = mth('ADD', F_cont, (9760, -260), v2=173.0); link(gin, S_SEED, sdCS, "Value")
cSclR = rnd('FLOAT', F_cont, (9940, -220))
link(cIdx2, "Index", cSclR, "ID"); link(sdCS, "Value", cSclR, "Seed")
cSMin = mth('SUBTRACT', F_cont, (9760, -400), v1=1.0); link(gin, S_SVAR, cSMin, "Value_001")
cSMax = mth('ADD', F_cont, (9760, -540), v1=1.0);      link(gin, S_SVAR, cSMax, "Value_001")
link(cSMin, "Value", cSclR, "Min"); link(cSMax, "Value", cSclR, "Max")
cSclV = mk("ShaderNodeCombineXYZ", F_cont, (10120, -220))
link(cSclR, "Value", cSclV, "X"); link(cSclR, "Value", cSclV, "Y")
isock(cSclV, "Z").default_value = 1.0

cInst = mk("GeometryNodeInstanceOnPoints", F_cont, (10480, 900))
link(cClean, "Geometry", cInst, "Points"); link(cQuad, "Mesh", cInst, "Instance")
link(cRot, "Rotation", cInst, "Rotation"); link(cSclV, "Vector", cInst, "Scale")
cReal = mk("GeometryNodeRealizeInstances", F_cont, (10680, 900))
link(cInst, "Instances", cReal, "Geometry")

# split a share of the contour tiles into triangles, exactly as the grid fill does:
# two passes with opposite fixed diagonals so the split direction varies
ctIdx = idx_node(F_cont, (10680, 300))
sdCT = mth('ADD', F_cont, (10680, 140), v2=311.0); link(gin, S_SEED, sdCT, "Value")
ctR = rnd('FLOAT', F_cont, (10860, 300))
link(ctIdx, "Index", ctR, "ID"); link(sdCT, "Value", ctR, "Seed")
sdCD = mth('ADD', F_cont, (10680, -20), v2=337.0); link(gin, S_SEED, sdCD, "Value")
cdR = rnd('FLOAT', F_cont, (10860, 140))
link(ctIdx, "Index", cdR, "ID"); link(sdCD, "Value", cdR, "Seed")
ctIs = cmp('LESS_THAN', 'FLOAT', F_cont, (11040, 300))
link(ctR, "Value", ctIs, "A"); link(gin, S_CTRI, ctIs, "B")
cdLow = cmp('LESS_THAN', 'FLOAT', F_cont, (11040, 140))
link(cdR, "Value", cdLow, "A"); isock(cdLow, "B").default_value = 0.5
cdNot = boolm('NOT', F_cont, (11220, 60)); link(cdLow, "Result", cdNot, 0)
ctSelA = boolm('AND', F_cont, (11220, 300))
link(ctIs, "Result", ctSelA, 0); link(cdLow, "Result", ctSelA, 1)
ctSelB = boolm('AND', F_cont, (11220, 180))
link(ctIs, "Result", ctSelB, 0); link(cdNot, "Boolean", ctSelB, 1)
ctA = mk("GeometryNodeTriangulate", F_cont, (11400, 900))
link(cReal, "Geometry", ctA, "Mesh"); link(ctSelA, "Boolean", ctA, "Selection")
isock(ctA, "Quad Method").default_value = "Fixed"
ctB = mk("GeometryNodeTriangulate", F_cont, (11580, 900))
link(ctA, "Mesh", ctB, "Mesh"); link(ctSelB, "Boolean", ctB, "Selection")
isock(ctB, "Quad Method").default_value = "Fixed Alternate"
# separate every contour tile again so the halves of a split one move independently
ctLoose = mk("GeometryNodeSplitEdges", F_cont, (11760, 900))
link(ctB, "Mesh", ctLoose, "Mesh")

cOn = cmp('GREATER_THAN', 'INT', F_cont, (10480, 620))
link(gin, S_ROWS, cOn, "A_INT"); isock(cOn, "B_INT").default_value = 0
cGate = switch('GEOMETRY', F_cont, (10880, 900))
link(cOn, "Result", cGate, "Switch"); link(ctLoose, "Mesh", cGate, "True")

allTiles = mk("GeometryNodeJoinGeometry", F_cont, (11080, 500))
link(tilesPick, "Output", allTiles, "Geometry")
link(cGate, "Output", allTiles, "Geometry")

# ============================================================================= 13. CUT
# vertices hanging outside their region are snapped onto the nearest boundary point
posX = pos_node(F_cut, (11080, 100))
upX = vmath('SCALE', F_cut, (11080, -40))
link(N, "Vector", upX, "Vector"); link(rayLen, "Value", upX, "Scale")
srcX = vmath('ADD', F_cut, (11260, 40))
link(posX, "Position", srcX, "Vector"); link(upX, "Vector", srcX, "Vector_001")
regAttrX = named('INT', F_cut, (11260, -120), A_REGION)
rcX = mk("GeometryNodeRaycast", F_cut, (11440, 40), data_type='INT')
isock(rcX, "Interpolation").default_value = "Nearest"
link(canvas, "Geometry", rcX, "Target Geometry")
link(regAttrX, "Attribute", rcX, "Attribute")
link(srcX, "Vector", rcX, "Source Position")
link(down, "Vector", rcX, "Ray Direction")
link(rayLen2, "Value", rcX, "Ray Length")
missX = boolm('NOT', F_cut, (11620, 140)); link(rcX, "Is Hit", missX, 0)

# A vertex can be well inside the SURFACE and still be on the wrong side of an internal
# wall -- the canvas is never split, so the raycast happily hits the neighbouring region.
# Cutting therefore has to test the region too, or nothing ever hugs an interior loop.
rcFace = mk("GeometryNodeRaycast", F_cut, (11440, -420), data_type='INT')
isock(rcFace, "Interpolation").default_value = "Nearest"
link(canvas, "Geometry", rcFace, "Target Geometry")
link(regAttrX, "Attribute", rcFace, "Attribute")
link(srcX, "Vector", rcFace, "Source Position")     # FACE context -> the tile centre
link(down, "Vector", rcFace, "Ray Direction")
link(rayLen2, "Value", rcFace, "Ray Length")
tileReg = mk("GeometryNodeFieldOnDomain", F_cut, (11620, -420),
             domain='FACE', data_type='INT')
link(rcFace, "Attribute", tileReg, "Value")
crossed = cmp('NOT_EQUAL', 'INT', F_cut, (11800, -280))
link(rcX, "Attribute", crossed, "A_INT"); link(tileReg, "Value", crossed, "B_INT")
outX = boolm('OR', F_cut, (11980, 60))
link(missX, "Boolean", outX, 0); link(crossed, "Result", outX, 1)

proxX = mk("GeometryNodeProximity", F_cut, (11440, -180), target_element='EDGES')
link(bndGeo, "Selection", proxX, "Target"); link(posX, "Position", proxX, "Source Position")

# A vertex is reshaped when it is on the wrong side of a wall OR sitting inside the
# boundary grout. Both end up on the same line -- Boundary Gap away from the real
# outline -- so the tile edge traces the boundary shape and is then held back by the
# gap, rather than simply being clipped flat against it.
tooNear = cmp('LESS_THAN', 'FLOAT', F_cut, (11800, -140))
link(proxX, "Distance", tooNear, "A"); link(gin, S_BGAP, tooNear, "B")
needFit = boolm('OR', F_cut, (11980, -100))
link(outX, "Boolean", needFit, 0); link(tooNear, "Result", needFit, 1)
cutOn0 = boolm('AND', F_cut, (12160, 60))
link(needFit, "Boolean", cutOn0, 0); link(proxX, "Is Valid", cutOn0, 1)  # no walls -> nothing to fit to
cutOn = boolm('AND', F_cut, (12340, 60))
link(cutOn0, "Boolean", cutOn, 0); link(gin, S_CUT, cutOn, 1)

# where to put it: the closest point ON the wall, stepped back towards the tile's own
# middle by Boundary Gap. Using the tile centroid keeps the reshaped tile convex --
# snapping straight onto the wall folds a quad whenever two corners share one target.
islX = mk("GeometryNodeInputMeshIsland", F_cut, (11080, -560))
accXn = mk("GeometryNodeAccumulateField", F_cut, (11260, -520),
           data_type='FLOAT', domain='POINT')
isock(accXn, "Value").default_value = 1.0
link(islX, "Island Index", accXn, "Group Index")
accXp = mk("GeometryNodeAccumulateField", F_cut, (11260, -680),
           data_type='FLOAT_VECTOR', domain='POINT')
link(posX, "Position", accXp, "Value"); link(islX, "Island Index", accXp, "Group Index")
cntX = mk("ShaderNodeCombineXYZ", F_cut, (11440, -520))
for k in ("X", "Y", "Z"): link(accXn, "Total", cntX, k)
cenX = vmath('DIVIDE', F_cut, (11620, -620))
link(accXp, "Total", cenX, "Vector"); link(cntX, "Vector", cenX, "Vector_001")
# Which way is "off the wall"?  Always the wall's own perpendicular, signed by which
# side the vertex is on: a vertex inside but within the grout moves straight out, one
# that crossed the wall moves straight back in. Aiming at the tile centre instead drags
# vertices sideways past their neighbours and bites notches out of the tile.
inDirC0 = vmath('SUBTRACT', F_cut, (11800, -900))
link(cenX, "Vector", inDirC0, "Vector"); link(proxX, "Position", inDirC0, "Vector_001")
inDirC = vmath('NORMALIZE', F_cut, (11980, -900)); link(inDirC0, "Vector", inDirC, "Vector")
inDirP0 = vmath('SUBTRACT', F_cut, (11800, -620))
link(posX, "Position", inDirP0, "Vector"); link(proxX, "Position", inDirP0, "Vector_001")
inDirP = vmath('NORMALIZE', F_cut, (11980, -620)); link(inDirP0, "Vector", inDirP, "Vector")
insideX = boolm('NOT', F_cut, (11800, -480)); link(outX, "Boolean", insideX, 0)
sgnX = switch('FLOAT', F_cut, (11980, -480))
link(insideX, "Boolean", sgnX, "Switch")
isock(sgnX, "False").default_value = -1.0
isock(sgnX, "True").default_value = 1.0
dirSigned = vmath('SCALE', F_cut, (12160, -620))
link(inDirP, "Vector", dirSigned, "Vector"); link(sgnX, "Output", dirSigned, "Scale")
# a vertex sitting exactly on the wall has no perpendicular -- fall back to the centroid
lenX = vmath('LENGTH', F_cut, (11980, -1040)); link(inDirP0, "Vector", lenX, "Vector")
degenX = cmp('LESS_THAN', 'FLOAT', F_cut, (12160, -1040))
link(lenX, "Value", degenX, "A"); isock(degenX, "B").default_value = 1e-6
inDirX = switch('VECTOR', F_cut, (12160, -760))
link(degenX, "Result", inDirX, "Switch")
link(dirSigned, "Vector", inDirX, "False")
link(inDirC, "Vector", inDirX, "True")
gapVX = vmath('SCALE', F_cut, (12340, -760))
link(inDirX, "Output", gapVX, "Vector"); link(gin, S_BGAP, gapVX, "Scale")
fitPos = vmath('ADD', F_cut, (12520, -620))
link(proxX, "Position", fitPos, "Vector"); link(gapVX, "Vector", fitPos, "Vector_001")
cutPos = mk("GeometryNodeSetPosition", F_cut, (12520, 300))
link(allTiles, "Geometry", cutPos, "Geometry")
link(cutOn, "Boolean", cutPos, "Selection")
link(fitPos, "Vector", cutPos, "Position")

# ============================================================================= 14. CONFORM
posY = pos_node(F_cnf, (11980, -200))
upY = vmath('SCALE', F_cnf, (11980, -340))
link(N, "Vector", upY, "Vector"); link(rayLen, "Value", upY, "Scale")
srcY = vmath('ADD', F_cnf, (12160, -260))
link(posY, "Position", srcY, "Vector"); link(upY, "Vector", srcY, "Vector_001")
rcY = mk("GeometryNodeRaycast", F_cnf, (12340, -260))
link(canvas, "Geometry", rcY, "Target Geometry")
link(srcY, "Vector", rcY, "Source Position")
link(down, "Vector", rcY, "Ray Direction")
link(rayLen2, "Value", rcY, "Ray Length")
onSurf = switch('VECTOR', F_cnf, (12520, -160))            # miss -> keep the flat position
link(rcY, "Is Hit", onSurf, "Switch")
link(posY, "Position", onSurf, "False"); link(rcY, "Hit Position", onSurf, "True")
confPos = switch('VECTOR', F_cnf, (12700, -160))
link(gin, S_CONF, confPos, "Switch")
link(posY, "Position", confPos, "False"); link(onSurf, "Output", confPos, "True")
offDir = switch('VECTOR', F_cnf, (12520, -400))
link(rcY, "Is Hit", offDir, "Switch")
link(N, "Vector", offDir, "False"); link(rcY, "Hit Normal", offDir, "True")
offV = vmath('SCALE', F_cnf, (12700, -400))
link(offDir, "Output", offV, "Vector"); link(gin, S_SOFF, offV, "Scale")
finPos = vmath('ADD', F_cnf, (12880, -260))
link(confPos, "Output", finPos, "Vector"); link(offV, "Vector", finPos, "Vector_001")
conformed = mk("GeometryNodeSetPosition", F_cnf, (13060, 200))
link(cutPos, "Geometry", conformed, "Geometry"); link(finPos, "Vector", conformed, "Position")

# ============================================================================= 15. ATTRIBUTES
# In a FACE context Position evaluates to the face centre, so one raycast tags every
# finished tile -- grid tiles and contour tiles alike -- with the region under it.
posA = pos_node(F_attr, (13060, -140))
upA = vmath('SCALE', F_attr, (13060, -280))
link(N, "Vector", upA, "Vector"); link(rayLen, "Value", upA, "Scale")
srcA = vmath('ADD', F_attr, (13240, -200))
link(posA, "Position", srcA, "Vector"); link(upA, "Vector", srcA, "Vector_001")
regAttrA = named('INT', F_attr, (13240, -380), A_REGION)
rcA = mk("GeometryNodeRaycast", F_attr, (13420, -200), data_type='INT')
isock(rcA, "Interpolation").default_value = "Nearest"
link(canvas, "Geometry", rcA, "Target Geometry")
link(regAttrA, "Attribute", rcA, "Attribute")
link(srcA, "Vector", rcA, "Source Position")
link(down, "Vector", rcA, "Ray Direction")
link(rayLen2, "Value", rcA, "Ray Length")
stReg = mk("GeometryNodeStoreNamedAttribute", F_attr, (13620, 200),
           data_type='INT', domain='FACE')
link(conformed, "Geometry", stReg, "Geometry")
link(gin, S_NREG, stReg, "Name"); link(rcA, "Attribute", stReg, "Value")

aIdx = idx_node(F_attr, (13620, -60))
stTid = mk("GeometryNodeStoreNamedAttribute", F_attr, (13800, 200),
           data_type='INT', domain='FACE')
link(stReg, "Geometry", stTid, "Geometry")
link(gin, S_NTID, stTid, "Name"); link(aIdx, "Index", stTid, "Value")

sdRnd = mth('ADD', F_attr, (13620, -220), v2=131.0); link(gin, S_SEED, sdRnd, "Value")
tRnd = rnd('FLOAT', F_attr, (13800, -160))
link(aIdx, "Index", tRnd, "ID"); link(sdRnd, "Value", tRnd, "Seed")
stRnd = mk("GeometryNodeStoreNamedAttribute", F_attr, (13980, 200),
           data_type='FLOAT', domain='FACE')
link(stTid, "Geometry", stRnd, "Geometry")
link(gin, S_NRND, stRnd, "Name"); link(tRnd, "Value", stRnd, "Value")

sdCol = mth('ADD', F_attr, (13620, -400), v2=211.0); link(gin, S_SEED, sdCol, "Value")
# Stored on CORNER -- the domain Blender's own colour attributes live on, so the
# result behaves like a normal colour attribute everywhere (shader Attribute node,
# Color Attribute panel, bake). Because the store runs in a CORNER context, `Index`
# would be the CORNER index and paint a gradient across each tile; the per-tile id
# has to be the FACE index evaluated in that context instead.
faceOfCorner = mk("GeometryNodeFieldOnDomain", F_attr, (13620, -560),
                  domain='FACE', data_type='INT')
link(aIdx, "Index", faceOfCorner, "Value")
tCol = rnd('FLOAT_VECTOR', F_attr, (13800, -380))
isock(tCol, "Min").default_value = (0.0, 0.0, 0.0)
isock(tCol, "Max").default_value = (1.0, 1.0, 1.0)
link(faceOfCorner, "Value", tCol, "ID"); link(sdCol, "Value", tCol, "Seed")
stCol = mk("GeometryNodeStoreNamedAttribute", F_attr, (14160, 200),
           data_type='FLOAT_COLOR', domain='CORNER')
link(stRnd, "Geometry", stCol, "Geometry")
link(gin, S_NCOL, stCol, "Name"); link(tCol, "Value", stCol, "Value")

# the bookkeeping attributes are an implementation detail -- do not leak them
prev = stCol
for i, aname in enumerate((A_TRI, A_DIAG, A_TILE, A_ROW, A_TAN,
                           A_NC, A_MI, A_MJ, A_BI, A_BD, A_SS, A_N1, A_N2, *A_V, *A_T)):
    rm = mk("GeometryNodeRemoveAttribute", F_attr, (14340 + i * 180, 200))
    link(prev, "Geometry", rm, "Geometry")
    isock(rm, "Name").default_value = aname
    prev = rm
clean = prev

# ============================================================================= 16. OUTPUT
thkNrm = mk("GeometryNodeInputNormal", F_fin, (15100, -120))
ext = mk("GeometryNodeExtrudeMesh", F_fin, (15280, 200), mode='FACES')
link(clean, "Geometry", ext, "Mesh")
link(thkNrm, "True Normal", ext, "Offset")
link(gin, S_THK, ext, "Offset Scale")
isock(ext, "Individual").default_value = True
thkOn = cmp('GREATER_THAN', 'FLOAT', F_fin, (15280, -60))
link(gin, S_THK, thkOn, "A"); isock(thkOn, "B").default_value = 1e-6
thkGate = switch('GEOMETRY', F_fin, (15480, 200))
link(thkOn, "Result", thkGate, "Switch")
link(clean, "Geometry", thkGate, "False"); link(ext, "Mesh", thkGate, "True")

setMat = mk("GeometryNodeSetMaterial", F_fin, (15660, 200))
link(thkGate, "Output", setMat, "Geometry"); link(gin, S_MAT, setMat, "Material")

withSrc = mk("GeometryNodeJoinGeometry", F_fin, (15840, 40))
link(setMat, "Geometry", withSrc, "Geometry"); link(gin, S_GEO, withSrc, "Geometry")
keepGate = switch('GEOMETRY', F_fin, (16020, 200))
link(gin, S_KEEP, keepGate, "Switch")
link(setMat, "Geometry", keepGate, "False"); link(withSrc, "Geometry", keepGate, "True")
link(keepGate, "Output", gout, "Geometry")

gout.location = (16240, 200)

# menu defaults must be set AFTER the Group Input is wired to their Menu Switch
iface.items_tree[S_TMODE].default_value = "Grid"
iface.items_tree[S_AXIS].default_value = "Auto"
iface.items_tree[S_FIT].default_value  = "Center Inside"

# ============================================================================= DEMO OBJECT
# Two organic shapes so the demo shows: an outline of any form, a hole in it (both
# picked up by "Use Open Edges"), and two separate regions with distinct region ids.
def blobA(t): return 1.55 + 0.30 * math.sin(3 * t) + 0.12 * math.sin(7 * t + 1.1)
def blobB(t): return 1.15 + 0.34 * math.sin(5 * t)

def ring_mesh(bm, outer_fn, inner_r, cx, na, nr):
    """well-shaped radial quad grid between an inner radius and an organic outline.
    A proper topology matters here: the Shatter mode subdivides the input's own faces,
    and longest-edge bisection provably cannot repair a bad triangulation -- it preserves
    the worst angle it starts with. A fan-filled n-gon would hand it slivers to inherit."""
    grid = []
    for i in range(na):
        t = 2.0 * math.pi * i / na
        rO = outer_fn(t)
        col = []
        for j in range(nr + 1):
            f = j / nr
            r = inner_r + (rO - inner_r) * f
            col.append(bm.verts.new((r * math.cos(t) + cx, r * math.sin(t), 0.0)))
        grid.append(col)
    for i in range(na):
        k = (i + 1) % na
        for j in range(nr):
            bm.faces.new((grid[i][j], grid[k][j], grid[k][j + 1], grid[i][j + 1]))
    return grid

def disc_mesh(bm, outer_fn, cx, na, nr):
    """same, but filled to a single centre vertex with a triangle fan"""
    hub = bm.verts.new((cx, 0.0, 0.0))
    grid = []
    for i in range(na):
        t = 2.0 * math.pi * i / na
        rO = outer_fn(t)
        grid.append([bm.verts.new(((rO * (j + 1) / nr) * math.cos(t) + cx,
                                   (rO * (j + 1) / nr) * math.sin(t), 0.0))
                     for j in range(nr)])
    for i in range(na):
        k = (i + 1) % na
        bm.faces.new((hub, grid[i][0], grid[k][0]))
        for j in range(nr - 1):
            bm.faces.new((grid[i][j], grid[k][j], grid[k][j + 1], grid[i][j + 1]))

if "Cube" in bpy.data.objects:                 # factory-startup leftover
    bpy.data.objects.remove(bpy.data.objects["Cube"], do_unlink=True)

me = bpy.data.meshes.new("GN_Demo")
bm = bmesh.new()
# blob A: organic outline with a round hole -- both rims are OPEN edges, so "Use Open
# Edges" alone bounds the mosaic to the ring between them
ring_mesh(bm, blobA, 0.52, -1.9, 96, 7)
# blob B: a separate island -> a second region with its own region id
disc_mesh(bm, blobB, 2.35, 80, 6)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
# a flat mesh has no inside for recalc to orient against, so pin it to +Z -- otherwise
# the Auto projection axis reads the average normal as -Z and Surface Offset lifts the
# tiles the wrong way
if sum(f.normal.z for f in bm.faces) < 0.0:
    bmesh.ops.reverse_faces(bm, faces=bm.faces[:])
print("DEMO faces:", len(bm.faces), "verts:", len(bm.verts),
      "avg normal z:", round(sum(f.normal.z for f in bm.faces) / len(bm.faces), 3))
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
    "Fill the bounded areas of a mesh with mosaic tesserae. Edge loops -- a marked "
    "Boundary Edges field and/or the mesh's own open edges -- cut the surface into "
    "regions, and every region is packed with tiles that stop at its outline, however "
    "organic. Grid mode intersects a warped square/triangle lattice with the region "
    "(fit modes, edge margin, adaptive tile sizes near walls); Shatter mode instead "
    "partitions the region's own faces by recursive edge cutting for exact coverage "
    "with 3-6 sided tiles, and can be made seamlessly tileable across a bounds box. "
    "Contour Rows lay N rows of tiles following the outline (opus vermiculatum). "
    "Outputs a unique tile_id per tile plus region_id, tile_random and a tile_color "
    "corner attribute for shading."
)
ng.is_modifier = True
ng.is_tool = False

bpy.ops.wm.save_as_mainfile(filepath=PATH)
print("SAVED", PATH, "| nodes:", len(ng.nodes))
sys.stdout.flush()
os._exit(0)
