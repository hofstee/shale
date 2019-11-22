import argparse
import functools
import itertools
import logging
import numpy as np
import os
import pandas as pd
import time
import json

# from IPython.display import display

from tools import PrimeTime, Genus
from tile import group_tiles_by_op, get_tile_ops
# from power.util import filter_ancestors #get_cover, get_intervals

pd.set_option('display.max_colwidth', -1)


def get_cover(intervals):
    res = set()
    for lo, hi in intervals:
        # intervals are closed
        res.update(range(lo, hi+1))

    return res


def intersect_intervals(a, b):
    ints = []

    i, j = 0, 0
    while i < len(a) and j < len(b):
        a0, a1 = a[i]
        b0, b1 = b[j]

        if a0 > b1:
            j += 1
            continue
        elif b0 > a1:
            i += 1
            continue

        ints.append((max(a0, b0), min(a1, b1)))

        if a1 > b1:
            j += 1
        else:
            i += 1

    return ints


def intersect_intervals(a, b):
    temp = get_cover(a) & get_cover(b)
    return temp


def diff_intervals(a, b):
    ints = []

    i, j = 0, 0
    while i < len(a) and j < len(b):
        a0, a1 = a[i]
        b0, b1 = b[j]

        if a0 > b1:
            j += 1
            continue
        elif b0 > a1:
            i += 1
            continue

        ints.append((max(a0, b0), min(a1, b1)))

        if a1 > b1:
            j += 1
        else:
            i += 1

    return ints


def diff_intervals(a, b):
    temp = get_cover(a) - get_cover(b)
    return temp


def get_intervals(df):
    return sorted(list(zip(df["id"], df["last"])), key=lambda x: x[0])


def filter_ancestors(df):
    # We can take advantage of the structure of our data. Our data has
    # two fields, `id` and `last`, which form the inclusive range of
    # the subtree with `id` as its root. This means that a parent must
    # have a lower `id` than its children, so we can sort the list to
    # traverse the tree using DFS.

    last = 0
    indices_to_drop = []
    for index, extent in get_intervals(df):
        if extent <= last:
            indices_to_drop.append(index)
            continue

        last = extent

    return df.set_index("id").drop(indices_to_drop).reset_index()


def remove_covered(df, covers):
    indices_to_drop = []
    for index, parent in sorted(list(zip(df["id"], df["parent"])), key=lambda x: x[0]):
        for key, cover in covers.items():
            if parent in cover:
                indices_to_drop.append(index)
                break

    return df.set_index("id").drop(indices_to_drop).reset_index()


def mem_tile_groups(cells):
    groups = {}

    groups["interconnect"] = cells[
        cells["name"].str.contains("|".join([
            "CB",
            "SB",
        ]))
    ]

    groups["clock"] = cells[
        cells["name"].str.contains("|".join([
            "CTS",
        ]))
    ]

    groups["dbuf_ctrl"] = cells[
        cells["name"].str.contains("|".join([
            "range",
            "stride",
            "iter_cnt",
            "depth",
            "starting_addr",
            "stencil_width",
            "switch_db",
            "enable_chain",
            "arbitrary_addr",
            "chain_wen_in",
            "rate_matched",
            "doublebuffer_control",
        ]))
        & ~cells.isin(groups["interconnect"]).all(1)
    ]

    groups["fifo_ctrl"] = cells[
        cells["name"].str.contains("|".join([
            "fifo_control",
            "circular_en",
        ]))
        & ~cells.isin(groups["interconnect"]).all(1)
    ]

    groups["lbuf_ctrl"] = cells[
        cells["name"].str.contains("|".join([
            "linebuffer_control",
        ]))
        & ~cells.isin(groups["interconnect"]).all(1)
    ]

    groups["sram_ctrl"] = cells[
        cells["name"].str.contains("|".join([
            "sram_control",
        ]))
        & ~cells.isin(groups["interconnect"]).all(1)
    ]

    groups["srams"] = cells[
        cells["name"].str.contains("|".join([
            "mem_inst\d+_m",
        ]), regex=True)
        & ~cells.isin(groups["interconnect"]).all(1)
    ]

    return groups


def pe_tile_groups(cells):
    groups = {}

    groups["interconnect"] = cells[
        cells["name"].str.contains("|".join([
            "CB",
            "SB",
        ]))
    ]

    groups["config"] = cells[
        cells["name"].str.contains("|".join([
            "config",
        ]))
    ]

    groups["clock"] = cells[
        cells["name"].str.contains("|".join([
            "CTS",
        ]))
    ]

    groups["decode"] = cells[
        cells["name"].str.contains("|".join([
            "DECODE",
        ]))
    ]

    groups["PE"] = cells[
        cells["cell"] == "PE_PE"
    ]

    return groups


def tile_breakdown(tilename, df, *, report_dir="reports"):
    top = df[df['name'] == tilename].iloc[0]
    cells = df[(df['id'] >= top['id']) & (df['id'] <= top['last'])]

    if top['name'] == "Tile_MemCore":
        groups = mem_tile_groups(cells)
    elif top['name'] == "Tile_PE":
        groups = pe_tile_groups(cells)
    else:
        raise NotImplementedError(top['name'], top['cell'])

    top = cells[cells['name'] == tilename]

    covers = {}
    for k in groups:
        groups[k] = filter_ancestors(groups[k])
        covers[k] = get_cover(get_intervals(groups[k]))

    for k in groups:
        groups[k] = remove_covered(groups[k], covers)
        covers[k] = get_cover(get_intervals(groups[k]))

    covered = functools.reduce(
        lambda a, b: a | b,
        [covers[group] for group in groups]
    )
    df = cells[cells["id"].isin(covered)]

    uncovered = get_cover(get_intervals(top)) - covered
    uncovered.remove(min(cells["id"]))
    groups["other"] = cells[cells["id"].isin(uncovered)]
    groups["other"] = filter_ancestors(groups["other"])
    covers["other"] = get_cover(get_intervals(groups["other"]))

    for k in groups:
        with open(f"{report_dir}/{k}.csv", "w") as f:
            f.write(cells[cells["id"].isin(covers[k])].sort_values(by=['total'], ascending=False).to_csv())


    for a, b in itertools.combinations(groups, 2):
        overlap = covers[a] & covers[b]
        if not len(overlap) == 0:
            logging.warning(f"`{a}` and `{b}` have {len(overlap)} overlapping cells. Double-counting.")
            logging.warning(cells[cells["id"].isin(list(overlap))])

    total_power = sum(top["total"])
    table = {}
    for key, group in groups.items():
        power = np.nansum(group["total"])
        table[key] = [power]
    table["Total"] = [total_power]
    table = pd.DataFrame(table.values(), index=table.keys(), columns=["total_power"])

    df = table["total_power"]
    table["percent"] = df/df.max()

    print(table)

    # display(table.style.format({
    #     'total_power': '{:,.3e}'.format,
    #     'percent': '{:,.2%}'.format,
    # }))

    return table


# PE core	MEM core	GB	Interconnect	Other (processor, AXI)	DRAM

# In addition to this, for each app, it would be good to get a breakdown of power for PE tile and Memory tile, averaged across all PE's or Memories utilized by the app. For PE tile the breakdown would be -- ops (fpmult, fpadd, mult, all other ops), SB, CB, config regs, pond. This will be useful for peak paper. For Memory tile the breakdown would be -- sram macros, each different controller, config regs, SB, CB. This will be useful for Lake paper.

# Finally, it will be good to get app level dynamic vs leakage CGRA power numbers at different Vt, VDD while keep frequency fixed. For this we will have to re-characterize the lib files at lower VDDs (unless they already exist). These were the numbers that were missing from Ankita's paper.


# Get all config registers inside of a memory tile
# {
#     "Tile_MemCore == cell"
#     {
#         "ConfigRegister in cell"
#     }
# }
#
# config_regs = df[df.name.str.contains("Config")]
# mem_tiles = df[df.name == "Tile_MemCore"]
# config_regs[config_regs.parent.isin(mem_tiles.id)]

def analyze_tile(src, *, source="PrimeTime", db=None, top=None, force=False, report_dir="reports"):
    if db is None:
        start = time.time()
        if source == "PrimeTime":
            df = PrimeTime().create_df(src, db)
        else:
            raise NotImplementedError(f"Can't parse report from `{source}`")
        logging.info(f"Creating database took {time.time()-start:0.2f}s")
    else:
        import sqlite3
        if force:
            if os.path.exists(db):
                os.remove(db)

        if db is ":memory:" or not os.path.exists(db):
            start = time.time()
            if source == "PrimeTime":
                conn = PrimeTime().create_db(src, db)
            elif source == "Genus":
                conn = Genus().create_db(src, db)
            else:
                raise NotImplementedError(f"Can't parse report from `{source}`")
            logging.info(f"Creating database took {time.time()-start:0.2f}s")
        else:
            conn = sqlite3.connect(db)

        c = conn.cursor()
        df = pd.read_sql("SELECT * FROM nodes", conn)
        conn.close()


    df.parent = df.parent.astype('Int64')

    # print(df.sort_values(by=['total'], ascending=False))

    if top is None:
        top = df[df["id"] == min(df["id"])].iloc[0]["name"]

    return tile_breakdown(top, df, report_dir=report_dir)


def main(args):
    analyze_tile(
        args.src,
        source=args.source,
        db=args.db,
        top=args.top,
        force=args.force,
        report_dir=args.report_dir,
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="""
    This is a helper script to aggregate power into categories for
    Garnet.
    """)

    parser.add_argument("src", type=str)
    parser.add_argument("--db", type=str, default=None)
    parser.add_argument("--source", type=str, default="PrimeTime")
    parser.add_argument("--report-dir", type=str, default="reports")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--top", type=str, default=None)
    args = parser.parse_args()

    main(args)
