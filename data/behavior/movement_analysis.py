"""Sham vs stim total movement from Item2.X / Item2.Y tracking (first pass).

For each session in behavior_key.csv with include and valid_xy_data True:
drop leading rows until X and Y are both valid, linearly inpaint remaining NaNs
(trailing NaNs take the last valid value), sum frame-to-frame Euclidean steps,
and divide by the retained duration. Sham and stim sessions are compared as two
groups with a two-sided permutation test on the difference in means.

Only the included .csv files are opened; nothing in Box is written.

Usage:  manuscript/.venv/bin/python data/behavior/movement_analysis.py
"""

import csv
import math
import random
import re
import statistics
from datetime import datetime
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

BOX = Path.home() / "Library" / "CloudStorage" / "Box-Box" / "MouseHatDBS"
HERE = Path(__file__).resolve().parent
KEY = HERE / "behavior_key.csv"
SUMMARY = HERE / "movement_summary.csv"
FIGURE = HERE / "movement_sham_vs_stim.png"
TIMELINE = HERE / "movement_timeline.png"
BIN_S = 60

N_PERMUTATIONS = 10_000
SEED = 0


def parse_float(value):
    try:
        return float(value)
    except ValueError:
        return math.nan


def parse_time(value):
    # Bonsai writes 7 fractional digits; datetime accepts at most 6.
    return datetime.fromisoformat(re.sub(r"(\.\d{6})\d+", r"\1", value))


def load_track(path):
    """Return (timestamps, xs, ys) starting at the first row with valid X and Y."""
    with path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        it, ix, iy = (header.index(c) for c in ("Item1.Timestamp", "Item2.X", "Item2.Y"))
        times, xs, ys = [], [], []
        started = False
        for row in reader:
            x, y = parse_float(row[ix]), parse_float(row[iy])
            bad = math.isnan(x) or math.isnan(y)
            if not started:
                if bad:
                    continue
                started = True
            times.append(row[it])
            xs.append(math.nan if bad else x)
            ys.append(math.nan if bad else y)
    return times, xs, ys


def inpaint(values):
    """Linear interpolation over NaN runs; trailing NaNs take the last valid value."""
    out = list(values)
    last = None
    i = 0
    while i < len(out):
        if not math.isnan(out[i]):
            last = i
            i += 1
            continue
        j = i
        while j < len(out) and math.isnan(out[j]):
            j += 1
        if j == len(out):
            for k in range(i, j):
                out[k] = out[last]
        else:
            a, b = out[last], out[j]
            span = j - last
            for k in range(i, j):
                out[k] = a + (b - a) * (k - last) / span
        i = j
    return out


def analyze(path):
    times, xs, ys = load_track(path)
    n_inpainted = sum(math.isnan(x) or math.isnan(y) for x, y in zip(xs, ys))
    xs, ys = inpaint(xs), inpaint(ys)
    t0 = parse_time(times[0])
    elapsed = [(parse_time(t) - t0).total_seconds() for t in times]
    steps = [math.hypot(xs[k] - xs[k - 1], ys[k] - ys[k - 1]) for k in range(1, len(xs))]
    distance = sum(steps)
    duration_min = elapsed[-1] / 60
    n_bins = int(elapsed[-1] // BIN_S)
    binned = [0.0] * n_bins
    for k, step in enumerate(steps, start=1):
        b = int(elapsed[k] // BIN_S)
        if b < n_bins:
            binned[b] += step
    return {
        "timeline_px_per_min": [d * 60 / BIN_S for d in binned],
        "n_frames": len(xs),
        "n_inpainted": n_inpainted,
        "duration_min": duration_min,
        "total_distance_px": distance,
        "distance_px_per_min": distance / duration_min,
    }


def permutation_p(a, b, n, seed):
    rng = random.Random(seed)
    observed = abs(statistics.mean(b) - statistics.mean(a))
    pooled = a + b
    hits = 0
    for _ in range(n):
        rng.shuffle(pooled)
        pa, pb = pooled[: len(a)], pooled[len(a):]
        if abs(statistics.mean(pb) - statistics.mean(pa)) >= observed:
            hits += 1
    return (hits + 1) / (n + 1)


def main():
    with KEY.open(newline="") as f:
        sessions = [
            r
            for r in csv.DictReader(f)
            if r.get("include") == "True" and r.get("valid_xy_data") == "True"
        ]

    results = []
    for s in sessions:
        r = {
            "date": s["date"],
            "subject": s["subject"],
            "condition": s["condition"],
            "group": "sham" if s["condition"] == "sham" else "stim",
        }
        r.update(analyze(BOX / s["csv_file"]))
        results.append(r)
        print(
            f"{r['date']}  {r['subject']:10s} {r['group']:4s} "
            f"{r['duration_min']:5.1f} min  {r['distance_px_per_min']:8.1f} px/min"
        )

    fields = ["date", "subject", "condition", "group", "n_frames", "n_inpainted",
              "duration_min", "total_distance_px", "distance_px_per_min"]
    with SUMMARY.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for r in results:
            writer.writerow(
                {
                    **r,
                    "duration_min": f"{r['duration_min']:.3f}",
                    "total_distance_px": f"{r['total_distance_px']:.1f}",
                    "distance_px_per_min": f"{r['distance_px_per_min']:.2f}",
                }
            )

    sham = [r["distance_px_per_min"] for r in results if r["group"] == "sham"]
    stim = [r["distance_px_per_min"] for r in results if r["group"] == "stim"]
    p = permutation_p(sham, stim, N_PERMUTATIONS, SEED)
    diff = statistics.mean(stim) - statistics.mean(sham)
    print()
    print(f"sham: {statistics.mean(sham):.1f} ± {statistics.stdev(sham):.1f} px/min (n = {len(sham)})")
    print(f"stim: {statistics.mean(stim):.1f} ± {statistics.stdev(stim):.1f} px/min (n = {len(stim)})")
    print(f"stim − sham: {diff:.1f} px/min ({100 * diff / statistics.mean(sham):+.1f} %), "
          f"permutation p = {p:.4f} ({N_PERMUTATIONS} shuffles)")

    plt.rcParams.update({"font.size": 9, "font.family": "sans-serif"})
    fig, ax = plt.subplots(figsize=(3.0, 3.2), constrained_layout=True)
    rng = random.Random(SEED)
    for k, (label, values) in enumerate((("Sham", sham), ("Stim", stim))):
        xs = [k + rng.uniform(-0.12, 0.12) for _ in values]
        ax.plot(xs, values, "o", color="0.55", markersize=4, alpha=0.8)
        ax.errorbar(k + 0.3, statistics.mean(values), yerr=statistics.stdev(values),
                    color="black", marker="s", markersize=5, capsize=3)
    ax.set_xticks([0, 1])
    ax.set_xticklabels([f"Sham\n(n = {len(sham)})", f"Stim\n(n = {len(stim)})"])
    ax.set_xlim(-0.5, 1.6)
    ax.set_ylim(bottom=0)
    ax.set_ylabel("Movement (px/min)")
    ax.set_title(f"permutation p = {p:.3f}", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(FIGURE, dpi=300)

    fig, ax = plt.subplots(figsize=(7.0, 3.2), constrained_layout=True)
    for r in sorted(results, key=lambda r: r["group"] == "stim"):
        series = r["timeline_px_per_min"]
        minutes = [(b + 0.5) * BIN_S / 60 for b in range(len(series))]
        ax.plot(minutes, series, color="black" if r["group"] == "stim" else "#d62728",
                linewidth=0.9, alpha=0.7)
    ax.plot([], [], color="black", label=f"Stim (n = {len(stim)})")
    ax.plot([], [], color="#d62728", label=f"Sham (n = {len(sham)})")
    ax.set_xlabel("Time from recording start (min)")
    ax.set_ylabel(f"Movement (px/min, {BIN_S} s bins)")
    ax.set_xlim(left=0)
    ax.set_ylim(bottom=0)
    ax.legend(frameon=False, loc="upper right")
    ax.spines[["top", "right"]].set_visible(False)
    fig.savefig(TIMELINE, dpi=300)
    print(f"wrote {SUMMARY.name}, {FIGURE.name} and {TIMELINE.name}")


if __name__ == "__main__":
    main()
