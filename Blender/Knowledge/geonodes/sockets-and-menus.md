# Geonode sockets, interfaces and menus

Scripting the group interface, links and Menu sockets.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Relink by socket identifier, not name](#feedback_gn_link_rewire_gotchas)
- [New inputs backfill existing modifiers with zero](#feedback_gn_new_socket_backfills_zero)
- [Scripted Menu inputs need a default_value](#feedback_gn_menu_socket_default)
- [One menu → master Menu Switch → Index Switches](#feedback_gn_menu_to_index_switch)

<a id="feedback_gn_link_rewire_gotchas"></a>

## Relink by socket identifier, not name

*Rewiring GN links safely — relink by socket IDENTIFIER never display name (names can duplicate), and Blender 5 Viewer item sockets self-delete on unlink so cached socket refs die*

Two bugs found 2026-07 when `tidy_layout.py` (LLMGeonodePipeline) silently changed GN_EdgeDestruct's geometry (516→442 verts) during a remove-then-relink layout pass:

1. **Relink by `socket.identifier`, never `socket.name`.** Two interface sockets can share a display name (GN_EdgeDestruct had "Auto Angle Degrees" twice: Socket_19 + Socket_25). `node.outputs[name]` returns the FIRST match → link lands on the wrong input and the modifier computes different geometry with no error.

2. **Blender 5 Viewer inputs are dynamic items that self-delete when unlinked.** After `links.remove()` on a viewer link, the socket is GONE (only `__extend__` remains) — a cached socket reference then silently fails to relink. Either skip viewer-bound links in rewiring passes (keep them direct), or fall back to linking into the node's `__extend__` socket to recreate the item.

**Why:** both failures are silent — the code "succeeds" but drops/miswires links. Only an evaluated-geometry before/after diff caught it.

**How to apply:** any script that removes-and-recreates node links must (a) key relinks on identifiers, (b) treat GeometryNodeViewer targets as fragile, (c) verify evaluated vertex positions unchanged before saving (the [Geonode layout](layout.md#feedback_gn_node_layout_spacing) pipeline's `run_pipeline.py` gate does exactly this — it caught the bug in practice). A third fix from the same session: `est_h`-style height estimates must prefer `node.dimensions.y / ui_scale` when drawn (unlinked VECTOR inputs add 3 slider rows the socket-count formula misses).

4. **(2026-08-03) The resolution order in point 3 is exact — an "enabled-first" resolver that still checks ALL identifiers before ANY name is WRONG.** `enabled-identifier → disabled-identifier → enabled-name → disabled-name` looks equivalent but is not: `FunctionNodeRandomValue` with `data_type='FLOAT'` enables `Min_001/Max_001/Value_001` (whose *names* are the plain "Min"/"Max"/"Value") while the DISABLED vector variants own the plain *identifiers*. So the plain key `"Min"` resolves to the disabled vector socket and every random silently dies. Symptom is not zero and not an error: the consumer falls back to its own socket default (a `ShaderNodeMath` input reads 0.5), so a tile field looked plausible while Seed, jitter and per-element colour all did nothing. Correct order, no shortcuts: **enabled-identifier → enabled-name → identifier → name.** Bit twice now (Compare in GN_TileableMeshNoise, Random Value in [Geonode techniques](techniques.md#feedback_gn_region_fill_tile_generator)) — copy a known-good `_pick` rather than rewriting it.

3. **(2026-07-18) Identifier match must also prefer ENABLED sockets.** Multi-type nodes (FunctionNodeCompare!) keep a DISABLED socket whose identifier is the plain name (`"A"` = the FLOAT variant) while the enabled variant is suffixed (`"A_INT"` when `data_type="INT"`). Linking the disabled socket raises no error but the link silently NO-OPS at evaluation (an INT Compare read `0 < 0` forever — GN_TileableMeshNoise's border-pin chain was dead through two rebuild cycles). Resolution order for by-key socket lookup: enabled-identifier → enabled-name → identifier → name. Diagnose by dumping `(s.identifier, s.name, s.enabled, s.is_linked)` per input — a link on an `enabled=False` socket is the smoking gun.

<a id="feedback_gn_new_socket_backfills_zero"></a>

## New inputs backfill existing modifiers with zero

*Adding a new GN interface input backfills EXISTING modifiers with type-zero, not the socket default — clamp/guard the value in-graph for backward compat*

When you add a new input socket to a Geometry Nodes group interface, modifiers that
already exist on objects do NOT pick up the socket's `default_value` — they store
**type-zero** (Int→0, Float→0.0). Only newly-added modifiers get the default.

**Why:** a stored `Tube Count = 0` (from a legacy modifier) fed a `Duplicate Elements`
Amount → zero tubes → silently broke every existing use of the group. The socket's
`min_value=1` does not protect it (min only clamps UI edits, not the stored legacy 0).

**How to apply:** for any new input that must be ≥1 (counts, divisors) or has a
meaningful nonzero default, **clamp/guard it inside the graph** (e.g. a `Math MAXIMUM
(value, 1)` node feeding the consumer) so a legacy stored 0 still behaves like the
default. Verify with the evaluated-geometry-unchanged gate at the default value across
`0` and `1`. Bit me on GN_EdgeDestruct's multi-tube feature (2026-07-18). Related:
[Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_socket_default), [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md).

**Idiom for a per-axis weight TRIPLE** (X/Y/Z factors where 0 is a legal value, so
`MAXIMUM` is not available): guard the whole triple — `CombineXYZ` → `VectorMath
DOT_PRODUCT` with `(1,1,1)` (one node instead of two adds) → `Compare LESS_THAN 1e-6`
→ `Switch(VECTOR)` picking `(1,1,1)`. **All three at zero reads as all-on**, which
restores legacy modifiers AND removes a useless all-zero state; say so in the socket
tooltip. Used for GN_Wave's Ripple Axes / Affect Axes (2026-09-20).

**A BOOL is the nastiest case and cannot be guarded in-graph.** A new bool backfills
`False`, so a `Selection` socket whose interface default is `True` silently kills the
modifier in every scene saved before the socket existed — no clamp can tell "stored
False" apart from "user set False". Proven across a full save/reload cycle
(2026-09-21, GN_Wireframe: evaluated mesh went to 0 vertices). Adding a
default-**False** bool (e.g. `Invert Selection`) is always safe. So: when adding a
default-True gate, set the value explicitly on every modifier instance inside the
shipped .blend, and document the one-time manual re-tick for users' own scenes —
Stephko accepted that trade-off rather than add a guard checkbox.

<a id="feedback_gn_menu_socket_default"></a>

## Scripted Menu inputs need a default_value

*When adding a Menu (NodeSocketMenu) input to a GN group via script, set its interface default_value or it silently reads as nothing when driven*

When building a Geometry Nodes group via the Blender MCP/Python and adding a `NodeSocketMenu` interface input wired to a Menu Switch node, you MUST set the interface socket's `default_value` to a valid item NAME (string), e.g. `sock.default_value = "X"`. A freshly created menu socket has `default_value = ''` (empty).

**Why:** With an empty default, when the group is used as a modifier the menu resolves to nothing, so the Menu Switch outputs 0/false and any logic downstream silently misbehaves (in GN_Delete the axis filter read position as 0 everywhere and deleted nothing). The Asset Browser/node editor may still look fine, so it's easy to miss. Existing working menus (e.g. On Domain default `'Point'`, Selection Mode default `'Selection Group'`) all have a non-empty default.

**How to apply:**
- Interface menu default is a STRING = the enum item name: `sock.default_value = "X"`.
- The per-modifier override value, by contrast, is stored as an INT IDProperty (NodeEnumItem exposes only name/description, no usable identifier) — so for scripted tests drive alternate menu configs via the interface `default_value` and add a fresh modifier (it inherits the default), rather than assigning `modifier[socket_id]` an int.
- After setting modifier inputs in script, call `obj.update_tag(); bpy.context.view_layer.update()` BEFORE reading the evaluated mesh, or you see stale (un-deleted) geometry.

Related: [ST3E geonode modifier — build recipe, roster, publish checklist](asset-checklist.md), [Headless Blender and automation](../headless-and-automation.md#reference_blender_mcp). GN_Delete now has an "Axis Filter" panel (Filter by Axis / Filter Axis / Axis Center / Delete Side) gating the delete selection per side of an axis.

<a id="feedback_gn_menu_to_index_switch"></a>

## One menu → master Menu Switch → Index Switches

*One GN Menu param cannot drive several Menu Switch nodes — use one master Menu Switch (INT) -> Index Switch nodes*

A Blender geometry-nodes Menu socket carries a **shared pointer to a single Menu Switch's enum definition**. So a single exposed menu group-input can legally bind to only ONE Menu Switch node. Wiring the same `Noise Type` menu into two separate Menu Switch nodes (even with identical item names) is invalid — each Menu Switch owns its own enum, and the socket can only point at one. This was the error in GN_RandomizePosition (fixed 2026-06-03).

**Why:** Enums are per-node; the menu socket resolves to exactly one of them.

**How to apply:** To make ONE menu control N selections, build a single master `GeometryNodeMenuSwitch` with `data_type='INT'`, give each enum item a constant int value (0,1,2…), expose its Menu input as the group input. Feed its integer output into multiple `GeometryNodeIndexSwitch` nodes (one per data type — VECTOR, FLOAT, etc.), each routing the real data. API notes: IndexSwitch starts with 2 items (`index_switch_items.new()` to add); IndexSwitchItem and NodeEnumItem have NO `name`/`identifier` for the data sockets you can rename — data inputs stay `0/1/2`. The modifier stores a menu selection as an **int IDProperty** (0/1/2 by item order), not a string. A single Menu→single Switch is fine (Direction switch was left as-is). Related: [Geonode sockets, interfaces and menus](sockets-and-menus.md#feedback_gn_menu_socket_default), [Geonode layout](layout.md#feedback_gn_node_layout_spacing).

**Scripted recipe (confirmed live, Blender 5.0, GN_NormalTransfer 2026-07):** name the menu items via `ms.data_type='INT'; ed=ms.enum_definition; while len(ed.enum_items): ed.enum_items.remove(ed.enum_items[-1]); [ed.enum_items.new(n) for n in names]`. Adding items shifts the INT item socket identifiers to `Item_2/Item_3/…` (they start at the old A/B = 0/1) — set values by iterating `[s for s in ms.inputs if s.identifier.startswith('Item')]`, not by hardcoded id. Expose the dropdown with `interface.new_socket("Masking Mode", in_out='INPUT', socket_type='NodeSocketMenu')` then link `group_input.outputs["Masking Mode"] -> ms.inputs["Menu"]`; the menu override on the modifier is keyed by the socket identifier (e.g. `mod["Socket_6"]=2`).

**Gotcha — `NodeTreeInterface.move(item, pos)` is finicky:** `pos` counts across the flattened items_tree (inputs AND the output sockets/panels), and chaining several moves corrupts the order (each move re-indexes). Don't loop moves blindly — move ONE item to its target, re-read the input order, repeat only if needed. In practice moving the Geometry input to index 0 was enough to fix a scrambled order; verify with `[it.name for it in I.items_tree if it.item_type=='SOCKET' and it.in_out=='INPUT']` after each move.
