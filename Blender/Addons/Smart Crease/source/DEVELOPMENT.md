# Smart Crease Add-on for Blender — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

### Data Attributes
- **Vertex Crease**: Custom float layer (`crease_vert`)
  - Created automatically if doesn't exist
  - Persistent across sessions
- **Edge Crease**: Built-in edge crease attribute
  - Native Blender attribute
  - Range: 0.0 to 1.0
- Both fully compatible with Subdivision Surface modifier

### Performance
- Uses BMesh for efficient per-element access
- Batch operations on all selected elements simultaneously
- Smooth viewport updates during modal operation
- Single undo step per operation
- No performance impact when not active
