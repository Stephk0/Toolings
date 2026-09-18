# Mass Collection Exporter — Export Flow

> Diagrams generated from `source/__init__.py` v13.7.0. Line references point at the
> dispatching code so this stays checkable against the source.

- [1. Top-level run](#1-top-level-run)
- [2. Per-collection gate and mode priority](#2-per-collection-gate-and-mode-priority)
- [3. Inside the empty-origins modes](#3-inside-the-empty-origins-modes)
- [4. The shared export tail](#4-the-shared-export-tail)
- [5. Settings reference](#5-settings-reference)

---

## 1. Top-level run

`MASSEXPORTER_OT_export_all.execute()` — `source/__init__.py:1277`

Everything below happens once per click, wrapped around the per-collection loop.

```mermaid
flowchart TD
    subgraph LOOP ["for each item where export_enabled AND collection AND export_path"]
        H["export_collection item"] --> I["see diagram 2"]
    end

    A["Export All Collections"] --> B["Force OBJECT mode"]
    B --> C["Recover stale __mexport_ objects<br/>left by a crashed prior run"]
    C --> D["Snapshot selection, active object<br/>and every parented empty location"]
    D --> E{"Any enabled collection with<br/>Move All Empties to Origin?"}
    E -->|yes| F["move_empties_to_origin_core_logic<br/>runs once, scene-wide"]
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

`export_collection()` — `source/__init__.py:1688`

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

    M1 -->|OFF| M2{"Group by Suffix?<br/>AND suffix list not empty"}
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

> **Mode 2 has a silent fallthrough.** `use_suffix_grouping` only fires when the global
> suffix list has at least one entry. With *Group by Suffix* ticked but no suffixes defined,
> the collection quietly drops to mode 3 / 4 / 5 instead.

---

## 3. Inside the empty-origins modes

Modes 3 and 4 both branch again on `join_empty_children`, and mode 3 can delegate into
mode 4's joining routine.

```mermaid
flowchart TD
    subgraph M3 ["MODE 3 - Sub-Collections as Single (line 1757)"]
        A1["Meshes sitting directly<br/>in the parent collection"] --> A2["export_objects_as_single<br/>named collection_main"]
        A2 --> A3["then: for each child collection"]
        A3 --> A4{"Use Parent Empties<br/>AND Join Empty Children?"}
        A4 -->|yes| A5["export_collection_with_all_empties_joined<br/>one joined file per sub-collection"]
        A4 -->|no| A6["export_objects_as_single<br/>one merged file per sub-collection"]
    end

    subgraph M4 ["MODE 4 - Use Parent Empties (line 1989)"]
        B1{"Join Empty Children?"} -->|ON| B2["export_collection_with_all_empties_joined<br/>ALL empties joined into ONE file"]
        B1 -->|OFF| B3["export_with_empty_origins_individual"]
        B3 --> B4{"Any empty with<br/>mesh children found?"}
        B4 -->|yes| B5["One file per empty<br/>Center Each Empty parks it at 0,0,0"]
        B4 -->|no empties| B6{"Merge?"}
        B6 -->|ON| B7["Fallback: one merged file"]
        B6 -->|OFF| B8["Fallback: one file per object"]
    end
```

**Join path only:** when joining, `apply_modifiers_before_join` bakes modifiers onto the
temporary duplicates, and its sub-option `apply_only_visible` drops modifiers whose viewport
toggle is off. This is a *separate, older* setting from the global **Only Visible Modifiers**
in diagram 4 — it governs the join path only, and still defaults to OFF.

---

## 4. The shared export tail

Every mode above eventually funnels into `export_objects_as_single()` / `export_single_object()`
and then the single choke point `perform_export()` — `source/__init__.py:2920`.

```mermaid
flowchart TD
    subgraph PEX ["perform_export - the single choke point"]
        PE["Build filepath"] --> PE1{"Export Rig with Mesh?"}
        PE1 -->|ON| PE2["_select_associated_rigs<br/>pulls armatures into the selection"]
        PE1 -->|OFF| PE3{"Apply Modifiers?"}
        PE2 --> PE3
        PE3 -->|OFF| PE8["FBX / OBJ / DAE / glTF<br/>exporter-side modifier flags all FALSE"]
        PE3 -->|ON| PE4["Duplicate each mesh<br/>copy takes the original name"]
        PE4 --> PE5{"Only Visible Modifiers?<br/>v13.7.0, default ON"}
        PE5 -->|ON| PE6["DELETE show_viewport=False modifiers<br/>off the copy BEFORE applying<br/>armature bindings exempt"]
        PE5 -->|OFF| PE6B["Keep every modifier"]
        PE6 --> PE7["modifier_apply on the copy"]
        PE6B --> PE7
        PE7 --> PE8
    end

    T0["export_objects_as_single<br/>or export_single_object"] --> T1["Select objects<br/>Snapshot loc / rot / scale"]
    T1 --> T2{"Move to Center?<br/>per collection"}
    T2 -->|ON| T3["_center_root_objects_temporarily<br/>park roots at world 0,0,0"]
    T2 -->|OFF| T4{"Apply Transforms?<br/>global"}
    T3 --> T4
    T4 -->|ON| T5["_apply_transforms_via_duplicates<br/>destructive, so runs on temp copies"]
    T4 -->|OFF| T6{"Override Materials?"}
    T5 --> T6
    T6 -->|ON| T7["apply_material_overrides onto<br/>whatever will actually be exported"]
    T6 -->|OFF| PE
    T7 --> PE

    PE8 --> F1["finally: delete temp copies,<br/>restore names, un-center,<br/>restore loc / rot / scale"]

    classDef new fill:#2f4f2f,stroke:#66cc66,color:#ffffff
    class PE5,PE6 new
```

### Why the modifier step looks like that

`bpy.ops.object.modifier_apply()` has **no notion of `show_viewport`** — it bakes a modifier
that is switched off in the stack exactly as if it were on. Measured on a cube with a visible
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
| Apply Modifiers | `apply_modifiers_before_join` | Join path only |
| Only Visible Modifiers | `apply_only_visible` | Join path only, default OFF |
| Merge | `merge_to_single` | Mode 5a, and mode 4's no-empties fallback |
| Move to Center | `move_to_center` | Diagram 4 — the shared tail |

### Global scene settings — apply to every collection

| UI label | Property | Where it acts |
|---|---|---|
| Export Format | `export_format` | Diagram 4 — which exporter runs |
| Export Hidden Collections | `export_hidden_collections` | Diagram 2 — the hidden gate |
| Apply Modifiers | `apply_modifiers` | Diagram 4 |
| Only Visible Modifiers | `apply_only_visible_modifiers` | Diagram 4, **default ON** (v13.7.0) |
| Skip Armature Modifier | `skip_armature_modifier` | Diagram 4 — suppresses ALL armature modifiers |
| Export Rig with Mesh | `export_rig_with_mesh` | Diagram 4 |
| Apply Transforms | `apply_transforms` | Diagram 4 |
| Override Materials | `override_materials` | Diagram 4 |
| Suffix list | `suffix_items` | Gates mode 2 |
| Debug Mode | `debug_mode` | Console output throughout |

---

## Quick-export entry points

The three quick-export buttons reuse the same machinery. They build a temporary collection
item, copy the reference collection's settings onto it, and drop into diagram 2:

```mermaid
flowchart LR
    Q1["Export Collection of Selected"] --> C1["Copy parent settings<br/>force Sub-Collections as Single OFF"]
    Q2["Export Sub-Collections of Selected"] --> C2["Copy reference settings"]
    Q3["Export Selected Objects"] --> C3["Suffix grouping, then Merge,<br/>then Individual - selection only"]
    C1 --> D["export_collection<br/>and the shared tail"]
    C2 --> D
    C3 --> D
```
