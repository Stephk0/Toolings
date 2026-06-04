# -*- coding: utf-8 -*-
"""Generates the annotated documentation image for Skin Transfer Setup.

Same visual language as MassExporter_v13.3.3_docs.png and
QuickAnimationExport_docs.png — single description column on the left,
N-panel screenshot on the right, metro-style coloured connectors between
them.

The source screenshot (skin_transfer_panel.png) was captured live from
Blender 5 via the MCP server with all sub-panels expanded:
  Active Object > Modifier Status (forced open)
  Batch by Collection (forced open, with Set all to... + Parts list)
Active object: Boot_L (Bind to Bone -> foot.L)
Active collection: Outfit_Parts with Torso/Arms/Boot_L/Boot_R/Skirt at
mixed modes.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r"D:/Stephko_Tooling/Toolings/Blender/Addons/ClaudeVibe_WIPs"
SRC  = os.path.join(ROOT, "skin_transfer_panel.png")
OUT  = os.path.join(ROOT, "SkinTransferSetup", "SkinTransferSetup_docs.png")

PASTE_X = 1380
PASTE_Y = 110
PANEL_SCALE = 2   # 2x upscale for presentation legibility
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
    "setup":   (0x5B, 0xA3, 0xF5),  # blue — Rig + Base Model (scene-wide)
    "refresh": (0xFF, 0x6B, 0x6B),  # red — global rebuild action
    "active":  (0xC7, 0x7D, 0xFF),  # purple — active object name + mode
    "bone":    (0x67, 0xD8, 0x8B),  # green — bone picker (bind-to-bone only)
    "act_btn": (0xE6, 0x95, 0x4C),  # orange — Re-apply / Clear (active)
    "status":  (0xB0, 0xBE, 0xC5),  # light grey — Modifier Status sub-box
    "batch":   (0x4D, 0xD0, 0xE1),  # cyan — collection picker
    "setall":  (0xFF, 0xD9, 0x3D),  # yellow — Set all to... mode buttons
    "parts":   (0xFF, 0xB3, 0xD9),  # pink — per-mesh parts list
}


# ---------- Field annotations ----------
# field_box uses ORIGINAL screenshot coordinates (322x790). The draw step
# multiplies by PANEL_SCALE and offsets by PASTE_X/PASTE_Y for placement on
# the final canvas, so these numbers stay easy to verify against the PNG.
FIELDS = [
    dict(
        group="setup",
        field_box=(6, 30, 318, 60),
        title="Rig (Armature)",
        body=[
            "The skeleton the parts deform with. Pure picker — nothing is",
            "applied to the rig itself. Drives the Bone search field below:",
            "only bones from this armature appear in the dropdown.",
        ],
        examples=["Restricted to objects of type ARMATURE via poll filter."],
    ),
    dict(
        group="setup",
        field_box=(6, 60, 318, 90),
        title="Weighted Base Model",
        body=[
            "The single mesh that already carries vertex groups for every",
            "bone of the rig. Acts as the Data Transfer source for every",
            "part tagged Transfer.",
            "Changing this picker re-targets EVERY Transfer object in the",
            "scene in one shot — no need to touch the parts individually.",
        ],
        examples=["e.g. Body_Base_Weighted — the rigged dummy your outfit",
                  "pieces are skinned around."],
    ),
    dict(
        group="refresh",
        field_box=(6, 95, 318, 130),
        title="Refresh All Transfer Targets",
        body=[
            "Walks every mesh with a skin_transfer property and rebuilds",
            "its addon-owned modifier from the current mode + bone + base.",
            "Use after manual edits to vertex groups, after re-pointing the",
            "Base Model, or to recover from a broken state.",
        ],
        examples=["Reports 'Refreshed Skin Transfer setup on N mesh(es)'",
                  "in the info bar."],
    ),
    dict(
        group="active",
        field_box=(6, 183, 318, 215),
        title="Active Object header (mesh name)",
        body=[
            "Echoes the active mesh's name so you can see what the panel",
            "below is configuring. Greys out to 'Select a mesh object'",
            "when no mesh is active.",
        ],
    ),
    dict(
        group="active",
        field_box=(6, 215, 318, 250),
        title="Mode — As-is / Transfer / Bind to Bone",
        body=[
            "Per-mesh choice driving which (if any) addon modifier the",
            "part gets:",
            "• As-is — no modifier added; use the mesh's own vgroups.",
            "• Transfer — Data Transfer pulling all vgroups from the",
            "  weighted base model.",
            "• Bind to Bone — Vertex Weight Edit pinning every vert to",
            "  one bone at weight 1.0 (a 'rigid bind').",
        ],
        examples=["Changing the mode runs the update callback which",
                  "applies / removes modifiers immediately."],
    ),
    dict(
        group="bone",
        field_box=(6, 250, 318, 285),
        title="Bone (Bind to Bone only)",
        body=[
            "Bone search field — only visible when Mode = Bind to Bone.",
            "Searches against the Rig picked above. The chosen bone name",
            "doubles as the vertex-group name created on the mesh.",
            "When no rig is set, falls back to a greyed-out 'Pick a rig",
            "first' hint.",
        ],
        examples=["Typical use: boot, glove, helmet props that should",
                  "rigidly follow one bone (foot.L, hand.R, head)."],
    ),
    dict(
        group="act_btn",
        field_box=(6, 292, 318, 326),
        title="Re-apply  /  Clear (active object)",
        body=[
            "Two scoped operators for the active mesh:",
            "• Re-apply — rebuild this mesh's modifier from its current",
            "  mode/bone settings. Manual fallback if a previous change",
            "  didn't take.",
            "• Clear — reset the mesh to As-is and strip its Skin",
            "  Transfer modifiers. Source vgroups are left intact.",
        ],
    ),
    dict(
        group="status",
        field_box=(6, 332, 318, 405),
        title="Modifier Status",
        body=[
            "Diagnostic readout of which addon-owned modifiers live on",
            "the active mesh RIGHT NOW. Distinct from 'Mode' because the",
            "modifier reflects the last applied state, not the pending",
            "selection.",
            "• Data Transfer → <base>   — Transfer mode active",
            "• Vertex Weight Edit → <bone>   — Bind-to-Bone mode active",
            "• 'No Skin Transfer modifiers'   — As-is or never applied",
        ],
        examples=["Collapsed by default in the addon — shown expanded here",
                  "for documentation."],
    ),
    dict(
        group="batch",
        field_box=(6, 442, 318, 478),
        title="Collection (Batch panel)",
        body=[
            "Scopes the batch operations to one collection's meshes.",
            "Pure organisational handle — the batch buttons act on every",
            "MESH object inside this collection (recursively, including",
            "child collections).",
        ],
        examples=["Useful for outfit-set workflows: one collection per",
                  "modular costume, switch between them via this picker."],
    ),
    dict(
        group="setall",
        field_box=(6, 484, 318, 568),
        title="Set all to…  (As-is / Transfer / Bind)",
        body=[
            "Bulk mode-setter for every mesh in the active collection.",
            "Fires the same per-mesh update path the dropdown does, so",
            "Transfer rows get Data Transfer modifiers, Bind rows get",
            "Vertex Weight Edit, As-is rows get cleaned.",
            "Bind variant leaves the bone empty — set it per-mesh in the",
            "Parts list below.",
        ],
    ),
    dict(
        group="parts",
        field_box=(6, 580, 318, 786),
        title="Parts list",
        body=[
            "Per-mesh row for every MESH in the active collection. Each",
            "row exposes:",
            "• Mesh name (read-only handle).",
            "• Mode dropdown — same property as Active Object > Mode,",
            "  edits propagate instantly.",
            "• Bone field — only renders for Bind-to-Bone rows. Searches",
            "  the same rig as the Active Object panel.",
            "Empties / lights / cameras inside the collection are skipped",
            "by the filter.",
        ],
        examples=["A typical character: Torso/Arms/Hands = Transfer,",
                  "Boots/Gloves = Bind to Bone, Cape/Skirt = As-is."],
    ),
]


# ---------- Layout constants ----------
COL_W = 760
PADDING = 12

# Metro tracks — one x-track per colour group between the description column
# (right edge ~x=820) and the panel (pasted at x=PASTE_X). Ordered roughly
# by first appearance in the panel so risers stay short.
GROUP_TRACK_X = {
    "setup":   870,
    "refresh": 925,
    "active":  980,
    "bone":    1035,
    "act_btn": 1090,
    "status":  1145,
    "batch":   1200,
    "setall":  1255,
    "parts":   1310,
}


def measure_block(field, _drawer):
    lines = [("title", field["title"])]
    for b in field["body"]:
        lines.append(("body", b))
    if field.get("examples"):
        lines.append(("ex_head", "examples:"))
        for ex in field["examples"]:
            lines.append(("ex", ex))
    line_heights = []
    for kind, txt in lines:
        f = {"title": F_HEADING, "body": F_BODY, "ex_head": F_SMALL,
             "ex": F_EX}[kind]
        bbox = f.getbbox(txt or " ")
        line_heights.append(bbox[3] - bbox[1] + 5)
    h = sum(line_heights) + 2 * PADDING
    return lines, line_heights, h


def draw_block(draw_, x, y, w, lines, line_heights, color):
    h = sum(line_heights) + 2 * PADDING
    draw_.rounded_rectangle([x, y, x + w, y + h], radius=8,
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
        draw_.text((x + PADDING, cy), txt, fill=col, font=f)
        cy += lh


def main():
    src = Image.open(SRC).convert("RGBA")
    if PANEL_SCALE != 1:
        sw, sh = src.size
        src = src.resize((sw * PANEL_SCALE, sh * PANEL_SCALE),
                         resample=Image.LANCZOS)
    pw, ph = src.size

    # Pre-measure all description blocks
    tmp_img = Image.new("RGBA", (10, 10))
    tmp_draw = ImageDraw.Draw(tmp_img)
    measured = [(*measure_block(f, tmp_draw), f) for f in FIELDS]

    COL_X = 40
    placements = {}
    cy = 130
    for i, (lines, lh, h, f) in enumerate(measured):
        fy0, fy1 = f["field_box"][1] * PANEL_SCALE, f["field_box"][3] * PANEL_SCALE
        field_cy = (fy0 + fy1) // 2 + PASTE_Y
        y_ideal = field_cy - h // 2
        y = max(cy, y_ideal)
        placements[i] = (COL_X, y, COL_W, h)
        cy = y + h + 18
    col_end_y = cy

    # Tip / workflow block
    tip_lines = [
        ("title", "Tip — typical setup flow"),
        ("body", "1. Pick the Rig (Armature) and Weighted Base Model at the top — these are the"),
        ("body", "   shared inputs every per-mesh choice references."),
        ("body", "2. Open the Batch by Collection panel, pick the collection holding your parts,"),
        ("body", "   and 'Set all to → Transfer' for a baseline."),
        ("body", "3. Walk the Parts list — switch obvious rigid props (boots, gloves, helmet) to"),
        ("body", "   'Bind to Bone' and pick their target bone."),
        ("body", "4. Swap base meshes? Just re-point the Weighted Base Model picker — every"),
        ("body", "   Transfer object retargets in one click."),
        ("body", "5. Hit 'Refresh All Transfer Targets' if anything looks stale after manual edits."),
    ]
    tip_heights = []
    for kind, txt in tip_lines:
        f_ = {"title": F_HEADING, "body": F_BODY}[kind]
        bbox = f_.getbbox(txt or " ")
        tip_heights.append(bbox[3] - bbox[1] + 5)
    tip_total_h = sum(tip_heights) + 2 * PADDING

    panel_bottom_y = PASTE_Y + ph
    bottom_start = max(panel_bottom_y, col_end_y) + 40
    tip_y = bottom_start
    required_bottom = tip_y + tip_total_h + 50

    NW = PASTE_X + pw + 40
    NH = max(panel_bottom_y + 80, required_bottom)
    canvas = Image.new("RGBA", (NW, NH), BG)
    canvas.paste(src, (PASTE_X, PASTE_Y))
    draw = ImageDraw.Draw(canvas)

    # Title strip
    draw.text((40, 24), "Skin Transfer Setup v1.0.0 — Field Reference",
              fill=(245, 245, 245), font=F_TITLE)
    draw.text((40, 68),
              "Each labelled box on the panel maps to a description on the left.",
              fill=(180, 180, 180), font=F_SUB)
    draw.text((40, 90),
              "Colours group related fields (setup, refresh, active object, batch).",
              fill=(180, 180, 180), font=F_SUB)

    # Field outlines on the panel
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        color = GROUPS[f["group"]]
        fx0, fy0, fx1, fy1 = f["field_box"]
        fx0o = fx0 * PANEL_SCALE + PASTE_X
        fx1o = fx1 * PANEL_SCALE + PASTE_X
        fy0o = fy0 * PANEL_SCALE + PASTE_Y
        fy1o = fy1 * PANEL_SCALE + PASTE_Y
        draw.rectangle([fx0o, fy0o, fx1o, fy1o], outline=color, width=3)

    # Description blocks
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        bx, by, bw, bh = placements[i]
        draw_block(draw, bx, by, bw, lines, lh, GROUPS[f["group"]])

    # Metro connectors
    r = 4
    for i in range(len(FIELDS)):
        lines, lh, h, f = measured[i]
        bx, by, bw, bh = placements[i]
        color = GROUPS[f["group"]]
        fx0, fy0, fx1, fy1 = f["field_box"]
        fx0o = fx0 * PANEL_SCALE + PASTE_X
        fy_mid = ((fy0 + fy1) // 2) * PANEL_SCALE + PASTE_Y

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

    # Tip block
    tip_x = 40
    tip_w = NW - 80
    draw.rounded_rectangle([tip_x, tip_y, tip_x + tip_w, tip_y + tip_total_h],
                           radius=8, fill=(38, 38, 38, 255),
                           outline=(120, 120, 120), width=1)
    cy_text = tip_y + PADDING
    for (kind, txt), lh in zip(tip_lines, tip_heights):
        if kind == "title":
            f_, col = F_HEADING, (235, 235, 235)
        else:
            f_, col = F_BODY, (210, 210, 210)
        draw.text((tip_x + PADDING, cy_text), txt, fill=col, font=f_)
        cy_text += lh

    # Footer
    draw.text((40, NH - 30),
              "Stephko / ClaudeVibe — Skin Transfer Setup v1.0.0   •   N-panel: 3D Viewport ▸ Skin Transfer",
              fill=(140, 140, 140), font=F_SMALL)

    canvas.convert("RGB").save(OUT, "PNG", optimize=True)
    print("Wrote", OUT, "size", canvas.size)


if __name__ == "__main__":
    main()
