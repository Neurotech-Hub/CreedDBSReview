"""Figure 5: bench output into 1 kOhm and 47 kOhm loads.

Reads the Joulescope JS220 recordings in data/bench (10, 50 and 100 %
amplitude settings, 180 us, 130 Hz; load from the _<n>k_ filename token,
1 kOhm if absent) and writes figures/fig5_bench.png. Panel A shows the 1 kOhm
recordings; panels B and C compare both loads. 0 % recordings are skipped.
Delivered current is the voltage across the load divided by the load; the
JS220 current channel shows range-switching spikes at each edge and is not
used. A 38 us median filter (passes steps, removes impulses) is applied
before analysis.

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

MEDIAN_US = 38
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


def analyze(path, pw_us, r_load):
    fs, v = load_voltage(path)
    i_ua = v / r_load * 1e6
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
    late2 = (ts > 3.0 * pw_us) & (ts < 5.0 * pw_us)
    return dict(
        i1_peak=med[(ts > 0) & (ts < 1.5 * pw_us)].max(), i2_late=np.median(med[late2]),
        ts=ts, med=med, lo=np.percentile(snips, 5, axis=0), hi=np.percentile(snips, 95, axis=0),
        i1=i1, i2=i2, w1=pos.sum() / fs * 1e6, w2=neg.sum() / fs * 1e6,
        q1=med[pos].sum() / fs * 1e3, q2=med[neg].sum() / fs * 1e3,  # nC
        q_net=full.sum(axis=1).mean() / fs * 1e3,
        f_hz=fs / np.diff(on).mean(), jitter_us=np.diff(on).std() / fs * 1e6,
        i1_sd=per_pulse_i1.std(), n=len(on),
    )


def main():
    runs = {}
    pat = r"flexdbs_(\d+)p_(\d+)us_(\d+)Hz(?:_(\d+)k)?_"
    for path in sorted(BENCH.glob("flexdbs_*p_*us_*Hz_*.jls")):
        m = re.match(pat, path.name)
        pct, pw_us, f_hz = (int(g) for g in m.groups()[:3])
        rk = int(m.group(4) or 1)
        if pct == 0:
            continue
        runs[rk, pct] = analyze(path, pw_us, rk * 1000.0)
    loads = sorted({k for k, _ in runs})
    pcts = sorted({p for _, p in runs})
    hi = max(loads)

    plt.rcParams.update({"font.size": 9, "font.family": "sans-serif"})
    fig, axes = plt.subplot_mosaic([["A", "A"], ["B", "C"]], figsize=(7.0, 5.6),
                                   height_ratios=[1.1, 1], constrained_layout=True)

    ax = axes["A"]
    ax.axvspan(0, pw_us, color="0.9", zorder=0)
    ax.axvspan(pw_us, 6 * pw_us, color="0.96", zorder=0)
    ax.text(pw_us / 2, 590, f"{pw_us} µs", ha="center", va="top", fontsize=7, color="0.4")
    ax.text(3.5 * pw_us, 590, f"{5 * pw_us} µs (set)", ha="center", va="top", fontsize=7, color="0.4")
    for p in pcts:
        r = runs[1, p]
        ax.fill_between(r["ts"], r["lo"], r["hi"], color=COLORS[p], alpha=0.25, linewidth=0)
        ax.plot(r["ts"], r["med"], color=COLORS[p], linewidth=1.2, label=f"{p} %")
    ax.axhline(0, color="0.6", linewidth=0.5)
    ax.set(xlabel="Time from pulse onset (µs)", ylabel="Current into 1 kΩ (µA)",
           xlim=(-150, 1400), ylim=(-170, 600))
    ax.legend(title="Amplitude setting", fontsize=8, title_fontsize=8, frameon=False, loc="upper right")
    ax.set_title("A", loc="left", fontweight="bold")

    ax = axes["B"]
    x = np.array(pcts, dtype=float)
    for key, name in (("i1", "Phase 1"), ("i2", "Phase 2")):
        yk = np.array([runs[1, p][key] for p in pcts])
        sk, ck = np.polyfit(x, yk, 1)
        print(f"{name}: {sk:.3f} uA/% {ck:+.1f} uA")
    y = np.array([runs[1, p]["i1"] for p in pcts])
    y_hi = np.array([runs[hi, p]["i1"] for p in pcts])
    ceiling = y_hi.max()
    ax.axhline(ceiling, color="0.75", linewidth=0.6, linestyle=":", zorder=0)
    ax.text(57, ceiling + 12, f"{hi} kΩ compliance limit ({ceiling:.0f} µA)", fontsize=6.5,
            color="0.55", va="bottom")
    ax.plot(x, y, color="black", linewidth=0.8, zorder=2)
    ax.plot(x, y_hi, color="black", linewidth=0.8, zorder=2)
    ax.scatter(x, y, c=[COLORS[p] for p in pcts], s=30, zorder=3, edgecolor="black",
               linewidth=0.4, label="1 kΩ")
    ax.scatter(x, y_hi, facecolor="white", edgecolor=[COLORS[p] for p in pcts], s=30, zorder=3,
               linewidth=1.2, label=f"{hi} kΩ")
    ax.set(xlabel="Amplitude setting (%)", ylabel="Stimulating-phase current (µA)",
           xlim=(0, 110), ylim=(0, 650), xticks=[0, 10, 50, 100])
    leg = ax.legend(fontsize=7, frameon=False, loc="upper left")
    for h in leg.legend_handles:
        h.set_facecolor("white" if h.get_label().startswith(f"{hi}") else "0.5")
        h.set_edgecolor("0.3")
    ax.set_title("B", loc="left", fontweight="bold")

    ax = axes["C"]
    idx = np.arange(len(pcts))
    w = 0.36
    for j, rk in enumerate(loads):
        off = (j - (len(loads) - 1) / 2) * (w + 0.04)
        hatch = None if rk == 1 else "////"
        cols = [COLORS[p] for p in pcts]
        q1 = [runs[rk, p]["q1"] for p in pcts]
        q2 = [runs[rk, p]["q2"] for p in pcts]
        qn = [runs[rk, p]["q_net"] for p in pcts]
        ax.bar(idx + off, q1, width=w, color=cols, hatch=hatch, edgecolor="white", linewidth=0)
        ax.bar(idx + off, q2, width=w, color=cols, alpha=0.45, hatch=hatch, edgecolor="white",
               linewidth=0)
        ax.scatter(idx + off, qn, color="black", marker="D", s=14, zorder=3)
        for k, n in enumerate(qn):
            ax.text(idx[k] + off, max(q1[k], 0) + 4, f"{n:+.0f}", fontsize=6.5, ha="center",
                    va="bottom")
    ax.bar([0], [0], color="0.35", label="Phase 1")
    ax.bar([0], [0], color="0.35", alpha=0.45, label="Phase 2")
    ax.bar([0], [0], color="0.6", label="1 kΩ")
    ax.bar([0], [0], color="0.6", hatch="////", edgecolor="white", linewidth=0, label=f"{hi} kΩ")
    ax.scatter([], [], color="black", marker="D", s=14, label="Net per period (labeled)")
    ax.axhline(0, color="0.6", linewidth=0.5)
    ax.set(xticks=idx, xticklabels=[f"{p} %" for p in pcts], xlabel="Amplitude setting",
           ylabel="Charge per pulse (nC)", ylim=(-110, 215))
    ax.legend(fontsize=7, frameon=False, loc="upper left", ncol=2)
    ax.set_title("C", loc="left", fontweight="bold")

    for a in axes.values():
        a.spines[["top", "right"]].set_visible(False)

    fig.savefig(OUT, dpi=300)
    print(f"wrote {OUT}")
    for rk, p in sorted(runs):
        r = runs[rk, p]
        print(f"{rk:2d}k {p:3d}%: n={r['n']} f={r['f_hz']:.2f} Hz jitter={r['jitter_us']:.1f} us "
              f"I1={r['i1']:.1f} (SD {r['i1_sd']:.2f}, peak {r['i1_peak']:.1f}) "
              f"I2={r['i2']:.1f} (late {r['i2_late']:.1f}) uA ratio={r['i1'] / -r['i2']:.2f} "
              f"w1={r['w1']:.0f} w2={r['w2']:.0f} us q1={r['q1']:.1f} q2={r['q2']:.1f} "
              f"net={r['q_net']:.1f} nC ({100 * r['q_net'] / r['q1']:.0f} %)")


if __name__ == "__main__":
    main()
