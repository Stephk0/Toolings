# Mass Collection Exporter — changelog

User docs: [README](../README.md). The authoritative current version is `VERSION` in
`__init__.py`.

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
