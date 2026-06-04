import socket
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

HOST = 'localhost'
PORT = 9876

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print(f"[OK] Connected to Blender at {HOST}:{PORT}\n")

    # Adjust tree parameters for a nice natural tree
    adjust_params = {
        "type": "execute_code",
        "params": {
            "code": """import bpy

# Get the tree object
obj = bpy.data.objects.get("TreeTrunk")
if not obj:
    print("Error: TreeTrunk object not found")
else:
    # Get the tree generator modifier
    modifier = obj.modifiers.get("ProceduralTreeGenerator")
    if not modifier:
        print("Error: ProceduralTreeGenerator modifier not found")
    else:
        node_group = modifier.node_group

        # Set parameters for a nice tree
        node_group.inputs['Iterations'].default_value = 3
        node_group.inputs['Branch Length'].default_value = 1.5
        node_group.inputs['Angular Spread'].default_value = 0.35
        node_group.inputs['Random Seed'].default_value = 42
        node_group.inputs['Base Thickness'].default_value = 0.15

        print("Tree parameters updated:")
        print("  - Iterations: 3")
        print("  - Branch Length: 1.5")
        print("  - Angular Spread: 0.35")
        print("  - Random Seed: 42")
        print("  - Base Thickness: 0.15")
        print("\\nTree should now have branches!")
"""
        }
    }

    message = json.dumps(adjust_params) + "\n"
    client.sendall(message.encode('utf-8'))
    response = client.recv(4096).decode('utf-8')
    result = json.loads(response)

    if result['status'] == 'success':
        print("[OK] Parameters adjusted successfully!")
        if result['result'].get('result'):
            print("\n" + result['result']['result'])
    else:
        print(f"[ERROR] {result.get('message', 'Unknown error')}")

    client.close()
    print("\n[OK] Done! Check Blender viewport to see your tree!")

except Exception as e:
    print(f"[ERROR] {str(e)}")
