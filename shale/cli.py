import argparse
import os
from pathlib import Path
from .util.cocotb import generate_makefile

# Functionality
# - generate testbenches from collateral
# - run them
# - capture runtime traces on io ports of a tile
# - do power analysis on the results
# - might just assume that aha commands exist
# - should the run them thing just be in aha?

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--garnet", default=os.environ.get("GARNET_HOME"))
    parser.add_argument("-s", "--simulator", default="incisive")
    args = parser.parse_args()

    if not args.garnet:
        raise Exception("Couldn't find garnet. Please specify '--garnet' or set $GARNET_HOME in your environment")

    args.garnet = Path(args.garnet).resolve()
    generate_makefile(args.garnet)

    if args.simulator == "incisive":
        "LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6"
