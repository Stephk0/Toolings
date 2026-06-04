# Blender Addon Creation Workflow

## When a Blender addon is requested, ALWAYS create addon in its own folder with ALL files inside:

### Folder Structure (All Files in One Folder)
**Location:** `Blender/Addons/ClaudeVibe_WIPs/AddonName/`

**Files:**
- `__init__.py` - Main addon code (for development)
- `addon_name.py` - Installable single-file version (copy of __init__.py)
- `README.md` - Complete documentation
- `test_addon.py` - Test suite (optional but recommended)

**Naming Convention:**
- Folder: PascalCase (e.g., `AddBoundsToName`, `MassExporter`)
- Installable .py: snake_case (e.g., `add_bounds_to_name.py`, `mass_exporter.py`)

**Purpose:**
- ALL addon files stay together in ONE folder
- `__init__.py` - For folder-based installation (developers)
- `addon_name.py` - For single-file installation (users)
- README and tests included in same location
- Easy to manage, update, and distribute entire addon

## Installation Methods

### Method 1: Install Single .py File (Recommended for Users)
1. Open Blender
2. Edit → Preferences → Add-ons
3. Click "Install..."
4. Select the `.py` file (e.g., `add_bounds_to_name.py`)
5. Enable the addon checkbox

### Method 2: Manual Folder Installation (For Developers)
1. Copy entire folder to Blender addons directory:
   - Windows: `%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\`
   - macOS: `~/Library/Application Support/Blender/4.5/scripts/addons/`
   - Linux: `~/.config/blender/4.5/scripts/addons/`
2. Restart Blender or click "Refresh" in preferences
3. Enable the addon

## File Structure Example

```
Blender/Addons/ClaudeVibe_WIPs/
└── AddBoundsToName/              # All addon files in ONE folder
    ├── __init__.py               # Main code (folder installation)
    ├── add_bounds_to_name.py     # Installable version (file installation)
    ├── README.md                 # Documentation
    └── test_addon.py             # Tests
```

**Important:** The single-file installable `.py` file stays INSIDE the addon folder, not at parent level.

## Key Points

1. **ALWAYS create both versions** when user requests a Blender addon
2. The single .py file is IDENTICAL to the __init__.py content
3. Users typically prefer the single .py file for installation
4. Developers prefer the folder structure for maintenance
5. Update CLAUDE.md to document the new addon

## DO NOT

- Create ZIP files (not the standard workflow)
- Only create folder without single .py file
- Only create single .py file without folder structure
- Use different code in the two versions
- Put the installable .py file at parent level (keep it IN the addon folder)

## Workflow Summary

When creating a Blender addon:
1. Create addon folder (e.g., `AddBoundsToName/`)
2. Create `__init__.py` with full addon code
3. Create `addon_name.py` in SAME folder (copy of __init__.py)
4. Create `README.md` with documentation
5. Create `test_addon.py` with test suite (optional)
6. Update CLAUDE.md with addon information
7. Inform user about installation methods

**Remember:** ALL files stay in the addon's folder - nothing at parent level!
