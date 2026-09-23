# Add Bounds To Name — changelog

User docs: [README](../README.md).

## v1.1.3 (2025-12-11)
- **NEW:** Omit Decimal Zero option for smart float formatting
- **IMPROVED:** Float mode can now produce clean output like `1x1.5x1` instead of `1.0x1.5x1.0`
- **IMPROVED:** UI shows "Omit Decimal Zero" checkbox when Float numeric style is selected
- **IMPROVED:** Preset system now includes `omit_decimal_zero` setting
- Default: Enabled (removes unnecessary .0 from whole numbers)

## v1.1.2 (2025-12-10)
- **IMPROVED:** Simplified axis swizzle UI labels ("X", "Y", "Z" instead of "1st", "2nd", "3rd")
- **IMPROVED:** Renamed "Axis Order" section to "Axis Swizzle" for clarity

## v1.1.1 (2025-12-10)
- **NEW:** 2D pattern detection (detects both `1x2` and `1x2x3` formats)
- **IMPROVED:** Detection order (3D patterns first, then 2D)
- **IMPROVED:** Supports upgrading 2D names to 3D (e.g., `wall_400x200` → `wall_400x200x10`)

## v1.1.0 (2025-12-10)
- **NEW:** Independent axis swizzling (3 separate dropdowns)
- **NEW:** Replace previous bounds feature with auto-detection
- **NEW:** Erase Blender numbering (.001, .002, etc.)
- **NEW:** Auto-detect common separators for bounds detection
- **NEW:** Manual separator specification option
- **NEW:** "Smart Renaming" section in UI
- **IMPROVED:** Regex-based bounds detection handles more cases
- **IMPROVED:** Debug output shows complete rename flow
- **FIX:** Correctly handles Blender numbering after bounds (.001 at end)

## v1.0.0 (2025-12-10)
- Initial release
- Full specification implementation
- Preset system
- Batch processing support
- Object/Mesh bounds options
