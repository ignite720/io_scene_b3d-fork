import struct, mathutils

class Table(dict):
    def __init__(self, literal={}):
        super().__init__(self)
        self.update(literal)
        self._len = 0

    def append(self, value):
        super().__setitem__(self._len, value)
        self._len += 1
    
    def __len__(self):
        return self._len

    def __setitem__(self, key, value):
        if isinstance(key, int) and key == self._len:
            self._len = key + 1

        super().__setitem__(key, value)
    
    def __delitem__(self, key):
        if isinstance(key, int) and key < self._len:
            self._len = key

# class Table:
#     def __init__(self):
#         self.hash = {}
#         self.array = []
    
#     def append(self, value):
#         self.array.append(value)
    
#     def __getitem__(self, key):
#         if isinstance(key, int):
#             return self.array.__getitem__(key)
#         else:
#             return self.hash.__getitem__(key)

#     def __setitem__(self, key, value):
#         if isinstance(key, int):
#             return self.array.__setitem__(key, value)
#         else:
#             return self.hash.__setitem__(key,  value)
    
#     def __delitem__(self, key):
#         if not isinstance(key, int):
#             return self.hash.__delitem__(self, key)

def Int(data):
    return int.from_bytes(data.read(4), "little")

def Float(data):
    return struct.unpack("f", data.read(4))[0]

def String(data, length):
    return data.read(length).decode("utf-8")

def CString(data):
    return "".join(iter(lambda: data.read(1).decode("utf-8"), "\x00"))

def Array(t, length, *data):
    array = []

    for _ in range(length):
        array.append(t(*data))

    return array

class Vector2:
    def __init__(self, data):
        self.x = Float(data)
        self.y = Float(data)
    
    @property
    def array(self):
        return [self.x, self.y]
    
    @property
    def Vec(self):
        return mathutils.Vector((self.x, self.y))

class Vector3(Vector2):
    def __init__(self, data):
        super().__init__(data)
        self.z = Float(data)
    
    @property
    def array(self):
        return [self.x, self.y, self.z]

    @property
    def Vec(self):
        return mathutils.Vector((self.x, self.y, self.z))

class Quaternion(Vector3):
    def __init__(self, data):
        self.w = Float(data)
        super().__init__(data)
    
    @property
    def array(self):
        return [self.w, self.x, self.y, self.z]
    
    @property
    def Quat(self):
        return mathutils.Quaternion((self.w, self.x, self.y, self.z))

class Color:
    def __init__(self, data):
        self.r = Float(data)
        self.g = Float(data)
        self.b = Float(data)
        self.a = Float(data)
