from pathlib import Path
import sys
from cocotb.monitors import Monitor
from cocotb.utils import get_sim_time
from vcd import VCDWriter


async def monitor(entity, signals, filename=None):
    with open(filename, "w") as f:
        with VCDWriter(f) as writer:
            vcd_vars = {}
            triggers = []
            for signal in signals:
                handle = getattr(entity, signal)
                vcd_vars[signal] = writer.register_var(
                    str(entity),
                    signal,
                    "wire",
                    size=len(handle),
                )
                triggers.append(Edge(handle))

            while True:
                await First(*triggers)

                time = get_sim_time()
                for signal in signals:
                    writer.change(vcd_vars[signal], time, getattr(entity, signal).value.binstr)


def generate_makefile(garnet_dir):
    extras_dir = (Path(__file__) / "../../extras").resolve()

    with open(extras_dir/"Makefile", "w") as f:
        f.write(rf"""
VERILOG_SOURCES ?= \
    {garnet_dir}/tests/AO22D0BWP16P90.sv \
    {garnet_dir}/tests/AN2D0BWP16P90.sv \
    {garnet_dir}/genesis_verif/memory_core.sv \
    {garnet_dir}/genesis_verif/mem_unq1.v \
    {garnet_dir}/genesis_verif/sram_stub_unq1.v \
    {garnet_dir}/genesis_verif/doublebuffer_control_unq1.sv \
    {garnet_dir}/genesis_verif/fifo_control_unq1.sv \
    {garnet_dir}/genesis_verif/linebuffer_control_unq1.sv \
    {garnet_dir}/genesis_verif/sram_control_unq1.sv \
    {garnet_dir}/peak_core/DW_fp_mult.v \
    {garnet_dir}/peak_core/DW_fp_add.v \
    {garnet_dir}/global_buffer/rtl/cfg_ifc.sv \
    {garnet_dir}/global_buffer/rtl/global_buffer_param.svh \
    {garnet_dir}/global_buffer/rtl/global_buffer_pkg.svh \
    {garnet_dir}/global_buffer/rtl/global_buffer.sv \
    {garnet_dir}/global_buffer/rtl/glb_tile.sv \
    {garnet_dir}/global_buffer/rtl/glb_tile_int.sv \
    {garnet_dir}/global_buffer/rtl/glb_tile_cfg.sv \
    {garnet_dir}/global_buffer/rtl/glb_tile_cfg_ctrl.sv \
    {garnet_dir}/global_buffer/rtl/glb_tile_pc_switch.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_proc_router.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_strm_router.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_pc_router.sv \
    {garnet_dir}/global_buffer/rtl/glb_dummy_start.sv \
    {garnet_dir}/global_buffer/rtl/glb_dummy_end.sv \
    {garnet_dir}/global_buffer/rtl/glb_core.sv \
    {garnet_dir}/global_buffer/rtl/glb_bank.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_store_dma.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_load_dma.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_pc_dma.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_switch.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_strm_mux.sv \
    {garnet_dir}/global_buffer/rtl/glb_core_sram_cfg_ctrl.sv \
    {garnet_dir}/global_buffer/rtl/glb_bank_memory.sv \
    {garnet_dir}/global_buffer/rtl/glb_bank_ctrl.sv \
    {garnet_dir}/global_buffer/rtl/glb_bank_sram_gen.sv \
    {garnet_dir}/global_buffer/rtl/glb_shift.sv \
    {garnet_dir}/global_buffer/rtl/TS1N16FFCLLSBLVTC2048X64M8SW.sv \
    {garnet_dir}/global_buffer/systemRDL/output/glb_jrdl_decode.sv \
    {garnet_dir}/global_buffer/systemRDL/output/glb_jrdl_logic.sv \
    {garnet_dir}/global_buffer/systemRDL/output/glb_pio.sv \
    {garnet_dir}/global_controller/design/genesis_verif/glc_axi_addrmap.sv \
    {garnet_dir}/global_controller/design/genesis_verif/jtag.sv \
    {garnet_dir}/global_controller/design/genesis_verif/cfg_and_dbg_unq1.sv \
    {garnet_dir}/global_controller/design/genesis_verif/global_controller.sv \
    {garnet_dir}/global_controller/design/genesis_verif/tap_unq1.sv \
    {garnet_dir}/global_controller/design/genesis_verif/glc_axi_ctrl.sv \
    {garnet_dir}/global_controller/design/genesis_verif/flop_unq3.sv \
    {garnet_dir}/global_controller/design/genesis_verif/glc_jtag_ctrl.sv \
    {garnet_dir}/global_controller/design/genesis_verif/flop_unq2.sv \
    {garnet_dir}/global_controller/design/genesis_verif/flop_unq1.sv \
    {garnet_dir}/global_controller/systemRDL/output/glc_jrdl_decode.sv \
    {garnet_dir}/global_controller/systemRDL/output/glc_pio.sv \
    {garnet_dir}/global_controller/systemRDL/output/glc_jrdl_logic.sv \
    /cad/synopsys/syn/P-2019.03/dw/sim_ver/DW_tap.v \
    {extras_dir}/garnet.sv \
    {extras_dir}/garnet_top.sv

TESTCASE?=test_standalone
TOPLEVEL?=Garnet_TB
TOPLEVEL_LANG=verilog
MODULE=test_standalone
COCOTB_HDL_TIMEPRECISION=1ps
COCOTB_HDL_TIMESTEP=1ps

ifeq ($(SIM), xcelium)
    SHM_RESET_DEFAULTS=1
endif

include $(shell cocotb-config --makefiles)/Makefile.sim
""")