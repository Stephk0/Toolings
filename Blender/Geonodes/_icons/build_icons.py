"""Stage A - render one 256x256 framed icon per recipe.

Runs inside Blender, one launch for the whole batch:

    blender --background --factory-startup --python build_icons.py -- [GROUP ...]

Writes out/<GROUP>.png plus out/manifest.json. An icon whose modifier produced
no measurable effect is reported as FAILED and no PNG is written - a silently
unmodified Suzanne is worse than a missing icon.
"""
import bpy
import json
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import stage        # noqa: E402
import recipes      # noqa: E402

GEONODES = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
FRAMES = os.path.join(HERE, "frames")


def frame_for(catalog):
    path = os.path.join(FRAMES, "frame_%s.png" % (catalog or "neutral").lower())
    return path if os.path.exists(path) else os.path.join(FRAMES, "frame_neutral.png")


def build_one(group, rec):
    stage.wipe()
    cam = stage.build_scene()

    base = stage.BASES[rec.get("base", "suzanne")]
    subject = base(**rec.get("base_args", {}))
    subject.name = "Subject"
    stage.run_preps(subject, rec.get("prep", []))

    # Helper objects feed Object/Collection sockets (cutters, sources, instance
    # prototypes). They are inputs, not subjects: hidden from the render and
    # left out of the camera fit. A param value of "@name" resolves to one.
    helpers = {}
    for spec in rec.get("helpers", []):
        if spec.get("kind") == "collection":
            coll = bpy.data.collections.new("Helper_" + spec["name"])
            for i, item in enumerate(spec.get("items", [])):
                obj = stage.BASES[item["base"]](**item.get("base_args", {}))
                for c in list(obj.users_collection):
                    c.objects.unlink(obj)
                coll.objects.link(obj)
                # At the ORIGIN, not parked off-screen: an instancer applies
                # the prototype's own transform, so parking them out of shot
                # smears the instanced grid across that offset.
                obj.location = item.get("location", (0.0, 0.0, 0.0))
                obj.hide_render = True
            helpers[spec["name"]] = coll
            continue
        if spec.get("kind") == "material":
            helpers[spec["name"]] = stage.clay_material(
                "Helper_" + spec["name"],
                tuple(spec.get("colour", stage.PALETTE[0])))
            continue
        helper = stage.BASES[spec["base"]](**spec.get("base_args", {}))
        helper.name = "Helper_" + spec["name"]
        helper.location = spec.get("location", (0.0, 0.0, 0.0))
        scale = spec.get("scale", 1.0)
        helper.scale = ((scale,) * 3 if isinstance(scale, (int, float))
                        else tuple(scale))
        helper.hide_render = True
        helpers[spec["name"]] = helper

    mat_spec = rec.get("material", "clay")
    if rec.get("hollow"):
        subject.data.materials.clear()
        subject.data.materials.append(stage.hollow_clay_material())
    elif rec.get("two_sided"):
        subject.data.materials.clear()
        subject.data.materials.append(stage.two_sided_clay_material())
    elif mat_spec == "clay" and not subject.data.materials:
        subject.data.materials.append(stage.clay_material())
    elif isinstance(mat_spec, (list, tuple)) and mat_spec[0] == "split":
        subject.data.materials.clear()
        subject.data.materials.append(
            stage.transfer_split_material(mat_spec[1],
                                          *(mat_spec[2:] or (0.45,))))
    elif isinstance(mat_spec, (list, tuple)) and mat_spec[0] == "attribute":
        channel = mat_spec[2] if len(mat_spec) > 2 else "color"
        shade = mat_spec[3] if len(mat_spec) > 3 else "emission"
        subject.data.materials.clear()
        subject.data.materials.append(
            stage.attribute_material(mat_spec[1], channel, shade))

    # An emblem recipe photographs no modifier at all: the group cannot be
    # attached as one. Skip straight to framing.
    if rec.get("emblem"):
        if not subject.data.materials:
            subject.data.materials.append(stage.clay_material())
        scale, centre = stage.frame_camera(cam, [subject])
        stage.refit_lights(scale, centre)
        stage.recentre_camera(cam, scale, OUT)
        stage.build_label(cam, rec.get("short", group.replace("GNG_", "")),
                          scale)
        stage.setup_compositor(frame_for(rec.get("catalog")))
        path = os.path.join(OUT, group + ".png")
        stage.render_to(path)
        return {"group": group, "catalog": rec.get("catalog"),
                "file": rec.get("file", recipes.source_file(group)),
                "expect": "emblem", "effect_ok": True,
                "effect": "emblem (group has no modifier form)",
                "cage": False, "ghost_wire": False,
                "ortho_scale": round(scale, 4), "png": path}

    before = stage.signature(subject)
    base_bounds = stage.world_points(subject)

    # keep_base draws the prepared mesh a second time, unmodified. Needed when
    # the modifier consumes its input: a scatter outputs instances only, so
    # without the host surface the icon is dots floating in space.
    if rec.get("keep_base"):
        host = subject.copy()
        host.data = subject.data.copy()
        host.name = "Host"
        stage.link_scene(host)
        host.data.materials.clear()
        host.data.materials.append(stage.clay_material())

    blend = os.path.join(GEONODES, rec.get("file", recipes.source_file(group)))
    ng = stage.append_group(blend, group)
    md = subject.modifiers.new(group, 'NODES')
    md.node_group = ng
    params = {k: (helpers[v[1:]] if isinstance(v, str) and v.startswith("@")
                  else v)
              for k, v in rec.get("params", {}).items()}
    stage.set_params(md, ng, params)
    subject.update_tag()
    bpy.context.view_layer.update()

    after = stage.signature(subject)
    ok, msg = stage.check_effect(subject, before, after, rec["expect"])

    # The cage is built AFTER the effect check: it adds geometry, which would
    # break an expect="deform" vertex-count assertion.
    extras = []
    if ok and rec.get("ghost_wire"):
        wire = stage.build_ghost_wire(subject, mode=rec["ghost_wire"])
        if wire:
            extras.append(wire)

    cage = None
    if ok and rec.get("cage"):
        cage = stage.build_cage(
            subject, md, ng,
            stage.TINTS.get(rec.get("catalog"), stage.TINTS["Neutral"]),
            rec.get("cage_resolution", stage.CAGE_RESOLUTION))

    # wire_only hides the solid result and keeps just its wireframe, for
    # generators whose output would otherwise occlude what it was built from.
    if rec.get("wire_only"):
        subject.hide_render = True

    # The cage is deliberately NOT part of the fit: it extends well past the
    # mesh, and including it would render Suzanne smaller on every caged icon
    # than on every other one. MARGIN leaves it room to bleed toward the edge.
    scale, centre = stage.frame_camera(
        cam, [subject], extra_points=base_bounds,
        margin=stage.MARGIN * (stage.CAGE_MARGIN if cage else 1.0))
    stage.refit_lights(scale, centre)
    if rec.get("hollow"):
        stage.add_interior_light(centre, scale)
    stage.recentre_camera(cam, scale, OUT)
    stage.build_label(cam, rec.get("short", group.replace("GN_", "")),
                      scale)
    stage.setup_compositor(frame_for(rec.get("catalog")))

    path = os.path.join(OUT, group + ".png")
    record = {"group": group, "catalog": rec.get("catalog"),
              "file": os.path.basename(blend), "expect": rec["expect"],
              "effect_ok": ok, "effect": msg, "cage": bool(cage),
              "ghost_wire": bool(extras),
              "ortho_scale": round(scale, 4)}
    if ok:
        stage.render_to(path)
        record["png"] = path
    elif os.path.exists(path):
        # Drop the previous run's image: leaving it behind lets embed_icons
        # bake a stale icon into the .blend and report success.
        os.remove(path)
    return record


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    wanted = argv or sorted(recipes.RECIPES)
    os.makedirs(OUT, exist_ok=True)

    results = []
    for group in wanted:
        rec = recipes.RECIPES.get(group)
        if rec is None:
            results.append({"group": group, "effect_ok": False,
                            "effect": "no recipe"})
            continue
        try:
            results.append(build_one(group, rec))
        except Exception:
            stale = os.path.join(OUT, group + ".png")
            if os.path.exists(stale):
                os.remove(stale)
            results.append({"group": group, "effect_ok": False,
                            "effect": traceback.format_exc(limit=4)})

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf8") as fh:
        json.dump(results, fh, indent=2)

    print("\n=== ICON BUILD ===")
    for r in results:
        flag = "ok  " if r.get("effect_ok") else "FAIL"
        print("%s %-26s %s" % (flag, r["group"], r.get("effect", "").strip()))
    bad = [r["group"] for r in results if not r.get("effect_ok")]
    print("=== %d/%d built ===" % (len(results) - len(bad), len(results)))
    sys.stdout.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    code = main()
    os._exit(code)
