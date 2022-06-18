import io, math
from .types import *

def eof(f):
    e = f.read(1) == b""
    f.seek(-1, 1)
    return e

class Chunk():
    def __init__(self, data):
        self.tag = String(data, 4)
        self.size = Int(data)
        self.data = io.BytesIO(data.read(self.size))

class TEXS(Chunk):
    def read(self):
        textures = []

        while not eof(self.data):
            textures.append({
                "file": CString(self.data),
                "flags": Int(self.data), "blend": Int(self.data),
                "pos": Vector2(self.data),
                "scale": Vector2(self.data),
                "rotation": Float(self.data),
            })
        return textures

class BRUS(Chunk):
    def read(self):
        brushes = Table({
            "n_texs": Int(self.data),
        })

        while not eof(self.data):
            brushes.append({
                "name": CString(self.data),
                "color": Color(self.data),
                "shininess": Float(self.data),
                "blend": Int(self.data), "fx": Int(self.data),
                "texture_id": Array(Int, brushes["n_texs"], self.data),
            })

        return brushes

class VRTS(Chunk):
    def read(self):
        vertices = Table({
            "flags": Int(self.data),
            "tex_coord_sets": Int(self.data),
            "tex_coord_set_size": Int(self.data),
        })

        has_normal = vertices["flags"] % 2 == 1 or None
        has_color = math.floor(vertices["flags"] / 2) % 2 == 1 or None

        while not eof(self.data):
            vertices.append({
                "pos": Vector3(self.data),
                "normal": has_normal and Vector3(self.data),
                "color": has_color and Color(self.data),
                "tex_coords": Array(Array, vertices["tex_coord_sets"], Float, vertices["tex_coord_set_size"], self.data),
            })
        
        return vertices
        
class TRIS(Chunk):
    def read(self):
        tris = Table({
            "brush_id": Int(self.data),
        })

        while not eof(self.data):
            tris.append(Array(Int, 3, self.data))
        
        return tris

class MESH(Chunk):
    def read(self):
        mesh = {
            "brush_id": Int(self.data),
            "vertices": VRTS(self.data).read(),
            "triangles": [],
        }

        while True:
            mesh["triangles"].append(TRIS(self.data).read())

            if eof(self.data):
                break
        
        return mesh

class BONE(Chunk):
    def read(self):
        bone = []

        while not eof(self.data):
            bone.append({
                "vertex_id": Int(self.data),
                # TODO: Ignore zero weights
                "weight": Float(self.data),
            })

        return bone

class KEYS(Chunk):
    def read(self):
        keys = Table({
            "flags": Int(self.data),
        })

        while not eof(self.data):
            frame = {
                "frame": Int(self.data)
            }

            if keys["flags"] & 1:
                frame["position"] = Vector3(self.data)
            
            if keys["flags"] & 2:
                frame["scale"] = Vector3(self.data)

            if keys["flags"] & 4:
                frame["rotation"] = Quaternion(self.data)
            
            keys.append(frame)

        # TODO: Sort bones
        return keys

class ANIM(Chunk):
    def read(self):
        return {
            "flags": Int(self.data),
            "frames": Int(self.data),
            "fps": Float(self.data),
        }

class NODE(Chunk):
    def read(self):
        node = {
            "name": CString(self.data),
            "position": Vector3(self.data),
            "scale": Vector3(self.data),
            "rotation": Quaternion(self.data),
            "keys": [],
            "children": [],
        }
        print(node["name"], math.floor(node["position"].x * 100) / 100, math.floor(node["position"].y * 100) / 100, math.floor(node["position"].z * 100) / 100)

        while not eof(self.data):
            chunk = Chunk(self.data)
            if chunk.tag == "MESH":
                node["mesh"] = MESH.read(chunk)
            elif chunk.tag == "BONE":
                node["bone"] = BONE.read(chunk)
            elif chunk.tag == "KEYS":
                node["keys"].append(KEYS.read(chunk))
            elif chunk.tag == "NODE":
                node["children"].append(NODE.read(chunk))
            elif chunk.tag == "ANIM":
                node["animation"] = ANIM.read(chunk)

        # TODO: Merge duplicate keys
        return node

class BB3D(Chunk):
    def read(self):
        version = Int(self.data)
        bb3d = {
            "version": [math.floor(version / 100), version % 100],
            "textures": [],
            "brushes": [],
        }

        while not eof(self.data):
            chunk = Chunk(self.data)
            if chunk.tag == "TEXS":
                bb3d["textures"].append(TEXS.read(chunk))
            elif chunk.tag == "BRUS":
                bb3d["textures"].append(BRUS.read(chunk))
            else:
                bb3d["node"] = NODE.read(chunk)
        
        return bb3d

import os
import bpy
import bmesh
from mathutils import Vector
from mathutils import Quaternion as Quat

class Reader:
    def __init__(self, path):
        file = open(path, "rb")
        self.b3d = BB3D(file).read()
        file.close()

        self.name = self.b3d["node"]["name"]
        
    def read_nodes(self, node, parent=None):
        if "mesh" in node:
            bm = bmesh.new()
            
            src = node["mesh"]
            svrts = src["vertices"]
            stris = src["triangles"]

            # Vertexes
            for i in range(len(svrts)):
                v = svrts[i]["pos"]
                bm.verts.new((v.x, v.z, v.y))
                bm.verts.ensure_lookup_table()

            # Triangles
            for triset in stris:
                for i in range(len(triset)):
                    s = triset[i]
                    bm.faces.new((bm.verts[s[0]], bm.verts[s[1]], bm.verts[s[2]]))

            # Mesh
            self.mesh = bpy.data.meshes.new(node["name"])
            self.mesh_obj = bpy.data.objects.new(node["name"], self.mesh)
            bpy.context.collection.objects.link(self.mesh_obj)

            self.mesh_obj.select_set(True)

            bm.to_mesh(self.mesh)
            bm.free()  
        elif "bone" in node:
            if not hasattr(self, "armature"):
                self.armature = bpy.data.armatures.new(self.name + "_Armature")
                self.armature_obj = bpy.data.objects.new(self.name + "_Armature", self.armature)
                self.armature_obj.show_in_front = True
                bpy.context.collection.objects.link(self.armature_obj)

                mod = bpy.data.objects[self.mesh_obj.name].modifiers.new(name="", type="ARMATURE")
                mod.object = self.armature_obj

                self.mesh_obj.parent = self.armature_obj
            
            bpy.context.view_layer.objects.active = self.armature_obj            
            bpy.ops.object.mode_set(mode="EDIT", toggle=False)

            bone = self.armature.edit_bones.new(node["name"])
            bp, br = node["position"], node["rotation"]
            bpos, brot = Vector((-bp.x, bp.z, bp.y)), Quat((br.w, br.x, br.y, br.z))

            # if parent is not None:
            #     bpos.x -= parent["position"].x
            #     bpos.y += parent["position"].y
            #     bpos.z += parent["position"].z
            # bone.head = node["position"].as_bpy()
            
            # print(math.floor(bpos.x * 100) / 1000, math.floor( bpos.y * 100) / 1000, math.floor(bpos.z * 100) / 1000)
            # bone.head = (-bpos.x, bpos.z, bpos.y)
            # bone.tail = (bone.head[0], bone.head[1], bone.head[2] + 1)
            
            bone.head = bpos
            bpos.rotate(brot)
            bone.tail = bpos
            bone.length = 1
            # bone.roll = 0
            bone.use_deform = True

            # bone.align_roll((0, 1, 0))
            # bone.use_relative_parent = True
            # bone.use_inherit_rotation = True
            # bone.use_local_location = True

            if (parent is not None) and "bone" in parent:
                bone.parent = self.armature.edit_bones[parent["name"]]

            vgroup = self.mesh_obj.vertex_groups.new(name=node["name"])
            for data in node["bone"]:
                if data["weight"] > 0:
                    vgroup.add([data["vertex_id"]], data["weight"], "ADD")
            
            # if "keys" in node:
            #     bpy.ops.object.mode_set(mode="POSE", toggle=False)

            #     pose = self.armature_obj.pose.bones[node["name"]]
                
            #     for keyset in node["keys"]:
            #         for i in range(len(keyset)):
            #             key = keyset[i]
            #             if "position" in key:
            #                 kpos = key["position"]
            #                 # if parent is not None:
            #                 #     kpos.x -= parent["position"].x
            #                 #     kpos.y += parent["position"].y
            #                 #     kpos.z += parent["position"].z
                            
            #                 pose.location = (-kpos.x, kpos.z, kpos.y)
            #                 pose.keyframe_insert("location", frame=key["frame"])

            #             if "rotation" in key:
            #                 krot = key["rotation"]
            #                 pose.rotation_quaternion = (krot.w, -krot.x, krot.z, krot.y)
            #                 pose.keyframe_insert("rotation_quaternion", frame=key["frame"])

            #             if "scale" in key:
            #                 kscale = key["scale"]
            #                 pose.scale = (kscale.x, kscale.y, kscale.z)
            #                 pose.keyframe_insert("scale", frame=key["frame"])

            bpy.ops.object.mode_set(mode="OBJECT", toggle=False)
            bpy.ops.object.select_all(action="DESELECT")
            bpy.context.view_layer.objects.active = self.mesh_obj

        else:
            raise ValueError("Invalid node type")

        if "children" in node:
            for child in node["children"]:
                self.read_nodes(child, node)

def import_node(context):
    # b3d = BB3D(f).read()
    # f.close()
    # node = b3d["node"]

    reader = Reader("test.b3d")
    reader.read_nodes(reader.b3d["node"])

    # if node["mesh"]:
    #     bm = bmesh.new()
        
    #     #
    #     src = node["mesh"]
    #     svrts = src["vertices"]
    #     stris = src["triangles"]

    #     # Vertexes
    #     for i in range(len(svrts)):
    #         v = svrts[i]["pos"]
    #         bm.verts.new((v.x, v.y, v.z))
    #         bm.verts.ensure_lookup_table()

    #     # Triangles
    #     for triset in stris:
    #         for i in range(len(triset)):
    #             s = triset[i]
    #             bm.faces.new((bm.verts[s[0]], bm.verts[s[1]], bm.verts[s[2]]))

    #     # Mesh
    #     mesh = bpy.data.meshes.new(node["name"])
    #     mesh_obj = bpy.data.objects.new(node["name"], mesh)
    #     bpy.context.collection.objects.link(mesh_obj)

    #     mesh_obj.select_set(True)

    #     bm.to_mesh(mesh)
    #     bm.free()

    #     # Armature
    #     arm = bpy.data.armatures.new(node["name"] + "_Armature")
    #     arm_obj = bpy.data.objects.new(node["name"] + "_Armature", arm)
    #     bpy.context.collection.objects.link(arm_obj)

    #     context.view_layer.objects.active = arm_obj
    #     bpy.ops.object.mode_set(mode="EDIT", toggle=False)

    #     # Vertex groups
    #     vgroup = mesh_obj.vertex_groups.new(name="Bone")
    #     vgroup.add([i for i in range(16)], 1.0, "ADD")

    #     # TODO: Make vertex group using all vertexes in B3D BONE
    #     bone = arm.edit_bones.new("Bone")
    #     bone.head = (0, 0, 0)
    #     bone.tail = (0, 0, 1)
    #     bone.use_deform = True

    #     bpy.ops.object.mode_set(mode="POSE", toggle=False)

    #     pose = arm_obj.pose.bones["Bone"]
        
    #     pose.location = (0, 0, 5)
    #     pose.scale = (2, 2, 2)
    #     pose.rotation_quaternion = (1.0, 1.0, 1.0, 0)
    #     pose.keyframe_insert("location", frame=10)
    #     pose.keyframe_insert("scale", frame=10)
    #     pose.keyframe_insert("rotation_quaternion", frame=10)

    #     pose.location = (0, 0, 0)
    #     pose.scale = (1, 1, 1)
    #     pose.rotation_quaternion = (1.0, 0, 0, 0)
    #     pose.keyframe_insert("location", frame=1)
    #     pose.keyframe_insert("scale", frame=1)
    #     pose.keyframe_insert("rotation_quaternion", frame=1)

    #     bpy.ops.object.mode_set(mode="OBJECT", toggle=False)

    #     # TODO: Modifier
    #     mod = bpy.data.objects[mesh_obj.name].modifiers.new(name="", type="ARMATURE")
    #     mod.object = arm_obj

    #     bpy.ops.object.select_all(action="DESELECT")
    #     context.view_layer.objects.active = mesh_obj
        
    #     # bpy.ops.object.modifier_add(type="ARMATURE")
    #     # print(bpy.ops.object.modifiers)
    #     # bpy.ops.object.modifiers.active.object = arm_obj

    #     mesh_obj.parent = arm_obj



    #     # for child in node["children"]:
    #     #     import_node(child, bm)

# import_node(b3d["node"])
