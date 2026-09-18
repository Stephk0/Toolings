# Continuation Brief — WMH Architecture Adoption

## Context
Research task that turned into setting a forward-direction architecture standard for the
Toolings suite. We compared our `ClaudeVibe_WIPs` Blender addons against our OWN sister repo
`wmh-dcc-tooling` (github.com/Windmillhill-Games/wmh-dcc-tooling). Key correction the user made:
both repos are OURS (Stephko / Windmill Hill Games) — no license barrier to sharing code/patterns.
WMH is the more architecturally mature repo; we adapt patterns FROM it.

## Progress (all DONE this session)
1. Researched wmh-dcc-tooling via `gh` CLI (README/QUICKSTART/HOWTO/CLAUDE.md + Serena memories).
   11 tools: blender_hapi, houdini_mcp, multi_modifier_driver, snippet_manager(+_api),
   viewport_pie_menu, rig_rebuild, ascii_fbx_import, hex_grid, wmh_vertex_wrangler, greyboxing.
2. Delivered a research briefing identifying high-priority adoptions + cross-pollination roster.
3. Created the canonical artifacts IN THE REPO (these are the source of truth):
   - Serena project memory: `.serena/memories/wmh_architecture_adoption.md`
   - Invocable skill: `.claude/skills/wmh-tool-architecture/SKILL.md`
     (covers BOTH building new tools and refactoring existing monoliths; has folder layout,
      core/blender boundary rule, checklists, install_to_blender.ps1 template, gotchas)
4. Converted the earlier `.claude/projects/.../memory/project_wmh_tooling_adoption.md` from a
   full duplicate into a THIN POINTER to the repo memory+skill (to avoid drift). Updated its
   MEMORY.md index hook too.

## Decisions
- **High-priority principles**: P1 = core/ (bpy-free, pytest) + blender/ (UI) split inside each
  tool's existing `source/`; P2 = adopt snippet_manager + snippet_manager_api wired into the
  Blender MCP workflow (search→execute vetted snippets); P5 = per-tool install_to_blender.ps1
  dev installer (KEEP the release-zip rule, ADD installer for iteration).
- Standard extends `_TOOLING_STRUCTURE.md` (README + source/ + distribution/ + assets/) by
  adding core/ + blender/ + tests/ INSIDE source/.
- Boundary rule: pure computation/parsing/math/naming → core/ (no bpy); anything touching
  bpy/context/depsgraph/operators/panels → blender/; __init__.py stays thin (register only).
- Priority refactor targets: MassExporter (internally v13.6.0, one file), SyncedModifiers,
  Compositor Render Sets. Skip tiny single-operator tools.
- Source of truth = the REPO memory + skill; keep those updated, not the .claude pointer.

## Next Steps
1. **Open question to resolve first** (asked user, not yet answered): the legacy Serena memory
   `.serena/memories/blender_addon_creation_workflow.md` now CONTRADICTS the new standard
   (it says "single .py file, no ZIP"). Decide: update it to point to the new standard, or
   delete it. Both new files already flag it as legacy.
2. Restart Claude Code (or new session) so the `.claude/skills/wmh-tool-architecture` skill loads
   and is invocable as `/wmh-tool-architecture`.
3. Begin adoption order: (1) core/blender split on MassExporter as the pilot refactor — extract
   suffix-grouping/base-name/name-collision/LayerCollection-exclude logic into core/ with pytest;
   (2) deploy snippet_manager(_api); (3) port multi_modifier_driver EDGE_CASES_ANALYSIS into
   SyncedModifiers; (4) viewport_pie_menu launcher for scattered modal tools; (5) installer template.

## Open Questions
- Update vs delete the legacy `blender_addon_creation_workflow` memory? (awaiting user)
- Which tool to pilot the core/blender refactor on — assumed MassExporter, confirm with user.
- Does the user want snippet_manager(_api) physically copied into ClaudeVibe_WIPs, or referenced
  from the wmh-dcc-tooling repo?

## Key references
- Repo memory `mem:wmh_architecture_adoption` (full detail + cross-pollination roster)
- Skill `.claude/skills/wmh-tool-architecture/SKILL.md`
- `_TOOLING_STRUCTURE.md`, legacy `mem:blender_addon_creation_workflow` (to reconcile)
