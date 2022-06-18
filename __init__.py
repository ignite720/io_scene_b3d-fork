bl_info = {
    "name": "Blitz3D Import-Export",
    "blender": (2, 80, 0),
    "category": "Import-Export",
}

import bpy
import os
import sys
from bpy_extras.io_utils import ExportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

import importlib

from io_scene_b3d.b3d_read import *
importlib.reload(b3d_read)
from .b3d_read import *

class ImportB3D(Operator):
    """Load a Blitz3D file."""
    bl_idname = "io_scene_b3d.import_b3d"
    bl_label = "Import Blitz3D"

    def execute(self, context):
        import_node(context)
        return {"FINISHED"}

class ExportB3D(Operator, ExportHelper):
    """Save a Blitz3D file."""
    bl_idname = "io_scene_b3d.export_b3d"
    bl_label = "Export Blitz3D"

    filename_ext = ".b3d"
    filter_glob: StringProperty(default="*.b3d", options={"HIDDEN"}, maxlen=255)

    use_selected: BoolProperty(
        name="Selection Only",
        description="Export selected objects only",
        default=True,
    )

    def execute(self, context):
        from . import export_b3d
        return export_b3d.save(context, self.filepath, self.use_selected)

def menu_func_export(self, context):
    self.layout.operator(ExportB3D.bl_idname, text="Blitz3D (.b3d)")

def menu_func_import(self, context):
    self.layout.operator(ImportB3D.bl_idname, text="Blitz3D (.b3d)")

def register():
    bpy.utils.register_class(ExportB3D)
    bpy.utils.register_class(ImportB3D)
    bpy.types.TOPBAR_MT_file_export.append(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.append(menu_func_import)

def unregister():
    bpy.utils.unregister_class(ExportB3D)
    bpy.utils.unregister_class(ImportB3D)
    bpy.types.TOPBAR_MT_file_export.remove(menu_func_export)
    bpy.types.TOPBAR_MT_file_import.remove(menu_func_import)

if __name__ == "__main__":
    register()
