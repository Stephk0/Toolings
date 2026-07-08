"""run_pipeline.py -- the LLM Geonode Pipeline orchestrator.

Ties the two halves of the suite together so they verify each other:

  1. DEFAULT layout engine: `tidy_layout.tidy_and_route` (deterministic layered
     tidy + orthogonal reroute routing + group-input localization).
  2. VERIFY, both goals, before committing:
       - geometry unchanged (tidy_layout's own safety check), AND
       - readability rules R1-R5 (`layout_audit.audit`).
     The file is saved ONLY if BOTH hold.

This is the default automated path. For interactive / AI-judged layout (custom,
non-layered arrangements), use the GeoNode Layout MCP tools instead
(capture_graph -> apply_layout) and then run `layout_audit` to check the result --
see the `geonode-layout-mcp` skill. Both paths share `layout_audit` as the single
source of truth for "what a good layout is", so they can't drift apart.

Usage
-----
  blender --background --factory-startup --python run_pipeline.py -- GN_NormalTransfer [GN_Bend ...]

  # or in a live session / import:
  import run_pipeline; run_pipeline.run("GN_NormalTransfer")

Swap the default engine, thresholds, or rules by editing `tidy_layout.py` /
`layout_audit.py` in this folder -- the orchestrator just composes them.
Exit code is non-zero (CLI) if any file failed to save.
"""

import bpy, sys, os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import tidy_layout
import layout_audit

# Rule policy lives in layout_audit (single source of truth): BLOCKING rules are
# structural integrity (block the save); ADVISORY rules are readability quality.
BLOCKING_RULES = layout_audit.BLOCKING
ADVISORY_RULES = layout_audit.ADVISORY


def _audit_gate(ng):
    """gate(ng) -> (ok, report). ok is False only if a BLOCKING rule FAILs."""
    report = layout_audit.audit(ng)
    ok = all(report[r]["status"] != "FAIL" for r in BLOCKING_RULES)
    return ok, report


def run(fname, save=True):
    """Apply the default tidy pipeline to <fname>.blend, verify both goals, save
    if both pass. Returns the process_file stats dict (with the audit report)."""
    res = tidy_layout.process_file(fname, save=save, gate=_audit_gate)

    print(f"\n########## LLM Geonode Pipeline: {fname} ##########")
    s = res["stats"]
    print(f"  tidy_and_route: local-GIs={s['local_gis']} node-entries={s.get('node_entries', 0)} "
          f"hv={s['hv']} fan={s['fan']} around={s['around']}")
    if res["gate_info"]:
        layout_audit.print_report(res["gate_info"])
    report = res["gate_info"] or {}
    advisories = [r for r in ADVISORY_RULES if report.get(r, {}).get("status") == "FAIL"]
    print(f"  GOAL 1 geometry unchanged      : {'PASS' if res['geom_ok'] else 'FAIL'}")
    print(f"  GOAL 2 structural rules (R1,R2): {'PASS' if res['gate_ok'] else 'FAIL'}")
    if advisories:
        print(f"  advisories not met (non-blocking): {', '.join(advisories)}")
    both_ok = res["geom_ok"] and res["gate_ok"]
    if res["saved"]:
        verdict = "SAVED (both goals met)"
    elif not res["geom_ok"]:
        verdict = "NOT SAVED -- geometry changed!"
    elif not res["gate_ok"]:
        verdict = "NOT SAVED -- structural rule (R1/R2) failed"
    else:  # both goals met but save was disabled (dry run)
        verdict = "OK (both goals met) -- dry run, not saved"
    print(f"  => {verdict}")
    return res


def _cli():
    names = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not names:
        print("usage: ... run_pipeline.py -- <GN_Name> [GN_Name ...]")
        sys.stdout.flush(); os._exit(2)
    n_fail = 0
    for nm in names:
        res = run(nm, save=True)
        if not res["saved"]:
            n_fail += 1
    print(f"\n{len(names) - n_fail}/{len(names)} saved.")
    sys.stdout.flush()
    os._exit(1 if n_fail else 0)


if __name__ == "__main__":
    _cli()
