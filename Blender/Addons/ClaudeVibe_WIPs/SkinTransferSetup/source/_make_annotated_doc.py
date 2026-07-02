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
ASSETS = os.path.join(ROOT, "SkinTransferSetup", "assets")
SRC  = os.path.join(ASSETS, "skin_transfer_panel.png")
OUT  = os.path.join(ASSETS, "SkinTransferSetup_docs.png")

PASTE_X = 1380
PASTE_Y = 110
PANEL_SCALE = 1   # panel captured hi-res (1015x732); no upscale
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
# field_box uses PANEL-CROP pixel coordinates (panel image 1015x732,
# captured at ui_scale 0.85). PANEL_SCALE=1, so the draw step only offsets
# by PASTE_X/PASTE_Y — numbers verify directly against the PNG.
FIELDS = [
    dict(group="setup", field_box=(4, 38, 1010, 54),
        title="Rig (Armature)",
        body=[
            "The armature the parts deform with. Pure picker — nothing is",
            "applied to the rig itself. Restricts the Bone fields below to",
            "this armature's bones.",
        ],
        examples=["Restricted to ARMATURE objects via a poll filter."]),
    dict(group="setup", field_box=(4, 57, 1010, 74),
        title="Weighted Base Model",
        body=[
            "The single mesh carrying vertex groups for every bone — the Data",
            "Transfer source for every part set to 'Transfer'. Re-pointing",
            "this picker retargets EVERY Transfer object in one shot.",
        ],
        examples=["e.g. BaseBody — the rigged dummy your outfit pieces are",
                  "skinned around."]),
    dict(group="bone", field_box=(4, 84, 1010, 101),
        title="Only Weighted Bones",
        body=[
            "Filter toggle: restrict the Bone search fields to bones that",
            "actually carry weights on the base model, hiding empty",
            "control / IK bones from the dropdown.",
        ]),
    dict(group="refresh", field_box=(4, 120, 1010, 163),
        title="Refresh All Transfer Targets",
        body=[
            "Walks every mesh with a Skin Transfer setup and rebuilds its",
            "addon-owned modifier from the current mode + bone + base model.",
            "'Also Ensure / Strip VGs' additionally creates missing vertex",
            "groups and strips stale ones during the refresh.",
        ]),
    dict(group="active", field_box=(4, 207, 1010, 225),
        title="Active Object (mesh name)",
        body=[
            "Echoes the active mesh's name — the Selection panel configures",
            "THIS mesh. Greys out when no mesh is active.",
        ]),
    dict(group="active", field_box=(4, 237, 1010, 255),
        title="Mode — As-is / Transfer / Bind to Bone",
        body=[
            "Per-mesh choice of which addon modifier the part gets:",
            "- As-is: no modifier; use the mesh's own vgroups.",
            "- Transfer: Data Transfer pulling vgroups from the base model.",
            "- Bind to Bone: Vertex Weight Edit pinning all verts to one",
            "  bone at weight 1.0 (a rigid bind).",
        ]),
    dict(group="bone", field_box=(4, 259, 1010, 278),
        title="Bone (Bind to Bone only)",
        body=[
            "Bone search — only shown when Mode = Bind to Bone. Searches the",
            "Rig above; the chosen bone name doubles as the vertex-group name",
            "created on the mesh. Red = not yet set / invalid.",
        ],
        examples=["For rigid props: boots, gloves, helmet (foot.L, hand.R)."]),
    dict(group="active", field_box=(4, 286, 1010, 321),
        title="Auto-Create VG / Auto-Strip Prior VG",
        body=[
            "Automation applied on a mode / bone change:",
            "- Auto-Create VG: make the target vertex group automatically.",
            "- Auto-Strip Prior VG: remove the previous bind's group so old",
            "  weights don't linger.",
        ]),
    dict(group="act_btn", field_box=(4, 342, 1010, 389),
        title="Active-object operators",
        body=[
            "Scoped operators for the active mesh:",
            "- Re-apply: rebuild this mesh's modifier from its settings.",
            "- Clear: reset to As-is and strip Skin Transfer modifiers.",
            "- Create VG / Strip Unused: manage this mesh's vertex groups.",
        ]),
    dict(group="status", field_box=(4, 397, 1010, 437),
        title="Modifier Status",
        body=[
            "Diagnostic readout of which addon-owned modifiers live on the",
            "active mesh RIGHT NOW (last applied state, not the pending Mode):",
            "- Data Transfer -> <base>   = Transfer active",
            "- Vertex Weight Edit -> <bone>   = Bind-to-Bone active",
            "Collapsed by default — shown expanded here.",
        ]),
    dict(group="batch", field_box=(4, 456, 1010, 502),
        title="Collection (Batch by Collection)",
        body=[
            "Scopes the batch operations to one collection's meshes",
            "(recursively, incl. child collections). Pure organisational",
            "handle — switch outfit sets by re-pointing this picker.",
        ]),
    dict(group="setall", field_box=(4, 511, 1010, 558),
        title="Set all to… / Strip Unused (Collection)",
        body=[
            "Bulk mode-setter for every mesh in the collection (As-is /",
            "Transfer / Bind), firing the same per-mesh update as the",
            "dropdown. 'Strip Unused (Collection)' cleans stale vertex",
            "groups across all parts at once.",
        ]),
    dict(group="parts", field_box=(4, 576, 1010, 730),
        title="Parts list",
        body=[
            "Per-mesh row for every MESH in the collection:",
            "- Mesh name (read-only handle).",
            "- Mode dropdown (same property as Active Object > Mode).",
            "- Bone field — only renders for Bind-to-Bone rows.",
            "Non-mesh objects (empties / lights / cameras) are skipped.",
        ],
        examples=["Typical: Torso/Arms = Transfer, Boots = Bind to Bone,",
                  "Skirt = As-is."]),
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
    draw.text((40, 24), "Skin Transfer Setup v1.3.0 — Field Reference",
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
              "Stephko / ClaudeVibe — Skin Transfer Setup v1.3.0   •   N-panel: 3D Viewport ▸ Skin Transfer",
              fill=(140, 140, 140), font=F_SMALL)

    canvas.convert("RGB").save(OUT, "PNG", optimize=True)
    print("Wrote", OUT, "size", canvas.size)


if __name__ == "__main__":
    main()
