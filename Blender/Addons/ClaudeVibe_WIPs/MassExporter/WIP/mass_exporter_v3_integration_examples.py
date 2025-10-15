# Mass Exporter v3 Integration Example
# This shows how to integrate the parent empty fix into your existing export workflow

import bpy

# Load the parent empty handler
exec(open(r'D:\BlenderAIDabbings\ClaudeTooling\mass_exporter_v3_complete_fix.py').read())

def enhanced_mass_export_workflow():
    """
    Enhanced mass export workflow with automatic parent empty handling
    Replace your existing export function with this pattern
    """
    
    print("=== ENHANCED MASS EXPORT v3 WORKFLOW ===")
    
    try:
        # STEP 1: Prepare parent empties for export
        print("Step 1: Preparing parent empties...")
        if not start_mass_export():
            print("Failed to prepare empties - aborting export")
            return False
        
        # STEP 2: Your existing export logic goes here
        print("Step 2: Performing export operations...")
        
        # Example export operations (replace with your actual export code):
        export_success = True
        
        """
        # Your existing export code would go here, for example:
        
        # Select objects to export
        bpy.ops.object.select_all(action='DESELECT')
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH':
                obj.select_set(True)
        
        # Export to FBX
        bpy.ops.export_scene.fbx(
            filepath="your_export_path.fbx",
            use_selection=True,
            global_scale=1.0
        )
        
        # Or export to OBJ
        bpy.ops.export_scene.obj(
            filepath="your_export_path.obj",
            use_selection=True,
            global_scale=1.0
        )
        
        export_success = True
        """
        
        print("   → Export operations completed successfully")
        
        # STEP 3: Always restore empties afterward (even if export failed)
        print("Step 3: Restoring parent empties...")
        end_mass_export()
        
        if export_success:
            print("✓ Enhanced mass export completed successfully!")
        else:
            print("⚠ Export completed with warnings")
            
        return export_success
        
    except Exception as e:
        print(f"Error during export: {e}")
        
        # Make sure to restore empties even if something goes wrong
        print("Attempting to restore empties after error...")
        try:
            end_mass_export()
        except:
            print("Could not restore empties - manual intervention may be needed")
            reset_mass_export()
        
        return False

def quick_export_fix():
    """
    Quick one-liner to fix parent empty issues before manual export
    Use this if you want to manually handle the export but fix the empties first
    """
    start_mass_export()
    print("Parent empties moved to center - perform your export now")
    print("Run end_mass_export() when done to restore positions")

def batch_export_multiple_objects():
    """
    Example of batch exporting multiple objects with parent empty fix
    """
    
    # Get all objects to export (example: all mesh objects)
    objects_to_export = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    if not objects_to_export:
        print("No objects to export")
        return
    
    # Start the parent empty fix session
    start_mass_export()
    
    try:
        for obj in objects_to_export:
            # Select only this object
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj
            
            # Export this object (example with FBX)
            filepath = f"D:\\exports\\{obj.name}.fbx"
            print(f"Exporting {obj.name} to {filepath}")
            
            """
            bpy.ops.export_scene.fbx(
                filepath=filepath,
                use_selection=True,
                global_scale=1.0
            )
            """
            
        print(f"Batch export of {len(objects_to_export)} objects completed")
        
    finally:
        # Always restore empties
        end_mass_export()

if __name__ == "__main__":
    print("Mass Exporter v3 Integration Examples Loaded")
    print("\nAvailable functions:")
    print("  enhanced_mass_export_workflow() - Complete export with auto parent empty fix")
    print("  quick_export_fix() - Just fix empties for manual export")
    print("  batch_export_multiple_objects() - Batch export example")
    
    # Uncomment to run examples:
    # enhanced_mass_export_workflow()
    # quick_export_fix()
    # batch_export_multiple_objects()
