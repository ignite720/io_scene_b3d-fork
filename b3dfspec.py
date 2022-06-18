import io, math, struct

def eof(f):
    e = f.read(1) == b""
    f.seek(-1, 1)
    return e

class Table(dict):
    def __init__(self, literal={}):
        super().__init__(self)
        self.update(literal)
        self.len = 0

    def append(self, value):
        super().__setitem__(self.len, value)
        self.len += 1

    def __setitem__(self, key, value):
        if isinstance(key, int) and key == self.len:
            self.len = key + 1

        super().__setitem__(key, value)
    
    def __delitem__(self, key):
        if isinstance(key, int) and key < self.len:
            self.len = key

class Type:
    def __init__(self, data, parent):
        self.value = self.read(data, parent)

class Int(Type):
    def read(self, data, parent):
        return int.from_bytes(data.read(4), "little")

class Float(Type):
    def read(self, data, parent):
        return struct.unpack("f", data.read(4))

class String(Type):
    def __init__(self, length):
        self.length = length

    def __call__(self, data, parent):
        self.value = self.read(data, parent)

    def read(self, data, parent):
        return data.read(self.length).decode("utf-8")

class CString(Type):
    def read(self, data, parent):
        return "".join(iter(lambda: data.read(1).decode("utf-8"), "\x00"))

class Array(Type):
    def __init__(self, dtype, length):
        self.dtype = dtype
        self.length = length
    
    def __call__(self, data, parent):
        self.value = self.read(data, parent)

    def read(self, data, parent):
        array = []

        for _ in range(self.length(parent)):
            array.append(self.dtype(data))

        return array

class Vector2(Type):
    def read(self, data, parent):
        self.x = Float(data)
        self.y = Float(data)

class Vector3(Vector2):
    def read(self, data, parent):
        super().read(data)
        self.z = Float(data)

class Quaternion(Vector3):
    def read(self, data, parent):
        super().read(data)
        self.w = Float(data)

class Color(Type):
    def read(self, data, parent):
        self.r = Float(data)
        self.g = Float(data)
        self.b = Float(data)
        self.a = Float(data)

class Repeat:
    def __init__(self, dtype):
        self.dtype = dtype
    
    def __call__(self, data, parent):
        while not eof(data):
            if type(self.dtype) is list:
                l = DList()
                for dtype in self.dtype:
                    dtype(data, l)
                parent.append(l)
            else:
                self.dtype(data, parent)

class Value:
    def __init__(self, key, dtype):
        self.dtype = dtype
        self.key = key
    
    def __call__(self, data, parent):
        parent[self.key] = self.dtype(data, parent)

class If:
    def __init__(self, check, stmt, res):
        self.check = check
        self.stmt = stmt
        self.res = res
    
    def __call__(self, data, parent):
        if self.stmt(check):
            self.res(data, parent)

class Literal:
    def __init__(self, value):
        self.value = value
    
    def __call__(self, parent):
        return self.value

class Key:
    def __init__(self, key):
        self.key = key
    
    def __call__(self, parent):
        return parent[self.key]

class Chunk():
    def __init__(self, data):
        self.tag = String(4)(data, None)
        self.size = Int(data, None)
        self.data = io.BytesIO(data.read(self.size))

class Spec(Chunk):
    def __init__(self, spec):
        self.spec = spec
    
    def read(self, data):
        return self.__call__(data)

    def __call__(self, data):
        super().__init__(self)
        out = Table()
        for dtype in self.spec:
            dtype(self.data, out)

TEXS = Spec([
    Repeat([
        Value("file", CString),
        Value("flags", Int),
        Value("blend", Int),
        Value("pos", Vector2),
        Value("scale", Vector2),
        Value("rotation", Float),
    ])
])

BRUS = Spec([
    Value("n_texs", Int),
    Repeat([
        Value("name", CString),
        Value("color", Color),
        Value("shininess", Float),
        Value("blend", Int),
        Value("fx", Int),
        Value("texture_id", Array(Int, Key("n_texs"))),
    ]),
])

VRTS = Spec([
    Value("flags", Int),
    Value("tex_coord_sets", Int),
    Value("tex_coord_set_size", Int),
    Repeat([
        Value("pos", Vector3),
        Value("normal", Vector3),
        Value("color", Color),
        Value("texture_id", Array(Array(Float, Key("tex_coord_set_size")), Key("tex_coord_sets"))),
    ]),
])

TRIS = Spec([
    Value("brush_id", Int),
    Repeat(Array(Int, Literal(3))),
])

MESH = Spec([
    Value("brush_id", Int),
    Value("vertices", VRTS),
    Value("triangles", Repeat(TRIS)),
])

BONE = Spec([
    Repeat([
        Value("vertex_id", Int),
        Value("weight", Float),
    ]),
])

KEYS = Spec([
    Value("flags", Int),
    Repeat([
        Value("frame", Int),
        If(Key("flags"), lambda a: a & 1, Value("position", Vector3)),
        If(Key("flags"), lambda a: a & 2, Value("scale", Vector3)),
        If(Key("flags"), lambda a: a & 4, Value("rotation", Quaternion)),
    ])
])

ANIM = Spec([
    Value("flags", Int),
    Value("frames", Int),
    Value("fps", Float),
])

def node_fill(data, parent):
    chunk = Chunk(data)
    if chunk.tag == "MESH":
        parent["mesh"] = MESH.read(chunk)
    elif chunk.tag == "BONE":
        parent["bone"] = BONE.read(chunk)
    elif chunk.tag == "KEYS":
        parent["keys"].append(KEYS.read(chunk))
    elif chunk.tag == "NODE":
        parent["children"].append(NODE.read(chunk))
    elif chunk.tag == "ANIM":
        parent["animation"] = ANIM.read(chunk)

NODE = Spec([
    Value("name", CString),
    Value("position", Vector3),
    Value("scale", Vector3),
    Value("rotaiton", Quaternion),
    Value("keys", Array(None, Literal(0))),
    Value("children", Array(None, Literal(0))),
    Repeat(node_fill)
])

def bb3d_fill(data, parent):
    chunk = Chunk(data)
    if chunk.tag == "TEXS":
        parent["textures"].append(TEXS.read(chunk))
    elif chunk.tag == "BRUS":
        parent["textures"].append(BRUS.read(chunk))
    else:
        parent["node"] = NODE.read(chunk)

BB3D = Spec([
    Value("version", Int),
    Value("keys", Array(None, Literal(0))),
    Value("children", Array(None, Literal(0))),
    Repeat(bb3d_fill),
])

f = open("test.b3d", "rb")
b3d = BB3D.read(f)
