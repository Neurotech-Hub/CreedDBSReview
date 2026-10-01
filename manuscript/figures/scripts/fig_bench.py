"""Figure 5: bench output into a 1 kOhm load.

Reads the three Joulescope JS220 recordings in data/bench (10, 50 and 100 %
amplitude settings, 180 us, 130 Hz), one output loaded with 1 kOhm, and writes
figures/fig5_bench.png. Delivered current is the voltage across the load
divided by 1 kOhm; the JS220 current channel shows range-switching spikes at
each edge and is not used. A 38 us median filter (passes steps, removes
impulses) is applied before analysis.

Usage (from manuscript/):  .venv/bin/python figures/scripts/fig_bench.py
"""

import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from pyjls import Reader  # noqa: E402
from scipy.ndimage import median_filter  # noqa: E402

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[2] / "data" / "bench"
OUT = HERE.parent / "fig5_bench.png"

R_LOAD = 1000.0
MEDIAN_US = 38
APP_UA_PER_PCT = 6.0
IDEAL_UA_PER_PCT = 6.25
COLORS = {10: "#1f77b4", 50: "#ff7f0e", 100: "#2ca02c"}


def load_voltage(path):
    r = Reader(str(path))
    try:
        fs = r.signals[2].sample_rate
        v = r.fsr(2, 0, r.signals[2].length).astype(float)
    finally:
        r.close()
    k = int(round(MEDIAN_US * 1e-6 * fs)) | 1
    return fs, median_filter(v, size=k, mode="nearest")


def onsets(v, fs):
    above = v > 0.5 * np.percentile(v, 99)
    edges = np.flatnonzero(above[1:] & ~above[:-1]) + 1
    return edges[np.insert(np.diff(edges) > fs * 1e-3, 0, True)]


def analyze(path, pw_us):
    fs, v = load_voltage(path)
    i_ua = v / R_LOAD * 1e6
    on = onsets(v, fs)[1:-1]
    pre, win = int(0.3e-3 * fs), int((6 * pw_us * 1e-6 + 0.8e-3) * fs)
    snips = np.array([i_ua[k - pre:k + win] for k in on])
    ts = np.arange(-pre, win) / fs * 1e6
    med = np.median(snips, axis=0)
    ph1 = (ts > 0.25 * pw_us) & (ts < 0.75 * pw_us)
    ph2 = (ts > 1.5 * pw_us) & (ts < 5.0 * pw_us)
    i1, i2 = med[ph1].mean(), med[ph2].mean()
    pos, neg = med > 0.5 * i1, med < 0.5 * i2
    period = int(np.median(np.diff(on)))
    full = np.array([i_ua[k - 200:k - 200 + period] for k in on[:-1]])
    per_pulse_i1 = snips[:, ph1].mean(axis=1)
    return dict(
        ts=ts, med=med, lo=np.percentile(snips, 5, axis=0), hi=np.percentile(snips, 95, axis=0),
        i1=i1, i2=i2, w1=pos.sum() / fs * 1e6, w2=neg.sum() / fs * 1e6,
        q1=med[pos].sum() / fs * 1e3, q2=med[neg].sum() / fs * 1e3,  # nC
        q_net=full.sum(axis=1).mean() / fs * 1e3,
        f_hz=fs / np.diff(on).mean(), jitter_us=np.diff(on).std() / fs * 1e6,
        i1_sd=per_pulse_i1.std(), n=len(on),
    )


def main():
    runs = {}
    for path in sorted(BENCH.glob("flexdbs_*p_*us_*Hz_*.jls")):
        pct, pw_us, f_hz = (int(g) for g in re.match(r"flexdbs_(\d+)p_(\d+)us_(\d+)Hz", path.name).groups())
        runs[pct] = analyze(path, pw_us)
    pcts = sorted(runs)

    plt.rcParams.update({"font.size": 9, "font.family": "sans-serif"})
    fig, axes = plt.subplot_mosaic([["A", "A"], ["B", "C"]], figsize=(7.0, 5.6),
                                   height_ratios=[1.1, 1], constrained_layout=True)

    ax = axes["A"]
    ax.axvspan(0, pw_us, color="0.9", zorder=0)
    ax.axvspan(pw_us, 6 * pw_us, color="0.96", zorder=0)
    ax.text(pw_us / 2, 590, f"{pw_us} µs", ha="center", va="top", fontsize=7, color="0.4")
    ax.text(3.5 * pw_us, 590, f"{5 * pw_us} µs (set)", ha="center", va="top", fontsize=7, color="0.4")
    for p in pcts:
        r = runs[p]
        ax.fill_between(r["ts"], r["lo"], r["hi"], color=COLORS[p], alpha=0.25, linewidth=0)
        ax.plot(r["ts"], r["med"], color=COLORS[p], linewidth=1.2, label=f"{p} %")
    ax.axhline(0, color="0.6", linewidth=0.5)
    ax.set(xlabel="Time from pulse onset (µs)", ylabel="Current into 1 kΩ (µA)",
           xlim=(-150, 1400), ylim=(-170, 600))
    ax.legend(title="Amplitude setting", fontsize=8, title_fontsize=8, frameon=False, loc="upper right")
    ax.set_title("A", loc="left", fontweight="bold")

    ax = axes["B"]
    x = np.array(pcts, dtype=float)
    xx = np.linspace(0, 100, 2)
    ax.plot(xx, APP_UA_PER_PCT * xx, color="0.5", linewidth=0.8, label="App label, 6 µA/%")
    ax.plot(xx, IDEAL_UA_PER_PCT * xx, color="0.5", linewidth=0.8, linestyle="--",
            label="Ideal, 6.25 µA/%")
    ax.plot(xx, -APP_UA_PER_PCT / 5 * xx, color="0.5", linewidth=0.8)
    ax.plot([], [], color="black", linewidth=0.8, linestyle=":", label="Linear fit")
    for key, marker, name in (("i1", "o", "Phase 1"), ("i2", "s", "Phase 2")):
        y = np.array([runs[p][key] for p in pcts])
        slope, icpt = np.polyfit(x, y, 1)
        ax.plot(xx, slope * xx + icpt, color="black", linewidth=0.8, linestyle=":")
        ax.scatter(x, y, c=[COLORS[p] for p in pcts], marker=marker, s=24, zorder=3,
                   edgecolor="black", linewidth=0.4)
        ax.scatter([], [], color="white", marker=marker, s=24, edgecolor="black", linewidth=0.6,
                   label=name)
        ax.text(102, slope * 100 + icpt, f"{slope:.2f} µA/%\n{icpt:+.0f} µA",
                fontsize=7, va="center")
        print(f"{name}: {slope:.3f} uA/% {icpt:+.1f} uA")
    ax.axhline(0, color="0.6", linewidth=0.5)
    ax.set(xlabel="Amplitude setting (%)", ylabel="Delivered current (µA)", xlim=(0, 125),
           xticks=[0, 10, 50, 100])
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax.set_title("B", loc="left", fontweight="bold")

    ax = axes["C"]
    idx = np.arange(len(pcts))
    q1 = [runs[p]["q1"] for p in pcts]
    q2 = [runs[p]["q2"] for p in pcts]
    qn = [runs[p]["q_net"] for p in pcts]
    ax.bar(idx, q1, width=0.6, color=[COLORS[p] for p in pcts])
    ax.bar(idx, q2, width=0.6, color=[COLORS[p] for p in pcts], alpha=0.45)
    ax.bar([0], [0], color="0.35", label="Phase 1")
    ax.bar([0], [0], color="0.35", alpha=0.45, label="Phase 2")
    ax.scatter(idx, qn, color="black", marker="D", s=20, zorder=3, label="Net per period")
    for k, (a, n) in enumerate(zip(q1, qn)):
        ax.text(k + 0.34, n, f"{n:+.0f}", fontsize=7, va="center")
    ax.axhline(0, color="0.6", linewidth=0.5)
    ax.set(xticks=idx, xticklabels=[f"{p} %" for p in pcts], xlabel="Amplitude setting",
           ylabel="Charge per pulse (nC)")
    ax.legend(fontsize=7, frameon=False, loc="upper left")
    ax.set_title("C", loc="left", fontweight="bold")

    for a in axes.values():
        a.spines[["top", "right"]].set_visible(False)

    fig.savefig(OUT, dpi=300)
    print(f"wrote {OUT}")
    for p in pcts:
        r = runs[p]
        print(f"{p:3d}%: n={r['n']} f={r['f_hz']:.2f} Hz jitter={r['jitter_us']:.1f} us "
              f"I1={r['i1']:.1f} (SD {r['i1_sd']:.2f}) I2={r['i2']:.1f} uA ratio={r['i1'] / -r['i2']:.2f} "
              f"w1={r['w1']:.0f} w2={r['w2']:.0f} us q1={r['q1']:.1f} q2={r['q2']:.1f} "
              f"net={r['q_net']:.1f} nC ({100 * r['q_net'] / r['q1']:.0f} %)")


if __name__ == "__main__":
    main()
