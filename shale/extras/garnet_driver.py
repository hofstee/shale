import cocotb
from cocotb.triggers import RisingEdge, ReadOnly, Lock
from cocotb.drivers import BusDriver
from cocotb.result import ReturnValue

class GlobalBuffer(BusDriver):
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

    @cocotb.coroutine
    def write(self, address, data, byte_enable=0b11111111, sync=True):
        """Write a value to an address.
        """
        if sync:
            yield RisingEdge(self.clock)

        yield self.write_busy.acquire()

        self.bus.wr_addr <= address
        self.bus.wr_data <= data
        self.bus.wr_en <= 1
        self.bus.wr_strb <= byte_enable

        yield RisingEdge(self.clock)

        self.bus.wr_strb <= 0
        self.write_busy.release()

    @cocotb.coroutine
    def read(self, address, sync=True):
        """Read from an address.
        Returns:
            BinaryValue: The read data value.
        """
        if sync:
            yield RisingEdge(self.clock)

        yield self.read_busy.acquire()

        self.bus.rd_addr <= address
        self.bus.rd_en <= 1

        yield RisingEdge(self.clock)

        self.bus.rd_en <= 0
        self.read_busy.release()

        yield ReadOnly()
        while self.bus.rd_data_valid != 1:
            yield RisingEdge(self.clock)
            yield ReadOnly()

        data = self.bus.rd_data

        raise ReturnValue(data)
