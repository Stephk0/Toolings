# Changelog - Unity Model Import Processor

All notable changes to this project will be documented in this file.

## [1.1.0] - 2026-01-03

### Added
- **ColliderSetupRule** - Automatic collider generation based on mesh naming conventions
- OnPostprocessModel support in ModelImportProcessor for GameObject-level modifications
- Mesh collider support with convex/non-convex options (`_COL` suffix)
- Box collider support with automatic bounds sizing (`_COLCUBE`, `_COLBOX` suffixes)
- Sphere collider support with automatic bounds sizing (`_COLSPHERE`, `_COLSPH` suffixes)
- Capsule collider support with automatic axis detection (`_COLCAPSULE`, `_COLCAP` suffixes)
- Collision mesh visibility controls (hide or remove)
- Case-insensitive suffix matching option
- Comprehensive collider setup documentation and examples
- ColliderSetupRule_TEMPLATE.txt example configuration

### Changed
- Updated README.md with collider setup documentation and workflow examples
- Enhanced ModelImportProcessor to support both preprocessing and postprocessing rules

### Technical Details
- Collider rules execute in OnPostprocessModel after GameObject hierarchy is created
- Recursive transform traversal for collider detection
- Automatic collider sizing based on mesh bounds
- Compatible with Blender, Maya, 3DS Max workflows

## [1.0.0] - 2026-01-03

### Added
- Initial release of Unity Model Import Processor
- **ImportRuleBase** - Base ScriptableObject class for extensible rule system
- **MaterialRemapRule** - Complete material remapping rule implementation
- **ModelImportProcessor** - AssetPostprocessor for automatic rule application
- Path pattern matching system with wildcard and regex support
- Priority-based rule execution system
- Automatic rule caching for performance
- Debug menu tools:
  - Refresh Rule Cache
  - List All Rules
  - Test Rules on Selected Asset
- Comprehensive documentation:
  - README.md with full usage guide
  - QUICK_REFERENCE.md for common tasks
  - Example rule template
  - In-code documentation and tooltips

### Features

#### Material Remapping
- Full Unity ModelImporter material API support
- Material import modes: None, ImportStandard, ImportViaMaterialDescription
- Material location: External, InPrefab
- Material naming: BasedOnTextureName, BasedOnMaterialName, BasedOnModelNameAndMaterialName
- Material search: Local, RecursiveUp, Everywhere
- SearchAndRemapMaterials integration
- Verbose logging option for debugging

#### Path Matching
- Wildcard patterns: `*`, `**`, `?`
- Regex pattern support
- Multiple path patterns per rule
- Case-insensitive matching

#### Rule Management
- ScriptableObject-based rules for reusability
- Priority system (0-100) for rule ordering
- Enable/disable toggle per rule
- Automatic cache invalidation on project changes

### Technical Details
- Unity 2019.4+ compatibility
- Pure C# implementation, no external dependencies
- Editor-only scripts (no runtime overhead)
- Efficient rule caching system
- Exception handling with detailed error messages

## Future Versions

### [1.1.0] - Planned
- Animation import rules
- Mesh import rules (normals, tangents, optimization)
- Batch rule application tool for existing assets
- Rule templates for common workflows

### [1.2.0] - Planned
- LOD generation rules
- Texture import rules
- Conditional logic (file size, polygon count)
- Rule dependency system

### [2.0.0] - Planned
- Visual rule editor window
- Rule sets/profiles
- Import report generation
- Team sync for shared rule configurations

## Version Compatibility

| Version | Unity Version | Status |
|---------|---------------|--------|
| 1.0.0 | 2019.4+ | ✅ Tested |
| 1.0.0 | 2020.3+ | ✅ Compatible |
| 1.0.0 | 2021.3+ | ✅ Compatible |
| 1.0.0 | 2022.3+ | ✅ Compatible |
| 1.0.0 | 2023.x | ✅ Compatible |
| 1.0.0 | 6000.x | ✅ Compatible |

## Breaking Changes

None (initial release)

## Known Issues

None

## Migration Guide

Not applicable (initial release)

---

**Author:** Stephan Viranyi (Stephko)
**Repository:** https://github.com/Stephk0/Toolings
**Contact:** stephko@viranyi.de
