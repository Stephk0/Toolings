import socket
import json
import sys

# Set UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

HOST = 'localhost'
PORT = 9876

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print(f"[OK] Connected to Blender\n")

    # Manual tree generator setup (simplified version)
    setup_code = """import bpy

# Get trunk
trunk = bpy.data.objects.get("TreeTrunk")
if not trunk:
    print("ERROR: TreeTrunk not found!")
else:
    print(f"Found trunk: {trunk.name}")

    # Add Geometry Nodes modifier
    mod = trunk.modifiers.new(name="TreeGenerator", type='NODES')
    print(f"Added modifier: {mod.name}")

    # Create node group
    if mod.node_group is None:
        node_group = bpy.data.node_groups.new('TreeGen_Simple', 'GeometryNodeTree')
        mod.node_group = node_group
        print(f"Created node group: {node_group.name}")
    else:
        node_group = mod.node_group

    # Clear existing nodes
    node_group.nodes.clear()

    # Create basic nodes
    nodes = node_group.nodes
    links = node_group.links

    # Input/Output
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-800, 0)

    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (800, 0)

    # Mesh to Curve
    mesh_to_curve = nodes.new('GeometryNodeMeshToCurve')
    mesh_to_curve.location = (-600, 0)

    # Resample Curve
    resample = nodes.new('GeometryNodeResampleCurve')
    resample.location = (-400, 0)
    resample.inputs['Count'].default_value = 20

    # Curve Circle (for profile)
    curve_circle = nodes.new('GeometryNodeCurvePrimitiveCircle')
    curve_circle.location = (200, -200)
    curve_circle.mode = 'RADIUS'
    curve_circle.inputs['Resolution'].default_value = 8
    curve_circle.inputs['Radius'].default_value = 0.1

    # Curve to Mesh
    curve_to_mesh = nodes.new('GeometryNodeCurveToMesh')
    curve_to_mesh.location = (400, 0)

    # Set Shade Smooth
    set_smooth = nodes.new('GeometryNodeSetShadeSmooth')
    set_smooth.location = (600, 0)

    # Create interface sockets FIRST
    for item in list(node_group.interface.items_tree):
        node_group.interface.remove(item)

    node_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    node_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # Now create links
    links.new(group_input.outputs[0], mesh_to_curve.inputs['Mesh'])
    links.new(mesh_to_curve.outputs['Curve'], resample.inputs['Curve'])
    links.new(resample.outputs['Curve'], curve_to_mesh.inputs['Curve'])
    links.new(curve_circle.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])
    links.new(curve_to_mesh.outputs['Mesh'], set_smooth.inputs['Geometry'])
    links.new(set_smooth.outputs['Geometry'], group_output.inputs[0])

    print("Basic tree generator setup complete!")
    print("You should see a mesh trunk in the viewport.")
"""

    command = {
        "type": "execute_code",
        "params": {
            "code": setup_code
        }
    }

    message = json.dumps(command) + "\n"
    client.sendall(message.encode('utf-8'))
    response = client.recv(8192).decode('utf-8')
    result = json.loads(response)

    if result['status'] == 'success':
        print("[OK] Tree generator fixed!")
        output = result['result'].get('result', '')
        if output:
            print("\nBlender output:")
            print(output)
    else:
        print(f"[ERROR] {result.get('message', 'Unknown error')}")

    client.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
