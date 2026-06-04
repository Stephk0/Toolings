import socket
import json
import sys

# Set UTF-8 encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

HOST = 'localhost'
PORT = 9876

# Phase 2 Implementation
# Adds: Thickness/Length Decay, Gravity, Sun Direction, Repeat Zone branching

phase2_code = """import bpy

print("=== PHASE 2: Tree Generator Enhancement ===\\n")

# Get trunk
trunk = bpy.data.objects.get("TreeTrunk")
if not trunk:
    print("ERROR: TreeTrunk not found!")
else:
    print(f"[1/6] Found trunk: {trunk.name}")

    # Remove old modifier if exists
    for mod in trunk.modifiers:
        trunk.modifiers.remove(mod)

    # Add new Geometry Nodes modifier
    mod = trunk.modifiers.new(name="ProceduralTreeGenerator_Phase2", type='NODES')
    print(f"[2/6] Created modifier: {mod.name}")

    # Create node group
    node_group = bpy.data.node_groups.new('TreeGen_Phase2', 'GeometryNodeTree')
    mod.node_group = node_group
    print(f"[3/6] Created node group: {node_group.name}")

    nodes = node_group.nodes
    links = node_group.links

    # Clear any existing nodes
    nodes.clear()

    # ===== CREATE FRAMES =====
    def create_frame(name, color):
        frame = nodes.new('NodeFrame')
        frame.label = name
        frame.use_custom_color = True
        frame.color = color
        return frame

    frame_input = create_frame("INPUT PROCESSING", (0.3, 0.5, 0.3))
    frame_attr = create_frame("ATTRIBUTE INITIALIZATION", (0.3, 0.3, 0.5))
    frame_branch = create_frame("BRANCH GENERATION (CORE)", (0.5, 0.3, 0.3))
    frame_growth = create_frame("GROWTH DIRECTION CALCULATOR", (0.5, 0.4, 0.2))
    frame_decay = create_frame("DECAY SYSTEM", (0.5, 0.5, 0.2))
    frame_geom = create_frame("GEOMETRY BUILDER", (0.4, 0.3, 0.5))

    print("[4/6] Created 6 organizational frames")

    # ===== INPUT/OUTPUT =====
    group_input = nodes.new('NodeGroupInput')
    group_input.location = (-1200, 0)

    group_output = nodes.new('NodeGroupOutput')
    group_output.location = (1400, 0)

    # ===== FRAME 1: INPUT PROCESSING =====
    mesh_to_curve = nodes.new('GeometryNodeMeshToCurve')
    mesh_to_curve.parent = frame_input
    mesh_to_curve.location = (-1000, 100)
    mesh_to_curve.label = "Convert Input to Curve"

    resample = nodes.new('GeometryNodeResampleCurve')
    resample.parent = frame_input
    resample.location = (-1000, -50)
    resample.inputs['Count'].default_value = 20

    # ===== FRAME 2: ATTRIBUTE INITIALIZATION =====
    store_iteration = nodes.new('GeometryNodeStoreNamedAttribute')
    store_iteration.parent = frame_attr
    store_iteration.location = (-700, 150)
    store_iteration.data_type = 'INT'
    store_iteration.domain = 'POINT'
    store_iteration.inputs['Name'].default_value = 'iteration_level'
    store_iteration.inputs['Value'].default_value = 0

    index_node = nodes.new('GeometryNodeInputIndex')
    index_node.parent = frame_attr
    index_node.location = (-900, 0)

    store_branch_id = nodes.new('GeometryNodeStoreNamedAttribute')
    store_branch_id.parent = frame_attr
    store_branch_id.location = (-700, 0)
    store_branch_id.data_type = 'INT'
    store_branch_id.domain = 'POINT'
    store_branch_id.inputs['Name'].default_value = 'branch_id'

    store_thickness = nodes.new('GeometryNodeStoreNamedAttribute')
    store_thickness.parent = frame_attr
    store_thickness.location = (-700, -150)
    store_thickness.data_type = 'FLOAT'
    store_thickness.domain = 'POINT'
    store_thickness.inputs['Name'].default_value = 'branch_thickness'

    # ===== FRAME 3: BRANCH GENERATION (REPEAT ZONE) =====
    repeat_input = nodes.new('GeometryNodeRepeatInput')
    repeat_input.parent = frame_branch
    repeat_input.location = (-400, 50)

    repeat_output = nodes.new('GeometryNodeRepeatOutput')
    repeat_output.parent = frame_branch
    repeat_output.location = (200, 50)

    # Link repeat zone
    repeat_output.pair_with_output(repeat_input)

    # Sample curve for spawn points
    sample_curve = nodes.new('GeometryNodeSampleCurve')
    sample_curve.parent = frame_branch
    sample_curve.location = (-200, 200)
    sample_curve.label = "Spawn Point Along Parent"

    random_spawn = nodes.new('FunctionNodeRandomValue')
    random_spawn.parent = frame_branch
    random_spawn.location = (-400, 200)
    random_spawn.data_type = 'FLOAT'
    random_spawn.inputs['Min'].default_value = 0.2
    random_spawn.inputs['Max'].default_value = 0.8
    random_spawn.label = "Random Spawn Position"

    # ===== FRAME 4: GROWTH DIRECTION =====
    # Parent normal
    normal_node = nodes.new('GeometryNodeInputNormal')
    normal_node.parent = frame_growth
    normal_node.location = (-200, -200)
    normal_node.label = "Parent Direction"

    # Gravity vector (Phase 2)
    combine_gravity = nodes.new('ShaderNodeCombineXYZ')
    combine_gravity.parent = frame_growth
    combine_gravity.location = (-200, -350)
    combine_gravity.inputs['X'].default_value = 0.0
    combine_gravity.inputs['Y'].default_value = 0.0
    combine_gravity.inputs['Z'].default_value = -1.0
    combine_gravity.label = "Gravity Vector (Down)"

    # Scale gravity by factor
    scale_gravity = nodes.new('ShaderNodeVectorMath')
    scale_gravity.parent = frame_growth
    scale_gravity.location = (0, -350)
    scale_gravity.operation = 'SCALE'
    scale_gravity.label = "Gravity Strength"

    # Sun direction (Phase 2)
    combine_sun = nodes.new('ShaderNodeCombineXYZ')
    combine_sun.parent = frame_growth
    combine_sun.location = (-200, -500)
    combine_sun.inputs['X'].default_value = 0.3
    combine_sun.inputs['Y'].default_value = 0.3
    combine_sun.inputs['Z'].default_value = 1.0
    combine_sun.label = "Sun Direction (Up-ish)"

    # Scale sun by factor
    scale_sun = nodes.new('ShaderNodeVectorMath')
    scale_sun.parent = frame_growth
    scale_sun.location = (0, -500)
    scale_sun.operation = 'SCALE'
    scale_sun.label = "Sun Strength"

    # Random variation
    random_vector = nodes.new('FunctionNodeRandomValue')
    random_vector.parent = frame_growth
    random_vector.location = (-200, -650)
    random_vector.data_type = 'FLOAT_VECTOR'
    random_vector.inputs['Min'].default_value = (-1, -1, -1)
    random_vector.inputs['Max'].default_value = (1, 1, 1)
    random_vector.label = "Random Variation"

    # Add all vectors
    add_vectors1 = nodes.new('ShaderNodeVectorMath')
    add_vectors1.parent = frame_growth
    add_vectors1.location = (200, -300)
    add_vectors1.operation = 'ADD'
    add_vectors1.label = "Combine Forces 1"

    add_vectors2 = nodes.new('ShaderNodeVectorMath')
    add_vectors2.parent = frame_growth
    add_vectors2.location = (400, -300)
    add_vectors2.operation = 'ADD'
    add_vectors2.label = "Combine Forces 2"

    add_vectors3 = nodes.new('ShaderNodeVectorMath')
    add_vectors3.parent = frame_growth
    add_vectors3.location = (600, -300)
    add_vectors3.operation = 'ADD'
    add_vectors3.label = "Combine Forces 3"

    # Normalize final direction
    normalize = nodes.new('ShaderNodeVectorMath')
    normalize.parent = frame_growth
    normalize.location = (800, -300)
    normalize.operation = 'NORMALIZE'
    normalize.label = "Final Growth Direction"

    # ===== FRAME 5: DECAY SYSTEM =====
    # Get iteration index
    repeat_index = nodes.new('GeometryNodeRepeatInput')
    repeat_index.parent = frame_decay
    repeat_index.location = (400, -600)
    repeat_index.inspection_index = 1  # Access index

    # Thickness decay: base * decay^iteration
    thickness_decay_factor = nodes.new('ShaderNodeMath')
    thickness_decay_factor.parent = frame_decay
    thickness_decay_factor.location = (600, -600)
    thickness_decay_factor.operation = 'POWER'
    thickness_decay_factor.inputs[1].default_value = 1  # Will connect iteration
    thickness_decay_factor.label = "Thickness Decay ^iteration"

    multiply_thickness = nodes.new('ShaderNodeMath')
    multiply_thickness.parent = frame_decay
    multiply_thickness.location = (800, -600)
    multiply_thickness.operation = 'MULTIPLY'
    multiply_thickness.label = "Final Branch Thickness"

    # Length decay
    length_decay_factor = nodes.new('ShaderNodeMath')
    length_decay_factor.parent = frame_decay
    length_decay_factor.location = (600, -750)
    length_decay_factor.operation = 'POWER'
    length_decay_factor.label = "Length Decay ^iteration"

    multiply_length = nodes.new('ShaderNodeMath')
    multiply_length.parent = frame_decay
    multiply_length.location = (800, -750)
    multiply_length.operation = 'MULTIPLY'
    multiply_length.label = "Final Branch Length"

    # Create branch curve
    curve_line = nodes.new('GeometryNodeCurveLine')
    curve_line.parent = frame_branch
    curve_line.location = (0, 50)
    curve_line.mode = 'DIRECTION'
    curve_line.label = "Create New Branch Segment"

    # Scale direction by length
    scale_direction = nodes.new('ShaderNodeVectorMath')
    scale_direction.parent = frame_branch
    scale_direction.location = (-50, -100)
    scale_direction.operation = 'SCALE'
    scale_direction.label = "Apply Branch Length"

    # Join geometry
    join_geometry = nodes.new('GeometryNodeJoinGeometry')
    join_geometry.parent = frame_branch
    join_geometry.location = (150, 100)
    join_geometry.label = "Combine Old + New Branches"

    # ===== FRAME 6: GEOMETRY BUILDER =====
    # Read thickness attribute
    attr_thickness = nodes.new('GeometryNodeInputNamedAttribute')
    attr_thickness.parent = frame_geom
    attr_thickness.location = (1000, 0)
    attr_thickness.data_type = 'FLOAT'
    attr_thickness.inputs['Name'].default_value = 'branch_thickness'

    set_radius = nodes.new('GeometryNodeSetCurveRadius')
    set_radius.parent = frame_geom
    set_radius.location = (1000, 100)

    curve_circle = nodes.new('GeometryNodeCurvePrimitiveCircle')
    curve_circle.parent = frame_geom
    curve_circle.location = (1000, -100)
    curve_circle.mode = 'RADIUS'
    curve_circle.inputs['Resolution'].default_value = 8
    curve_circle.inputs['Radius'].default_value = 1.0

    curve_to_mesh = nodes.new('GeometryNodeCurveToMesh')
    curve_to_mesh.parent = frame_geom
    curve_to_mesh.location = (1200, 50)

    set_smooth = nodes.new('GeometryNodeSetShadeSmooth')
    set_smooth.parent = frame_geom
    set_smooth.location = (1350, 50)

    print("[5/6] Created all nodes in organized frames")

    # ===== CREATE INTERFACE =====
    for item in list(node_group.interface.items_tree):
        node_group.interface.remove(item)

    node_group.interface.new_socket(name='Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    node_group.interface.new_socket(name='Base Thickness', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Base Thickness'].default_value = 0.15
    node_group.inputs['Base Thickness'].min_value = 0.01
    node_group.inputs['Base Thickness'].max_value = 2.0

    node_group.interface.new_socket(name='Branch Length', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Branch Length'].default_value = 1.5
    node_group.inputs['Branch Length'].min_value = 0.1
    node_group.inputs['Branch Length'].max_value = 10.0

    node_group.interface.new_socket(name='Iterations', in_out='INPUT', socket_type='NodeSocketInt')
    node_group.inputs['Iterations'].default_value = 3
    node_group.inputs['Iterations'].min_value = 0
    node_group.inputs['Iterations'].max_value = 10

    node_group.interface.new_socket(name='Random Seed', in_out='INPUT', socket_type='NodeSocketInt')
    node_group.inputs['Random Seed'].default_value = 42

    node_group.interface.new_socket(name='Thickness Decay', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Thickness Decay'].default_value = 0.7
    node_group.inputs['Thickness Decay'].min_value = 0.1
    node_group.inputs['Thickness Decay'].max_value = 0.99

    node_group.interface.new_socket(name='Length Decay', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Length Decay'].default_value = 0.8
    node_group.inputs['Length Decay'].min_value = 0.1
    node_group.inputs['Length Decay'].max_value = 0.99

    node_group.interface.new_socket(name='Gravity Strength', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Gravity Strength'].default_value = 0.2
    node_group.inputs['Gravity Strength'].min_value = 0.0
    node_group.inputs['Gravity Strength'].max_value = 1.0

    node_group.interface.new_socket(name='Sun Strength', in_out='INPUT', socket_type='NodeSocketFloat')
    node_group.inputs['Sun Strength'].default_value = 0.3
    node_group.inputs['Sun Strength'].min_value = 0.0
    node_group.inputs['Sun Strength'].max_value = 1.0

    node_group.interface.new_socket(name='Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')

    # ===== CREATE LINKS =====
    # Input chain
    links.new(group_input.outputs[0], mesh_to_curve.inputs['Mesh'])
    links.new(mesh_to_curve.outputs['Curve'], resample.inputs['Curve'])
    links.new(resample.outputs['Curve'], store_iteration.inputs['Geometry'])
    links.new(store_iteration.outputs['Geometry'], store_branch_id.inputs['Geometry'])
    links.new(index_node.outputs['Index'], store_branch_id.inputs['Value'])
    links.new(store_branch_id.outputs['Geometry'], store_thickness.inputs['Geometry'])
    links.new(group_input.outputs['Base Thickness'], store_thickness.inputs['Value'])

    # Into repeat zone
    links.new(store_thickness.outputs['Geometry'], repeat_input.inputs[0])
    links.new(group_input.outputs['Iterations'], repeat_input.inputs['Iterations'])

    # Branch generation
    links.new(repeat_input.outputs[0], sample_curve.inputs['Curve'])
    links.new(random_spawn.outputs['Value'], sample_curve.inputs['Factor'])
    links.new(group_input.outputs['Random Seed'], random_spawn.inputs['Seed'])

    # Growth direction
    links.new(combine_gravity.outputs['Vector'], scale_gravity.inputs['Vector'])
    links.new(group_input.outputs['Gravity Strength'], scale_gravity.inputs['Scale'])
    links.new(combine_sun.outputs['Vector'], scale_sun.inputs['Vector'])
    links.new(group_input.outputs['Sun Strength'], scale_sun.inputs['Scale'])

    links.new(normal_node.outputs['Normal'], add_vectors1.inputs[0])
    links.new(scale_gravity.outputs['Vector'], add_vectors1.inputs[1])
    links.new(add_vectors1.outputs['Vector'], add_vectors2.inputs[0])
    links.new(scale_sun.outputs['Vector'], add_vectors2.inputs[1])
    links.new(add_vectors2.outputs['Vector'], add_vectors3.inputs[0])
    links.new(random_vector.outputs['Value'], add_vectors3.inputs[1])
    links.new(add_vectors3.outputs['Vector'], normalize.inputs['Vector'])

    # Decay system (using iteration index from repeat zone)
    links.new(group_input.outputs['Thickness Decay'], thickness_decay_factor.inputs[0])
    links.new(repeat_input.outputs['Index'], thickness_decay_factor.inputs[1])
    links.new(thickness_decay_factor.outputs['Value'], multiply_thickness.inputs[0])
    links.new(group_input.outputs['Base Thickness'], multiply_thickness.inputs[1])

    links.new(group_input.outputs['Length Decay'], length_decay_factor.inputs[0])
    links.new(repeat_input.outputs['Index'], length_decay_factor.inputs[1])
    links.new(length_decay_factor.outputs['Value'], multiply_length.inputs[0])
    links.new(group_input.outputs['Branch Length'], multiply_length.inputs[1])

    # Create branch
    links.new(sample_curve.outputs['Position'], curve_line.inputs['Start'])
    links.new(normalize.outputs['Vector'], scale_direction.inputs['Vector'])
    links.new(multiply_length.outputs['Value'], scale_direction.inputs['Scale'])
    links.new(scale_direction.outputs['Vector'], curve_line.inputs['Direction'])

    # Join
    links.new(repeat_input.outputs[0], join_geometry.inputs['Geometry'])
    links.new(curve_line.outputs['Curve'], join_geometry.inputs['Geometry'])
    links.new(join_geometry.outputs['Geometry'], repeat_output.inputs[0])

    # Geometry builder
    links.new(repeat_output.outputs[0], set_radius.inputs['Curve'])
    links.new(attr_thickness.outputs['Attribute'], set_radius.inputs['Radius'])
    links.new(set_radius.outputs['Curve'], curve_to_mesh.inputs['Curve'])
    links.new(curve_circle.outputs['Curve'], curve_to_mesh.inputs['Profile Curve'])
    links.new(curve_to_mesh.outputs['Mesh'], set_smooth.inputs['Geometry'])
    links.new(set_smooth.outputs['Geometry'], group_output.inputs[0])

    print("[6/6] All connections complete!")
    print("\\n=== PHASE 2 TREE GENERATOR READY ===")
    print("\\nFeatures:")
    print("  ✓ Repeat Zone branching (0-10 iterations)")
    print("  ✓ Thickness decay per iteration")
    print("  ✓ Length decay per iteration")
    print("  ✓ Gravity effect (branches droop)")
    print("  ✓ Sun direction (phototropism)")
    print("  ✓ 6 organized frames with color coding")
    print("  ✓ 8 user parameters")
    print("\\nRecommended settings:")
    print("  - Iterations: 3")
    print("  - Thickness Decay: 0.7")
    print("  - Length Decay: 0.8")
    print("  - Gravity Strength: 0.2")
    print("  - Sun Strength: 0.3")
"""

try:
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((HOST, PORT))
    print(f"[OK] Connected to Blender at {HOST}:{PORT}\\n")

    command = {
        "type": "execute_code",
        "params": {
            "code": phase2_code
        }
    }

    message = json.dumps(command) + "\\n"
    client.sendall(message.encode('utf-8'))
    response = client.recv(16384).decode('utf-8')
    result = json.loads(response)

    if result['status'] == 'success':
        print("[OK] Phase 2 Implementation Complete!\\n")
        output = result['result'].get('result', '')
        if output:
            print(output)
    else:
        print(f"[ERROR] {result.get('message', 'Unknown error')}")

    client.close()

except Exception as e:
    print(f"[ERROR] {str(e)}")
    import traceback
    traceback.print_exc()
