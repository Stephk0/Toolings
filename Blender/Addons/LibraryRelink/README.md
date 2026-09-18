# Library Relink

**Version:** 1.0.0
**Blender:** 4.2+ (extension), tested on 5.0
**Location:** 3D View > Sidebar (N) > Relink

Bulk-relink the linked libraries of the current .blend file to a new folder —
with a dry-run preview — instead of relinking every library one by one in the
Outliner.

Typical use case: a scene links a dozen `GN_*.blend` geonode assets from
`D:\...\Geonodes\` and that folder moves (new drive, new machine, project
handoff). One Preview + one Relink click repoints all of them.

## Usage

1. Open the .blend whose links you want to fix.
2. In the 3D View sidebar, open the **Relink** tab.
3. Set **New Folder** to the destination the libraries should point to.
4. Optionally set **Only From** to the old folder — only libraries currently
   inside it are touched, so unrelated links (Blender essentials, other asset
   libraries) stay untouched. Leave empty to consider every linked library.
5. Click **Preview**. Every library is classified:
   - **Relink** (refresh icon) — same filename exists in the new folder; will be repointed. Uncheck individual entries to exclude them.
   - **Missing** (error icon) — no matching file in the new folder; left untouched, so you never end up with broken links.
   - **Filtered** (filter icon) — outside the *Only From* folder; left untouched.
   - **Unchanged** (checkmark) — already points at the new folder.
6. Click **Relink** and confirm. Libraries are repointed and reloaded.
7. **Save the .blend** to make the relink permanent.

**Relative Paths** stores the new paths as `//`-relative to the current .blend
instead of absolute (requires the file to be saved).

## Features

- Dry-run preview plan before anything is touched
- Filename-based matching (case-insensitive), so renamed folders are fine as long as the filenames match
- Source-folder filter to protect unrelated libraries
- Per-library include checkboxes + enable/disable-all buttons
- Detail box showing current → new path for the selected entry
- Confirmation popup (library reload is not undoable), per-library error reporting

## Layout

```
LibraryRelink/
├── README.md
├── install_to_blender.ps1     # dev deploy to newest Blender (restart required)
├── source/
│   ├── __init__.py            # bl_info + register wiring only
│   ├── blender_manifest.toml
│   ├── core/                  # bpy-free planning logic (relink.py)
│   ├── blender/               # properties / operators / panels
│   └── tests/                 # pytest over core/ — runs without Blender
└── distribution/              # installable zip (+ archive/)
```

## Development

```
cd LibraryRelink
python -m pytest source/tests -q     # core logic tests, no Blender needed
./install_to_blender.ps1             # deploy to newest installed Blender
```

## Changelog

### v1.0.0 (2026-07-16)
- Initial release (WMH architecture: bpy-free core + blender UI split)
- Preview plan (Relink / Missing / Filtered / Unchanged) with per-library include toggles
- Source-folder filter, relative-path option, reload with error reporting
