# Mass Collection Exporter — Export Flow

> Diagrams describe `source/__init__.py` v13.8.0. Function names point at the
> dispatching code so this stays checkable against the source.

- [1. Top-level run](#1-top-level-run)
- [2. Per-collection gate and mode priority](#2-per-collection-gate-and-mode-priority)
- [3. Inside the empty-origins modes](#3-inside-the-empty-origins-modes)
- [4. The shared export tail](#4-the-shared-export-tail)
- [5. Settings reference](#5-settings-reference)

---

## 1. Top-level run

`MASSEXPORTER_OT_export_all.execute()`

Everything below happens once per click, wrapped around the per-collection loop.

```mermaid
flowchart TD
    subgraph LOOP ["for each item where export_enabled AND collection AND export_path"]
        H["export_collection item"] --> I["see diagram 2"]
    end

    A["Export All Collections"] --> B["Force OBJECT mode"]
    B --> C["Recover stale temp copies and<br/>__mexport_ names left by a crashed run"]
    C --> D["Snapshot selection, active object<br/>and every empty transform"]
    D --> E{"Any enabled collection with<br/>Move All Empties to Origin?"}
    E -->|yes| F["move_empties_to_origin_core_logic<br/>only those collections, world origin"]
    E -->|no| G["skip pre-pass"]
    F --> LOOP
    G --> LOOP

    LOOP --> Z["Restore empty positions,<br/>selection and active object"]
    Z --> Y["Report count plus first 3 collection names<br/>in the status bar"]
```

**Note:** the loop keys off each row's `export_enabled` checkbox, **not** the row highlighted
in the UIList. A per-item `try/except` means one failing collection does not abort the rest.

---

## 2. Per-collection gate and mode priority

`export_collection()`

This is the diagram that matters. The five export modes are **mutually exclusive** and
resolved in a fixed priority order — turning two on does not combine them, the higher one
wins silently.

```mermaid
flowchart TD
    S["export_collection item"] --> P{"export_path exists?"}
    P -->|no| PM["Try mkdir"]
    PM -->|fails| PERR["ERROR - skip collection"]
    PM -->|ok| HID
    P -->|yes| HID{"Collection effectively hidden?"}

    HID -->|"hidden AND Export Hidden Collections OFF"| SKIP["WARNING - skip collection"]
    HID -->|"hidden AND toggle ON"| ISO["_unhide_collection_for_export<br/>isolates layer / local-view / hidden state"]
    HID -->|not hidden| ISO

    ISO --> M1{"Whole Collection<br/>as One File?"}
    M1 -->|ON| R1["MODE 1 - export_collection_as_single_fbx<br/>every object type plus hierarchy in one file<br/>name = Custom Filename or collection name"]

    M1 -->|OFF| M2{"Group by Suffix?<br/>AND an enabled suffix"}
    M2 -->|ON| R2["MODE 2 - export_with_suffix_grouping<br/>one file per base name"]

    M2 -->|OFF| M3{"Sub-Collections<br/>as Single?"}
    M3 -->|ON| R3["MODE 3 - export_subcollections_as_single<br/>see diagram 3"]

    M3 -->|OFF| M4{"Use Parent Empties?"}
    M4 -->|ON| R4["MODE 4 - export_with_empty_origins<br/>see diagram 3"]

    M4 -->|OFF| M5{"Merge?"}
    M5 -->|ON| R5["MODE 5a - export_objects_as_single<br/>one file named after the collection"]
    M5 -->|OFF| R6["MODE 5b - export_single_object per object<br/>one file per mesh"]

    R1 --> FIN["finally: _restore_collection_for_export"]
    R2 --> FIN
    R3 --> FIN
    R4 --> FIN
    R5 --> FIN
    R6 --> FIN

    classDef mode fill:#2d4a63,stroke:#5b9bd5,color:#ffffff
    classDef bail fill:#5a3535,stroke:#cc6666,color:#ffffff
    class R1,R2,R3,R4,R5,R6 mode
    class SKIP,PERR bail
```

### Priority table

| # | Setting | Property | Result |
|---|---------|----------|--------|
| 1 | Whole Collection as One File | `export_as_single_fbx` | One file, all object types, hierarchy intact |
| 2 | Group by Suffix | `use_suffix_grouping` | One file per base name — `cube` + `cube_COL` becomes `cube.fbx` |
| 3 | Sub-Collections as Single | `export_subcollections_as_single` | One file per child collection, plus `<name>_main` |
| 4 | Use Parent Empties | `use_empty_origins` | Empties drive origins — joined or per-empty |
| 5 | Merge / *(none)* | `merge_to_single` | One merged file, or one file per object |

> **Mode 2 needs an enabled suffix.** `use_suffix_grouping` only fires when the global
> suffix list has at least one *enabled*, non-empty suffix. With *Group by Suffix* ticked but
> no suffix switched on, the collection drops to mode 3 / 4 / 5 instead.
>
> Each mesh lands in exactly one suffix group: children of an empty go with the empty, then
> meshes of a sub-collection go with the sub-collection, then any other mesh by its own name.

---

## 3. Inside the empty-origins modes

Modes 3 and 4 both branch again on `join_empty_children`, and mode 3 can delegate into
mode 4's joining routine.

```mermaid
flowchart TD
    subgraph M3 ["MODE 3 - Sub-Collections as Single"]
        A1["Meshes sitting directly<br/>in the parent collection"] --> A2["export_objects_as_single<br/>named collection_main"]
        A2 --> A3["then: for each child collection"]
        A3 --> A4{"Use Parent Empties<br/>AND Join Empty Children?"}
        A4 -->|yes| A5["export_collection_with_all_empties_joined<br/>one joined file per sub-collection"]
        A4 -->|no| A6["export_objects_as_single<br/>one merged file per sub-collection"]
    end

    subgraph M4 ["MODE 4 - Use Parent Empties"]
        B1{"Join Empty Children?"} -->|ON| B2["export_collection_with_all_empties_joined<br/>every empty member AND loose mesh<br/>joined into ONE file named after the collection"]
        B1 -->|OFF| B3["export_with_empty_origins_individual"]
        B3 --> B5["One file per empty member<br/>Center Each Empty parks the empty at world 0,0,0"]
        B3 --> B6{"Loose meshes<br/>under no empty?"}
        B6 -->|Merge ON| B7["one merged file named after the collection"]
        B6 -->|Merge OFF| B8["one file per loose mesh"]
    end
```

**Empty membership:** a mesh belongs to its *nearest* empty ancestor, so grandchildren
(empty → mesh → mesh) are included and nested empties never claim the same mesh twice.

**Join path:** every temporary copy bakes its *own* modifier stack before the join when
`apply_modifiers_before_join` or the global *Apply Modifiers* is on; otherwise all modifiers
are removed from the copies. (`bpy.ops.object.join` keeps only the active object's stack, so
joining un-baked copies used to spread one child's modifiers over all of them.) Hidden
modifiers are dropped when the global **Only Visible Modifiers** is on, or when the
per-collection `apply_only_visible` is ticked.

---

## 4. The shared export tail

Every mode above eventually funnels into `export_objects_as_single()` / `export_single_object()`
and then the single choke point `perform_export()`.

```mermaid
flowchart TD
    subgraph PEX ["perform_export - the single choke point"]
        PE["Build filepath"] --> PE1{"Export Rig with Mesh?"}
        PE1 -->|ON| PE2["_select_associated_rigs<br/>pulls armatures into the selection"]
        PE1 -->|OFF| PE3{"Apply Modifiers?"}
        PE2 --> PE3
        PE3 -->|OFF| PEM["Material Options on the final selection<br/>restored after export"]
        PE3 -->|ON| PE4["Copy each mesh<br/>copy takes the original name"]
        PE4 --> PE5{"Only Visible Modifiers?<br/>default ON"}
        PE5 -->|ON| PE6["DELETE show_viewport=False modifiers<br/>off the copy BEFORE baking<br/>armature bindings exempt"]
        PE5 -->|OFF| PE6B["Keep every modifier"]
        PE6 --> PE7["Depsgraph bake into a new mesh<br/>works with shape keys<br/>children re-pointed at the copy"]
        PE6B --> PE7
        PE7 --> PEM
        PEM --> PE8["FBX / OBJ / glTF<br/>exporter-side modifier flags all FALSE"]
    end

    T0["export_objects_as_single<br/>or export_single_object"] --> T1["Select objects<br/>Snapshot loc / rot / scale"]
    T1 --> T2{"Move to Center?<br/>per collection"}
    T2 -->|ON| T3["_center_root_objects_temporarily<br/>park roots at world 0,0,0"]
    T2 -->|OFF| T4{"Apply Transforms?<br/>global, every mode"}
    T3 --> T4
    T4 -->|ON| T5["_apply_transforms_via_duplicates<br/>destructive, so runs on temp copies<br/>children keep their parent"]
    T4 -->|OFF| PE
    T5 --> PE

    PE8 --> F1["finally: restore materials, parents,<br/>delete temp copies, restore names,<br/>un-center, restore loc / rot / scale"]

    classDef new fill:#2f4f2f,stroke:#66cc66,color:#ffffff
    class PE5,PE6 new
```

### Why the modifier step looks like that

`bpy.ops.object.modifier_apply()` has **no notion of `show_viewport`** — it bakes a modifier
that is switched off in the stack exactly as if it were on. It also refuses meshes with shape
keys. Since v13.8.0 the copy is baked through the depsgraph (`Mesh.new_from_object`) after the
unwanted modifiers are deleted, which handles both. Measured on a cube with a visible
Subsurf and a disabled 3x Array:

| | Vertices |
|---|---|
| What the viewport shows | 26 |
| Vanilla "apply all modifiers" | **78** — the disabled Array got baked |
| *Only Visible Modifiers* ON | 26 |

The fix is to **delete** the disabled modifiers from the throwaway copy rather than skip them
in the apply loop. Deleting keeps stack order intact, so whatever follows a stripped modifier
evaluates on the previous result, exactly like the viewport. Source objects are never touched.

If *every* modifier on an object is hidden, no copy is made at all and the object exports as-is.

---

## 5. Settings reference

### Per-collection — one row in the collection list

| UI label | Property | Where it acts |
|---|---|---|
| Export | `export_enabled` | Diagram 1 — the loop filter |
| Export Path | `export_path` | Diagram 2 — created if missing |
| Whole Collection as One File | `export_as_single_fbx` | Mode 1 |
| Custom Filename | `single_fbx_custom_name` | Mode 1 filename |
| Group by Suffix | `use_suffix_grouping` | Mode 2 |
| Sub-Collections as Single | `export_subcollections_as_single` | Mode 3 |
| Use Parent Empties | `use_empty_origins` | Mode 4 |
| Center Each Empty | `center_parent_empties` | Mode 4, per-empty centering |
| Move All Empties to Origin | `move_empties_to_origin_on_export` | Diagram 1 — scene-wide pre-pass |
| Join Empty Children | `join_empty_children` | Modes 3 and 4 |
| Apply Modifiers | `apply_modifiers_before_join` | Join path: bake each copy even when global Apply Modifiers is off |
| Only Visible Modifiers | `apply_only_visible` | Join path: skip hidden modifiers even when the global toggle is off |
| Merge | `merge_to_single` | Mode 5a, and mode 4's no-empties fallback |
| Move to Center | `move_to_center` | Diagram 4 — the shared tail |

### Global scene settings — apply to every collection

| UI label | Property | Where it acts |
|---|---|---|
| Export Format | `export_format` | Diagram 4 — which exporter runs (FBX, OBJ, glTF as `.glb`) |
| Export Hidden Collections | `export_hidden_collections` | Diagram 2 — the hidden gate |
| Apply Modifiers | `apply_modifiers` | Diagram 4 |
| Only Visible Modifiers | `apply_only_visible_modifiers` | Diagram 4, **default ON** (v13.7.0) |
| Skip Armature Modifier | `skip_armature_modifier` | Diagram 4 — suppresses ALL armature modifiers |
| Export Rig with Mesh | `export_rig_with_mesh` | Diagram 4 |
| Apply Transforms | `apply_transforms` | Diagram 4, every mode |
| Override Materials / Assign if No Material / Add M_ Prefix | `override_materials`, `assign_if_no_material`, `add_m_prefix` | Diagram 4 — exported file only, restored after |
| Suffix list | `suffix_items` | Gates mode 2 (needs an enabled suffix) |
| Debug Mode | `debug_mode` | Console output throughout |

---

## Quick-export entry points

The three quick-export buttons reuse the same machinery. The collection buttons build a
temporary collection item, copy **every** setting of the reference collection onto it (minus
its custom filename), and drop into diagram 2:

```mermaid
flowchart LR
    Q1["Export Collection of Selected"] --> C1["Copy parent settings<br/>force Sub-Collections as Single OFF"]
    Q2["Export Sub-Collections of Selected"] --> C2["Copy reference settings"]
    Q3["Export Selected Objects"] --> C3["Suffix grouping, then Merge (2+ objects),<br/>then one file each - selection only"]
    C1 --> D["export_collection<br/>and the shared tail"]
    C2 --> D
    C3 --> D
```
