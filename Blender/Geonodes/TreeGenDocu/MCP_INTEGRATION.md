# Blender MCP Integration Guide

**Purpose:** Connect Claude AI to Blender for automated tree generation and iteration

**Status:** Future Enhancement (Not yet implemented in this project)

**Date:** 2025-12-03

---

## What is MCP (Model Context Protocol)?

MCP is a protocol that allows AI assistants like Claude to interact with external tools and applications. For Blender, this would enable:

- Automated script execution
- Parameter adjustment via conversation
- Iteration on designs through natural language
- Screenshot analysis and feedback loops
- Batch tree generation with variations

---

## Current Status

### ✅ What We Have Now:

1. **Manual Python Scripts:**
   - `setup_tree_generator.py` - Main setup
   - `quick_test_scene.py` - Test scene creation
   - Run these manually in Blender's Text Editor

2. **Geometry Nodes System:**
   - Fully procedural node tree
   - Organized into functional frames
   - Adjustable parameters

3. **Workflow:**
   ```
   User → Run Python Script in Blender → Adjust Parameters → Iterate
   ```

### 🔄 What MCP Would Enable:

1. **AI-Assisted Workflow:**
   ```
   User: "Create a willow tree"
   Claude via MCP:
     → Launches Blender
     → Runs setup script
     → Adjusts parameters for willow characteristics
     → Takes screenshot
     → Shows result to user
     → Iterates based on feedback
   ```

2. **Natural Language Control:**
   - "Make the branches droopier"
   - "Add more iterations for density"
   - "Try a different random seed"
   - "Make it look more like an oak"

3. **Batch Processing:**
   - Generate 100 tree variations
   - Create forest with species variety
   - Automatic render and save

---

## How to Set Up Blender MCP (Future)

### Prerequisites

- Blender 4.5+ installed
- Python 3.11+
- MCP-compatible AI client (Claude Desktop, etc.)
- Blender MCP server (to be developed/configured)

### Architecture

```
┌─────────────────┐
│   Claude AI     │
│   (via MCP)     │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│  MCP Server     │
│  (Python/Node)  │
└────────┬────────┘
         │ RPC/API Calls
         ▼
┌─────────────────┐
│     Blender     │
│  Python bpy API │
└─────────────────┘
```

### Option 1: Blender Python RPC Server

Create a simple RPC server within Blender:

```python
# blender_mcp_server.py (concept - not yet implemented)

import bpy
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

class BlenderMCPHandler(BaseHTTPRequestHandler):
    """Handle MCP requests to Blender"""

    def do_POST(self):
        """Execute Blender commands from MCP"""

        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        command = json.loads(post_data)

        try:
            if command['action'] == 'run_script':
                exec(command['script'])
                result = {'status': 'success'}

            elif command['action'] == 'set_parameter':
                # Adjust tree generator parameter
                obj = bpy.data.objects.get(command['object_name'])
                if obj and obj.modifiers:
                    modifier = obj.modifiers.get('ProceduralTreeGenerator')
                    if modifier:
                        modifier.node_group.inputs[command['param']].default_value = command['value']
                        result = {'status': 'success'}

            elif command['action'] == 'screenshot':
                # Render viewport screenshot
                bpy.ops.render.opengl(write_still=True)
                result = {'status': 'success', 'path': bpy.context.scene.render.filepath}

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())

        except Exception as e:
            self.send_error(500, str(e))

# Start server in background thread
def start_mcp_server(port=8765):
    server = HTTPServer(('localhost', port), BlenderMCPHandler)
    print(f"Blender MCP Server running on port {port}")
    server.serve_forever()

# Run in Blender
if __name__ == "__main__":
    import threading
    thread = threading.Thread(target=start_mcp_server, daemon=True)
    thread.start()
```

### Option 2: File-Based Communication

Simpler approach using file watching:

```python
# blender_file_watcher.py (concept)

import bpy
import json
import time
from pathlib import Path

COMMAND_FILE = Path("D:/Stephko_Tooling/mcp_commands.json")
RESULT_FILE = Path("D:/Stephko_Tooling/mcp_results.json")

def process_command_file():
    """Check for and process MCP commands"""

    if not COMMAND_FILE.exists():
        return

    try:
        with open(COMMAND_FILE, 'r') as f:
            command = json.load(f)

        # Execute command
        if command['action'] == 'setup_tree':
            exec(open(command['script_path']).read())
            result = {'status': 'success', 'message': 'Tree generator setup complete'}

        elif command['action'] == 'adjust_param':
            # Adjust parameter
            obj = bpy.data.objects.get(command['object'])
            # ... parameter adjustment logic
            result = {'status': 'success'}

        # Write result
        with open(RESULT_FILE, 'w') as f:
            json.dump(result, f)

        # Remove command file
        COMMAND_FILE.unlink()

    except Exception as e:
        result = {'status': 'error', 'message': str(e)}
        with open(RESULT_FILE, 'w') as f:
            json.dump(result, f)

# Register timer to check for commands
bpy.app.timers.register(process_command_file, first_interval=1.0, persistent=True)
```

### Option 3: Existing MCP Server for Blender

Check if a Blender MCP server already exists:

- Search GitHub for "blender mcp server"
- Look for community implementations
- Check Anthropic MCP documentation

---

## Proposed MCP Functions for Tree Generator

### Core Functions

```json
{
  "name": "blender_tree_create",
  "description": "Create a new procedural tree",
  "parameters": {
    "trunk_shape": "string (straight|bent|twisted|forked)",
    "species": "string (oak|willow|pine|custom)",
    "iterations": "integer (0-10)",
    "base_thickness": "float (0.01-2.0)",
    "branch_length": "float (0.1-10.0)",
    "random_seed": "integer (0-999999)"
  }
}

{
  "name": "blender_tree_adjust",
  "description": "Modify existing tree parameters",
  "parameters": {
    "object_name": "string",
    "parameter": "string (iterations|thickness|length|seed|spread)",
    "value": "number"
  }
}

{
  "name": "blender_tree_render",
  "description": "Render tree and return screenshot",
  "parameters": {
    "object_name": "string",
    "camera_angle": "string (front|side|top|perspective)",
    "output_path": "string"
  }
}

{
  "name": "blender_tree_export",
  "description": "Export tree as file",
  "parameters": {
    "object_name": "string",
    "format": "string (fbx|obj|gltf)",
    "output_path": "string"
  }
}

{
  "name": "blender_tree_batch_generate",
  "description": "Generate multiple tree variations",
  "parameters": {
    "count": "integer",
    "base_params": "object",
    "variation_range": "object"
  }
}
```

### Example Conversation Flow

```
User: "Create a willow tree with drooping branches"

Claude (via MCP):
  1. blender_tree_create(
       species="willow",
       iterations=3,
       branch_length=2.5,
       base_thickness=0.3
     )
  2. blender_tree_adjust(
       parameter="angular_spread",
       value=0.6  # More droop
     )
  3. blender_tree_render(
       camera_angle="perspective"
     )
  4. Returns screenshot to user

User: "Make it less dense"

Claude:
  1. blender_tree_adjust(
       parameter="iterations",
       value=2  # Reduce from 3 to 2
     )
  2. blender_tree_render()
  3. Returns updated screenshot
```

---

## Benefits of MCP Integration

### For Users:
- Natural language tree creation
- Rapid iteration without learning Blender UI
- Batch generation for forests/variations
- AI-guided parameter optimization

### For Developers:
- Automated testing of node setups
- Parameter space exploration
- Regression testing
- Documentation screenshot generation

### For Production:
- Speed up asset creation pipeline
- Consistency across multiple trees
- Version control via conversation history
- Easy collaboration with non-technical stakeholders

---

## Challenges & Considerations

### Technical:
- Blender doesn't have native HTTP server
- Background mode limitations
- Thread safety in Blender Python
- Performance with large node trees

### Security:
- Arbitrary code execution risks
- Need authentication for remote access
- Sandboxing of MCP commands
- File system access controls

### User Experience:
- Blender must remain responsive
- Clear error messaging
- Parameter validation
- Undo/redo support

---

## Immediate Alternative: Semi-Automated Workflow

While full MCP isn't set up yet, you can create a hybrid workflow:

### 1. Template Scripts
Create pre-configured scripts for common tree types:

```python
# oak_tree.py
exec(open("setup_tree_generator.py").read())
modifier = bpy.context.object.modifiers['ProceduralTreeGenerator']
modifier.node_group.inputs['Iterations'].default_value = 3
modifier.node_group.inputs['Branch Length'].default_value = 1.2
modifier.node_group.inputs['Base Thickness'].default_value = 0.4
modifier.node_group.inputs['Angular Spread'].default_value = 0.35
```

### 2. Command Line Blender
Run Blender headless with scripts:

```bash
blender --background --python setup_tree_generator.py --python oak_tree.py -- --render-output ./output.png
```

### 3. Batch File Processing
Create a batch processor:

```python
# batch_trees.py
trees = [
    {'name': 'oak', 'seed': 1, 'iterations': 3},
    {'name': 'pine', 'seed': 2, 'iterations': 4},
    {'name': 'willow', 'seed': 3, 'iterations': 2},
]

for tree in trees:
    # Setup and configure
    # Render
    # Export
```

---

## Next Steps for MCP Integration

### Phase 1: Research
- [ ] Investigate existing Blender MCP servers
- [ ] Review Anthropic MCP SDK documentation
- [ ] Test simple RPC server in Blender
- [ ] Prototype file-based communication

### Phase 2: Core Implementation
- [ ] Create basic MCP server for Blender
- [ ] Implement core tree functions
- [ ] Add parameter validation
- [ ] Test with Claude Desktop

### Phase 3: Advanced Features
- [ ] Screenshot capture and analysis
- [ ] Batch processing
- [ ] Parameter optimization loops
- [ ] Integration with tree specification

### Phase 4: Polish
- [ ] Error handling
- [ ] Documentation
- [ ] Example workflows
- [ ] Performance optimization

---

## Resources

### Blender Python API:
- [bpy documentation](https://docs.blender.org/api/current/)
- [Geometry Nodes Python](https://docs.blender.org/api/current/bpy.types.GeometryNode.html)

### MCP Resources:
- [Anthropic MCP Documentation](https://modelcontextprotocol.io/)
- [MCP Servers Repository](https://github.com/modelcontextprotocol/servers)
- [Building MCP Servers](https://modelcontextprotocol.io/docs/tools/building)

### Community:
- Blender Artists Forum
- Blender StackExchange
- Anthropic Discord

---

## Conclusion

While MCP integration is not yet implemented, the groundwork is in place:

✅ **We Have:**
- Fully procedural system
- Python API access
- Organized node structure
- Clear parameter interface

🔄 **We Need:**
- MCP server implementation
- Communication protocol
- Function definitions
- Testing infrastructure

The current manual scripts work great and can be enhanced with MCP when ready!

---

*Last Updated: 2025-12-03*
*Status: Conceptual - Awaiting MCP Server Implementation*
*Author: Stephan Viranyi (Stephko)*
