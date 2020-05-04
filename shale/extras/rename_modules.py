import argparse
import base64
from pathlib import Path
import re
import time
import uuid

re_module_defn = re.compile(r"module\W+(?P<name>\w+)(?P<body>.*?)endmodule", re.DOTALL)

def main(args):
    args.src = Path(args.src)
    # args.dst = Path(args.dst)

    suffix = "".join(base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip(b'=').decode('ascii').split("-"))

    with open(args.src) as f:
        s = f.read()

        names = {}
        modules = []
        for match in re_module_defn.finditer(s):
            name = match.group('name')

            if name not in args.exclude:
                names[name] = name + suffix

            modules.append(match)

        skip_token = False
        tokens = re.split(r"(\s+)", s)

        for k, token in enumerate(tokens):
            # skip whitespace tokens
            if token.strip() == "":
                continue

            if skip_token:
                skip_token = False
                continue

            if token in names:
                tokens[k] = names[token]
                # If a module instance name is the same as the module
                # name we don't want to rename the instance. This is
                # hacky, a better way would be to parse the Verilog
                # into an AST and actually do things correctly.
                skip_token = True

        print("".join(tokens))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    This is a helper script to rename modules in a Verilog file.
    """)

    parser.add_argument("src", nargs="?", default=".")
    # parser.add_argument("dst", nargs="?", default=".")
    # parser.add_argument("modules", nargs="?", default=".")
    # parser.add_argument("name", nargs="?", default=".")
    parser.add_argument("--exclude", nargs="*", default=[])

    args = parser.parse_args()

    main(args)
