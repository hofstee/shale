from pathlib import Path

def generate_makefile(garnet_dir):
    extras_dir = (Path(__file__) / "../../extras").resolve()

    with open("extras/Makefile", "w") as f:
        f.write(rf"""
VERILOG_SOURCES ?= \
    {garnet_dir}/tests/AO22D0BWP16P90.sv \
    {garnet_dir}/tests/AN2D0BWP16P90.sv \
    {garnet_dir}/global_buffer/rtl/TS1N16FFCLLSBLVTC2048X64M8SW.sv \
    {garnet_dir}/memory_core/genesis_new/TS1N16FFCLLSBLVTC512X16M8S.sv \
    {garnet_dir}/peak_core/DW_fp_add.v \
    {garnet_dir}/peak_core/DW_fp_mult.v \
    {garnet_dir}/genesis_verif/memory_core.sv \
    {garnet_dir}/genesis_verif/mem_unq1.v \
    {garnet_dir}/genesis_verif/sram_stub_unq1.v \
    {garnet_dir}/genesis_verif/doublebuffer_control_unq1.sv \
    {garnet_dir}/genesis_verif/sram_control_unq1.sv \
    {garnet_dir}/genesis_verif/fifo_control_unq1.sv \
    {garnet_dir}/genesis_verif/linebuffer_control_unq1.sv \
    {garnet_dir}/genesis_verif/global_buffer.sv \
    {garnet_dir}/genesis_verif/global_buffer_int.sv \
    {garnet_dir}/genesis_verif/memory_bank.sv \
    {garnet_dir}/genesis_verif/bank_controller.sv \
    {garnet_dir}/genesis_verif/glbuf_memory_core.sv \
    {garnet_dir}/genesis_verif/cfg_controller.sv \
    {garnet_dir}/genesis_verif/cfg_address_generator.sv \
    {garnet_dir}/genesis_verif/sram_controller.sv \
    {garnet_dir}/genesis_verif/memory.sv \
    {garnet_dir}/genesis_verif/io_controller.sv \
    {garnet_dir}/genesis_verif/io_address_generator.sv \
    {garnet_dir}/genesis_verif/sram_gen.sv \
    {garnet_dir}/genesis_verif/host_bank_interconnect.sv \
    {garnet_dir}/genesis_verif/global_controller.sv \
    {garnet_dir}/genesis_verif/axi_ctrl_unq1.sv \
    {garnet_dir}/genesis_verif/jtag_unq1.sv \
    {garnet_dir}/genesis_verif/cfg_and_dbg_unq1.sv \
    {garnet_dir}/genesis_verif/flop_unq3.sv \
    {garnet_dir}/genesis_verif/flop_unq2.sv \
    {garnet_dir}/genesis_verif/flop_unq1.sv \
    {garnet_dir}/genesis_verif/tap_unq1.sv \
    {extras_dir}/CW_tap.v \
    {extras_dir}/garnet.sv \
    {extras_dir}/garnet_top.sv

TESTCASE?=test_app
TOPLEVEL?=Garnet_TB
TOPLEVEL_LANG=verilog
MODULE=tb
COCOTB_HDL_TIMEPRECISION=1ps
COCOTB_HDL_TIMESTEP=1ps

ifeq ($(SIM), vcs)
    override COMPILE_ARGS += -LDFLAGS -Wl,--no-as-needed
    override COMPILE_ARGS += -top $(TOPLEVEL)
else ifeq ($(SIM), ius)
    LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libstdc++.so.6
else ifeq ($(SIM), xcelium)
    SHM_RESET_DEFAULTS=1
endif

include $(shell cocotb-config --makefiles)/Makefile.inc
include $(shell cocotb-config --makefiles)/Makefile.sim
""")
