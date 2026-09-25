# Smart Set Orientation — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## How It Works

### Selection Tracking

The addon uses MD5 hashing to track your selection state:
- Generates a unique hash based on selected vertices, edges, and faces
- Detects when you've changed your selection
- Automatically creates new orientations when selection changes
- Toggles between orientations when working with the same selection

### Custom Orientation Management

- Custom orientations are created using Blender's native `transform.create_orientation` operator
- The addon tracks the most recently created custom orientation
- Previous custom orientations remain available in your scene
- Orientations can be overwritten or preserved based on your workflow

### Context Override System

- Uses Blender's context override to ensure operators work correctly
- Finds appropriate 3D Viewport regions automatically
- Handles edge cases where multiple viewports exist

## Technical Details

### Selection Hash Algorithm

```python
# Combines vertex, edge, and face indices into unique hash
selected_verts = tuple(sorted(v.index for v in bm.verts if v.select))
selected_edges = tuple(sorted(e.index for e in bm.edges if e.select))
selected_faces = tuple(sorted(f.index for f in bm.faces if f.select))
selection_str = f"v{selected_verts}_e{selected_edges}_f{selected_faces}"
hash = hashlib.md5(selection_str.encode()).hexdigest()
```

### Context Validation

- Checks for valid 3D Viewport context before execution
- Verifies appropriate region types (WINDOW)
- Handles context override for operator execution
- Falls back gracefully on errors

## Contributing

This addon is part of ST3E — Stephko's 3D Extensions. For issues, suggestions, or contributions:
- Report bugs with detailed steps to reproduce
- Include Blender version and OS information
- Describe expected vs actual behavior
