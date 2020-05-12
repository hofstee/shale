from pprint import pprint
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
    "../garnet/global_controller/systemRDL/rdl_models/glc.rdl.final",
    "../garnet/global_buffer/systemRDL/rdl_models/glb.rdl.final",
]

listener = MyListener()
for f in files:
    rdlc.compile_file(f)
    root_node = rdlc.elaborate()
    RDLWalker(unroll=True).walk(root_node, listener)

defs = listener.defs
pprint(defs)
