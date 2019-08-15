import os
import subprocess

cwd = os.getcwd()
for entry in os.scandir("apps"):
    if entry.is_dir():
        subprocess.call(
            [
                "python garnet.py",
                "--width 32",
                "--height 16",
                "--no-pd",
                "--interconnect-only",
                f"--input-app {cwd}/{entry.path}/bin/design_top.json",
                f"--input-file {cwd}/{entry.path}/{entry.name}_input.raw",
                f"--gold-file {cwd}/{entry.path}/{entry.name}_gold.raw",
                f"--output-file {cwd}/{entry.path}/bin/{entry.name}.bs",
            ],
            cwd="deps/garnet"
        )
