"""Build behavior_key.csv from the session folders in the MouseHatDBS Box folder.

Each session folder is named YYMMDD_<subject>[_active]_<condition>, where
condition is "sham" or the stimulation parameters starting at "<N>percent". Fields are parsed
from the folder name, which is more consistent than the CSV file names inside it.
Only file names are listed; no files (in particular the .avi videos) are opened.

Usage:  python3 data/behavior/build_key.py
"""

import csv
import re
from pathlib import Path

BOX = Path.home() / "Library" / "CloudStorage" / "Box-Box" / "MouseHatDBS"
OUT = Path(__file__).resolve().parent / "behavior_key.csv"

SESSION = re.compile(
    r"^(?P<date>\d{6})_(?P<subject>.+?)(?:_active)?_(?P<condition>sham|\d*percent.*)$"
)


def main():
    rows = []
    unparsed = []
    for csv_path in sorted(BOX.glob("*/*.csv")):
        folder = csv_path.parent.name
        match = SESSION.match(folder)
        if not match:
            unparsed.append(folder)
            continue
        d = match.group("date")
        rows.append(
            {
                "date": f"20{d[:2]}-{d[2:4]}-{d[4:]}",
                "subject": match.group("subject"),
                "condition": match.group("condition"),
                "csv_file": csv_path.relative_to(BOX).as_posix(),
            }
        )

    with OUT.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "subject", "condition", "csv_file"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {len(rows)} rows to {OUT}")
    for folder in sorted(set(unparsed)):
        print(f"could not parse: {folder}")


if __name__ == "__main__":
    main()
