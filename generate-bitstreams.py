import csv
import os
import re
import subprocess

cwd = os.getcwd()
cgra_utilization = re.compile(r"PE: (?P<PE>\d+) IO: (?P<IO>\d+) MEM: (?P<MEM>\d+) REG: (?P<REG>\d+)")

with open(f"{cwd}/apps/utilization.csv", "w") as f:
    w = csv.DictWriter(f, fieldnames=["name", "PE", "IO", "MEM", "REG"])
    w.writeheader()

    for entry in os.scandir("apps"):
        if entry.is_dir():
            p = subprocess.run(
                [
                    "python",
                    "garnet.py",
                    "--width", "32",
                    "--height", "16",
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

            if not p.returncode:
                util = cgra_utilization.search(p.stdout)
                if util:
                    d = util.groupdict()
                    d["name"] = entry.name
                    w.writerow(d)
