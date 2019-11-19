# INFO: You may need to `limit stacksize unlimited` for the top-level
# Garnet to work correctly. `ulimit -S -s unlimited` on bash.

source /sim/thofstee/tsmc16_setup.tcl

#########################################################
lappend search_path . ..

set power_enable_analysis true
# set power_analysis_mode averaged
set power_analysis_mode time_based

set BASE $::env(BASE)
set APP $::env(APP)
set DESIGN $::env(DESIGN)

set sim_type "gate"
set activity_file $BASE/$APP.vcd
set parasitics_file /sim/latest/garnet/tapeout_16/synth/$DESIGN/final.spef
read_verilog /sim/latest/garnet/tapeout_16/synth/$DESIGN/pnr.v

if {$DESIGN == "Tile_MemCore"} {
  set dut "Tile_MemCore"
} elseif {$DESIGN == "Tile_PE"} {
  set dut "Tile_PE"
}

set report_dir "./reports/${APP}"

#########################################################
# Read in design                                        #
#########################################################
current_design $DESIGN

set LINK_STATUS [link_design]
if {$LINK_STATUS == 0} {
  echo [concat [format "%s%s" [join [concat "Err" "or"] ""] {: unresolved references. Exiting ...}]]
  quit
}


#########################################################
# Constraints                                           #
#########################################################
switch -glob $DESIGN {
  "GarnetSOC_Pad_Frame" {create_clock -name clk -period 5.0 [get_ports pad_cgra_clk_i]}
  "Garnet" {create_clock -name clk -period 5.0 [get_ports clk_in]}
  "Tile*" {create_clock -name clk -period 5.0 [get_ports clk]}
}

# switch -glob $DESIGN {
#   "GarnetSOC_Pad_Frame" {create_clock -name clk -period 2.3 [get_ports pad_cgra_clk_i]}
#   "Garnet" {create_clock -name clk -period 2.3 [get_ports clk_in]}
#   "Tile*" {create_clock -name clk -period 2.3 [get_ports clk]}
# }

set_input_delay 0.0 -clock clk [all_inputs]
set_output_delay 0.0 -clock clk [all_outputs]
set_input_delay -min 0.0 -clock clk [all_inputs]
set_output_delay -min 0.0 -clock clk [all_outputs]

# TODO: SDC files from PNR?

# set all SB to register outputs by default to break false
# combinational loops in the design
if {$DESIGN == "Garnet"} {
  set sb_muxes {RMUX_T0_NORTH_B1 RMUX_T0_SOUTH_B1 RMUX_T0_EAST_B1 RMUX_T0_WEST_B1 RMUX_T1_NORTH_B1 RMUX_T1_SOUTH_B1 RMUX_T1_EAST_B1 RMUX_T1_WEST_B1 RMUX_T2_NORTH_B1 RMUX_T2_SOUTH_B1 RMUX_T2_EAST_B1 RMUX_T2_WEST_B1 RMUX_T3_NORTH_B1 RMUX_T3_SOUTH_B1 RMUX_T3_EAST_B1 RMUX_T3_WEST_B1 RMUX_T4_NORTH_B1 RMUX_T4_SOUTH_B1 RMUX_T4_EAST_B1 RMUX_T4_WEST_B1 RMUX_T0_NORTH_B16 RMUX_T0_SOUTH_B16 RMUX_T0_EAST_B16 RMUX_T0_WEST_B16 RMUX_T1_NORTH_B16 RMUX_T1_SOUTH_B16 RMUX_T1_EAST_B16 RMUX_T1_WEST_B16 RMUX_T2_NORTH_B16 RMUX_T2_SOUTH_B16 RMUX_T2_EAST_B16 RMUX_T2_WEST_B16 RMUX_T3_NORTH_B16 RMUX_T3_SOUTH_B16 RMUX_T3_EAST_B16 RMUX_T3_WEST_B16 RMUX_T4_NORTH_B16 RMUX_T4_SOUTH_B16 RMUX_T4_EAST_B16 RMUX_T4_WEST_B16}

  foreach sb_mux $sb_muxes {
      set muxes [get_cells -hierarchical [format *%s_sel* $sb_mux]]
      set mux_outs [get_pins -of_objects $muxes -filter "direction==out"]
      set_case_analysis 1 $mux_outs
  }
}

read_parasitics $parasitics_file

#########################################################
# Read VCD                                              #
#########################################################
while {[get_license {"PrimeTime-PX"}] == 0} {
  echo {Waiting for PrimeTime-PX license...}
  sh sleep 120
}
puts "LICENSE ACQUIRED"

proc time_to_float {t} {
    set dur   [lindex [split $t /] 0]
    set scale [lindex [split $t /] 1]

    switch $scale {
        "ps" {return [expr $dur / 1e3]}
        "us" {return [expr $dur * 1e3]}
        "ms" {return [expr $dur * 1e6]}
        "s"  {return [expr $dur * 1e9]}
    }
}

set time_window [list [time_to_float $::env(T_0)] [time_to_float $::env(T_1)]]
switch [file extension $activity_file] {
    ".vcd"  {read_vcd -rtl $activity_file -strip_path $dut -time $time_window}
}

#########################################################
# Iterate over switching activity files to generate     #
# average or time based power reports per diag          #
#########################################################

report_switching_activity
report_switching_activity > "$report_dir/pre_switching_activity.rpt"

report_power
report_power > "$report_dir/power.rpt"

report_switching_activity > "$report_dir/post_switching_activity.rpt"

get_switching_activity -toggle_rate "*" > "$report_dir/switching.rpt"

report_power -nosplit -hierarchy -leaf > "$report_dir/hierarchy.rpt"

report_power -groups clock_network -nosplit -hierarchy -leaf > "$report_dir/clock_power.rpt"

exit
