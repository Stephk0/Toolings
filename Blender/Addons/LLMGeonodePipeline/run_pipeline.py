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


def _audit_gate(trees):
    """gate(trees) -> (ok, {tree name: report}).

    EVERY tree the tool owns is audited, not just the outermost one: a helper group is a
    graph the user opens and reads, so it is held to the same bar. ok is False if a
    BLOCKING rule FAILs in ANY of them -- one unreadable helper blocks the save."""
    reports = {ng.name: layout_audit.audit(ng) for ng in trees}
    ok = all(r[rule]["status"] != "FAIL"
             for r in reports.values() for rule in BLOCKING_RULES)
    return ok, reports


def run(fname, save=True):
    """Apply the default tidy pipeline to <fname>.blend, verify both goals, save
    if both pass. Returns the process_file stats dict (with the audit report)."""
    res = tidy_layout.process_file(fname, save=save, gate=_audit_gate)

    print(f"\n########## LLM Geonode Pipeline: {fname} ##########")
    print(f"  trees tidied: {', '.join(res['trees'])}")
    for nm, s in [(fname, res["stats"])] + sorted(res.get("sub_stats", {}).items()):
        print(f"  tidy_and_route [{nm}]: local-GIs={s['local_gis']} "
              f"node-entries={s.get('node_entries', 0)} hv={s['hv']} fan={s['fan']} "
              f"around={s['around']}")
    reports = res["gate_info"] or {}
    for nm, report in reports.items():
        layout_audit.print_report(report)
    advisories = sorted({f"{r} [{nm}]" for nm, report in reports.items()
                         for r in ADVISORY_RULES
                         if report.get(r, {}).get("status") == "FAIL"})
    print(f"  GOAL 1 geometry unchanged      : {'PASS' if res['geom_ok'] else 'FAIL'}")
    print(f"  GOAL 2 structural rules (R1,R2), all {len(reports)} tree(s): "
          f"{'PASS' if res['gate_ok'] else 'FAIL'}")
    if advisories:
        print(f"  advisories not met (non-blocking): {', '.join(advisories)}")
    both_ok = res["geom_ok"] and res["gate_ok"]
    if res["saved"]:
        verdict = "SAVED (both goals met)"
    elif not res["geom_ok"]:
        verdict = "NOT SAVED -- geometry changed!"
    elif not res["gate_ok"]:
        verdict = "NOT SAVED -- structural rule (R1/R2) failed in one of the trees"
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
