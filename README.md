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

To generate VCD or SAIF files using these CSV files as input,

## Troubleshooting

### `AttributeError: Can not find Root Handle (...)`

This is an issue related to cocotb as far as I can tell. If your
`TOPLEVEL` in the Makefile is specified to be a top level design unit,
then try `make clean` and make again to see if that helps. Otherwise,
you may need to modify the Verilog so that the module you want to test
is a top level module in the design (i.e. there are no modules that
instantiate it in any of the files you include in the Makefile).