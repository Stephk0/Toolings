# Add Bounds To Name — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

## Technical Details

### Order of Operations (CRITICAL)

The addon processes names in a specific order to handle the common case where Blender numbering appears AFTER bounds:

**Example:** `cube_1x1x1.001` (not `cube.001_1x1x1`)

**Processing Steps:**
1. **Strip Blender Numbering (.001, .002, etc.)**
   - Must happen FIRST before bounds detection
   - Pattern: `\.\d{3,}$` at end of name
2. **Detect and Remove Previous Bounds**
   - Now that `.001` is gone, regex can match `_1x1x1` pattern
   - Extracts base name without dimensions
3. **Add New Bounds**
   - Applies current dimensions to clean base name

**Why This Order Matters:**

❌ **WRONG ORDER (detect bounds first):**
```
Input:  cube_1x1x1.001
Step 1: Try to detect bounds → FAILS (ends with .001, not a number)
Step 2: Strip .001 → cube_1x1x1
Step 3: Add new bounds → cube_1x1x1_2x2x2  (DOUBLED UP!)
```

✅ **CORRECT ORDER (strip numbering first):**
```
Input:  cube_1x1x1.001
Step 1: Strip .001 → cube_1x1x1
Step 2: Detect bounds → cube (removed _1x1x1)
Step 3: Add new bounds → cube_2x2x2  (CLEAN!)
```

**Real-World Scenario:**
```
1. Create object with bounds:   cube → cube_1x1x1
2. Duplicate object (Shift+D):  cube_1x1x1 → cube_1x1x1.001
3. Scale 2x and rename:         cube_1x1x1.001 → cube_2x2x2 ✅
```

### Bounds Calculation

**Object Bounds:**
- Uses `object.dimensions` property
- Includes all modifiers (array, mirror, etc.)
- Includes child objects
- Includes armature deformations

**Mesh Bounds:**
- Calculates from mesh vertex positions
- Applies object scale only
- Ignores modifiers
- Local space calculation

### Blender Numbering Detection

Uses regex pattern: `\.\d{3,}$`

**Matches:**
- `.001`, `.002`, ..., `.999` (3 digits)
- `.1000`, `.1001`, ..., `.9999` (4 digits)
- `.10000` and beyond (5+ digits)

**Does NOT match:**
- `.1`, `.12` (less than 3 digits - not Blender numbering)
- `.obj`, `.fbx` (file extensions)

### Previous Bounds Detection

**Auto-Detect Mode:**
Tries combinations of separators to find patterns in this order:

**Detection Priority (to avoid false matches):**
1. **3D Suffix** - Try `name_1x2x3` patterns FIRST
2. **2D Suffix** - Try `name_1x2` patterns if 3D not found
3. **3D Prefix** - Try `1x2x3_name` patterns
4. **2D Prefix** - Try `1x2_name` patterns

**Why 3D First?**
- Prevents matching first 2 numbers of a 3D pattern
- Example: `cube_100x200x300` should match as 3D, not 2D

**Suffix Patterns:**
- **3D:** `name[sep]num[dim]num[dim]num[unit]`
  - Example: `cube_100x200x300cm`
- **2D:** `name[sep]num[dim]num[unit]`
  - Example: `floor_500x500mm`

**Prefix Patterns:**
- **3D:** `[unit]num[dim]num[dim]num[sep]name`
  - Example: `100x200x300_cube`
- **2D:** `[unit]num[dim]num[sep]name`
  - Example: `500x500_floor`

**Separator Priority:**
1. Name: `_`, `-`, ` `, `.`
2. Dimension: `x`, `X`, `-`, `*`, `by`

**Examples Detected:**
- ✅ `cube_1x2x3` (3D suffix)
- ✅ `wall_400x200` (2D suffix)
- ✅ `1x2x3_cube` (3D prefix)
- ✅ `500x500_floor` (2D prefix)
- ✅ `trim_10x100mm` (2D with unit)
- ✅ `box_1-2-3` (alternate separator)

## Performance

- **Single Object:** Instant (<1ms)
- **Batch (100 objects):** ~50ms
- **Preset Save/Load:** <10ms
- **Regex Detection:** <1ms per object

No performance impact on viewport or rendering.

## Sources

Research on Blender's naming system:
- [Blender Manual - Naming](https://docs.blender.org/manual/en/latest/animation/armatures/bones/editing/naming.html)
- [Blender Studio - Naming Conventions](https://studio.blender.org/tools/naming-conventions/introduction)
- [Datablock Names - Blender Studio](https://studio.blender.org/tools/naming-conventions/datablock-names)

---

*Part of ST3E — Stephko's 3D Extensions*
