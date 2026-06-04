# Tooling Folder Structure — Convention

> How every tool in `ClaudeVibe_WIPs/` (and new tools we create) must be organized.
> Established 2026-05-31. Follow this layout for **every** tool, every time.

## Standard layout

Each tool lives in its **own folder** at the root of `ClaudeVibe_WIPs/`, named after the
tool (mixed case with spaces is fine, e.g. `Smart Crease`). Inside:

```
<ToolName>/
├── README.md          # tool overview, version, install, layout note (REQUIRED)
├── source/            # all addon code + ancillary docs (CHANGELOG, LICENSE, plans, icons)
├── distribution/      # the CURRENT installable zip
│   └── archive/       # all older version zips (and legacy formats like .rar)
└── assets/            # screenshots / doc images (only if the tool has any)
```

### Rules
- **README.md** stays at the tool root — never inside `source/`.
- **source/** holds everything needed to build/edit the addon: `__init__.py`, modules,
  `blender_manifest.toml`, plus tool-specific dev scripts and design/install/changelog docs.
- **distribution/** holds exactly **one** zip — the latest version. Every older zip goes
  into `distribution/archive/`. Legacy archive formats (`.rar`) also live in `archive/`.
- **assets/** holds PNG/JPG screenshots and doc images. Omit the folder if there are none.
- Tools with **no published zip yet** keep an empty `distribution/` (with a `.gitkeep`).
  Build a versioned zip on the next change (see the always-zip rule below).

## When building a new zip (release)
1. Bump the version in `source/__init__.py` (`bl_info` / `VERSION`) and
   `source/blender_manifest.toml`.
2. Build the installable zip with addon files at the **archive root** (drag-and-drop ready).
3. Move the previous `distribution/*.zip` into `distribution/archive/`.
4. Drop the new zip into `distribution/`.
5. Update `README.md`'s version line.

## When creating a brand-new tool
Create `<ToolName>/` with the four subfolders above, write a `README.md` from the template
(title, version, Blender min, category, description, install, folder layout), put code in
`source/`, and the first zip in `distribution/`.

## Notes / gotchas
- `MassExporter/` source is internally **v13.6.0** (the folder was formerly named
  `MassExporter_v12.4`; the old `MassExporter` WIP folder was removed). Don't be fooled by
  the old folder name — trust `source/__init__.py` `VERSION`.
- `__pycache__`, `tmpclaude-*`, and scratch `.py` probes are junk — never commit them.
- `__alqe_test_exports/` and the repo-level `docs/` are NOT tools and stay at the root.
