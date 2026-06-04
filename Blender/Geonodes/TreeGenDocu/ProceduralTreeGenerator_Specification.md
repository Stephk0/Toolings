# Procedural Tree Generator - GeoNodes Specification

**Version:** 1.0
**Date:** 2025-12-01
**Author:** Stephan Viranyi (Stephko)
**Target Blender Version:** 4.5+

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [Core Components](#core-components)
4. [Input Systems](#input-systems)
5. [Branch Generation Logic](#branch-generation-logic)
6. [Canopy-Guided Growth](#canopy-guided-growth)
7. [Leaf/Asset Spawning System](#leafasset-spawning-system)
8. [Attribute Structure](#attribute-structure)
9. [User-Exposed Parameters](#user-exposed-parameters)
10. [Implementation Guidelines](#implementation-guidelines)
11. [Technical Requirements](#technical-requirements)
12. [Development Roadmap](#development-roadmap)

---

## Project Overview

### Goal
Create a fully procedural GeoNodes system in Blender that generates realistic trees with:
- Main trunk/branch system
- Multiple iterative levels of sub-branches
- Optional canopy-based growth limiting
- Optional leaf/asset scattering system

### Design Principles
- **Fully Procedural:** All geometry generation remains non-destructive
- **Modular Architecture:** Clean node groups with clear responsibilities
- **Attribute-Driven:** Extensive use of named attributes for data flow
- **User-Friendly:** Organized, intuitive controls with sensible defaults
- **Production-Ready:** Performance-conscious and robust

---

## System Architecture

### High-Level Flow

```
User Input (Branches/Curves)
    ↓
Resample & Initialize Attributes
    ↓
┌─────────────────────────────────┐
│  Iterative Branch Generation    │
│  (Repeat Zone / Simulation)     │
│                                 │
│  For each iteration:            │
│  1. Select spawn points         │
│  2. Calculate growth vectors    │
│  3. Generate sub-branches       │
│  4. Apply thickness/length decay│
│  5. Store hierarchy data        │
└─────────────────────────────────┘
    ↓
Canopy Guidance (Optional)
    ↓
Curve to Mesh Conversion
    ↓
Leaf/Asset Scattering (Optional)
    ↓
Final Tree Geometry
```

### Module Breakdown

| Module | Purpose | Key Outputs |
|--------|---------|-------------|
| **Input Processor** | Normalize user input curves | Resampled curves with initial attributes |
| **Branch Iterator** | Generate sub-branch hierarchy | Multi-level branch curves |
| **Growth Director** | Calculate branch directions | Direction vectors per spawn point |
| **Canopy Controller** | Limit/guide growth to canopy | Clamped endpoints, attraction vectors |
| **Geometry Builder** | Convert curves to mesh | Mesh branches with proper radius |
| **Asset Scatterer** | Place leaves/objects | Instanced geometry at endpoints |

---

## Core Components

### 1. Input Processor

**Function:** Prepare user-provided curves for procedural generation

**Operations:**
- Convert mesh edges to curves if needed
- Resample curves for even point distribution
- Initialize root attributes:
  - `branch_index` = unique ID
  - `iteration_level` = 0 (root level)
  - `parent_thickness` = user-defined base thickness
  - `spawn_position` = normalized curve parameter [0-1]

**Node Types Used:**
- Mesh to Curve
- Resample Curve
- Store Named Attribute
- Set Position

---

### 2. Branch Iterator (Core System)

**Function:** Generate multiple levels of sub-branches procedurally

**Implementation Strategy:**
- Use **Repeat Zone** (Blender 4.0+) or **Simulation Zone** for iterative generation
- Default: 3 iterations (user-configurable)
- Each iteration spawns new branches from previous level

**Per-Iteration Steps:**

1. **Spawn Point Selection**
   - Select random points along parent curves
   - Exclude endpoints (first/last 5-10% of curve)
   - Use Poisson disk sampling for natural spacing
   - Apply spawn probability mask

2. **Direction Calculation**
   - Combine multiple vector influences (see Growth Director)
   - Add random angular variation
   - Ensure angle constraints relative to parent

3. **Sub-Branch Creation**
   - Create new curve segments
   - Assign hierarchy attributes
   - Apply decay formulas

4. **Attribute Propagation**
   - Inherit parent data
   - Increment iteration level
   - Store parent-child relationships

**Decay Formulas:**
```
new_thickness = parent_thickness × thickness_decay_factor^iteration
new_length = base_length × length_decay_factor^iteration
spawn_probability = base_probability × (1 - iteration / max_iterations)
```

---

### 3. Growth Director

**Function:** Calculate natural branch growth directions

**Vector Components:**

| Vector | Weight | Purpose |
|--------|--------|---------|
| **Parent Normal** | 0.3-0.5 | Maintain general growth direction |
| **Sun Direction** | 0.2-0.4 | Phototropism (branches reach toward light) |
| **Gravity** | 0.1-0.2 | Downward pull (negative Z) |
| **Wind Noise** | 0.1-0.3 | Natural irregularity and sway |
| **Canopy Attraction** | 0.2-0.5 | Guide toward canopy boundary (if enabled) |
| **Random Variation** | 0.1-0.3 | Fibonacci sphere distribution |

**Calculation Method:**
```
final_direction = normalize(
    parent_normal × w1 +
    sun_vector × w2 +
    (0, 0, -1) × gravity × w3 +
    noise_vector × w4 +
    canopy_vector × w5 +
    random_sphere_vector × w6
)
```

**Noise Types:**
- **Curl Noise:** Natural wiggling along branch length
- **Perlin Noise:** Large-scale directional variation
- **Voronoi F1:** Clustered growth patterns

---

### 4. Canopy Controller

**Function:** Define growth boundaries and attraction surfaces

#### Mode A: Procedural Canopy

**Parameters:**
- Canopy height (base to top)
- Radius profile (bezier curve or formula)
- Taper amount
- Noise roughness
- Shape preset (sphere, cone, custom)

**Implementation:**
- Generate implicit volume using math nodes
- Compute signed distance field
- Use distance for:
  - Branch endpoint clamping
  - Growth vector attraction
  - Spawn probability modulation

#### Mode B: User-Provided Canopy Mesh

**Input:** Mesh object (referenced, not consumed)

**Operations:**
- Geometry Proximity node for nearest surface
- Calculate:
  - Distance to surface
  - Surface normal at nearest point
  - Attraction vector toward surface

**Growth Control Options:**
- **Clamp:** Stop branch exactly at surface
- **Overshoot:** Extend beyond surface by random % (0-20%)
- **Undershoot:** Stop before surface by random % (0-30%)
- **Blend:** Weighted combination based on branch level

#### Mode C: Combined (Procedural + Mesh)

**Strategy:**
- Calculate both attraction vectors
- Weight-blend based on user slider
- Allows procedural base shape with mesh detail refinement

---

### 5. Geometry Builder

**Function:** Convert branch curves to solid geometry

**Process:**

1. **Radius Assignment**
   - Read `branch_thickness` attribute
   - Apply radius profile curve (root to tip taper)
   - Clamp child thickness < parent thickness

2. **Curve to Mesh**
   - Use Curve to Mesh node
   - Profile curve: circular cross-section (8-12 vertices)
   - Optional: UV mapping for bark textures

3. **Mesh Joining**
   - Join all branch levels
   - Optional: Merge vertices at junctions
   - Optional: Add connection geometry at splits

4. **Material Assignment**
   - Assign material based on iteration level
   - Store level as vertex color for shader variation

---

### 6. Asset Scatterer

**Function:** Place leaves or custom objects on tree

**Primary Placement:** Branch endpoints (final iteration)

**Secondary Placement (Optional):**
- Branch junctions (where splits occur)
- Random points along branch length (low density)
- Clustered around specific attribute values

**Scattering Logic:**

1. **Point Generation**
   - Distribute Points on Faces (for surface scattering)
   - Or sample curve endpoints directly
   - Apply spawn density mask

2. **Instance Selection**
   - Single object mode: One asset type
   - Collection mode: Random pick from collection
   - Weighted randomness for variety

3. **Transformation**
   - **Position:** Exact or offset by noise
   - **Rotation:**
     - Align Y-axis to branch tangent
     - Random twist around branch axis
     - Slight random tilt for natural variation
   - **Scale:**
     - Random within min/max range
     - Optional: Scale by branch thickness
     - Cluster size variation

4. **Alignment Options**
   - **Sun Alignment:** Rotate leaves toward sun direction
   - **Gravity Droop:** Slight downward tilt
   - **Wind Orientation:** Align with wind vector

---

## Input Systems

### 1. Main Branch Input (Required)

**Type:** Mesh edges or curve

**Requirements:**
- At least one edge/curve segment
- Can be single trunk or multiple main branches
- Supports arbitrary starting shapes (Y-branch, V-shape, etc.)

**Preprocessing:**
- Convert edges to curves
- Resample to target point density
- Initialize root-level attributes

**Use Cases:**
- Single straight trunk (classic tree)
- Pre-bent trunk (wind-swept tree)
- Multi-trunk (bush or ancient tree)
- User-sculpted base structure

---

### 2. Canopy Input (Optional)

**Type:** Mesh object or procedural parameters

#### Procedural Canopy Parameters:

| Parameter | Type | Range | Default |
|-----------|------|-------|---------|
| Height | Float | 0-100m | 10m |
| Radius Base | Float | 0-50m | 5m |
| Radius Top | Float | 0-50m | 3m |
| Shape | Enum | Sphere/Cone/Ellipsoid/Custom | Sphere |
| Roughness | Float | 0-1 | 0.3 |
| Noise Scale | Float | 0.1-10 | 1.0 |

#### Mesh Canopy Requirements:
- Closed or open mesh
- Any topology (quads/tris/ngons)
- No overlapping geometry (for best results)

---

### 3. Spawn Object Input (Optional)

**Type:** Object or Collection

**Single Object Mode:**
- One mesh/curve object
- All instances use same geometry
- Fast and simple

**Collection Mode:**
- Multiple objects in collection
- Random selection per instance
- Optional: Weighted probability per object

**Supported Types:**
- Mesh objects (leaves, flowers, fruit)
- Curve objects (vines, tendrils)
- Empty objects (for custom shading tricks)

---

## Branch Generation Logic

### Iterative Spawning System

**Core Concept:** Each iteration adds a new level of branches to the previous level

**Implementation Pattern:**

```
Repeat Zone:
    Input: Branches from previous iteration
    Iteration Count: Current level (1 to max_iterations)

    Operations:
        1. Sample spawn points on parent curves
        2. Calculate growth directions
        3. Generate new curve segments
        4. Assign attributes (parent_id, level, thickness)
        5. Apply decay factors

    Output: Combined geometry (old + new branches)
```

### Random Distribution Rules

**Spawn Point Selection:**
- **Poisson Disk Sampling:** Maintain minimum distance between spawn points
- **Exclude Zones:**
  - First 10% of curve (near root)
  - Last 10% of curve (near tip)
- **Probability Mask:** Higher probability in middle sections

**Angular Distribution:**
- **Fibonacci Sphere:** Natural spiral pattern around parent
- **Golden Angle:** 137.5° rotation between consecutive branches
- **Clustering:** Slight bias toward certain angles (realistic irregularity)

**Spacing Distribution:**
- **Base Spacing:** User-defined minimum distance
- **Level Modifier:** Closer spacing at higher iterations
- **Random Jitter:** ±20% variation from base spacing

### Growth Direction Calculation

**Phototropism (Sun Direction):**
- Branches bend toward sun vector
- Strength increases with iteration level (outer branches more sun-seeking)
- Applied as angle adjustment per curve point

**Gravitropism (Gravity):**
- Downward pull (negative Z)
- Weaker on main branches, stronger on small twigs
- Creates natural drooping effect

**Wind Effect:**
- Noise-driven directional bias
- Low-frequency noise (large-scale sway)
- Per-branch variation (not uniform)

**Natural Randomness:**
- Curl noise for organic wiggling
- Prevent perfect symmetry
- Avoid self-intersection

### Geometry Creation Details

**Curve Generation:**
- Start point: Spawn location on parent
- Direction: Calculated growth vector
- Length: Base length × decay factor
- Handle type: Vector or Auto for smooth curves

**Radius Profile:**
```
radius(t) = branch_thickness × (1 - t × taper_factor)
where t = curve parameter [0-1]
```

**Thickness Constraints:**
- Child thickness ≤ parent thickness × 0.7
- Minimum thickness: 0.01 units (prevent degenerate geometry)
- Smooth transition at junction

---

## Canopy-Guided Growth

### Distance Field Method

**For Procedural Canopy:**

1. Define implicit surface equation:
   ```
   For sphere: distance = |position - center| - radius
   For cone: distance = custom_formula(position, height, radius)
   ```

2. Sample distance at branch endpoints

3. Clamp or modulate based on signed distance:
   - Negative (inside): Allow growth
   - Zero (on surface): Stop or slight overshoot
   - Positive (outside): Pull back toward surface

### Surface Attraction Method

**For Mesh Canopy:**

1. Use **Geometry Proximity** node:
   - Input: Branch endpoint positions
   - Target: Canopy mesh
   - Output: Nearest point, distance, normal

2. Calculate attraction vector:
   ```
   attraction = normalize(nearest_point - current_position)
   ```

3. Blend with growth vector:
   ```
   final_direction = lerp(growth_vector, attraction, canopy_weight)
   ```

### Overshoot/Undershoot System

**Per-Branch Randomization:**
- Roll random value [0-1] per branch
- Compare to threshold for mode selection:
  - 0.0-0.3: Undershoot (stop early)
  - 0.3-0.7: Exact clamp (stop at surface)
  - 0.7-1.0: Overshoot (extend beyond)

**Distance Modulation:**
```
if undershoot:
    stop_distance = surface_distance × random(0.7, 1.0)
elif exact:
    stop_distance = surface_distance
elif overshoot:
    stop_distance = surface_distance × random(1.0, 1.2)
```

### Combined Mode Strategy

**Blending Procedural + Mesh:**

1. Calculate both volume distance and mesh proximity
2. Weight by user slider (0 = procedural only, 1 = mesh only)
3. Use blended distance for all growth decisions

**Use Case:**
- Procedural volume defines rough shape (fast, controllable)
- Mesh adds detail (custom silhouette, asymmetry)

---

## Leaf/Asset Spawning System

### Placement Strategy

**Priority Locations:**

1. **Endpoint Focus (Primary):**
   - Final iteration branch tips
   - Highest density
   - Natural leaf location

2. **Junction Points (Secondary):**
   - Where branches split
   - Lower density (10-20% of endpoint density)
   - Represents buds or small leaves

3. **Along Length (Tertiary):**
   - Random points on branch curves
   - Very low density (5-10%)
   - For vines or special leaf types

### Scattering Parameters

| Parameter | Type | Range | Default | Description |
|-----------|------|-------|---------|-------------|
| Density | Float | 0-100 | 50 | Overall spawn probability |
| Endpoint Bias | Float | 0-1 | 0.8 | Weight toward branch tips |
| Scale Min | Float | 0.01-10 | 0.8 | Minimum random scale |
| Scale Max | Float | 0.01-10 | 1.2 | Maximum random scale |
| Rotation Random | Float | 0-180° | 45° | Random rotation range |
| Sun Align | Float | 0-1 | 0.5 | Leaf orientation toward sun |
| Cluster Size | Int | 1-10 | 1 | Leaves per spawn point |

### Instance Transformation

**Rotation Logic:**

1. **Align to Branch:**
   - Get branch tangent at spawn point
   - Align leaf Y-axis (stem) to tangent
   - Or align normal toward sun

2. **Random Twist:**
   - Rotate around branch axis
   - Random angle per instance

3. **Natural Tilt:**
   - Slight random rotation (±15°)
   - Curl noise for organic variation

**Scale Variation:**
```
scale = random(scale_min, scale_max)
if scale_by_branch_thickness:
    scale *= branch_thickness / base_thickness
```

### Collection Handling

**Random Selection:**
- Pick random object from collection per spawn point
- Use consistent seed for reproducibility

**Weighted Probability:**
- Assign weight per object (stored in custom property?)
- Use weighted random selection

**Performance Note:**
- Instance-on-Points is fast
- Collection instancing has negligible overhead

### Natural Clustering

**Create Leaf Groups:**
- Spawn multiple leaves at same point
- Slight position offset per leaf in cluster
- Varying rotation within cluster

**Distribution Pattern:**
- Use Voronoi texture for clustered mask
- Higher values = more leaves
- Creates natural "fullness" variation

---

## Attribute Structure

### Core Attributes (Required)

| Attribute Name | Type | Scope | Description |
|----------------|------|-------|-------------|
| `branch_id` | Int | Point | Unique identifier per branch segment |
| `parent_branch_id` | Int | Point | ID of parent branch (0 for root) |
| `iteration_level` | Int | Point | Generation depth (0=trunk, 1=main, 2=sub, etc.) |
| `branch_thickness` | Float | Point | Radius at this point (for Curve to Mesh) |
| `branch_length` | Float | Curve | Total length of this branch segment |
| `spawn_factor` | Float | Point | Normalized position along parent [0-1] |
| `curve_parameter` | Float | Point | Position along this curve [0-1] |

### Growth Control Attributes

| Attribute Name | Type | Scope | Description |
|----------------|------|-------|-------------|
| `sun_vector` | Vector | Global | Direction to sun (for phototropism) |
| `gravity_factor` | Float | Point | Gravity influence strength |
| `wind_vector` | Vector | Global | Wind direction and strength |
| `canopy_target_vector` | Vector | Point | Direction toward canopy surface |
| `canopy_distance` | Float | Point | Signed distance to canopy boundary |
| `growth_direction` | Vector | Point | Final calculated growth direction |

### Spawning Control Attributes

| Attribute Name | Type | Scope | Description |
|----------------|------|-------|-------------|
| `leaf_spawn_mask` | Float | Point | Probability of leaf spawn [0-1] |
| `is_endpoint` | Boolean | Point | True if branch endpoint (for leaf priority) |
| `is_junction` | Boolean | Point | True if branch split point |
| `spawn_cluster_id` | Int | Point | Group ID for leaf clustering |

### Utility Attributes

| Attribute Name | Type | Scope | Description |
|----------------|------|-------|-------------|
| `random_seed` | Int | Point | Per-branch random seed for reproducibility |
| `noise_offset` | Vector | Point | 3D position offset for noise sampling |
| `is_active` | Boolean | Point | Used in iterative generation (temp) |

---

## User-Exposed Parameters

### Interface Organization

**Group 1: Main Branch Settings**
- Input Curve/Mesh (Object selector)
- Resample Count (Int, 10-1000, default: 100)
- Base Thickness (Float, 0.1-10, default: 0.5)
- Seed (Int, 0-999999, default: 0)

**Group 2: Branch Generation**
- Number of Iterations (Int, 1-10, default: 3)
- Spawn Probability (Float, 0-1, default: 0.7)
  - Per-level array (advanced)
- Thickness Decay (Float, 0.1-0.99, default: 0.7)
- Length Decay (Float, 0.1-0.99, default: 0.8)
- Branch Length Base (Float, 0.1-10, default: 2.0)
- Angular Spread (Float, 0-90°, default: 45°)
- Twist Amount (Float, 0-360°, default: 60°)

**Group 3: Growth Forces**
- Gravity Factor (Float, 0-1, default: 0.2)
- Sun Direction (Vector, default: (0, 0, 1))
- Sun Strength (Float, 0-1, default: 0.3)
- Wind Direction (Vector, default: (1, 0, 0))
- Wind Strength (Float, 0-1, default: 0.1)
- Wind Noise Scale (Float, 0.1-10, default: 2.0)
- Curl Noise Intensity (Float, 0-1, default: 0.3)

**Group 4: Canopy Controls**
- Canopy Mode (Enum: None/Procedural/Mesh/Both)
- *If Procedural:*
  - Height (Float, 0-100, default: 10)
  - Radius Base (Float, 0-50, default: 5)
  - Radius Top (Float, 0-50, default: 3)
  - Shape (Enum: Sphere/Cone/Ellipsoid)
  - Roughness (Float, 0-1, default: 0.3)
  - Noise Scale (Float, 0.1-10, default: 1.0)
- *If Mesh:*
  - Canopy Mesh (Object selector)
  - Attraction Strength (Float, 0-1, default: 0.5)
- Overshoot % (Float, 0-50, default: 10)
- Undershoot % (Float, 0-50, default: 20)
- Clamp vs Attract (Float, 0-1, default: 0.5)

**Group 5: Leaf/Object Spawning**
- Enable Leaves (Boolean, default: False)
- Spawn Mode (Enum: Single/Collection)
- Object/Collection (Object/Collection selector)
- Density (Float, 0-100, default: 50)
- Endpoint Bias (Float, 0-1, default: 0.8)
- Scale Min (Float, 0.01-10, default: 0.8)
- Scale Max (Float, 0.01-10, default: 1.2)
- Scale by Thickness (Boolean, default: True)
- Random Rotation (Float, 0-180, default: 45)
- Sun Alignment (Float, 0-1, default: 0.5)
- Cluster Size (Int, 1-10, default: 1)
- Cluster Spread (Float, 0-1, default: 0.1)

**Group 6: Advanced/Debug**
- Show Attributes (Boolean, default: False)
  - Displays attribute values as vertex colors
- Debug Mode (Boolean, default: False)
  - Shows intermediate geometry
- Profile Resolution (Int, 3-32, default: 8)
  - Circle vertices for branch mesh
- Material Slot (Material selector)

---

## Implementation Guidelines

### Node Group Structure

**Recommended Hierarchy:**

```
TreeGenerator_Main
├── InputProcessor
│   ├── EdgeToCurve
│   ├── ResampleCurve
│   └── InitializeAttributes
├── BranchIterator (Repeat Zone)
│   ├── SpawnPointSelector
│   ├── GrowthDirector
│   │   ├── CalculateSunVector
│   │   ├── CalculateGravity
│   │   ├── CalculateWind
│   │   └── BlendVectors
│   ├── BranchGeometry
│   │   ├── CreateCurveSegment
│   │   └── AssignAttributes
│   └── DecayModifier
├── CanopyController (Optional)
│   ├── ProceduralCanopy
│   ├── MeshCanopy
│   └── CombinedMode
├── GeometryBuilder
│   ├── CurveToMesh
│   ├── RadiusProfile
│   └── MaterialAssign
└── AssetScatterer (Optional)
    ├── PointGeneration
    ├── InstanceSelector
    └── TransformationLogic
```

### Frame Organization & Naming

**Critical Requirement:** All nodes MUST be organized into labeled frames for clarity and maintainability.

#### Frame Structure (Phase 1 & 2)

**Frame 1: INPUT PROCESSING**
- **Color:** Green (0.3, 0.5, 0.3)
- **Location:** Left side of node tree (-1000 to -600 X)
- **Contents:**
  - Mesh to Curve conversion
  - Curve resampling (even point distribution)
  - Set Curve Normal (consistent direction)
  - Selection mask cleanup

**Frame 2: ATTRIBUTE INITIALIZATION**
- **Color:** Blue (0.3, 0.3, 0.5)
- **Location:** (-600 to -400 X)
- **Contents:**
  - Store Named Attribute: `iteration_level` (Int, starts at 0)
  - Store Named Attribute: `branch_id` (Int, unique ID)
  - Store Named Attribute: `parent_branch_id` (Int, hierarchy)
  - Store Named Attribute: `branch_thickness` (Float, from user input)
  - Store Named Attribute: `curve_parameter` (Float, 0-1 along curve)
  - Index node for ID generation
  - Spline Parameter for curve factor

**Frame 3: BRANCH GENERATION (CORE SYSTEM)**
- **Color:** Red (0.5, 0.3, 0.3)
- **Location:** Center (-200 to 400 X)
- **Contents:**
  - **Repeat Zone Input/Output** (main iteration container)
  - Sample Curve (spawn point selection)
  - Random Value (spawn positions)
  - Curve Line (new branch segment creation)
  - Join Geometry (combine old + new branches)
  - Store iteration increment

**Frame 4: GROWTH DIRECTION CALCULATOR**
- **Color:** Orange (0.5, 0.4, 0.2)
- **Location:** Below Branch Generation (-200 to 400 X, -400 to -200 Y)
- **Contents:**
  - **Parent Normal** - base direction inheritance
  - **Sun Direction Vector** - phototropism (Phase 2)
  - **Gravity Vector** - downward pull (Phase 2)
  - **Wind Noise** - natural variation (Phase 2)
  - **Random Variation** - Fibonacci/golden angle distribution
  - Mix/Combine nodes - blend all influences
  - Normalize - final unit vector

**Frame 5: DECAY SYSTEM** (Phase 2)
- **Color:** Yellow (0.5, 0.5, 0.2)
- **Location:** Right of Growth Direction (400 to 600 X, -400 to -200 Y)
- **Contents:**
  - Math nodes for thickness decay (exponential)
  - Math nodes for length decay (exponential)
  - Probability reduction per iteration
  - Clamp minimum thickness (0.01 units)
  - Child thickness constraint (≤ parent × 0.7)

**Frame 6: GEOMETRY BUILDER**
- **Color:** Purple (0.4, 0.3, 0.5)
- **Location:** Right side (500 to 900 X)
- **Contents:**
  - Named Attribute read: `branch_thickness`
  - Set Curve Radius
  - Curve Circle (profile, 8-12 vertices)
  - Curve to Mesh
  - Set Shade Smooth
  - Optional: Material assignment by iteration level

**Frame 7: CANOPY SYSTEM** (Phase 3+)
- **Color:** Cyan (0.2, 0.5, 0.5)
- **Location:** Top area (0 to 600 X, 200 to 400 Y)
- **Contents:** (Future implementation)

**Frame 8: ASSET SCATTERING** (Phase 5+)
- **Color:** Magenta (0.5, 0.3, 0.5)
- **Location:** Bottom area (500 to 900 X, -600 to -400 Y)
- **Contents:** (Future implementation)

#### Naming Conventions

**Frames:**
- ALL CAPS for frame labels
- Space-separated words
- Descriptive of system function
- Examples: "INPUT PROCESSING", "GROWTH DIRECTION CALCULATOR"

**Nodes:**
- Descriptive labels for complex operations
- Examples:
  - "Calculate Sun Influence" (not just "Math")
  - "Thickness Decay Factor" (not just "Multiply")
  - "Random Branch Angle" (not just "Random Value")
  - "Spawn Point Along Parent" (not just "Sample Curve")

**Node Groups (if created):**
- PascalCase
- Prefix with system: `Growth_CalculateSunVector`
- Clear purpose: `Decay_ThicknessReduction`

**Attributes:**
- lowercase_with_underscores
- Descriptive: `iteration_level`, not `iter`
- Type prefix for clarity:
  - `vec_` for vectors: `vec_growth_direction`
  - `is_` for booleans: `is_endpoint`

#### Visual Organization Best Practices

**Horizontal Flow:**
```
Input → Attributes → [Loop: Branch Gen + Growth] → Decay → Geometry → Output
-1000      -600           -200 to 400              400      600       800
```

**Vertical Layers:**
```
        Canopy (top, +200 to +400 Y)
              ↓
Main Flow (center, 0 Y)
              ↓
Growth Calculation (mid, -200 to -400 Y)
              ↓
   Asset Scattering (bottom, -600 Y)
```

**Frame Positioning:**
- No overlapping frames
- 50-100 pixel spacing between frames
- Related systems vertically aligned
- Clear signal flow left-to-right

**Reroute Nodes:**
- Use for long connections
- Keep vertical/horizontal (no diagonals)
- Label important reroutes: "Geometry Flow", "Thickness Data"

**Color Coding Summary:**

| System | Color | RGB | Visual Cue |
|--------|-------|-----|------------|
| Input Processing | Green | (0.3, 0.5, 0.3) | Data entry point |
| Attributes | Blue | (0.3, 0.3, 0.5) | Data storage |
| Branch Generation | Red | (0.5, 0.3, 0.3) | Core algorithm |
| Growth Direction | Orange | (0.5, 0.4, 0.2) | Physics/forces |
| Decay System | Yellow | (0.5, 0.5, 0.2) | Degradation |
| Geometry Builder | Purple | (0.4, 0.3, 0.5) | Mesh output |
| Canopy (future) | Cyan | (0.2, 0.5, 0.5) | Boundary control |
| Assets (future) | Magenta | (0.5, 0.3, 0.5) | Detail layer |

### Development Phases

**Phase 1: Core Branch Generation (MVP)**
- Input processing
- Single iteration branch spawning
- Basic growth direction (parent normal + random)
- Curve to mesh conversion
- Essential attributes

**Phase 2: Iteration & Hierarchy**
- Repeat zone implementation
- Multi-level generation
- Thickness/length decay
- Parent-child relationship tracking

**Phase 3: Natural Growth Forces**
- Sun direction (phototropism)
- Gravity effect
- Wind noise integration
- Angular distribution (Fibonacci)

**Phase 4: Canopy System**
- Procedural canopy volume
- Distance field calculation
- Growth clamping
- Overshoot/undershoot logic

**Phase 5: Mesh Canopy Integration**
- Geometry proximity
- Surface attraction
- Normal-based growth
- Combined mode blending

**Phase 6: Asset Scattering**
- Endpoint detection
- Instance-on-Points setup
- Collection support
- Transformation controls

**Phase 7: Refinement & Optimization**
- UI organization
- Parameter presets
- Performance optimization
- Edge case handling

### Testing Checklist

**Functionality Tests:**
- [ ] Single straight trunk generates correctly
- [ ] Multiple iterations create hierarchy
- [ ] Thickness decay works properly
- [ ] Branches don't exceed parent thickness
- [ ] Random seed produces reproducible results
- [ ] Canopy clamping prevents overgrowth
- [ ] Leaves spawn at correct locations
- [ ] Collection instancing works
- [ ] All attributes store correctly

**Edge Cases:**
- [ ] Zero iterations (should output input)
- [ ] Single point input (should handle gracefully)
- [ ] Extreme thickness decay (near 0 or 1)
- [ ] Very high iteration count (performance)
- [ ] Overlapping canopy mesh (non-manifold)
- [ ] Empty collection input
- [ ] Missing canopy mesh reference

**Performance Tests:**
- [ ] 10,000+ branch segments (should remain interactive)
- [ ] 100,000+ leaf instances
- [ ] Real-time viewport update (< 1 second)
- [ ] Render time acceptable

---

## Technical Requirements

### Non-Negotiable Requirements

1. **Fully Procedural:**
   - No baking
   - No destructive operations
   - All editable via input parameters

2. **Input Flexibility:**
   - Single edge or multiple edges
   - Curve or mesh input
   - Arbitrary starting topology

3. **Randomness Control:**
   - Seeded randomness (reproducible)
   - Per-branch seeds exposed
   - User-controllable seed value

4. **Hierarchy Preservation:**
   - Child thickness < parent thickness
   - Length constraints per level
   - Angle limits respected
   - No self-intersection (best effort)

5. **Attribute System:**
   - Named attributes for all data
   - No data loss between nodes
   - Attributes visible for debugging

6. **Editability:**
   - All parameters adjustable after generation
   - Instant feedback in viewport
   - No modal operations

### Performance Targets

| Metric | Target | Acceptable | Notes |
|--------|--------|------------|-------|
| Branch Count | 50,000 | 100,000 | Before slowdown |
| Leaf Instances | 100,000 | 500,000 | With instancing |
| Viewport FPS | 30 fps | 15 fps | While adjusting parameters |
| Update Latency | < 0.5s | < 2s | Parameter change to viewport |
| Memory Usage | < 500 MB | < 2 GB | For typical tree |

### Blender Version Requirements

**Minimum:** Blender 4.0
- Repeat Zones introduced in 4.0
- Improved attribute system

**Recommended:** Blender 4.5+
- Performance improvements
- Better geometry nodes tools
- Enhanced attribute debugging

**Required Nodes:**
- Repeat Zone (4.0+)
- Store Named Attribute
- Geometry Proximity
- Instance on Points
- Curve to Mesh
- Distribute Points on Faces
- Various math/vector nodes

### Dependencies

**None.** Pure Blender GeoNodes implementation.
- No external addons
- No Python scripting
- No third-party assets

---

## Development Roadmap

### Version 1.0 (Core Functionality)
- ✅ Single trunk input
- ✅ 3-iteration branch generation
- ✅ Basic thickness/length decay
- ✅ Curve to mesh conversion
- ✅ Essential attributes

### Version 1.1 (Natural Growth)
- ⬜ Sun direction (phototropism)
- ⬜ Gravity effect
- ⬜ Wind noise
- ⬜ Fibonacci angular distribution
- ⬜ Improved randomness

### Version 1.2 (Canopy System)
- ⬜ Procedural canopy shapes
- ⬜ Distance field clamping
- ⬜ Overshoot/undershoot
- ⬜ Attraction system

### Version 1.3 (Mesh Canopy)
- ⬜ User mesh input
- ⬜ Surface proximity
- ⬜ Normal-based attraction
- ⬜ Combined mode

### Version 1.4 (Asset Scattering)
- ⬜ Endpoint leaf spawning
- ⬜ Collection support
- ⬜ Transform controls
- ⬜ Clustering system

### Version 2.0 (Advanced Features)
- ⬜ Bark texture UVs
- ⬜ Branch joint smoothing
- ⬜ Seasonal variation presets
- ⬜ Damage/dead branch system
- ⬜ Wind animation (runtime)

### Version 2.1 (Optimization)
- ⬜ LOD system (distance-based detail)
- ⬜ Culling (off-camera branch removal)
- ⬜ Instancing optimization
- ⬜ Memory footprint reduction

---

## Best Practices

### Attribute Naming Conventions
- Use lowercase with underscores: `branch_thickness`
- Prefix type for clarity: `is_endpoint` (boolean), `vec_growth` (vector)
- Avoid abbreviations: `iteration_level` not `iter_lvl`
- Be specific: `parent_branch_id` not just `parent`

### Node Group Organization
- One clear purpose per group
- Inputs on left, outputs on right
- Use reroute nodes for clarity
- Frame important sections with labels
- Color-code by function (green=input, blue=processing, red=output)

### Performance Considerations
- Minimize geometry conversions (mesh↔curve)
- Use instancing wherever possible
- Cache unchanging calculations
- Avoid redundant attribute reads/writes
- Use simpler noise types when acceptable

### User Experience
- Group related parameters with frames
- Provide sensible default values
- Use descriptive tooltips (custom properties)
- Hide advanced parameters by default
- Include presets for common tree types

---

## Troubleshooting

### Common Issues

**Branches Don't Appear:**
- Check input curve is not empty
- Verify spawn probability > 0
- Ensure iteration count > 0
- Check thickness values (not zero)

**Branches Explode/Scatter:**
- Reduce angular spread
- Increase gravity factor
- Check wind noise scale (lower values)
- Verify seed produces stable result

**Performance Degradation:**
- Reduce iteration count
- Lower resample density
- Decrease leaf density
- Disable real-time viewport update

**Leaves Not Spawning:**
- Enable leaves option
- Check density value
- Verify object/collection input
- Ensure endpoints exist (iteration > 0)

**Thickness Issues:**
- Verify base thickness > 0
- Check decay factor (0.5-0.9 typical)
- Ensure minimum thickness threshold

---

## References

### Blender Documentation
- [Geometry Nodes Manual](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/index.html)
- [Repeat Zone](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/simulation/repeat.html)
- [Attributes](https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/attributes_reference.html)

### Procedural Generation Concepts
- L-Systems (not directly used but inspirational)
- Space Colonization Algorithm (for vein-like growth)
- Fibonacci Phyllotaxis (natural spiral patterns)
- Poisson Disk Sampling (natural spacing)

### Natural Growth Principles
- Phototropism (light-seeking)
- Gravitropism (gravity response)
- Apical Dominance (top growth priority)
- Branch Angle Optimization

---

## Appendix: Mathematical Formulas

### Thickness Decay
```
thickness(level) = base_thickness × decay_factor^level
Constraint: thickness(child) ≤ thickness(parent) × 0.7
Minimum: 0.01 units
```

### Length Decay
```
length(level) = base_length × length_decay^level × random(0.8, 1.2)
```

### Angular Distribution (Fibonacci)
```
golden_angle = 137.5° (or 2π / φ², φ = golden ratio)
angle(n) = n × golden_angle + random(-spread, spread)
```

### Gravity Vector
```
gravity_influence = (0, 0, -1) × gravity_factor × (1 - level / max_level)^2
```

### Sun Attraction
```
sun_influence = normalize(sun_direction) × sun_strength × level / max_level
```

### Canopy Distance (Spherical)
```
distance = |point - center| - radius + noise(point) × roughness
```

---

## Version History

**v1.0 (2025-12-01):** Initial specification document created

---

**Document Status:** Draft / Planning Phase
**Next Review:** After Phase 1 implementation
**Maintainer:** Stephan Viranyi (Stephko)

---

*This document serves as the complete technical specification for the Procedural Tree Generator GeoNodes system. All implementation should reference this document for design decisions, parameter ranges, and system architecture.*
