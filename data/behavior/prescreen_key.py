"""Add include / valid_xy_data columns to behavior_key.csv.

include: date on or after START_DATE and condition is "sham" or >= MIN_PERCENT.
valid_xy_data (included rows only): in the CSV's Item2.X / Item2.Y columns, drop
leading rows until the first row where both are numbers; of the remaining rows,
the fraction with X or Y NaN (to be inpainted) must not exceed MAX_NAN_FRACTION.

Only the included .csv files are opened; nothing in Box is written.

Usage:  python3 data/behavior/prescreen_key.py   (after build_key.py)
"""

import csv
import math
import re
from pathlib import Path

START_DATE = "2025-12-18"
MIN_PERCENT = 50
MAX_NAN_FRACTION = 0.20

BOX = Path.home() / "Library" / "CloudStorage" / "Box-Box" / "MouseHatDBS"
KEY = Path(__file__).resolve().parent / "behavior_key.csv"
BASE_COLUMNS = ["date", "subject", "condition", "csv_file"]
NEW_COLUMNS = ["include", "valid_xy_data", "n_rows", "n_leading_dropped", "nan_fraction"]


def is_included(row):
    if row["date"] < START_DATE:
        return False
    if row["condition"] == "sham":
        return True
    match = re.match(r"(\d+)percent", row["condition"])
    return bool(match) and int(match.group(1)) >= MIN_PERCENT


def parse(value):
    try:
        v = float(value)
    except ValueError:
        return math.nan
    return v


def screen_xy(path):
    """Return (n_rows, n_leading_dropped, nan_fraction or None if never valid)."""
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        ix, iy = header.index("Item2.X"), header.index("Item2.Y")
        n_rows = 0
        first_valid = None
        n_nan_after = 0
        for row in reader:
            x, y = parse(row[ix]), parse(row[iy])
            bad = math.isnan(x) or math.isnan(y)
            if first_valid is None and not bad:
                first_valid = n_rows
            elif first_valid is not None and bad:
                n_nan_after += 1
            n_rows += 1
    if first_valid is None:
        return n_rows, n_rows, None
    return n_rows, first_valid, n_nan_after / (n_rows - first_valid)


def main():
    with KEY.open(newline="") as f:
        rows = list(csv.DictReader(f))

    for row in rows:
        for col in NEW_COLUMNS:
            row[col] = ""
        if not is_included(row):
            row["include"] = "False"
            continue
        row["include"] = "True"
        n_rows, n_drop, frac = screen_xy(BOX / row["csv_file"])
        row["n_rows"] = n_rows
        row["n_leading_dropped"] = n_drop
        row["nan_fraction"] = "" if frac is None else f"{frac:.4f}"
        row["valid_xy_data"] = str(frac is not None and frac <= MAX_NAN_FRACTION)

    with KEY.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=BASE_COLUMNS + NEW_COLUMNS, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)

    included = [r for r in rows if r["include"] == "True"]
    valid = [r for r in included if r["valid_xy_data"] == "True"]
    print(f"{len(included)} of {len(rows)} rows included; {len(valid)} with valid XY data")
    for r in included:
        print(
            f"{r['date']}  {r['subject']:10s} {r['condition']:22s} "
            f"rows={r['n_rows']:>6}  lead_drop={r['n_leading_dropped']:>5}  "
            f"nan={r['nan_fraction'] or 'n/a':>6}  valid={r['valid_xy_data']}"
        )


if __name__ == "__main__":
    main()
