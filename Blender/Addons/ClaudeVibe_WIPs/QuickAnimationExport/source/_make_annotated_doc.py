# -*- coding: utf-8 -*-
"""Generates an annotated documentation image for Quick Animation Export
by overlaying labelled boxes + descriptions onto a Blender screenshot.

Canvas is extended 25% to the left and 50% downward versus the source
screenshot to give the description column proper breathing room and to
make space for the viewport-header button callout under the panel.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"D:/Stephko_Tooling/Toolings/Blender/Addons/ClaudeVibe_WIPs"
SRC = os.path.join(ROOT, "quick_anim_export_screenshot.png")
OUT = os.path.join(ROOT, "QuickAnimationExport", "QuickAnimationExport_docs.png")

# Canvas geometry — the screenshot is pasted with this offset so its grey
# 3D viewport area is widened on the left.
LEFT_PAD = 482        # 25% of 1928, added to the left
BOTTOM_PAD = 548      # 50% of 1095, added at the bottom
PANEL_LEFT_SRC = 1346 # left edge of the N-panel inside the source screenshot

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
    "status":  (0xE6, 0x95, 0x4C),
    "output":  (0x5B, 0xA3, 0xF5),
    "perlay":  (0x4D, 0xD0, 0xE1),
    "file":    (0x67, 0xD8, 0x8B),
    "clip":    (0xC7, 0x7D, 0xFF),
    "scope":   (0xFF, 0x99, 0x33),
    "bake":    (0xFF, 0xD9, 0x3D),
    "fbx":     (0xB0, 0xBE, 0xC5),
    "action":  (0xFF, 0x6B, 0x6B),
    "header":  (0xFF, 0xB3, 0xD9),   # viewport header callout
}

# ---------- Field annotations ----------
# field_box uses ORIGINAL screenshot coordinates; they get offset by LEFT_PAD
# at draw time so the same numbers stay easy to verify against the source.
FIELDS = [
    dict(
        group="status",
        field_box=(1362, 47, 1916, 92),
        title="Status / Animation Layers detection",
        body=[
            "Sanity-check banner. Green checkmark = the Animation Layers addon",
            "is installed, enabled, and the active armature actually has layers.",
            "If absent, the panel falls back to plain FBX export with no merge step.",
        ],
    ),
    dict(
        group="output",
        field_box=(1362, 100, 1916, 128),
        title="Export Path",
        body=[
            "Folder the FBX file(s) are written to. Accepts Blender's // relative",
            "paths (resolved against the .blend file) and absolute system paths.",
        ],
        examples=["//exports/", "D:/Work/Anims/"],
    ),
    dict(
        group="output",
        field_box=(1362, 133, 1916, 161),
        title="Export Mode — Merged vs Per Layer",
        body=[
            "MERGED: bake every Animation Layer into one merged clip and write a",
            "single FBX. PER LAYER: each layer becomes its own file (or a single",
            "FBX containing one clip per layer if Bundle is on below).",
        ],
    ),
    dict(
        group="perlay",
        field_box=(1362, 166, 1916, 293),
        title="Per-Layer Options (only shown in Per Layer mode)",
        body=[
            "• Bundle into single FBX — all layers exported as separate AnimStacks",
            "  inside one FBX via the NLA-strip bake path.",
            "• Only Visible Layers — skip layers whose eye/mute flag is off.",
        ],
        examples=["Bundle ON  -> idleLayered.fbx (3 clips)",
                  "Bundle OFF -> idle_BasePose.fbx, idle_Overlay.fbx ..."],
    ),
    dict(
        group="file",
        field_box=(1362, 338, 1916, 372),
        title="Filename → Source",
        body=[
            "How the base filename is derived.",
            "• Layer / Action Name — use the active layer's action name.",
            "• Armature Name — use the armature object's name.",
            "• Custom — use the Name field shown directly below.",
        ],
    ),
    dict(
        group="file",
        field_box=(1362, 375, 1916, 406),
        title="Filename → Name (Custom only)",
        body=[
            "Literal base name when Source = Custom. Prefix/Suffix wrap around it.",
        ],
        examples=["idleLayered  ->  anim_idleLayered.fbx"],
    ),
    dict(
        group="file",
        field_box=(1362, 410, 1916, 442),
        title="Filename → Prefix  /  Suffix",
        body=[
            "Strings glued to the front/back of the resolved base name. Suffix is",
            "inserted before the .fbx extension. Both apply to the FILE name only.",
        ],
        examples=["Prefix 'anim_' + base 'idleLayered'  ->  anim_idleLayered.fbx"],
    ),
    dict(
        group="clip",
        field_box=(1362, 455, 1916, 543),
        title="Clip Name → Source (FBX AnimStack label)",
        body=[
            "Independent from the filename. Controls the clip label written INSIDE",
            "the FBX (what Unity/Unreal display as the animation clip).",
            "Same as Filename / Layer-Action / Armature / Custom.",
        ],
        examples=[
            "Given Filename Source = Custom 'idleLayered'  (file = idleLayered.fbx):",
            "Clip Source = Same as Filename    ->  Clip = idleLayered",
            "Clip Source = Layer/Action Name   ->  Clip = BasePose   (the active layer's action)",
            "Clip Source = Armature Name       ->  Clip = Armature",
            "Clip Source = Custom 'main'       ->  Clip = main",
        ],
    ),
    dict(
        group="clip",
        field_box=(1362, 547, 1916, 578),
        title="Clip Name → Clip Prefix / Suffix",
        body=[
            "Wraps every clip label. Common usage: a project/rig tag separate from",
            "the file's prefix, e.g. an engine that expects 'animClip_*'.",
        ],
        examples=["animClip_ + idleLayered  ->  animClip_idleLayered"],
    ),
    dict(
        group="clip",
        field_box=(1362, 580, 1916, 614),
        title="Clip Name → Layer Token",
        body=[
            "Per-clip differentiator appended to the clip base name. Essential when",
            "bundling multiple layers as separate clips in one FBX so each AnimStack",
            "has a unique label.",
            "Options: None / Layer Name / Layer Index / Index_Name / Name_Index.",
        ],
        examples=[
            "Given Clip Source = Same as Filename, File = idleLayered.fbx:",
            "Token = None         ->  Clip = idleLayered",
            "Token = Layer Name   ->  Clip = idleLayered_BasePose",
            "Token = Layer Index  ->  Clip = idleLayered_00",
            "Token = Index_Name   ->  Clip = idleLayered_00_BasePose",
        ],
    ),
    dict(
        group="scope",
        field_box=(1362, 620, 1916, 654),
        title="Scope — what to include in the export",
        body=[
            "• Active Armature Only — just the rig in focus.",
            "• Active Armature + Children — rig plus everything parented to it",
            "  (meshes, props). The usual default.",
            "• Selected Armatures + Children — every selected rig and its kids.",
        ],
    ),
    dict(
        group="bake",
        field_box=(1362, 660, 1916, 772),
        title="Bake / Merge — engine, operator, direction",
        body=[
            "Mirrors Animation Layers' merge dialog so you don't have to leave",
            "this panel.",
            "• Bake Type — 'Anim Layers' (preserves layer key density) or NLA Bake.",
            "• Bake Operator — Merge layers down vs bake into a new layer.",
            "• Direction — All / Down / Up relative to the active layer.",
        ],
    ),
    dict(
        group="bake",
        field_box=(1362, 775, 1916, 800),
        title="Merge Cyclic & Fcurve Modifiers",
        body=[
            "Include F-curve modifiers (cyclic, noise, etc.) in the bake instead",
            "of throwing them away when layers are flattened.",
        ],
    ),
    dict(
        group="bake",
        field_box=(1362, 800, 1916, 822),
        title="Smart Bake  /  Bake Step",
        body=[
            "Smart Bake (AL only): keep the original key density after merge.",
            "Bake Step: only bake every Nth frame (cheaper, less precise).",
        ],
        examples=["Bake Step 1 = every frame    Bake Step 2 = every 2nd frame"],
    ),
    dict(
        group="bake",
        field_box=(1362, 822, 1916, 872),
        title="Only Selected Bones  /  Copy Original Merged Action",
        body=[
            "• Only Selected Bones — bake just the bones you have selected in",
            "  pose mode (faster for partial bakes).",
            "• Copy Original Merged Action — keep a backup of the action that gets",
            "  overwritten. QAE already restores actions itself, so usually OFF.",
        ],
    ),
    dict(
        group="bake",
        field_box=(1362, 880, 1916, 910),
        title="Frame Range",
        body=[
            "Source for the bake's frame range.",
            "• Scene — use the scene start/end.",
            "• Action — use each action's own length.",
            "• Custom — type your own start/end below the dropdown.",
        ],
    ),
    dict(
        group="fbx",
        field_box=(1362, 918, 1916, 1040),
        title="FBX Animation / Armature / General (collapsed)",
        body=[
            "Three foldouts that mirror Blender's native FBX exporter:",
            "• Animation — sampling rate, simplify, NLA strips, force start/end.",
            "• Armature — leaf bones, primary/secondary bone axis, node type.",
            "• General — unit scale, apply transform, forward/up axes, path mode.",
            "Open only when you need to tune the FBX exporter itself.",
        ],
    ),
    dict(
        group="action",
        field_box=(1362, 1049, 1916, 1083),
        title="Quick Export Animation",
        body=[
            "Run it. Bakes (if AL is active) and writes the FBX(s) using every",
            "setting above.",
        ],
    ),
]


# ---------- Layout constants for the extended canvas ----------
COL_W = 800
PADDING = 12

# Metro-map style: each colour group gets its own dedicated vertical track
# inside the corridor between the description column (right edge ~x=840) and
# the panel (left edge ~x=1828). Tracks are spaced ~110px apart so risers
# never sit on top of each other or behind the text boxes.
# Ordered by first appearance in the FIELDS list so tracks roughly follow the
# panel from top to bottom — keeps crossings between groups to a minimum.
GROUP_TRACK_X = {
    "status": 900,
    "output": 1010,
    "perlay": 1120,
    "file":   1230,
    "clip":   1340,
    "scope":  1450,
    "bake":   1560,
    "fbx":    1670,
    "action": 1780,
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
        bbox = f.getbbox(txt)
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
    """Tiny illustration of where the addon adds its viewport-header button.

    A short stylised top-bar with a few generic icons on the left and the
    QAE icon highlighted on the right, with a label arrow.
    """
    bar_w = 540
    bar_h = 36
    bar = (x, y, x + bar_w, y + bar_h)
    draw.rounded_rectangle(bar, radius=4, fill=(48, 48, 48), outline=(90, 90, 90), width=1)

    # Generic dummy icons on the left
    icon_y = y + 6
    for i in range(6):
        ix = x + 10 + i * 28
        draw.rounded_rectangle([ix, icon_y, ix + 22, icon_y + 24], radius=3,
                               fill=(60, 60, 60), outline=(95, 95, 95), width=1)

    # The QAE button — highlighted on the right end
    bx0 = x + bar_w - 36
    by0 = y + 4
    bx1 = bx0 + 28
    by1 = by0 + 28
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=4,
                           fill=(75, 110, 165), outline=GROUPS["header"], width=2)
    # Stylised sine wave + arrow inside
    cx, cy = (bx0 + bx1) // 2, (by0 + by1) // 2
    draw.line([(cx - 9, cy + 2), (cx - 5, cy - 4), (cx, cy + 2), (cx + 5, cy - 4)],
              fill=(245, 245, 245), width=2)
    draw.polygon([(cx + 6, cy + 4), (cx + 10, cy + 4), (cx + 8, cy + 8)],
                 fill=(245, 245, 245))

    return bar


def main():
    src = Image.open(SRC).convert("RGBA")
    sw, sh = src.size

    # Pre-measure all description blocks before we know the final canvas size.
    # The bottom blocks (viewport-header callout, workflow tip) are sized first
    # because the canvas height has to grow to fit them under the columns.
    tmp_img = Image.new("RGBA", (10, 10))
    tmp_draw = ImageDraw.Draw(tmp_img)
    measured = [(*measure_block(f, tmp_draw), f) for f in FIELDS]

    # Single description column on the left. Each box's y is pulled towards
    # its field's centre where the flow allows — keeps the metro-map risers
    # short. We use one column instead of two so the connector corridor
    # between text and panel stays clear of any text boxes.
    COL_X = 40

    placements = {}
    cy = 130
    for i, (lines, lh, h, f) in enumerate(measured):
        fy0, fy1 = f["field_box"][1], f["field_box"][3]
        field_cy = (fy0 + fy1) // 2
        y_ideal = field_cy - h // 2
        y = max(cy, y_ideal)
        placements[i] = (COL_X, y, COL_W, h)
        cy = y + h + 18  # comfortable gap between blocks
    col_end_y = {"single": cy}

    # Measure the viewport-button callout and workflow tip up-front so we know
    # how much vertical room they need below the columns / screenshot.
    vb_lines = [
        ("title", "Quick Export Button (3D viewport header, top-right)"),
        ("body", "The addon also appends a single icon button to every 3D viewport's"),
        ("body", "header bar, on the right-hand side. Clicking it fires the same"),
        ("body", "qae.quick_export operator the panel's button calls — so you can"),
        ("body", "trigger an export without opening the N-panel."),
        ("body", ""),
        ("body", "• Custom icon — a sine wave flowing into an export arrow."),
        ("body", "• Greyed out unless the active object is an armature."),
        ("body", "• Falls back to Blender's ARMATURE_DATA icon if the PNG fails to load."),
    ]
    vb_heights = []
    for kind, txt in vb_lines:
        f_ = {"title": F_HEADING, "body": F_BODY}[kind]
        bbox = f_.getbbox(txt or " ")
        vb_heights.append(bbox[3] - bbox[1] + 5)
    vb_total_h = sum(vb_heights) + 2 * PADDING

    note_lines = [
        ("title", "Tip — typical workflow"),
        ("body", "1. Set Export Path and Export Mode (Merged for one-shots, Per Layer to keep layers separate)."),
        ("body", "2. Pick Filename + Clip Name conventions once — they survive between sessions."),
        ("body", "3. Choose Scope (usually 'Active Armature + Children')."),
        ("body", "4. Tune Bake/Merge only if the AL defaults don't suit the rig."),
        ("body", "5. Hit Quick Export Animation — from the N-panel or the viewport header button."),
    ]
    note_heights = []
    for kind, txt in note_lines:
        f_ = {"title": F_HEADING, "body": F_BODY}[kind]
        bbox = f_.getbbox(txt or " ")
        note_heights.append(bbox[3] - bbox[1] + 5)
    note_total_h = sum(note_heights) + 2 * PADDING

    # The bottom blocks must sit BELOW the original screenshot AND below the
    # bottom of the description column — whichever is lower.
    bottom_start = max(sh, col_end_y["single"]) + 40
    vp_bar_h = 36
    vb_y = bottom_start
    vp_y = bottom_start + max(0, (vb_total_h - vp_bar_h) // 2)
    note_y = max(vb_y + vb_total_h, vp_y + vp_bar_h) + 30

    required_bottom = note_y + note_total_h + 40  # 40px footer margin

    # Extended canvas: 25% more on the left; bottom expands to fit everything.
    NW = sw + LEFT_PAD
    NH = max(sh + BOTTOM_PAD, required_bottom + 30)
    canvas = Image.new("RGBA", (NW, NH), BG)
    canvas.paste(src, (LEFT_PAD, 0))
    draw = ImageDraw.Draw(canvas)

    # Title
    draw.text((40, 24), "Quick Animation Export — Field Reference",
              fill=(245, 245, 245), font=F_TITLE)
    draw.text((40, 68),
              "Each labelled box on the panel maps to a description on the left.",
              fill=(180, 180, 180), font=F_SUB)
    draw.text((40, 90),
              "Colours group related fields (output, filename, clip, bake/merge, FBX, action).",
              fill=(180, 180, 180), font=F_SUB)

    # --- Field outlines (drawn first so tracks/dots sit on top) ---
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        color = GROUPS[f["group"]]
        fx0, fy0, fx1, fy1 = f["field_box"]
        fx0o = fx0 + LEFT_PAD
        fx1o = fx1 + LEFT_PAD
        draw.rectangle([fx0o, fy0, fx1o, fy1], outline=color, width=3)

    # --- Description blocks (drawn before connectors so the corridor stays
    # visually clean — no track ever runs through a text box anyway, but the
    # blocks landing first makes the dot/box-edge meeting point look tidy). ---
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        bx, by, bw, bh = placements[i]
        draw_block(draw, bx, by, bw, lines, lh, GROUPS[f["group"]])

    # --- Metro-map connectors ---
    # Each group has a dedicated vertical track between the description column
    # and the panel. A connector is 3 segments: short horizontal out of the
    # box, vertical along the group's track, short horizontal into the field.
    # Same-colour boxes share the same track x — fields stack onto it like
    # stations on a metro line. Different groups run as parallel verticals.
    r = 4
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        bx, by, bw, bh = placements[i]
        color = GROUPS[f["group"]]
        fx0, fy0, fx1, fy1 = f["field_box"]
        fx0o = fx0 + LEFT_PAD

        block_anchor = (bx + bw, by + bh // 2)
        field_anchor = (fx0o, (fy0 + fy1) // 2)
        track_x = GROUP_TRACK_X[f["group"]]

        # Out of box → track (horizontal)
        draw.line([block_anchor, (track_x, block_anchor[1])],
                  fill=color, width=3)
        # Vertical riser at the group track
        draw.line([(track_x, block_anchor[1]), (track_x, field_anchor[1])],
                  fill=color, width=3)
        # Track → field (horizontal)
        draw.line([(track_x, field_anchor[1]), field_anchor],
                  fill=color, width=3)

        # Station dots at both ends so the entry/exit points read clearly
        draw.ellipse([block_anchor[0] - r, block_anchor[1] - r,
                      block_anchor[0] + r, block_anchor[1] + r], fill=color)
        draw.ellipse([field_anchor[0] - r, field_anchor[1] - r,
                      field_anchor[0] + r, field_anchor[1] + r], fill=color)

    # --- Viewport header button callout (in the new bottom grey area) ---
    vp_x = 40
    bar_rect = draw_viewport_button_mock(draw, vp_x, vp_y)
    bar_x0, bar_y0, bar_x1, bar_y1 = bar_rect

    # Description block for the viewport button — placed to the right of the
    # mock bar, vertically centred against it.
    vb_x = bar_x1 + 30
    vb_w = NW - vb_x - 40

    # Connector from the highlighted QAE icon on the mock bar to the callout.
    btn_cx = bar_x1 - 22
    btn_cy = bar_y0 + 18
    draw.line([(btn_cx + 16, btn_cy), (vb_x - 8, vb_y + 30)],
              fill=GROUPS["header"], width=2)

    draw.rounded_rectangle([vb_x, vb_y, vb_x + vb_w, vb_y + vb_total_h],
                           radius=8, fill=(40, 40, 40, 255),
                           outline=GROUPS["header"], width=2)
    cy = vb_y + PADDING
    for (kind, txt), lh in zip(vb_lines, vb_heights):
        if kind == "title":
            f_, col = F_HEADING, GROUPS["header"]
        else:
            f_, col = F_BODY, (225, 225, 225)
        draw.text((vb_x + PADDING, cy), txt, fill=col, font=f_)
        cy += lh

    # Workflow note spans the full width below the viewport-button callout.
    note_x = 40
    note_w = NW - 80
    draw.rounded_rectangle([note_x, note_y, note_x + note_w, note_y + note_total_h],
                           radius=8, fill=(38, 38, 38, 255),
                           outline=(120, 120, 120), width=1)
    cy = note_y + PADDING
    for (kind, txt), lh in zip(note_lines, note_heights):
        if kind == "title":
            f_, col = F_HEADING, (235, 235, 235)
        else:
            f_, col = F_BODY, (210, 210, 210)
        draw.text((note_x + PADDING, cy), txt, fill=col, font=f_)
        cy += lh

    # Footer
    draw.text((40, NH - 28),
              "Stephko / ClaudeVibe — Quick Animation Export   •   N-panel: 3D Viewport ▸ Animation",
              fill=(140, 140, 140), font=F_SMALL)

    canvas.convert("RGB").save(OUT, "PNG", optimize=True)
    print("Wrote", OUT, "size", canvas.size)


if __name__ == "__main__":
    main()
