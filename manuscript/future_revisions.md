# Future revisions

Items deferred beyond the preprint. Not built into the manuscript or the working notes.

- **Timing diagram.** The per-pulse sequence in Section 2.2 (amplifier enable and 150 µs settle; switches close and 30 µs settle; DAC step to *I* for *P*; step to −*I*/5 for 5·*P*; return to reference; switches open; amplifier shutdown) could become a Figure 1 inset or a panel of Figure 5, preferably from a scope capture.

## Bench QC, 1 kΩ load

Follow-ups to the three Joulescope JS220 recordings in `data/bench/` (10, 50 and 100 % amplitude, 180 µs, 130 Hz set; analyzed with `data/bench/bench_qc.py`).

- **More amplitude points.** Measure 0 % and several intermediate settings. The three points give 4.7 µA/% with a +47 µA intercept but deviate from that line by up to ~20 µA, and phase 2 does not shift by the same offset, so the cause (Howland mismatch, DAC code mapping or something else) is not yet identified.
- **Other pulse widths.** Measure several settings, including 90 µs, to separate a fixed timing offset from a proportional error and to find what the 90 µs reference setting actually delivers.
- **Interpulse transient.** A brief transient about 2 ms after each pulse ends (largest on the current channel, ~−8 mV on the voltage channel) matches the "artifact at SHDN+2 ms" described in the firmware comments (LT6020 shutdown coupling through the open switch). The median filter suppresses it, so its absence in filtered plots should not be read as absence in the device; raw traces are shown in grey in the QC figures.
- **Phase 1 step.** At 10 % the phase 1 plateau steps up by ~10 µA partway through (visible in Figure 5A). Not investigated.
- **Load sweep.** Delivered current versus load at 100 and 400 µA to measure the compliance limit (would confirm the ~4.9 V swing used in Section 3.3 and Figure 4B) and the Howland load dependence bounded analytically in Section 7. Section 4.1 and the Limitations currently state that both are derived from the schematic.
- **Other bench items.** A representative pulse at the reference protocol (90 µs); op-amp on-time per pulse (210 µs + 6·*P*, currently from firmware constants).
