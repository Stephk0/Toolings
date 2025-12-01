# Edge Constraint Mode - Bug Fix Summary

## Error Fixed
**TypeError: VIEW3D_OT_edge_constraint_mode.__init__() takes 1 positional argument but 2 were given**

## Root Cause
The Blender operator class had **class-level mutable attributes** defined with default values. This is an anti-pattern in Python and causes issues with how Blender's operator system instantiates operators.

### Problematic Code (Original):
```python
class VIEW3D_OT_edge_constraint_mode(Operator):
    bl_idname = "view3d.edge_constraint_mode"
    bl_label = "Edge Constraint Mode"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    
    # ❌ PROBLEM: Class-level mutable attributes
    _initial_mouse = None
    _constraint_data = None
    _bm = None
    _obj = None
    _pivot = None
    _original_positions = {}  # ❌ Mutable default!
    _transform_mode = 'NONE'
    _draw_handler = None
    _sensitivity = 0.01
    _accumulated_delta = 0.0
```

## Solution
Move all instance variable initialization from class-level to the `invoke()` method where they belong.

### Fixed Code (v1.2.0):
```python
class VIEW3D_OT_edge_constraint_mode(Operator):
    bl_idname = "view3d.edge_constraint_mode"
    bl_label = "Edge Constraint Mode"
    bl_options = {'REGISTER', 'UNDO', 'BLOCKING'}
    
    # ✓ No class-level mutable attributes
    
    @classmethod
    def poll(cls, context):
        return (context.mode == 'EDIT_MESH' and 
                context.active_object and 
                context.active_object.type == 'MESH')
    
    def invoke(self, context, event):
        global draw_handler
        
        # ✓ Initialize instance variables in invoke()
        self._initial_mouse = None
        self._constraint_data = None
        self._bm = None
        self._obj = None
        self._pivot = None
        self._original_positions = {}
        self._transform_mode = 'NONE'
        self._draw_handler = None
        self._sensitivity = 0.01
        self._accumulated_delta = 0.0
        
        # ... rest of invoke method
```

## Changes Made
1. ✓ Removed all class-level mutable attribute definitions
2. ✓ Added instance variable initialization at the start of `invoke()` method
3. ✓ Updated version from 1.1.0 to 1.2.0
4. ✓ Maintained all original functionality

## Why This Matters
In Blender operators:
- Instance variables should be initialized in `invoke()` or `execute()`
- Class-level attributes are shared across all instances
- Mutable defaults (like `{}` or `[]`) can cause unexpected behavior
- Blender's operator system requires specific instantiation patterns

## Files
- **Original (buggy):** `edge_constraint_mode.py`
- **Fixed (working):** `edge_constraint_mode_fixed.py`

## Testing
The fixed version has been successfully tested and registered in Blender without errors.

---
**Maintainer:** Stephan Viranyi + Claude  
**Date:** 2025-10-24  
**Fixed Version:** 1.2.0
