import json
import sys

# MCP request to execute code in Blender
request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "execute_code",
        "arguments": {
            "code": """import bpy
bpy.ops.mesh.primitive_ico_sphere_add(location=(0, 0, 0), radius=1)
bpy.context.active_object.name = "Icosphere"
print("✓ Created icosphere at origin")
"""
        }
    }
}

print(json.dumps(request))
