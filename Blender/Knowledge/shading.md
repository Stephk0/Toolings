# Shading

Shader node work in `Blender/Shading/`: Unity URP ports and EEVEE cavity/curvature.

> Migrated verbatim from Claude auto-memory on 2026-09-22. Dates and version numbers are from when each note was written — trust the code when they disagree.

- [Unity URP shader ports — conversion table](#project_unity_shader_ports)
- [Vector Transform CAMERA space is +Z into the screen](#feedback_blender_camera_space_z_flip)
- [Cavity and curvature sources in EEVEE](#feedback_eevee_cavity_curvature_sources)

<a id="project_unity_shader_ports"></a>

## Unity URP shader ports — conversion table

*Blender/Shading/ holds Blender re-creations of Unity URP shaders; ash_char_base_SSS is the reference port*

`D:\Stephko_Tooling\Toolings\Blender\Shading\` is the folder for Blender material networks ported from other engines (created 2026-08-03). First entry: `ash_char_base_SSS.blend` + `README.md`, a port of the Unity URP/Amplify shader at `D:\Work_DistrictGames\Project Main\unity\Assets\ProjectAres\Assets\Shader\ash_char_base_SSS.shader`.

**Scope widened 2026-08-14:** the folder also holds shader node groups that port *Blender's own viewport-only features* into a render engine — `SH_Cavity.blend` (Solid-viewport Cavity overlay in EEVEE) is the first, with a `_build/` build+tidy+verify script trio mirroring the `Geonodes/_build/` pattern. See [Shading](shading.md#feedback_eevee_cavity_curvature_sources).

**Why:** Unity shaders for Project Ares get previewed/authored in Blender; the port needs to be behaviourally faithful, not just "looks similar".

**How to apply — porting an Amplify/URP shader:**
- Amplify emits every pass with the same body. Only the `Forward` pass matters; `GBuffer` duplicates it, everything else reuses `Alpha`. Grep for `float3 Color = ` to confirm before reading 3000 lines.
- `UniversalMaterialType = "Unlit"` + `SHADERPASS_UNLIT` means it is NOT lit — output through an **Emission** node, not Principled.
- HLSL `smoothstep(e0,e1,x)` → **Map Range** with `interpolation_type='SMOOTHSTEP'` (exact).
- HLSL colour dodge `dest / max(1-src, 1e-5)` → **Mix Color** `blend_type='DODGE'`, Factor 1, `clamp_result=True`, A=dest, B=src (exact — Blender computes `A/(1-fac*B)` clamped).
- `saturate(sign(dot(normalOS, viewDirOS)))` front-face test → `1 - ` Geometry **Backfacing**.
- Unity Y-up vs Blender Z-up: hardcoded `(0,1,0)` world-up constants become `(0,0,1)`.
- View-space normals need a Z flip — see [Shading](shading.md#feedback_blender_camera_space_z_flip).
- Two URP things have no Blender node equivalent and must become manual inputs: `_MainLightPosition.xyz` (shader nodes can't query a light) and the additional-lights loop (`GetAdditionalLightsCount`). Expose them, keep the surrounding maths faithful, and say so in the README.
- Build headlessly per [Headless Blender and automation](headless-and-automation.md#feedback_blender_version_and_headless); creating a new .blend that way never touches the user's live session.

Related: [Geonode layout](geonodes/layout.md#feedback_gn_node_layout_spacing) (frame + label the network the same way as geonodes).

<a id="feedback_blender_camera_space_z_flip"></a>

## Vector Transform CAMERA space is +Z into the screen

*Blender's Vector Transform CAMERA space has +Z INTO the screen — opposite to Unity/GL view space; flip Z when porting view-space (matcap) shader maths*

Blender's **Vector Transform** node with `convert_to='CAMERA'` produces a vector whose **+Z points into the screen**. A normal facing the viewer reads `z = -1`, not `+1`.

Unity's view space (`UNITY_MATRIX_V` / `UNITY_MATRIX_IT_MV`) follows the OpenGL convention — camera looks down **-Z**, so a normal facing the viewer reads `z = +1`. X (right) and Y (up) agree between the two.

**Why:** Blender's own docs say "camera looks down -Z", which is true of the camera *object's* local axes but NOT of the Vector Transform node's Camera space. Reasoning from the docs gives the wrong answer; measuring gives the right one. Cost a wrong-then-right-then-wrong flip while porting `ash_char_base_SSS` (see [Shading](shading.md#project_unity_shader_ports)).

**How to apply:**
- When porting any view-space / matcap shader maths from Unity (or HLSL generally) to Blender, insert a `Vector Math > Multiply` by `(1, 1, -1)` right after the World→Camera transform.
- Symptom if missing: only vectors with a Z component are wrong, so a default spec vector like `(1,0,0)` still looks fine — the bug hides until an artist tilts the highlight.
- **Verify by measuring, not reasoning:** wire the transformed vector to an Emission, set `scene.view_settings.view_transform = 'Standard'` (no tonemap), render small, then read `img.pixels` at known points (sphere centre / silhouette). Negative components clip to 0 in 8-bit output, which is itself the signal.

Related: [Headless Blender and automation](headless-and-automation.md#reference_blender_mcp), [Headless Blender and automation](headless-and-automation.md#feedback_blender_version_and_headless).

<a id="feedback_eevee_cavity_curvature_sources"></a>

## Cavity and curvature sources in EEVEE

*Two ways to get viewport-cavity/curvature into an EEVEE shader — AO probe pair, and the Bump node as Blender's ONLY screen-space derivative; plus the workbench formulas, the Workbench flat-white ground truth, and the two render settings that fake shader bugs in numeric probes*

Built two shader node groups reproducing the Solid-viewport Cavity overlay in
EEVEE (2026-08-14): `Blender/Shading/SH_Cavity.blend` (AO-based, World + Screen)
and `SH_ScreenCavity.blend` (Screen Space only, Bump-derivative, no ray tracing).
Both share the maths below; only the curvature SOURCE differs. What cost time:

**Curvature sources in EEVEE, measured not assumed:**
- **Geometry ▸ Pointiness is useless in EEVEE** — returns a flat 0.5 (Cycles-only).
  Ruled out by rendering it and finding max == 0.5 over the whole surface.
- **Ambient Occlusion node works in EEVEE 5.0 out of the box** (no `use_raytracing`
  needed) and `Distance` genuinely bites. `inside=False` → **concave/valley** mask
  (`1 - AO`), `inside=True` → **convex/ridge** mask. Verified by eye on Suzanne:
  concave lights the eye-socket creases, convex lights brow/ears/nose. This pair
  is the practical substitute for the depth/normal buffer.
  Caveat: the inward probe reads ~2.7× stronger than the outward one, so
  `convex − concave` is **biased toward ridge** — valley sliders need more range.
- **The Bump node is Blender's ONLY screen-space derivative**, and it works well
  enough to ship (`SH_ScreenCavity.blend`, 2026-08-14). Recipe:
  `dot(Bump(h, invert=off) − Bump(h, invert=on), axis)` ≈ `-2*D * dH(axis)/det`.
  Four Bump nodes (2 per screen axis, h = view normal .x and .y) reconstruct
  workbench's `normal_diff` exactly. **An earlier note here called this harsh and
  rejected it — that was a broken probe, not the technique** (see the negative-
  emission trap below). Verified: flat plane → exactly 0, convex sphere → uniform
  ridge, r = 0.73 vs Workbench.
  - It differentiates normal-derived heights fine (not only texco chains).
  - **The `det` division cancels the pixel footprint**: amplitude is world-
    normalised and invariant to zoom / camera distance / resolution (measured).
    The *sampling footprint is still one pixel*, so it stays viewport-crisp —
    only the strength needs an explicit gain input.
  - **Do NOT feed the gain into Bump's `Distance`** — a large Distance tilts the
    normal far enough that `normalize()` saturates and the reading stops being
    proportional (0.05→0.10 gave 1.69×, not 2×). Fix the probe step small
    (0.01) and multiply afterwards; the control is then exactly linear.
  - Bump flips `dist` on **backfaces** — correct with `1 - 2*Backfacing`, else the
    ridge/valley sign inverts on any open mesh seen from behind.
  - Differentiating a piecewise-linear normal field gives piecewise-CONSTANT
    curvature → visible faceting on coarse meshes. Inherent, not a bug.

**The exact workbench maths** (source moved: `workbench_{cavity,curvature,composite}.bsl.hh`,
no longer `*_lib.glsl`):
```
color.rgb *= clamp((1 - cavity) * (1 + edges) * (1 + curvature), 0, 4)
soft_clamp(c, ctrl) = c < 0.5/ctrl ? c*(1 - c*ctrl) : 0.25/ctrl
curvature = d < 0 ? -2*soft_clamp(-d, valley_ctrl) : 2*soft_clamp(d, ridge_ctrl)
ridge_ctrl = 0.5/max(ridge²,1e-4)   valley_ctrl = 0.7/max(valley²,1e-4)
```
Porting a **branch** to nodes: both sides always evaluate, so clamp each side's
input to its own sign (`max(d,0)` / `max(-d,0)`) — otherwise the idle branch
reaches ~1e4 (`c*(1-c*ctrl)` with ctrl=7000 at slider 0) and float32 cancellation
in the arithmetic select eats the result.

**Ground truth for anything cavity-shaped:** Workbench with
`shading.light='FLAT'`, `color_type='SINGLE'`, `single_color=(1,1,1)` and
`cavity_type='SCREEN'` outputs *precisely* `clamp(1 + curvature, 0, 4)`. Render it
and your own Factor to EXR and correlate pixel for pixel — that is how the default
gain got calibrated (swept the gain, picked the lowest RMSE: mean 1.1903 vs
Blender's 1.1901). Intersect the two alpha masks by pixel INDEX; EEVEE and
Workbench do not rasterise the silhouette identically, so the surface-pixel counts
differ (2938 vs 3190) and a naive zip misaligns everything.

**EEVEE clamps NEGATIVE emission to black.** Probing a signed value by wiring it
into an Emission silently reads back all-zeros, which looks exactly like "the node
does nothing" — this is what made the Bump route look dead for two probe rounds.
Add a constant in-shader and subtract it on read-back.

**The other measurement trap:** EEVEE's default 1.5 px
reconstruction filter mixes the transparent background into pixels that still
report **alpha 1.0**, so a *constant* emission of 1.0 reads back as **0.985** near
the silhouette. Every tolerance test picks up a phantom ~1.5% error that looks
exactly like a shader bug and is byte-identical across rebuilds (that
reproducibility is the tell — real float noise moves). Probe numerically with
`scene.render.filter_size = 0.01`; restore 1.5 for beauty renders. Blender's EXR
is also premultiplied, so divide RGB by alpha when masking on alpha.

**Reusable:** `LLMGeonodePipeline/tidy_layout.py` + `layout_audit.py` are
tree-type agnostic (they only key on NodeFrame / NodeGroupInput / NodeGroupOutput /
NodeReroute) — `tidy_and_route(ng)` lays out a **ShaderNodeTree** unchanged and
R1–R11 all pass. `node.inputs["Factor_Float"]` FAILS: `inputs[key]` looks up by
display NAME, not identifier, and Mix has three sockets named "A" — use an
enabled-identifier-first resolver.

New asset catalog **`ST3E/Shading` = `3c7d5e91-2b64-4f8a-9d13-6a0e5f2c8b47`**
(added to `Blender/blender_assets.cats.txt`). `is_modifier`/`is_tool` are
GeometryNodeTree traits only — a ShaderNodeTree has neither.

Related: [Shading](shading.md#project_unity_shader_ports), [Geonode layout](geonodes/layout.md#feedback_gn_node_layout_spacing),
[Headless Blender and automation](headless-and-automation.md#feedback_blender_version_and_headless), [ST3E geonode modifier — build recipe, roster, publish checklist](geonodes/asset-checklist.md).
