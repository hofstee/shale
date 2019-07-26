import json
from commands import *

import operator
from functools import reduce
def prod(iterable):
    return reduce(operator.mul, iterable, 1)

def process_inst(inst):
    args = inst['genargs']

    num_bits = args['width'][1]
    num_elems = args['depth'][1]
    if num_bits != 16:
        raise NotImplementedError("Non 16-bit inputs are not supported.")

    for k,v in args.items():
        print(k, v)

    dims = []
    for k in range(args['dimensionality'][1]):
        stride = args[f"stride_{k}"][1]
        length = args[f"range_{k}"][1]
        dims.append((length, stride))

    return {
        "addr": None,
        "location": 0,
        "dims": dims,
        "size": num_inputs,
        "nbytes": (num_bits // 8) * num_inputs,
    }


# app = "handcrafted_ub_conv_3_3"
app = "handcrafted_ub_layer_gb"

with open(app + ".json", "r") as f:
    js = json.load(f)
    with open(app + ".map.json", "r") as f2:
        mapping = json.load(f2)

    print(mapping['inputs'])
    print(mapping['outputs'])

    instances = js['namespaces']['global']['modules']['DesignTop']['instances']

    inputs = []
    for i in mapping['inputs']:
        inst = instances[i['instance']]
        inputs.append(process_inst(inst))

    outputs = []
    for o in mapping['outputs']:
        inst = instances[o['instance']]
        outputs.append(process_inst(inst))

    # TODO: go through everything and figure out sizes to place in the global buffer

    # gb_input = instances['gb_input']
    # gb_args = gb_input['genargs']

    # num_bits = gb_args['width'][1]
    # num_inputs = gb_args['depth'][1]
    # if num_bits != 16:
    #     raise NotImplementedError("Non 16-bit inputs are not supported.")

    # for k,v in gb_args.items():
    #     print(k, v)

    # # TODO: what is iter_cnt

    # dims = []
    # for k in range(gb_args['dimensionality'][1]):
    #     stride = gb_args[f"stride_{k}"][1]
    #     length = gb_args[f"range_{k}"][1]
    #     dims.append((length, stride))

    # TODO: need to get location from gb_args
    # TODO: need to calculate inputs and outputs reserved space
    # TODO: support for double buffering
    # TODO: addressing for double buffering
    # TODO: allocate into global buffer regions
    # TODO: which input ports are these going to?
    # TODO: is the input expected to be every single cycle?
    inputs = []
    inputs.append({
        "addr": BANK_ADDR(0),
        "location": 0,
        "size": num_inputs,
        "nbytes": (num_bits // 8) * num_inputs,
    })

    outputs = []
    outputs.append({
        "addr": BANK_ADDR(16),
        "location": 1,
        "size": prod([ x[0] for x in dims ]),
        "nbytes": (num_bits // 8) * prod([ x[0] for x in dims ]),
    })

    print(inputs)
    print(outputs)
    print(dims)

    print([
        # WRITE_REG(GLOBAL_RESET_REG, 1), # TODO: delete?
        # Stall the CGRA
        WRITE_REG(STALL_REG, 0b1111),

        # Enable interrupts
        WRITE_REG(INTERRUPT_ENABLE_REG, 0b11),

        # Configure the CGRA
        PRINT("Configuring CGRA..."),
        # *gc_config_bitstream(self.bitstream),
        *gb_config_bitstream(self.bitstream, width=self.args.width),
        PRINT("Done."),

        # Set up global buffer for pointwise
        *configure_io(
            IO_INPUT_STREAM,
            inputs[0]["addr"],
            inputs[0]["size"],
            io_ctrl=inputs[0]["location"],
            width=self.args.width
        ),
        *configure_io(
            IO_OUTPUT_STREAM,
            outputs[0]["addr"],
            outputs[0]["size"],
            io_ctrl=outputs[0]["location"],
            width=self.args.width
        ),

        # Put image into global buffer
        PRINT("Transferring input data..."),
        WRITE_DATA(BANK_ADDR(0), 0xc0ffee, im.nbytes, im),
        PRINT("Done."),

        # Start the application
        PRINT("Starting application..."),
        WRITE_REG(STALL_REG, 0),
        PEND(0b01, "start"),
        WRITE_REG(CGRA_START_REG, 1),
        PRINT("Waiting for completion..."),
        WAIT(0b01, "start"),
        PRINT("Done."),

        PRINT("Reading output data..."),
        READ_DATA(
            BANK_ADDR(16),
            gold.nbytes,
            gold,
            _file=self.outfile,
        ),
        PRINT("All tasks complete!"),
    ])
