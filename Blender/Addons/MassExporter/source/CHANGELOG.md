# Mass Collection Exporter — changelog

User docs: [README](../README.md). The authoritative current version is `VERSION` in
`__init__.py`.

## v13.8.0
Reliability release from a full review. Every item below is covered by
`source/tests/headless_export_test.py` (Blender 5.0 and 4.5, 44 checks).

Source data
- **Override Materials** no longer replaces the source meshes' materials — the override is
  applied to the exported selection and restored after each export (object-linked slots too)
- **Add M_ Prefix** renames only the exported objects' materials, and only for the export
  (it used to rename every material in the file permanently)
- **Move All Empties to Origin** moves only the empties of collections that have it ticked
  (it moved every enabled collection's empties), and moves to world origin for parented empties

Exported geometry
- **Join Empty Children** bakes each child's own modifier stack before joining (the join
  used to keep only the active child's stack and apply it to all children); with no apply
  option on, modifiers are left out
- Join path honours the global **Only Visible Modifiers** (hidden modifiers were baked)
- Meshes with **shape keys** get their modifiers baked (modifier_apply refused them and the
  modifier was dropped silently); the bake now uses the depsgraph
- **Whole Collection as One File** keeps the hierarchy when a parent has modifiers, and
  honours **Apply Transforms**
- **Group by Suffix** exports an empty's child once (it was also exported under its own name)
- **Use Parent Empties** exports meshes that sit under no empty (they were dropped); the
  empty modes include grandchildren (empty > mesh > mesh)
- **Center Each Empty** centres parented empties in world space
- Temporary copies no longer depend on *Preferences > Editing > Duplicate Data*

Formats
- ⚠️ **Collada (DAE) removed** — Blender 5.0 dropped the exporter; scenes set to DAE fall
  back to FBX
- **OBJ** export works again (the axis enum names were wrong, every OBJ export failed)
- **glTF** is written as `.glb` explicitly (the code assumed `.gltf`)
- Export errors are reported in the status bar instead of only the console

Settings and quick exports
- **Assign if No Material** works without Override Materials
- **Group by Suffix** only takes over when at least one suffix is enabled
- Quick exports copy **every** collection setting (whole-collection mode, suffix grouping,
  move to center were lost); temp list items are removed even when an export fails
- ⚠️ **Export Selected Object(s)** follows Suffix grouping → Merge → one file per object;
  with Merge off, several selected objects now give one file each (they were always merged)
- Crash recovery deletes leftover temp copies and restores `__mexport_xform_` names
- Removed stale code: the list refresh button, `visibility_synced`, the unused
  "Custom FBX ASCII" setting
- FBX *Apply Transform* tooltip and Unity tips warn that it is experimental for rigs

## v13.7.0
- **Only Visible Modifiers** — exports bake only viewport-enabled modifiers (default ON)
- Workaround for Blender's `modifier_apply` ignoring `show_viewport`: disabled modifiers are
  stripped from the temporary export copy before applying
- Objects whose modifiers are *all* hidden now skip duplication entirely and export as-is
- Preserved armature bindings are exempt from the visibility filter
- ⚠️ Behaviour change: objects carrying viewport-disabled modifiers now export differently.
  Turn the option off to restore v13.6 output.

## v13.6.3
- Restored the per-collection **Group by Suffix** checkbox in Collection Options. The setting
  existed and drove the export flow, but the checkbox was lost in the v13 UI rewrite.

## v13.6.2 and earlier v13
- See git history.

## v12.2
- **Export Selected Object(s)** — quick export button that exports the collections of the
  selected objects using their configured settings

## v12.1
- **Quick Export from Selection** — export the collection or sub-collections of the selected
  object with one click

## v12.0
- Export meshes even when no empties are present (falls back to normal mesh export)
- Improved error handling and validation, better object existence checks
- Comprehensive debug mode for troubleshooting

## Earlier
- v11: Enhanced empty joining logic
- v10: Added modifier application
- v9: Sub-collection export modes
- v8: Parent empty centering
- v7: Initial release
