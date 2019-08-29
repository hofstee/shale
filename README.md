# shale
[![Actions Status](https://github.com/thofstee/shale/workflows/Python%20package/badge.svg)](https://github.com/thofstee/shale/actions)

## Setup Instructions
```
git clone --recurse-submodules git@github.com:THofstee/shale.git
pip install -r deps/garnet/requirements.txt
pip install --ignore-installed deps/jmapper-0.1.19-cp37-cp37m-manylinux1_x86_64.whl
pip install astor numpy genesis2 pycoreir cocotb
cp /cad/cadence/GENUS17.21.000.lnx86/share/synth/lib/chipware/sim/verilog/CW/CW_tap.v extras/CW_tap.v
```

## Usage Instructions
```
python run.py --width 32 --height 16 conv_3_3
cd apps/conv_3_3/test

# Pick one of the following (VCS tends to run the quickest):
make SIM=vcs COMPILE_ARGS="-LDFLAGS -Wl,--no-as-needed"
LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6 make SIM=ius
make SIM=xcelium

# You can also modify COMPILE_ARGS and SIM_ARGS as you see fit.
# Adding SIM_ARGS="-ucli" or SIM_ARGS="-gui" to the VCS example are
# some of the more useful choices.

# To verify outputs, run this command:
python test.py --verify-trace conv_3_3
```

If you specified any signals to be traced in the CoreIR
`design_top.json` for an application, these will be output to
`{signal_name}.csv` in the test directory of the application.

### Generating Tile Power Reports (SAIF/VCD)

#### VCS

There are two ways to go about generating SAIF or VCD files
using the CSV files generated above. These make use of secondary
testbenches, and unfortunately many of the flags we need are
compile-time flags for VCS, so make sure you `make clean` first.

We'll need to specify `TOPLEVEL` and add `-top` to `COMPILE_ARGS` in
order for this all to work. Additionally, we'll change the `TESTCASE`
to be `test_tile` instead.

To dump a VCD file, we can add `+vcs+dumpvars+{filename}.vpd` to
COMPILE_ARGS, and specify the CSV file we want to use with
`TRACE="{filename}.csv"`. If you just want a plain VCD file, change
the extension on dumpvars to `.vcd` instead.

An example of such a command is as follows:

```
make SIM=vcs TESTCASE="test_tile" COMPILE_ARGS="-LDFLAGS -Wl,--no-as-needed +vcs+dumpvars+test.vpd -top Tile_MemCore" TOPLEVEL="Tile_MemCore" TRACE="linebuffer_bank_0_0.csv"
```

Alternatively, running the same command without the
`vcs+dumpvars+test.vpd` (or with, doesn't matter) will create a
`test.tcl` file in the test directory, which is a script that can be
used to get a SAIF file. To use this tcl script, we need to run make
again, but this time adding `SIM_ARGS="-ucli"` to the command, which
will bring up the ucli prompt in VCS. Then we can just `source
test.tcl`, which will generate a SAIF file named `test.saif`.

```
make SIM=vcs TESTCASE="test_tile" COMPILE_ARGS="-LDFLAGS -Wl,--no-as-needed -top Tile_MemCore" SIM_ARGS="-ucli" TOPLEVEL="Tile_MemCore" TRACE="linebuffer_bank_0_0.csv"
```

Using this method to generate a SAIF file, you should have run make a
total of 3 times. Once to generate the CSV, once to generate the TCL
file, and a final time to generate the SAIF file.

## Known Issues

### Timescale using VCS

For whatever reason, it seems like the timescale reported by VCS is
not in the correct units. Please be cautious if using anything that
relies on the timescale to be accurate. I believe Incisive does not
have this issue.

## Troubleshooting

### Something isn't working

`make clean` and try again. If that doesn't work, file an issue or
contact me.

### `AttributeError: Can not find Root Handle (...)`

This is an issue related to cocotb as far as I can tell. If your
`TOPLEVEL` in the Makefile is specified to be a top level design unit,
then try `make clean` and make again to see if that helps. Otherwise,
you may need to modify the Verilog so that the module you want to test
is a top level module in the design (i.e. there are no modules that
instantiate it in any of the files you include in the Makefile).