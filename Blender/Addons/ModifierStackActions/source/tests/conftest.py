import os
import sys

# Make `core` importable as a top-level package without importing the addon
# __init__ (which needs bpy).
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
