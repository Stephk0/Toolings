"""Dump a node group's real interface before writing its icon recipe.

    blender --background --factory-startup --python probe.py -- GN_X [GN_Y ...]
    blender --background --factory-startup --python probe.py -- GN_X --file GN_Other.blend

Read-only. Finds the .blend holding each group (recipe file, then
`<group>.blend`, then a sweep of Blender/Geonodes and Blender/Shading), appends
a copy and prints what a recipe needs:

  - asset catalog, is_modifier, whether a recipe / PNG / embedded preview exists
  - the FIRST input's type - a group whose first input is not Geometry cannot
    be a modifier at all (GOTCHAS: "Not every asset-marked group is a modifier")
  - every input socket by panel: type, default, range, identifier, and names
    that are not unique (bind those as "Name#2" or by identifier)
  - every Menu socket's ITEM NAMES, followed into nested groups
  - outputs, nested groups, and hints for the prep class

Never write a recipe from memory or from ICONS.md's socket names - run this.
"""
import bpy
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import recipes      # noqa: E402
from coverage import CATALOGS   # noqa: E402

GEONODES = os.path.dirname(HERE)
SHADING = os.path.join(os.path.dirname(GEONODES), "Shading")
OUT = os.path.join(HERE, "out")


def candidates(group):
    """.blend paths to try for a group, most likely first."""
    keys = [k for k in recipes.RECIPES if recipes.group_of(k) == group]
    first = []
    for k in keys:
        first += [os.path.normpath(os.path.join(GEONODES, f))
                  for f in recipes.files_of(k)]
    first.append(os.path.join(GEONODES, recipes.source_file(group)))
    sweep = (sorted(glob.glob(os.path.join(GEONODES, "*.blend")))
             + sorted(glob.glob(os.path.join(SHADING, "*.blend"))))
    seen, out = set(), []
    for p in first + sweep:
        p = os.path.normpath(p)
        if p not in seen and os.path.exists(p):
            seen.add(p)
            out.append(p)
    return out


def find_files(group, forced=None):
    if forced:
        p = forced if os.path.isabs(forced) else os.path.join(GEONODES, forced)
        return [os.path.normpath(p)]
    hits = []
    for p in candidates(group):
        with bpy.data.libraries.load(p) as (src, _dst):
            if group in src.node_groups:
                hits.append(p)
    return hits


def purge():
    for ng in list(bpy.data.node_groups):
        try:
            bpy.data.node_groups.remove(ng)
        except Exception:
            pass


def load(path, group):
    """Append the group; return the datablock the load returns, never a by-name lookup."""
    purge()
    with bpy.data.libraries.load(path, link=False) as (_src, dst):
        dst.node_groups = [group]
    return dst.node_groups[0]


def _fmt(v):
    if isinstance(v, float):
        return "%g" % v
    if hasattr(v, "__len__") and not isinstance(v, str):
        return "(" + ", ".join(_fmt(x) for x in v) + ")"
    return repr(v)


def _follow(ng, out_socket_id, depth=0):
    """Menu item names reached from a Group Input output, through reroutes and nested groups."""
    if depth > 8:
        return None
    for node in ng.nodes:
        if node.bl_idname != "NodeGroupInput":
            continue
        for sock in node.outputs:
            if sock.identifier != out_socket_id:
                continue
            for link in sock.links:
                got = _from_target(link.to_node, link.to_socket, depth)
                if got:
                    return got
    return None


def _from_target(node, sock, depth):
    if node.bl_idname == "NodeReroute":
        for link in node.outputs[0].links:
            got = _from_target(link.to_node, link.to_socket, depth)
            if got:
                return got
        return None
    if node.bl_idname == "GeometryNodeMenuSwitch" and sock.identifier == "Menu":
        return [i.name for i in node.enum_items]
    if node.bl_idname == "GeometryNodeGroup" and node.node_tree:
        return _follow(node.node_tree, sock.identifier, depth + 1)
    return None


def nested(ng, acc=None):
    acc = acc if acc is not None else set()
    for node in ng.nodes:
        tree = getattr(node, "node_tree", None)
        if node.bl_idname in ("GeometryNodeGroup", "ShaderNodeGroup") and tree \
                and tree.name not in acc:
            acc.add(tree.name)
            nested(tree, acc)
    return acc


def report(group, path, ng):
    ad = ng.asset_data
    cat = CATALOGS.get(ad.catalog_id, ad.catalog_id) if ad else None
    keys = [k for k in recipes.RECIPES if recipes.group_of(k) == group
            and os.path.basename(path) in [os.path.basename(f) for f in recipes.files_of(k)]]
    key = keys[0] if keys else None
    png = os.path.join(OUT, (key or group) + ".png")
    preview = bool(ng.preview and ng.preview.image_size[0] > 0
                   and ng.preview.is_image_custom)

    print("\n" + "=" * 72)
    print("%s  @ %s" % (group, os.path.relpath(path, os.path.dirname(GEONODES))))
    print("=" * 72)
    print("tree      %s" % ng.bl_idname)
    print("asset     %s   catalog=%s   is_modifier=%s"
          % (ad is not None, cat, getattr(ng, "is_modifier", None)))
    print("recipe    %s   png=%s   embedded preview=%s"
          % (key or "-", os.path.exists(png), preview))

    inputs = [it for it in ng.interface.items_tree
              if it.item_type == 'SOCKET' and it.in_out == 'INPUT']
    outputs = [it for it in ng.interface.items_tree
               if it.item_type == 'SOCKET' and it.in_out == 'OUTPUT']
    if ng.bl_idname == "GeometryNodeTree":
        first = inputs[0].socket_type if inputs else None
        if first != "NodeSocketGeometry":
            print("!! first input is %s, not Geometry - this group cannot work as a "
                  "modifier (emblem=True on ST3E/Group instead)" % first)

    counts = {}
    for it in inputs:
        counts[it.name] = counts.get(it.name, 0) + 1
    seen = {}
    print("\nINPUTS")
    menus, hints = [], set()
    for it in inputs:
        seen[it.name] = seen.get(it.name, 0) + 1
        panel = it.parent.name if it.parent and it.parent.name else ""
        stype = it.socket_type.replace("NodeSocket", "")
        bits = []
        if hasattr(it, "default_value"):
            bits.append("default=" + _fmt(it.default_value))
        if hasattr(it, "min_value") and (abs(it.min_value) < 1e9
                                         or abs(it.max_value) < 1e9):
            bits.append("range=%s..%s" % (_fmt(it.min_value), _fmt(it.max_value)))
        if getattr(it, "default_input", "VALUE") not in ("VALUE", None):
            bits.append("implicit=" + it.default_input)
        if getattr(it, "hide_value", False):
            bits.append("field-only")
        name = it.name if counts[it.name] == 1 else "%s#%d" % (it.name, seen[it.name])
        print("  %-22s %-30s %-11s %-12s %s"
              % (panel[:22], name[:30], stype, it.identifier, "  ".join(bits)))
        if it.socket_type == "NodeSocketMenu":
            menus.append(it)
        if stype in ("Object", "Collection"):
            hints.add("class 3: external %s -> helpers=[...] + \"@name\"" % stype.lower())
        if stype == "Material" or "material" in it.name.lower():
            hints.add("class 2?: material slots + material_index prep")
        if stype == "Bool" and "invert" not in it.name.lower() and (
                getattr(it, "hide_value", False)
                                or "selection" in it.name.lower()
                                or "boundary" in it.name.lower()):
            hints.add("class 4?: per-element field '%s' -> (\"attr\", name) + "
                      "bool_attribute prep" % it.name)
        if it.name == "Show Deformation Preview":
            hints.add("deformer with a preview cage -> cage=True")
        if it.name in recipes.NO_OVERLAY:
            hints.add("has overlay sockets -> **NO_OVERLAY in params")

    if menus:
        print("\nMENU ITEMS (pass the item NAME as the param value)")
        for it in menus:
            items = _follow(ng, it.identifier)
            print("  %-30s %s" % (it.name, items if items else
                                  "?? not reached from the group input - walk the graph"))

    print("\nOUTPUTS")
    for it in outputs:
        print("  %-30s %-11s %s" % (it.name, it.socket_type.replace("NodeSocket", ""),
                                    it.identifier))
        if it.socket_type != "NodeSocketGeometry" and ng.bl_idname == "GeometryNodeTree":
            hints.add("non-geometry output '%s' -> outputs={...} to store it, maybe "
                      "expect=attribute:<name> (class 5)" % it.name)

    sub = sorted(nested(ng))
    if sub:
        print("\nNESTED GROUPS  " + ", ".join(sub))
    if hints:
        print("\nHINTS (check, do not trust)")
        for h in sorted(hints):
            print("  - " + h)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    forced = None
    if "--file" in argv:
        i = argv.index("--file")
        forced = argv[i + 1]
        del argv[i:i + 2]
    if not argv:
        print("usage: probe.py -- GROUP [GROUP ...] [--file X.blend]")
        return 2
    bad = 0
    for group in argv:
        files = find_files(group, forced)
        if not files:
            print("\n!! %s: not found in any .blend under Geonodes/ or Shading/" % group)
            bad += 1
            continue
        if len(files) > 1:
            print("\nnote: %s exists in %d files: %s"
                  % (group, len(files), [os.path.basename(f) for f in files]))
        for path in files:
            try:
                report(group, path, load(path, group))
            except Exception as exc:
                print("\n!! %s @ %s: %s" % (group, os.path.basename(path), exc))
                bad += 1
    sys.stdout.flush()
    return 1 if bad else 0


if __name__ == "__main__":
    code = main()
    os._exit(code)
