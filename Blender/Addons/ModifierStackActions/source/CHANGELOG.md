# Changelog — Modifier Stack Actions

## 1.2.0 — 2026-10-22

- **Fix:** **Move to Last** (and Move Down) did nothing, without a warning, when the stack had
  modifiers with **Pin to Last** on. It now stops right above the pinned modifiers, and the
  entries name that: **Move to Last (Before Pinned)**.
- **New:** **Move After Pinned (Pin)** on a normal modifier and **Move Before Pinned (Unpin)** /
  **Move to First (Unpin)** on a pinned one, shown when the stack has pinned modifiers.
- **New:** **Duplicate Modifier** in the right-click menu: a copy directly below the modifier.
- **New:** **Apply Modifiers Above**: applies every modifier above the clicked one into the
  mesh, top to bottom. Switched-off modifiers are skipped and kept; shared meshes ask to be
  made single user first.
- **Fix:** Add Modifier Before / After and Paste Before / After next to a pinned modifier left
  the new modifier at the end of its block; it now takes the anchor's pin setting and lands
  next to it.

## 1.1.0 — 2026-10-21

- **New:** **Move Up / Move Down** in the right-click menu, next to Move to First / Last.
- **New:** **Copy Modifier** and **Paste Modifier Before / After**: copy a modifier, then
  right-click any modifier (same object or another one) to paste a copy with all its settings
  directly before or after it. The paste entries show the copied modifier's name.

## 1.0.0 — 2026-10-20

- **New:** right-click a modifier → **Show Up To Here**: hides every later modifier in the
  viewport, with a banner and **Restore** in the Modifiers panel. Run it again on the same
  modifier to restore. Modifiers that were already off stay off.
- **New:** right-click a modifier → **Extract Up To Here**: new object from the stack evaluated
  up to and including that modifier. The source object is not changed.
- **New:** **Extract Up To Here As...**: same, with a dialog to change the default
  `<Object>_<Modifier>` name first. The name is also editable in the Redo panel.
- **New:** **Add Modifier Before / After**: Blender's Add Modifier menu (all categories,
  Geometry Nodes asset catalogs, search) as a submenu; the new modifier lands next to the
  right-clicked one.
- **New:** **Move to First / Move to Last** in the right-click menu.
