# Geonode sockets, interfaces and menus

Scripting the group interface, links and Menu sockets. Interface conventions (panels, names,
Selection gate) live in `Blender/Addons/LLMGeonodePipeline/GEONODE_CRITERIA.md`.

- [Relink by socket identifier, not name](#feedback_gn_link_rewire_gotchas)
- [New inputs backfill existing modifiers with zero](#feedback_gn_new_socket_backfills_zero)
- [Menu sockets: default and overrides](#feedback_gn_menu_socket_default)
- [One menu → master Menu Switch → Index Switches](#feedback_gn_menu_to_index_switch)
- [Interface identifiers follow creation order](#gn_socket_identifiers_by_creation_order)

<a id="feedback_gn_link_rewire_gotchas"></a>

## Relink by socket identifier, not name

*Resolve sockets enabled-identifier → enabled-name → identifier → name; Viewer item sockets self-delete on unlink*

**Why:** every failure here is silent — the link "succeeds" on the wrong or a disabled socket and
the geometry changes with no error.

**How to apply:**
- **Key relinks on `socket.identifier`.** Display names can repeat (two "Auto Angle Degrees"
  inputs) and `node.inputs[name]` returns the first match.
- **Prefer ENABLED sockets.** Multi-type nodes keep disabled variants: Compare `data_type='INT'`
  enables `A_INT` while the disabled FLOAT socket owns identifier `"A"`; Random Value FLOAT
  enables `Min_001/Max_001` (named "Min"/"Max") while disabled vector sockets own `"Min"`. A link
  on a disabled socket no-ops — the consumer falls back to its default. Exact order, no shortcuts:
  **enabled-identifier → enabled-name → identifier → name.** Copy a known-good `_pick` (e.g.
  `Blender/Geonodes/_build/build_gn_mosaic.py`) rather than rewriting it.
- Diagnose by dumping `(s.identifier, s.name, s.enabled, s.is_linked)` per input.
- **Viewer inputs are dynamic items that vanish when unlinked** (only `__extend__` remains). Skip
  viewer links in rewiring passes, or relink into `__extend__`.
- Verify evaluated vertex positions unchanged before saving (`run_pipeline.py` gate).

<a id="feedback_gn_new_socket_backfills_zero"></a>

## New inputs backfill existing modifiers with zero

*A new interface input gives EXISTING modifiers type-zero, not the socket default — guard it in-graph; a default-True bool can't be guarded*

Only newly added modifiers get `default_value`; existing ones store 0 / 0.0 / False / None.
`min_value` doesn't help (it only clamps UI edits).

**How to apply:**
- Counts/divisors: `Math MAXIMUM(value, 1)` before the consumer (a legacy `Tube Count = 0` gave
  zero tubes). Verify the geometry gate at 0 and 1.
- Per-axis weight triple where 0 is legal: `dot(CombineXYZ, (1,1,1)) < 1e-6` →
  `Switch(VECTOR)` → `(1,1,1)`; all-zero reads as all-on (say so in the tooltip).
- **A default-True bool cannot be guarded** — stored False is indistinguishable from user False
  (GN_Wireframe went to 0 verts after adding `Selection`). Set it explicitly on every modifier in
  the shipped .blend and document the re-tick for users. Default-False bools are always safe.

<a id="feedback_gn_menu_socket_default"></a>

## Menu sockets: default and overrides

*A scripted Menu input needs a string `default_value`; a modifier's override is the item's value id, not its position*

**How to apply:**
- A new `NodeSocketMenu` has `default_value = ''` → the Menu Switch outputs 0 and downstream
  logic silently misbehaves. Set `sock.default_value = "X"` (the item NAME).
- The modifier stores the override as an INT **value id**, not the 0-based position, and
  `NodeEnumItem` exposes no `.value`. Cleanly built menus have ids 0,1,2… so `mod[sock] = int`
  works by luck; hand-built ones don't (Shear's were non-sequential → "Missing property").
- Panels never come before loose sockets of the same level: the modifier draws sockets first,
  and `interface.move(panel, 0)` / `move_to_parent(panel, root, 1)` is ignored. To put a panel
  on top, file every other socket of that level (except Geometry) into panels.
- Scripted tests: set the interface `default_value` by name and add a FRESH modifier (it picks the
  default) instead of writing int overrides.
- The interface `default_value` is ALSO stored as an id. Renumber the items (rebuild the Menu
  Switch) and the old id now names another item: GNG_SelectionGate v2→v3 turned 40 tools'
  default `Add` (id 2) into `Intersect`. Re-set every consumer's `default_value` by name after.
- Adding a Menu input to a group that already has modifiers stores **-1** on them (the socket has
  no items until linked to a Menu Switch) — the menu then selects nothing. Write
  `mod[identifier] = <id>` after linking, and check `mod.get(identifier) != -1`.
- After setting modifier inputs, `obj.update_tag(); bpy.context.view_layer.update()` before
  reading the evaluated mesh.

<a id="feedback_gn_menu_to_index_switch"></a>

## One menu → master Menu Switch → Index Switches

*One Menu input can bind to only ONE Menu Switch — drive several selections from one master `MenuSwitch(INT)` into Index Switches*

**Why:** a Menu socket points at a single Menu Switch's enum definition; two Menu Switches off one
menu (even with identical items) is invalid.

**How to apply:**
- Master `GeometryNodeMenuSwitch(data_type='INT')`, item values 0,1,2…, its Menu input exposed;
  its int output feeds one `GeometryNodeIndexSwitch` per data type. IndexSwitch starts with 2
  items (`index_switch_items.new()`); its data inputs stay `0/1/2`.
- Naming items: **rename the two default items in place** (`ed = ms.enum_definition;
  ed.enum_items[0].name = "A"`), then `ed.enum_items.new(name)` for the rest. Removing all and
  re-adding continues the value counter (ids start at 2), so the 0/1 an existing modifier — or a
  new input's zero backfill — stores selects nothing. Adding items shifts INT item identifiers
  (`Item_2/Item_3/…`) — iterate
  `[s for s in ms.inputs if s.identifier.startswith('Item')]`, never hardcode.
- Expose: `interface.new_socket("Mode", in_out='INPUT', socket_type='NodeSocketMenu')` → link to
  `ms.inputs["Menu"]`.
- `iface.new_panel()` has no `parent` kwarg — nest with
  `iface.move_to_parent(panel, parent, len(parent.interface_items))`.
- `NodeTreeInterface.move(item, pos)` counts across the flattened `items_tree` and chained moves
  re-index — move one item, re-read the order, repeat only if needed.
- A menu inside a helper group propagates outward — see
  [vertex data channels](nodes-and-fields.md#feedback_gn_vertex_data_channels).

<a id="gn_socket_identifiers_by_creation_order"></a>

## Interface identifiers follow creation order

*`Socket_0, Socket_1, …` are minted in creation order (each `new_panel` burns one) — inserting a socket mid-interface re-points every saved modifier value below it*

A rebuild-from-scratch script mints identifiers the same way, so a `new_socket` call added in the
middle of a panel renumbers everything after it, and values saved on users' modifiers land on
the wrong input (their Gap value on Seed). Renaming a socket or re-parenting it keeps the
identifier, so both are safe.

**How to apply:**
- Declare new sockets **last** (after the Geometry output), then
  `iface.move_to_parent(item, panel, index)` to file them; `iface.move(panel, i)` reorders panels
  among root children. Diff `identifier → name` before and after.
- Keep the socket object returned by `new_socket`. `iface.items_tree["X"]` returns the PANEL
  when a panel and a socket share a name — or look items up by name AND `item_type`.
- Bool overrides need real bools: `mod[id] = int(True)` and `mod[id + "_use_attribute"] = 1`
  raise "Cannot assign a 'int' value to Boolean IDProperty".
- Display name ≠ identifier on some nodes: Accumulate Field's group socket is identifier
  `Group Index`, displayed `Group ID`. On a Math node `"Value"` is input 0's identifier, so
  linking a second operand needs `"Value_001"`.
