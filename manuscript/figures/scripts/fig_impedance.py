"""Figure 4: in-vivo electrode impedance and the compliance envelope.

Reads the "platinum cohort 1" (M1, M2 = mice 1, 2) and "platinum cohort 2"
(F1, F2 = mice 3, 4) sheets of data/impedance/mousehatImpedance.xlsx, using the
per-week mean rows for both outputs of each mouse except mouse 1 output 0, and
writes figures/fig4_impedance.png.

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

SHEETS = {
    "platinum cohort 1": {"M1": "Mouse 1", "M2": "Mouse 2"},
    "platinum cohort 2": {"F1": "Mouse 3", "F2": "Mouse 4"},
}
OUTPUT_COLUMNS = {0: "D", 1: "I"}  # resistance (kOhm) column for each output
EXCLUDE = {("Mouse 1", 0)}  # reads ~0 V at every session (short to return)

SWING_V = 4.9  # approximate output swing of the Howland stage on +/-5 V rails
SERIES_OHM = 2000 + 660  # sense resistor plus output filter resistance
BATTERY_V = 3.0  # illustrative battery-direct compliance
REFERENCE_UA = 100  # reference protocol amplitude

COLORS = {
    "Mouse 1": "#1f77b4",
    "Mouse 2": "#d62728",
    "Mouse 3": "#2ca02c",
    "Mouse 4": "#9467bd",
}

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


def weekly_means(cells, labels):
    """{(mouse, output): [(week, kOhm), ...]} from the per-week mean rows."""
    rows = sorted({int(re.sub(r"\D", "", ref)) for ref in cells})
    data = {}
    week = None
    mouse = None
    for row in rows:
        a = cells.get(f"A{row}", "")
        match = re.match(r"(\d+) weeks? post implant", a)
        if match:
            week = int(match.group(1))
        elif a in labels:
            mouse = labels[a]
        elif a == "mean" and week is not None and mouse is not None:
            for output, col in OUTPUT_COLUMNS.items():
                if (mouse, output) in EXCLUDE:
                    continue
                data.setdefault((mouse, output), []).append(
                    (week, float(cells[f"{col}{row}"]))
                )
    return data


def i_max_ua(z_kohm, volts, series_ohm):
    return volts / (z_kohm * 1e3 + series_ohm) * 1e6


def main():
    data = {}
    for sheet, labels in SHEETS.items():
        data.update(weekly_means(read_sheet(XLSX, sheet), labels))

    plt.rcParams.update({"font.size": 9, "font.family": "sans-serif"})
    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(7.0, 3.2), constrained_layout=True)

    for (mouse, output), points in sorted(data.items()):
        weeks, z = zip(*points)
        ax_a.plot(
            weeks,
            z,
            marker="o" if output == 1 else "s",
            linestyle="-" if output == 1 else "--",
            markerfacecolor=COLORS[mouse] if output == 1 else "white",
            color=COLORS[mouse],
            markersize=4,
            linewidth=1,
        )
    max_week = max(w for points in data.values() for w, _ in points)
    ax_a.set_xlabel("Weeks after implantation")
    ax_a.set_ylabel("Impedance (kΩ)")
    ax_a.set_xticks(range(1, max_week + 1))
    mouse_handles = [
        plt.Line2D([], [], color=c, marker="o", linewidth=1, markersize=4, label=m)
        for m, c in COLORS.items()
    ]
    output_handles = [
        plt.Line2D([], [], color="black", marker="o", linestyle="-", linewidth=1,
                   markersize=4, label="Output 1"),
        plt.Line2D([], [], color="black", marker="s", linestyle="--", linewidth=1,
                   markersize=4, markerfacecolor="white", label="Output 0"),
    ]
    ax_a.legend(handles=mouse_handles + output_handles, frameon=False,
                loc="upper center", ncol=3, fontsize=7)
    ax_a.set_ylim(0, 150)
    ax_a.set_title("A", loc="left", fontweight="bold")

    z_grid = [i / 2 for i in range(2, 281)]
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
    ax_b.text(138, REFERENCE_UA + 8, "100 µA", ha="right", va="bottom", color="gray")
    for (mouse, output), points in sorted(data.items()):
        z = [p[1] for p in points]
        ax_b.plot(
            z,
            [i_max_ua(v, SWING_V, SERIES_OHM) for v in z],
            "o" if output == 1 else "s",
            color=COLORS[mouse],
            markerfacecolor=COLORS[mouse] if output == 1 else "white",
            markersize=4,
        )
    ax_b.set_xlabel("Load impedance (kΩ)")
    ax_b.set_ylabel("Maximum regulated current (µA)")
    ax_b.set_xlim(0, 140)
    ax_b.set_ylim(0, 600)
    ax_b.legend(frameon=False, loc="upper right")
    ax_b.set_title("B", loc="left", fontweight="bold")

    for ax in (ax_a, ax_b):
        ax.spines[["top", "right"]].set_visible(False)

    fig.savefig(OUT, dpi=300)
    print(f"wrote {OUT}")
    for (mouse, output), points in sorted(data.items()):
        print(mouse, f"output {output}:", ", ".join(f"w{w} {z:.1f}" for w, z in points))


if __name__ == "__main__":
    main()
