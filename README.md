# shale
[![Actions Status](https://github.com/thofstee/shale/workflows/Python%20package/badge.svg)](https://github.com/thofstee/shale/actions)

## Setup Instructions
```
git clone --recurse-submodules git@github.com:THofstee/shale.git
pip install -r deps/garnet/requirements.txt
pip install --ignore-installed deps/jmapper-0.1.19-cp37-cp37m-manylinux1_x86_64.whl
pip install -e .
cp /cad/cadence/GENUS17.21.000.lnx86/share/synth/lib/chipware/sim/verilog/CW/CW_tap.v extras/CW_tap.v
```

## Usage Instructions
```
python run.py --width 32 --height 16 conv_3_3
cd apps/conv_3_3/test

# Pick one of the following (VCS tends to run the quickest):
make SIM=vcs
make SIM=ius
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

### Creating a `map.json` for your application

As an example, the `map.json` for conv_3_3 looks like this:

```
{
    "inputs": [
        {
            "name": "input",
            "instance": "gb_input",
            "location": "0",
            "num_active": "64",
            "num_inactive": "0",
            "file": "conv_3_3_input.raw",
            "trace": "in.trace"
        }
    ],
    "outputs": [
        {
            "name": "output",
            "instance": "gb_output",
            "location": "1",
            "file": "conv_3_3_gold.raw",
            "trace": "out.trace"
        }
    ],
    "trace": [
        "add_290_294_295",
        "mul_249_251_252",
        "linebuffer_bank_0_0"
    ]
}
```

At the top level, the `map.json` contains three entires: `inputs`,
`outputs`, and `trace`.

#### Inputs and Outputs

The inputs and outputs are both lists of json
records that have at the very least a `name`, `instance`, `location`,
and `file`.

- `name` is just a name for the stream. Pick whatever makes sense to
  you.

- `instance` corresponds to the instance name that holds the unified
  buffer parameters for this stream in `bin/global_buffer.json`.

- `location` decides which I/O port of the CGRA this stream is
  connected to. TODO: this feature could be automated with some
  effort.

- `file` is a filename that holds the data that should be loaded into
  the global buffer during testing. Currently the files are expected
  to be binary data where every byte is a new input element. These are
  zero-padded to 16-bits by the testbench as the CGRA operates on
  16-bit data.

- `trace` will configure the testbench to log the data when it is
valid to the filename given.

Additionally you can specify `num_active` and `num_inactive` on the
inputs. These can occasionally be automatically detected by the
testbench, but there are quirks with the current implementation. TODO:
fix the implementation.

- `num_active` specifies how many cycles of the *inner loop* should be
  sent at a time. It is *very important* that this is less than or
  equal to the range of the inner loop or else the testbench will not
  function properly.

- `num_inactive` specifies how many cycles the inputs should be paused
  between active inputs. If you want no inactive cycles, just set this
  to 0.

As an example, `range=16, num_active=4, num_inactive=4` will send 4
elements, wait 4 cycles, and repeat this three more times for a total
of 32 cycles to send the 16 elements. After these 32 cycles it will
then increment the next dimension of the loop if one exists.

#### Tracing application signals

The `trace` field is a list of signals from the `design_top.json` that
should be monitored during application execution. By default they are
saved to `{signal_name}.csv`. These are used when generating tile
power reports to provide the input stimulus for a testbench. This is
done because generating power information on the entire Garnet design
is very time consuming, so if you just need power information for a
specific tile in the CGRA it is much faster to just simulate the
tile. More information can be found in the section in this readme
about 'Generating Tile Power Reports'.

### Generating Tile Power Reports (SAIF/VCD)

#### VCS

There are two ways to go about generating SAIF or VCD files
using the CSV files generated above. These make use of secondary
testbenches, and unfortunately many of the flags we need are
compile-time flags for VCS, so make sure you `make clean` first.

We'll need to specify `TOPLEVEL` in order for this all to
work. Additionally, we'll change the `TESTCASE` to be `test_tile`
instead.

To dump a VCD file, we can add `+vcs+dumpvars+{filename}.vpd` to
COMPILE_ARGS, and specify the CSV file we want to use with
`TRACE="{filename}.csv"`. If you just want a plain VCD file, change
the extension on dumpvars to `.vcd` instead.

An example of such a command is as follows:

```
make SIM=vcs TESTCASE="test_tile" COMPILE_ARGS="+vcs+dumpvars+test.vpd" TOPLEVEL="Tile_MemCore" TRACE="linebuffer_bank_0_0.csv"
```

Alternatively, running the same command without the
`vcs+dumpvars+test.vpd` (or with, doesn't matter) will create a
`test.tcl` file in the test directory, which is a script that can be
used to get a SAIF file. To use this tcl script, we need to run make
again, but this time adding `SIM_ARGS="-ucli"` to the command, which
will bring up the ucli prompt in VCS. Then we can just `source
test.tcl`, which will generate a SAIF file named `test.saif`.

```
make SIM=vcs TESTCASE="test_tile" SIM_ARGS="-ucli" TOPLEVEL="Tile_MemCore" TRACE="linebuffer_bank_0_0.csv"
```

Using this method to generate a SAIF file, you should have run make a
total of 3 times. Once to generate the CSV, once to generate the TCL
file, and a final time to generate the SAIF file.

#### Incisive/Xcelium (NCSim)

Please read the VCS section first to get a general idea for the flow,
then come back here. First thing to note is that unlike VCS, you do
not need to `make clean` beforhand. Like in the VCS case, you'll need
to run the tile level testbench first to generate some tcl scripts for
reporting power information.

An example of a command is as follows:

```
make SIM=xcelium TESTCASE="test_tile" TOPLEVEL="Tile_PE" TRACE="add_290_294_295.csv"
```

Then you can run one of the tcl scripts as input to get a SAIF file
out.

```
make SIM=xcelium TESTCASE="test_tile" TOPLEVEL="Tile_PE" TRACE="add_290_294_295.csv" SIM_ARGS="-input xrun_power_Tile_PE.tcl"
```

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
