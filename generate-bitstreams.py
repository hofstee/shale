import argparse
import csv
import os
import re
import subprocess
import sys

parser = argparse.ArgumentParser()
parser.add_argument("apps", nargs="*")
parser.add_argument("--width", type=int, default=32)
parser.add_argument("--height", type=int, default=16)
parser.add_argument("--force", action="store_true")
args = parser.parse_args()

cwd = os.getcwd()
cgra_utilization = re.compile(r"PE: (?P<PE>\d+) IO: (?P<IO>\d+) MEM: (?P<MEM>\d+) REG: (?P<REG>\d+)")

def should_run_app(subdir, entry, args):
    # Complete applications are expected to be in subdirectories of
    # the apps folder. These subdirectories have the following
    # information:
    #
    # bin/design_top.json - This is the top level CoreIR for the
    #                       bitstream that we generate.
    #
    # bin/global_buffer.json - This holds the global buffer's unified
    #                          buffer parameters we use to generate
    #                          our access patterns.
    #
    # {app_name}_{data}.raw - These are binary data files containing
    #                         the expected inputs or results for an
    #                         application. Typically a result file
    #                         will be called 'gold', while inputs are
    #                         called 'inputs' or 'weights', etc.
    #
    # map.json - This file contains supplemental information used to
    #            create the testbenches, such as which signals are
    #            correlated to which names, a list of signals in the
    #            design_top.json to trace, information about the
    #            location of the i/o streams, and paths containing the
    #            data to drive or expect from the global buffer.
    if not entry.is_dir():
        return False

    # If args.apps is empty, we run all apps.
    if not (len(args.apps) == 0 or (subdir + "/" + entry.name) in args.apps):
        return False

    if args.force:
        return True

    # We haven't created the bitstream yet.
    if not os.path.exists(f"{entry.path}/bin/{entry.name}.bs"):
        return True

    # Check if the design has been modified more recently than the
    # bitstream.
    design_mtime = os.path.getmtime(f"{entry.path}/bin/design_top.json")
    bitstream_mtime = os.path.getmtime(f"{entry.path}/bin/{entry.name}.bs")
    if bitstream_mtime > design_mtime:
        print(f"INFO: `{entry.name}` is already up to date.")
        return False

    return True

with open(f"apps/utilization.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=["name", "PE", "IO", "MEM", "REG"])
    w.writeheader()

    print(args.width, args.height)

    # If there are apps within a folder, grab the apps that are inside that folder
    entries = []
    for entry in os.scandir("apps"):
        if os.path.isdir(f"{entry.path}/bin/"):
            entries.append(("", entry))
        elif entry.is_dir():
            for subentry in os.scandir(entry):
                entries.append((entry.name, subentry))

    for dir_entry in entries:
        if should_run_app(dir_entry[0], dir_entry[1], args):
            entry = dir_entry[1]
            p = subprocess.run(
                [
                    "python",
                    "garnet.py",
                    "--width", f"{args.width}",
                    "--height", f"{args.height}",
                    "--no-pd",
                    "--interconnect-only",
                    "--input-app", f"{cwd}/{entry.path}/bin/design_top.json",
                    "--input-file", f"{cwd}/{entry.path}/{entry.name}_input.raw",
                    "--gold-file", f"{cwd}/{entry.path}/{entry.name}_gold.raw",
                    "--output-file", f"{cwd}/{entry.path}/bin/{entry.name}.bs",
                ],
                cwd="deps/garnet",
                stdout=subprocess.PIPE,
                text=True,
            )

            with open (f"{entry.path}/bin/garnet.log", "w") as log:
                log.write(p.stdout)

            if p.returncode:
                print(f"Garnet failed to map `{entry.name}`", file=sys.stderr)
                print(p.stdout, file=sys.stderr)
            else:
                for collateral in os.scandir("deps/garnet/temp"):
                    os.rename(collateral.path, f"{entry.path}/bin/{collateral.name}")

                util = cgra_utilization.search(p.stdout)
                if util:
                    d = util.groupdict()
                    d["name"] = entry.name
                    w.writerow(d)
