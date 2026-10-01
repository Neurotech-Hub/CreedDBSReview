"""QC of Joulescope JS220 bench recordings of the FLEX-DBS output into a resistive load.

Usage: python bench_qc.py flexdbs_<pct>p_<pw>us_<f>Hz_<load>k_<datetime>.jls [more.jls ...]
Writes <name>_qc.png next to each input and prints raw and filtered metrics.
The load is read from the <load>k token (e.g. 1k, 47k); files without it are 1 kOhm.

Voltage across the load is the primary measurement. The current channel
shows 2-9 sample (4-18 us) spikes starting 45-60 us after each voltage edge,
consistent with the meter's range switching. Both channels get the same
median filter: it removes impulses shorter than half the window but passes
steps unchanged, so plateau levels and phase widths are preserved. Raw and
filtered metrics are printed side by side so the effect can be checked.
"""
import re
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from pyjls import Reader
from scipy.ndimage import median_filter

MEDIAN_US = 38  # 19 samples at 500 kHz; removes impulses up to 9 samples


def load(path):
    r = Reader(str(path))
    try:
        fs = r.signals[1].sample_rate
        n = r.signals[1].length
        i = r.fsr(1, 0, n).astype(float)
        v = r.fsr(2, 0, n).astype(float)
    finally:
        r.close()
    return fs, i, v


def despike(x, fs):
    k = int(round(MEDIAN_US * 1e-6 * fs)) | 1
    return median_filter(x, size=k, mode="nearest")


def pulse_onsets(v, fs):
    thr = 0.5 * np.percentile(v, 99)
    above = v > thr
    edges = np.flatnonzero(above[1:] & ~above[:-1]) + 1
    keep = np.insert(np.diff(edges) > fs * 1e-3, 0, True)
    return edges[keep]


def snippets(x, on, pre, win):
    return np.array([x[k - pre:k + win] for k in on[1:-1]])


def metrics(i, v, on, fs, pw_us, r_load):
    pre = int(0.3e-3 * fs)
    win = int((6 * pw_us * 1e-6 + 0.8e-3) * fs)
    ts = np.arange(-pre, win) / fs * 1e6
    med_i = np.median(snippets(i, on, pre, win), axis=0)
    med_v = np.median(snippets(v, on, pre, win), axis=0)
    ph1 = (ts > 0.25 * pw_us) & (ts < 0.75 * pw_us)
    ph2 = (ts > 1.5 * pw_us) & (ts < 5.0 * pw_us)
    v1, v2 = med_v[ph1].mean(), med_v[ph2].mean()
    pos, neg = med_v > 0.5 * v1, med_v < 0.5 * v2
    per = int(np.median(np.diff(on)))
    full = snippets(v, on, 200, per - 200)
    return dict(
        f_hz=fs / np.diff(on).mean(),
        i1=np.median(med_i[ph1]) * 1e6, i2=np.median(med_i[ph2]) * 1e6,
        v1=v1 / r_load * 1e6, v2=v2 / r_load * 1e6,
        w1=pos.sum() / fs * 1e6, w2=neg.sum() / fs * 1e6,
        q1=med_v[pos].sum() / fs / r_load * 1e9, q2=med_v[neg].sum() / fs / r_load * 1e9,
        q_net=full.sum(axis=1).mean() / fs / r_load * 1e9,
        jitter=np.std(np.diff(on)) / fs * 1e6,
        ts=ts, med_i=med_i, med_v=med_v,
    )


def report(name, pct, pw_us, f_hz, rk, raw, flt):
    rows = [
        ("Frequency (Hz)", "f_hz", f"{f_hz}"),
        ("Period jitter SD (µs)", "jitter", ""),
        ("Phase 1, current channel (µA)", "i1", f"{6 * pct}"),
        (f"Phase 1, V / {rk} kΩ (µA)", "v1", f"{6 * pct}"),
        ("Phase 2, current channel (µA)", "i2", f"{-6 * pct / 5:.0f}"),
        (f"Phase 2, V / {rk} kΩ (µA)", "v2", f"{-6 * pct / 5:.0f}"),
        ("Phase 1 width (µs)", "w1", f"{pw_us}"),
        ("Phase 2 width (µs)", "w2", f"{5 * pw_us}"),
        ("Phase 1 charge (nC)", "q1", ""),
        ("Phase 2 charge (nC)", "q2", ""),
        ("Net charge per period (nC)", "q_net", "0"),
    ]
    lines = [f"{name}", f"{'':32s}{'raw':>9s}{'filtered':>10s}{'set':>8s}"]
    for label, key, setv in rows:
        lines.append(f"{label:32s}{raw[key]:9.1f}{flt[key]:10.1f}{setv:>8s}")
    lines.append(f"{'Amplitude ratio (V)':32s}{raw['v1'] / -raw['v2']:9.2f}{flt['v1'] / -flt['v2']:10.2f}{'5.00':>8s}")
    lines.append(f"{'Charge imbalance (V, %)':32s}{100 * raw['q_net'] / raw['q1']:9.1f}"
                 f"{100 * flt['q_net'] / flt['q1']:10.1f}{'0':>8s}")
    return "\n".join(lines)


def qc(path):
    path = Path(path)
    m = re.match(r"flexdbs_(\d+)p_(\d+)us_(\d+)Hz(?:_(\d+)k)?_", path.name)
    pct, pw_us, f_hz = (int(g) for g in m.groups()[:3])
    rk = int(m.group(4) or 1)
    r_load = rk * 1000.0
    fs, i, v = load(path)
    i_f, v_f = despike(i, fs), despike(v, fs)
    on = pulse_onsets(v, fs)
    raw = metrics(i, v, on, fs, pw_us, r_load)
    flt = metrics(i_f, v_f, on, fs, pw_us, r_load)
    text = report(path.name, pct, pw_us, f_hz, rk, raw, flt)
    print(text, "\n")

    t = np.arange(len(i)) / fs
    lo = 1.6 * flt["v2"] - 40
    hi = 1.25 * flt["v1"] + 40
    fig, axs = plt.subplots(4, 2, figsize=(12, 12), constrained_layout=True,
                            gridspec_kw=dict(height_ratios=[1, 1, 1, 0.55]))
    ax = axs[:3]
    gs = axs[3, 0].get_gridspec()
    for a in axs[3]:
        a.remove()
    tax = fig.add_subplot(gs[3, :])
    tax.axis("off")
    fig.suptitle(f"{path.name}    median filter {MEDIAN_US} µs on both channels", fontsize=10)

    dec = max(1, len(i) // 20000)
    for col, (x, xf, c, lab) in enumerate(((i * 1e6, i_f * 1e6, "C0", "Current (µA)"),
                                           (v / r_load * 1e6, v_f / r_load * 1e6, "C1", f"V / {rk} kΩ (µA)"))):
        a0 = ax[0, col]
        a0.plot(t[::dec], x[::dec], lw=0.4, color="0.7", label="raw")
        a0.plot(t[::dec], xf[::dec], lw=0.5, color=c, label="filtered")
        a0.set(title="Full record (decimated)", xlabel="Time (s)", ylabel=lab)
        a0.legend(fontsize=8, loc="upper right")

        a, b = on[5] - int(0.3e-3 * fs), on[8] + int(1.5e-3 * fs)
        a1 = ax[1, col]
        a1.plot(t[a:b] * 1e3, x[a:b], lw=0.5, color="0.7", label="raw")
        a1.plot(t[a:b] * 1e3, xf[a:b], lw=0.8, color=c, label="filtered")
        a1.set(title="Three periods", xlabel="Time (ms)", ylabel=lab, ylim=(lo, hi))

        a2 = ax[2, col]
        key = "med_i" if col == 0 else "med_v"
        scale = 1e6 if col == 0 else 1e6 / r_load
        a2.plot(raw["ts"], raw[key] * scale, lw=0.8, color="0.6", label="raw median")
        a2.plot(flt["ts"], flt[key] * scale, lw=1.2, color=c, label="filtered median")
        a2.axvspan(0, pw_us, color="g", alpha=0.08, label="set phase 1")
        a2.axvspan(pw_us, 6 * pw_us, color="r", alpha=0.06, label="set phase 2")
        a2.set(title="Median pulse", xlabel="Time from onset (µs)", ylabel=lab, ylim=(lo, hi))
        a2.legend(fontsize=7, loc="upper right")

    ax[0, 0].set_ylim(lo, hi)
    tax.text(0.5, 0.5, text, fontsize=8, family="monospace", ha="center", va="center",
             transform=tax.transAxes)
    out = path.with_name(path.stem + "_qc.png")
    fig.savefig(out, dpi=130)
    print(out)


if __name__ == "__main__":
    for p in sys.argv[1:]:
        qc(p)
