# -*- coding: utf-8 -*-
"""Generates an annotated documentation image for Mass Collection Exporter
v13.3.3 by overlaying labelled boxes + metro-style connectors onto the
captured N-panel screenshot.

Mirrors the layout of `QuickAnimationExport/_make_annotated_doc.py` so the
two docs feel like a matched set.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"D:/Stephko_Tooling/Toolings/Blender/Addons/ClaudeVibe_WIPs"
SRC = os.path.join(ROOT, "mass_exporter_panel.png")
OUT = os.path.join(ROOT, "MassExporter_v13.3.3_docs.png")

# Panel paste offset in the final canvas.
PASTE_X = 1820
PASTE_Y = 80

BG = (63, 63, 63, 255)


# ---------- Fonts ----------
def load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for p in candidates:
        if os.path.isfile(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

F_TITLE   = load_font(32, bold=True)
F_SUB     = load_font(15)
F_HEADING = load_font(17, bold=True)
F_BODY    = load_font(14)
F_EX      = load_font(13)
F_SMALL   = load_font(12)


# ---------- Colour groups ----------
GROUPS = {
    "action":    (0xFF, 0x6B, 0x6B),  # red — primary action buttons
    "control":   (0xE6, 0x95, 0x4C),  # orange — global toggles (hidden, debug)
    "quick":     (0x5B, 0xA3, 0xF5),  # blue — quick export from selection
    "list":      (0x4D, 0xD0, 0xE1),  # cyan — collection list + columns
    "perlist":   (0x67, 0xD8, 0x8B),  # green — per-collection options
    "transform": (0xC7, 0x7D, 0xFF),  # purple — transform options
    "material":  (0xFF, 0x99, 0x33),  # orange-2 — material options
    "modifier":  (0xFF, 0xD9, 0x3D),  # yellow — modifier / rig options
    "file":      (0xB0, 0xBE, 0xC5),  # light grey — file export options
    "suffix":    (0xFF, 0xB3, 0xD9),  # pink — suffix grouping
    "debug":     (0xA0, 0xA0, 0xA0),  # grey — debug controls
    "header":    (0xFF, 0xCC, 0x66),  # gold — viewport header button (separate)
}


# ---------- Field annotations ----------
# field_box uses PANEL-CROP coordinates (panel image is 980x1760). y-values
# were verified against a 2x ruler overlay. The draw step adds (PASTE_X,
# PASTE_Y) so the same numbers stay easy to verify against the source crop.
FIELDS = [
    # 1 — Export All Collections (primary action)
    dict(
        group="action",
        field_box=(20, 115, 970, 150),
        title="Export All Collections",
        body=[
            "The primary action. Iterates every row in the Collection list",
            "whose Export checkbox is ON, then writes each to its configured",
            "Export Path using the active File Export Options.",
        ],
        examples=["3 enabled rows  ->  3 FBX files written this run"],
    ),
    # 2 — Export Hidden Collections
    dict(
        group="control",
        field_box=(20, 152, 970, 178),
        title="Export Hidden Collections",
        body=[
            "Temporarily unhide hidden objects (outliner eye, hide_viewport,",
            "layer-collection exclude, local view) so they participate, then",
            "restore. When OFF, hidden collections are skipped with a warning.",
            "Default: ON.",
        ],
        examples=["Reason: Blender's FBX exporter silently drops hidden",
                  "objects — this toggle prevents accidental data loss."],
    ),
    # 3 — Export Selected Object(s)
    dict(
        group="quick",
        field_box=(20, 235, 970, 270),
        title="Export Selected Object(s)",
        body=[
            "Quick export scoped to the viewport selection. Exports ONLY the",
            "selected objects (not their whole collection) but honours the",
            "parent collection's Merge / Suffix Grouping / Sub-Collections",
            "as Single settings.",
        ],
    ),
    # 4 — Export Collection of Selected
    dict(
        group="quick",
        field_box=(20, 275, 970, 310),
        title="Export Collection of Selected",
        body=[
            "Finds the immediate collection containing the selected object",
            "and exports it. The collection does NOT need to be enabled in",
            "the list first — handy for ad-hoc one-off exports.",
        ],
    ),
    # 5 — Export Sub-Collections of Selected
    dict(
        group="quick",
        field_box=(20, 312, 970, 348),
        title="Export Sub-Collections of Selected",
        body=[
            "Walks one level into the selected collection and exports each",
            "of its child collections as its own file. Useful when a parent",
            "collection groups several modular variants you want shipped",
            "as separate FBXs.",
        ],
    ),
    # 6 — Debug Mode
    dict(
        group="control",
        field_box=(20, 372, 970, 398),
        title="Debug Mode",
        body=[
            "Prints verbose status to the system console: which objects are",
            "processed, what's joined, what's skipped, resolved paths,",
            "modifier-eval steps, etc.",
            "Flip on before reporting a bug. Default: OFF.",
        ],
    ),
    # 7 — Collection List (the UIList with all five columns)
    dict(
        group="list",
        field_box=(20, 445, 970, 590),
        title="Collection List (Collection Options panel)",
        body=[
            "The core export queue. Each row has five columns:",
            "• Eye — mirrors the outliner eye (LayerCollection.hide_viewport).",
            "• Export checkbox — include this row in Export All Collections.",
            "• Merge icon — merge all meshes in this collection into one file.",
            "• Collection picker — the actual bpy.types.Collection.",
            "• Export Path — destination folder for this row's FBX(s).",
            "Side buttons (right): Add row, Remove row, Refresh (rescan scene).",
        ],
        examples=["Per-row settings are independent — different collections",
                  "can target different folders or merge modes in one run."],
    ),
    # 8 — Sub-Collections as Single (per-row enhanced option)
    dict(
        group="perlist",
        field_box=(20, 647, 970, 672),
        title="Sub-Collections as Single",
        body=[
            "Per-row enhanced option for the row selected above. When ON,",
            "each child collection is merged into one mesh and exported as",
            "one FBX. When OFF, each sub-collection is its own file.",
        ],
        examples=["Useful when each sub-collection is one modular asset",
                  "variant that should ship as a single mesh."],
    ),
    # 9 — Use Parent Empties
    dict(
        group="perlist",
        field_box=(20, 678, 970, 703),
        title="Use Parent Empties",
        body=[
            "Per-row. When ON, the exporter searches for parent empties and",
            "uses each empty's transform as the origin/centre for the meshes",
            "parented to it. Reveals two extra sub-panels (Empty Options +",
            "Join Options) for centring + join behaviour.",
        ],
    ),
    # 10 — Export at Origin
    dict(
        group="transform",
        field_box=(20, 754, 970, 779),
        title="Export at Origin",
        body=[
            "Move each export's pivot to world (0,0,0) during the export call,",
            "then restore. Produces engine-ready FBXs that import at world",
            "origin instead of carrying the source-scene placement.",
        ],
    ),
    # 11 — Apply Transforms
    dict(
        group="transform",
        field_box=(20, 785, 970, 810),
        title="Apply Transforms",
        body=[
            "Bake object location / rotation / scale into mesh data so the",
            "exported FBX object has identity transform. Avoids surprises",
            "when an engine doesn't honour the original transform.",
        ],
    ),
    # 12 — Forward / Up axes
    dict(
        group="transform",
        field_box=(20, 828, 970, 885),
        title="Transform Axis Settings — Forward / Up",
        body=[
            "Coordinate-system axes baked into the FBX. Defaults:",
            "-Z Forward, Y Up — what Unity expects.",
            "Note: the same two properties also appear inside File Export",
            "Options > FBX. Edit either — they refer to the same prop.",
        ],
    ),
    # 13 — Material Options (collapsed header)
    dict(
        group="material",
        field_box=(20, 898, 970, 925),
        title="Material Options (collapsed)",
        body=[
            "Click to expand. Houses optional material substitution:",
            "• Override Materials — replace every assigned material with one",
            "  shared material on export (scene unchanged).",
            "• Override Material — the replacement (only enabled when",
            "  Override Materials is on).",
            "• Assign Override Material if No Material — covers objects with",
            "  no material slot at all.",
            "• Add M_ Prefix if Missing — Unity/Unreal naming convention,",
            "  prepends 'M_' to material names that lack it.",
        ],
    ),
    # 14 — Apply Modifiers
    dict(
        group="modifier",
        field_box=(20, 1005, 970, 1035),
        title="Apply Modifiers",
        body=[
            "Apply every modifier on every exported mesh. Required for",
            "displacement / array / boolean / subdivision output to show",
            "up in the FBX. Default: ON.",
        ],
    ),
    # 15 — Export Rig with Mesh
    dict(
        group="modifier",
        field_box=(20, 1085, 970, 1115),
        title="Export Rig with Mesh",
        body=[
            "Include the Armature object referenced by any Armature modifier,",
            "even when it lives outside the export collection. Default: OFF.",
            "Turn on when you need the rig to land in the FBX alongside the",
            "skinned mesh.",
        ],
    ),
    # 16 — Skip Armature Modifier
    dict(
        group="modifier",
        field_box=(20, 1118, 970, 1148),
        title="Skip Armature Modifier",
        body=[
            "When applying modifiers, leave Armature modifiers in place so",
            "the mesh ships in its rest pose (no skinning baked in).",
            "Greyed out unless Apply Modifiers is ON.",
        ],
        examples=["Combo for skinned export: Apply Modifiers ON + Skip",
                  "Armature Modifier ON + Export Rig with Mesh ON."],
    ),
    # 17 — File Export Options (collapsed header)
    dict(
        group="file",
        field_box=(20, 1163, 970, 1193),
        title="File Export Options (collapsed)",
        body=[
            "Click to expand. Format + format-specific tuning:",
            "• Export Format — FBX / OBJ / DAE / glTF 2.0.",
            "• FBX-only sub-options (when format = FBX): Apply Scaling,",
            "  Apply Transform, Forward/Up axes (duplicate of Transform",
            "  Options), Primary/Secondary Bone Axis, Armature FBX Node,",
            "  Only Deform Bones, Add Leaf Bones, Custom FBX ASCII",
            "  Exporter (experimental), Unity import tips.",
            "Apply Scaling defaults to 'FBX Units Scale' (Unity-correct).",
        ],
    ),
    # 18 — Suffix Grouping info+example
    dict(
        group="suffix",
        field_box=(20, 1232, 970, 1305),
        title="Suffix Grouping — info banner",
        body=[
            "Read-only banner explaining the feature. Objects whose names",
            "share a base but differ by a registered suffix (cube,",
            "cube_COL, cube_LOD0) collapse into one FBX named after the",
            "base — standard pattern for shipping a render mesh plus its",
            "collision and LOD siblings to a game engine.",
        ],
    ),
    # 19 — Suffix List (UIList)
    dict(
        group="suffix",
        field_box=(20, 1320, 970, 1460),
        title="Suffix List",
        body=[
            "Editable list of suffix definitions. Each row has:",
            "• Enabled checkbox — turn this suffix on/off for grouping.",
            "• Suffix string — the literal trailing token to match",
            "  (case-insensitive, e.g. _COL).",
            "• Description column — label that echoes into the box below.",
            "Side buttons: Add row, Remove row.",
        ],
    ),
    # 20 — Description (active suffix)
    dict(
        group="suffix",
        field_box=(20, 1470, 970, 1502),
        title="Suffix Description (active row)",
        body=[
            "Read-only echo of the selected suffix's Description field.",
            "Confirms what a suffix is meant for without expanding the row.",
        ],
    ),
    # 21 — Add Default Suffixes
    dict(
        group="suffix",
        field_box=(20, 1518, 970, 1552),
        title="Add Default Suffixes",
        body=[
            "One-shot populator. Adds the standard game-engine set if not",
            "already present: _COL, _col, _UCX, _LOD0, _LOD1, _LOD2, _LOD3.",
            "Safe to click on a partially-populated list — duplicates skipped.",
        ],
    ),
    # 22 — Move Empties to Origin (debug)
    dict(
        group="debug",
        field_box=(20, 1595, 970, 1632),
        title="Move Empties to Origin (debug)",
        body=[
            "Standalone tool: moves every empty in the scene to world (0,0,0).",
            "Useful for previewing what the exporter does internally when",
            "Use Parent Empties + Move All Empties to Origin are set.",
            "Destructive on the scene — Ctrl-Z to undo.",
        ],
    ),
    # 23 — Join Empties (Preview)
    dict(
        group="debug",
        field_box=(20, 1632, 970, 1670),
        title="Join Empties (Preview)",
        body=[
            "Standalone tool: joins each empty's mesh children into one",
            "object so you can inspect the merge result before running a",
            "real export with Join Empty Children turned on.",
            "Destructive on the scene — Ctrl-Z to undo.",
        ],
    ),
]


# ---------- Layout constants ----------
COL_W = 800
PADDING = 12

# Metro tracks. One x-track per colour group, parallel verticals like a
# subway map. Spaced 90 px apart in the corridor between the description
# column (right edge x=840) and the panel (pasted at x=1820).
GROUP_TRACK_X = {
    "action":    900,
    "control":   990,
    "quick":     1080,
    "list":      1170,
    "perlist":   1260,
    "transform": 1350,
    "material":  1440,
    "modifier":  1530,
    "file":      1620,
    "suffix":    1710,
    "debug":     1800,
}


def measure_block(field, draw):
    lines = [("title", field["title"])]
    for b in field["body"]:
        lines.append(("body", b))
    if field.get("examples"):
        lines.append(("ex_head", "examples:"))
        for ex in field["examples"]:
            lines.append(("ex", ex))
    line_heights = []
    for kind, txt in lines:
        f = {"title": F_HEADING, "body": F_BODY, "ex_head": F_SMALL, "ex": F_EX}[kind]
        bbox = f.getbbox(txt or " ")
        line_heights.append(bbox[3] - bbox[1] + 5)
    h = sum(line_heights) + 2 * PADDING
    return lines, line_heights, h


def draw_block(draw, x, y, w, lines, line_heights, color):
    h = sum(line_heights) + 2 * PADDING
    draw.rounded_rectangle([x, y, x + w, y + h], radius=8,
                           fill=(40, 40, 40, 255), outline=color, width=2)
    cy = y + PADDING
    for (kind, txt), lh in zip(lines, line_heights):
        if kind == "title":
            f, col = F_HEADING, color
        elif kind == "body":
            f, col = F_BODY, (225, 225, 225)
        elif kind == "ex_head":
            f, col = F_SMALL, (160, 160, 160)
        else:
            f, col = F_EX, (180, 220, 200)
        draw.text((x + PADDING, cy), txt, fill=col, font=f)
        cy += lh


def draw_viewport_button_mock(draw, x, y):
    """Mock-up of the 3D Viewport header bar with the addon's Export-All
    icon button highlighted on the right end."""
    bar_w = 540
    bar_h = 36
    bar = (x, y, x + bar_w, y + bar_h)
    draw.rounded_rectangle(bar, radius=4, fill=(48, 48, 48), outline=(90, 90, 90), width=1)

    icon_y = y + 6
    for i in range(6):
        ix = x + 10 + i * 28
        draw.rounded_rectangle([ix, icon_y, ix + 22, icon_y + 24], radius=3,
                               fill=(60, 60, 60), outline=(95, 95, 95), width=1)

    bx0 = x + bar_w - 36
    by0 = y + 4
    bx1 = bx0 + 28
    by1 = by0 + 28
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=4,
                           fill=(75, 110, 165), outline=GROUPS["header"], width=2)
    cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
    # Stylised up-arrow (export glyph)
    draw.line([(cx, cy + 6), (cx, cy - 6)], fill=(245, 245, 245), width=2)
    draw.polygon([(cx - 5, cy - 2), (cx + 5, cy - 2), (cx, cy - 8)],
                 fill=(245, 245, 245))
    return bar


def main():
    src = Image.open(SRC).convert("RGBA")
    pw, ph = src.size

    # Pre-measure all description blocks.
    tmp_img = Image.new("RGBA", (10, 10))
    tmp_draw = ImageDraw.Draw(tmp_img)
    measured = [(*measure_block(f, tmp_draw), f) for f in FIELDS]

    # Single column on the left, y-aligned to each field's centre.
    COL_X = 40

    placements = {}
    cy = 130
    for i, (lines, lh, h, f) in enumerate(measured):
        fy0, fy1 = f["field_box"][1], f["field_box"][3]
        field_cy = (fy0 + fy1) // 2 + PASTE_Y  # convert to canvas y
        y_ideal = field_cy - h // 2
        y = max(cy, y_ideal)
        placements[i] = (COL_X, y, COL_W, h)
        cy = y + h + 18
    col_end_y = cy

    # Viewport-header button callout (mock + description) and a "Review
    # Notes" block — both anchor below the column.
    vb_lines = [
        ("title", "Export All Button — 3D Viewport header (top-right)"),
        ("body", "The addon also drops an Export-All icon button at the right"),
        ("body", "end of every 3D Viewport header. Fires the same operator as"),
        ("body", "the panel's main 'Export All Collections' button — no need to"),
        ("body", "open the N-panel."),
        ("body", ""),
        ("body", "• Greyed out when zero collections have Export checked."),
        ("body", "• Tooltip surfaces the reason when it's disabled."),
    ]
    vb_heights = []
    for kind, txt in vb_lines:
        f_ = {"title": F_HEADING, "body": F_BODY}[kind]
        bbox = f_.getbbox(txt or " ")
        vb_heights.append(bbox[3] - bbox[1] + 5)
    vb_total_h = sum(vb_heights) + 2 * PADDING

    # Code-review notes — informational block at the bottom that documents
    # things worth fixing or revisiting in the addon source.
    review_lines = [
        ("title", "Code Review Notes (v13.3.3)"),
        ("body", "• Single 3 542-line __init__.py — splitting properties / operators / ui / export"),
        ("body", "  into modules would make future maintenance a lot easier."),
        ("body", "• axis_forward / axis_up appears in BOTH Transform Options AND inside the FBX"),
        ("body", "  section of File Export Options — same property, two UI locations. Confusing"),
        ("body", "  when users edit one and don't realise the other is the same."),
        ("body", "• CollectionExportItem defines `move_to_center` and `use_suffix_grouping` but"),
        ("body", "  neither is exposed in the panel — they read as dead per-collection props."),
        ("body", "• `visibility_synced` keeps its update callback for back-compat even though the"),
        ("body", "  UIList eye now uses the toggle operator — comment acknowledges this; consider"),
        ("body", "  dropping the prop entirely on a major version."),
        ("body", "• `apply_modifiers` is global; `apply_modifiers_before_join` is per-collection and"),
        ("body", "  only visible under Use Parent Empties + Join Empty Children. Scope mismatch is"),
        ("body", "  easy to misread — a tooltip clarifying which one wins would help."),
        ("body", "• 'Skip Armature Modifier' is drawn unconditionally but only meaningful when Apply"),
        ("body", "  Modifiers is ON (currently grey-outs via `sub.enabled` — works, just verify"),
        ("body", "  Blender 5 still respects nested .enabled on a Box child)."),
        ("body", "• Quick Export operators duplicate export logic across four operators — there's"),
        ("body", "  ~3 200 lines of operator code that could share a single resolver pipeline."),
        ("body", "• Old `mass_exporter_v13_WIP.py` still sits in scripts/addons (disabled). Stale."),
    ]
    review_heights = []
    for kind, txt in review_lines:
        f_ = {"title": F_HEADING, "body": F_BODY}[kind]
        bbox = f_.getbbox(txt or " ")
        review_heights.append(bbox[3] - bbox[1] + 5)
    review_total_h = sum(review_heights) + 2 * PADDING

    # The bottom blocks sit below the column AND below the panel screenshot.
    panel_bottom_y = PASTE_Y + ph
    bottom_start = max(panel_bottom_y, col_end_y) + 40

    vp_bar_h = 36
    vb_y = bottom_start
    vp_y = bottom_start + max(0, (vb_total_h - vp_bar_h) // 2)
    review_y = max(vb_y + vb_total_h, vp_y + vp_bar_h) + 30

    required_bottom = review_y + review_total_h + 60

    # Canvas size.
    NW = PASTE_X + pw + 40
    NH = max(panel_bottom_y + 80, required_bottom)
    canvas = Image.new("RGBA", (NW, NH), BG)
    canvas.paste(src, (PASTE_X, PASTE_Y))
    draw = ImageDraw.Draw(canvas)

    # Title
    draw.text((40, 24), "Mass Collection Exporter v13.3.3 — Field Reference",
              fill=(245, 245, 245), font=F_TITLE)
    draw.text((40, 68),
              "Each labelled box on the panel maps to a description on the left.",
              fill=(180, 180, 180), font=F_SUB)
    draw.text((40, 90),
              "Colours group related fields (action, list, per-collection, transform, modifier, file, suffix, debug).",
              fill=(180, 180, 180), font=F_SUB)

    # --- Field outlines (drawn first) ---
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        color = GROUPS[f["group"]]
        fx0, fy0, fx1, fy1 = f["field_box"]
        fx0o = fx0 + PASTE_X
        fx1o = fx1 + PASTE_X
        fy0o = fy0 + PASTE_Y
        fy1o = fy1 + PASTE_Y
        draw.rectangle([fx0o, fy0o, fx1o, fy1o], outline=color, width=3)

    # --- Description blocks ---
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        bx, by, bw, bh = placements[i]
        draw_block(draw, bx, by, bw, lines, lh, GROUPS[f["group"]])

    # --- Metro-map connectors ---
    r = 4
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        bx, by, bw, bh = placements[i]
        color = GROUPS[f["group"]]
        fx0, fy0, fx1, fy1 = f["field_box"]
        fx0o = fx0 + PASTE_X
        fy_mid = (fy0 + fy1) // 2 + PASTE_Y

        block_anchor = (bx + bw, by + bh // 2)
        field_anchor = (fx0o, fy_mid)
        track_x = GROUP_TRACK_X[f["group"]]

        draw.line([block_anchor, (track_x, block_anchor[1])],
                  fill=color, width=3)
        draw.line([(track_x, block_anchor[1]), (track_x, field_anchor[1])],
                  fill=color, width=3)
        draw.line([(track_x, field_anchor[1]), field_anchor],
                  fill=color, width=3)

        draw.ellipse([block_anchor[0] - r, block_anchor[1] - r,
                      block_anchor[0] + r, block_anchor[1] + r], fill=color)
        draw.ellipse([field_anchor[0] - r, field_anchor[1] - r,
                      field_anchor[0] + r, field_anchor[1] + r], fill=color)

    # --- Viewport-header button callout ---
    vp_x = 40
    bar_rect = draw_viewport_button_mock(draw, vp_x, vp_y)
    bar_x0, bar_y0, bar_x1, bar_y1 = bar_rect

    vb_x = bar_x1 + 30
    vb_w = NW - vb_x - 40

    btn_cx = bar_x1 - 22
    btn_cy = bar_y0 + 18
    draw.line([(btn_cx + 16, btn_cy), (vb_x - 8, vb_y + 30)],
              fill=GROUPS["header"], width=2)

    draw.rounded_rectangle([vb_x, vb_y, vb_x + vb_w, vb_y + vb_total_h],
                           radius=8, fill=(40, 40, 40, 255),
                           outline=GROUPS["header"], width=2)
    cy_text = vb_y + PADDING
    for (kind, txt), lh in zip(vb_lines, vb_heights):
        if kind == "title":
            f_, col = F_HEADING, GROUPS["header"]
        else:
            f_, col = F_BODY, (225, 225, 225)
        draw.text((vb_x + PADDING, cy_text), txt, fill=col, font=f_)
        cy_text += lh

    # --- Code review notes ---
    review_x = 40
    review_w = NW - 80
    draw.rounded_rectangle([review_x, review_y, review_x + review_w, review_y + review_total_h],
                           radius=8, fill=(34, 34, 38, 255),
                           outline=(140, 140, 160), width=1)
    cy_text = review_y + PADDING
    for (kind, txt), lh in zip(review_lines, review_heights):
        if kind == "title":
            f_, col = F_HEADING, (235, 220, 180)
        else:
            f_, col = F_BODY, (210, 210, 215)
        draw.text((review_x + PADDING, cy_text), txt, fill=col, font=f_)
        cy_text += lh

    # Footer
    draw.text((40, NH - 30),
              "Stephko / ClaudeVibe — Mass Collection Exporter v13.3.3   •   N-panel: 3D Viewport ▸ Mass Exporter",
              fill=(140, 140, 140), font=F_SMALL)

    canvas.convert("RGB").save(OUT, "PNG", optimize=True)
    print("Wrote", OUT, "size", canvas.size)


if __name__ == "__main__":
    main()
