# Tile UV Projector v1.2.1

Tile-based UV projection and placement for texture atlas workflows in Blender.

## Overview

Select mesh faces, click a tile in the grid, and the addon automatically projects, unwraps, relaxes, and fits the UVs into that tile with padding. Ideal for texture atlas creation and tile-based texturing workflows.

## Features

- **Uniform Grid Mode** - Configurable X/Y grid (default 4x4) with clickable tile buttons
- **Proportional Grid Buttons** - W:H proportion field controls button aspect ratio to match your texture
- **Atlas Texture Preview** - Load your texture atlas and see it above the grid for visual reference
- **Custom Atlas Mode** - Define arbitrary UV rectangles for non-uniform atlases
- **Clear Seams** - Clears existing seams on selected faces before unwrapping (fixes incorrect splits)
- **Auto Seams** - Automatically marks seams on selection boundary
- **Multiple Unwrap Methods** - Angle Based, Conformal
- **UV Relaxation** - Optional post-unwrap relaxation with configurable iterations
- **View Projection** - Projects UVs from current viewport before unwrapping
- **Padding Control** - Configurable padding inside each tile to prevent bleeding
- **Tile Splitting** - Split custom tiles horizontally or vertically
- **Grid-to-Custom** - Generate custom tiles from uniform grid as starting point

## Installation

### Method 1: Single File (Recommended)
1. Open Blender > Edit > Preferences > Add-ons
2. Click "Install..."
3. Select `tile_uv_projector.py`
4. Enable the addon

### Method 2: Folder Installation
1. Copy the `TileUVProjector` folder to your Blender addons directory
2. Restart Blender and enable the addon

## Usage

1. Open the **N-panel** in the 3D Viewport
2. Find the **"Tile UV"** tab
3. Enter **Edit Mode** and select faces
4. Configure grid size, unwrap method, and padding
5. Click a tile button in the grid to project UVs into that tile

### Uniform Grid Mode
- Set columns (X) and rows (Y) for your atlas layout
- Each button in the grid shows its (col, row) coordinate
- Grid is drawn with row 0 at the bottom (matching UV space)

### Custom Atlas Mode
- Toggle "Advanced Grid" to switch modes
- Add tiles manually or generate from uniform grid
- Edit tile UV bounds (Min U/V, Max U/V)
- Split tiles horizontally or vertically for subdivision
- Click "Apply to [tile]" to project into the selected tile

## Settings

| Setting | Description | Default |
|---------|-------------|---------|
| Columns/Rows | Grid dimensions | 4x4 |
| Padding | Inner tile padding (UV space) | 0.005 |
| Proportion W:H | Texture aspect ratio for button sizing | 1:1 |
| Atlas Texture | Image to show as preview above grid | None |
| Clear Seams | Clear existing seams on selection before unwrap | On |
| Auto Seams | Mark seams on selection boundary | On |
| Unwrap Method | Angle Based / Conformal | Angle Based |
| Relax | Post-unwrap relaxation | Off |
| Relax Iterations | Number of relaxation passes | 10 |
| Projection | View / Unwrap Only | View |

## Edge Cases

- **No faces selected** - Operation cancelled with warning
- **Zero-area UV bounds** - Operation cancelled with warning
- **Non-uniform scale** - Warning shown, suggests applying transforms
- **Padding too large** - Error if padding exceeds tile size

## Requirements

- Blender 4.5+
- No external dependencies

## Author

Stephan Viranyi (stephko@viranyi.de)
