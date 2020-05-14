# from pprint import pprint
import subprocess
from systemrdl import RDLCompiler, RDLWalker, RDLListener
import tempfile

rdlc = RDLCompiler()

# class Field:
#     def write(self, value):
#         pass

#     def read(self, value):
#         pass

# class Register:
#     def __init__(self, fields):
#         self.fields = {field.name: field for field in field}
#         for field in fields:
#             self.fields[field] = Field()

#     def __getattr__(self, k):
#         return self.fields[k]

#     def write(self, value):
#         pass

#     def read(self, value):
#         pass

# r = Register(["cgra_stall", "glb_stall"])
# print(r.write(0))
# assert False

class MyListener(RDLListener):
    def __init__(self):
        self.defs = {}

    def enter_AddressableComponent(self, node):
        self.defs[node.get_path()] = node.absolute_address

    # def enter_Addrmap(self, node):
    #     print("Entering addrmap", node.get_path())

    # def exit_Addrmap(self, node):
    #     print("Exiting addrmap", node.get_path())

    # def enter_Reg(self, node):
    #     print("Entering register", node.get_path())

    # def exit_Reg(self, node):
    #     print("Exiting register", node.get_path())

    # def enter_Field(self, node):
    #     print("Entering field", node.get_path())

    # def exit_Field(self, node):
    #     print("Exiting field", node.get_path())


# subprocess.check_call(
#     [
#         "make", "rdl",
#     ],
#     chdir=
# )

files = [
    "/aha/garnet/global_controller/systemRDL/rdl_models/glc.rdl.final",
    "/aha/garnet/global_buffer/systemRDL/rdl_models/glb.rdl.final",
]

listener = MyListener()
for f in files:
    rdlc.compile_file(f)
    root_node = rdlc.elaborate()
    RDLWalker(unroll=True).walk(root_node, listener)

defs = listener.defs

def format_def(d):
    return d.upper().replace(".", "_")

def gen_c_header():
    header = []
    glc_defs = [d for d in defs if d.startswith("glc.")]
    glb_defs = [d for d in defs if d.startswith("glb.")]

    header += [
        "#pragma once",
    ]

    for glc_def in glc_defs:
        header.append(f"#define {format_def(glc_def)} {hex(defs[glc_def])}")

    for tile in range(16):
        for glb_def in glb_defs:
            header.append(f"#define GLB_TILE{tile}_{format_def(glb_def)[4:]} {hex(defs[glb_def] | tile << 8)}")

    return "\n".join(header)
