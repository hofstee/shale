import sqlite3
import time
from util import get_labels

class PrimeTime():
    def __init__(self, *, batch_size=1024):
        self.batch_size = batch_size
        pass

    def create_db(self, rpt_file, db_file):
        con = sqlite3.connect(db_file)
        # con.execute("PRAGMA foreign_keys = ON")

        # Create table
        con.execute("""
        CREATE TABLE IF NOT EXISTS nodes
        (id INTEGER PRIMARY KEY,
         parent INTEGER,
         last INTEGER,
         name TEXT,
         cell TEXT,
         internal REAL,
         switching REAL,
         leakage REAL,
         total REAL,
         FOREIGN KEY(parent) REFERENCES nodes(id),
         FOREIGN KEY(last) REFERENCES nodes(id))
        """)

        header = []

        with open(rpt_file) as f:
            hier = []
            rows = []
            skip_header = True
            for k, line in enumerate(f):
                line_num = k+1
                if skip_header:
                    if "----" in line:
                        skip_header = False
                        temp = []
                        for header_line in reversed(header):
                            if header_line.strip() == '':
                                break
                            temp.append(header_line)
                        labels = get_labels("\n".join(reversed(temp)))
                        print(labels)
                    else:
                        header.append(line)
                    continue

                if line == "1\n":
                    print(f"Done on line {line_num}")
                    break

                info = line.split()
                if len(info) == 6:
                    cell = None
                    name, internal, switching, leakage, total, percent = info
                elif len(info) == 7:
                    name, cell, internal, switching, leakage, total, percent = info
                elif len(info) == 10:
                    cell = None
                    name, internal, switching, leakage, peak_power, peak_time, glitch_power, x_tran_power, total, percent = info
                elif len(info) == 11:
                    name, cell, internal, switching, leakage, peak_power, peak_time, glitch_power, x_tran_power, total, percent = info
                else:
                    raise NotImplementedError(line)

                if cell is not None:
                    cell = cell.lstrip("(").rstrip(")")
                if total == "N/A":
                    total = None

                info = {
                    "indent": len(line) - len(line.lstrip(' ')),
                    "id": line_num,
                    "name": name,
                    "cell": cell,
                    "internal": internal,
                    "switching": switching,
                    "leakage": leakage,
                    "total": total,
                }

                while len(hier) > 0 and info["indent"] <= hier[-1]["indent"]:
                    node = hier.pop()
                    node["last"] = line_num-1
                    node["parent"] = hier[-1]["id"] if len(hier) > 0 else None
                    rows.append((
                        node["id"],
                        node["parent"],
                        node["last"],
                        node["name"],
                        node["cell"],
                        node["internal"],
                        node["switching"],
                        node["leakage"],
                        node["total"],
                    ))

                if len(rows) > self.batch_size:
                    con.executemany(
                        "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        rows
                    )
                    rows.clear()

                hier.append(info)

            while len(hier) > 0:
                node = hier.pop()
                node["last"] = line_num-1
                node["parent"] = hier[-1]["id"] if len(hier) > 0 else None
                rows.append((
                    node["id"],
                    node["parent"],
                    node["last"],
                    node["name"],
                    node["cell"],
                    node["internal"],
                    node["switching"],
                    node["leakage"],
                    node["total"],
                ))

            con.executemany(
                "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                rows
            )

        con.commit()
        foreign_key_failures = con.execute("PRAGMA foreign_key_check").fetchall()
        if len(foreign_key_failures) > 0:
            raise sqlite3.IntegrityError(f"Failed foreign key checks: {foreign_key_failures}")

        # print(f"split:   {time_split}")
        # print(f"update:  {time_update}")
        return con


class Genus():
    def __init__(self):
        pass

    def create_db(self, rpt_file, db_file):
        con = sqlite3.connect(db_file)
        con.execute("PRAGMA foreign_keys = 1")

        # Create table
        con.execute("""
        CREATE TABLE IF NOT EXISTS nodes
        (id INTEGER PRIMARY KEY,
         parent INTEGER,
         last INTEGER,
         name TEXT,
         cell TEXT,
         internal REAL,
         switching REAL,
         leakage REAL,
         total REAL,
         percent REAL,
         FOREIGN KEY(parent) REFERENCES nodes(id),
         FOREIGN KEY(last) REFERENCES nodes(id))
        """)

        with open(rpt_file) as f:
            indent_levels = []
            hier = []

            skip_header = True
            for k, line in enumerate(f):
                line_num = k+1

                if skip_header:
                    if "----" in line:
                        skip_header = False
                    continue

                info = line.split()
                if len(info) == 5:
                    cell = None
                    name, _, leakage, dynamic, total = info
                elif len(info) == 0:
                    print(f"Done on line {line_num}")
                    break
                else:
                    raise NotImplementedError(line)

                info = {
                    "name": name,
                    "cell": cell,
                    "internal": None,
                    "switching": dynamic + "e-9",
                    "leakage": leakage + "e-9",
                    "total": total + "e-9",
                    "percent": None,
                }

                indent = len(line) - len(line.lstrip(' '))
                while len(indent_levels) > 0 and indent <= indent_levels[-1]:
                    indent_levels.pop()
                    con.execute(
                        "UPDATE nodes SET last=? WHERE id=?",
                        (line_num-1, hier.pop())
                    )

                # if info["percent"] == "N/A":
                #     info["percent"] = 0

                con.execute(
                    "INSERT INTO nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        line_num,
                        hier[-1] if len(hier) > 0 else None,
                        None,
                        info["name"],
                        info["cell"],
                        info["internal"],
                        info["switching"],
                        info["leakage"],
                        info["total"],
                        info["percent"],
                    )
                )

                indent_levels.append(indent)
                hier.append(line_num)

            while len(indent_levels) > 0:
                indent_levels.pop()
                con.execute(
                    "UPDATE nodes SET last=? WHERE id=?",
                    (line_num-1, hier.pop())
                )

        con.commit()
        return con
