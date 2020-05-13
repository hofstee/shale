import re


def get_inputs(verilog, instance=None, module=None):
    with open(verilog) as f:
        src = f.read()

    if module is None:
        match = re.search(fr"([A-z0-9_]+)\s+{instance}\b", src)
        module = match[1]

    match = re.search(fr"module\s+{module}\s*\((.*?)\);", src, flags=re.S)
    ports = [port.strip() for port in match[1].split(",")]
    ports = [(port.split()[0], port.split()[-1]) for port in ports]

    inputs = [port[1] for port in ports if port[0] == "input"]
    return inputs
