# VERILOG_SOURCES = \
#     $(PWD)/AO22D0BWP16P90.sv \
#     $(PWD)/AN2D0BWP16P90.sv \
#     $(PWD)/memory_core.sv \
#     $(PWD)/mem_unq1.v \
#     $(PWD)/sram_stub_unq1.v \
#     $(PWD)/doublebuffer_control_unq1.sv \
#     $(PWD)/sram_control_unq1.sv \
#     $(PWD)/fifo_control_unq1.sv \
#     $(PWD)/linebuffer_control_unq1.sv \
#     $(PWD)/global_buffer.sv \
#     $(PWD)/global_buffer_int.sv \
#     $(PWD)/memory_bank.sv \
#     $(PWD)/bank_controller.sv \
#     $(PWD)/glbuf_memory_core.sv \
#     $(PWD)/cfg_controller.sv \
#     $(PWD)/cfg_address_generator.sv \
#     $(PWD)/sram_controller.sv \
#     $(PWD)/memory.sv \
#     $(PWD)/io_controller.sv \
#     $(PWD)/io_address_generator.sv \
#     $(PWD)/sram_gen.sv \
#     $(PWD)/TS1N16FFCLLSBLVTC2048X64M8SW.sv \
#     $(PWD)/host_bank_interconnect.sv \
#     $(PWD)/global_controller.sv \
#     $(PWD)/DW_fp_add.v \
#     $(PWD)/DW_fp_mult.v \
#     $(PWD)/axi_ctrl_unq1.sv \
#     $(PWD)/jtag_unq1.sv \
#     $(PWD)/cfg_and_dbg_unq1.sv \
#     $(PWD)/flop_unq3.sv \
#     $(PWD)/flop_unq2.sv \
#     $(PWD)/flop_unq1.sv \
#     $(PWD)/tap_unq1.sv \
#     $(PWD)/CW_tap.v

# TOPLEVEL=garnet  # the module name in your Verilog or VHDL file
# MODULE=tb  # the name of the Python test file

# include $(shell cocotb-config --makefiles)/Makefile.inc
# include $(shell cocotb-config --makefiles)/Makefile.sim

import argparse
import re
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("apps", nargs="*")
parser.add_argument("--width", type=int, default=32)
parser.add_argument("--height", type=int, default=16)
parser.add_argument("--force", action="store_true")
parser.add_argument("--skip-garnet", action="store_true")
args = parser.parse_args()

git_up_to_date = re.compile(r"Already up-to-date.")

def generate_garnet():
    subprocess.run(
        [
            "git",
            "checkout",
            "flow",
        ],
        cwd="deps/garnet",
        stdout=subprocess.PIPE,
        text=True,
    )

    p = subprocess.run(
        [
            "git",
            "pull",
        ],
        cwd="deps/garnet",
        stdout=subprocess.PIPE,
        text=True,
    )

    if p.returncode:
        print(f"WARN: Couldn't fetch latest updates.", file=sys.stderr)
        up_to_date = True
    else:
        up_to_date = git_up_to_date.search(p.stdout)

    if args.force:
        up_to_date = False

    if up_to_date:
        print(f"INFO: `garnet.v` is already up to date.")
        return

    print(f"INFO: Generating `garnet.v`...")
    subprocess.run(
        [
            "python",
            "garnet.py",
            "--width", f"{args.width}",
            "--height", f"{args.height}",
            "--verilog",
        ],
        cwd="deps/garnet",
        stdout=subprocess.PIPE,
        text=True,
    )

def generate_bitstreams():
    subprocess.run(
        [
            "git",
            "checkout",
            "simple_mapper",
        ],
        cwd="deps/garnet",
        stdout=subprocess.PIPE,
        text=True,
    )

    p = subprocess.run(
        [
            "git",
            "pull",
        ],
        cwd="deps/garnet",
        stdout=subprocess.PIPE,
        text=True,
    )

    if p.returncode:
        print(f"WARN: Couldn't fetch latest updates.", file=sys.stderr)
        up_to_date = True
    else:
        up_to_date = git_up_to_date.search(p.stdout)

    if args.force:
        up_to_date = False

    gen_bitstream_args = [
        "--width", f"{args.width}",
        "--height", f"{args.height}",
        *args.apps,
    ]

    if not up_to_date:
        gen_bitstream_args.append("--force")

    subprocess.run(
        [
            "python",
            "generate-bitstreams.py",
            *gen_bitstream_args,
        ],
    )

def generate_testbenches():
    for app in args.apps:
        subprocess.run(
            [
                "python",
                "test.py",
                app,
            ],
        )


if not args.skip_garnet:
    generate_garnet()

generate_bitstreams()
