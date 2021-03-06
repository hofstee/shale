import argparse
import itertools
import os
import pandas as pd

from aggregate import analyze_tile
from tile import get_active_tiles, group_tiles_by_op, get_tile_ops


def analyze_app(args):
    active_tiles = get_active_tiles(f"{args.app}/bin/design.route")
    tile_ops = get_tile_ops(f"{args.app}/bin/mapped.json", f"{args.app}/bin/design.place")
    tile_ops = {tile: tile_ops.get(tile, "passthrough") for tile in active_tiles}
    tile_ops = {tile: tile_ops.get(tile, "inactive") for tile in itertools.product(range(args.width), range(1,args.height+1))}
    tile_metadata = {tile: {"op": tile_ops[tile]} for tile in tile_ops}
    breakdowns = {}

    for x,y in tile_ops:
        if y == 0:
            tile_metadata[(x,y)]["type"] = "io"
        elif x%4 == 3:
            tile_metadata[(x,y)]["type"]  = "mem"
        else:
            tile_metadata[(x,y)]["type"]  = "pe"

        if args.metadata_only:
            continue

        tilename = f"Tile_X{x:02X}_Y{y:02X}"
        os.makedirs(f"reports/{args.app.rsplit('/')[-1]}/{tilename}", exist_ok=True)
        breakdowns[(x,y)] = analyze_tile(f"{args.reports}/{tilename}/hierarchy.rpt", report_dir=f"reports/{args.app.rsplit('/')[-1]}/{tilename}")


    tag_to_tiles = {}
    for tile, tags in tile_metadata.items():
        key = tuple(sorted(tags.items()))
        tag_to_tiles[key] = tag_to_tiles.get(key, []) + [tile]

    if not args.metadata_only:
        for tag, tiles in tag_to_tiles.items():
            df = pd.concat([breakdowns[tile]["total_power"] for tile in tiles], axis=1).transpose().set_index(pd.Index(tiles, names=["x", "y"]), drop=True)
            print(tag)
            print(df)
            sanitized_tag = "-".join("_".join(t) for t in tag)
            with open(f"reports/{args.app.rsplit('/')[-1]}/{sanitized_tag}.csv", "w") as f:
                f.write(df.to_csv())

    print(tag_to_tiles)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    parser.add_argument("app", type=str)
    parser.add_argument("--width", type=int, default=32)
    parser.add_argument("--height", type=int, default=16)
    parser.add_argument("--reports", type=str)
    parser.add_argument("--metadata-only", action="store_true")
    args = parser.parse_args()

    analyze_app(args)
