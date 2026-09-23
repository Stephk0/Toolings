# Center Loops - Blender Addon — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

### How It Works

**Edge Loop Centering:**
- Identifies perpendicular edges connected to each vertex of the selected edge
- Calculates the average position of perpendicular vertices
- Moves edge vertices to the calculated center position
- Handles multiple face types simultaneously (tris, quads, ngons)

**Vertex Centering:**
- Finds all connected vertices through manifold edges
- Calculates weighted or unweighted average of neighbor positions
- Moves vertex to the averaged position
