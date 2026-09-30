"""Figure 4: in-vivo electrode impedance and the compliance envelope.

Reads the "platinum cohort 1" sheet of data/impedance/mousehatImpedance.xlsx
(output 1 per mouse, per-week mean rows) and writes figures/fig4_impedance.png.

Usage (from manuscript/):  .venv/bin/python figures/scripts/fig_impedance.py
"""

import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).resolve().parent
XLSX = HERE.parents[2] / "data" / "impedance" / "mousehatImpedance.xlsx"
OUT = HERE.parent / "fig4_impedance.png"
SHEET = "platinum cohort 1"

SWING_V = 4.9  # approximate output swing of the Howland stage on +/-5 V rails
SERIES_OHM = 2000 + 660  # sense resistor plus output filter resistance
BATTERY_V = 3.0  # illustrative battery-direct compliance
REFERENCE_UA = 100  # reference protocol amplitude

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def read_sheet(path, name):
    """Return {cell_ref: value} for one worksheet, using only the stdlib."""
    z = zipfile.ZipFile(path)
    strings = [
        "".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t"))
        for si in ET.fromstring(z.read("xl/sharedStrings.xml"))
    ]
    rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
    targets = {r.get("Id"): r.get("Target") for r in rels}
    workbook = ET.fromstring(z.read("xl/workbook.xml"))
    for sheet in workbook.find("m:sheets", NS):
        if sheet.get("name") != name:
            continue
        target = targets[sheet.get(f"{{{NS['r']}}}id")].lstrip("/")
        if not target.startswith("xl/"):
            target = "xl/" + target
        cells = {}
        for c in ET.fromstring(z.read(target)).iter(f"{{{NS['m']}}}c"):
            v = c.find("m:v", NS)
            if v is None:
                continue
            cells[c.get("r")] = strings[int(v.text)] if c.get("t") == "s" else v.text
        return cells
    raise KeyError(f"sheet {name!r} not found in {path}")


def output1_means(cells):
    """Per-week output-1 mean impedance (kOhm) for each mouse, in sheet order."""
    rows = sorted({int(re.sub(r"\D", "", ref)) for ref in cells})
    data = {}
    week = None
    mouse = None
    for row in rows:
        a = cells.get(f"A{row}", "")
        match = re.match(r"(\d+) weeks? post implant", a)
        if match:
            week = int(match.group(1))
        elif re.fullmatch(r"M\d+", a):
            mouse = a
        elif a == "mean" and week is not None and mouse is not None:
            data.setdefault(mouse, []).append((week, float(cells[f"I{row}"])))
    return data


def i_max_ua(z_kohm, volts, series_ohm):
    return volts / (z_kohm * 1e3 + series_ohm) * 1e6


def main():
    data = output1_means(read_sheet(XLSX, SHEET))
    labels = {"M1": "Mouse 1", "M2": "Mouse 2"}
    colors = {"M1": "#1f77b4", "M2": "#d62728"}

    plt.rcParams.update({"font.size": 9, "font.family": "sans-serif"})
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.0, 3.0), constrained_layout=True)

    for mouse, points in data.items():
        weeks, z = zip(*points)
        ax_a.plot(weeks, z, "o-", color=colors[mouse], label=labels[mouse])
    ax_a.set_xlabel("Weeks after implantation")
    ax_a.set_ylabel("Impedance (kΩ)")
    ax_a.set_xticks(range(1, 6))
    ax_a.set_ylim(0, 90)
    ax_a.legend(frameon=False, loc="lower right")
    ax_a.set_title("A", loc="left", fontweight="bold")

    z_grid = [i / 2 for i in range(2, 241)]
    ax_b.plot(
        z_grid,
        [i_max_ua(z, SWING_V, SERIES_OHM) for z in z_grid],
        color="black",
        label="FLEX-DBS (±5 V rails)",
    )
    ax_b.plot(
        z_grid,
        [i_max_ua(z, BATTERY_V, 0) for z in z_grid],
        color="gray",
        linestyle="--",
        label="Battery-direct (~3 V)",
    )
    ax_b.axhline(REFERENCE_UA, color="gray", linewidth=0.8, linestyle=":")
    ax_b.text(118, REFERENCE_UA + 8, "100 µA", ha="right", va="bottom", color="gray")
    for mouse, points in data.items():
        z = [p[1] for p in points]
        ax_b.plot(
            z,
            [i_max_ua(v, SWING_V, SERIES_OHM) for v in z],
            "o",
            color=colors[mouse],
            label=labels[mouse],
        )
    ax_b.set_xlabel("Load impedance (kΩ)")
    ax_b.set_ylabel("Maximum regulated current (µA)")
    ax_b.set_xlim(0, 120)
    ax_b.set_ylim(0, 600)
    ax_b.legend(frameon=False, loc="upper right")
    ax_b.set_title("B", loc="left", fontweight="bold")

    for ax in (ax_a, ax_b):
        ax.spines[["top", "right"]].set_visible(False)

    fig.savefig(OUT, dpi=300)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
