import cocotb
from cocotb.clock import Clock
from cocotb.drivers import BusDriver
from cocotb.triggers import RisingEdge, ReadOnly, Lock
from cocotb.result import ReturnValue
from shale.util.rdl import defs as rdl


class GlobalController:
    def __init__(self, dut=None, mode="cocotb"):
        self.mode = mode
        if mode == "cocotb":
            self.dut = dut
            self.driver = AXI4LiteMaster(dut, "GC", dut.clk)
        else:
            pass

    def _addr(self, reg_name, controller=0):
        offset = rdl[reg_name]
        if reg_name.startswith("glc"):
            return offset
        elif reg_name.startswith("glb"):
            return int(f"0b1{controller:04b}{offset:08b}", 2)
        raise NotImplementedError(reg_name)

    async def write(self, reg_name, data):
        addr = self._addr(reg_name)
        if self.mode == "cocotb":
            await self.driver.write(addr, data)
        else:
            print("WRITE", hex(addr), hex(data))

    async def read(self, reg_name):
        return await self.driver.read(_addr(rdl[reg_name]))


class GlobalBufferDriver(BusDriver):
    _signals = ["rd_addr", "rd_data", "rd_data_valid", "rd_en",
                "wr_addr", "wr_data", "wr_en", "wr_strb"]

    def __init__(self, entity, name, clock):
        BusDriver.__init__(self, entity, name, clock)

        # Drive some sensible defaults (setimmediatevalue to avoid x asserts)
        self.bus.rd_addr.setimmediatevalue(0)
        self.bus.rd_en.setimmediatevalue(0)

        self.bus.wr_addr.setimmediatevalue(0)
        self.bus.wr_data.setimmediatevalue(0)
        self.bus.wr_en.setimmediatevalue(0)
        self.bus.wr_strb.setimmediatevalue(0)

        # Mutex for each channel that we master to prevent contention
        self.write_busy = Lock("%s_wbusy" % name)
        self.read_busy = Lock("%s_rbusy" % name)

    async def write(self, address, data, byte_enable=0b11111111, sync=True):
        """Write a value to an address.
        """
        if sync:
            await RisingEdge(self.clock)

        await self.write_busy.acquire()

        self.bus.wr_addr <= address
        self.bus.wr_data <= data
        self.bus.wr_en <= 1
        self.bus.wr_strb <= byte_enable

        await RisingEdge(self.clock)

        self.bus.wr_strb <= 0
        self.bus.wr_en <= 0
        self.write_busy.release()

    async def read(self, address, sync=True):
        """Read from an address.
        Returns:
            BinaryValue: The read data value.
        """
        if sync:
            await RisingEdge(self.clock)

        await self.read_busy.acquire()

        self.bus.rd_addr <= address
        self.bus.rd_en <= 1

        await RisingEdge(self.clock)

        self.bus.rd_en <= 0
        self.read_busy.release()

        await ReadOnly()
        while self.bus.rd_data_valid != 1:
            await RisingEdge(self.clock)
            await ReadOnly()

        data = self.bus.rd_data

        return data


class GlobalBuffer:
    def __init__(self, dut=None, mode="cocotb"):
        self.mode = mode
        if mode == "cocotb":
            self.dut = dut
            self.driver = GlobalBufferDriver(dut, "GC", dut.clk)
        else:
            pass

    def _addr(self, offset):
        return offset

    async def write(self, offset, data):
        addr = self._addr(offset)
        if self.mode == "cocotb":
            await self.driver.write(addr, data)
        else:
            print("WRITE", hex(addr), hex(data))

    async def read(self, addr):
        if self.mode == "cocotb":
            return await self.driver.read(_addr(addr))
        else:
            print("READ", hex(addr))


class Garnet:
    def __init__(self, dut=None, mode="cocotb"):
        self.mode = mode
        self.dut = dut
        self.gc = GlobalController(dut=dut, mode=mode)
        self.gb = GlobalBuffer(dut=dut, mode=mode)

        if mode == "cocotb":
            cocotb.fork(Clock(self.dut.clk, CLK_PERIOD, 'ns').start())

    async def reset(self):
        # reset
        cocotb.fork(Clock(dut.clk, CLK_PERIOD, 'ns').start())
        self.dut.JTAG_TCK = 0
        self.dut.JTAG_TDI = 0
        self.dut.JTAG_TMS = 0
        self.dut.JTAG_TRSTn = 1
        self.dut.reset = 0
        self.dut.GC_ARADDR = 0
        self.dut.GC_AWADDR = 0
        self.dut.GC_WDATA = 0
        self.dut.GC_WSTRB = 0
        await Timer(CLK_PERIOD * 10, 'ns')
        self.dut.JTAG_TRSTn = 0
        self.dut.reset = 1
        await Timer(CLK_PERIOD * 10, 'ns')
        self.dut.JTAG_TRSTn = 1
        self.dut.reset = 0

        await gc.write(gc_cfg_addr(rdl['glc.global_reset']), 10)
        await Timer(CLK_PERIOD * 20, 'ns')


    def log(self, *args):
        if self.mode == "cocotb":
            self.dut._log.info(*args)
        else:
            print(*args)
