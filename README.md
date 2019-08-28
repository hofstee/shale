# shale
[![Actions Status](https://github.com/thofstee/shale/workflows/Python%20package/badge.svg)](https://github.com/thofstee/shale/actions)
pip install astor numpy genesis2 pycoreir
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

