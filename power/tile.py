from canal.pnr_io import __parse_raw_routing_result
import json


def get_loc(node_str: str):
    if node_str[0] == "SB":
        _, x, y, _, _, _ = node_str[1:]
        return x, y
    elif node_str[0] == "PORT":
        _, x, y, _ = node_str[1:]
        return x, y
    elif node_str[0] == "REG":
        _, _, x, y, _ = node_str[1:]
        return x, y
    elif node_str[0] == "RMUX":
        _, x, y, _ = node_str[1:]
        return x, y
    else:
        raise Exception("Unknown node " + " ".join(node_str))


# design.route -> set(((x, y),))
def get_active_tiles(filename: str):
    raw_routing_result = __parse_raw_routing_result(filename)
    locations = set()
    for net_id, raw_routes in raw_routing_result.items():
        for raw_segment in raw_routes:
            for node_str in raw_segment:
                loc = get_loc(node_str)
                locations.add(loc)
    return locations


def parse_placement(filename):
    if len(filename) == 0:
        return {}, {}
    with open(filename) as f:
        lines = f.readlines()
    lines = lines[2:]
    placement = {}
    name_to_id = {}
    for line in lines:
        raw_line = line.split()
        assert (len(raw_line) == 4)
        blk_name = raw_line[0]
        x = int(raw_line[1])
        y = int(raw_line[2])
        blk_id = raw_line[-1][1:]
        placement[blk_id] = (x, y)
        name_to_id[blk_name] = blk_id

    return placement, name_to_id


# mapped.json -> {tile: op}
def get_tile_ops(design, placement):
    placement = parse_placement(placement)
    with open(design) as f:
        design = json.load(f)
        instances = design["namespaces"]["global"]["modules"]["DesignTop"]["instances"]

        tiles = {}
        for instance, params in instances.items():
            if params.get("genref", None) == "cgralib.PE":
                alu_op = params["modargs"].get("alu_op", None)
                if alu_op:
                    x, y = placement[0][placement[1][instance]]
                    tiles[(x, y)] = alu_op[1]
            elif params.get("genref", None) == "cgralib.Mem":
                x, y = placement[0][placement[1][instance]]
                tiles[(x, y)] = "mem"
            elif params.get("genref", None) == "coreir.const":
                pass
            elif params.get("modref", None) == "corebit.const":
                pass
            elif params.get("genref", None) == "cgralib.IO":
                x, y = placement[0][placement[1][instance]]
                tiles[(x, y)] = "io"
            elif params.get("modref", None) == "cgralib.BitIO":
                x, y = placement[0][placement[1][instance]]
                tiles[(x, y)] = "io"
            elif params.get("genref", None) == "coreir.reg":
                pass
            else:
                raise NotImplementedError(params)

    for tile in tiles:
        if tiles[tile] in ("mult_0", "mult_1", "mult_2"):
            tiles[tile] = "mult"

    return tiles


# {tile: op} -> {op: [tiles]}
def group_tiles_by_op(tiles):
    op_mapping = {}
    for tile, op in tiles.items():
        op_mapping[op] = op_mapping.get(op, []) + [tile]

    return op_mapping


print(get_tile_ops("/home/teguhhofstee/aha/temp/mapped.json"))
print(get_active_tiles("/home/teguhhofstee/aha/temp/design.route"))
print(group_tiles_by_op(get_tile_ops("/home/teguhhofstee/aha/temp/mapped.json")))
