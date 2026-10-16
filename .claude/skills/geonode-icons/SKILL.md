---
name: geonode-icons
description: Create, rebuild or fix the Asset-Browser thumbnails / icons / previews of the ST3E geonode modifiers, helper groups (GNG_/SHG_) and shader groups (SH_). Use when the user asks for a thumbnail, icon or preview for a modifier ("make a thumbnail for GN_X", "the icon for X looks wrong", "which modifiers have no icon", "re-tint / re-render the icons"), or after a new geonode is finished and needs its icon. Runs headless — no live Blender, no earlier session needed.
---

# Geonode icons — request to shipped preview

Pipeline: `Blender/Geonodes/_icons/`. Contract `ICONS.md`, findings `GOTCHAS.md` — read
both before writing or changing a recipe (they are the context this skill does not repeat).
Everything goes through one plain-Python CLI that launches Blender 5.0 headless itself:

```
cd Blender/Geonodes/_icons
python icon.py coverage              # what has no icon
python icon.py probe GN_X            # real interface: sockets, menu ITEM names, first-input check, hints
python icon.py build GN_X            # STAGE A: renders out/GN_X.png, never touches a .blend
python icon.py ship  GN_X            # STAGE B: embed -> cold verify (all) -> README gallery + tables
```

`$ST3E_BLENDER` overrides the Blender path. Several keys may be passed at once.

## Flow

1. **Find the target.** `coverage` if the user named none. A recipe key is the icon id;
   `group=` names the datablock when they differ (see ICONS.md "Recipe keys are icon ids").
2. **Probe — always, even for an existing recipe.** Sockets get renamed mid-session in the
   source `.blend`s. Never write socket names from memory or from ICONS.md examples.
   - First input not Geometry → it is not a modifier: `emblem=True` on `ST3E/Group`.
   - Menu sockets take the **item name** string shown by the probe.
   - Probe hints map onto the five prep classes in ICONS.md; they are hints, check them.
3. **Write/adjust the recipe** in `recipes.py`. Pick the tightest true `expect`. Edit by a
   unique anchor, never by string index (two recipes were lost that way); the recipe count
   must not change except by the ones you add.
4. **Build**, then **Read the PNG** (`LOOK AT:` lines). Green only proves something changed.
   Judge: is the effect readable at 256 px, centred, right catalog tint, label correct?
   Iterate on prep / params / helpers / `ghost_wire` / `cage` until it reads. Helper
   placement is visual — sweep and look, do not calculate.
5. **Show the user the PNG and get a yes before `ship`** — ship writes the library `.blend`s.
6. **Ship.** It refuses keys without a PNG. Then commit on a branch: the `.blend`(s),
   `_icons/out/`, `recipes.py`, `Blender/Geonodes/README.md`. Check `git status` first —
   other work may have the same `.blend`s or README dirty; commit only your hunks.

## Rules

- `build` is read-only against the library; `ship` is the only step that saves, and only
  ID previews. Do not add other writes to either.
- A failed effect check deletes the PNG on purpose. Fix the recipe; never bypass the gate.
- Do not change the look (camera, lights, frames, label) without reading GOTCHAS.md, and
  rebuild every icon after such a change (`python icon.py build` with all keys, or
  `build_icons.py` with no args).
- After a frame edit: `python icon.py frames`, then rebuild.
- A new finding that cost time goes into `GOTCHAS.md`, not memory.
