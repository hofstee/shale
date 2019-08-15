import os
import subprocess

cwd = os.getcwd()
for entry in os.scandir("apps"):
    if entry.is_dir():
        subprocess.call(
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
            cwd="deps/garnet"
        )
