# Flow Element — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Layout (WMH split)

```
source/
├── __init__.py            # bl_info + register/unregister only
├── blender_manifest.toml
├── core/                  # bpy-free
│   ├── vec.py             # tuple vector math
│   ├── topology.py        # lazy adjacency (callbacks), ordered vertex fans, opposite edges,
│   │                      #   line continuation
│   └── flow.py            # arc prediction, line walking, least-squares combine, solve()
├── blender/
│   ├── operators.py       # mesh.st3e_flow_element: BMesh adapters -> core.flow.solve
│   └── ui.py              # Vertex / Edge / Face menus + edit-mode context menu
└── tests/
    ├── pytest.ini         # rootdir = tests/, never imports the bpy addon package
    ├── test_flow.py       # core on synthetic cylinders / spheres / grids
    └── headless/
        └── blender_checks.py  # operator in real Blender, exits 1 on failure
```

## Algorithm

For every moving vertex `v`:

1. **Lines.** Pairs of opposite edges through `v`: topological opposites for an interior
   vertex with even valence (fan order from face corners), otherwise the most opposite pair
   by direction (≥ ~105°). Edge mode excludes the selected edges, leaving the crossing ring.
2. **Anchors.** Each side of a line is walked (topological opposite again, geometric
   fallback) through moving vertices until the first fixed vertex `A1`, plus one more `A2`.
   Lines that never reach fixed geometry are dropped. Anchors are always fixed, so the solve
   is direct: no fairing iteration. An earlier damped-Jacobi version needed ~300 iterations
   for a 6-wide patch, and the count grows with the 4th power of patch size.
3. **Prediction.** Circle through `(A2, A1, B1)` and circle through `(A1, B1, B2)`, each
   evaluated at `v`'s chord parameter `t` between `A1` and `B1`, then averaged
   (circle-average: exact on circles, straight at an S-bend). Tension scales the offset
   from the chord.
4. **Combine.** Each line only constrains `v` across its tangent `u_i` (numeric derivative of
   the predicted curve). Solve `Σ(I − u_i u_iᵀ) d = Σ(I − u_i u_iᵀ) d_i`. A plain average of
   the predicted points cuts inside curved surfaces (1.4 % on a wide cylinder patch).
5. **Passes.** Repeat 2–4 with updated positions (`t` and tangents change, anchors don't).
   On the test patches, 3 passes reach < 1e-5.

A normal-only constraint was tried and removed. It is inexact whenever the damage wasn't
along the normal (6 % on a squashed ring), and keeping `t` already stops sliding.

Benny Sauder's EdgeFlow (`set_flow`) was the reference. It uses a Hermite midpoint per loop
vertex with an empirical tension of 1.8 and iterates.

## Tests

```
cd source/tests && python -m pytest -q
"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" --background --factory-startup --python source/tests/headless/blender_checks.py
```

Both pass on Blender 5.0 and 4.5.

## Performance

Pure Python. On a 130k-vert sphere, face mode moving 1.5k verts takes 0.6 s and 7.5k verts
takes 3.5 s. Every redo-panel tweak re-solves. If it gets slow, the first fix is to cache
the line walks between passes (they are recomputed per vertex today, O(n · patch width)).

## Dev deploy

`install_to_blender.ps1` at the tool root copies `source/` into the highest Blender's
`extensions/user_default/flow_element`. Restart Blender after deploying.
