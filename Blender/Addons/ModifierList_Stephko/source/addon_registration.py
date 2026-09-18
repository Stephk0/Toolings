"""Utility module for registering classes and properties"""

import importlib
import inspect
import os
import sys
import types

from bpy.types import bpy_struct, WorkSpaceTool
from bpy.utils import register_class, unregister_class
from typing import Optional, Iterable
import bpy
from .modules.icons import load_icons
from bpy.app.handlers import persistent

imported_modules: list[types.ModuleType] = []
sorted_classes = []

@persistent
def load_icons_after_loading_file(dummy):
    import functools
    bpy.app.timers.register(functools.partial(load_icons), first_interval=2.0)
    # second time to be sure, sometimes the first time is not enoght!
    bpy.app.timers.register(functools.partial(load_icons), first_interval=12.0)

# Finding and importing modules
# ======================================================================

def _find_modules(root_dir: str) -> set[str]:
    """Finds all modules in the given directory and returns them in a
    set.

    The form of the returned modules is 'relative.path.module'.

    Directories whose name contains "__" are ignored.
    """
    current_directory = os.path.dirname(__file__)
    #print("current_directory", current_directory)
    root_directory = os.path.join(current_directory, root_dir)
    #print("root_directory", root_directory)

    if not os.path.exists(root_directory):
        raise FileNotFoundError("root_dir doesn't exist")

    modules: set[str] = set()

    for root, dirs, files in os.walk(root_directory):
        dirs[:] = [d for d in dirs if "__" not in d]
        #print("dirs", dirs)
        relative_root = os.path.relpath(root, current_directory)
        #print("relative_root", relative_root)
        for f in files:
            if f.endswith(".py") and "__" not in f:
                joined = os.path.join(relative_root, f[:-3])
                modules.add(joined.replace(os.path.sep, "."))
        #print("modules", modules)
    return modules


def _import_modules(modules: set[str]) -> list[types.ModuleType]:
    """Imports or reloads the given modules and returns them in a list.

    Modules must contain their relative paths.
    """
    if imported_modules:
        for mod in imported_modules:
            try:
                sys.modules.pop(mod.__name__)
            except KeyError:
                pass
    #print("modules import", modules)
    return [importlib.import_module("." + mod, package=__package__) for mod in modules]


def _store_modules(modules: list[types.ModuleType]) -> None:
    """Puts the given modules into a global 'imported_modules' list"""
    global imported_modules
    imported_modules.clear()
    imported_modules = modules
    #print("imported_modules_store", imported_modules)


# Finding and sorting classes
# ======================================================================

def _find_bl_classes(modules):
    """Finds all add-on classes (excluding subclasses of WorkSpaceTool)
    in the given modules and returns them in a list.

    Modules must contain their relative paths.
    """
    bl_classes = []
    #print("modules", modules)
    #print("bl_classes", bl_classes)

    cur_dir_path = os.path.dirname(__file__)
    #print("cur_dir_path", cur_dir_path)
    cur_dir_basename = os.path.basename(cur_dir_path)
    #print("cur_dir_basename", cur_dir_basename)

    for mod in modules:
        full_module_path = mod.__file__
        #print("full_module_path", full_module_path)
        module_path_from_cur_dir = full_module_path.replace(cur_dir_path, cur_dir_basename)
        #print("module_path_from_cur_dir", module_path_from_cur_dir)
        formatted_module_path = module_path_from_cur_dir.replace(os.path.sep, ".")[:-3]
        #print("formatted_module_path", formatted_module_path)
        #print("formatted_module_path", formatted_module_path)
        class_members = [m[1] for m in inspect.getmembers(mod, inspect.isclass)]

        #remove the classmember if its not in formatted_module_path since __module__ does not seem to work in 4.2 with manifest the way it was writen before, but works with legacy bl
        # I love debugging for hours :D
        class_members = [cm for cm in class_members if formatted_module_path in cm.__module__]

        #print("class_members", class_members)
        bpy_subclasses = [cm for cm in class_members if issubclass(cm, bpy_struct) and
                          not issubclass(cm, WorkSpaceTool)]
        #print("bpy_subclasses", bpy_subclasses)
        bl_classes.extend(bpy_subclasses)
        #print("bl_classes", bl_classes)

    #print("all bl_classes", bl_classes)
    return bl_classes


def _sort_classes_topologically(classes):
    """Sorts classes based on their hierarchy."""
    unsorted_classes = classes[:]
    sorted_classes_from_bottom = []

    safety_counter = 0

    while unsorted_classes:
        for cls in unsorted_classes:
            if not [c for c in cls.__subclasses__() if c in unsorted_classes]:
                sorted_classes_from_bottom.append(cls)
                unsorted_classes.remove(cls)

        safety_counter += 1
        assert safety_counter < 10000, "Infinite loop in_sort_classes_topologically"

    return list(reversed(sorted_classes_from_bottom))


def _sort_panel_classes(classes, panel_order):
    """Sorts the panel classes in the given classes iteratable and
    returns a new list in which they are at the end.

    classes: an iteratable of classes
    panel_order: an iteratable of panel class names
    """
    other_classes = [cls for cls in classes if cls.__name__ not in panel_order]
    panel_classes = [cls for panel in panel_order for cls in classes if cls.__name__ == panel]
    return other_classes + panel_classes


def _store_classes(modules):
    global sorted_classes
    sorted_classes.clear()
    sorted_classes = modules


def _sort_modules(module_order: list[str]) -> list[types.ModuleType]:
    modules_to_be_sorted: list[types.ModuleType] = []
    unsorted_modules: list[types.ModuleType] = []

    for mod in imported_modules:
        if mod.__name__.split(".")[-1] in module_order:
            modules_to_be_sorted.append(mod)
        else:
            unsorted_modules.append(mod)

    sorted_modules = sorted(modules_to_be_sorted,
                            key=lambda mod: module_order.index(mod.__name__.split(".")[-1]))

    return sorted_modules + unsorted_modules


# Registering classes
# ======================================================================

def _register_classes(classes, addon_name_for_counter=None):
    """Registers all add-on classes that inherit from bpy_struct from
    all modules."""
    for cls in classes:
        register_class(cls)

    if addon_name_for_counter:
        print(f"{addon_name_for_counter}: Registered {str(len(classes))} classes")


# Public functions
# ======================================================================

def import_modules(root_dir):
    """Imports all modules in the given directory in order to make them
    available for other functions in addon_registration.
    """
    modules = _find_modules(root_dir)
    modules = _import_modules(modules)
    _store_modules(modules)


def register_bl_classes(modules_to_ignore=None, classes_to_ignore=None, panel_order=None,
                        addon_name_for_counter=None):
    """Registers all add-on classes that inherit from bpy_struct from
    all modules.

    import_modules needs to be called before this.

    Args:
        modules_to_ignore: an iteratable of the names of the
            moduless that should be ignored
        classes_to_ignore: an iteratable of the names of the
            classes that should be ignored
        panel_order: an iteratable of panel class names
        addon_name_for_counter: The name of the addon. If given, the
            number of the registered classes is printed out.

    Modules and packages that have "__" in their name are ignored.

    If you have panel classes, panel_order is needed because the order
    of panels in Blender's UI is defined by the order they are
    registered in.
    """
    if modules_to_ignore:
        modules = [m for m in imported_modules
                   if m.__name__.split(".")[-1] not in modules_to_ignore]
    else:
        modules = imported_modules

    classes = _find_bl_classes(modules)
    classes = _sort_classes_topologically(classes)

    if classes_to_ignore:
        classes = [cls for cls in classes if cls.__name__.split(".")[-1] not in classes_to_ignore]

    if panel_order:
        classes = _sort_panel_classes(classes, panel_order)

    _store_classes(classes)
    _register_classes(classes, addon_name_for_counter)


def unregister_bl_classes(addon_name_for_counter=None):
    """Unregisters all add-on classes.

    Args:
        addon_name_for_counter: The name of the addon. If given, the
            number of the unregistered classes is printed out.
    """
    classes = list(reversed(sorted_classes))

    for cls in classes:
        unregister_class(cls)

    if addon_name_for_counter:
        print(f"{addon_name_for_counter}: Unregistered {str(len(classes))} classes")


# Calling (un)register

def call_register(module_order=None):
    """Calls register of all add-on modules.

    Args:
        module_order: list of module names. Register functions in
            modules in the list are called before other modules
            register.

    import_modules must have been called before this.
    """
    modules = _sort_modules(module_order) if module_order else imported_modules

    for mod in modules:
        if hasattr(mod, "register"):
            mod.register()

    # needed since sometimes it fails to properly load the icons in some files due to a Blender bug! This is a workaround
    bpy.app.handlers.load_post.append(load_icons_after_loading_file)


def call_unregister(module_order: Optional[list[str]] = None) -> None:
    """Calls unregister of all add-on modules.

    Args:
        module_order: list of module names. Unregister functions in
            modules in the list are called before other modules
            unregister.
    """
    modules = _sort_modules(module_order) if module_order else imported_modules

    for mod in modules:
        if hasattr(mod, "unregister"):
            mod.unregister()

    bpy.app.handlers.load_post.remove(load_icons_after_loading_file)
    