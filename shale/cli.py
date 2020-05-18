import argparse
import copy
import os
from pathlib import Path
import shutil
import subprocess
from .util.cocotb import generate_makefile

# Functionality
# - generate testbenches from collateral
# - run them
# - log vcd files if necessary
# - capture runtime traces on io ports of a tile
# - do power analysis on the results
# - might just assume that aha commands exist
# - should the run them thing just be in aha?

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--garnet", default=os.environ.get("GARNET_HOME"))
    parser.add_argument("-s", "--simulator", default="incisive")
    parser.add_argument("-t", "--test", default="test_standalone")
    parser.add_argument("--dump-vcd", action="store_true")
    args = parser.parse_args()

    if not args.garnet:
        raise Exception("Couldn't find garnet. Please specify '--garnet' or set $GARNET_HOME in your environment")

    args.garnet = Path(args.garnet).resolve()
    generate_makefile(args.garnet, test=args.test)

    if not os.path.exists("shale/extras/garnet.sv"):
        os.symlink(
            args.garnet / "garnet.v",
            "shale/extras/garnet.sv"
        )
    if not os.path.exists("shale/extras/glc.rdl"):
        os.symlink(
            args.garnet / "global_controller/systemRDL/rdl_models/glc.rdl.final",
            "shale/extras/glc.rdl"
        )
    if not os.path.exists("shale/extras/glb.rdl"):
        os.symlink(
            args.garnet / "global_buffer/systemRDL/rdl_models/glb.rdl.final",
            "shale/extras/glb.rdl"
        )

    shutil.copy2("shale/extras/Makefile", "tests/Makefile")

    if args.simulator == "incisive":
        env = copy.copy(os.environ)
        env["LD_PRELOAD"] = "/usr/lib/x86_64-linux-gnu/libstdc++.so.6"

        tcl_commands = [
            "database -open -vcd vcddb -into test.vcd -default -timescale ps",
            "probe -create -all -vcd -depth all",
            "run",
            "quit",
        ]

        command = [
            "make", "SIM=ius",
        ]

        if args.dump_vcd:
            with open("tests/commands.tcl", "w") as f:
                f.write("\n".join(tcl_commands))
            command += ["EXTRA_ARGS='-input commands.tcl'"]

        subprocess.run(
            command,
            cwd="tests",
            env=env,
            text=True,
        )
    elif args.simulator == "vcs":
        subprocess.run(
            [
                "make", "SIM=vcs",
            ],
            cwd="tests",
            text=True,
        )
