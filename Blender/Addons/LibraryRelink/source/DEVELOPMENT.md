# Library Relink — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

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
