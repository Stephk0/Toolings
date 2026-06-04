#!/usr/bin/env python3
"""
Blender MCP Server
Enables Claude AI to control Blender through the Model Context Protocol

Author: Stephan Viranyi (Stephko)
Date: 2025-12-03
Version: 1.0

This server allows Claude to:
- Execute Python scripts in Blender
- Adjust tree generator parameters
- Create scenes and objects
- Render and capture screenshots
- Read Blender scene information
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Optional
import xmlrpc.client
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp import types

# Server instance
app = Server("blender-mcp")

# Blender RPC connection (will be established when Blender addon is running)
BLENDER_RPC_URL = "http://localhost:8765"
blender_proxy: Optional[xmlrpc.client.ServerProxy] = None


def get_blender_connection():
    """Get or create connection to Blender RPC server"""
    global blender_proxy

    if blender_proxy is None:
        try:
            blender_proxy = xmlrpc.client.ServerProxy(BLENDER_RPC_URL, allow_none=True)
            # Test connection
            blender_proxy.ping()
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to Blender. Please ensure:\n"
                f"1. Blender is running\n"
                f"2. MCP addon is installed and enabled\n"
                f"3. RPC server is started\n"
                f"Error: {str(e)}"
            )

    return blender_proxy


@app.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available Blender tools"""

    return [
        types.Tool(
            name="blender_execute_script",
            description="Execute arbitrary Python code in Blender",
            inputSchema={
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Python code to execute in Blender (uses bpy API)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what the script does"
                    }
                },
                "required": ["script"]
            }
        ),
        types.Tool(
            name="blender_tree_create",
            description="Create a procedural tree using the tree generator",
            inputSchema={
                "type": "object",
                "properties": {
                    "base_thickness": {
                        "type": "number",
                        "description": "Trunk radius (0.01-2.0m, default: 0.1)",
                        "minimum": 0.01,
                        "maximum": 2.0
                    },
                    "branch_length": {
                        "type": "number",
                        "description": "Branch length (0.1-10.0m, default: 1.0)",
                        "minimum": 0.1,
                        "maximum": 10.0
                    },
                    "iterations": {
                        "type": "integer",
                        "description": "Branch subdivision levels (0-10, default: 2)",
                        "minimum": 0,
                        "maximum": 10
                    },
                    "random_seed": {
                        "type": "integer",
                        "description": "Seed for randomness (0-999999, default: 0)",
                        "minimum": 0,
                        "maximum": 999999
                    },
                    "angular_spread": {
                        "type": "number",
                        "description": "Branch randomness (0.0-1.0, default: 0.3)",
                        "minimum": 0.0,
                        "maximum": 1.0
                    },
                    "name": {
                        "type": "string",
                        "description": "Name for the tree object",
                        "default": "ProceduralTree"
                    }
                }
            }
        ),
        types.Tool(
            name="blender_tree_adjust",
            description="Adjust parameters of an existing tree",
            inputSchema={
                "type": "object",
                "properties": {
                    "tree_name": {
                        "type": "string",
                        "description": "Name of the tree object to modify"
                    },
                    "parameter": {
                        "type": "string",
                        "description": "Parameter to adjust",
                        "enum": ["base_thickness", "branch_length", "iterations", "random_seed", "angular_spread"]
                    },
                    "value": {
                        "type": "number",
                        "description": "New value for the parameter"
                    }
                },
                "required": ["tree_name", "parameter", "value"]
            }
        ),
        types.Tool(
            name="blender_render_viewport",
            description="Render the current viewport and save as image",
            inputSchema={
                "type": "object",
                "properties": {
                    "output_path": {
                        "type": "string",
                        "description": "Path to save the rendered image (PNG format)"
                    },
                    "width": {
                        "type": "integer",
                        "description": "Image width in pixels (default: 1920)",
                        "default": 1920
                    },
                    "height": {
                        "type": "integer",
                        "description": "Image height in pixels (default: 1080)",
                        "default": 1080
                    }
                },
                "required": ["output_path"]
            }
        ),
        types.Tool(
            name="blender_get_scene_info",
            description="Get information about the current Blender scene",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_objects": {
                        "type": "boolean",
                        "description": "Include list of objects in scene",
                        "default": True
                    },
                    "include_materials": {
                        "type": "boolean",
                        "description": "Include list of materials",
                        "default": False
                    }
                }
            }
        ),
        types.Tool(
            name="blender_setup_test_scene",
            description="Create a clean test scene with camera and lighting",
            inputSchema={
                "type": "object",
                "properties": {
                    "scene_type": {
                        "type": "string",
                        "description": "Type of scene to create",
                        "enum": ["basic", "tree_showcase", "forest"],
                        "default": "basic"
                    }
                }
            }
        ),
        types.Tool(
            name="blender_export_object",
            description="Export an object to various formats",
            inputSchema={
                "type": "object",
                "properties": {
                    "object_name": {
                        "type": "string",
                        "description": "Name of object to export"
                    },
                    "output_path": {
                        "type": "string",
                        "description": "Path for exported file"
                    },
                    "format": {
                        "type": "string",
                        "description": "Export format",
                        "enum": ["fbx", "obj", "gltf", "dae"],
                        "default": "fbx"
                    }
                },
                "required": ["object_name", "output_path"]
            }
        )
    ]


@app.call_tool()
async def handle_call_tool(
    name: str, arguments: dict[str, Any] | None
) -> list[types.TextContent]:
    """Handle tool execution"""

    try:
        blender = get_blender_connection()
    except ConnectionError as e:
        return [types.TextContent(
            type="text",
            text=f"Error: {str(e)}"
        )]

    try:
        if name == "blender_execute_script":
            script = arguments.get("script", "")
            description = arguments.get("description", "Executing script...")

            result = blender.execute_script(script)

            return [types.TextContent(
                type="text",
                text=f"✓ {description}\n\nResult:\n{result}"
            )]

        elif name == "blender_tree_create":
            # Create tree with parameters
            params = {
                "base_thickness": arguments.get("base_thickness", 0.1),
                "branch_length": arguments.get("branch_length", 1.0),
                "iterations": arguments.get("iterations", 2),
                "random_seed": arguments.get("random_seed", 0),
                "angular_spread": arguments.get("angular_spread", 0.3),
                "name": arguments.get("name", "ProceduralTree")
            }

            result = blender.create_tree(params)

            return [types.TextContent(
                type="text",
                text=f"✓ Created tree: {params['name']}\n\n{result}"
            )]

        elif name == "blender_tree_adjust":
            tree_name = arguments.get("tree_name")
            parameter = arguments.get("parameter")
            value = arguments.get("value")

            result = blender.adjust_tree_parameter(tree_name, parameter, value)

            return [types.TextContent(
                type="text",
                text=f"✓ Adjusted {parameter} to {value} on {tree_name}\n\n{result}"
            )]

        elif name == "blender_render_viewport":
            output_path = arguments.get("output_path")
            width = arguments.get("width", 1920)
            height = arguments.get("height", 1080)

            result = blender.render_viewport(output_path, width, height)

            return [types.TextContent(
                type="text",
                text=f"✓ Rendered viewport to: {output_path}\n\n{result}"
            )]

        elif name == "blender_get_scene_info":
            include_objects = arguments.get("include_objects", True)
            include_materials = arguments.get("include_materials", False)

            info = blender.get_scene_info(include_objects, include_materials)

            return [types.TextContent(
                type="text",
                text=f"Scene Information:\n\n{json.dumps(info, indent=2)}"
            )]

        elif name == "blender_setup_test_scene":
            scene_type = arguments.get("scene_type", "basic")

            result = blender.setup_test_scene(scene_type)

            return [types.TextContent(
                type="text",
                text=f"✓ Created {scene_type} test scene\n\n{result}"
            )]

        elif name == "blender_export_object":
            object_name = arguments.get("object_name")
            output_path = arguments.get("output_path")
            format_type = arguments.get("format", "fbx")

            result = blender.export_object(object_name, output_path, format_type)

            return [types.TextContent(
                type="text",
                text=f"✓ Exported {object_name} to {output_path}\n\n{result}"
            )]

        else:
            return [types.TextContent(
                type="text",
                text=f"Unknown tool: {name}"
            )]

    except Exception as e:
        return [types.TextContent(
            type="text",
            text=f"Error executing {name}: {str(e)}"
        )]


async def main():
    """Main server entry point"""

    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="blender-mcp",
                server_version="1.0.0",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )


if __name__ == "__main__":
    asyncio.run(main())
