# Blender/Geonodes — work rules

**For ANY work on a geonode in this folder — creating, tidying, or otherwise
altering — invoke the `geonode-layout-mcp` skill first and follow the criteria
it loads.**

The canonical criteria live with the tooling (deliberately outside the AI
config, so they version with the pipeline):

`Blender/Addons/ClaudeVibe_WIPs/LLMGeonodePipeline/GEONODE_CRITERIA.md`

Enforcement: `layout_audit.py` (R1–R11) + `run_pipeline.py` in the same folder —
saves are gated on geometry-unchanged AND the blocking rules.
