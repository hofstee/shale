# TODO: flatten nested dimensions that still have linear access
# TODO: handle multidimensional outputs

import csv
import json
from commands import *
from pprint import pprint

import ast
import astor
import textwrap

import argparse

def new_code_context():
    return ast.Module()

def gather_input_ports(modulename):
    with open("deps/garnet/garnet.v") as f:
        verilog = f.read()
        match = re.search(f"(module {modulename} \([^)]*\);)", verilog)
        module_signature = verilog[match.start():match.end()]

        return map(
            lambda x: x.rsplit(' ', 1)[-1].rstrip(","),
            re.findall("input (.*)", module_signature)
        )

mem_tile_inputs = list(gather_input_ports("Tile_MemCore"))
pe_tile_inputs = list(gather_input_ports("Tile_PE"))

def gen_monitor(module, portlist, name=None):
    if name is None:
        name = module

    temp = create_function(f"monitor_{name}")
    temp.decorator_list.append(ast.Attribute(
        value=ast.Name(id='cocotb'),
        attr='coroutine',
    ))

    node = parse_ast(f"""
    with open("{name}.log", "w") as f:
       while True:
           yield RisingEdge(dut.clk)
           yield ReadOnly()
    """).body[0]

    ctx = node.body[0].body

    for port in portlist:
        ctx.append(parse_ast(f"""
            try:
                f.write(f"{{int({module}.{port})}}, ")
            except:
                f.write(", ")
        """).body[0])

    temp.body.append(node)

    return temp

def parse_ast(s):
    return ast.parse(textwrap.dedent(s))

def print_ast(tree):
    print(astor.to_source(tree))

def parse_placement(placement_file):
    if len(placement_file) == 0:
        return {}, {}
    with open(placement_file) as f:
        lines = f.readlines()
    lines = lines[2:]
    placement = {}
    name_to_id = {}
    for line in lines:
        raw_line = line.split()
        assert (len(raw_line) == 4)
        blk_name = raw_line[0].split('$')[0]
        x = int(raw_line[1])
        y = int(raw_line[2])
        blk_id = raw_line[-1][1:]
        placement[blk_id] = (x, y)
        name_to_id[blk_name] = blk_id
    return placement, name_to_id

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
        "size": num_elems,
        "nbytes": (num_bits // 8) * num_elems,
    }


parser = argparse.ArgumentParser(description="""
A simple SoC stub to test application flow of the CGRA.
""")

parser.add_argument('--verify-trace', action='store_true')
args = parser.parse_args()

# app = "apps/handcrafted_ub_conv_3_3"
# app = "apps/handcrafted_ub_layer_gb"
app = "conv_3_3"
# app = "apps/avg_pool/"

with open(f"apps/{app}/bin/global_buffer.json", "r") as f:
    js = json.load(f)
    with open(f"apps/{app}/map.json", "r") as f2:
        mapping = json.load(f2)

    print(mapping['inputs'])
    print(mapping['outputs'])

    instances = js['namespaces']['global']['modules']['DesignTop']['instances']

    inputs = []
    for i in mapping['inputs']:
        name = i[0]
        i = i[1]
        inst = instances[i['instance']]
        _in = process_inst(inst)
        _in['location'] = i['location']

        if i.get('num_active'):
            num_active = i['num_active']
        else:
            num_active = _in['dims'][0][0]

        if i.get('num_inactive'):
            num_inactive = i['num_inactive']
        else:
            num_inactive = instances['ub_' + name]['genargs']['iter_cnt'][1] - num_active

        _in['num_active'] = num_active
        _in['num_inactive'] = num_inactive
        _in['double_buffered'] = False
        _in['kind'] = 'input'

        # TODO this is metadata for testing... not sure where to put it...
        _in['file'] = i['file']
        _in['trace'] = i['trace']
        _in['name'] = name

        inputs.append(_in)

    outputs = []
    for o in mapping['outputs']:
        name = o[0]
        o = o[1]
        inst = instances[o['instance']]
        _out = process_inst(inst)
        _out['location'] = o['location']
        _out['kind'] = 'output'

        # TODO this is metadata for testing... not sure where to put it...
        _out['file'] = o['file']
        _out['trace'] = o['trace']
        _out['name'] = name

        outputs.append(_out)

    def allocate_gb(inputs, outputs):
        bank = 0
        for _in in inputs:
            _in['addr'] = BANK_ADDR(bank)
            bank += 4

        for _out in outputs:
            _out['addr'] = BANK_ADDR(bank)
            bank += 4

    allocate_gb(inputs, outputs)

    def create_function(name,
                        args=[],
                        vararg=None,
                        kwonlyargs=[],
                        kw_defaults=[],
                        kwarg=None,
                        defaults=[]):

        return ast.FunctionDef(
            name=name,
            args=ast.arguments(
                args=args,
                vararg=vararg,
                kwonlyargs=kwonlyargs,
                kw_defaults=kw_defaults,
                kwarg=kwarg,
                defaults=defaults,
            ),
            body=[],
            decorator_list=[]
        )

    placement = parse_placement(f"apps/{app}/bin/design.place")

    def name_to_tile(name):
        x, y = placement[0][placement[1][name]]
        return f"dut.DUT.Interconnect_inst0.Tile_X{x:02X}_Y{y:02X}"

    scope = parse_ast("""
    import cocotb
    from cocotb.clock import Clock
    from cocotb.triggers import Timer, RisingEdge, FallingEdge, ReadOnly, Lock, Event, Combine
    from cocotb.drivers import BusDriver
    from cocotb.drivers.amba import AXI4LiteMaster
    from cocotb.result import ReturnValue, TestSuccess
    from cocotb.utils import get_sim_time
    from pprint import pprint
    import numpy as np

    from commands import *
    from garnet_driver import GlobalBuffer

    CLK_PERIOD = 10
    """)

    tb = create_function(f"test_{app}", args=[ast.arg(arg='dut', annotation=None)])
    tb.decorator_list.append(ast.Call(
        func=ast.Attribute(
            value=ast.Name(id='cocotb'),
            attr='test',
        ),
        args=[],
        keywords=[],
    ))

    tb.body.append(parse_ast(f"""
    gc = AXI4LiteMaster(dut, "GC", dut.clk)
    gb = GlobalBuffer(dut, "GB", dut.clk)

    global_buffer = dut.DUT.GlobalBuffer_inst0.global_buffer_inst0.global_buffer_int

    auto_restart_instream = [
        global_buffer.io_controller.io_address_generator_0.auto_restart_instream,
        global_buffer.io_controller.io_address_generator_1.auto_restart_instream,
        global_buffer.io_controller.io_address_generator_2.auto_restart_instream,
        global_buffer.io_controller.io_address_generator_3.auto_restart_instream,
        global_buffer.io_controller.io_address_generator_4.auto_restart_instream,
        global_buffer.io_controller.io_address_generator_5.auto_restart_instream,
        global_buffer.io_controller.io_address_generator_6.auto_restart_instream,
        global_buffer.io_controller.io_address_generator_7.auto_restart_instream,
    ]

    in_valid = [
        dut.DUT.Interconnect_inst0.Tile_X00_Y00.io2f_1,
        dut.DUT.Interconnect_inst0.Tile_X04_Y00.io2f_1,
        dut.DUT.Interconnect_inst0.Tile_X08_Y00.io2f_1,
        dut.DUT.Interconnect_inst0.Tile_X0A_Y00.io2f_1,
        dut.DUT.Interconnect_inst0.Tile_X10_Y00.io2f_1,
        dut.DUT.Interconnect_inst0.Tile_X04_Y00.io2f_1,
        dut.DUT.Interconnect_inst0.Tile_X08_Y00.io2f_1,
        dut.DUT.Interconnect_inst0.Tile_X0A_Y00.io2f_1,
    ]

    in_data = [
        dut.DUT.Interconnect_inst0.Tile_X00_Y00.io2f_16,
        dut.DUT.Interconnect_inst0.Tile_X04_Y00.io2f_16,
        dut.DUT.Interconnect_inst0.Tile_X08_Y00.io2f_16,
        dut.DUT.Interconnect_inst0.Tile_X0A_Y00.io2f_16,
        dut.DUT.Interconnect_inst0.Tile_X00_Y00.io2f_16,
        dut.DUT.Interconnect_inst0.Tile_X04_Y00.io2f_16,
        dut.DUT.Interconnect_inst0.Tile_X08_Y00.io2f_16,
        dut.DUT.Interconnect_inst0.Tile_X0A_Y00.io2f_16,
    ]

    out_valid = [
        dut.DUT.Interconnect_inst0.Tile_X01_Y00.f2io_1_0,
        dut.DUT.Interconnect_inst0.Tile_X05_Y00.f2io_1_0,
        dut.DUT.Interconnect_inst0.Tile_X09_Y00.f2io_1_0,
        dut.DUT.Interconnect_inst0.Tile_X0B_Y00.f2io_1_0,
        dut.DUT.Interconnect_inst0.Tile_X11_Y00.f2io_1_0,
        dut.DUT.Interconnect_inst0.Tile_X15_Y00.f2io_1_0,
        dut.DUT.Interconnect_inst0.Tile_X19_Y00.f2io_1_0,
        dut.DUT.Interconnect_inst0.Tile_X1B_Y00.f2io_1_0,
    ]

    out_data = [
        dut.DUT.Interconnect_inst0.Tile_X01_Y00.f2io_16_0,
        dut.DUT.Interconnect_inst0.Tile_X05_Y00.f2io_16_0,
        dut.DUT.Interconnect_inst0.Tile_X09_Y00.f2io_16_0,
        dut.DUT.Interconnect_inst0.Tile_X0B_Y00.f2io_16_0,
        dut.DUT.Interconnect_inst0.Tile_X11_Y00.f2io_16_0,
        dut.DUT.Interconnect_inst0.Tile_X15_Y00.f2io_16_0,
        dut.DUT.Interconnect_inst0.Tile_X19_Y00.f2io_16_0,
        dut.DUT.Interconnect_inst0.Tile_X1B_Y00.f2io_16_0,
    ]

    @cocotb.coroutine
    def log_valid_data(filename, valid, data):
        with open(filename, "w") as f:
            while True:
                yield RisingEdge(dut.clk)
                yield ReadOnly()
                try:
                    if int(valid):
                        f.write(f"{{int(data)}}, ")
                        f.flush()
                except:
                    pass


    @cocotb.coroutine
    def wait_and_clear_interrupt():
        yield RisingEdge(dut.GC_interrupt)
        mask = yield gc.read(INTERRUPT_STATUS_REG)
        yield gc.write(INTERRUPT_STATUS_REG, mask)

    # reset
    dut.reset = 1
    cocotb.fork(Clock(dut.clk, CLK_PERIOD).start())
    yield(Timer(CLK_PERIOD * 10))
    dut.reset = 0

    t_init = get_sim_time()

    # prep cgra
    yield gc.write(STALL_REG, 0b1111)
    yield gc.write(INTERRUPT_ENABLE_REG, 0b11)

    dut._log.info("Configuring CGRA...")
    for command in gc_config_bitstream("apps/{app}/bin/{app}.bs"):
        yield gc.write(command.addr, command.data)
    dut._log.info("Done.")
    """))

    # TODO: check output

    monitors = []
    for signal in mapping['trace']:
        print(f"derp for {signal}")
        print(name_to_tile(signal))
        tb.body.append(gen_monitor(name_to_tile(signal), pe_tile_inputs, name=signal))
        monitors.append(signal)

    def process_input(_in):
        assert _in['dims'][0][1] == 1, "ERROR: Innermost loop accesses must be linear."

        temp = create_function(f"stream_{_in['location']}")
        temp.decorator_list.append(ast.Attribute(
            value=ast.Name(id='cocotb'),
            attr='coroutine',
        ))

        context = []
        curr_body = temp.body
        context.append(curr_body)

        idxs = [hex(_in['addr'])]
        for k, dim in enumerate(_in['dims'][1:][::-1]):
            curr_body.append(parse_ast(f"""
            for x{k} in range({dim[0]}):
                idx{k} = x{k} * {dim[1]} * 2
            """).body[0])
            idxs.append(f"idx{k}")
            context.append(curr_body[-1].body)
            curr_body = context[-1]

        # Initial config
        if len(idxs) > 1:
            conds = [f"x{k} == 0" for k in range(len(idxs)-1)]
            cond = " and ".join(conds)
            curr_body.append(parse_ast(f"""
            if {cond}:
                pass
            """).body[0])
            context.append(curr_body[-1].body)
            curr_body = context[-1]
            del curr_body[0]

        if _in['double_buffered']:
            curr_body.append(parse_ast(f"""
            for command in configure_io(mode=IO_INPUT_STREAM,
                         addr={" + ".join(idxs)},
                         size={_in['dims'][0][0]},
                         io_ctrl={_in['location']},
                         num_active={_in['num_active']},
                         num_inactive=0,
                         width=32):
                yield gc.write(command.addr, command.data)
            """).body[0])
        else:
            curr_body.append(parse_ast(f"""
            for command in configure_io(mode=IO_INPUT_STREAM,
                         addr={" + ".join(idxs)},
                         size={_in['dims'][0][0]},
                         io_ctrl={_in['location']},
                         num_active={_in['num_active']},
                         num_inactive={_in['num_inactive']},
                         width=32):
                yield gc.write(command.addr, command.data)
            """).body[0])

        curr_body.append(parse_ast(f"""
        init_done[{_in['location']}].set()
        """).body[0])

        curr_body.append(parse_ast(f"""
        yield start_done.wait()
        """).body[0])


        if len(_in['dims']) > 1:
            context.pop()
            curr_body = context[-1][-1].orelse

            # Iteration config
            if len(idxs) > 1:
                curr_body.append(parse_ast(f"""
                for command in configure_io(mode=IO_INPUT_STREAM,
                             addr={" + ".join(idxs)},
                             size={_in['dims'][0][0]},
                             io_ctrl={_in['location']},
                             num_active={_in['num_active']},
                             num_inactive={_in['num_inactive']},
                             width=32):
                    yield gc.write(command.addr, command.data)
                """).body[0])

                curr_body += parse_ast(f"""
                yield gc.write(IO_AUTO_RESTART_REG({_in['location']}), 1)
                # dut._log.info("Waiting for input auto_restart...")
                yield FallingEdge(auto_restart_instream[{_in['location']}])
                """).body


            # for k, dim in enumerate(_in['dims'][1:]):
            #     old_body = temp.body
            #     temp.body = parse_ast(f"""
            #     for x{k} in range({dim[0]}):
            #         idx{k} = x{k} * {dim[1]}
            #     """).body
            #     temp.body[0].body += old_body
            #     print(dim)

        # print(astor.dump_tree(temp))
        return temp

    def process_output(_out):
        assert _out['dims'][0][1] == 1, "ERROR: Innermost loop accesses must be linear."

        temp = create_function(f"stream_{_out['location']}")
        temp.decorator_list.append(ast.Attribute(
            value=ast.Name(id='cocotb'),
            attr='coroutine',
        ))

        temp.body.append(parse_ast(f"""
        for command in configure_io(mode=IO_OUTPUT_STREAM,
                     addr={_out['addr']},
                     size={_out['dims'][0][0]},
                     io_ctrl={_out['location']},
                     width=32):
            yield gc.write(command.addr, command.data)
        """).body[0])

        temp.body.append(parse_ast(f"""
        init_done[{_out['location']}].set()
        """).body[0])

        return temp

    tb.body += parse_ast("start_done = Event()").body
    tb.body += parse_ast(f"""
    init_done = [{', '.join(['Event()' for _ in range(len(inputs) + len(outputs))])}]
    """).body

    num_streams = len(inputs) + len(outputs)
    for _in in inputs:
        tb.body += parse_ast(f"""
        {_in['name']}_data = np.fromfile("apps/{app}/{_in['file']}", dtype=np.uint8).astype(np.uint16)
        dut._log.info("Transferring {_in['name']} data...")
        tasks = []
        for k,x in enumerate({_in['name']}_data.view(np.uint64)):
            tasks.append(cocotb.fork(gb.write({_in['addr']} + 8*k, int(x))))
        for task in tasks:
            yield task.join()
        dut._log.info("Done.")

        """).body
        tb.body.append(process_input(_in))

    for _out in outputs:
        tb.body += parse_ast(f"""
        {_out['name']}_data = np.fromfile("apps/{app}/{_out['file']}", dtype=np.uint8).astype(np.uint16)
        """).body
        tb.body.append(process_output(_out))

    tb.body += parse_ast(
        "\n".join([f"cocotb.fork(stream_{n}())" for n in range(num_streams)])
    ).body
    tb.body += parse_ast(
        "Combine(" +
        ",".join(f"init_done[{n}].wait()" for n in range(num_streams)) +
        ")"
    ).body

    tb.body += parse_ast("""
    t_start = get_sim_time()
    dut._log.info("Starting application...")
    yield gc.write(STALL_REG, 0)
    yield gc.write(CGRA_START_REG, 1)
    """).body

    # launch all the monitors
    tb.body += parse_ast("\n".join(f"cocotb.fork(monitor_{name}())" for name in monitors)).body
    for _in in inputs:
        if _in['trace']:
            tb.body.append(parse_ast(
                f"cocotb.fork(log_valid_data(\"{_in['trace']}\", in_valid[{_in['location']}], in_data[{_in['location']}]))"
            ))
    for _out in outputs:
        if _out['trace']:
            tb.body.append(parse_ast(
                f"cocotb.fork(log_valid_data(\"{_out['trace']}\", in_valid[{_out['location']}], in_data[{_out['location']}]))"
            ))


    tb.body += parse_ast("""
    start_done.set()

    yield wait_and_clear_interrupt()
    dut._log.info("Done.")

    t_end = get_sim_time()

    dut._log.info(f"{t_init}, {t_start}, {t_end}")
    with open("test.tcl", "w") as f:
        f.write(f\"\"\"
            run {t_start}
            power -gate_level on
            power DUT
            power -enable
            run {t_end - t_start}
            power -disable
            power -report test.saif 1e-09 DUT
            quit
        \"\"\")

    raise TestSuccess()
    """).body

    with open("tb.py", "w") as f:
        scope.body.append(tb)
        f.write(astor.to_source(scope))

    def index(dims):
        xs = [ 0 for _ in range(len(dims)) ]

        def increment(idx):
            xs[idx] += 1
            if xs[idx] == dims[idx][0]:
                xs[idx] = 0
                return True
            return False

        k = 0
        while k < len(dims):
            idx = 0
            for i,x in enumerate(xs):
                idx += x * dims[i][1]
            yield idx

            k = 0
            while increment(k):
                k += 1
                if k == len(dims):
                    break

    def read_csv(fname):
        with open(fname) as f:
            reader = csv.reader(f, skipinitialspace=True, quoting=csv.QUOTE_NONNUMERIC)
            for row in reader:
                return list(map(int, row[:-1]))

    def validate(i):
        data = np.fromfile(i['file'], dtype=np.uint8)
        trace = np.array(read_csv(i['trace']), dtype=np.uint8)
        gold = [data[k] for k in index(i['dims'])]

        print(f"Validating {i['name']}...")
        if len(gold) != len(trace):
            print(f"ERROR: Expected {len(gold)} values but got {len(trace)} instead.")

        for k in range(len(trace)):
            if gold[k] != trace[k]:
                print(f"ERROR ({k}): Expected {hex(gold[k])} but got {hex(trace[k])}.")
        print("Done.")

    if args.verify_trace:
        for i in inputs:
            validate(i)

        for o in outputs:
            validate(o)

    # def index(dims, idx):
    #     if len(dims) == 0:
    #         yield idx
    #     else:
    #         for x in range(dims[0][0]):
    #             for k in index(dims[1:], idx + x * dims[0][1] ):
    #                 yield k

    # # print([ x for x in index([(256,1), (2,0)][::-1], 0)])
    # # print([ x for x in index(inputs[0]['dims'], 0) ])
    # # print(inputs[0]['dims'])

    # TODO: go through everything and figure out sizes to place in the global buffer
    # TODO: need to get location from gb_args
    # TODO: need to calculate inputs and outputs reserved space
    # TODO: support for double buffering
    # TODO: addressing for double buffering
    # TODO: allocate into global buffer regions
    # TODO: which input ports are these going to?
    # TODO: is the input expected to be every single cycle?

    # inputs = []
    # inputs.append({
    #     "addr": BANK_ADDR(0),
    #     "location": 0,
    #     "size": num_inputs,
    #     "nbytes": (num_bits // 8) * num_inputs,
    # })

    # outputs = []
    # outputs.append({
    #     "addr": BANK_ADDR(16),
    #     "location": 1,
    #     "size": prod([ x[0] for x in dims ]),
    #     "nbytes": (num_bits // 8) * prod([ x[0] for x in dims ]),
    # })

    # print(inputs)
    # print(outputs)

    # print([
    #     # WRITE_REG(GLOBAL_RESET_REG, 1), # TODO: delete?
    #     # Stall the CGRA
    #     WRITE_REG(STALL_REG, 0b1111),

    #     # Enable interrupts
    #     WRITE_REG(INTERRUPT_ENABLE_REG, 0b11),

    #     # Configure the CGRA
    #     PRINT("Configuring CGRA..."),
    #     # *gc_config_bitstream(self.bitstream),
    #     *gb_config_bitstream(self.bitstream, width=self.args.width),
    #     PRINT("Done."),

    #     # Set up global buffer for pointwise
    #     *configure_io(
    #         IO_INPUT_STREAM,
    #         inputs[0]["addr"],
    #         inputs[0]["size"],
    #         io_ctrl=inputs[0]["location"],
    #         # num_active=inputs[0]["num_active"],
    #         # num_inactive=inputs[0]["num_inactive"],
    #         width=self.args.width
    #     ),
    #     *configure_io(
    #         IO_INPUT_STREAM,
    #         inputs[1]["addr"],
    #         inputs[1]["size"],
    #         io_ctrl=inputs[1]["location"],
    #         num_active=inputs[1]["num_active"],
    #         num_inactive=inputs[1]["num_inactive"],
    #         width=self.args.width
    #     ),
    #     *configure_io(
    #         IO_OUTPUT_STREAM,
    #         outputs[0]["addr"],
    #         outputs[0]["size"],
    #         io_ctrl=outputs[0]["location"],
    #         width=self.args.width
    #     ),

    #     # Put image into global buffer
    #     PRINT("Transferring input data..."),
    #     WRITE_DATA(BANK_ADDR(0), 0xc0ffee, im.nbytes, im),
    #     PRINT("Done."),

    #     # Start the application
    #     PRINT("Starting application..."),
    #     WRITE_REG(STALL_REG, 0),
    #     PEND(0b01, "start"),
    #     WRITE_REG(CGRA_START_REG, 1),
    #     PRINT("Waiting for completion..."),
    #     WAIT(0b01, "start"),
    #     PRINT("Done."),

    #     PRINT("Reading output data..."),
    #     READ_DATA(
    #         BANK_ADDR(16),
    #         gold.nbytes,
    #         gold,
    #         _file=self.outfile,
    #     ),
    #     PRINT("All tasks complete!"),
    # ])
