# Add Bounds To Name

**Version:** 1.1.3
**Author:** Stephan Viranyi
**Blender Version:** 4.5+
**Category:** Object

## Overview

Automatically rename objects with their bounding box dimensions. Perfect for production pipelines where asset sizes need to be clearly identified in file names.

## Features

- ✅ **Automatic Dimension Detection** - Reads object or mesh bounding boxes
- ✅ **Flexible Unit Conversion** - Output in meters, centimeters, or millimeters
- ✅ **Smart Rounding** - Floor, ceiling, or standard rounding with custom increments
- ✅ **Independent Axis Swizzling** - Choose each dimension separately (X, Y, or Z for each position)
- ✅ **Replace Previous Bounds** - Automatically detect and replace existing bounds in names
- ✅ **Erase Blender Numbering** - Remove .001, .002, etc. suffixes automatically
- ✅ **Auto-Detect Separators** - Smart detection of common naming patterns
- ✅ **Smart Float Formatting** - Omit unnecessary .0 from whole numbers (1.0 → 1, but 1.5 stays 1.5)
- ✅ **Custom Formatting** - Prefix/suffix placement, separators, padding
- ✅ **Batch Processing** - Rename multiple objects at once
- ✅ **Preset System** - Save and load custom configurations
- ✅ **Non-Destructive** - Undo support for all operations

## Installation

### Method 1: Install the Zip (Recommended)
1. Drag `distribution/AddBoundsToName_v1.1.3.zip` into the Blender window, or open
   Blender → Edit → Preferences → Add-ons and click **"Install from Disk..."**
2. Select the zip
3. Enable the checkbox

### Method 2: Manual Folder Installation
1. Copy the `source` folder, renamed to `AddBoundsToName`, into the Blender addons directory:
   - Windows: `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/4.5/scripts/addons/`
   - Linux: `~/.config/blender/4.5/scripts/addons/`
2. Restart Blender or click "Refresh"
3. Enable the addon

## Location

**3D Viewport → Sidebar (N key) → Bounds Name tab**

## Usage

### Basic Workflow

1. Select one or more objects
2. Configure formatting options in sidebar
3. Click **Rename Active Object** or **Rename Selected Objects**
4. Object names update with dimension suffixes

### Example Output

**Original:** `cube`
**After rename:** `cube_1x1x1` (with default settings)

## Settings

### Units & Rounding

**Target Unit**
- `Meters` - Output in meters (1.5m)
- `Centimeters` - Output in centimeters (150cm)
- `Millimeters` - Output in millimeters (1500mm)

**Rounding Mode**
- `None` - Use exact calculated values
- `Round` - Round to nearest increment
- `Floor` - Always round down
- `Ceil` - Always round up

**Rounding Increment**
- Value to round to in target units
- Example: `100` with Floor mode rounds 110cm → 100cm

### Axis Swizzle (NEW in v1.1.0)

**Simple X, Y, Z Swizzle**
- Three dropdowns labeled **X**, **Y**, **Z**
- Choose which axis value goes into each output position
- Each dropdown can select: X, Y, or Z

**Examples:**
- Default `X, Y, Z` → 2×3×5 object outputs: `2x3x5`
- Swizzle `Z, X, Y` → 2×3×5 object outputs: `5x2x3`
- Height first `Z, Y, X` → 2×3×5 object outputs: `5x3x2`

### Formatting

**Format Style**
- `Prefix` - Size before name: `1x1x1_cube`
- `Suffix` - Size after name: `cube_1x1x1`

**Name Separator**
- Character(s) between name and size
- Default: `_`

**Dimension Separator**
- Character(s) between dimension values
- Default: `x`

**Numeric Style**
- `Integer` - Whole numbers only (100)
- `Float` - Decimal values (1.50)

**Decimal Places**
- Number of decimal places in float mode (0-6)

**Omit Decimal Zero** (NEW in v1.1.3)
- Removes unnecessary `.0` from whole numbers when using float mode
- Example: `1.0x1.5x1.0` becomes `1x1.5x1`
- Keeps decimals for fractional values (`1.5` stays `1.5`)
- Default: Enabled

**Digit Padding**
- Minimum digits with zero-padding
- Example: padding=2 outputs `01` instead of `1`

**Show Unit Suffix**
- Append unit abbreviation to size
- Example: `cube_100x100x100cm`

### Smart Renaming (NEW in v1.1.0)

**Replace Previous Bounds**
- Automatically finds and replaces existing dimension information in names
- Works with both prefix and suffix formats
- Prevents accumulation of bounds: `cube_1x1x1_2x2x2_3x3x3` ❌
- Clean replacement: `cube_1x1x1` → `cube_2x2x2` ✅

**Auto-Detect Separators** (Default: ON)
- Automatically detects common naming patterns
- **Name separators:** `_`, `-`, ` ` (space), `.`
- **Dimension separators:** `x`, `X`, `-`, `*`, `by`
- **Detects both 2D and 3D patterns:**
  - **3D patterns** (3 dimensions): `cube_1x2x3`, `wall_400x200x10cm`
  - **2D patterns** (2 dimensions): `floor_500x500`, `trim_10x100mm`
- **Examples detected:**
  - `cube_1x2x3` ✅ (3D suffix)
  - `wall_400x200` ✅ (2D suffix)
  - `cube-100x200x300cm` ✅ (3D with unit)
  - `1x2x3_cube` ✅ (3D prefix)
  - `500x500_floor` ✅ (2D prefix)
  - `cube 1-2-3` ✅ (space separator)
  - `trim_10x100` ✅ (2D for thin objects)

**Manual Separator Specification**
- Disable auto-detect to use custom separators
- **Name Separators:** Comma-separated list (e.g., `_,-,.`)
- **Dimension Separators:** Comma-separated list (e.g., `x,X,-`)

**Erase Blender Numbering** (Default: ON)
- Removes Blender's automatic `.001`, `.002`, `.003` etc. suffixes
- Blender adds these to duplicated objects for uniqueness
- Example: `cube.001_1x1x1` → `cube_1x1x1` ✅
- Pattern matched: `.###` where ### is 3+ digits
- Also removes: `.1000`, `.1001`, etc. (4+ digit suffixes)

**How Blender Numbering Works:**
- Blender requires unique names for all objects
- When duplicating, Blender appends `.001`, `.002`, etc.
- Format is always: `name.###` (dot + 3+ digits)
- This cannot be changed by users (hardcoded behavior)
- Reference: [Blender Naming Documentation](https://docs.blender.org/manual/en/latest/)

### Measurement

**Bounds Source**
- `Object Bounds` - Uses object.dimensions (includes modifiers, children)
- `Mesh Bounds` - Calculates from base mesh data only (no modifiers)

## Use Cases

### Replace Previous Bounds Workflow

**Scenario:** You're iterating on modular building pieces and need to update dimensions

```
Initial:   wall_segment_400x200x10cm
Scale 2x:  wall_segment_400x200x10cm  (still shows old dims)
Rename:    wall_segment_800x400x20cm  (✅ replaced, not appended)
```

**With "Replace Previous Bounds" OFF:**
```
Initial:   wall_segment_400x200x10cm
Rename:    wall_segment_400x200x10cm_800x400x20cm  (❌ doubled up)
```

### 2D vs 3D Pattern Detection

**Scenario:** Working with flat objects or standardized sizes

**2D Patterns (automatically detected):**
```
floor_500x500       → floor_600x600     (square tiles)
wall_400x200        → wall_800x400      (width × height only)
trim_10x100mm       → trim_20x200mm     (thin strips)
plate_250x250       → plate_300x300     (flat objects)
```

**3D Patterns (always 3 dimensions):**
```
cube_1x1x1          → cube_2x2x2        (all dimensions)
box_400x200x100cm   → box_800x400x200cm (full 3D)
```

**Why 2D Detection Matters:**
- Flat objects often only specify 2 dimensions
- Square objects might show `500x500` instead of `500x500x10`
- Architectural elements use width × height convention
- The addon now correctly replaces BOTH 2D and 3D patterns

**Detection Priority:**
1. Tries 3D pattern first (to avoid matching first 2 numbers of `1x2x3`)
2. Falls back to 2D pattern if no 3D match found
3. Always replaces with your current 3D output format

### Erase Blender Numbering Workflow

**Scenario:** You duplicated objects and want clean names

```
Duplicate:      cube.001
Without erase:  cube.001_2x2x2
With erase:     cube_2x2x2     (✅ clean name)
```

### Production Asset Organization

Quickly identify asset dimensions for optimization:
```
tree_large_5x8x5
tree_medium_3x5x3
tree_small_1x2x1
```

### Export Size Validation

Verify objects meet size requirements before export:
```
platform_100x100x10cm
prop_25x50x25cm
```

### Mesh Optimization

Track poly reduction impact on dimensions:
```
rock_highpoly_2.5x1.8x2.1
rock_lowpoly_2.5x1.8x2.1  # Same bounds, different poly count
```

### Modular Building Sets

Organize modular pieces by standardized dimensions:
```
wall_400x200x10cm
floor_400x400x5cm
ceiling_400x200x5cm
```

## Examples

### Example 1: Simple 1m Cube

**Settings:**
- Bounds: 1m × 1m × 1m
- Unit: Meters
- Rounding: None
- Format: Suffix
- Axis Swizzle: X, Y, Z (default)

**Output:** `cube_1x1x1`

### Example 2: 110cm Cube Rounded Down

**Settings:**
- Bounds: 1.1m × 1.1m × 1.1m (110cm)
- Unit: Centimeters
- Rounding: Floor
- Increment: 100

**Output:** `cube_100x100x100`

### Example 3: Custom Axis Swizzle (ZXY)

**Settings:**
- Bounds: X=1m, Y=2m, Z=3m
- Axis Swizzle: Z, X, Y

**Output:** `cube_3x1x2`

### Example 4: Replace Previous Bounds

**Scenario:**
- Object named: `prop_100x200x50cm`
- Rescaled to: 2x size
- Settings: Replace Previous Bounds ON, Auto-Detect ON

**Output:** `prop_200x400x100cm` (old bounds replaced)

### Example 5: Clean Blender Duplicates

**Scenario:**
- Duplicated object: `tree.003`
- Dimensions: 5×8×5 meters
- Settings: Erase Blender Numbering ON

**Output:** `tree_5x8x5` (`.003` removed)

### Example 6: 2D to 3D Conversion

**Scenario:**
- Object named: `floor_500x500` (old 2D naming)
- Actual dimensions: 5×5×0.1 meters
- Settings: Replace Previous Bounds ON, Auto-Detect ON

**Processing:**
1. Detects 2D pattern `_500x500`
2. Removes it → base name: `floor`
3. Adds full 3D bounds → `floor_5x5x0.1`

**Output:** `floor_5x5x0.1` (upgraded from 2D to 3D format)

### Example 7: Smart Float Formatting (NEW in v1.1.3)

**Scenario:**
- Object dimensions: 100cm × 150cm × 100cm
- Settings: Target Unit = Meters, Numeric Style = Float, Omit Decimal Zero = ON

**Processing:**
1. Convert to meters: 1.0 × 1.5 × 1.0
2. Apply smart formatting: Remove `.0` from whole numbers
3. Result: `1 × 1.5 × 1` (clean, readable)

**Output:** `cube_1x1.5x1`

**Comparison:**
- With Omit Decimal Zero OFF: `cube_1.0x1.5x1.0` (verbose)
- With Omit Decimal Zero ON: `cube_1x1.5x1` (clean) ✅

## Tips & Best Practices

### For Production Pipelines

1. **Enable "Replace Previous Bounds"** - Keep names clean when iterating
2. **Enable "Erase Blender Numbering"** - Remove .001 suffixes for export
3. **Create Standard Presets** - Define company-wide naming conventions
4. **Use Auto-Detect** - Handles most common naming patterns automatically

### For Modular Assets

1. **Use Integer Mode** - Cleaner names for standardized sizes
2. **Floor Rounding** - Ensures modular pieces don't exceed grid sizes
3. **Prefix Format** - Sort assets by size in file browsers
4. **Axis Swizzle Z, X, Y** - Height first for architectural assets

### For Optimization

1. **Mesh Bounds** - Track base mesh size without modifier influence
2. **Object Bounds** - Include modifier stack for final output size
3. **Replace Previous Bounds** - Update dimensions as you optimize
4. **Compare Before/After** - Use debug mode to verify changes

### Working with Duplicates

1. **Always enable "Erase Blender Numbering"** for clean export names
2. **Use "Replace Previous Bounds"** to update dimensions on copies
3. **Batch rename** all duplicates at once for consistency

## Debug Mode

Enable **Debug Mode** checkbox to print detailed information to console:

```
[AddBoundsToName] Stripped Blender numbering: 'cube_1x1x1.001' → 'cube_1x1x1'
[AddBoundsToName] Detected and removed previous bounds: '_1x1x1'
[AddBoundsToName] Renamed: 'cube_1x1x1.001' -> 'cube_2x2x2'
[AddBoundsToName] Size label: 2x2x2
```

**Example Debug Output (Complete Flow):**
```
Original name: tree_5x8x5.003
[AddBoundsToName] Stripped Blender numbering: 'tree_5x8x5.003' → 'tree_5x8x5'
[AddBoundsToName] Detected and removed previous bounds: '_5x8x5'
[AddBoundsToName] Size label: 10x16x10
[AddBoundsToName] Renamed: 'tree_5x8x5.003' -> 'tree_10x16x10'
```

Useful for:
- Verifying separator detection
- Troubleshooting regex pattern matching
- Confirming Blender numbering removal
- Seeing the complete rename flow step-by-step
- Checking dimension calculations

## Troubleshooting

### "No active object" Error

**Cause:** No object is selected
**Solution:** Select an object in the viewport

### Dimensions Show as 0x0x0

**Cause:** Object has zero scale or empty mesh
**Solution:** Check object scale and mesh data

### Previous Bounds Not Detected

**Cause:** Using non-standard separators
**Solution:**
1. Enable Debug Mode to see what's being processed
2. Try manual separator specification
3. Check that bounds follow pattern: `num[sep]num[sep]num`

### Blender Numbering Not Removed

**Cause:** Suffix doesn't match `.###` pattern
**Solution:**
- Check if suffix has 3+ digits (`.1` and `.12` are not removed)
- Enable Debug Mode to verify detection

### Preset Not Saving

**Cause:** Invalid preset name or file permissions
**Solution:** Use alphanumeric names, check Blender scripts folder permissions

### Replace Bounds Adds Instead of Replacing

**Cause:** Previous bounds pattern not detected
**Solution:**
- Enable Auto-Detect Separators
- Or manually specify the exact separators used in names
- Verify naming pattern matches: `name_1x2x3` or `1x2x3_name`

## Support

**Issues & Feature Requests:**
https://github.com/Stephk0/Toolings

**Author:**
Stephan Viranyi
stephko@viranyi.de

## License

Personal and commercial use permitted.
Attribution appreciated but not required.

---

---

[Developer notes](source/DEVELOPMENT.md) · [changelog](source/CHANGELOG.md)
