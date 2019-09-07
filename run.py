# make SIM=vcs COMPILE_ARGS="-LDFLAGS -Wl,--no-as-needed"
# LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 make SIM=ius

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("apps", nargs="*")
parser.add_argument("--width", type=int, default=32)
parser.add_argument("--height", type=int, default=16)
parser.add_argument("--force", action="store_true")
parser.add_argument("--skip-garnet", action="store_true")
parser.add_argument("--app-root", type=str, default="apps")
args = parser.parse_args()

cwd = os.getcwd()
git_up_to_date = re.compile(r"Already up-to-date.")

if len(args.apps) == 0:
    for entry in os.scandir(f"{args.app_root}"):
        if entry.is_dir():
            args.apps.append(entry.name)

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
    else:
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

    garnet_sv = Path("extras/garnet.sv")
    if not (garnet_sv.is_symlink() or garnet_sv.is_file()):
        os.symlink(f"{cwd}/deps/garnet/garnet.v", garnet_sv)

def generate_makefile():
    with open("extras/Makefile", "w") as f:
        f.write(f"""
VERILOG_SOURCES = \\
    {cwd}/deps/garnet/tests/AO22D0BWP16P90.sv \\
    {cwd}/deps/garnet/tests/AN2D0BWP16P90.sv \\
    {cwd}/deps/garnet/global_buffer/genesis/TS1N16FFCLLSBLVTC2048X64M8SW.sv \\
    {cwd}/deps/garnet/peak_core/DW_fp_add.v \\
    {cwd}/deps/garnet/peak_core/DW_fp_mult.v \\
    {cwd}/deps/garnet/genesis_verif/memory_core.sv \\
    {cwd}/deps/garnet/genesis_verif/mem_unq1.v \\
    {cwd}/deps/garnet/genesis_verif/sram_stub_unq1.v \\
    {cwd}/deps/garnet/genesis_verif/doublebuffer_control_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/sram_control_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/fifo_control_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/linebuffer_control_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/global_buffer.sv \\
    {cwd}/deps/garnet/genesis_verif/global_buffer_int.sv \\
    {cwd}/deps/garnet/genesis_verif/memory_bank.sv \\
    {cwd}/deps/garnet/genesis_verif/bank_controller.sv \\
    {cwd}/deps/garnet/genesis_verif/glbuf_memory_core.sv \\
    {cwd}/deps/garnet/genesis_verif/cfg_controller.sv \\
    {cwd}/deps/garnet/genesis_verif/cfg_address_generator.sv \\
    {cwd}/deps/garnet/genesis_verif/sram_controller.sv \\
    {cwd}/deps/garnet/genesis_verif/memory.sv \\
    {cwd}/deps/garnet/genesis_verif/io_controller.sv \\
    {cwd}/deps/garnet/genesis_verif/io_address_generator.sv \\
    {cwd}/deps/garnet/genesis_verif/sram_gen.sv \\
    {cwd}/deps/garnet/genesis_verif/host_bank_interconnect.sv \\
    {cwd}/deps/garnet/genesis_verif/global_controller.sv \\
    {cwd}/deps/garnet/genesis_verif/axi_ctrl_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/jtag_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/cfg_and_dbg_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/flop_unq3.sv \\
    {cwd}/deps/garnet/genesis_verif/flop_unq2.sv \\
    {cwd}/deps/garnet/genesis_verif/flop_unq1.sv \\
    {cwd}/deps/garnet/genesis_verif/tap_unq1.sv \\
    {cwd}/extras/CW_tap.v \\
    {cwd}/extras/garnet.sv \\
    {cwd}/extras/garnet_top.sv

TESTCASE?=test_app
TOPLEVEL?=Garnet_TB
TOPLEVEL_LANG=verilog
MODULE=tb

include $(shell cocotb-config --makefiles)/Makefile.inc
include $(shell cocotb-config --makefiles)/Makefile.sim
""")


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
                "--width", f"{args.width}",
            ],
        )

        if os.path.islink(f"{args.app_root}/{app}/test/Makefile"):
            os.remove(f"{args.app_root}/{app}/test/Makefile")

        if not os.path.exists(f"{args.app_root}/{app}/test/Makefile"):
            os.symlink(f"{cwd}/extras/Makefile", f"{args.app_root}/{app}/test/Makefile")


if not args.skip_garnet:
    generate_garnet()

generate_makefile()
generate_bitstreams()
generate_testbenches()
