# Modifier Display Toggle (Edit Mode) — developer notes

Implementation and maintenance notes. User docs: [README](../README.md).

### How It Works

The addon uses a "parity" system to intelligently manage modifier states:

1. **Parity Check**: Compares edit mode display with viewport display
2. **Smart Toggle**: 
   - If parity exists and modifiers are on → Disable all edit mode display
   - If parity doesn't exist → Create parity by syncing to viewport

This approach provides a predictable, two-state toggle that matches common workflow needs.

### Operators

- `mesh.toggle_modifier_display` - Main edit mode display toggle
- `mesh.toggle_on_cage_display` - On cage display toggle

## Development

This addon was developed to streamline the Edit Mode workflow by providing quick access to modifier visibility controls that would otherwise require multiple clicks in the Properties panel.
