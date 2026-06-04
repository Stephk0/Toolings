import socket
import json
import sys

# Set UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Connect to Blender's socket server
HOST = 'localhost'
PORT = 9876

try:
    # Create socket connection
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print(f"[OK] Connected to Blender at {HOST}:{PORT}")

    # Command to get scene info
    command = {
        "type": "execute_code",
        "params": {
            "code": """import bpy

print("=== SCENE OBJECTS ===")
for obj in bpy.data.objects:
    print(f"Object: {obj.name} (Type: {obj.type})")
    if obj.modifiers:
        print(f"  Modifiers:")
        for mod in obj.modifiers:
            print(f"    - {mod.name} ({mod.type})")
"""
        }
    }

    # Send command
    message = json.dumps(command) + "\n"
    client.sendall(message.encode('utf-8'))
    print(f"[OK] Sent command to create icosphere")

    # Receive response
    response = client.recv(4096).decode('utf-8')
    print(f"\nResponse from Blender:")
    print(response)

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
