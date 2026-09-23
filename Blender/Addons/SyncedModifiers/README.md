# Synced Modifiers

**Version:** 2.5.0 · **Blender:** 4.2+ · **Category:** Object · **Location:** 3D View ▸ Sidebar (N) ▸ Item ▸ Synced Modifiers · **Author:** Stephan Viranyi

Add modifiers to multiple objects at once and keep them synchronized using Blender's
driver system — now with Geometry Nodes support.

## Features
- Driver-based sync of modifier properties across many objects
- Geometry Nodes modifier support with dynamic input syncing
- Sync ID system (`ModifierName (Source:abc123)`) for reliable source tracking
- Reference-field sync (Object / Collection / Material) with viewport refresh
- Find original source by tracing the driver chain; resync when GN inputs change

## Install
Drag-and-drop [`distribution/SyncedModifiers_v2.5.0.zip`](distribution/SyncedModifiers_v2.5.0.zip)
onto Blender (4.2+), or install it via *Edit ▸ Preferences ▸ Add-ons ▸ Install from Disk*.

---

[Developer notes](source/DEVELOPMENT.md)
