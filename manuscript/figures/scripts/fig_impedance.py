"""Figure 4: in-vivo electrode impedance and the compliance envelope.

Reads the "platinum cohort 1" (M1, M2 = mice 1, 2) and "platinum cohort 2"
(F1, F2 = mice 3, 4) sheets of data/impedance/mousehatImpedance.xlsx, using the
per-week mean rows for both outputs of each mouse except mouse 1 output 0, and
writes figures/fig4_impedance.png.

Usage (from manuscript/):  .venv/bin/python figures/scripts/fig_impedance.py
"""

import re
import statistics
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
EXCLUDE_MICE = {"Mouse 3"}

SWING_V = 4.60  # stimulating-phase swing measured into 47 kOhm: 92.6 uA x (47 kOhm + SERIES_OHM)
SERIES_OHM = 2000 + 660  # sense resistor plus output filter resistance
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
                if (mouse, output) in EXCLUDE or mouse in EXCLUDE_MICE:
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
    fig, axes = plt.subplot_mosaic(
        [["A", "B"], ["A", "S"]],
        figsize=(7.0, 3.6),
        height_ratios=[3, 1.4],
        constrained_layout=True,
    )
    ax_a, ax_b, ax_s = axes["A"], axes["B"], axes["S"]
    ax_s.sharex(ax_b)

    by_week = {}
    for points in data.values():
        for week, z in points:
            by_week.setdefault(week, []).append(z)
    weeks = sorted(by_week)
    means = [statistics.mean(by_week[w]) for w in weeks]
    sds = [statistics.stdev(by_week[w]) for w in weeks]
    ax_a.errorbar(weeks, means, yerr=sds, color="black", marker="o", markersize=4,
                  linewidth=1, capsize=3, label=f"Mean ± SD ({len(data)} electrodes)")
    ax_a.legend(fontsize=7, frameon=False, loc="upper right")
    ax_a.set_xlabel("Weeks after implantation")
    ax_a.set_ylabel("Impedance (kΩ)")
    ax_a.set_xticks(weeks)
    ax_a.set_ylim(0, 90)
    ax_a.set_title("A", loc="left", fontweight="bold")

    z_max = 100
    z_grid = [i / 4 for i in range(4, 4 * z_max + 1)]
    ax_b.plot(z_grid, [i_max_ua(z, SWING_V, SERIES_OHM) for z in z_grid],
              color="black", linewidth=1.2, label="Compliance limit")
    z_lo, z_hi = min(means), max(means)
    i_hi, i_lo = (i_max_ua(z, SWING_V, SERIES_OHM) for z in (z_lo, z_hi))
    ax_b.axvspan(z_lo, z_hi, color="0.85", zorder=0, label="Weekly mean range")
    band = [z for z in z_grid if z_lo <= z <= z_hi]
    ax_b.plot(band, [i_max_ua(z, SWING_V, SERIES_OHM) for z in band],
              color="black", linewidth=3)
    for k, (z, i) in enumerate(((z_lo, i_hi), (z_hi, i_lo))):
        ax_b.plot([0, z], [i, i], color="0.4", linewidth=0.8, linestyle="--",
                  label="Projected range" if k == 0 else None)
    ax_b.text(z_hi + 2, i_hi + 12, f"{i_lo:.0f}–{i_hi:.0f} µA", ha="left", va="bottom")
    ax_b.axhline(REFERENCE_UA, color="gray", linewidth=0.8, linestyle=":",
                 label="Reference protocol")
    ax_b.legend(fontsize=6.5, frameon=False, loc="upper right", borderaxespad=0,
                handlelength=1.5)
    ax_b.text(z_max - 1, REFERENCE_UA - 8, "100 µA", ha="right", va="top", color="gray")
    ax_b.set_ylabel("Maximum regulated\ncurrent (µA)")
    ax_b.set_ylim(0, 300)
    ax_b.tick_params(labelbottom=False)
    ax_b.set_title("B", loc="left", fontweight="bold")

    cmap = plt.get_cmap("viridis")
    ax_s.axvspan(z_lo, z_hi, color="0.85", zorder=0)
    for k, (w, m, sd) in enumerate(zip(weeks, means, sds)):
        c = cmap(k / max(len(weeks) - 1, 1))
        ax_s.errorbar(m, w, xerr=sd, color=c, marker="o", markersize=3.5,
                      linewidth=1, capsize=2,
                      label="Weekly mean ± SD" if k == len(weeks) // 2 else None)
    ax_s.legend(fontsize=6.5, frameon=False, loc="lower right", borderaxespad=0,
                handlelength=1.5)
    ax_s.set_ylim(min(weeks) - 0.7, max(weeks) + 0.7)
    ax_s.set_yticks([min(weeks), max(weeks)])
    ax_s.set_ylabel("Week")
    ax_s.set_xlabel("Load impedance (kΩ)")
    ax_s.set_xlim(0, z_max)

    for ax in (ax_a, ax_b, ax_s):
        ax.spines[["top", "right"]].set_visible(False)

    fig.savefig(OUT, dpi=300)
    print(f"wrote {OUT}")
    for (mouse, output), points in sorted(data.items()):
        print(mouse, f"output {output}:", ", ".join(f"w{w} {z:.1f}" for w, z in points))
    for w, m, s in zip(weeks, means, sds):
        print(f"week {w}: {m:.1f} ± {s:.1f} kΩ (n = {len(by_week[w])})")


if __name__ == "__main__":
    main()
