# Compositor Render Sets - Implementation Patterns

**Reference Document**
**Version:** 1.0
**Date:** 2025-01-17

---

## Overview

This document captures key implementation patterns discovered while building the Compositor Render Sets addon. These patterns are valuable for any addon dealing with rendering, node manipulation, or state management.

---

## Critical Patterns

### 1. LayerCollection vs Collection for Visibility

**Problem**: Setting `Collection.hide_viewport` doesn't update the eye icon in outliner

**Solution**: Use `LayerCollection.hide_viewport`

```python
def find_layer_collection(layer_collection, collection):
    """Recursively find a LayerCollection for a given Collection"""
    if layer_collection.collection == collection:
        return layer_collection
    for child in layer_collection.children:
        result = find_layer_collection(child, collection)
        if result:
            return result
    return None

# Usage:
view_layer = context.view_layer
layer_coll = find_layer_collection(view_layer.layer_collection, collection)
layer_coll.hide_viewport = False  # This controls the eye icon!
```

**Key Points:**
- `Collection.hide_viewport` - Global visibility (rarely what you want)
- `LayerCollection.hide_viewport` - Per-view-layer visibility (outliner eye icon)
- Always update both `VIEW_3D` and `OUTLINER` areas after changes

---

### 2. Modal Operator with Async Rendering

**Problem**: No way to detect when `bpy.ops.render.render()` completes

**Solution**: Use render handlers with a modal operator

```python
class RenderOperator(Operator):
    _render_complete = False

    def render_complete_handler(self, scene, depsgraph=None):
        """Called when render finishes"""
        self._render_complete = True

    def install_handlers(self):
        bpy.app.handlers.render_complete.append(self.render_complete_handler)
        bpy.app.handlers.render_cancel.append(self.render_complete_handler)

    def remove_handlers(self):
        bpy.app.handlers.render_complete.remove(self.render_complete_handler)
        bpy.app.handlers.render_cancel.remove(self.render_complete_handler)

    def modal(self, context, event):
        if event.type == 'TIMER':
            if self._render_complete:
                # Render done, process next item
                self._render_complete = False
                self.render_next()
        return {'RUNNING_MODAL'}

    def execute(self, context):
        self.install_handlers()
        self._timer = context.window_manager.event_timer_add(0.5, window=context.window)
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cleanup(self, context):
        self.remove_handlers()
        context.window_manager.event_timer_remove(self._timer)
```

**Key Points:**
- Use timer (0.5s interval) to check completion flag
- Install handlers in `execute()`, remove in `cleanup()`
- Handle both `render_complete` and `render_cancel`
- Always call `cleanup()` in both `modal()` finish and `cancel()`

---

### 3. State Restoration Pattern

**Problem**: Sequential operations accumulate state changes (e.g., `XXX_Beauty` → `SetA_Beauty` → `SetA_SetB_Beauty`)

**Solution**: Restore to original state BEFORE each operation

```python
# Cache once at start
original_state = cache_node_state(node)

# For each operation
for render_set in render_sets:
    # 1. Restore to original first
    restore_node_state(node, original_state)

    # 2. Configure from clean slate
    configure_node_for_set(node, render_set, prefix)

    # 3. Perform operation
    render()

# Final restoration
restore_node_state(node, original_state)
```

**Wrong Approach:**
```python
# DON'T DO THIS - state accumulates
for render_set in render_sets:
    configure_node_for_set(node, render_set, prefix)  # No restore!
    render()
restore_node_state(node, original_state)
```

**Key Points:**
- Cache original state once at the beginning
- Restore before EACH modification (not just at the end)
- This ensures each operation starts from a known clean state
- Final restoration is still needed for user-facing cleanup

---

### 4. File Output Node Manipulation

**Pattern**: Safely modify File Output node settings

```python
def cache_node_state(node):
    """Cache original state"""
    state = {
        'base_path': node.base_path,
        'file_slots': []
    }
    for i, slot in enumerate(node.file_slots):
        state['file_slots'].append({
            'path': slot.path,
            'index': i
        })
    return state

def restore_node_state(node, state):
    """Restore cached state"""
    node.base_path = state['base_path']
    for slot_data in state['file_slots']:
        idx = slot_data['index']
        if idx < len(node.file_slots):
            node.file_slots[idx].path = slot_data['path']

def configure_node_for_set(node, render_set, prefix):
    """Configure for specific render set"""
    # Set output directory
    node.base_path = bpy.path.abspath(render_set.output_path)

    # Replace prefix in slot names
    for slot in node.file_slots:
        if slot.path.startswith(prefix):
            remainder = slot.path[len(prefix):]
            slot.path = render_set.name + remainder

    # Force update
    bpy.context.scene.node_tree.update_tag()
```

**Key Points:**
- Cache by index, not by name (slots may be renamed)
- Always call `node_tree.update_tag()` after changes
- Ensure paths end with separator for directory handling
- Create output directories before rendering

---

### 5. Visibility Sync Patterns

**Collection Visibility Sync:**
```python
def sync_visibility_to_render(context):
    """Sync render visibility to viewport (eye icon)"""
    original_states = {}
    view_layer = context.view_layer

    def sync_recursive(layer_coll):
        collection = layer_coll.collection
        original_states[collection.name] = collection.hide_render
        collection.hide_render = layer_coll.hide_viewport  # Sync from eye icon
        for child in layer_coll.children:
            sync_recursive(child)

    sync_recursive(view_layer.layer_collection)
    return original_states
```

**Modifier Visibility Sync:**
```python
def sync_modifiers_to_viewport(context):
    """Sync modifier render to viewport display"""
    original_states = {}

    for obj in bpy.data.objects:
        if not hasattr(obj, 'modifiers'):
            continue

        obj_mods = {}
        for mod in obj.modifiers:
            obj_mods[mod.name] = mod.show_render
            mod.show_render = mod.show_viewport  # WYSIWYG

        if obj_mods:
            original_states[obj.name] = obj_mods

    return original_states
```

**Key Points:**
- Cache original states before syncing
- Process all objects/collections, not just visible ones
- Return cache for restoration
- Sync FROM viewport TO render (WYSIWYG direction)

---

### 6. Scene Update Pattern

**Problem**: Node/visibility changes don't propagate to render

**Solution**: Force multiple update types

```python
# After modifying nodes
context.scene.node_tree.update_tag()

# After modifying view layer
context.view_layer.update()

# After all changes
context.evaluated_depsgraph_get().update()

# Force UI refresh
for area in context.screen.areas:
    if area.type in {'VIEW_3D', 'OUTLINER'}:
        area.tag_redraw()
```

**Key Points:**
- Different update calls for different systems
- Compositor needs `node_tree.update_tag()`
- View layer needs `view_layer.update()`
- Full scene needs `depsgraph.update()`
- UI needs `area.tag_redraw()`

---

## Common Issues & Solutions

### Issue: Files Overwrite Same Path

**Cause**: Node state not restored between renders

**Fix**: Restore to original state before each render set configuration

### Issue: Eye Icon Doesn't Change

**Cause**: Using `Collection.hide_viewport` instead of `LayerCollection.hide_viewport`

**Fix**: Use `find_layer_collection()` and modify LayerCollection

### Issue: Modal Operator Stuck

**Cause**: Render handler never fires or timer not created

**Fix**: Check handler installation and timer creation in execute()

### Issue: Modifiers Render Differently Than Viewport

**Cause**: `modifier.show_render` doesn't match `modifier.show_viewport`

**Fix**: Implement modifier sync pattern

---

## Testing Patterns

### Test Node Setup
```python
def test_node_setup(context):
    """Verify File Output node configuration"""
    node, error = find_file_output_node(context)
    if not node:
        return error

    # Check prefix matching
    prefix = context.scene.props.settings.name_prefix
    matching = [s.path for s in node.file_slots if s.path.startswith(prefix)]

    if not matching:
        return f"No slots with prefix '{prefix}'"

    return f"Found {len(matching)} matching slots: {matching}"
```

### Debug Logging
```python
# Start of operation
print(f"{'='*60}")
print(f"OPERATION: {operation_name}")
print(f"{'='*60}")

# During operation
print(f"[STEP] Description of step")
print(f"  Detail 1: {value1}")
print(f"  Detail 2: {value2}")

# End of operation
print(f"{'='*60}")
print(f"COMPLETE")
print(f"{'='*60}\n")
```

---

## Performance Considerations

1. **State Caching**: Cache once, restore many times (not vice versa)
2. **Batch Updates**: Group scene updates, don't update per-item
3. **Recursive Traversal**: Cache results if traversing same hierarchy multiple times
4. **Handler Management**: Install once, remove once (not per-operation)
5. **Modifier Sync**: Only sync once at start, not per render set

---

## References

- **CLAUDE.md** - Repository-wide patterns and practices
- **blender-tooling-specialist-agent.md** - Complete agent specification
- Blender API: `docs.blender.org/api/current/`

---

**Last Updated:** 2025-01-17
**Addon Version:** 1.0.0
