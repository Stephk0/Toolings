# Changelog — Modifier Stack Actions

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
