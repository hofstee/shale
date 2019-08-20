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
args = parser.parse_args()

cwd = os.getcwd()
cgra_utilization = re.compile(r"PE: (?P<PE>\d+) IO: (?P<IO>\d+) MEM: (?P<MEM>\d+) REG: (?P<REG>\d+)")

def should_run_app(entry, args):
    return entry.is_dir() and (len(args.apps) == 0 or entry.name in args.apps)

with open(f"apps/utilization.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=["name", "PE", "IO", "MEM", "REG"])
    w.writeheader()

    print(args.width, args.height)

    for entry in os.scandir("apps"):
        if should_run_app(entry, args):
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
                stdout=subprocess.PIPE,
                cwd="deps/garnet",
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
