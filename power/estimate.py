import argparse
import itertools
import os
import pandas as pd

from power.tile import get_active_tiles, group_tiles_by_op, get_tile_ops

from tabulate import tabulate
import textwrap

def print_power(groups, name=None):
    if name is not None:
        print(name)

    data = list(groups.items()) + [("total", sum(groups.values()))]
    print(textwrap.indent(tabulate(data, tablefmt="plain", floatfmt=".3e"), "  "))

power = {
    "ic_base": 40e-6,
    "ic_track": 4e-6,
    "ic_reg": 14e-6,
    "pe_base": 50.1e-6, # TODO: double check
    "pe_active": 400e-6, # TODO: double check
    "mem_base": 0,
    "mem_clock": 300e-6, # TODO: depending on how gating happens could be less
    "mem_srams": 1.656e-3,
    "mem_ctrl_fifo": 86e-6,
    "mem_ctrl_lbuf": 25e-6,
    "mem_ctrl_dbuf": 140e-6, # TODO: these registers are huge
    "mem_ctrl_sram": 19e-6,
    "mem_other": 150e-6,
    "reg16": 14e-6,
}

pull_power = {
    "other": (power["ic_base"]
              + 2 * power["ic_track"] # addr lines
              + 2 * power["ic_track"] # data lines
              ),
    "sram": (power["mem_base"]
             + power["mem_srams"]
              # + power["mem_clock"] # This was for the registers mainly...?
             + power["mem_other"]),
    # And we also burn a PE tile in the pull configuration
    "pe": (power["pe_base"]
           + power["pe_active"]
           + 6 * power["reg16"] # extra stride registers
           + 6 * power["reg16"] # extra range registers
           + power["mem_clock"] / 4 # clock tree will be in PE?
           ),
}

push_power = {
    "other": (power["ic_base"]
              + 2 * power["ic_track"] # data lines
              ),
    "sram": (power["mem_base"]
             + power["mem_srams"]
             + power["mem_other"]),
    "controllers": (power["mem_clock"]
                    + power["mem_ctrl_fifo"]
                    + power["mem_ctrl_lbuf"]
                    + power["mem_ctrl_dbuf"]
                    + power["mem_ctrl_sram"])
}

lb_power = {
    "other": (power["ic_base"]
              + 2 * power["ic_track"] # data lines
              ),
    "sram": (power["mem_base"]
             + power["mem_srams"]
             + power["mem_other"]),
    "controllers": (power["mem_clock"]
                    + power["mem_ctrl_lbuf"])
}

lbdb_power = {
    "other": (power["ic_base"]
              + 2 * power["ic_track"] # data lines
              ),
    "sram": (power["mem_base"]
             + power["mem_srams"]
             + power["mem_other"]),
    "controllers": (power["mem_clock"]
                    + power["mem_ctrl_fifo"]
                    + power["mem_ctrl_lbuf"]
                    + power["mem_ctrl_dbuf"]
                    + power["mem_ctrl_sram"])
}

ub_power = {
    "other": (power["ic_base"]
              + 2 * power["ic_track"] # data lines
              ),
    "sram": (power["mem_base"]
             + power["mem_srams"]
             + power["mem_other"]),
    "controllers": (power["mem_clock"]
                    + power["mem_ctrl_dbuf"]
                    + power["mem_ctrl_sram"])
}

print_power(pull_power, "pull")
print_power(push_power, "push")

print_power(lb_power, "LB")
print_power(lbdb_power, "LB-DB")
print_power(ub_power, "UB")

def ic_power(num_active_tracks=0, num_passthrough_regs=0):
    return (power["ic_base"]
            + num_active_tracks * power["ic_track"]
            + num_passthrough_regs * power["ic_reg"])

# TODO: build model
def pe_power(active=False):
    return (power["pe_base"]
            + (power["pe_active"] if active else 0))

def mem_power(active=False):
    return (power["mem_base"]
            + power["mem_clock"]
            + (power["mem_srams"] if active else 0)
            + power["mem_ctrl_fifo"]
            + power["mem_ctrl_lbuf"]
            + power["mem_ctrl_dbuf"]
            + power["mem_ctrl_sram"]
            + power["mem_other"])

# print(f"ic_power        {ic_power(1, 1):.3e}W")
# print(f"pe_power        {pe_power(True):.3e}W")
# print(f"mem_power       {mem_power(True):.3e}W")

# print(f"total_power     {mem_power(True) + ic_power(1, 1):.3e}W")

# print(f"total_power  {total_power:.3e}W")


def analyze_app(app, *, width=32, height=16):
    active_tiles = get_active_tiles(f"{app}/bin/design.route")
    tile_ops = get_tile_ops(f"{app}/bin/mapped.json", f"{app}/bin/design.place")
    tile_ops = {tile: tile_ops.get(tile, "passthrough") for tile in active_tiles}
    tile_ops = {tile: tile_ops.get(tile, "inactive") for tile in itertools.product(range(width), range(1,height+1))}
    tile_metadata = {tile: {"op": tile_ops[tile]} for tile in tile_ops}

    for x,y in tile_ops:
        if y == 0:
            tile_metadata[(x,y)]["type"] = "io"
        elif x%4 == 3:
            tile_metadata[(x,y)]["type"]  = "mem"
        else:
            tile_metadata[(x,y)]["type"]  = "pe"


    power = {}
    categories = {
        "interconnect": 0,
        "pe": 0,
        "mem": 0,
    }
    for tile, metadata in tile_metadata.items():
        power[tile] = 0
        is_active = not metadata["op"] in ["passthrough", "inactive"]

        # TODO: get better interconnect numbers
        power[tile] += ic_power(1, 0)
        categories["interconnect"] += ic_power(1, 0)

        if metadata["type"] == "pe":
            power[tile] += pe_power(is_active)
            categories["pe"] += pe_power(is_active)
        elif metadata["type"] == "mem":
            power[tile] += mem_power(is_active)
            categories["mem"] += mem_power(is_active)
        else:
            raise NotImplementedError(tile, metadata)
        # print(tile)

    print(app, f"{sum(power.values()):.3e}W")
    print(categories)
    return power, categories


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("app", type=str)
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--height", type=int, default=16)
    args = parser.parse_args()

    analyze_app(args.app,
                width=args.width,
                height=args.height)
