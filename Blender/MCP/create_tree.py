import socket
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Connect to Blender's socket server
HOST = 'localhost'
PORT = 9876

# Read the tree generator setup script
setup_script_path = r"D:\Stephko_Tooling\Toolings\Blender\Geonodes\setup_tree_generator.py"

try:
    with open(setup_script_path, 'r', encoding='utf-8') as f:
        tree_setup_code = f.read()
    print("[OK] Loaded tree generator setup script")
except Exception as e:
    print(f"[ERROR] Could not load setup script: {e}")
    sys.exit(1)

try:
    # Create socket connection
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print(f"[OK] Connected to Blender at {HOST}:{PORT}")

    # Step 1: Create trunk curve
    print("\n[1/2] Creating trunk curve...")
    create_trunk = {
        "type": "execute_code",
        "params": {
            "code": """import bpy

# Delete default objects
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()

# Create vertical trunk curve
bpy.ops.curve.primitive_bezier_curve_add(location=(0, 0, 0))
trunk = bpy.context.active_object
trunk.name = "TreeTrunk"

# Scale vertically
trunk.scale.z = 5
bpy.ops.object.transform_apply(scale=True)

print("Created trunk curve: " + trunk.name)
"""
        }
    }

    message = json.dumps(create_trunk) + "\n"
    client.sendall(message.encode('utf-8'))
    response = client.recv(4096).decode('utf-8')
    print(f"Response: {json.loads(response)['status']}")

    # Step 2: Run tree generator setup
    print("\n[2/2] Setting up tree generator...")
    setup_tree = {
        "type": "execute_code",
        "params": {
            "code": tree_setup_code
        }
    }

    message = json.dumps(setup_tree) + "\n"
    client.sendall(message.encode('utf-8'))
    response = client.recv(8192).decode('utf-8')
    result = json.loads(response)

    if result['status'] == 'success':
        print("[OK] Tree generator setup complete!")
        print("\nNext steps:")
        print("1. Switch to Geometry Nodes workspace in Blender")
        print("2. Open Modifier Properties (wrench icon)")
        print("3. Adjust parameters:")
        print("   - Iterations: 2-3")
        print("   - Branch Length: 1.0-2.0")
        print("   - Angular Spread: 0.3-0.5")
        print("4. Change Random Seed for variations")
    else:
        print(f"[ERROR] Setup failed: {result.get('message', 'Unknown error')}")

    # Close connection
    client.close()
    print("\n[OK] Done!")

except ConnectionRefusedError:
    print(f"[ERROR] Cannot connect to Blender at {HOST}:{PORT}")
    print("Make sure:")
    print("1. Blender is running")
    print("2. Blender MCP addon is installed and enabled")
    print("3. You clicked 'Connect to Claude' in Blender")
except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
